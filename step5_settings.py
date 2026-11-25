"""
STEP 5 – Tray icon + Settings window (saved in settings.json)

What you learn here:
  • config files     -> settings live in settings.json, not in the code
  • a tray icon      -> Buddy's "remote control" near the clock
  • a table editor   -> QTableWidget with checkboxes, number boxes and drop-downs inside cells
  • live reload      -> Save applies the new settings immediately, no restart
  • on/off switches  -> one master switch for ALL reminders + one per reminder + "pause 1 hour"

Run:   py step5_settings.py
Then right-click her face icon near the clock (click the ^ arrow if you don't see it).
"""
import json
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from paths import app_dir

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon, QAction, QFont
from PySide6.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QCheckBox, QSpinBox,
                               QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
                               QVBoxLayout, QHBoxLayout, QSystemTrayIcon, QMenu, QAbstractItemView)

import step3_reminders as s3
import step4_bubble as s4
from step4_bubble import BubbleBuddy

SETTINGS_FILE = app_dir() / "settings.json"

# ---------------------------------------------------------------
# 1. SETTINGS FILE – load / save, with sensible defaults
# ---------------------------------------------------------------
DEFAULT_SETTINGS = {
    "enabled": True,          # master switch: False = no reminders at all
    "test_mode": True,        # True: 1 minute = 3 seconds
    "snooze_minutes": 5,
    "reminders": [
        {"enabled": True, "name": "Drink water", "every": 45, "gesture": "drink",
         "message": "Sip sip! Time for a glass of water 💧"},
        {"enabled": True, "name": "Rest eyes", "every": 20, "gesture": "eyes",
         "message": "20-20-20! Look at something far away for 20 seconds 👀"},
        {"enabled": True, "name": "Posture", "every": 30, "gesture": "wave",
         "message": "Shoulders back, sit up tall! 💪"},
        {"enabled": True, "name": "Stretch", "every": 60, "gesture": "stretch",
         "message": "Stand up and stretch those arms high! 🙆"},
    ],
}


def load_settings():
    if SETTINGS_FILE.exists():
        try:
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            return {**DEFAULT_SETTINGS, **data}       # fill in any missing keys with defaults
        except (json.JSONDecodeError, OSError) as e:
            print(f"Could not read settings.json ({e}) – using defaults")
    save_settings(DEFAULT_SETTINGS)                    # first run: create the file
    return json.loads(json.dumps(DEFAULT_SETTINGS))    # a deep copy


def save_settings(settings):
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")


# A reminder now also has its own on/off switch
@dataclass(eq=False)
class Reminder(s3.Reminder):
    enabled: bool = True


def to_reminder(d):
    return Reminder(name=d["name"], every=int(d["every"]), gesture=d["gesture"],
                    message=d["message"], enabled=bool(d.get("enabled", True)))


