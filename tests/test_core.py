import json, tempfile, unittest
from pathlib import Path
from mystery_game.core import DataManager, DataError, SaveManager, normalize_answer

class CoreTests(unittest.TestCase):
    def test_answer_normalization(self):
        self.assertEqual(normalize_answer(" Фотоаппарат! "), "фотоаппарат")
        self.assertEqual(normalize_answer("Ёлка"), "елка")
    def test_save_round_trip(self):
        with tempfile.TemporaryDirectory() as folder:
            m=SaveManager(Path(folder)); s=m.create("Тест","case-1")
            s["current_clue"]=2;m.save(s); loaded=m.load(s["id"])
            self.assertEqual(loaded["current_clue"],2);self.assertEqual(loaded["name"],"Тест")
    def test_completed_case_listing(self):
        with tempfile.TemporaryDirectory() as folder:
            m=SaveManager(Path(folder));s=m.create("Тест","case-1")
            s.update(completed=True,case_title="Дело №1");m.save(s)
            self.assertEqual(m.completed_cases()[0]["name"],"Дело №1")
    def test_case_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"cases.json";p.write_text(json.dumps([{"id":"x","title":"X","clues":[]}]),encoding="utf-8")
            with self.assertRaises(DataError):DataManager(p).load_cases()

if __name__=="__main__":unittest.main()
