import json, re
from datetime import datetime
from pathlib import Path
from uuid import uuid4

class DataError(Exception): pass
class SaveError(Exception): pass

def normalize_answer(value):
    value = (value or "").casefold().replace("ё", "е")
    return "".join(ch for ch in value if ch.isalnum())

class DataManager:
    def __init__(self, path): self.path = Path(path)
    @staticmethod
    def validate_case(case):
        if not isinstance(case, dict) or not case.get("id") or not case.get("title"):
            raise DataError("У каждого дела должны быть id и title.")
        clues = case.get("clues")
        if not isinstance(clues, list) or not clues:
            raise DataError(f"В деле «{case.get('title', '?')}» нет улик.")
        for i, clue in enumerate(clues, 1):
            if not clue.get("task") or not clue.get("answers"):
                raise DataError(f"Улика №{i}: нужны task и непустой список answers.")
    def load_cases(self):
        try: cases = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc: raise DataError(str(exc)) from exc
        if not isinstance(cases, list) or not cases: raise DataError("Список расследований пуст.")
        for case in cases: self.validate_case(case)
        return cases
    def save_cases(self, cases):
        if not isinstance(cases, list) or not cases: raise DataError("Ожидается непустой список дел.")
        ids = [c.get("id") for c in cases]
        if len(ids) != len(set(ids)): raise DataError("ID расследований должны быть уникальными.")
        for case in cases: self.validate_case(case)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError as exc:
            tmp.unlink(missing_ok=True); raise DataError(str(exc)) from exc

class SaveManager:
    def __init__(self, directory):
        self.directory = Path(directory); self.directory.mkdir(parents=True, exist_ok=True)
    def _path(self, slot_id):
        safe = re.sub(r"[^a-zA-Z0-9_-]", "_", slot_id)
        return self.directory / f"{safe}.json"
    @staticmethod
    def _atomic_write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True); tmp = path.with_suffix(".tmp")
        try:
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(path)
        except OSError as exc:
            tmp.unlink(missing_ok=True); raise SaveError(str(exc)) from exc
    def create(self, name, case_id):
        now = datetime.now().isoformat(timespec="seconds")
        save = {"id": uuid4().hex[:12], "name": name.strip(), "case_id": case_id,
                "current_clue": 0, "inventory": [], "completed": False,
                "created_at": now, "updated_at": now, "hints_used": 0}
        self.save(save); return save
    def save(self, save):
        data = dict(save); data["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._atomic_write(self._path(data["id"]), data); save["updated_at"] = data["updated_at"]
    def load(self, slot_id):
        try:
            data = json.loads(self._path(slot_id).read_text(encoding="utf-8"))
            required = {"id", "name", "case_id", "current_clue", "inventory", "completed"}
            if not required.issubset(data): raise ValueError("Неполный формат сохранения")
            return data
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise SaveError(f"Не удалось загрузить сохранение: {exc}") from exc
    def list_saves(self):
        result = []
        for path in self.directory.glob("*.json"):
            if path.name == "settings.json": continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if {"id", "name", "case_id", "current_clue", "completed"}.issubset(data): result.append(data)
            except (OSError, ValueError, TypeError): continue
        return sorted(result, key=lambda x: x.get("updated_at", ""), reverse=True)
    def latest_incomplete(self):
        return next((x for x in self.list_saves() if not x.get("completed")), None)
    def completed_cases(self):
        unique = {}
        for x in self.list_saves():
            if x.get("completed"):
                unique[x["case_id"]] = {"case_id": x["case_id"], "name": x.get("case_title", x["name"]),
                                        "completed_at": x.get("completed_at", x.get("updated_at", ""))}
        return sorted(unique.values(), key=lambda x: x["completed_at"], reverse=True)
    def load_settings(self):
        defaults = {"sound_enabled": True, "music_enabled": True, "music_volume": .35,
                    "animations": True, "font_scale": 1.0, "difficulty": "normal"}
        try:
            data = json.loads((self.directory / "settings.json").read_text(encoding="utf-8"))
            if isinstance(data, dict): defaults.update(data)
        except (OSError, ValueError, TypeError): pass
        return defaults
    def save_settings(self, settings): self._atomic_write(self.directory / "settings.json", settings)

class AudioManager:
    def __init__(self, folder, settings):
        self.folder, self.settings, self.pg = Path(folder), settings, None
        try:
            import pygame
            pygame.mixer.init(); self.pg = pygame
        except Exception: pass
    def apply(self, settings):
        self.settings = settings
        if self.pg and self.pg.mixer.get_init():
            self.pg.mixer.music.set_volume(float(settings.get("music_volume", .35)))
    def music(self):
        path = self.folder / "music.ogg"
        if self.pg and self.settings.get("music_enabled") and path.exists():
            try:
                self.pg.mixer.music.load(str(path)); self.pg.mixer.music.set_volume(float(self.settings.get("music_volume", .35)))
                self.pg.mixer.music.play(-1)
            except Exception: pass
    def stop(self):
        if self.pg:
            try: self.pg.mixer.music.stop()
            except Exception: pass
    def effect(self, name):
        path = self.folder / name
        if self.pg and self.settings.get("sound_enabled") and path.exists():
            try: self.pg.mixer.Sound(str(path)).play()
            except Exception: pass
    def close(self):
        self.stop()
        if self.pg:
            try: self.pg.mixer.quit()
            except Exception: pass
