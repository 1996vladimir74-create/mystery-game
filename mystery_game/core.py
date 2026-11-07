import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from uuid import uuid4


class DataError(Exception):
    """Raised when an investigation file is invalid."""


class SaveError(Exception):
    """Raised when a save or settings file cannot be read or written."""


def normalize_answer(value):
    """Normalize user input while ignoring case, whitespace and punctuation."""
    value = unicodedata.normalize("NFKC", str(value or "")).casefold().replace("ё", "е")
    return "".join(ch for ch in value if ch.isalnum())


class DataManager:
    def __init__(self, path):
        self.path = Path(path)

    @staticmethod
    def validate_case(case):
        if not isinstance(case, dict):
            raise DataError("Каждое расследование должно быть JSON-объектом.")
        if not isinstance(case.get("id"), str) or not case["id"].strip():
            raise DataError("У каждого дела должен быть непустой строковый id.")
        if not isinstance(case.get("title"), str) or not case["title"].strip():
            raise DataError(f"У дела «{case.get('id', '?')}» должно быть название.")
        for field in ("cover_image", "background_image", "document_image"):
            if field in case and case[field] is not None and not isinstance(case[field], str):
                raise DataError(f"Поле {field} должно быть строкой с относительным путём к изображению.")
        clues = case.get("clues")
        if not isinstance(clues, list) or not clues:
            raise DataError(f"В деле «{case['title']}» должен быть непустой список улик.")
        for i, clue in enumerate(clues, 1):
            if not isinstance(clue, dict):
                raise DataError(f"Улика №{i} должна быть объектом.")
            if not isinstance(clue.get("task"), str) or not clue["task"].strip():
                raise DataError(f"Улика №{i}: поле task должно содержать текст.")
            answers = clue.get("answers")
            if (not isinstance(answers, list) or not answers
                    or any(not isinstance(x, str) or not x.strip() or not normalize_answer(x) for x in answers)):
                raise DataError(f"Улика №{i}: answers должен быть непустым списком строк.")
            for field in ("background_image", "illustration_image", "document_image", "item_image"):
                if field in clue and clue[field] is not None and not isinstance(clue[field], str):
                    raise DataError(f"Улика №{i}: поле {field} должно быть строкой с относительным путём к изображению.")
            hints = clue.get("hints", [])
            if not isinstance(hints, list) or any(not isinstance(x, str) for x in hints):
                raise DataError(f"Улика №{i}: hints должен быть списком строк.")
        if "final_letter" in case and not isinstance(case["final_letter"], str):
            raise DataError("final_letter должен быть текстом.")

    @classmethod
    def validate_cases(cls, cases):
        if not isinstance(cases, list) or not cases:
            raise DataError("Ожидается непустой список расследований.")
        ids = []
        for case in cases:
            cls.validate_case(case)
            ids.append(case["id"])
        if len(ids) != len(set(ids)):
            raise DataError("ID расследований должны быть уникальными.")

    def load_cases(self):
        try:
            cases = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DataError(f"Не удалось прочитать расследования: {exc}") from exc
        self.validate_cases(cases)
        return cases

    def save_cases(self, cases):
        self.validate_cases(cases)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise DataError(f"Не удалось сохранить расследования: {exc}") from exc


