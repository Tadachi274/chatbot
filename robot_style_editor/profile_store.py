import json
from datetime import datetime
from pathlib import Path

from .config import PROFILE_PATH, SAVE_JSON_DIR


class ProfileStore:
    def __init__(self, path=PROFILE_PATH):
        self.path = path
        self.data = self.load()

    def load(self):
        if not self.path.exists():
            return {}

        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save(self):
        self.data["updated_at"] = datetime.now().isoformat(timespec="seconds")

        self.path.parent.mkdir(parents=True, exist_ok=True)

        self.path.write_text(
            json.dumps(self.data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def save_as_new(self, filename, directory=SAVE_JSON_DIR):
        filename = (filename or "").strip()
        if not filename:
            raise ValueError("ファイル名を入力してください")

        if not filename.endswith(".json"):
            filename = f"{filename}.json"

        target_name = Path(filename).name
        if target_name != filename:
            raise ValueError("ファイル名にはフォルダ区切りを含めないでください")

        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / target_name

        if target.exists():
            raise FileExistsError(f"同名の保存データが既にあります: {target.name}")

        data = dict(self.data)
        now = datetime.now().isoformat(timespec="seconds")
        data["updated_at"] = now
        data["saved_at"] = now

        target.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target

    def load_from(self, path, persist_active=True):
        source = Path(path)
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("保存データの形式が正しくありません")

        self.data = data
        if persist_active:
            self.save()

        return source

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value, auto_save=True):
        self.data[key] = value

        if auto_save:
            self.save()

    def get_nested(self, key, default=None):
        value = self.data.get(key)
        if value is None:
            return default
        return value
