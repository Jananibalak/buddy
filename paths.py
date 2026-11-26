"""
Where Kutty keeps its files.

Running as a script (py step6_characters.py): the folder of the .py files.
Running as Kutty.exe (PyInstaller):          the folder that contains Kutty.exe.

Why it matters: inside an .exe, __file__ points to a hidden internal folder,
but settings.json and characters/ must live next to Kutty.exe so you can see and edit them.
"""
import sys
from pathlib import Path


def app_dir() -> Path:
    if getattr(sys, "frozen", False):          # PyInstaller sets sys.frozen = True
        return Path(sys.executable).parent
    return Path(__file__).parent
