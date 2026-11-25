"""
STEP 6 – Character packs: pick who visits you (different dresses / characters)

What you learn here:
  • a plugin-style folder  -> every folder in characters/ is one character; no code change to add one
  • fallbacks              -> a pack with only walk + wave still works for every reminder
  • migration              -> first run moves your existing assets/ into the first pack automatically
  • swapping at runtime    -> change character in Settings, she changes on her next visit

  • background work        -> converting videos runs in a QThread, so Buddy never freezes

Run:   py step6_characters.py
Make a new character:  Settings → "＋ New character…"  (or make_character.py, see HOW_TO_CREATE_A_CHARACTER.md)
"""
import json
import shutil
import sys
from pathlib import Path

from paths import app_dir

from PySide6.QtCore import Qt, QTimer, QThread, Signal
from PySide6.QtGui import QPixmap, QTransform, QIcon, QFont
from PySide6.QtWidgets import (QApplication, QLabel, QComboBox, QHBoxLayout, QVBoxLayout, QGridLayout,
                               QSystemTrayIcon, QDialog, QLineEdit, QPushButton, QFileDialog,
                               QDoubleSpinBox, QPlainTextEdit, QProgressBar)

import step4_bubble as s4
import step5_settings as s5

HERE = app_dir()
CHARACTERS = HERE / "characters"
STANDARD_ACTIONS = ["drink", "stretch", "eyes", "wave"]


# ---------------------------------------------------------------
# 1. CHARACTER PACKS ON DISK
#    characters/<folder>/character.json  {"name": "School uniform"}
#                        clips.json       {"walk": {"frames":31, "fps":24, ...}, ...}
#                        walk.png, wave.png, drink.png ...
# ---------------------------------------------------------------
def ensure_first_pack():
    """Migration: on first run, copy the original assets/ into characters/school_uniform."""
    if any(CHARACTERS.glob("*/clips.json")):
        return
    src = HERE / "assets"
    if not (src / "clips.json").exists():
        sys.exit("No characters found. Put a pack in characters/ or keep the assets/ folder.")
    dst = CHARACTERS / "school_uniform"
    shutil.copytree(src, dst, dirs_exist_ok=True)
    (dst / "character.json").write_text(json.dumps({"name": "School uniform", "walk_faces": "right"}, indent=2))
    print(f"Created first character pack: {dst}")


def list_packs():
    """{folder_name: display_name} for every valid pack."""
    packs = {}
    for clips_file in sorted(CHARACTERS.glob("*/clips.json")):
        folder = clips_file.parent
        info_file = folder / "character.json"
        info = json.loads(info_file.read_text()) if info_file.exists() else {}
        packs[folder.name] = info.get("name", folder.name.replace("_", " ").title())
    return packs


class PackClip:
    """Same as Step 2's Clip, but loads from any character folder."""
    def __init__(self, folder, name, info):
        strip = QPixmap(str(folder / f"{name}.png"))
        w = info["frame_width"]
        self.frames = [strip.copy(i * w, 0, w, strip.height()) for i in range(info["frames"])]
        mirror = QTransform().scale(-1, 1)
        self.flipped = [f.transformed(mirror) for f in self.frames]
        self.fps = info["fps"]


def load_pack(key, only=None):
    folder = CHARACTERS / key
    meta = json.loads((folder / "clips.json").read_text())
    clips = {name: PackClip(folder, name, info) for name, info in meta.items()
             if (only is None or name in only) and (folder / f"{name}.png").exists()}
    # fallbacks: missing actions borrow another clip, so any reminder works with any pack
    if "wave" not in clips and "walk" in clips:
        clips["wave"] = clips["walk"]
    if "happy" not in clips and "wave" in clips:
        clips["happy"] = clips["wave"]
    return clips


# ---------------------------------------------------------------
# 2. "NEW CHARACTER" WINDOW – pick videos, convert them in the background
# ---------------------------------------------------------------
ACTION_HELP = {
    "walk": "walk (required) – side view, facing right",
    "wave": "wave – hello / used when an action is missing",
    "drink": "drink – 💧 water reminder",
    "stretch": "stretch – 🙆 stretch reminder",
    "eyes": "eyes – 👀 eye break",
    "happy": "happy – dance after Done",
}
VIDEO_FILTER = "Videos (*.mp4 *.mov *.webm *.mkv *.avi)"


