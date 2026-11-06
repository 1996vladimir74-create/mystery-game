import os
import sys
from pathlib import Path

# PyInstaller unpacks resources into _MEIPASS; user saves must stay outside it.
ROOT_DIR = Path(__file__).resolve().parent.parent
IS_FROZEN = bool(getattr(sys, "frozen", False))
RESOURCE_DIR = Path(getattr(sys, "_MEIPASS", ROOT_DIR))

if IS_FROZEN:
    USER_DATA_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "AnastasiaDaysMysteryGame"
    DATA_DIR = RESOURCE_DIR / "data"
    SAVES_DIR = USER_DATA_DIR / "saves"
    INVESTIGATIONS_FILE = USER_DATA_DIR / "investigations.json"
else:
    USER_DATA_DIR = ROOT_DIR
    DATA_DIR = ROOT_DIR / "data"
    SAVES_DIR = ROOT_DIR / "saves"
    INVESTIGATIONS_FILE = DATA_DIR / "investigations.json"

ASSETS_DIR = RESOURCE_DIR / "assets"
THEME_FILE = ASSETS_DIR / "theme.json"
SOUNDS_DIR = ASSETS_DIR / "sounds"
BUNDLED_INVESTIGATIONS_FILE = DATA_DIR / "investigations.json"
WINDOW_SIZE = "1000x700"
APP_TITLE = "ANASTASIA DAYS — MYSTERY GAME"
