# utterance_planner.py
import json
import re
from pathlib import Path

APOLOGY_KEYWORDS = ["すみません", "申し訳", "失礼しました", "ごめんなさい"]
THANKS_KEYWORDS = ["ありがとう", "ありがとうございます", "感謝"]
GREETING_KEYWORDS = ["こんにちは", "こんばんは", "おはようございます", "いらっしゃいませ", "ようこそ"]

def split_sentences(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts = re.split(r'(?<=[。！？!?])\s*', text)
    return [p.strip() for p in parts if p.strip()]

def classify_sentence(text: str) -> str:
    s = text.strip()
    if any(k in s for k in APOLOGY_KEYWORDS):
        return "apology"
    if any(k in s for k in THANKS_KEYWORDS):
        return "thanks"
    if any(k in s for k in GREETING_KEYWORDS):
        return "greeting"
    return "explanation"

def build_plan(text: str) -> list[dict]:
    sentences = split_sentences(text)
    plan = []
    for i, sent in enumerate(sentences):
        label = classify_sentence(sent)
        plan.append({
            "text": sent,
            "label": label,
            "is_last": i == len(sentences) - 1
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