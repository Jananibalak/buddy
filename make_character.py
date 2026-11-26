"""
make_character.py – turn green-screen videos into a Kutty character pack

Usage (from your Kutty folder):
    py make_character.py "Saree" walk=walk.mp4 wave=wave.mp4 drink=drink.mp4 stretch=stretch.mp4

    • The first argument is the character's display name.
    • Each video is  action=file.mp4
    • Optional time range in seconds:  drink=drink.mp4@1.5-7   (use only 1.5 s .. 7 s of the video)
    • Only "walk" is required. Missing actions fall back to "wave" (or "walk").

It creates:  characters/<name>/  with one PNG strip per action + clips.json + character.json

What it does to each video (the same steps that were done by hand for your first character):
    1. read every frame                    (OpenCV)
    2. remove the green background        -> transparent pixels (soft edges, no green fringe)
    3. remove stray bits like the Gemini ✦ watermark (keeps only the biggest shape = her)
    4. find a smooth loop                  -> the clip ends where it started, so it repeats without a jump
    5. crop around her, scale to Kutty size, keep the feet on one line
    6. save as a strip of frames           -> walk.png, drink.png ...

Needs:  py -m pip install opencv-python-headless numpy pillow
"""
import json
import re
import sys
from pathlib import Path

from paths import app_dir

import cv2
import numpy as np
from PIL import Image

TARGET_HEIGHT = 204          # her standing height on screen, in pixels
OUT_FPS = {"walk": 24}       # walk looks best at 24 fps; everything else 12 fps
DEFAULT_FPS = 12
CHARACTERS = app_dir() / "characters"
ACTIONS = ["walk", "wave", "drink", "stretch", "eyes", "happy"]


class CharacterError(Exception):
    """A problem with the videos – shown to the user instead of crashing."""


