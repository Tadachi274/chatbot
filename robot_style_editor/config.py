from pathlib import Path

TTS_URL = 'http://192.168.0.169:15001/synthesize'

BASE_DIR = Path(__file__).resolve().parent

PROFILE_PATH = BASE_DIR / "robot_speech_profile.json"

PERSON = [
    "nozomi_emo_22_standard",
    "kenta_emo_22_standard",
]

DEFAULT_INSTRUCTIONS = {
    "tts_volume": 1.3,
    "tts_rate": 1.0,
    "tts_pitch": 1.0,
    "tts_emphasis": 1.0,
    "tts_emo_joy": 0,
    "tts_emo_angry": 0,
    "tts_emo_sad": 0,
}

POLITENESS_OPTIONS = [
    {
        "id": "very_formal",
        "label": "尊敬語・謙譲語",
        "short": "かなり丁寧",
        "example1": "本日はどのようなご用件でございますか。",
        "example2": "恐れ入りますが、ご本人様確認のため、身分証明書を拝見してもよろしいでしょうか。",
        "prompt": (
            "尊敬語・謙譲語を多く使い、かなり丁寧で改まった話し方にしてください。"
            "例：「本日はどのようなご用件でございますか。」"
            "「恐れ入りますが、ご本人様確認のため、身分証明書を拝見してもよろしいでしょうか。」"
        ),
    },
    {
        "id": "formal",
        "label": "軽い尊敬語",
        "short": "丁寧で自然",
        "example1": "本日はどのようなご用件でしょうか。",
        "example2": "ご本人様確認のため、身分証明書を確認させていただいてもよろしいでしょうか。",
        "prompt": (
            "軽い尊敬語を使い、丁寧だが堅すぎない自然な話し方にしてください。"
            "例：「本日はどのようなご用件でしょうか。」"
            "「ご本人様確認のため、身分証明書を確認させていただいてもよろしいでしょうか。」"
        ),
    },
    {
        "id": "polite",
        "label": "丁寧語",
        "short": "標準的",
        "example1": "今日はどのような用件でしょうか。",
        "example2": "確認のため、身分証明書を見せてもらえますか。",
        "prompt": (
            "です・ますを中心にした標準的な丁寧語で話してください。"
            "尊敬語や謙譲語は必要以上に使わないでください。"
            "例：「今日はどのような用件でしょうか。」"
            "「確認のため、身分証明書を見せてもらえますか。」"
        ),
    },
    {
        "id": "casual",
        "label": "カジュアル",
        "short": "親しみやすい",
        "example1": "今日はどうしたの？",
        "example2": "確認したいから、身分証明書を見せてもらってもいい？",
        "prompt": (
            "カジュアルで親しみやすい話し方にしてください。"
            "敬語は弱め、友好的でやわらかい表現にしてください。"
            "例：「今日はどうしたの？」"
            "「確認したいから、身分証明書を見せてもらってもいい？」"
        ),
    },
    {
        "id": "other",
        "label": "その他",
        "short": "自由入力",
        "example1": "",
        "example2": "",
        "prompt": "",
    },
]

