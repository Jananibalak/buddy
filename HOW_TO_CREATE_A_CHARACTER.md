# How to create a new Buddy character

A **character** is a folder inside `characters/` that holds her animations.
You can have as many as you like (school uniform, saree, office wear, a festival look...)
and switch between them in **Settings → Character**.

You need about 30 minutes and a Gemini account. You can use any AI that makes images and short videos.

---

## Overview

```
 1. Character picture   →   2. One short video per action   →   3. Settings → New character   →   4. Save
    (Gemini image)            (Gemini video, green screen)       (pick the videos, click Create)
```

| Action   | Needed?      | Used for                                  |
|----------|--------------|-------------------------------------------|
| `walk`   | **Required** | walking in and out                        |
| `wave`   | Recommended  | hello, posture, and any action that's missing |
| `drink`  | Optional     | 💧 water reminder                          |
| `stretch`| Optional     | 🙆 stretch reminder                         |
| `eyes`   | Optional     | 👀 20-20-20 eye break                       |
| `happy`  | Optional     | the dance after you click **Done** (uses wave if missing) |

Start with **walk + wave**. Add the others later; the tool adds them to the same character.

---

## Step 1 – Make the character picture

Attach **your photo** (or describe an original character) and use this prompt in Gemini:

```
Using my attached photo, create a cute chibi cartoon character of me.
Keep my face shape, skin tone, hairstyle and any glasses so it clearly looks like me.
Style: big head, small body, big sparkly eyes, rosy cheeks, soft friendly smile,
clean outlines, flat pastel colours, like a cute mobile game mascot.
Outfit: [WRITE THE OUTFIT HERE – e.g. "a light pink cotton saree with a gold border"].
Full body, standing, facing the viewer, on a plain solid white background.
No text, no shadow, no extra objects.
```

Regenerate until you love it. **Every video is made from this picture**, so it's worth taking your time here.
Save it as `character.png`.

> Tip: for a new **dress** of the same person, only change the *Outfit* line.

---

## Step 2 – Make one video per action

Attach `character.png` and use this **base prompt**, replacing `[ACTION]`:

```
Animate this exact character. Keep her face, hairstyle, outfit, colours and proportions exactly the same.
[ACTION]
Full body always visible, character stays in the centre of the frame at the same size,
static camera, no zoom, no camera movement.
She starts and ends in the same pose so the clip loops smoothly.
Plain solid bright green background, no props other than the ones mentioned, no text.
Cute, bouncy cartoon motion.
```

| Save as       | Replace `[ACTION]` with |
|---------------|-------------------------|
| `walk.mp4`    | `Walking in place, side view, facing RIGHT, a cheerful walk cycle with arms swinging.` |
| `wave.mp4`    | `Facing the viewer, waving hello with one hand and smiling.` |
| `drink.mp4`   | `She holds a small clear water bottle, lifts it, takes a happy sip with eyes closed, lowers it and smiles.` |
| `stretch.mp4` | `Facing the viewer, she raises both arms above her head, stretches tall, leans left, then right, and lowers her arms.` |
| `eyes.mp4`    | `Facing the viewer, she gently rubs her eyes, then looks far away with one hand shading her eyes, then smiles.` |
| `happy.mp4`   | `Facing the viewer, she does a happy little celebration dance with a hop and both arms up.` |

**Check each video before moving on:**
- ✅ face and dress match the picture
- ✅ background is **plain bright green** all the time
- ✅ she stays in the middle and doesn't walk out of the frame
- ✅ in `walk.mp4` she faces **right** (→)

Don't worry about the Gemini ✦ watermark or extra seconds at the start/end – the tool handles those.

Put the videos in your `Buddy` folder (or a sub-folder such as `videos\saree\`).

---

## Step 3 – Turn the videos into a character

One-time setup (in PowerShell):

```
py -m pip install opencv-python-headless numpy pillow
```

### Easy way: from Buddy's Settings (no commands)

1. Right-click Buddy's face icon near the clock → **Settings…**
2. Click **＋ New character…**
3. **Name:** type a new name (e.g. `Saree`), *or* pick an existing character to add more actions to it.
4. Click **Choose…** next to each action and pick its video.
   Or click **Pick several videos…** and select them all at once. Files named `walk.mp4`, `drink.mp4` ... are matched automatically.
5. *(Optional)* **From / To**: use only part of a video, in seconds. Leave `–` for the whole video.
6. Click **Create**. The log shows each video as it's converted (about 5–10 seconds each). Buddy keeps working meanwhile.
7. When it says **Done**, the new character is already selected, with a waving preview. Click **Save**.

### Command-line way (same result)

Handy for doing many characters at once.

One-time setup:

```
py -m pip install opencv-python-headless numpy pillow
```

Then, in PowerShell inside your `Buddy` folder:

```
py make_character.py "Saree" walk=videos\saree\walk.mp4 wave=videos\saree\wave.mp4 drink=videos\saree\drink.mp4
```

- The first argument (`"Saree"`) is the name shown in Settings.
- Each video is written as `action=path`.
- It takes about 5–10 seconds per video. You'll see something like:

```
Making character 'Saree' in ...\characters\saree
  walk     240 frames @ 24 fps  -> loop 6.0s–7.2s, 28 frames, 113x212px
  wave     240 frames @ 24 fps  -> loop 0.5s–8.8s, 99 frames, 140x208px
Done! Open Buddy → Settings → Character → 'Saree'
```

**Add more actions later** by using the **same name** again. Existing actions are kept:

```
py make_character.py "Saree" stretch=videos\saree\stretch.mp4 eyes=videos\saree\eyes.mp4
```

**Use only part of a video**. Gemini sometimes mixes two actions in one clip.
Add `@start-end` in seconds:

```
py make_character.py "Saree" stretch=videos\saree\stretch.mp4@3.5-10
```

---

## Step 4 – Choose her in Buddy (if you used the command line)

1. Right-click Buddy's face icon near the clock → **Settings…**
2. **Character** drop-down → choose **Saree**. She waves in the little preview.
3. **Save**. If she's on screen right now, she changes after she walks away.

---

## What the tool does (so you can fix things)

| Step | What happens | If it goes wrong |
|------|--------------|------------------|
| 1. Read frames | every frame of the video | "Can't open video": check the path / file name |
| 2. Remove green | green → transparent, soft edges, green glow removed | green edges: ask Gemini for a *brighter, plainer* green |
| 3. Keep only her | the biggest shape is kept, small bits (watermark) dropped | a prop disappears: keep props touching her hand |
| 4. Find a loop | picks the part where the last frame matches the first | a "jump" when it repeats: use `@start-end` |
| 5. Crop & scale | centres her, makes her ~204 px tall, feet on one line | wrong size: change `TARGET_HEIGHT` in the tool |
| 6. Save | `walk.png` etc. (all frames side by side) + `clips.json` | – |

## Inside a character folder

```
characters/
  saree/
    character.json   {"name": "Saree", "walk_faces": "right"}
    clips.json       frames, speed (fps) and size of each action
    walk.png  wave.png  drink.png ...
```

You can edit by hand:
- **Rename** a character: change `"name"` in `character.json`.
- **Speed** an action up or down: change its `"fps"` in `clips.json` (e.g. 12 → 15).
- **Delete** a character: delete its folder (keep at least one).
- **Share** a character: zip the folder; the other person unzips it into their `characters/`.

> Use your own photo or an original design. Don't make characters of real celebrities or other people without their permission.
