import json
from datetime import datetime

from .config import PROFILE_PATH


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