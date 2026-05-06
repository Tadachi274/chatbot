from copy import deepcopy

from .config import BASE_DIR
from .config_style_detail import STYLE_DETAIL_DEFAULTS, get_style_detail_option


NEUTRAL_VOICE_PARAMS = {
    "volume": 1.3,
    "rate": 1.0,
    "pitch": 1.0,
    "emphasis": 1.0,
    "joy": 0.0,
    "anger": 0.0,
    "sadness": 0.0,
}

NEUTRAL_TTS_INSTRUCTIONS = {
    "tts_volume": 1.3,
    "tts_rate": 1.0,
    "tts_pitch": 1.0,
    "tts_emphasis": 1.0,
    "tts_emo_joy": 0.0,
    "tts_emo_angry": 0.0,
    "tts_emo_sad": 0.0,
}

NEUTRAL_VOICE = {
    "id": "neutral",
    "label": "Neutral",
    "params": NEUTRAL_VOICE_PARAMS,
    "controls": {
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
    },
}

NEUTRAL_FACE = {
    "id": "neutral",
    "label": "Neutral",
    "type": "neutral",
    "level": 1,
}

STYLE_SOURCES = {
    "politeness": {
        "id": "formal",
        "label": "軽い尊敬語",
        "example1": "本日はどのようなご用件でしょうか。",
        "example2": "ご本人様確認のため、身分証明書を確認させていただいてもよろしいでしょうか。",
        "prompt": (
            "軽い尊敬語を使い、丁寧だが堅すぎない自然な話し方にしてください。"
            "例：「本日はどのようなご用件でしょうか。」"
            "「ご本人様確認のため、身分証明書を確認させていただいてもよろしいでしょうか。」"
        ),
    },
    "intimacy": {
        "id": "middle",
        "label": "中",
        "person": "nozomi",
        "politeness": "formal",
        "example1": "今日はどのようなご用件でしょうか。",
        "example2": "確認のため、身分証明書を見せていただけますか。",
        "prompt": "親しみは中程度にしてください。丁寧さを保ちながら、少し話しかけやすい自然な表現にしてください。",
    },
    "vocabulary": {
        "id": "middle",
        "label": "中",
        "person": "nozomi",
        "politeness": "formal",
        "intimacy": "middle",
        "example1": "こちらは、甘味が強く、口に入れるとふわっと溶けるようなお菓子ですよ。",
        "example2": "入口から見て右側の棚にありますよ。",
        "prompt": "語彙は中程度にしてください。一般的な接客で自然に使われる、少し具体的な表現にしてください。",
    },
    "length": {
        "id": "middle",
        "label": "中",
        "example1": "もうすぐ閉店時間です。",
        "example2": "少しだけお待ちいただけますか。",
        "prompt": (
            "発話は中くらいの長さにしてください。現在選択されている敬語・親しみ・語彙の方針は維持したまま、"
            "短すぎず長すぎない自然な一文で伝えてください。"
        ),
    },
}


def make_intent(intent, label, text, techniques=None, extra=None):
    data = {
        "intent": intent,
        "label": label,
        "text": text,
        "face": deepcopy(NEUTRAL_FACE),
        "voice": deepcopy(NEUTRAL_VOICE),
        "tts_instructions": deepcopy(NEUTRAL_TTS_INSTRUCTIONS),
        "techniques": techniques or [],
        "prompt": f"{label}の発話。保存された text を読み上げる。",
    }
    if extra:
        data.update(extra)
    return data


def build_default_style_detail():
    labels = {}
    prompts = []
    for key, selected in STYLE_DETAIL_DEFAULTS.items():
        selected_ids = selected if isinstance(selected, list) else [selected]
        option_labels = []
        for option_id in selected_ids:
            option = get_style_detail_option(key, option_id)
            if option:
                option_labels.append(option["label"])
                prompts.append(option["prompt"])
        labels[key] = "、".join(option_labels) if option_labels else "なし"

    return {
        "label": "詳細設定",
        "selections": deepcopy(STYLE_DETAIL_DEFAULTS),
        "labels": labels,
        "prompt": " ".join(prompts),
        "description": "会話全体に反映する話し方の詳細傾向。",
    }


