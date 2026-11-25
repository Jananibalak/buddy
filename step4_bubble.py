"""
STEP 4 – Speech bubble with Done / Snooze, and a happy dance

What you learn here:
  • custom painting  -> draw the bubble shape yourself (rounded box + little tail) with QPainter
  • signals & slots  -> the bubble "announces" a click; Buddy "listens" and reacts
  • not stealing focus -> the bubble appears without interrupting your typing
  • animations       -> the heart floats up and fades with QPropertyAnimation
  • waiting without freezing -> she waits for your click, with a timeout

Run:   py step4_bubble.py      (TEST_MODE from Step 3 still applies: 1 minute = 3 seconds)
"""
import sys
import time

from PySide6.QtCore import (Qt, QTimer, Signal, QPoint, QPropertyAnimation,
                            QParallelAnimationGroup, QEasingCurve, QRectF)
from PySide6.QtGui import QPainter, QPainterPath, QColor, QPolygonF, QFont, QPen
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout

from step3_reminders import ReminderBuddy, REMINDERS

SNOOZE_MINUTES = 5
AUTO_DISMISS_SECONDS = 90     # no answer in 90 s -> treat as snooze

# Window flags shared by the bubble and the heart: floating, on top, never takes keyboard focus
OVERLAY_FLAGS = (Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                 | Qt.WindowDoesNotAcceptFocus)


def ding():
    """A soft Windows notification sound (silently skipped on other systems)."""
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        pass


# ---------------------------------------------------------------
# The speech bubble – its own little transparent window
# Several looks ("styles"); choose one in Settings (Step 6) or change BUBBLE_STYLE here.
# ---------------------------------------------------------------
BUBBLE_STYLES = {
    #            width: None = shrink to fit   fill/border: (R, G, B, alpha 0–255)
    "cute":    dict(width=210, fill=(255, 236, 243, 235), border=(255, 184, 204, 255), text="#7A3E55",
                    font=9.5, radius=18, tail="dots", buttons="icons", layout="stack"),
    "mini":    dict(width=None, fill=(255, 255, 255, 228), border=(222, 228, 244, 255), text="#2B2F45",
                    font=9, radius=15, tail="triangle", buttons="icons", layout="row"),
    "glass":   dict(width=210, fill=(255, 255, 255, 140), border=(255, 255, 255, 230), text="#1E2340",
                    font=9.5, radius=16, tail="triangle", buttons="icons", layout="stack"),
    "classic": dict(width=300, fill=(255, 255, 255, 255), border=None, text="#2B2F45",
                    font=11, radius=16, tail="triangle", buttons="text", layout="stack"),
}
BUBBLE_STYLE = "cute"


