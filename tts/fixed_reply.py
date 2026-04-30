from pathlib import Path
import re

SCENARIO_CONFIG = {
    "hotel": {
        "role": "ホテル受付",
        "first_task": "チェックインかどうかを確認してください。",
        "greeting_reply": "こんにちは。チェックインでよろしいでしょうか？",
        "call_reply": "はい。いかがされましたか？",
        "thanks_reply": "こちらこそありがとうございます。どうぞごゆっくりおくつろぎくださいませ。",
        "final_thanks_context": {"CLOSING", "THANKING"},
    },

    "market": {
        "role": "スーパーのレジ店員",
        "first_task": "会計を始める流れに進めてください。",
        "greeting_reply": "こんにちは。いらっしゃいませ。お会計でよろしいでしょうか？",
        "call_reply": "はい。いかがされましたか？",
        "thanks_reply": "ありがとうございました。またお越しくださいませ。",
        "final_thanks_context": {"CLOSING", "THANKING"},
    },

    "electronics_store": {
        "role": "家電量販店の店員",
        "first_task": "商品案内や相談につなげてください。",
        "greeting_reply": "こんにちは。いらっしゃいませ。本日はどのような商品をお探しでしょうか？",
        "call_reply": "はい。何かお探しでしょうか？",
        "thanks_reply": "ありがとうございます。また何かございましたらお気軽にお声がけください。",
        "final_thanks_context": {"CLOSING", "THANKING"},
    },

    "restaurant": {
        "role": "ファミレスの店員",
        "first_task": "来店人数や席への案内につなげてください。",
        "greeting_reply": "こんにちは。いらっしゃいませ。何名様でしょうか？",
        "call_reply": "はい。ご注文でしょうか？",
        "thanks_reply": "ありがとうございます。ごゆっくりお過ごしください。",
        "final_thanks_context": {"CLOSING", "THANKING"},
    },

    "station": {
        "role": "駅の窓口係",
        "first_task": "切符購入や乗り換え案内につなげてください。",
        "greeting_reply": "こんにちは。本日はどちらまで行かれますか？",
        "call_reply": "はい。どのようなご案内でしょうか？",
        "thanks_reply": "ありがとうございます。お気をつけてお出かけください。",
        "final_thanks_context": {"CLOSING", "THANKING"},
    },

    "apparel": {
        "role": "アパレルショップの店員",
        "first_task": "お客様の様子を見ながら、必要に応じて商品提案やコーディネートの案内につなげてください。",
        "greeting_reply": "こんにちは。いらっしゃいませ。ごゆっくりご覧くださいませ。",
        "call_reply": "はい。何かお探しでしょうか？",
        "thanks_reply": "ありがとうございます。またぜひお立ち寄りくださいませ。",
        "final_thanks_context": {"CLOSING", "THANKING"},
    },


}


FIXED_RESPONSES = {}

for scenario, cfg in SCENARIO_CONFIG.items():
    FIXED_RESPONSES[scenario] = [
        {
            "intent": "greeting",
            "patterns": ["こんにちは", "こんばんは", "おはようございます", "はじめまして"],
            "reply_text": cfg["greeting_reply"],
            "wav_path": Path(f"reply_audio/{scenario}/greeting/greeting.wav"),
            "label": "OPENING",
        },
        {
            "intent": "call",
            "patterns": ["すみません", "すいません", "あの"],
            "reply_text": cfg["call_reply"],
            "wav_path": Path(f"reply_audio/{scenario}/call/call.wav"),
            "label": "QUESTION",
        },
        {
            "intent": "final_thanks",
            "patterns": ["ありがとう", "ありがとうございます", "ありがとうございました"],
            "reply_text": cfg["thanks_reply"],
            "wav_path": Path(f"reply_audio/{scenario}/thanks/thanks.wav"),
            "label": "CLOSING",
        },
    ]


SHORT_AFFIRM_SET = {
    "はい", "うん", "ええ", "お願いします", "大丈夫です", "結構です"
}


def normalize_utterance(text: str) -> str:
    text = text.strip()
    text = re.sub(r"[ 　]+", "", text)
    text = text.replace("。", "").replace("！", "").replace("!", "")
    text = text.replace("?", "").replace("？", "")
    return text


def is_short_affirm(text: str) -> bool:
    t = normalize_utterance(text)
    if t in SHORT_AFFIRM_SET:
        return True
    return len(t) <= 6 and t in {"はい", "うん", "ええ", "お願い", "お願いします"}


def get_scenario_config(scenario: str) -> dict:
    return SCENARIO_CONFIG.get(scenario, SCENARIO_CONFIG["hotel"])


def find_fixed_response(utterance: str, scenario: str, prev_da_type: str | None = None):
    norm = normalize_utterance(utterance)

    if scenario not in FIXED_RESPONSES:
        scenario = "hotel"

    cfg = get_scenario_config(scenario)

    # 「ありがとう」は会話途中にも出るので、締め文脈だけ固定返答にする
    if norm in {"ありがとう", "ありがとうございます", "ありがとうございました"}:
        if prev_da_type in cfg.get("final_thanks_context", {"CLOSING", "THANKING"}):
            for item in FIXED_RESPONSES[scenario]:
                if item.get("intent") == "final_thanks":
                    return item
        return None

    for item in FIXED_RESPONSES[scenario]:
        for p in item["patterns"]:
            if norm == normalize_utterance(p):
                return item

    return None


def find_opening_prefetch_key(utterance: str, scenario: str) -> str | None:
    norm = normalize_utterance(utterance)

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