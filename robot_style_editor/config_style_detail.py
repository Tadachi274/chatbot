STYLE_DETAIL_SECTIONS = [
    {
        "key": "information_structure",
        "label": "情報構造",
        "mode": "multi",
        "options": [
            {
                "id": "conclusion_first",
                "label": "結論先出し",
                "description": "先に答えや要点を伝えてから補足する。",
                "prompt": "結論や要点を先に述べ、その後で必要な補足を入れる。",
            },
            {
                "id": "reason",
                "label": "理由提示",
                "description": "判断や案内の理由を短く添える。",
                "prompt": "判断や案内には、必要に応じて短い理由を添える。",
            },
            {
                "id": "step_by_step",
                "label": "手順化",
                "description": "複数の行動を順番に分けて伝える。",
                "prompt": "手続きや複数の行動は、順番が分かるように段階的に伝える。",
            },
        ],
    },
    {
        "key": "information_amount",
        "label": "情報量",
        "mode": "single",
        "default": "standard",
        "options": [
            {
                "id": "brief",
                "label": "簡潔",
                "description": "要点を優先し、補足は最小限にする。",
                "prompt": "情報量は簡潔にし、必要な要点を優先して伝える。",
            },
            {
                "id": "standard",
                "label": "標準",
                "description": "要点と最低限の補足を自然に入れる。",
                "prompt": "情報量は標準にし、要点と自然な補足のバランスを取る。",
            },
            {
                "id": "detailed",
                "label": "詳細",
                "description": "相手が迷わないよう補足を多めにする。",
                "prompt": "情報量は詳細にし、相手が迷わないように必要な補足を入れる。",
            },
        ],
    },
    {
        "key": "emotional_expression",
        "label": "感情表出",
        "mode": "single",
        "default": "standard",
        "options": [
            {
                "id": "low",
                "label": "少なめ",
                "description": "感情語や共感語を控えめにする。",
                "prompt": "感情語や共感語は控えめにし、落ち着いた表現にする。",
            },
            {
                "id": "standard",
                "label": "標準",
                "description": "必要な場面で自然に共感を入れる。",
                "prompt": "感情語や共感語は標準的にし、必要な場面で自然に入れる。",
            },
            {
                "id": "high",
                "label": "多め",
                "description": "嬉しさ、安心、共感などを言葉に出しやすくする。",
                "prompt": "感情語や共感語を多めにし、嬉しさ・安心・共感を言葉で示す。",
            },
        ],
    },
    {
        "key": "interpersonal_consideration",
        "label": "対人的配慮",
        "mode": "multi",
        "options": [
            {
                "id": "hedge",
                "label": "ヘッジ",
                "description": "断定を少し和らげる。「ちょっと」「〜かもしれません」「〜と思われます」などのヘッジ表現を入れる。",
                "prompt": "断定を少し和らげ、必要に応じて「ちょっと」「かもしれません」「と思います」などを使う。",
            },
            {
                "id": "permission",
                "label": "許可取り",
                "description": "行動や説明の前に確認を入れる。「～してもよろしいでしょうか？」",
                "prompt": "行動や説明の前に、必要に応じて許可や確認を取る。「～してもよろしいでしょうか？」",
            },
            {
                "id": "burden_reduction",
                "label": "負担軽減",
                "description": "相手の負担を減らす言い方や提案を入れる。",
                "prompt": "相手の負担が軽くなるよう、手間や不安を減らす表現を入れる。",
            },
        ],
    },
    {
        "key": "initiative",
        "label": "主導性",
        "mode": "multi",
        "options": [
            {
                "id": "proactive_suggestion",
                "label": "先回り提案",
                "description": "相手が次に必要としそうな情報を先に出す。",
                "prompt": "相手が次に必要としそうな情報や選択肢を先回りして提案する。",
            },
            {
                "id": "next_action",
                "label": "次行動の提示",
                "description": "次に何をすればよいか明確に伝える。",
                "prompt": "会話の終わりや手続きの節目で、次に何をすればよいかを明確に伝える。",
            },
        ],
    },
]


STYLE_DETAIL_DEFAULTS = {
    "information_structure": [],
    "information_amount": "standard",
    "emotional_expression": "standard",
    "interpersonal_consideration": [],
    "initiative": [],
}


def get_style_detail_option(section_key, option_id):
    for section in STYLE_DETAIL_SECTIONS:
        if section["key"] != section_key:
            continue
        for option in section["options"]:
            if option["id"] == option_id:
                return option
    return None
