# 🧸 Buddy – a desktop friend who reminds you to take care of yourself

Buddy is a small animated character (a chibi cartoon of you) who **walks onto your screen only when it's time**
to drink water, stretch, rest your eyes or fix your posture. She shows a speech bubble, waits for you to click
**Done** or **Snooze**, does a happy dance, and walks away again. The rest of the time she's invisible.

Built with **Python + PySide6 (Qt)**. Runs on your own Windows PC with no internet and no accounts.

---

## Features

- 🚶 Walks in from the edge of the screen, does an action, walks back out
- 💧🙆👀 A different animation for each reminder (drink, stretch, rest eyes, wave …)
- 💬 Speech bubble with **Done ✓** / **Snooze**; a happy dance and a floating heart when you're done
- ⏰ Each reminder has its own interval; if two are due together, they come one after another
- 🔕 **Master on/off switch**, an on/off switch per reminder, and **Pause for 1 hour**
- ⚙️ **Settings window** to edit reminders in a table (saved to `settings.json`, applied instantly)
- 👗 **Character packs**: switch dresses or characters; create new ones from your own Gemini videos inside the app
- 🖱️ Never steals focus or blocks clicks; you can keep typing while she's on screen
- 🧩 Built in small steps, each one a working program you can run and learn from

---

## Quick start

### Option A – build the app (recommended)
1. Install the requirements below (once).
2. Double-click **`build.bat`**. After 1–3 minutes, `dist\Buddy\Buddy.exe` opens in Explorer.
3. Move the `dist\Buddy` folder anywhere you like (e.g. `C:\Users\Admin\Apps\Buddy`), keeping everything inside it together.
4. Double-click **Buddy.exe** → right-click her tray icon → tick **Start with Windows**.

### Option B – run from the Python files

```powershell
# 1. Requirements (once) – Python 3.10+ (tested with 3.13)
py -m pip install PySide6-Essentials
py -m pip install opencv-python-headless numpy pillow     # only needed to create new characters

# 2. Run (from the Buddy folder)
cd C:\Users\Admin\Buddy
py buddy.py
```

Her face appears as an icon near the clock (click **^** if hidden). Right-click it for the menu.
With **Quick test mode** on (the default), 1 minute = 3 seconds, so you'll see her within a minute.
Turn it off in Settings for real use.

---

## Using Buddy

| Where | What you can do |
|-------|-----------------|
| **Speech bubble** | **Done ✓**: dance, then come back after the full interval · **Snooze**: come back in 5 min · no click for 90 s counts as snooze |
| **Tray menu** (right-click her face) | Show a reminder now ▸ · Reminders ON ✓ (master switch) · Pause for 1 hour · Resume now · Start with Windows ✓ · Settings… · Quit |
| **Tray tooltip** (hover) | "next: Rest eyes in 12 min" / "paused (40 min left)" / "reminders OFF" |
| **Settings** (double-click the icon) | Master switch · snooze length · test mode · **Character** picker with preview · **Bubble** style (cute / mini / glass / classic) · **＋ New character…** · reminders table (On, Name, Every, Action, Message) · Add / Delete / ▶ Preview · Save |

---

## Folder structure

```
Buddy/
├── step1_window.py         Step 1 – a transparent, always-on-top window (learning step)
├── step2_walk.py           Step 2 – animation + walking            ┐
├── step3_reminders.py      Step 3 – scheduler + queue               │  each step builds on
├── step4_bubble.py         Step 4 – speech bubble, Done/Snooze      │  the one before it
├── step5_settings.py       Step 5 – tray icon, settings, switches   │  (inheritance)
├── step6_characters.py     Step 6 – character packs                 ┘
├── buddy.py                Step 7 – the app: single instance, Start with Windows  ← RUN THIS
├── paths.py                finds the right folder (script vs Buddy.exe)
├── build.bat               builds dist\Buddy\Buddy.exe with PyInstaller
├── buddy.ico               her face, used as the app icon
├── make_character.py       green-screen videos → character pack (used by Settings, or from the command line)
├── settings.json           your settings (created on first run)
├── HOW_TO_CREATE_A_CHARACTER.md
├── assets/                 the original animations (copied into characters/ on first run)
└── characters/
    ├── school_uniform/     character.json · clips.json · walk.png · wave.png · drink.png …
    └── saree/              (any characters you create)
```

---

## How it works

### The big picture