INTIMACY_OPTIONS_BY_PERSON_AND_POLITENESS = {
    "nozomi": {
        "very_formal": [
            {
                "id": "low",
                "label": "低",
                "example1": "本日はどのようなご用件でございますか。",
                "example2": "恐れ入りますが、身分証明書を拝見してもよろしいでしょうか。",
                "prompt": (
                    "親しみは低めにしてください。"
                    "距離感を保ち、落ち着いた丁寧な話し方にしてください。"
                    "語尾を伸ばしたり、砕けた表現は使わないでください。"
                ),
            },
            {
                "id": "middle",
                "label": "中",
                "example1": "本日はどのようなご用件でしょうか。",
                "example2": "よろしければ、身分証明書を確認させていただけますか。",
                "prompt": (
                    "親しみは中程度にしてください。"
                    "丁寧さは保ちながら、少し柔らかく話しかけやすい表現にしてください。"
                ),
            },
            {
                "id": "high",
                "label": "高",
                "example1": "本日はどのようなご用件でしょうか〜？",
                "example2": "すみません〜、確認のために身分証明書を見せていただけますか？",
                "prompt": (
                    "親しみは高めにしてください。"
                    "丁寧さは残しつつ、語尾に伸ばし棒などを使い、柔らかく親しげな話し方にしてください。"
                    "話者がのぞみの場合は、少しやわらかく、近い距離感の表現にしてください。"
                ),
            },
            {
                "id": "other",
                "label": "その他",
                "example1": "",
                "example2": "",
                "prompt": "",
            },
        ],
        "formal": [
            {
                "id": "low",
                "label": "低",
                "example1": "本日はどのようなご用件でしょうか。",
                "example2": "身分証明書を確認させていただいてもよろしいでしょうか。",
                "prompt": (
                    "親しみは低めにしてください。"
                    "丁寧で落ち着いた話し方にし、馴れ馴れしい表現は避けてください。"
                ),
            },
            {
                "id": "middle",
                "label": "中",
                "example1": "今日はどのようなご用件でしょうか。",
                "example2": "確認のため、身分証明書を見せていただけますか。",
                "prompt": (
                    "親しみは中程度にしてください。"
                    "丁寧さを保ちながら、少し話しかけやすい自然な表現にしてください。"
                ),
            },
            {
                "id": "high",
                "label": "高",
                "example1": "今日はどんなご用件ですか〜？",
                "example2": "確認したいので、身分証明書を見せてもらってもいいですか〜？",
                "prompt": (
                    "親しみは高めにしてください。"
                    "語尾に伸ばし棒などを使い、柔らかく親しげな話し方にしてください。"
                    "ただし接客として最低限の丁寧さは残してください。"
                ),
            },
            {
                "id": "other",
                "label": "その他",
                "example1": "",
                "example2": "",
                "prompt": "",
            },
        ],
        "polite": [
            {
                "id": "low",
                "label": "低",
                "example1": "今日はどのような用件でしょうか。",
                "example2": "確認のため、身分証明書を見せてもらえますか。",
                "prompt": (
                    "親しみは低めにしてください。"
                    "です・ます調を中心に、距離感を保った落ち着いた話し方にしてください。"
                ),
            },
            {
                "id": "middle",
                "label": "中",
                "example1": "今日はどうされましたか。",
                "example2": "確認したいので、身分証明書を見せてもらえますか。",
                "prompt": (
                    "親しみは中程度にしてください。"
                    "丁寧語を使いながら、少し柔らかく話しかけやすい表現にしてください。"
                ),
            },
            {
                "id": "high",
                "label": "高",
                "example1": "今日はどうしましたか〜？",
                "example2": "ちょっと確認したいので、身分証明書を見せてもらってもいいですか〜？",
                "prompt": (
                    "親しみは高めにしてください。"
                    "語尾に伸ばし棒などを使い、柔らかく親しげな話し方にしてください。"
                ),
            },
            {
                "id": "other",
                "label": "その他",
                "example1": "",
                "example2": "",
                "prompt": "",
            },
        ],
        "casual": [
            {
                "id": "low",
                "label": "低",
                "example1": "今日はどうした？",
                "example2": "確認したいから、身分証明書を見せてもらえる？",
                "prompt": (
                    "親しみは低めにしてください。"
                    "カジュアルではあるが、過度に馴れ馴れしくせず、落ち着いた話し方にしてください。"
                ),
            },
            {
                "id": "middle",
                "label": "中",
                "example1": "今日はどうしたの？",
                "example2": "確認したいから、身分証明書を見せてもらってもいい？",
                "prompt": (
                    "親しみは中程度にしてください。"
                    "カジュアルで話しかけやすいが、距離が近すぎない表現にしてください。"
                ),
            },
            {
                "id": "high",
                "label": "高",
                "example1": "今日はどうしたの〜？",
                "example2": "ちょっと確認したいから、身分証明書見せてもらってもいい〜？",
                "prompt": (
                    "親しみは高めにしてください。"
                    "語尾に伸ばし棒などを使い、かなり親しげで柔らかい話し方にしてください。"
                ),
            },
            {
                "id": "other",
                "label": "その他",
                "example1": "",
                "example2": "",
                "prompt": "",
            },
        ],
    },

    "kenta": {
        "very_formal": [
            {
                "id": "low",
                "label": "低",
                "example1": "本日はどのようなご用件でございますか。",
                "example2": "恐れ入りますが、身分証明書を拝見してもよろしいでしょうか。",
                "prompt": (
                    "親しみは低めにしてください。"
                    "距離感を保ち、落ち着いた丁寧な話し方にしてください。"
                    "砕けた表現は使わないでください。"
                ),
            },
            {
                "id": "middle",
                "label": "中",
                "example1": "本日はどのようなご用件でしょうか。",
                "example2": "よろしければ、身分証明書を確認させていただけますか。",
                "prompt": (
                    "親しみは中程度にしてください。"
                    "丁寧さを保ちながら、少し話しかけやすい表現にしてください。"
                ),
            },
            {
                "id": "high",
                "label": "高",
                "example1": "本日はどのようなご用件っすかね。",
                "example2": "すみません、確認のために身分証明書を見せていただきたいっす。",
                "prompt": (
                    "親しみは高めにしてください。"
                    "話者がけんたの場合は、「〜っすね」「〜っすか」など、接客場面で許容される範囲の砕けた表現を使ってください。"
                    "ただし乱暴な表現や失礼な表現にはしないでください。"
                ),
            },
            {
                "id": "other",
                "label": "その他",
                "example1": "",
                "example2": "",
                "prompt": "",
            },
        ],
        "formal": [
            {
                "id": "low",
                "label": "低",
                "example1": "本日はどのようなご用件でしょうか。",
                "example2": "身分証明書を確認させていただいてもよろしいでしょうか。",
                "prompt": (
                    "親しみは低めにしてください。"
                    "丁寧で落ち着いた話し方にし、砕けた表現は避けてください。"
                ),
            },
            {
                "id": "middle",
                "label": "中",
                "example1": "今日はどのようなご用件でしょうかね。",
                "example2": "確認のため、身分証明書を見せていただけますかね。",
                "prompt": (
                    "親しみは中程度にしてください。"
                    "丁寧さを保ちながら、少し話しかけやすい表現にしてください。"
                ),
            },
            {
                "id": "high",
                "label": "高",
                "example1": "今日はどんな用件っすか。",
                "example2": "確認したいので、身分証明書を見せてもらってもいいっすか。",
                "prompt": (
                    "親しみは高めにしてください。"
                    "「〜っすね」「〜っすか」など、店員らしく砕けた表現を使ってください。"
                    "ただし接客として最低限の丁寧さは残してください。"
                ),
            },
            {
                "id": "other",
                "label": "その他",
                "example1": "",
                "example2": "",
                "prompt": "",
            },
        ],
        "polite": [
            {
                "id": "low",
                "label": "低",
                "example1": "今日はどのような用件でしょうか。",
                "example2": "確認のため、身分証明書を見せてもらえますか。",
                "prompt": (
                    "親しみは低めにしてください。"
                    "です・ます調を中心に、距離感を保った落ち着いた話し方にしてください。"
                ),
            },
            {
                "id": "middle",
                "label": "中",
                "example1": "今日はどうされましたかね。",
                "example2": "確認したいので、身分証明書を見せてもらえますかね。",
                "prompt": (
                    "親しみは中程度にしてください。"
                    "丁寧語を使いながら、少し話しかけやすい表現にしてください。"
                ),
            },
            {
                "id": "high",
                "label": "高",
                "example1": "今日はどうしたんすか。",
                "example2": "ちょっと確認したいんで、身分証明書見せてもらってもいいっすか。",
                "prompt": (
                    "親しみは高めにしてください。"
                    "「〜っすね」「〜っすか」「〜なんすか」など、店員らしく砕けた表現を使ってください。"
                    "ただし乱暴な表現や失礼な表現にはしないでください。"
                ),
            },
            {
                "id": "other",
                "label": "その他",
                "example1": "",
                "example2": "",
                "prompt": "",
            },
        ],
        "casual": [
            {
                "id": "low",
                "label": "低",
                "example1": "今日はどうした？",
                "example2": "確認したいから、身分証明書を見せてもらえる？",
                "prompt": (
                    "親しみは低めにしてください。"
                    "カジュアルではあるが、距離感を保った落ち着いた話し方にしてください。"
                ),
            },
            {
                "id": "middle",
                "label": "中",
                "example1": "今日はどうしたの？",
                "example2": "確認したいから、身分証明書を見せてもらってもいい？",
                "prompt": (
                    "親しみは中程度にしてください。"
                    "カジュアルで話しかけやすいが、砕けすぎない表現にしてください。"
                ),
            },
            {
                "id": "high",
                "label": "高",
                "example1": "今日はどうしたの〜？",
                "example2": "確認したいから、身分証明書見せてもらってもいい〜？",
                "prompt": (
                    "親しみは高めにしてください。"
                    "「〜っすね」「〜っすか」など、店員らしく砕けた表現を使ってください。"
                ),
            },
            {
                "id": "other",
                "label": "その他",
                "example1": "",
                "example2": "",
                "prompt": "",
            },
        ],
    },
}

