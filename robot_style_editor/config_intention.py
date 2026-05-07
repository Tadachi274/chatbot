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
        "id": "neutral",
        "label": "Neutral",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "挨拶を標準的に伝える声色。",
    },
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

EXPLANATION_VOICE_PRESETS = [
    {
        "id": "neutral",
        "label": "ニュートラル",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "情報をそのまま伝える標準的な声色。",
    },
    {
        "id": "calm",
        "label": "落ち着き",
        "friendly": 1.0,
        "calm": 1.5,
        "tension": 0.8,
        "description": "急かさず、安心して聞ける説明。",
    },
    {
        "id": "soft",
        "label": "柔らかい",
        "friendly": 1.4,
        "calm": 1.2,
        "tension": 0.9,
        "description": "少し親しみがあり、角が立たない説明。",
    },
    {
        "id": "other",
        "label": "その他",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "7項目を個別に調整します。",
    },
]

QUESTION_VOICE_PRESETS = [
    {
        "id": "neutral",
        "label": "ニュートラル",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "質問内容をそのまま確認する標準的な声色。",
    },
    {
        "id": "expressive",
        "label": "抑揚多め",
        "friendly": 1.1,
        "calm": 0.9,
        "tension": 1.45,
        "description": "確認の意図が伝わりやすい、少し抑揚のある声色。",
    },
    {
        "id": "soft",
        "label": "柔らかい",
        "friendly": 1.4,
        "calm": 1.2,
        "tension": 0.9,
        "description": "相手が答えやすい、角の立たない質問。",
    },
    {
        "id": "other",
        "label": "その他",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "7項目を個別に調整します。",
    },
]

APOLOGY_VOICE_PRESETS = [
    {
        "id": "neutral",
        "label": "Neutral",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "謝罪文を標準的に伝える声色。",
    },
    {
        "id": "calm",
        "label": "落ち着き",
        "friendly": 0.9,
        "calm": 1.5,
        "tension": 0.8,
        "description": "慌てず、落ち着いて謝意を伝える声色。",
    },
    {
        "id": "apologetic",
        "label": "申し訳なさそうに",
        "friendly": 0.8,
        "calm": 1.45,
        "tension": 0.75,
        "description": "少し抑えめで、申し訳なさが伝わる声色。",
    },
    {
        "id": "other",
        "label": "その他",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "7項目を個別に調整します。",
    },
]

GRATITUDE_VOICE_PRESETS = [
    {
        "id": "neutral",
        "label": "Neutral",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "感謝を標準的に伝える声色。",
    },
    {
        "id": "soft",
        "label": "柔らかく",
        "friendly": 1.4,
        "calm": 1.2,
        "tension": 0.9,
        "description": "穏やかで、あたたかく感謝を伝える声色。",
    },
    {
        "id": "lively",
        "label": "テンション高く",
        "friendly": 1.3,
        "calm": 0.85,
        "tension": 1.55,
        "description": "明るく、うれしさが伝わる声色。",
    },
    {
        "id": "other",
        "label": "その他",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "7項目を個別に調整します。",
    },
]

SMALLTALK_VOICE_PRESETS = [
    {
        "id": "neutral",
        "label": "Neutral",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "雑談を標準的に話す声色。",
    },
    {
        "id": "soft",
        "label": "柔らかく",
        "friendly": 1.4,
        "calm": 1.2,
        "tension": 0.9,
        "description": "相手が返しやすい、やわらかい声色。",
    },
    {
        "id": "lively",
        "label": "テンション高く",
        "friendly": 1.25,
        "calm": 0.85,
        "tension": 1.55,
        "description": "明るく、会話を広げやすい声色。",
    },
    {
        "id": "other",
        "label": "その他",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "7項目を個別に調整します。",
    },
]

ACCEPTANCE_VOICE_PRESETS = [
    {
        "id": "neutral",
        "label": "Neutral",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "承諾を標準的に伝える声色。",
    },
    {
        "id": "calm",
        "label": "落ち着き",
        "friendly": 1.0,
        "calm": 1.45,
        "tension": 0.85,
        "description": "安心して任せられる印象の承諾。",
    },
    {
        "id": "soft",
        "label": "柔らかい",
        "friendly": 1.35,
        "calm": 1.15,
        "tension": 0.9,
        "description": "角を立てず、受け止める承諾。",
    },
    {
        "id": "other",
        "label": "その他",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "7項目を個別に調整します。",
    },
]