```
                    ┌──────────────────── every 1 s ────────────────────┐
                    ▼                                                   │
  settings.json ─► Scheduler ── due? ──► Queue ──► Visit ──────────────┘
                    (Step 3)              (Step 3)    │
                                                      ├─ walk in        (Step 2: game loop moves the window)
                                                      ├─ do the action  (clip for this reminder)
                                                      ├─ speech bubble  (Step 4: wait for Done/Snooze)
                                                      ├─ happy dance    (if Done)
                                                      └─ walk out → hide → schedule next time
```

### Each step adds one layer (inheritance)

```
Buddy (step2) → ReminderBuddy (step3) → BubbleBuddy (step4) → TrayBuddy (step5) → CharacterBuddy (step6)
```

Each class **inherits** everything from the one before and only **overrides** what changes.
For example, Step 3 replaces Step 2's "wave then come back in 5 s" with "do this reminder's action, then reschedule".
That's why each step file is short, and why every step can still be run on its own.

### Step 1: a window that's only her
- `FramelessWindowHint`: no title bar · `WindowStaysOnTopHint`: above all apps · `Tool`: no taskbar button, not in Alt+Tab
- `WA_TranslucentBackground`: transparent pixels show the desktop behind, with smooth edges
- `availableGeometry()`: the screen minus the taskbar, so her feet rest on top of the taskbar

### Step 2: animation and walking
- **Sprite strips**: each action is one PNG with all frames side by side. Frame *i* is the slice at `x = i × frame_width`.
- **Game loop**: a `QTimer` calls `tick()` every 16 ms (~60 fps), but only while she's visible.
- **Time-based**: `dt` = seconds since the last tick. Frames advance at the clip's own fps, and she moves `speed × dt`, so she's equally smooth on fast and slow PCs.
- **The window itself walks**: the small window is moved each tick, so she never covers the rest of your screen.
- **Mirroring**: the walk clip faces right; mirrored copies (made once at load time) are used for walking left.
- **Callbacks**: `walk_to(x, then=next_step)` chains steps without freezing the app.

### Step 3: scheduler and queue
- Each reminder is a `@dataclass` (name, every, gesture, message, next_at).
- A slow timer (every 1 s) checks `now >= next_at`. Due reminders join a `deque` queue.
- Only one visit at a time. When she leaves, `gone()` sets that reminder's next time and starts the next queued one.
- While queued, `next_at = infinity`, so the reminder is never added twice.

### Step 4: the speech bubble
- The bubble is its own transparent window, drawn by hand in `paintEvent` with `QPainterPath` (rounded box + tail + soft shadow).
- **Signals & slots**: the bubble only *announces* `done` / `snooze`, and Buddy *listens*. Neither knows the other's internals.
- **Polite**: `WindowDoesNotAcceptFocus` and `WA_ShowWithoutActivating` mean it appears without interrupting your typing.
- **Waiting without freezing**: a 90 s single-shot timer races your click, and whichever comes first wins (an `asking` flag ignores the rest).
- `QPropertyAnimation` fades the bubble in and floats and fades the heart.

### Step 5: settings, tray and switches
- **Config file**: `settings.json` holds your choices. On load it's merged with defaults (`{**DEFAULT, **data}`), so older files keep working.
- **Three levels of "off"**: master switch (saved) → pause until a time (not saved) → per-reminder `enabled`.
- **No pile-up**: when reminders resume after a pause, all countdowns restart fresh instead of everything firing at once.
- **Live reload**: Save emits a `saved` signal. Reminders you didn't change *keep their countdown*; changed ones restart.
- The table uses real widgets inside cells (`setCellWidget`): checkbox, number box, drop-down.

### Step 6: character packs
- **Plugin folders**: every `characters/*/clips.json` is a character. Adding a folder adds a character, with no code change and no restart.
- **Fallbacks**: a missing action plays `wave` (or `walk`), and a missing `happy` uses `wave`, so a pack with only walk + wave works everywhere.
- **Migration**: the first run copies `assets/` into `characters/school_uniform/` automatically.
- **Safe switching**: changing character while she's on screen waits until she has walked off.
- **Background thread**: "New character" converts videos in a `QThread`. The worker only talks to the window through signals, because Qt widgets must only be touched from the main thread.

