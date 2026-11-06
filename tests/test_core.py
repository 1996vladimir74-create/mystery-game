import json
import tempfile
import unittest
from pathlib import Path

from mystery_game.core import DataError, DataManager, SaveError, SaveManager, normalize_answer
from mystery_game.images import ImageAssets
from mystery_game.data import DLCManager

VALID_CASE = {
    "id": "case-one", "title": "Тестовое дело",
    "clues": [{"task": "Найди ключ", "answers": ["ключ", "ключик"],
               "hints": ["Подсказка"], "icon": "🔑", "item_name": "Ключ"}]
}


class NormalizeAnswerTests(unittest.TestCase):
    def test_ignores_case_spaces_punctuation_and_yo(self):
        self.assertEqual(normalize_answer("  ЁЛКА, КЛЮЧ! "), "елкаключ")

    def test_empty_input_is_empty(self):
        self.assertEqual(normalize_answer(" ... "), "")


class DataManagerTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = DataManager(Path(tmp) / "investigations.json")
            manager.save_cases([VALID_CASE])
            self.assertEqual(manager.load_cases(), [VALID_CASE])

    def test_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = DataManager(Path(tmp) / "investigations.json")
            with self.assertRaises(DataError):
                manager.save_cases([VALID_CASE, dict(VALID_CASE)])

    def test_rejects_string_instead_of_answers_list(self):
        bad = json.loads(json.dumps(VALID_CASE))
        bad["clues"][0]["answers"] = "ключ"
        with tempfile.TemporaryDirectory() as tmp:
            manager = DataManager(Path(tmp) / "investigations.json")
            with self.assertRaises(DataError):
                manager.save_cases([bad])

    def test_rejects_answer_without_letters_or_digits(self):
        bad = json.loads(json.dumps(VALID_CASE))
        bad["clues"][0]["answers"] = ["!!!"]
        with tempfile.TemporaryDirectory() as tmp:
            manager = DataManager(Path(tmp) / "investigations.json")
            with self.assertRaises(DataError):
                manager.save_cases([bad])


class SaveManagerTests(unittest.TestCase):
    def test_save_load_and_resume_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = SaveManager(tmp)
            save = manager.create("Моё дело", "case-one")
            save["current_clue"] = 1
            save["inventory"] = [{"name": "Ключ", "icon": "🔑"}]
            manager.save(save)
            loaded = manager.load(save["id"])
            self.assertEqual(loaded["current_clue"], 1)
            self.assertEqual(loaded["inventory"][0]["name"], "Ключ")

    def test_rejects_path_traversal_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = SaveManager(tmp)
            with self.assertRaises(SaveError):
                manager.load("../outside")

    def test_corrupt_save_is_skipped_in_listing_and_rejected_on_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = SaveManager(tmp)
            (Path(tmp) / "deadbeef.json").write_text("{broken", encoding="utf-8")
            self.assertEqual(manager.list_saves(), [])
            with self.assertRaises(SaveError):
                manager.load("deadbeef")

    def test_settings_are_sanitized(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = SaveManager(tmp)
            manager.save_settings({"sound_enabled": "yes", "music_volume": 9,
                                   "font_scale": 0.1, "difficulty": "impossible"})
            settings = manager.load_settings()
            self.assertTrue(settings["sound_enabled"])
            self.assertEqual(settings["music_volume"], 1.0)
            self.assertEqual(settings["font_scale"], 0.8)
            self.assertEqual(settings["difficulty"], "normal")

    def test_completed_cases_are_deduplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = SaveManager(tmp)
            first = manager.create("Первое прохождение", "case-one")
            first.update(completed=True, case_title="Тестовое дело")
            manager.save(first)
            second = manager.create("Второе прохождение", "case-one")
            second.update(completed=True, case_title="Тестовое дело")
            manager.save(second)
            self.assertEqual(len(manager.completed_cases()), 1)


if __name__ == "__main__":
    unittest.main()


class ImageAssetPathTests(unittest.TestCase):
    def test_resolves_existing_relative_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "assets"
            image_dir = root / "images" / "items"
            image_dir.mkdir(parents=True)
            image_file = image_dir / "camera.png"
            image_file.write_bytes(b"placeholder")
            assets = ImageAssets(root)
            self.assertEqual(assets.resolve("items/camera.png"), image_file.resolve())

    def test_rejects_path_traversal_and_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets = ImageAssets(Path(tmp) / "assets")
            self.assertIsNone(assets.resolve("../../outside.png"))
            self.assertIsNone(assets.resolve(str(Path(tmp) / "outside.png")))

    def test_rejects_unsupported_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            assets = ImageAssets(Path(tmp) / "assets")
            self.assertIsNone(assets.resolve("items/camera.svg"))


class DLCManagerTests(unittest.TestCase):
    def test_newest_dlc_is_sorted_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dlcs.json"
            path.write_text(json.dumps([
                {"id": "old", "title": "Old", "added_at": "2026-01-01", "quests": ["case-one"]},
                {"id": "new", "title": "New", "added_at": "2026-11-01", "quests": ["case-one"]}
            ]), encoding="utf-8")
            manager = DLCManager(path, lambda: [VALID_CASE])
            self.assertEqual([x["id"] for x in manager.load_dlcs()], ["new", "old"])

    def test_rejects_unknown_quest_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dlcs.json"
            path.write_text(json.dumps([
                {"id": "bad", "title": "Bad", "added_at": "2026-11-01", "quests": ["missing"]}
            ]), encoding="utf-8")
            manager = DLCManager(path, lambda: [VALID_CASE])
            with self.assertRaises(DataError):
                manager.load_dlcs()

    def test_save_invalid_dlc_does_not_overwrite_previous_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dlcs.json"
            valid = [{"id": "ok", "title": "OK", "added_at": "2026-11-01", "quests": ["case-one"]}]
            path.write_text(json.dumps(valid), encoding="utf-8")
            manager = DLCManager(path, lambda: [VALID_CASE])
            with self.assertRaises(DataError):
                manager.save_dlcs([{"id": "bad", "title": "Bad", "quests": ["missing"]}])
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), valid)


class CompletedDLCBoardTests(unittest.TestCase):
    def test_board_lists_each_completed_quest_from_a_finished_dlc(self):
        with tempfile.TemporaryDirectory() as tmp:
            manager = SaveManager(Path(tmp))
            save = manager.create("Autumn story", "final-case")
            save.update(
                completed=True,
                case_title="Autumn story",
                completed_at="2026-11-06T12:00:00",
                completed_case_ids=["letter-case", "old-house", "final-case"],
                completed_case_titles={
                    "letter-case": "The letter",
                    "old-house": "The old house",
                    "final-case": "The final secret"
                }
            )
            manager.save(save)
            self.assertEqual(
                [item["name"] for item in manager.completed_cases()],
                ["The letter", "The old house", "The final secret"]
            )