REQUEST_VOICE_PRESETS = [
    {
        "id": "neutral",
        "label": "Neutral",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "依頼内容を標準的に伝える声色。",
    },
    {
        "id": "soft",
        "label": "柔らかい",
        "friendly": 1.4,
        "calm": 1.2,
        "tension": 0.9,
        "description": "相手に負担を感じさせにくい依頼。",
    },
    {
        "id": "clear",
        "label": "はっきり",
        "friendly": 1.0,
        "calm": 1.05,
        "tension": 1.25,
        "description": "お願いする行動が伝わりやすい声色。",
    },
    {
        "id": "other",
        "label": "その他",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "7項目を個別に調整します。",
    },
]

REQUEST_TECHNIQUE_ORDER = [
    "hedge",
    "purpose",
    "consideration",
]

REQUEST_TECHNIQUE_LABELS = {
    "hedge": "ヘッジ",
    "purpose": "目的の提示",
    "consideration": "配慮",
}

REQUEST_TECHNIQUE_DEFS = {
    "hedge": (
        "要求を直接言い切らず、「恐れ入りますが」「もしよろしければ」など、"
        "相手への圧を弱める表現を入れる。"
    ),
    "purpose": (
        "なぜお願いするのかを短く示す。"
        "例：「ご本人様確認のため」「正確にご案内するため」。"
    ),
    "consideration": (
        "相手の負担に配慮する表現を入れる。"
        "例：「お手数ですが」「少しだけ」「ご無理のない範囲で」。"
    ),
}


REQUEST_TEXT_VARIANTS = {
    "very_formal": {
        "easy": {
            "short": "こちらにご記入くださいませ。",
            "middle": "こちらにご記入をお願いいたします。",
            "long": "こちらの欄にご記入をお願いいたします。",
        },
        "middle": {
            "short": "ご記入をお願いいたします。",
            "middle": "こちらにご記入をお願いいたします。",
            "long": "こちらの欄にご記入をお願いいたします。",
        },
        "hard": {
            "short": "ご記入をお願いいたします。",
            "middle": "こちらの項目にご記入をお願いいたします。",
            "long": "こちらの必要項目にご記入をお願いいたします。",
        },
    },
    "formal": {
        "easy": {
            "short": "こちらにご記入ください。",
            "middle": "こちらにご記入をお願いします。",
            "long": "こちらの欄にご記入をお願いします。",
        },
        "middle": {
            "short": "ご記入をお願いします。",
            "middle": "こちらにご記入をお願いします。",
            "long": "こちらの欄にご記入をお願いします。",
        },
        "hard": {
            "short": "ご記入をお願いします。",
            "middle": "こちらの項目にご記入をお願いします。",
            "long": "こちらの必要項目にご記入をお願いします。",
        },
    },
    "polite": {
        "easy": {
            "short": "ここに書いてください。",
            "middle": "こちらに書いてください。",
            "long": "こちらの欄に書いてください。",
        },
        "middle": {
            "short": "記入をお願いします。",
            "middle": "こちらに記入をお願いします。",
            "long": "こちらの欄に記入をお願いします。",
        },
        "hard": {
            "short": "ご記入ください。",
            "middle": "こちらの項目にご記入ください。",
            "long": "こちらの必要項目にご記入ください。",
        },
    },
    "casual": {
        "easy": {
            "short": "ここに書いて。",
            "middle": "ここに書いてくれる？",
            "long": "ここの欄に書いてくれる？",
        },
        "middle": {
            "short": "記入してね。",
            "middle": "ここに記入してね。",
            "long": "ここの欄に記入してね。",
        },
        "hard": {
            "short": "ここに記入して。",
            "middle": "この項目に記入してね。",
            "long": "この必要項目に記入してね。",
        },
    },
}


REQUEST_HEDGE_TEXT = {
    "very_formal": "恐れ入りますが、",
    "formal": "恐れ入りますが、",
    "polite": "すみませんが、",
    "casual": "よければ、",
}

REQUEST_CONSIDERATION_TEXT = {
    "very_formal": "お手数をおかけいたしますが、",
    "formal": "お手数をおかけしますが、",
    "polite": "お手数ですが、",
    "casual": "悪いんだけど、",
}

REQUEST_COMBINED_SOFTENER_TEXT = {
    "very_formal": "恐れ入りますが、",
    "formal": "恐れ入りますが、",
    "polite": "お手数ですが、",
    "casual": "悪いんだけど、",
}

REQUEST_PURPOSE_TEXT = {
    "very_formal": "確認のため、",
    "formal": "確認のため、",
    "polite": "確認のため、",
    "casual": "確認したいので、",
}

