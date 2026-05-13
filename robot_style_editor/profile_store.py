import json
from datetime import datetime
from pathlib import Path

from .config import PROFILE_PATH, SAVE_JSON_DIR


class ProfileStore:
    def __init__(self, path=PROFILE_PATH):
        self.path = path
        self.user_dir = path.parent if path.parent != Path(".") else SAVE_JSON_DIR
        self.user_name = None
        self.current_venue_id = None
        self.current_venue_label = None
        self.data = self.load()
        self.example_results = self.data.pop("example_results", {}) or {}
        self.last_example_results_path = None
        self.load_companion_example_results(path)

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

        data = dict(self.data)
        data.pop("example_results", None)
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def save_as_new(self, filename, directory=SAVE_JSON_DIR):
        target = self.resolve_save_path(filename, directory)
        example_target = self.example_results_path_for(target)

        if target.exists():
            raise FileExistsError(f"同名の保存データが既にあります: {target.name}")
        if self.example_results and example_target.exists():
            raise FileExistsError(f"同名の接客履歴が既にあります: {example_target.name}")

        data = dict(self.data)
        data.pop("example_results", None)
        now = datetime.now().isoformat(timespec="seconds")
        data["updated_at"] = now
        data["saved_at"] = now

        target.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.save_example_results_as(target, now)
        return target

    def resolve_save_path(self, filename, directory=SAVE_JSON_DIR):
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
        return directory / target_name

    def resolve_user_dir(self, username, directory=SAVE_JSON_DIR):
        username = (username or "").strip()
        if not username:
            raise ValueError("ユーザー名を入力してください")

        target_name = Path(username).name
        if target_name != username:
            raise ValueError("ユーザー名にはフォルダ区切りを含めないでください")

        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        return directory / target_name

    def start_new_user_folder(self, username, directory=SAVE_JSON_DIR):
        target = self.resolve_user_dir(username, directory)
        if target.exists() and not target.is_dir():
            raise FileExistsError(f"同名のファイルが既にあります: {target.name}")
        if target.exists() and any(target.iterdir()):
            raise FileExistsError(f"同名のユーザーフォルダが既にあります: {target.name}")

        target.mkdir(parents=True, exist_ok=True)
        self.user_dir = target
        self.user_name = target.name
        self.current_venue_id = None
        self.current_venue_label = None
        self.path = target / "_未選択.json"
        self.data = {}
        self.example_results = {}
        self.last_example_results_path = None
        return target

    def load_user_folder(self, path):
        target = Path(path)
        if target.is_file():
            return self.load_from(target)
        if not target.exists() or not target.is_dir():
            raise ValueError("ユーザーフォルダを選択してください")

        self.user_dir = target
        self.user_name = target.name
        self.current_venue_id = None
        self.current_venue_label = None
        self.path = target / "_未選択.json"
        self.data = {}
        self.example_results = {}
        self.last_example_results_path = None
        return target

    def venue_profile_path(self, venue_id):
        if self.user_dir is None:
            raise ValueError("先にユーザーを開始してください")
        return Path(self.user_dir) / f"{venue_id}.json"

    def select_venue_session(self, venue_id, venue_label=None):
        from .config_default_profile import build_default_profile

        target = self.venue_profile_path(venue_id)
        self.current_venue_id = venue_id
        self.current_venue_label = venue_label or venue_id
        self.path = target

        if target.exists():
            self.load_from(target, persist_active=False)
            self.current_venue_id = venue_id
            self.current_venue_label = venue_label or self.data.get("venue_label") or venue_id
            self.data["user_name"] = self.user_name
            self.data["venue_id"] = self.current_venue_id
            self.data["venue_label"] = self.current_venue_label
            self.save()
            return target

        self.data = build_default_profile()
        self.example_results = {}
        self.last_example_results_path = None
        self.data["user_name"] = self.user_name
        self.data["venue_id"] = self.current_venue_id
        self.data["venue_label"] = self.current_venue_label
        self.save()
        return target

    def start_new_session(self, filename, directory=SAVE_JSON_DIR):
        target = self.resolve_save_path(filename, directory)
        example_target = self.example_results_path_for(target)
        if target.exists():
            raise FileExistsError(f"同名の保存データが既にあります: {target.name}")
        if example_target.exists():
            raise FileExistsError(f"同名の接客履歴が既にあります: {example_target.name}")

        self.path = target
        self.example_results = {}
        self.last_example_results_path = None
        self.data.pop("saved_at", None)
        self.save()
        return target

    def save_current_with_examples(self):
        self.save()
        return self.save_example_results_as(self.path)

    def load_from(self, path, persist_active=True):
        source = Path(path)
        data = json.loads(source.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("保存データの形式が正しくありません")

        self.data = data
        self.example_results = self.data.pop("example_results", {}) or {}
        self.path = source
        self.user_dir = source.parent
        self.user_name = source.parent.name if source.parent != SAVE_JSON_DIR else source.stem
        self.current_venue_id = self.data.get("venue_id")
        self.current_venue_label = self.data.get("venue_label")
        self.load_companion_example_results(source)
        if persist_active:
            self.save()

        return source

    def example_results_path_for(self, profile_path):
        profile_path = Path(profile_path)
        return profile_path.with_name(f"{profile_path.stem}_example_results.json")

    def example_results_candidates_for(self, profile_path):
        profile_path = Path(profile_path)
        candidates = [self.example_results_path_for(profile_path)]
        save_json_candidate = SAVE_JSON_DIR / f"{profile_path.stem}_example_results.json"
        if save_json_candidate not in candidates:
            candidates.append(save_json_candidate)
        return candidates

    def load_companion_example_results(self, profile_path):
        for candidate in self.example_results_candidates_for(profile_path):
            if not candidate.exists():
                continue
            data = json.loads(candidate.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"接客履歴の形式が正しくありません: {candidate.name}")
            self.example_results = data.get("example_results", data)
            self.last_example_results_path = candidate
            return candidate
        self.last_example_results_path = None
        return None

    def save_example_results_as(self, profile_path, saved_at=None):
        self.last_example_results_path = None
        if not self.example_results:
            return None

        target = self.example_results_path_for(profile_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        now = saved_at or datetime.now().isoformat(timespec="seconds")
        payload = {
            "saved_at": now,
            "profile_file": Path(profile_path).name,
            "example_results": self.example_results,
        }
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        self.last_example_results_path = target
        return target

    def get_example_results(self):
        return self.example_results

    def set_example_results(self, value):
        self.example_results = value or {}

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