def folder_name(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") or "character"


# ---------------------------------------------------------------
# 1. read frames
# ---------------------------------------------------------------
def read_video(path, start=None, end=None):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise CharacterError(f"Can't open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    frames = []
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        frames.append(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
    cap.release()
    a = int((start or 0) * fps)
    b = int(end * fps) if end else len(frames)
    return frames[a:b], fps


# ---------------------------------------------------------------
# 2. green screen -> transparency
# ---------------------------------------------------------------
def key_green(rgb):
    f = rgb.astype(np.float32)
    r, g, b = f[..., 0], f[..., 1], f[..., 2]
    greenness = g - np.maximum(r, b)                     # how much greener than red/blue
    alpha = np.clip(1 - (greenness - 25) / (70 - 25), 0, 1)   # soft edge between 25 and 70
    g = np.minimum(g, np.maximum(r, b) + 8)              # "despill": remove green glow on edges
    return np.dstack([r, g, b, alpha * 255]).clip(0, 255).astype(np.uint8)


# ---------------------------------------------------------------
# 3. keep only her (drop watermark / specks)
# ---------------------------------------------------------------
def keep_main_shape(rgba_frames):
    union = np.zeros(rgba_frames[0].shape[:2], np.uint8)
    for f in rgba_frames:
        union |= (f[..., 3] > 128).astype(np.uint8)     # everywhere she ever is
    n, labels, stats, _ = cv2.connectedComponentsWithStats(union, connectivity=8)
    if n <= 1:
        raise CharacterError("No character found – is the background bright green?")
    biggest = 1 + np.argmax(stats[1:, cv2.CC_STAT_AREA])
    keep = cv2.dilate((labels == biggest).astype(np.uint8), np.ones((9, 9), np.uint8))
    for f in rgba_frames:
        f[..., 3] *= keep
    return rgba_frames


# ---------------------------------------------------------------
# 4. find a smooth loop
# ---------------------------------------------------------------
def small(f):
    return cv2.resize(f[..., 3], (64, 36), interpolation=cv2.INTER_AREA).astype(np.float32)


def best_loop(frames, fps, action):
    """Return (start, end) so frame[end] looks like frame[start] -> seamless repeat."""
    s = [small(f) for f in frames]
    n = len(s)
    if action == "walk":                                 # one walk cycle: 0.8 – 2.5 s
        lengths = range(int(0.8 * fps), min(int(2.5 * fps), n - 1))
        starts = range(0, max(1, n - int(2.5 * fps)))
    else:                                                # actions: as long as possible
        lengths = range(int(n * 0.5), n - 1)
        starts = range(0, max(1, int(n * 0.25)))
    best = (1e9, 0, n - 1)
    for a in starts:
        for L in lengths:
            if a + L < n:
                diff = float(np.abs(s[a] - s[a + L]).mean()) - (0.02 * L if action != "walk" else 0)
                if diff < best[0]:
                    best = (diff, a, a + L)
    return best[1], best[2]


# ---------------------------------------------------------------
# 5. crop, scale, align feet
# ---------------------------------------------------------------
def bbox(alpha):
    ys, xs = np.where(alpha > 128)
    return xs.min(), ys.min(), xs.max(), ys.max()


def crop_and_scale(frames):
    boxes = np.array([bbox(f[..., 3]) for f in frames])
    heights = boxes[:, 3] - boxes[:, 1]
    standing = np.percentile(heights, 25)                # arms-down height (ignores raised arms)
    scale = TARGET_HEIGHT / standing

    # centre on her legs (bottom 15% of the shape) in the first frame
    a0 = frames[0][..., 3]
    x0, y0, x1, y1 = boxes[0]
    legs = a0[int(y1 - 0.15 * (y1 - y0)):y1 + 1]
    centre = int(np.where(legs > 128)[1].mean())
    half = int(max(centre - boxes[:, 0].min(), boxes[:, 2].max() - centre)) + 6
    top, bottom = max(0, boxes[:, 1].min() - 6), boxes[:, 3].max() + 2

    out = []
    for f in frames:
        img = Image.fromarray(f)
        img = img.crop((centre - half, top, centre + half, bottom))   # crop() pads outside with transparent
        out.append(img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS))
    return out


# ---------------------------------------------------------------
# 6. save strip
# ---------------------------------------------------------------
def save_strip(frames, path):
    w, h = frames[0].size
    strip = Image.new("RGBA", (w * len(frames), h))
    for i, f in enumerate(frames):
        strip.paste(f, (i * w, 0))
    strip.save(path, optimize=True)
    return w, h


def make_clip(action, video, start, end, out_dir, log=print):
    frames, fps = read_video(video, start, end)
    if len(frames) < 10:
        raise CharacterError(f"{action}: video is too short (check the time range)")
    rgba = keep_main_shape([key_green(f) for f in frames])
    a, b = best_loop(rgba, fps, action)
    rgba = rgba[a:b]
    out_fps = OUT_FPS.get(action, DEFAULT_FPS)
    step = max(1, round(fps / out_fps))
    rgba = rgba[::step]
    images = crop_and_scale(rgba)
    w, h = save_strip(images, out_dir / f"{action}.png")
    log(f"  {action:<8} ✓  loop {a / fps:.1f}s–{b / fps:.1f}s, {len(images)} frames, {w}x{h}px")
    return {"frames": len(images), "fps": round(fps / step), "frame_width": w, "frame_height": h}


def build_character(name, jobs, log=print):
    """jobs = {action: (video_path, start_seconds_or_None, end_seconds_or_None)}. Returns the folder."""
    folder = CHARACTERS / folder_name(name)
    clips_file = folder / "clips.json"
    clips = json.loads(clips_file.read_text()) if clips_file.exists() else {}   # add to an existing pack
    if "walk" not in jobs and "walk" not in clips:
        raise CharacterError("A walk video is required for a new character.")
    folder.mkdir(parents=True, exist_ok=True)
    log(f"Making character '{name}' in {folder}")
    for action, (video, start, end) in jobs.items():
        log(f"  {action:<8} reading {Path(video).name} ...")
        clips[action] = make_clip(action, video, start, end, folder, log)
        clips_file.write_text(json.dumps(clips, indent=2))       # save after each action
    (folder / "character.json").write_text(json.dumps({"name": name, "walk_faces": "right"}, indent=2))
    log(f"Done! Choose '{name}' in Settings → Character.")
    return folder


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    name = sys.argv[1]
    jobs = {}
    for arg in sys.argv[2:]:
        m = re.fullmatch(r"(\w+)=(.+?)(?:@([\d.]+)-([\d.]+))?", arg)
        if not m:
            sys.exit(f"Don't understand '{arg}'. Use action=video.mp4  or  action=video.mp4@start-end")
        action, video, start, end = m.groups()
        jobs[action] = (Path(video), float(start) if start else None, float(end) if end else None)
    try:
        build_character(name, jobs)
    except CharacterError as e:
        sys.exit(f"Error: {e}")


if __name__ == "__main__":
    main()
