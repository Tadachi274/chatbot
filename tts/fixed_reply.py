from pathlib import Path
import re

FIXED_RESPONSES = {
    "hotel": [
        {
            "patterns": [ "はじめまして","こんばんは","おはようございます"],
            "reply_text": "こんにちは。チェックインでよろしいでしょうか",
            "wav_path": Path("reply_audio/hotel/greeting/こんにちは。チェックインでよろしいでしょうか？_pitch1.08_emphasis1.02_joy0.81.wav"),
            "label": "OPENING",
        },
        {
            "patterns": ["ありがとう", "ありがとうございます","ありがとうございました"],
            "reply_text": "こちらこそありがとうございます。どうぞごゆっくりおくつろぎください。",
            "wav_path": Path("reply_audio/hotel/thanks/こちらこそありがとうございます。どうぞごゆっくりおくつろぎくださいませ。_rate1.04_joy0.4_sad0.4.wav"),
            "label": "CLOSING",
        },
        {
            "patterns": ["すみません", "すいません", "あの"],
            "reply_text": "はい。いかがされましたか？",
            "wav_path": Path("reply_audio/hotel/call/はい。いかがされましたか？_20260415-163529_pitch1.04_emphasis1.04_joy0.22_sad0.22.wav"),
            "label": "QUESTION",
        },
    ],
    "market": [
        {
            "patterns": ["こんにちは", "いらっしゃいませ"],
            "reply_text": "いらっしゃいませ。こんにちは。",
            "wav_path": Path("fixed_wav/market/hello.wav"),
            "label": "greeting",
        },
        {
            "patterns": ["ありがとう", "ありがとうございます"],
            "reply_text": "ありがとうございました。",
            "wav_path": Path("fixed_wav/market/thanks.wav"),
            "label": "greeting",
        },
    ],
}

SHORT_AFFIRM_SET = {
    "はい", "うん", "ええ", "お願いします", "大丈夫です", "結構です"
}

def normalize_utterance(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[ 　]+", "", text)
    text = text.replace("。", "").replace("！", "").replace("?", "").replace("？", "")
    return text

def is_short_affirm(text: str) -> bool:
    t = normalize_utterance(text)
    if t in SHORT_AFFIRM_SET:
        return True
    return len(t) <= 6 and t in {"はい", "うん", "ええ", "お願い", "お願いします"}

def find_fixed_response(utterance: str, scenario: str, prev_da_type: str | None = None):
    norm = normalize_utterance(utterance)
    print(f"[fixed reply] utterance {utterance}")

    if norm in {"ありがとう", "ありがとうございます"}:
        if prev_da_type in {"CLOSING", "THANKING"}:
            for item in FIXED_RESPONSES[scenario]:
                if item.get("intent") == "final_thanks":
                    return item
            return None

        return None

    for item in FIXED_RESPONSES[scenario]:
        for p in item["patterns"]:
            if norm == normalize_utterance(p):
                return item
    return None


def find_opening_prefetch_key(utterance: str, scenario: str) -> str | None:
    norm = normalize_utterance(utterance)

    if scenario == "hotel":
        greeting_set = {
            normalize_utterance("こんにちは"),
            normalize_utterance("こんばんは"),
            normalize_utterance("おはようございます"),
            normalize_utterance("はじめまして"),
        }

        call_set = {
            normalize_utterance("すみません"),
            normalize_utterance("すいません"),
            normalize_utterance("あの"),
        }

        if norm in greeting_set:
            return "greeting"

        if norm in call_set:
            return "call"

    return None