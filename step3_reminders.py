"""
STEP 3 – The scheduler: she stays hidden and only walks out when a reminder is due

What you learn here:
  • inheritance   -> reuse ALL of Step 2's walking code, change only what's different
  • a dataclass   -> a tidy way to describe one reminder
  • a scheduler   -> a slow timer that checks "is anything due?"
  • a queue       -> if two reminders are due together, she does them one after another

Run:   py step3_reminders.py
In TEST_MODE, 1 "minute" = 3 seconds, so you'll see her within a minute.
Quit:  right-click on her while she's visible, or close the PowerShell window (Ctrl+C there may not stop Qt)
"""
import sys
import time
from collections import deque
from dataclasses import dataclass, field

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from step2_walk import Buddy          # everything from Step 2: clips, game loop, walk_to ...

# ---------------------------------------------------------------
# Settings
# ---------------------------------------------------------------
TEST_MODE = True            # True: 1 minute = 3 seconds (for testing). Set False for real use.
ACTION_SECONDS = 8          # how long she does her action before walking away (Step 4 waits for your click)


@dataclass(eq=False)        # eq=False: compare reminders by identity, not by their values
class Reminder:
    name: str
    every: int              # minutes between reminders
    gesture: str            # which clip she plays: drink, stretch, eyes, wave
    message: str
    next_at: float = field(default=0.0)   # filled in by the scheduler


REMINDERS = [
    Reminder("Drink water", 45, "drink",   "Sip sip! Time for a glass of water 💧"),
    Reminder("Rest eyes",   20, "eyes",    "20-20-20! Look at something far away for 20 seconds 👀"),
    Reminder("Posture",     30, "wave",    "Shoulders back, sit up tall! 💪"),
    Reminder("Stretch",     60, "stretch", "Stand up and stretch those arms high! 🙆"),
]


class ReminderBuddy(Buddy):
    """Step 2's Buddy, but visits are driven by reminders instead of a 5-second loop."""

    def __init__(self, reminders):
        super().__init__()                         # run Step 2's setup first
        self.reminders = reminders
        self.queue = deque()
        self.busy = False
        self.current = None

        now = time.monotonic()
        for r in self.reminders:
            r.next_at = now + self.seconds(r.every)

        # The scheduler: much slower than the game loop – checking once a second is plenty
        self.scheduler = QTimer(self)
        self.scheduler.timeout.connect(self.check_due)
        self.scheduler.start(1000)

        self.print_schedule()

    # ---------- time helpers ----------
    @staticmethod
    def seconds(minutes):
        return minutes * 3 if TEST_MODE else minutes * 60

    def print_schedule(self):
        now = time.monotonic()
        for r in self.reminders:
            if r.next_at != float("inf"):
                print(f"   {r.name:<12} in {int(r.next_at - now)} s")

    # ---------- the scheduler ----------
    def check_due(self):
        now = time.monotonic()
        for r in self.reminders:
            if now >= r.next_at and r not in self.queue:
                self.queue.append(r)
                r.next_at = float("inf")          # "waiting in the queue" – reset after the visit
        self.start_next()

    def start_next(self):
        if self.busy or not self.queue:
            return                                # she's already out, or nothing to do
        self.current = self.queue.popleft()
        self.busy = True
        print(f"[{time.strftime('%H:%M:%S')}] {self.current.message}")
        self.visit()                              # Step 2: walk in ... then calls say_hi()

    # ---------- overriding Step 2's visit steps ----------
    def say_hi(self):
        """Arrived: instead of always waving, do this reminder's action."""
        self.facing_left = False
        self.play(self.current.gesture)
        QTimer.singleShot(ACTION_SECONDS * 1000, self.leave)

    def gone(self):
        """Walked out: instead of looping, schedule this reminder's next time."""
        self.hide()
        self.timer.stop()
        self.current.next_at = time.monotonic() + self.seconds(self.current.every)
        self.current = None
        self.busy = False
        print("Next up:")
        self.print_schedule()
        self.start_next()                         # another one already waiting? go again


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)          # she is hidden most of the time – keep running
    buddy = ReminderBuddy(REMINDERS)
    print("Buddy is running. She'll appear when a reminder is due.")
    sys.exit(app.exec())
