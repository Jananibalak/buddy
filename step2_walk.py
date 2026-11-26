"""
STEP 2 – Bring her to life: animate the frames, walk in, wave, walk out

What you learn here:
  • a game loop      -> a QTimer calls tick() ~60 times a second
  • frame animation  -> show frame 0, 1, 2 ... at the clip's own speed (fps)
  • movement         -> move the whole window a few pixels every tick
  • mirroring        -> the walk clip faces right; flip it to walk left
  • callbacks        -> "walk there, THEN wave, THEN leave" without freezing the app

Run:   py step2_walk.py
She walks in from the right edge, waves, walks out, and comes back every 5 seconds.
Quit:  right-click on her
"""
import json
import sys
from pathlib import Path

from paths import app_dir

from PySide6.QtCore import Qt, QTimer, QElapsedTimer
from PySide6.QtGui import QPixmap, QTransform
from PySide6.QtWidgets import QApplication, QLabel

ASSETS = app_dir() / "assets"
WALK_SPEED = 95        # pixels per second – matched to her stride so feet don't "slide"
STOP_FROM_RIGHT = 250  # where she stops, measured from the right edge of the screen


# ---------------------------------------------------------------
# A Clip = one animation (walk, wave, drink ...) cut into frames
# ---------------------------------------------------------------
class Clip:
    def __init__(self, name, info):
        strip = QPixmap(str(ASSETS / f"{name}.png"))
        w = info["frame_width"]
        # cut the strip: frame i starts at x = i * w
        self.frames = [strip.copy(i * w, 0, w, strip.height()) for i in range(info["frames"])]
        # pre-make mirrored copies once (cheaper than flipping every tick)
        mirror = QTransform().scale(-1, 1)
        self.flipped = [f.transformed(mirror) for f in self.frames]
        self.fps = info["fps"]


def load_clips():
    meta = json.loads((ASSETS / "clips.json").read_text())
    return {name: Clip(name, info) for name, info in meta.items()}


class Kutty(QLabel):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.clips = load_clips()

        # One fixed window size that fits the widest/tallest clip.
        # Frames are drawn bottom-centre, so switching clips never makes her jump.
        self.setFixedSize(max(c.frames[0].width() for c in self.clips.values()),
                          max(c.frames[0].height() for c in self.clips.values()))
        self.setAlignment(Qt.AlignHCenter | Qt.AlignBottom)

        self.area = QApplication.primaryScreen().availableGeometry()   # screen minus taskbar
        self.y_pos = self.area.bottom() - self.height() + 1           # feet on the taskbar
        self.x = 0.0                                                  # float, for smooth movement

        # animation state
        self.clip = None
        self.frame = 0
        self.frame_clock = 0.0
        self.facing_left = False

        # walking state
        self.target = None       # x she is walking to (None = standing still)
        self.on_arrive = None    # what to do when she gets there

        # the game loop: tick() about 60 times per second
        self.clock = QElapsedTimer()
        self.last = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

    # ---------- animation ----------
    def play(self, name):
        self.clip = self.clips[name]
        self.frame = 0
        self.frame_clock = 0.0
        self.show_frame()

    def show_frame(self):
        frames = self.clip.flipped if self.facing_left else self.clip.frames
        self.setPixmap(frames[self.frame])

    def tick(self):
        now = self.clock.elapsed() / 1000.0
        dt = min(0.1, now - self.last)   # seconds since last tick (capped, in case the PC lagged)
        self.last = now

        # 1) advance the animation at the clip's own speed
        self.frame_clock += dt
        while self.frame_clock >= 1.0 / self.clip.fps:
            self.frame_clock -= 1.0 / self.clip.fps
            self.frame = (self.frame + 1) % len(self.clip.frames)
        self.show_frame()

        # 2) move towards the target, if walking
        if self.target is not None:
            direction = 1 if self.target > self.x else -1
            self.x += direction * WALK_SPEED * dt
            arrived = (direction > 0 and self.x >= self.target) or (direction < 0 and self.x <= self.target)
            if arrived:
                self.x = self.target
                self.target = None
                if self.on_arrive:
                    self.on_arrive()          # e.g. start waving
        self.move(round(self.x), self.y_pos)

    # ---------- walking ----------
    def walk_to(self, x, then=None):
        self.facing_left = x < self.x
        self.play("walk")
        self.target = x
        self.on_arrive = then

    # ---------- one visit: in -> wave -> out ----------
    def visit(self):
        self.x = self.area.right() + 10                 # start just off the right edge
        self.move(round(self.x), self.y_pos)
        self.play("walk")
        self.clock.restart(); self.last = 0.0
        self.timer.start(16)                            # ~60 fps
        self.show()
        self.walk_to(self.area.right() - self.width() - STOP_FROM_RIGHT, then=self.say_hi)

    def say_hi(self):
        self.facing_left = False                        # turn to face you
        self.play("wave")
        QTimer.singleShot(4000, self.leave)             # wave for 4 seconds

    def leave(self):
        self.walk_to(self.area.right() + 10, then=self.gone)

    def gone(self):
        self.hide()
        self.timer.stop()                               # no CPU used while she's away
        QTimer.singleShot(5000, self.visit)             # demo: come back in 5 s

    # right-click = quit
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    kutty = Kutty()
    kutty.visit()
    sys.exit(app.exec())
