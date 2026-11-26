"""
STEP 7 – The real app: Kutty.exe

This is the file PyInstaller turns into Kutty.exe (see build.bat). It adds:
  • only one Kutty at a time   -> a lock file; starting a second copy just says "already running"
  • "Start with Windows"        -> a tray menu tick that adds/removes Kutty from Windows startup
  • real-use defaults           -> a brand-new settings.json starts with test mode OFF

Run as a script:  py kutty.py          (same as step6, plus the extras above)
Build the .exe:   double-click build.bat
"""
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QLockFile
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

import step5_settings as s5
from step6_characters import CharacterKutty
from paths import app_dir

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"   # per-user startup list in the registry
APP_NAME = "Kutty"


# ---------------------------------------------------------------
# Start with Windows: one entry in HKEY_CURRENT_USER\...\Run
# (no admin rights needed; you can also see/remove it in Task Manager → Startup apps)
# ---------------------------------------------------------------
def startup_command():
    if getattr(sys, "frozen", False):                           # running as Kutty.exe
        return f'"{sys.executable}"'
    pythonw = Path(sys.executable).with_name("pythonw.exe")     # pythonw = no console window
    return f'"{pythonw}" "{Path(__file__).resolve()}"'


def startup_enabled():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except (OSError, ImportError):
        return False


def set_startup(on):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            if on:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, startup_command())
            else:
                winreg.DeleteValue(key, APP_NAME)
    except FileNotFoundError:
        pass                                                    # already removed
    except (OSError, ImportError) as e:
        print(f"Couldn't change startup setting: {e}")


class AppKutty(CharacterKutty):
    def build_menu(self):
        """Step 5's tray menu + a 'Start with Windows' tick, placed just above 'Settings…'."""
        super().build_menu()
        start = QAction("Start with Windows", self.menu, checkable=True)
        start.setChecked(startup_enabled())
        start.toggled.connect(set_startup)
        settings_action = next(a for a in self.menu.actions() if a.text().startswith("Settings"))
        self.menu.insertAction(settings_action, start)
        self.menu.insertSeparator(settings_action)


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    # only one Kutty: the first one holds a lock file; others see it and quit
    lock = QLockFile(str(Path(tempfile.gettempdir()) / "kutty.lock"))
    if not lock.tryLock(100):
        QMessageBox.information(None, APP_NAME, "Kutty is already running – look for her face near the clock. 🧸")
        return 0

    if not s5.SETTINGS_FILE.exists():                           # first run of the real app
        s5.DEFAULT_SETTINGS["test_mode"] = False

    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("No system tray found – the tray icon won't show.")
    kutty = AppKutty(s5.load_settings())
    app.setWindowIcon(kutty.icon)
    print(f"Kutty is running from {app_dir()}")
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