class SaveManager:
    DEFAULT_SETTINGS = {
        "sound_enabled": True, "music_enabled": True, "music_volume": 0.35,
        "animations": True, "font_scale": 1.0, "difficulty": "normal"
    }
    VALID_DIFFICULTIES = {"easy", "normal", "hard"}

    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, slot_id):
        if not isinstance(slot_id, str) or not re.fullmatch(r"[a-fA-F0-9_-]{1,64}", slot_id):
            raise SaveError("Некорректный идентификатор сохранения.")
        return self.directory / f"{slot_id}.json"

    @staticmethod
    def _atomic_write(path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(path)
        except (OSError, TypeError, ValueError) as exc:
            tmp.unlink(missing_ok=True)
            raise SaveError(f"Не удалось записать файл: {exc}") from exc

    def create(self, name, case_id):
        if not isinstance(name, str) or not name.strip():
            raise SaveError("Название сохранения не может быть пустым.")
        if not isinstance(case_id, str) or not case_id.strip():
            raise SaveError("Не указан идентификатор расследования.")
        now = datetime.now().isoformat(timespec="seconds")
        save = {
            "id": uuid4().hex[:12], "name": name.strip(), "case_id": case_id,
            "current_clue": 0, "inventory": [], "completed": False,
            "created_at": now, "updated_at": now, "hints_used": 0
        }
        self.save(save)
        return save

    def save(self, save):
        if not isinstance(save, dict) or not save.get("id"):
            raise SaveError("Сохранение имеет неверный формат.")
        data = dict(save)
        data["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._atomic_write(self._path(data["id"]), data)
        save["updated_at"] = data["updated_at"]

    def load(self, slot_id):
        try:
            data = json.loads(self._path(slot_id).read_text(encoding="utf-8"))
            required = {"id", "name", "case_id", "current_clue", "inventory", "completed"}
            if not isinstance(data, dict) or not required.issubset(data):
                raise ValueError("Неполный формат сохранения.")
            if data["id"] != slot_id or not isinstance(data["name"], str) or not data["name"].strip():
                raise ValueError("Некорректные метаданные сохранения.")
            if not isinstance(data["case_id"], str):
                raise ValueError("Некорректный ID расследования.")
            if type(data["current_clue"]) is not int or data["current_clue"] < 0:
                raise ValueError("Некорректный номер текущей улики.")
            if not isinstance(data["inventory"], list) or type(data["completed"]) is not bool:
                raise ValueError("Некорректный инвентарь или статус сохранения.")
            if type(data.get("hints_used", 0)) is not int or data.get("hints_used", 0) < 0:
                raise ValueError("Некорректное число использованных подсказок.")
            return data
        except (OSError, ValueError, TypeError, json.JSONDecodeError, SaveError) as exc:
            raise SaveError(f"Не удалось загрузить сохранение: {exc}") from exc

    def list_saves(self):
        result = []
        for path in self.directory.glob("*.json"):
            if path.name == "settings.json":
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                required = {"id", "name", "case_id", "current_clue", "completed"}
                if isinstance(data, dict) and required.issubset(data) and data["id"] == path.stem:
                    result.append(data)
            except (OSError, ValueError, TypeError):
                continue
        return sorted(result, key=lambda x: x.get("updated_at", ""), reverse=True)

    def delete(self, slot_id):
        """Delete one save slot by its validated identifier."""
        path = self._path(slot_id)
        try:
            path.unlink()
        except FileNotFoundError as exc:
            raise SaveError("Это сохранение уже удалено.") from exc
        except OSError as exc:
            raise SaveError(f"Не удалось удалить сохранение: {exc}") from exc

    def latest_incomplete(self):
        return next((x for x in self.list_saves() if not x.get("completed")), None)

    def completed_cases(self):
        unique = {}
        for item in self.list_saves():
            if not item.get("completed"):
                continue
            ids = item.get("completed_case_ids") or [item["case_id"]]
            titles = item.get("completed_case_titles") or {}
            for case_id in ids:
                unique[case_id] = {
                    "case_id": case_id,
                    "name": titles.get(case_id, item.get("case_title", item["name"])),
                    "completed_at": item.get("completed_at", item.get("updated_at", ""))
                }
        return sorted(unique.values(), key=lambda x: x["completed_at"], reverse=True)

    @classmethod
    def sanitize_settings(cls, settings):
        result = dict(cls.DEFAULT_SETTINGS)
        if isinstance(settings, dict):
            for key in ("sound_enabled", "music_enabled", "animations"):
                if isinstance(settings.get(key), bool):
                    result[key] = settings[key]
            try:
                result["music_volume"] = min(1.0, max(0.0, float(settings.get("music_volume", result["music_volume"]))))
            except (TypeError, ValueError):
                pass
            try:
                result["font_scale"] = min(1.4, max(0.8, float(settings.get("font_scale", result["font_scale"]))))
            except (TypeError, ValueError):
                pass
            if settings.get("difficulty") in cls.VALID_DIFFICULTIES:
                result["difficulty"] = settings["difficulty"]
        return result

    def load_settings(self):
        try:
            data = json.loads((self.directory / "settings.json").read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            data = {}
        return self.sanitize_settings(data)

    def save_settings(self, settings):
        self._atomic_write(self.directory / "settings.json", self.sanitize_settings(settings))


class AudioManager:
    """Optional pygame mixer wrapper; the game remains playable without audio support."""
    def __init__(self, folder, settings):
        self.folder, self.settings, self.pg = Path(folder), settings, None
        try:
            import pygame
            pygame.mixer.init()
            self.pg = pygame
        except Exception:
            self.pg = None

    def apply(self, settings):
        self.settings = settings
        if self.pg and self.pg.mixer.get_init():
            try:
                self.pg.mixer.music.set_volume(float(settings.get("music_volume", 0.35)))
            except Exception:
                pass

    def music(self):
        path = self.folder / "music.ogg"
        if self.pg and self.settings.get("music_enabled") and path.exists():
            try:
                self.pg.mixer.music.load(str(path))
                self.pg.mixer.music.set_volume(float(self.settings.get("music_volume", 0.35)))
                self.pg.mixer.music.play(-1)
            except Exception:
                pass

    def stop(self):
        if self.pg:
            try:
                self.pg.mixer.music.stop()
            except Exception:
                pass

    def effect(self, name):
        path = self.folder / name
        if self.pg and self.settings.get("sound_enabled") and path.exists():
            try:
                self.pg.mixer.Sound(str(path)).play()
            except Exception:
                pass

    def close(self):
        self.stop()
        if self.pg:
            try:
                self.pg.mixer.quit()
            except Exception:
                pass