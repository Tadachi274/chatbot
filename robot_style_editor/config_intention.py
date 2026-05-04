VOICE_FRIENDLY_MAP = {
    "volume": (1.3, 1.3),
    "rate": (1.0, 1.0),
    "pitch": (1.0, 1.05),
    "emphasis": (1.0, 1.05),
    "joy": (0.0, 0.3),
    "anger": (0.0, 0.0),
    "sadness": (0.0, 0.3),
}

VOICE_CALM_MAP = {
    "volume": (1.3, 1.3),
    "rate": (1.0, 0.9),
    "pitch": (1.0, 0.9),
    "emphasis": (1.0, 0.95),
    "joy": (0.0, 0.0),
    "anger": (0.0, 0.0),
    "sadness": (0.0, 0.4),
}

VOICE_TENSION_MAP = {
    "volume": (1.3, 1.5),
    "rate": (1.0, 1.2),
    "pitch": (1.0, 1.2),
    "emphasis": (1.0, 1.3),
    "joy": (0.0, 0.4),
    "anger": (0.0, 0.0),
    "sadness": (0.0, 0.1),
}

VOICE_BASE_PARAMS = {
    "volume": 1.3,
    "rate": 1.0,
    "pitch": 1.0,
    "emphasis": 1.0,
    "joy": 0.0,
    "anger": 0.0,
    "sadness": 0.0,
}

VOICE_RANGE = {
    "volume": (0.0, 2.0),
    "rate": (0.5, 2.0),
    "pitch": (0.5, 2.0),
    "emphasis": (0.0, 2.0),
    "joy": (0.0, 1.0),
    "anger": (0.0, 1.0),
    "sadness": (0.0, 1.0),
}

VOICE_CONTROL_RANGE = (0.0, 2.0)

VOICE_PRESETS = [
    {
        "id": "friendly",
        "label": "親しみ",
        "friendly": 1.5,
        "calm": 1.0,
        "tension": 1.0,
        "description": "少し明るく、距離が近い挨拶。",
    },
    {
        "id": "calm",
        "label": "落ち着き",
        "friendly": 1.0,
        "calm": 1.5,
        "tension": 0.9,
        "description": "安心感があり、急かさない挨拶。",
    },
    {
        "id": "lively",
        "label": "テンション",
        "friendly": 1.2,
        "calm": 0.9,
        "tension": 1.5,
        "description": "元気で来店直後に目を引く挨拶。",
    },
    {
        "id": "other",
        "label": "その他",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "フェーダーで声色を調整します。",
    },
]

TECHNIQUE_DEFS = {
    "empathy": "相手の感情や状況を言語化し、共感を示す一文を入れる。「ご不安ですよね」などの形で明示する。",
    "consideration": "相手への配慮を入れる。負担を気遣う表現や「もしよろしければ」などの柔らかい言い回しを含める。",
    "seasonal_topic": "季節に関する話題を入れる。気温や天候、時期感（暑いですね、寒いですね等）に触れる。",
    "time_topic": "時間帯に関する話題を入れる。朝・昼・夜や「お仕事帰り」など、現在の時間状況に言及する。",
    "self_disclosure": "軽い自己開示を入れる。店員側の経験や傾向を一文だけ入れ、親しみを生む。",
    "evidence": "発言に対する理由や根拠を入れる。判断理由を明示する。",
    "expertise": "専門的な知識や用語を一つ以上入れる。ただし必要に応じて簡単な説明も添える。",
    "paraphrase": "一度述べた内容を別の言い方で言い換える。難しい表現の後に分かりやすい説明を続ける。",
    "summary": "相手の発言や状況を短くまとめる一文を入れる。「つまり〜ということですね」などで整理する。",
    "step_by_step": "手順や説明を段階的に分ける。1ステップずつ順番に説明する形にする。",
    "proactive": "相手が次に必要としそうな情報や行動を先回りして提案する。",
    "goal_clarity": "会話の目的やゴールを最初または途中で明示する。「これから〜をご案内します」など。",
    "permission": "行動や説明の前に許可を取る。「よろしいでしょうか」といった確認を入れる。",
    "positive_reframe": "否定的な状況でも前向きな言い方に変換する。メリットや良い面を示す。",
    "hedge": "断定を少し和らげる。「〜かもしれません」「〜と思われます」などのヘッジ表現を入れる。",
    "options": "複数の選択肢を提示する。最低でも2つの案とその違いを簡単に示す。",
    "alternative": "別の方法や代替案を提示する。現在の案に加えて他の選択肢も示す。",
    "name_call": "相手の名前が分かる前提で、名前を呼ぶ形の一文を入れる。",
    "confirmation": "内容確認の一文を入れる。「〜でよろしいでしょうか」などで認識の一致を確認する。",
    "clarification_question": "曖昧な点について質問する。不足情報を具体化する質問を一つ以上入れる。",
    "hypothesis": "相手の意図を推測し、仮説として提示する。「〜ということでしょうか」などで確認する。",
}

