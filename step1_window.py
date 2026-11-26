"""
STEP 1 – Show Kutty on the desktop (a still picture, no animation yet)

What you learn here:
  • a frameless window        -> no title bar, no borders
  • a transparent background  -> only her pixels are visible
  • always-on-top             -> she floats above every other app
  • positioning on the screen -> bottom-right corner, just above the taskbar

Run:   py step1_window.py
Quit:  right-click on her (or press Esc while she is selected)
"""
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QLabel

ASSETS = Path(__file__).parent / "assets"


class Kutty(QLabel):
    def __init__(self):
        super().__init__()

        # 1) Window behaviour: no frame, always on top, no taskbar button ("Tool" window)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )

        # 2) See-through background: transparent pixels of the PNG show the desktop behind
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 3) Load the wave strip and cut out just the FIRST frame
        strip = QPixmap(str(ASSETS / "wave.png"))
        frame_width = 128                      # from assets/clips.json
        first_frame = strip.copy(0, 0, frame_width, strip.height())
        self.setPixmap(first_frame)
        self.resize(first_frame.size())

        # 4) Put her in the bottom-right corner of the usable screen (above the taskbar)
        area = QApplication.primaryScreen().availableGeometry()
        self.move(area.right() - self.width() - 150,
                  area.bottom() - self.height())

    # Right-click on her -> close the app
    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            QApplication.quit()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            QApplication.quit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    kutty = Kutty()
    kutty.show()
    sys.exit(app.exec())