def build_default_profile():
    profile = {
        "speaker": "nozomi_emo_22_standard",
        "speaker_test_text": "話し手が変更されました",
        "politeness": deepcopy(STYLE_SOURCES["politeness"]),
        "politeness_test_text": "今日はどのようなご用件でしょうか。",
        "intimacy": deepcopy(STYLE_SOURCES["intimacy"]),
        "intimacy_test_text": "今日はどのようなご用件でしょうか。",
        "vocabulary": deepcopy(STYLE_SOURCES["vocabulary"]),
        "vocabulary_test_text": "こちらは、甘味が強く、口に入れるとふわっと溶けるようなお菓子です。",
        "length": deepcopy(STYLE_SOURCES["length"]),
        "length_test_text": "もうすぐ閉店時間です。",
        "style_detail": build_default_style_detail(),
        "special_consideration": {
            "label": "特別考慮",
            "text": "",
            "prompt": "",
            "strength": "strong",
            "description": "参加者や場面に合わせて強く反映する自由記述の配慮条件。",
        },
        "speech_speed": {
            "value": 1.0,
            "label": "1.00 倍",
            "prompt": "話すスピードは通常の 1.00 倍程度にしてください。ただし不自然に聞こえない範囲で調整してください。",
        },
        "sentence_pause": {
            "value": 0.2,
            "label": "0.20 秒",
            "gaze": {
                "id": "front",
                "label": "正面",
                "lookaway": "f",
                "priority": 4,
                "keeptime": 800,
            },
            "description": "ターンを保持している間の一文と一文の間の時間",
            "example": "こんにちは。 / 今日はどのようなご用件でしょうか？",
            "prompt": "一文と一文の間は約0.20秒空けてください。これは発話中にターンを保持している状態での文間ポーズです。",
        },
        "response_delay": {
            "total_value": 0.4,
            "label": "0.40 秒",
            "wait_after_detection": 0.2,
            "thinking_total_value": 1.0,
            "thinking_label": "1.00 秒",
            "thinking_wait_after_detection": 0.8,
            "silence_hold_sec": 0.2,
            "description": "相手の発話終了からロボットが返答を開始するまでの総時間。",
            "prompt": "通常時は相手の発話が終わってから約0.40秒後、考えている時は約1.00秒後に返答を開始してください。",
        },
        "thinking_pose": {
            "face": deepcopy(NEUTRAL_FACE),
            "gaze": {
                "id": "front",
                "label": "正面",
                "lookaway": "f",
                "priority": 4,
                "keeptime": 1500,
            },
            "description": "ロボットが考えている間の表情と視線方向",
        },
        "listening_pose": {
            "face": deepcopy(NEUTRAL_FACE),
            "eye_open": {
                "id": "normal",
                "left_upper": 64,
                "left_lower": 0,
                "right_upper": 64,
                "right_lower": 0,
                "axes": {"1": 64, "6": 0, "2": 64, "7": 0},
            },
            "nod": {
                "id": "none",
                "label": "無",
                "amplitude": 0,
                "duration": 0,
                "times": 1,
                "priority": 3,
            },
            "backchannel_voice": {
                "mode": "none",
                "probability": 0.3,
                "effective_probability": 0.0,
                "word_id": "hai",
                "word_type": "wav",
                "text": "はい",
                "custom_text": "",
                "wav_path": str(BASE_DIR / "sample_audio" / "はい.wav"),
                "description": "うなづき時に、指定割合で既存WAVの相槌を再生する",
            },
            "amount": {
                "id": "middle",
                "label": "中",
                "silence_sec": 0.2,
                "description": "自然な文節の間で相槌を入れる",
            },
            "description": "ロボットが相手の話を聴いている間の表情・目の開き・相槌設定",
        },
        "understanding_pose": {
            "face": deepcopy(NEUTRAL_FACE),
            "nod": {
                "id": "large_once",
                "label": "大 1回",
                "amplitude": 15,
                "duration": 500,
                "count": 1,
                "priority": 3,
            },
            "word": {
                "word_id": "hai",
                "word_type": "wav",
                "text": "はい",
                "custom_text": "",
                "wav_path": str(BASE_DIR / "sample_audio" / "はい.wav"),
            },
            "response_delay_source": "response_delay.wait_after_detection / response_delay.thinking_wait_after_detection",
            "description": "相手の発話を理解した直後に出す表情・うなづき・短い言葉",
        },
        "filler": {
            "enabled": False,
            "selected_ids": [],
            "phrases": [],
            "custom_text": "",
            "voice": deepcopy(NEUTRAL_VOICE),
            "tts_instructions": deepcopy(NEUTRAL_TTS_INSTRUCTIONS),
            "prompt": "フィラーは使用しない。",
        },
    }

    profile["greeting"] = make_intent("greeting", "挨拶", "こんにちは、いらっしゃいませ。")
    profile["explanation"] = make_intent("explanation", "説明時", "チェックアウトは11時となっております。")
    profile["question"] = make_intent("question", "質問時", "本日は一泊でよろしいでしょうか。")
    profile["acceptance"] = make_intent("acceptance", "承諾時", "かしこまりました。")
    profile["request"] = make_intent("request", "要求時", "こちらにご記入をお願いいたします。")
    profile["apology"] = make_intent("apology", "謝罪時", "申し訳ございません。")
    profile["gratitude"] = make_intent("gratitude", "感謝時", "ありがとうございます。")
    profile["smalltalk"] = make_intent("smalltalk", "雑談時", "今日は過ごしやすいですね。")

    return profile