VOCABULARY_BASE_OPTIONS = [
    {
        "id": "easy",
        "label": "簡単",
        "example1_content": "甘くてふわふわなお菓子",
        "example2_content": "あちらの棚",
        "prompt": (
            "語彙は簡単にしてください。"
            "日常的でわかりやすい言葉を使い、短く直感的に伝えてください。"
        ),
    },
    {
        "id": "middle",
        "label": "中",
        "example1_content": "甘味が強く、口に入れるとふわっと溶けるようなお菓子",
        "example2_content": "入口から見て右側の棚",
        "prompt": (
            "語彙は中程度にしてください。"
            "一般的な接客で自然に使われる、少し具体的な表現にしてください。"
        ),
    },
    {
        "id": "hard",
        "label": "難しい",
        "example1_content": "上品な甘みと、ほどけるような軽い口どけが魅力のお菓子",
        "example2_content": "入口右手の陳列棚、中段の見やすい位置",
        "prompt": (
            "語彙は難しめにしてください。"
            "表現が具体的で、描写が豊かで、少し上品に感じられる言葉を使ってください。"
        ),
    },
    {
        "id": "other",
        "label": "その他",
        "example1_content": "",
        "example2_content": "",
        "prompt": "",
    },
]

VOCABULARY_STYLE_TEMPLATES = {
    "nozomi": {
        "very_formal": {
            "low": {
                "example1": "こちらは、{content}でございます。",
                "example2": "{content}にございます。",
            },
            "middle": {
                "example1": "こちらは、{content}でございますよ。",
                "example2": "{content}にございますよ。",
            },
            "high": {
                "example1": "こちらは、{content}でございます〜。",
                "example2": "{content}にございますよ〜。",
            },
        },
        "formal": {
            "low": {
                "example1": "こちらは、{content}です。",
                "example2": "{content}にあります。",
            },
            "middle": {
                "example1": "こちらは、{content}ですよ。",
                "example2": "{content}にありますよ。",
            },
            "high": {
                "example1": "こちら、{content}ですよ〜。",
                "example2": "{content}にありますよ〜。",
            },
        },
        "polite": {
            "low": {
                "example1": "こちらは、{content}です。",
                "example2": "{content}にあります。",
            },
            "middle": {
                "example1": "これは、{content}ですよ。",
                "example2": "{content}にありますよ。",
            },
            "high": {
                "example1": "これ、{content}ですよ〜。",
                "example2": "{content}にありますよ〜。",
            },
        },
        "casual": {
            "low": {
                "example1": "これは、{content}だよ。",
                "example2": "{content}にあるよ。",
            },
            "middle": {
                "example1": "これ、{content}だよ。",
                "example2": "{content}にあるよ。",
            },
            "high": {
                "example1": "これ、{content}だよ〜。",
                "example2": "{content}にあるよ〜。",
            },
        },
    },

    "kenta": {
        "very_formal": {
            "low": {
                "example1": "こちらは、{content}でございます。",
                "example2": "{content}にございます。",
            },
            "middle": {
                "example1": "こちらは、{content}でございますね。",
                "example2": "{content}にございますね。",
            },
            "high": {
                "example1": "こちら、{content}っすね。",
                "example2": "{content}にあるっすね。",
            },
        },
        "formal": {
            "low": {
                "example1": "こちらは、{content}です。",
                "example2": "{content}にあります。",
            },
            "middle": {
                "example1": "こちらは、{content}ですね。",
                "example2": "{content}にありますね。",
            },
            "high": {
                "example1": "こちら、{content}っすね。",
                "example2": "{content}にあるっすね。",
            },
        },
        "polite": {
            "low": {
                "example1": "こちらは、{content}です。",
                "example2": "{content}にあります。",
            },
            "middle": {
                "example1": "これは、{content}ですね。",
                "example2": "{content}にありますね。",
            },
            "high": {
                "example1": "これ、{content}っすね。",
                "example2": "{content}にあるっすね。",
            },
        },
        "casual": {
            "low": {
                "example1": "これは、{content}だよ。",
                "example2": "{content}にあるよ。",
            },
            "middle": {
                "example1": "これ、{content}だよね。",
                "example2": "{content}にあるよね。",
            },
            "high": {
                "example1": "これ、{content}っす。",
                "example2": "{content}にあるっす。",
            },
        },
    },
}