# ---------------------------------------------------------------
# 2. THE SETTINGS WINDOW
# ---------------------------------------------------------------
class SettingsWindow(QWidget):
    saved = Signal(dict)      # "here are the new settings"
    preview = Signal(dict)    # "show me this reminder now"

    COLS = ["On", "Name", "Every", "Action", "Message"]

    def __init__(self, gestures, icon):
        super().__init__()
        self.gestures = gestures
        self.setWindowTitle("Buddy – Settings")
        self.setWindowIcon(icon)
        self.resize(820, 420)

        title = QLabel("🧸  Buddy settings")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))

        # --- global options ---
        self.master = QCheckBox("Reminders ON  (untick to stop ALL reminders)")
        self.master.setFont(QFont("Segoe UI", 10, QFont.Bold))
        self.test_mode = QCheckBox("Quick test mode (1 minute = 3 seconds)")
        self.snooze = QSpinBox()
        self.snooze.setRange(1, 120)
        self.snooze.setSuffix(" min")
        top = QHBoxLayout()
        top.addWidget(self.master)
        top.addStretch()
        top.addWidget(QLabel("Snooze:"))
        top.addWidget(self.snooze)

        # --- reminders table ---
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        header = self.table.horizontalHeader()
        for col, mode in enumerate([QHeaderView.ResizeToContents, QHeaderView.ResizeToContents,
                                    QHeaderView.ResizeToContents, QHeaderView.ResizeToContents,
                                    QHeaderView.Stretch]):
            header.setSectionResizeMode(col, mode)

        # --- buttons ---
        add_btn = QPushButton("＋ Add reminder")
        del_btn = QPushButton("Delete selected")
        prev_btn = QPushButton("▶ Preview selected")
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.setDefault(True)
        save_btn.setStyleSheet("background:#5CC98B; color:white; padding:6px 18px; border-radius:6px;")

        add_btn.clicked.connect(lambda: self.add_row({"enabled": True, "name": "New reminder", "every": 30,
                                                      "gesture": "wave", "message": "Hello! 😊"}))
        del_btn.clicked.connect(self.delete_selected)
        prev_btn.clicked.connect(self.preview_selected)
        save_btn.clicked.connect(self.on_save)
        cancel_btn.clicked.connect(self.close)

        buttons = QHBoxLayout()
        for b in (add_btn, del_btn, prev_btn):
            buttons.addWidget(b)
        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(save_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addLayout(top)
        layout.addWidget(self.test_mode)
        layout.addWidget(self.table)
        layout.addLayout(buttons)

    # fill the window from a settings dict
    def open_with(self, settings):
        self.master.setChecked(settings["enabled"])
        self.test_mode.setChecked(settings["test_mode"])
        self.snooze.setValue(settings["snooze_minutes"])
        self.table.setRowCount(0)
        for r in settings["reminders"]:
            self.add_row(r)
        self.show()
        self.raise_()
        self.activateWindow()

    def add_row(self, r):
        row = self.table.rowCount()
        self.table.insertRow(row)

        on = QTableWidgetItem()                                   # a checkbox cell
        on.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        on.setCheckState(Qt.Checked if r.get("enabled", True) else Qt.Unchecked)
        self.table.setItem(row, 0, on)

        self.table.setItem(row, 1, QTableWidgetItem(r["name"]))  # editable text cells

        every = QSpinBox()                                        # a number box inside a cell
        every.setRange(1, 600)
        every.setSuffix(" min")
        every.setValue(int(r["every"]))
        self.table.setCellWidget(row, 2, every)

        action = QComboBox()                                      # a drop-down inside a cell
        action.addItems(self.gestures)
        action.setCurrentText(r["gesture"])
        self.table.setCellWidget(row, 3, action)

        self.table.setItem(row, 4, QTableWidgetItem(r["message"]))

    def row_to_dict(self, row):
        return {
            "enabled": self.table.item(row, 0).checkState() == Qt.Checked,
            "name": self.table.item(row, 1).text().strip(),
            "every": self.table.cellWidget(row, 2).value(),
            "gesture": self.table.cellWidget(row, 3).currentText(),
            "message": self.table.item(row, 4).text().strip(),
        }

    def delete_selected(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for row in rows:                       # delete from the bottom up so row numbers stay valid
            self.table.removeRow(row)

    def preview_selected(self):
        row = self.table.currentRow()
        if row >= 0:
            self.preview.emit(self.row_to_dict(row))

    def on_save(self):
        reminders = [self.row_to_dict(r) for r in range(self.table.rowCount())]
        settings = {
            "enabled": self.master.isChecked(),
            "test_mode": self.test_mode.isChecked(),
            "snooze_minutes": self.snooze.value(),
            "reminders": [r for r in reminders if r["name"]],     # skip rows with no name
        }
        save_settings(settings)
        self.saved.emit(settings)
        self.close()


# ---------------------------------------------------------------
# 3. BUDDY WITH A TRAY ICON + SETTINGS
# ---------------------------------------------------------------
class TrayBuddy(BubbleBuddy):
    def __init__(self, settings):
        self.settings = settings
        self.paused_until = 0.0
        self.was_active = True
        self.apply_globals()
        super().__init__([to_reminder(d) for d in settings["reminders"]])

        self.icon = self.make_icon()
        self.settings_window = SettingsWindow(
            gestures=[g for g in self.clips if g not in ("walk", "happy")], icon=self.icon)
        self.settings_window.saved.connect(self.apply_settings)
        self.settings_window.preview.connect(lambda d: self.show_now(to_reminder(d)))

        self.tray = QSystemTrayIcon(self.icon)
        self.tray.activated.connect(self.on_tray_click)
        self.build_menu()
        self.tray.show()

    # ---------- tray ----------
    def make_icon(self):
        frame = self.clips["wave"].frames[0]
        size = min(frame.width(), int(frame.height() * 0.45))       # just her face
        face = frame.copy((frame.width() - size) // 2, 0, size, size)
        return QIcon(face)

    def build_menu(self):
        menu = QMenu()
        show_menu = menu.addMenu("Show a reminder now")
        for r in self.reminders:
            show_menu.addAction(r.name, lambda checked=False, rem=r: self.show_now(rem))
        menu.addSeparator()

        self.master_action = QAction("Reminders ON", menu, checkable=True)
        self.master_action.setChecked(self.settings["enabled"])
        self.master_action.toggled.connect(self.set_master)
        menu.addAction(self.master_action)

        menu.addAction("Pause for 1 hour", lambda: self.pause_for(60))
        menu.addAction("Resume now", lambda: self.pause_for(0))
        menu.addSeparator()
        menu.addAction("Settings…", self.open_settings)
        menu.addAction("Quit Buddy", QApplication.quit)
        self.menu = menu                      # keep a reference so Python doesn't delete it
        self.tray.setContextMenu(menu)

    def on_tray_click(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.open_settings()

    def open_settings(self):
        self.settings_window.open_with(self.settings)

    # ---------- on/off switches ----------
    def is_active(self):
        return self.settings["enabled"] and time.time() >= self.paused_until

    def set_master(self, on):
        self.settings["enabled"] = on
        save_settings(self.settings)
        if self.master_action.isChecked() != on:      # keep the tray tick mark in sync
            self.master_action.blockSignals(True)
            self.master_action.setChecked(on)
            self.master_action.blockSignals(False)
        if not on:
            self.queue.clear()                # forget anything waiting

    def pause_for(self, minutes):
        self.paused_until = time.time() + minutes * 60
        if minutes:
            self.queue.clear()
            self.tray.showMessage("Buddy", f"Paused for {minutes} minutes 🤫", self.icon, 3000)

    def show_now(self, reminder):
        """Manual 'show now' works even when reminders are paused or switched off."""
        if reminder not in self.queue:
            self.queue.append(reminder)
        self.start_next()

    # ---------- scheduler: now respects the switches ----------
    def check_due(self):
        active = self.is_active()
        if active and not self.was_active:
            self.reschedule_all()             # coming back from a pause: start fresh, no pile-up
        self.was_active = active
        self.update_tooltip()
        if not active:
            return
        now = time.monotonic()
        for r in self.reminders:
            if r.enabled and now >= r.next_at and r not in self.queue:
                self.queue.append(r)
                r.next_at = float("inf")
        self.start_next()

    def reschedule_all(self):
        now = time.monotonic()
        for r in self.reminders:
            r.next_at = now + self.seconds(r.every)

    def update_tooltip(self):
        if not self.settings["enabled"]:
            text = "Buddy – reminders OFF"
        elif time.time() < self.paused_until:
            text = f"Buddy – paused ({int((self.paused_until - time.time()) / 60) + 1} min left)"
        else:
            upcoming = [r for r in self.reminders if r.enabled and r.next_at != float("inf")]
            if upcoming:
                r = min(upcoming, key=lambda r: r.next_at)
                secs = max(0, int(r.next_at - time.monotonic()))
                when = f"{secs} s" if s3.TEST_MODE else f"{secs // 60 + 1} min"
                text = f"Buddy – next: {r.name} in {when}"
            else:
                text = "Buddy – no reminders on"
        self.tray.setToolTip(text)

    def print_schedule(self):
        now = time.monotonic()
        for r in self.reminders:
            if not r.enabled:
                print(f"   {r.name:<12} (off)")
            elif r.next_at != float("inf"):
                print(f"   {r.name:<12} in {int(r.next_at - now)} s")

    # ---------- live reload after Save ----------
    def apply_globals(self):
        s3.TEST_MODE = self.settings["test_mode"]
        s4.SNOOZE_MINUTES = self.settings["snooze_minutes"]

    def apply_settings(self, new):
        old_by_name = {r.name: r for r in self.reminders}
        test_mode_changed = new["test_mode"] != self.settings["test_mode"]
        self.settings = new
        self.apply_globals()
        self.bubble.set_snooze_minutes(new["snooze_minutes"])
        self.master_action.setChecked(new["enabled"])

        now = time.monotonic()
        fresh = []
        for d in new["reminders"]:
            r = to_reminder(d)
            old = old_by_name.get(r.name)
            unchanged = old and old.every == r.every and old.enabled == r.enabled and not test_mode_changed
            # keep the countdown of reminders you didn't touch; restart the ones you changed
            r.next_at = old.next_at if unchanged and old.next_at != float("inf") else now + self.seconds(r.every)
            fresh.append(r)
        self.reminders = fresh
        self.queue.clear()
        self.build_menu()                     # menu lists the new reminder names
        print("Settings saved. Schedule:")
        self.print_schedule()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)      # closing Settings must not quit Buddy
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("No system tray found – the tray icon won't show.")
    buddy = TrayBuddy(load_settings())
    print(f"Buddy is running. Settings file: {SETTINGS_FILE}")
    sys.exit(app.exec())
