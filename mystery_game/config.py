from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
ASSETS_DIR = ROOT_DIR / "assets"
SOUNDS_DIR = ASSETS_DIR / "sounds"
SAVES_DIR = ROOT_DIR / "saves"
INVESTIGATIONS_FILE = DATA_DIR / "investigations.json"
WINDOW_SIZE = "1000x700"
APP_TITLE = "ANASTASIA DAYS — MYSTERY GAME"