LENGTH_BASE_OPTIONS = [
    {
        "id": "short",
        "label": "短い",
        "example1": "閉店です。",
        "example2": "少々お待ちください。",
        "prompt": (
            "発話は短くしてください。"
            "現在選択されている敬語・親しみ・語彙の方針は維持したまま、"
            "同じ内容をできるだけ短く、必要最小限の言葉で伝えてください。"
            "理由、確認、提案、補足は必要以上に増やさないでください。"
        ),
    },
    {
        "id": "middle",
        "label": "中",
        "example1": "もうすぐ閉店時間です。",
        "example2": "少しだけお待ちいただけますか。",
        "prompt": (
            "発話は中くらいの長さにしてください。"
            "現在選択されている敬語・親しみ・語彙の方針は維持したまま、"
            "短すぎず長すぎない自然な一文で伝えてください。"
            "理由、確認、提案、補足は必要以上に増やさないでください。"
        ),
    },
    {
        "id": "long",
        "label": "長い",
        "example1": "当店はまもなく閉店のお時間となっております。",
        "example2": "恐れ入りますが、少しだけお待ちいただけますでしょうか。",
        "prompt": (
            "発話は長めにしてください。"
            "現在選択されている敬語・親しみ・語彙の方針は維持したまま、"
            "情報量を大きく増やすのではなく、同じ内容をやや余裕のある言い回しにしてください。"
            "ただし、提案・確認・理由説明を過剰に追加しないでください。"
        ),
    },
    {
        "id": "other",
        "label": "その他",
        "example1": "",
        "example2": "",
        "prompt": "",
    },
]

def get_person_key_from_speaker(speaker_id: str) -> str:
    if speaker_id.startswith("kenta"):
        return "kenta"
    if speaker_id.startswith("nozomi"):
        return "nozomi"
    return "nozomi"


def normalize_politeness_id(politeness_id: str) -> str:
    if politeness_id in ("very_formal", "formal", "polite", "casual"):
        return politeness_id
    return "formal"


def normalize_intimacy_id(intimacy_id: str) -> str:
    if intimacy_id in ("low", "middle", "high"):
        return intimacy_id
    return "middle"


def build_vocabulary_examples(person_key: str, politeness_id: str, intimacy_id: str, vocab_option: dict) -> tuple[str, str]:
    politeness_id = normalize_politeness_id(politeness_id)
    intimacy_id = normalize_intimacy_id(intimacy_id)

    templates = VOCABULARY_STYLE_TEMPLATES[person_key][politeness_id][intimacy_id]

    example1 = templates["example1"].format(
        content=vocab_option["example1_content"]
    )

    example2 = templates["example2"].format(
        content=vocab_option["example2_content"]
    )

    return example1, example2