REQUEST_TEXT_VARIANTS["light_casual"] = REQUEST_TEXT_VARIANTS["polite"]
REQUEST_HEDGE_TEXT["light_casual"] = REQUEST_HEDGE_TEXT["polite"]
REQUEST_CONSIDERATION_TEXT["light_casual"] = REQUEST_CONSIDERATION_TEXT["polite"]
REQUEST_COMBINED_SOFTENER_TEXT["light_casual"] = REQUEST_COMBINED_SOFTENER_TEXT["polite"]
REQUEST_PURPOSE_TEXT["light_casual"] = REQUEST_PURPOSE_TEXT["casual"]


def get_request_softener_text(politeness_id, intimacy_id, has_hedge, has_consideration):
    """
    要求時の前置き表現を返す。
    hedge と consideration を両方ONにしても、
    「恐れ入りますが、お手数ですが、」のように重ねすぎない。
    """
    if not has_hedge and not has_consideration:
        return ""

    key = politeness_id
    if key not in REQUEST_HEDGE_TEXT:
        key = "formal"

    if intimacy_id == "high" and key == "casual":
        return REQUEST_COMBINED_SOFTENER_TEXT["casual"]

    if has_hedge and has_consideration:
        return REQUEST_COMBINED_SOFTENER_TEXT[key]

    if has_hedge:
        return REQUEST_HEDGE_TEXT[key]

    return REQUEST_CONSIDERATION_TEXT[key]


def get_request_purpose_text(politeness_id, intimacy_id):
    key = politeness_id
    if key not in REQUEST_PURPOSE_TEXT:
        key = "formal"

    if intimacy_id == "high" and key == "casual":
        return REQUEST_PURPOSE_TEXT["casual"]

    return REQUEST_PURPOSE_TEXT[key]


def apply_request_techniques_to_text(base_text, selected_techniques, politeness_id, intimacy_id):
    """
    要求文に、要求時専用テクニックを反映する。
    """
    selected = set(selected_techniques)

    softener = get_request_softener_text(
        politeness_id=politeness_id,
        intimacy_id=intimacy_id,
        has_hedge=("hedge" in selected),
        has_consideration=("consideration" in selected),
    )

    purpose = ""
    if "purpose" in selected:
        purpose = get_request_purpose_text(politeness_id, intimacy_id)

    return f"{softener}{purpose}{base_text}"

FILLER_VOICE_PRESETS = [
    {
        "id": "neutral",
        "label": "Neutral",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "自然に間をつなぐ標準的な声色。",
    },
    {
        "id": "thinking",
        "label": "考え中",
        "friendly": 1.0,
        "calm": 1.25,
        "tension": 0.8,
        "description": "少し考えている印象の声色。",
    },
    {
        "id": "soft",
        "label": "柔らかい",
        "friendly": 1.3,
        "calm": 1.15,
        "tension": 0.9,
        "description": "会話の流れを止めにくい柔らかい声色。",
    },
    {
        "id": "other",
        "label": "その他",
        "friendly": 1.0,
        "calm": 1.0,
        "tension": 1.0,
        "description": "7項目を個別に調整します。",
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
    "rich_emotion": "感情を少し強めに表現する。「本当に」「とても助かります」など、感謝や喜びが伝わる一文にする。",
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
    "rich_emotion": "感情豊か",
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
    ("time_topic",): "お仕事帰りでしょうか？",
    ("consideration",): "もしよろしければ、ゆっくりご案内します。",
    ("seasonal_topic", "time_topic"): "今日は過ごしやすい気候ですね。お仕事帰りでしょうか？",
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
    ("time_topic",): "お帰りですか？",
    ("consideration",): "ごゆっくりどうぞ。",
    ("seasonal_topic", "time_topic"): "いい気候ですね。お帰りですか？",
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
        "high": "こんにちは、いらっしゃいませぇ。",
    },
    "casual": {
        "low": "こんにちは。",
        "middle": "こんにちは。",
        "high": {
            "nozomi": "こんにちはぁ。",
            "kenta": "こんにちはっす。",
        },
    },
}