TECHNIQUE_LABELS = {
    "empathy": "共感",
    "consideration": "配慮",
    "seasonal_topic": "季節",
    "time_topic": "時間",
    "self_disclosure": "自己開示",
    "evidence": "根拠",
    "expertise": "専門",
    "paraphrase": "言換",
    "summary": "要約",
    "step_by_step": "段階",
    "proactive": "先回り",
    "goal_clarity": "目的",
    "permission": "許可",
    "positive_reframe": "前向き",
    "hedge": "柔らげ",
    "options": "選択肢",
    "alternative": "代替",
    "name_call": "名前",
    "confirmation": "確認",
    "clarification_question": "質問",
    "hypothesis": "仮説",
}

GREETING_TECHNIQUE_ORDER = [
    "seasonal_topic",
    "time_topic",
    "consideration",
]

GREETING_TECHNIQUE_COMBO_SENTENCES = {
    (): "",
    ("seasonal_topic",): "今日は少し過ごしやすい気候ですね。",
    ("time_topic",): "お仕事帰りでしょうか。",
    ("consideration",): "もしよろしければ、ゆっくりご案内します。",
    ("seasonal_topic", "time_topic"): "今日は過ごしやすい気候ですね。お仕事帰りでしょうか。",
    ("seasonal_topic", "consideration"): "今日は過ごしやすい気候ですね。もしよろしければ、ゆっくりご案内します。",
    ("time_topic", "consideration"): "お仕事帰りでしたら、無理のない範囲でゆっくりご案内します。",
    (
        "seasonal_topic",
        "time_topic",
        "consideration",
    ): "今日は過ごしやすい気候ですね。お仕事帰りでしたら、無理のない範囲でゆっくりご案内します。",
}

GREETING_SHORT_TECHNIQUE_COMBO_SENTENCES = {
    (): "",
    ("seasonal_topic",): "いい気候ですね。",
    ("time_topic",): "お帰りですか。",
    ("consideration",): "ごゆっくりどうぞ。",
    ("seasonal_topic", "time_topic"): "いい気候ですね。お帰りですか。",
    ("seasonal_topic", "consideration"): "いい気候ですね。ごゆっくりどうぞ。",
    ("time_topic", "consideration"): "お帰りなら、無理せずどうぞ。",
    (
        "seasonal_topic",
        "time_topic",
        "consideration",
    ): "いい気候ですね。お帰りなら、無理せずどうぞ。",
}

GREETING_OPENING_TEXT = {
    "very_formal": {
        "low": "いらっしゃいませ。",
        "middle": "いらっしゃいませ。",
        "high": "いらっしゃいませ。",
    },
    "formal": {
        "low": "いらっしゃいませ。",
        "middle": "こんにちは、いらっしゃいませ。",
        "high": "こんにちは、いらっしゃいませ。",
    },
    "polite": {
        "low": "こんにちは、いらっしゃいませ。",
        "middle": "こんにちは、いらっしゃいませ。",
        "high": "こんにちは、いらっしゃいませ〜。",
    },
    "casual": {
        "low": "こんにちは。",
        "middle": "こんにちは。",
        "high": {
            "nozomi": "こんにちは〜。",
            "kenta": "こんにちはっす。",
        },
    },
}