class SpeechBubble(QWidget):
    done = Signal()       # signals: "something happened" announcements
    snooze = Signal()

    TAIL = 16             # space under the bubble for the tail
    SHADOW = 4
    TAIL_X = 60           # tail position, measured from the bubble's right edge

    def __init__(self, style=None):
        super().__init__()
        self.style_name = style or BUBBLE_STYLE
        st = self.st = BUBBLE_STYLES.get(self.style_name, BUBBLE_STYLES["cute"])
        self.setWindowFlags(OVERLAY_FLAGS)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        if st["width"]:
            self.setFixedWidth(st["width"])

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setFont(QFont("Segoe UI", st["font"]))
        self.label.setStyleSheet(f"color: {st['text']}; background: transparent;")
        if st["layout"] == "row":
            self.label.setMaximumWidth(190)

        # --- buttons: round icons (cute) or text pills (classic) ---
        if st["buttons"] == "icons":
            self.done_btn = self.round_button("✓", "#7BD8A0", "#62C98A", "white", "Done")
            self.snooze_btn = self.round_button("💤", "#E9E4FB", "#DAD3F7", "#5B4B9A", "")
        else:
            pill = "QPushButton {{ background:{bg}; color:{fg}; border:none; border-radius:8px;" \
                   " padding:6px 12px; font: 10pt 'Segoe UI'; }} QPushButton:hover {{ background:{hover}; }}"
            self.done_btn = QPushButton("Done ✓")
            self.snooze_btn = QPushButton("")
            self.done_btn.setStyleSheet(pill.format(bg="#5CC98B", fg="white", hover="#4AB879"))
            self.snooze_btn.setStyleSheet(pill.format(bg="#F0F2F7", fg="#444455", hover="#E2E6F0"))
        for b in (self.done_btn, self.snooze_btn):
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
        self.set_snooze_minutes(SNOOZE_MINUTES)

        # clicking a button emits our signal
        self.done_btn.clicked.connect(self.done.emit)
        self.snooze_btn.clicked.connect(self.snooze.emit)

        pad_x, pad_y = (10, 7) if st["layout"] == "row" else (12, 9)
        if st["layout"] == "row":                       # text and buttons side by side
            layout = QHBoxLayout(self)
            layout.addWidget(self.label, 1)
            layout.addWidget(self.done_btn)
            layout.addWidget(self.snooze_btn)
        else:                                           # text on top, buttons underneath
            layout = QVBoxLayout(self)
            buttons = QHBoxLayout()
            if st["buttons"] == "icons":
                buttons.addStretch()                    # round icons sit on the right
            buttons.addWidget(self.done_btn)
            buttons.addWidget(self.snooze_btn)
            if st["buttons"] != "icons":
                buttons.addStretch()                    # text pills sit on the left
            layout.addWidget(self.label)
            layout.addLayout(buttons)
        layout.setSpacing(6)
        # leave room around the content for the shadow and the tail
        layout.setContentsMargins(pad_x + self.SHADOW, pad_y + self.SHADOW,
                                  pad_x + self.SHADOW, pad_y + self.SHADOW + self.TAIL)

        self.fade = QPropertyAnimation(self, b"windowOpacity")
        self.fade.setDuration(250)

    @staticmethod
    def round_button(text, bg, hover, fg, tip):
        b = QPushButton(text)
        b.setFixedSize(28, 28)
        b.setToolTip(tip)
        b.setStyleSheet(f"QPushButton {{ background:{bg}; color:{fg}; border:none; border-radius:14px;"
                        f" font: bold 11pt 'Segoe UI'; }} QPushButton:hover {{ background:{hover}; }}")
        return b

    def set_snooze_minutes(self, minutes):
        if self.st["buttons"] == "icons":
            self.snooze_btn.setToolTip(f"Snooze {minutes} min")
        else:
            self.snooze_btn.setText(f"Snooze {minutes} min")

    def show_message(self, text, tail_tip_x, tail_tip_y):
        """Show the bubble so the tip of its tail points at (tail_tip_x, tail_tip_y)."""
        self.label.setText(text)
        self.adjustSize()                                   # grow/shrink to fit the text
        self.move(tail_tip_x - (self.width() - self.TAIL_X), tail_tip_y - self.height())
        self.setWindowOpacity(0.0)
        self.show()
        self.fade.setStartValue(0.0)
        self.fade.setEndValue(1.0)
        self.fade.start()

    def paintEvent(self, event):
        """Draw the bubble: rounded box + tail (triangle or 'thought' dots), soft shadow, optional border."""
        st = self.st
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        s, t = self.SHADOW, self.TAIL
        box = QRectF(s, s, self.width() - 2 * s, self.height() - 2 * s - t)
        tip_x = self.width() - self.TAIL_X

        shape = QPainterPath()
        shape.addRoundedRect(box, st["radius"], st["radius"])
        if st["tail"] == "triangle":
            tail = QPainterPath()
            tail.addPolygon(QPolygonF([QPoint(tip_x - 12, int(box.bottom()) - 1),
                                       QPoint(tip_x, int(box.bottom()) + t - 2),
                                       QPoint(tip_x + 2, int(box.bottom()) - 1)]))
            shape = shape.united(tail)
        else:                                               # "thought bubble": two little circles
            shape.addEllipse(QRectF(tip_x - 13, box.bottom() + 3, 9, 9))
            shape.addEllipse(QRectF(tip_x - 4, box.bottom() + 11, 5, 5))

        p.setPen(Qt.NoPen)
        for i, alpha in enumerate((14, 9, 6)):              # 3 faint layers = soft shadow
            p.setBrush(QColor(20, 30, 70, alpha))
            p.drawPath(shape.translated(0, 1.5 + i))
        p.setBrush(QColor(*st["fill"]))
        if st["border"]:
            p.setPen(QPen(QColor(*st["border"]), 1.6))
        p.drawPath(shape)