GREETING_NEED_SENTENCE = {
    "very_formal": {
        "easy": {
            "low": "本日は何をお探しでしょうか？",
            "middle": "本日は何をお探しでしょうか？",
            "high": "本日は何をお探しでしょうか？",
        },
        "middle": {
            "low": "本日はどのようなご用件でしょうか？",
            "middle": "本日はどのようなご用件でしょうか？",
            "high": "本日はどのようなご用件でしょうか？",
        },
        "hard": {
            "low": "本日はどのようなご相談やお探し物がございますか？",
            "middle": "本日はどのようなご相談やお探し物がございますか？",
            "high": "本日はどのようなご相談やお探し物がございますか？",
        },
    },
    "formal": {
        "easy": {
            "low": "今日は何をお探しでしょうか？",
            "middle": "今日は何をお探しでしょうか？",
            "high": "今日は何をお探しでしょうか？",
        },
        "middle": {
            "low": "今日はどのようなご用件でしょうか？",
            "middle": "今日はどのようなご用件でしょうか？",
            "high": "今日はどのようなご用件でしょうか？",
        },
        "hard": {
            "low": "今日はどのようなご相談やお探し物でしょうか？",
            "middle": "今日はどのようなご相談やお探し物でしょうか？",
            "high": "今日はどのようなご相談やお探し物でしょうか？",
        },
    },
    "polite": {
        "easy": {
            "low": "今日は何をお探しですか？",
            "middle": "今日は何をお探しですか？",
            "high": "今日は何をお探しですかぁっ？",
        },
        "middle": {
            "low": "今日はどのような用件でしょうか？",
            "middle": "今日はどのようなご用件でしょうか？",
            "high": "今日はどのようなご用件でしょうかぁっ？",
        },
        "hard": {
            "low": "今日はどのようなご相談やお探し物でしょうか？",
            "middle": "今日はどのようなご相談やお探し物でしょうか？",
            "high": "今日はどのようなご相談やお探し物でしょうかぁっ？",
        },
    },
    "casual": {
        "easy": {
            "low": "何を探してる？",
            "middle": "何を探してるの？",
            "high": {
                "nozomi": "何を探してるのぉっ？",
                "kenta": "何を探してるんすか？",
            },
        },
        "middle": {
            "low": "今日はどうした？",
            "middle": "今日はどうしたの？",
            "high": {
                "nozomi": "今日はどうしたのぉっ？",
                "kenta": "今日はどうしたんすか？",
            },
        },
        "hard": {
            "low": "今日はどんな相談？",
            "middle": "今日はどんな相談なの？",
            "high": {
                "nozomi": "今日はどんな相談なのぉっ？",
                "kenta": "今日はどんな相談っすか？",
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

GREETING_OPENING_TEXT["light_casual"] = GREETING_OPENING_TEXT["polite"]
GREETING_NEED_SENTENCE["light_casual"] = GREETING_NEED_SENTENCE["polite"]
GREETING_LONG_EXTRA["light_casual"] = "よければ、一緒に確認しながら案内します。"

EXPLANATION_DEFAULT_TEXT = "チェックアウトは11時となっております。"

QUESTION_DEFAULT_TEXT = "本日は一泊でよろしいでしょうか？"

ACCEPTANCE_DEFAULT_TEXT = "かしこまりました。"

REQUEST_DEFAULT_TEXT = "こちらにご記入をお願いいたします。"

APOLOGY_DEFAULT_TEXT = "申し訳ございません。"

GRATITUDE_DEFAULT_TEXT = "ありがとうございます。"

SMALLTALK_DEFAULT_TEXT = "今日は過ごしやすいですね。"

FILLER_OPTIONS = [
    {"id": "sou_desu_ne", "label": "そうですね"},
    {"id": "etto", "label": "えっと"},
    {"id": "ano", "label": "あの"},
    {"id": "maa", "label": "まあ"},
    {"id": "sou_desu_nee", "label": "そうですねえ"},
]

APOLOGY_TECHNIQUE_ORDER = [
    "alternative",
    "empathy",
    "positive_reframe",
]

GRATITUDE_TECHNIQUE_ORDER = [
    "name_call",
    "rich_emotion",
]

EXPLANATION_TECHNIQUE_ORDER = [
    "empathy",
    "evidence",
    "expertise",
    "paraphrase",
    "summary",
    "step_by_step",
    "proactive",
    "goal_clarity",
    "permission",
]

EXPLANATION_TECHNIQUE_SENTENCES = {
    "empathy": "朝のお支度で慌ただしいですよね。",
    "evidence": "清掃と次のお客様の準備があるためです。",
    "expertise": "館内運用上、レイトチェックアウト枠とは別に管理しています。",
    "paraphrase": "つまり、11時までにお部屋を出ていただく形です。",
    "summary": "まとめると、チェックアウト時刻は11時です。",
    "step_by_step": "まずお荷物をまとめて、11時までにフロントへお越しください。",
    "proactive": "延長をご希望の場合は、空き状況をこちらで確認できます。",
    "goal_clarity": "チェックアウトの時間についてご案内します。",
    "permission": "先にチェックアウト時間をお伝えしてもよろしいでしょうか？",
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