class MakerThread(QThread):
    """Runs make_character.build_character() off the main thread.
    Signals carry messages back to the window safely."""
    log = Signal(str)
    done = Signal(str)       # folder key of the finished character
    failed = Signal(str)

    def __init__(self, name, jobs):
        super().__init__()
        self.name, self.jobs = name, jobs

    def run(self):           # everything in run() happens in the background thread
        try:
            import make_character as mc
            folder = mc.build_character(self.name, self.jobs, log=self.log.emit)
            self.done.emit(folder.name)
        except ImportError as e:
            self.failed.emit(f"{e}\nInstall once:  py -m pip install opencv-python-headless numpy pillow")
        except Exception as e:                       # CharacterError or anything unexpected
            self.failed.emit(str(e))


class NewCharacterDialog(QDialog):
    created = Signal(str)

    def __init__(self, parent, packs):
        super().__init__(parent)
        self.setWindowTitle("Buddy – New character")
        self.resize(760, 520)
        self.thread = None

        title = QLabel("Create a character from your green-screen videos")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        hint = QLabel("Give it a name (or pick an existing character to add actions to), choose the videos, "
                      "then click Create. Only <b>walk</b> is required for a new character. "
                      "Optional: use only part of a video with From / To (seconds, 0 = whole video).")
        hint.setWordWrap(True)

        self.name = QComboBox()
        self.name.setEditable(True)                  # type a new name OR choose an existing one
        self.name.addItems(packs.values())
        self.name.setEditText("")
        self.name.lineEdit().setPlaceholderText("e.g. Saree")

        pick_many = QPushButton("Pick several videos…")
        pick_many.setToolTip("Select many files at once – matched by file name (walk.mp4, drink.mp4 ...)")
        pick_many.clicked.connect(self.pick_many)
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        name_row.addWidget(self.name, 1)
        name_row.addWidget(pick_many)

        grid = QGridLayout()
        for col, text in enumerate(["Action", "Video", "", "From", "To", ""]):
            grid.addWidget(QLabel(f"<b>{text}</b>"), 0, col)
        self.rows = {}
        for r, action in enumerate(ACTION_HELP, start=1):
            path = QLineEdit(); path.setReadOnly(True); path.setPlaceholderText("no video chosen")
            choose = QPushButton("Choose…")
            start = QDoubleSpinBox(); end = QDoubleSpinBox()
            for sb in (start, end):
                sb.setRange(0, 600); sb.setSuffix(" s"); sb.setDecimals(1); sb.setSpecialValueText("–")
            clear = QPushButton("✕"); clear.setFixedWidth(28)
            choose.clicked.connect(lambda _=False, a=action: self.pick_one(a))
            clear.clicked.connect(lambda _=False, p=path: p.clear())
            for col, w in enumerate([QLabel(ACTION_HELP[action]), path, choose, start, end, clear]):
                grid.addWidget(w, r, col)
            self.rows[action] = (path, start, end)
        grid.setColumnStretch(1, 1)

        self.log_box = QPlainTextEdit(); self.log_box.setReadOnly(True)
        self.log_box.setFont(QFont("Consolas", 9))
        self.progress = QProgressBar(); self.progress.setRange(0, 0); self.progress.hide()   # "busy" bar

        self.create_btn = QPushButton("Create")
        self.create_btn.setStyleSheet("background:#5CC98B; color:white; padding:6px 18px; border-radius:6px;")
        self.create_btn.clicked.connect(self.create)
        close_btn = QPushButton("Close"); close_btn.clicked.connect(self.close)
        buttons = QHBoxLayout(); buttons.addWidget(self.progress, 1); buttons.addWidget(close_btn); buttons.addWidget(self.create_btn)

        layout = QVBoxLayout(self)
        for item in (title, hint):
            layout.addWidget(item)
        layout.addLayout(name_row)
        layout.addLayout(grid)
        layout.addWidget(self.log_box, 1)
        layout.addLayout(buttons)

    # ----- choosing files -----
    def pick_one(self, action):
        file, _ = QFileDialog.getOpenFileName(self, f"Video for '{action}'", "", VIDEO_FILTER)
        if file:
            self.rows[action][0].setText(file)

    def pick_many(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Choose videos (named walk, wave, drink ...)", "", VIDEO_FILTER)
        unmatched = []
        for f in files:
            stem = Path(f).stem.lower()
            action = next((a for a in ACTION_HELP if a in stem), None)
            if action:
                self.rows[action][0].setText(f)
            else:
                unmatched.append(Path(f).name)
        if unmatched:
            self.log_box.appendPlainText("Couldn't tell which action these are – use Choose… for them:\n  "
                                         + "\n  ".join(unmatched))

    # ----- converting -----
    def create(self):
        name = self.name.currentText().strip()
        jobs = {a: (Path(p.text()), s.value() or None, e.value() or None)
                for a, (p, s, e) in self.rows.items() if p.text()}
        if not name:
            return self.log_box.appendPlainText("Please type a name first.")
        if not jobs:
            return self.log_box.appendPlainText("Please choose at least one video.")
        self.set_busy(True)
        self.log_box.appendPlainText(f"Working… about 5–10 seconds per video.")
        self.thread = MakerThread(name, jobs)
        self.thread.log.connect(self.log_box.appendPlainText)
        self.thread.done.connect(self.on_done)
        self.thread.failed.connect(self.on_failed)
        self.thread.start()                          # returns immediately – the window stays responsive

    def on_done(self, key):
        self.set_busy(False)
        self.created.emit(key)
        for p, s, e in self.rows.values():
            p.clear(); s.setValue(0); e.setValue(0)

    def on_failed(self, message):
        self.set_busy(False)
        self.log_box.appendPlainText(f"❌ {message}")

    def set_busy(self, busy):
        self.progress.setVisible(busy)
        self.create_btn.setEnabled(not busy)
        self.name.setEnabled(not busy)

    def closeEvent(self, event):
        if self.thread and self.thread.isRunning():  # don't close mid-conversion
            self.log_box.appendPlainText("Please wait – still converting…")
            event.ignore()
        else:
            super().closeEvent(event)


# ---------------------------------------------------------------
# 3. SETTINGS WINDOW + character picker with a live preview
# ---------------------------------------------------------------
class CharacterSettingsWindow(s5.SettingsWindow):
    def __init__(self, gestures, icon, packs):
        super().__init__(gestures, icon)
        self.resize(820, 580)

        self.char_box = QComboBox()
        self.fill_packs(packs)
        self.char_box.currentIndexChanged.connect(self.load_preview)

        self.preview_label = QLabel()
        self.preview_label.setFixedSize(120, 150)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background:#EEF3FF; border-radius:10px;")
        self.preview_frames, self.preview_i = [], 0
        self.preview_timer = QTimer(self)
        self.preview_timer.timeout.connect(self.next_preview_frame)

        new_btn = QPushButton("＋ New character…")
        new_btn.clicked.connect(self.open_new_character)

        self.bubble_box = QComboBox()                 # speech bubble look: cute / mini / glass / classic
        self.bubble_box.addItems(list(s4.BUBBLE_STYLES))

        row = QHBoxLayout()
        row.addWidget(QLabel("Character:"))
        row.addWidget(self.char_box)
        row.addWidget(self.preview_label)
        row.addWidget(new_btn)
        row.addSpacing(20)
        row.addWidget(QLabel("Bubble:"))
        row.addWidget(self.bubble_box)
        row.addStretch()
        self.layout().insertLayout(2, row)            # put it under the title + master switch

    def fill_packs(self, packs):
        self.char_box.blockSignals(True)
        self.char_box.clear()
        for key, name in packs.items():
            self.char_box.addItem(name, key)          # show the name, remember the folder key
        self.char_box.blockSignals(False)

    def open_new_character(self):
        dialog = NewCharacterDialog(self, list_packs())
        dialog.created.connect(self.on_character_created)
        dialog.show()

    def on_character_created(self, key):
        self.fill_packs(list_packs())
        self.char_box.setCurrentIndex(max(0, self.char_box.findData(key)))
        self.load_preview()                           # you see her waving right away; Save to use her

    def load_preview(self):
        key = self.char_box.currentData()
        if not key:
            return
        clips = load_pack(key, only={"wave", "walk"})
        clip = clips["wave"]
        self.preview_frames = [f.scaledToHeight(140, Qt.SmoothTransformation) for f in clip.frames]
        self.preview_i = 0
        self.preview_timer.start(int(1000 / clip.fps))

    def next_preview_frame(self):
        if self.preview_frames:
            self.preview_label.setPixmap(self.preview_frames[self.preview_i % len(self.preview_frames)])
            self.preview_i += 1

    def open_with(self, settings):
        self.fill_packs(list_packs())                 # new packs appear without restarting Buddy
        i = self.char_box.findData(settings.get("character"))
        self.char_box.setCurrentIndex(max(0, i))
        self.bubble_box.setCurrentText(settings.get("bubble_style", s4.BUBBLE_STYLE))
        self.load_preview()
        super().open_with(settings)

    def closeEvent(self, event):
        self.preview_timer.stop()                     # no animating while closed
        super().closeEvent(event)

    def on_save(self):
        """Same as Step 5's Save, plus the chosen character."""
        reminders = [self.row_to_dict(r) for r in range(self.table.rowCount())]
        settings = {
            "enabled": self.master.isChecked(),
            "test_mode": self.test_mode.isChecked(),
            "snooze_minutes": self.snooze.value(),
            "character": self.char_box.currentData(),
            "bubble_style": self.bubble_box.currentText(),
            "reminders": [r for r in reminders if r["name"]],
        }
        s5.save_settings(settings)
        self.saved.emit(settings)
        self.close()


# ---------------------------------------------------------------
# 4. BUDDY THAT CAN CHANGE CHARACTER
# ---------------------------------------------------------------
class CharacterBuddy(s5.TrayBuddy):
    def __init__(self, settings):
        ensure_first_pack()
        packs = list_packs()
        settings.setdefault("character", next(iter(packs)))
        if settings["character"] not in packs:             # pack deleted? use the first one
            settings["character"] = next(iter(packs))
        self.pending_character = None
        super().__init__(settings)                          # Steps 2–5 (loads assets/ at first)

        self.use_character(settings["character"])           # ...then switch to the chosen pack
        self.pending_bubble = None
        self.set_bubble_style(settings.get("bubble_style", s4.BUBBLE_STYLE))

        # replace Step 5's settings window with the one that has the character picker
        gestures = sorted({*STANDARD_ACTIONS,
                           *[a for k in packs for a in json.loads((CHARACTERS / k / "clips.json").read_text())]}
                          - {"walk", "happy"})
        self.settings_window = CharacterSettingsWindow(gestures, self.icon, packs)
        self.settings_window.saved.connect(self.apply_settings)
        self.settings_window.preview.connect(lambda d: self.show_now(s5.to_reminder(d)))

    def use_character(self, key):
        self.clips = load_pack(key)
        self.character = key
        # window size fits the biggest frame of this pack; feet stay on the taskbar line
        self.setFixedSize(max(c.frames[0].width() for c in self.clips.values()),
                          max(c.frames[0].height() for c in self.clips.values()))
        self.y_pos = self.area.bottom() - self.height() + 1
        self.icon = self.make_icon()
        self.tray.setIcon(self.icon)
        print(f"Character: {list_packs().get(key, key)}")

    def set_bubble_style(self, style):
        """Swap the speech bubble for one with a different look."""
        if self.asking:                                     # bubble is on screen: change it next time
            self.pending_bubble = style
            return
        self.bubble.hide()
        self.bubble.deleteLater()
        self.bubble = s4.SpeechBubble(style)
        self.bubble.set_snooze_minutes(self.settings["snooze_minutes"])
        self.bubble.done.connect(lambda: self.answer("done"))
        self.bubble.snooze.connect(lambda: self.answer("snooze"))

    def play(self, name):
        if name not in self.clips:                          # e.g. "drink" missing in this pack
            name = "wave" if "wave" in self.clips else "walk"
        super().play(name)

    def apply_settings(self, new):
        if new.get("character") and new["character"] != self.character:
            if self.busy:
                self.pending_character = new["character"]   # she's on screen: switch after she leaves
            else:
                self.use_character(new["character"])
        if new.get("bubble_style") and new["bubble_style"] != self.bubble.style_name:
            self.set_bubble_style(new["bubble_style"])
        super().apply_settings(new)

    def gone(self):
        if self.pending_character:
            self.hide()
            self.use_character(self.pending_character)
            self.pending_character = None
        if self.pending_bubble:
            self.set_bubble_style(self.pending_bubble)
            self.pending_bubble = None
        super().gone()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("No system tray found – the tray icon won't show.")
    buddy = CharacterBuddy(s5.load_settings())
    print(f"Buddy is running. Characters folder: {CHARACTERS}")
    sys.exit(app.exec())
