import json
from datetime import datetime
from pathlib import Path

from .config import DEFAULT_SCENARIO_PATH, SAVE_DIR


class ScenarioStore:
    def __init__(self, path=DEFAULT_SCENARIO_PATH):
        self.path = Path(path)
        self.data = self.load()

    def load(self):
        if not self.path.exists():
            return {
                "scenario_title": "あるシナリオ",
                "utterances": [],
            }

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {
                "scenario_title": "あるシナリオ",
                "utterances": [],
            }

    def save(self):
        self.data["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.path

    def save_as(self, filename):
        filename = (filename or "").strip()
        if not filename:
            raise ValueError("ファイル名を入力してください")
        if not filename.endswith(".json"):
            filename = f"{filename}.json"

        target_name = Path(filename).name
        if target_name != filename:
            raise ValueError("ファイル名にはフォルダ区切りを含めないでください")

        self.path = SAVE_DIR / target_name
        return self.save()