### Step 7: a real app
- **PyInstaller** bundles Python, Qt and your code into `dist\Buddy\` with `Buddy.exe`. `--windowed` means no black console window.
- **`paths.app_dir()`**: inside an exe, `__file__` points to a hidden internal folder, so settings and characters are looked up next to `Buddy.exe` instead. This keeps them visible and editable.
- **One Buddy at a time**: a `QLockFile` in the temp folder. A second copy sees the lock and only says "already running".
- **Start with Windows**: adds an entry under `HKEY_CURRENT_USER\...\Run` (no admin rights needed). It also shows in **Task Manager → Startup apps**.
- **Real defaults**: a brand-new `settings.json` starts with test mode OFF.

### make_character.py: videos → character pack
| # | Step | How |
|---|------|-----|
| 1 | Read frames | OpenCV `VideoCapture`, optional `@start-end` range |
| 2 | Remove green | alpha from "how much greener than red/blue", soft edge, green "despill" |
| 3 | Keep only her | union of all frames → connected components → keep the biggest (drops the ✦ watermark) |
| 4 | Find a loop | compare small silhouettes; pick start/end frames that match (walk: one 0.8–2.5 s cycle) |
| 5 | Crop & scale | centre on her legs, scale her standing height to 204 px, feet aligned at the bottom |
| 6 | Save | PNG strip per action + `clips.json` (frames, fps, size) + `character.json` (name) |

---

## Configuration reference

### `settings.json`
```json
{
  "enabled": true,              // master switch
  "test_mode": false,           // true = 1 minute becomes 3 seconds
  "snooze_minutes": 5,
  "character": "school_uniform",// folder name in characters/
  "reminders": [
    { "enabled": true, "name": "Drink water", "every": 45,
      "gesture": "drink", "message": "Sip sip! Time for a glass of water 💧" }
  ]
}
```
*(Comments are only for explanation; real JSON can't contain them.)* Easiest is to edit everything in the Settings window.

### Settings in the code (constants at the top of each file)
| File | Constant | Meaning |
|------|----------|---------|
| step2_walk.py | `WALK_SPEED` | pixels per second (wrong values make her feet "slide") |
| step2_walk.py | `STOP_FROM_RIGHT` | where she stops, from the right edge |
| step4_bubble.py | `AUTO_DISMISS_SECONDS` | how long she waits for a click |
| make_character.py | `TARGET_HEIGHT` | her height in pixels for new characters |

### A character pack
```
characters/saree/
  character.json   {"name": "Saree", "walk_faces": "right"}
  clips.json       {"walk": {"frames": 28, "fps": 24, "frame_width": 113, "frame_height": 212}, ...}
  walk.png  wave.png  drink.png  stretch.png  eyes.png  happy.png
```
How to make one: see **HOW_TO_CREATE_A_CHARACTER.md**.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `pip install PySide6` is very slow | install `PySide6-Essentials` instead (much smaller, has everything Buddy needs) |
| No tray icon | click the **^** arrow by the clock; drag her icon onto the taskbar to keep it visible |
| She never appears | check the tray tooltip: reminders OFF? paused? all reminders unticked? Try **Show a reminder now** |
| She appears too often / too rarely | **Quick test mode** is probably on (1 min = 3 s). Untick it → Save |
| "No module named cv2" when creating a character | `py -m pip install opencv-python-headless numpy pillow` |
| Green edges around a new character | ask Gemini for a *plainer, brighter* green background and regenerate |
| A "jump" when an action repeats | use **From / To** to pick the part of the video that starts and ends in the same pose |
| She walks backwards | the walk video must show her facing **right** |
| Closing the PowerShell window stops her | expected with `py`. Use `Buddy.exe` (build.bat) instead |
| Windows says "Windows protected your PC" | the exe isn't signed: **More info → Run anyway** (only for the Buddy.exe you built yourself) |
| Build fails in build.bat | close any running Buddy.exe first, then run build.bat again |
| `dist\Buddy` is big (a few hundred MB) | normal: it contains Python, Qt, OpenCV. Don't email it; copy the folder |

---

## Roadmap

- [x] Steps 1–6: window, walking, scheduler, bubble, settings & tray, character packs
- [x] **Step 7** – package as `Buddy.exe` (PyInstaller), start with Windows
- [ ] **Step 8** – learning mode: offline RAG with Ollama over your notes, micro-lessons in the bubble
- [ ] **Step 9** – "Ask Buddy" chat and quiz cards with spaced repetition
- [ ] Ideas: quiet hours, drag her around, click her to wave, random strolls, daily water count

---

*Your character is made from your own photo with Gemini. Please use your own likeness or original designs, not real celebrities.*