# ---------------------------------------------------------------
# A heart that floats up and fades away
# ---------------------------------------------------------------
class Heart(QLabel):
    def __init__(self):
        super().__init__("♥")
        self.setWindowFlags(OVERLAY_FLAGS)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setStyleSheet("color:#FF6F91; font-size:34px;")
        self.adjustSize()

        self.rise = QPropertyAnimation(self, b"pos")
        self.rise.setDuration(1400)
        self.rise.setEasingCurve(QEasingCurve.OutCubic)
        self.fade = QPropertyAnimation(self, b"windowOpacity")
        self.fade.setDuration(1400)
        self.fade.setKeyValueAt(0.0, 0.0)
        self.fade.setKeyValueAt(0.25, 1.0)
        self.fade.setKeyValueAt(1.0, 0.0)
        self.group = QParallelAnimationGroup()      # run both animations together
        self.group.addAnimation(self.rise)
        self.group.addAnimation(self.fade)
        self.group.finished.connect(self.hide)

    def float_up(self, x, y):
        self.rise.setStartValue(QPoint(x, y))
        self.rise.setEndValue(QPoint(x, y - 90))
        self.move(x, y)
        self.show()
        self.group.start()


# ---------------------------------------------------------------
# Buddy with a bubble: Step 3 + "ask and wait for an answer"
# ---------------------------------------------------------------
class BubbleBuddy(ReminderBuddy):
    def __init__(self, reminders):
        super().__init__(reminders)
        self.bubble = SpeechBubble()
        self.heart = Heart()
        self.asking = False
        self.next_delay = None          # minutes until this reminder comes back

        # slots: connect the bubble's signals to Buddy's reaction
        self.bubble.done.connect(lambda: self.answer("done"))
        self.bubble.snooze.connect(lambda: self.answer("snooze"))

        # if nobody answers, give up after a while (counts as snooze)
        self.no_answer = QTimer(self)
        self.no_answer.setSingleShot(True)
        self.no_answer.timeout.connect(lambda: self.answer("timeout"))

    def say_hi(self):
        """Arrived: do the action, show the bubble, and WAIT (no fixed timer any more)."""
        self.facing_left = False
        self.play(self.current.gesture)
        ding()
        # tail points at her head: a bit right of her centre, near the top of her window
        self.bubble.show_message(self.current.message,
                                 tail_tip_x=round(self.x) + self.width() // 2 + 10,
                                 tail_tip_y=self.y_pos + 8)
        self.asking = True
        self.no_answer.start(AUTO_DISMISS_SECONDS * 1000)

    def answer(self, how):
        if not self.asking:             # ignore double clicks
            return
        self.asking = False
        self.no_answer.stop()
        self.bubble.hide()
        print(f"   -> {how}")

        if how == "done":
            self.next_delay = self.current.every
            self.play("happy")
            self.heart.float_up(round(self.x) + self.width() // 2 - self.heart.width() // 2, self.y_pos)
            QTimer.singleShot(2000, self.leave)         # dance for 2 s, then walk off
        else:
            self.next_delay = SNOOZE_MINUTES
            self.leave()

    def gone(self):
        """Walked out: schedule the next time based on your answer."""
        self.hide()
        self.timer.stop()
        self.current.next_at = time.monotonic() + self.seconds(self.next_delay)
        self.current = None
        self.busy = False
        print("Next up:")
        self.print_schedule()
        self.start_next()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    buddy = BubbleBuddy(REMINDERS)
    print("Buddy is running. She'll appear when a reminder is due.")
    sys.exit(app.exec())