GREETING_NEED_SENTENCE = {
    "very_formal": {
        "easy": {
            "low": "本日は何をお探しでしょうか。",
            "middle": "本日は何をお探しでしょうか。",
            "high": "本日は何をお探しでしょうか。",
        },
        "middle": {
            "low": "本日はどのようなご用件でしょうか。",
            "middle": "本日はどのようなご用件でしょうか。",
            "high": "本日はどのようなご用件でしょうか。",
        },
        "hard": {
            "low": "本日はどのようなご相談やお探し物がございますか。",
            "middle": "本日はどのようなご相談やお探し物がございますか。",
            "high": "本日はどのようなご相談やお探し物がございますか。",
        },
    },
    "formal": {
        "easy": {
            "low": "今日は何をお探しでしょうか。",
            "middle": "今日は何をお探しでしょうか。",
            "high": "今日は何をお探しでしょうか。",
        },
        "middle": {
            "low": "今日はどのようなご用件でしょうか。",
            "middle": "今日はどのようなご用件でしょうか。",
            "high": "今日はどのようなご用件でしょうか。",
        },
        "hard": {
            "low": "今日はどのようなご相談やお探し物でしょうか。",
            "middle": "今日はどのようなご相談やお探し物でしょうか。",
            "high": "今日はどのようなご相談やお探し物でしょうか。",
        },
    },
    "polite": {
        "easy": {
            "low": "今日は何をお探しですか。",
            "middle": "今日は何をお探しですか。",
            "high": "今日は何をお探しですか〜。",
        },
        "middle": {
            "low": "今日はどのような用件でしょうか。",
            "middle": "今日はどのようなご用件でしょうか。",
            "high": "今日はどのようなご用件でしょうか〜。",
        },
        "hard": {
            "low": "今日はどのようなご相談やお探し物でしょうか。",
            "middle": "今日はどのようなご相談やお探し物でしょうか。",
            "high": "今日はどのようなご相談やお探し物でしょうか〜。",
        },
    },
    "casual": {
        "easy": {
            "low": "何を探してる？",
            "middle": "何を探してるの？",
            "high": {
                "nozomi": "何を探してるの〜？",
                "kenta": "何を探してるんすか。",
            },
        },
        "middle": {
            "low": "今日はどうした？",
            "middle": "今日はどうしたの？",
            "high": {
                "nozomi": "今日はどうしたの〜？",
                "kenta": "今日はどうしたんすか。",
            },
        },
        "hard": {
            "low": "今日はどんな相談？",
            "middle": "今日はどんな相談なの？",
            "high": {
                "nozomi": "今日はどんな相談なの〜？",
                "kenta": "今日はどんな相談っすか。",
            },
        },
    },
}

GREETING_LONG_EXTRA = {
    "very_formal": "必要に応じて、順番に確認しながらご案内いたします。",
    "formal": "必要に応じて、順番に確認しながらご案内します。",
    "polite": "必要でしたら、一緒に確認しながらご案内します。",
    "casual": "よければ、一緒に見ていこう。",
}


def clamp(value, vmin, vmax):
    return max(vmin, min(value, vmax))


def add_voice_modifier(params, control_value, mapping):
    for key, (base, target) in mapping.items():
        delta = target - base
        ratio = (float(control_value) - 1.0) / (1.5 - 1.0)
        params[key] += delta * ratio

    return params


def compute_voice_params(friendly=1.0, calm=1.0, tension=1.0):
    params = dict(VOICE_BASE_PARAMS)
    params = add_voice_modifier(params, friendly, VOICE_FRIENDLY_MAP)
    params = add_voice_modifier(params, calm, VOICE_CALM_MAP)
    params = add_voice_modifier(params, tension, VOICE_TENSION_MAP)

    for key, (vmin, vmax) in VOICE_RANGE.items():
        params[key] = round(clamp(params[key], vmin, vmax), 2)

    return params


def voice_params_to_tts_instructions(params):
    return {
        "tts_volume": round(float(params["volume"]), 2),
        "tts_rate": round(float(params["rate"]), 2),
        "tts_pitch": round(float(params["pitch"]), 2),
        "tts_emphasis": round(float(params["emphasis"]), 2),
        "tts_emo_joy": round(float(params["joy"]), 2),
        "tts_emo_angry": round(float(params["anger"]), 2),
        "tts_emo_sad": round(float(params["sadness"]), 2),
    }
