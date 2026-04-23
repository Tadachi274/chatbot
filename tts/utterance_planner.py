# utterance_planner.py
import json
import re
from pathlib import Path

VALID_TYPES = {
    "OPENING", "STATEMENT", "OPINION", "QUESTION",
    "APOLOGY", "THANKING", "CLOSING", "ACCEPT"
}


def build_plan(data) -> list[dict]:
    if isinstance(data, str):
        data = json.loads(data)

    plan = []
    for i, item in enumerate(data):
        utterance = item.get("utterance", "").strip()
        label = item.get("type", "")

        if not utterance:
            continue
        if label not in VALID_TYPES:
            label = "STATEMENT"

        plan.append({
            "text": utterance,
            "label": label,
            "is_last": i == len(data) - 1
        })
    return plan

def load_voice_config(path: str) -> dict:
    cfg_path = Path(path)
    with cfg_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    # 新形式: {"voices": {...}}
    if "voices" in data:
        return data["voices"]

    # 旧形式: {"instructions": {...}} しかない場合
    if "instructions" in data:
        base = data["instructions"]
        return {
            "greeting": dict(base),
            "thanks": dict(base),
            "apology": dict(base),
            "explanation": dict(base),
        }

    raise ValueError(f"voice config format error: {path}")


def load_motion_config(path: str) -> dict:
    cfg_path = Path(path)
    with cfg_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if "motions" not in data:
        raise ValueError(f"motion config format error: {path}")

    return data["motions"]