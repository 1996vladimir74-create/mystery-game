import json
import shutil

DEFAULT_CASE = [
  {
    "id": "mystical-package", "title": "MYSTICAL PACKAGE",
    "description": "Таинственное дело, которое предстоит раскрыть.",
    "cover_image": "cases/mystical-package/cover.jpg",
    "background_image": "cases/mystical-package/background.jpg",
    "document_image": "cases/mystical-package/case-document.jpg",
    "final_letter": "Дело №1 закрыто!\n\nТы собрала все улики и раскрыла тайну посылки. Но это ещё не конец истории…\n\nС любовью, твой главный сообщник.",
    "clues": [
      {"task":"Улика №1: Найди предмет, которым Настя любила фотографировать.","answers":["фотоаппарат","фотокамера","камера"],"icon":"📷","illustration_image":"cases/mystical-package/clue-01.jpg","document_image":"cases/mystical-package/document-01.jpg","item_image":"items/camera.jpg","item_name":"Фотоаппарат","item_description":"Предмет, который сохраняет мгновения и превращает их в воспоминания.","story":"На старой фотографии заметен знакомый силуэт. Кажется, эта вещь многое повидала.","hints":["Вещь помогает сохранять изображения.","Подумай о старом устройстве для фотосъёмки."]},
      {"task":"Улика №2: Найди любимую книгу Насти.","answers":["книга","книжка","роман"],"icon":"📖","illustration_image":"cases/mystical-package/clue-02.jpg","document_image":"cases/mystical-package/document-02.jpg","item_image":"items/book.jpg","item_name":"Книга","item_description":"Истории иногда прячут подсказки между строк.","story":"На полях обнаружена короткая пометка, оставленная неизвестным почерком.","hints":["Это можно читать.","Ищи предмет с переплётом и страницами."]},
      {"task":"Улика №3: Найди старый ключ от шкатулки.","answers":["ключ","ключик"],"icon":"🔑","illustration_image":"cases/mystical-package/clue-03.jpg","document_image":"cases/mystical-package/document-03.jpg","item_image":"items/key.jpg","item_name":"Старый ключ","item_description":"Маленький ключ открывает то, что долго оставалось скрытым.","story":"На металле видна крошечная гравировка — знак следующего этапа.","hints":["Он нужен, чтобы открыть замок.","Ищи небольшой металлический предмет."]},
      {"task":"Улика №4: Найди обрывок загадочного письма.","answers":["письмо","записка","послание"],"icon":"✉️","illustration_image":"cases/mystical-package/clue-04.jpg","document_image":"cases/mystical-package/document-04.jpg","item_image":"items/letter.jpg","item_name":"Письмо","item_description":"Фрагмент послания, который связывает найденные предметы.","story":"Чернила немного выцвели, но несколько слов всё ещё можно разобрать.","hints":["Это написанное сообщение.","Его обычно кладут в конверт."]},
      {"task":"Улика №5: Найди таинственный амулет.","answers":["амулет","талисман"],"icon":"🔮","illustration_image":"cases/mystical-package/clue-05.jpg","document_image":"cases/mystical-package/document-05.jpg","item_image":"items/amulet.jpg","item_name":"Амулет","item_description":"Символ удачи и последняя необычная находка перед финалом.","story":"Амулет совпадает с рисунком на конверте из первой улики.","hints":["Это небольшой предмет-оберег.","Его могут носить на цепочке."]},
      {"task":"Улика №6: Найди последний элемент головоломки.","answers":["головоломка","пазл","деталь"],"icon":"🧩","illustration_image":"cases/mystical-package/clue-06.jpg","document_image":"cases/mystical-package/document-06.jpg","item_image":"items/puzzle.jpg","item_name":"Последний фрагмент","item_description":"Последняя часть тайны. Все найденные улики теперь складываются в одну историю.","story":"Все нити расследования сошлись. Осталось открыть финальное послание.","hints":["Это задача, которую нужно решить.","Последний элемент собирает картину целиком."]}
    ]
  }
]

def ensure_default(path, bundled_path=None):
    """Create editable user data, preserving bundled custom cases on first launch."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    if bundled_path and bundled_path.exists() and bundled_path.resolve() != path.resolve():
        shutil.copy2(bundled_path, path)
        return
    path.write_text(json.dumps(DEFAULT_CASE, ensure_ascii=False, indent=2), encoding="utf-8")


class DLCManager:
    """Loads and validates DLC packs, each containing an ordered quest chain."""

    def __init__(self, path, cases_provider):
        from pathlib import Path
        self.path = Path(path)
        self.cases_provider = cases_provider

    def load_dlcs(self):
        import json
        from .core import DataError
        try:
            dlcs = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise DataError(f"Не удалось прочитать список DLC: {exc}") from exc
        if not isinstance(dlcs, list):
            raise DataError("Файл DLC должен содержать JSON-список.")
        case_ids = {case["id"] for case in self.cases_provider()}
        seen = set()
        for dlc in dlcs:
            if not isinstance(dlc, dict) or not isinstance(dlc.get("id"), str) or not dlc["id"].strip():
                raise DataError("У каждого DLC должен быть непустой id.")
            if dlc["id"] in seen:
                raise DataError("ID DLC должны быть уникальными.")
            seen.add(dlc["id"])
            if not isinstance(dlc.get("title"), str) or not dlc["title"].strip():
                raise DataError(f"У DLC «{dlc['id']}» должно быть название.")
            quests = dlc.get("quests")
            if not isinstance(quests, list) or not quests or any(q not in case_ids for q in quests):
                raise DataError(f"У DLC «{dlc['title']}» должен быть непустой список существующих ID расследований.")
            if len(quests) != len(set(quests)):
                raise DataError(f"В DLC «{dlc['title']}» один квест указан несколько раз.")
        return sorted(dlcs, key=lambda item: item.get("added_at", ""), reverse=True)

    def save_dlcs(self, dlcs):
        import json
        from .core import DataError
        if not isinstance(dlcs, list):
            raise DataError("Ожидается список DLC.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(dlcs, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self.path)
        except OSError as exc:
            tmp.unlink(missing_ok=True)
            raise DataError(f"Не удалось сохранить список DLC: {exc}") from exc
        self.load_dlcs()
