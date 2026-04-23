# speaking_style_file.py
from pathlib import Path
import json

STYLE_STATE_PATH = Path("command/speaking_style_state.json")

DA_TYPES = [
    "OPENING",
    "STATEMENT",
    "OPINION",
    "QUESTION",
    "APOLOGY",
    "THANKING",
    "CLOSING",
    "ACCEPT",
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

DA_TECHNIQUE_MAP = {
    "OPENING": ["seasonal_topic", "time_topic", "consideration"],
    "STATEMENT": [
        "empathy",
        "evidence",
        "expertise",
        "paraphrase",
        "summary",
        "step_by_step",
        "proactive",
        "goal_clarity",
        "permission",
    ],
    "OPINION": ["self_disclosure", "positive_reframe", "hedge", "expertise"],
    "QUESTION": ["options"],
    "APOLOGY": ["alternative"],
    "THANKING": ["name_call"],
    "CLOSING": ["seasonal_topic", "time_topic", "consideration", "name_call"],
    "ACCEPT": ["confirmation", "clarification_question", "hypothesis"],
}

def load_style() -> dict:
    if not STYLE_STATE_PATH.exists():
        return {"neutral": 0, "base_style": {}, "da_techniques": {}}

    try:
        return json.loads(STYLE_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"neutral": 0, "base_style": {}, "da_techniques": {}}


def _base_style_lines(base: dict) -> list[str]:
    lines = []

    # politeness
    v = base.get("politeness", 0)
    if v == 1:
        lines.append("絶対に丁寧な敬語で話す。です・ます調を基本とし、「恐れ入りますが」「かしこまりました」などの表現を必ず含める。")
    elif v == -1:
        lines.append("絶対に敬語を弱め、常体またはカジュアルな口調で話す。です・ます調は極力使わない。")

    # length
    v = base.get("length", 0)
    if v == 1:
        lines.append("絶対にやや長めに話す。")
    elif v == -1:
        lines.append("絶対に短く簡潔に話す。余分な説明を削り、必要最低限の内容だけにする。")

    # vocabulary
    v = base.get("vocabulary", 0)
    if v == 1:
        lines.append("絶対にやや高度で洗練された語彙を使う。抽象語や専門語を積極的に用いる。")
    elif v == -1:
        lines.append("絶対にやさしく単純で分かりやすい語彙を使う。難しい言葉や専門語は避ける。")

    # friendliness
    v = base.get("friendliness", 0)
    if v == 1:
        lines.append("絶対に相手を既知の顧客として扱う。初対面の接客表現（いらっしゃいませ等）は使用せず、再来訪を前提とした挨拶に変換する。「お久しぶりです」「またのご利用ありがとうございます」などを必ず含め、距離の近い会話として開始する。")
    elif v == -1:
        lines.append("絶対に距離を保った話し方にする。馴れ馴れしい表現は避ける。")

    # emotion_strength
    v = base.get("emotion_strength", 0)
    if v == 1:
        lines.append("絶対に感情表現をやや強めにする。発話の冒頭で歓迎の感情を示し、その後に案内や質問を続ける。「お待ちしておりました」「お越しいいただきありがとうございます」などの歓迎表現は必ず文の最初に自然な形で入れる。文の途中や末尾に不自然に追加することは禁止する。")
    elif v == -1:
        lines.append("絶対に感情表現を抑え、淡々とした事務的な話し方にする。")

    return lines

def _enabled_da_techniques(da_techniques: dict, da_type: str) -> list[str]:
    da_dict = da_techniques.get(da_type, {})
    allowed = DA_TECHNIQUE_MAP.get(da_type, [])

    return [
        k for k in allowed
        if da_dict.get(k, 0) == 1 and k in TECHNIQUE_DEFS
    ]

def _da_instruction_lines(da_techniques: dict) -> list[str]:
    lines = []
    lines.append("【DAごとの技法】")
    lines.append("各文には必ず type を1つ付け、type に応じて使ってよい技法だけを使うこと。")
    lines.append("出力JSON以外は禁止。")
    lines.append("type は次のいずれかのみを使うこと:")
    lines.append(", ".join(DA_TYPES))
    lines.append("")

    for da in DA_TYPES:
        enabled = _enabled_da_techniques(da_techniques, da)
        
        print(f"[Speaking_style_file] enabled {enabled} ")
        if enabled:
            lines.append(f"- {da}:")
            for key in enabled:
                lines.append(f"  - {key}: {TECHNIQUE_DEFS[key]}")
        else:
            lines.append(f"- {da}: 有効な追加技法なし")

    

    return lines

def build_prompt(style: dict | None = None) -> str:
    if style is None:
        style = load_style()

    base = style.get("base_style", {})
    techniques = style.get("da_techniques", {})

    lines = []
    lines.append("以下の条件を守って応答を生成すること。")
    lines.append("応答は文ごとのJSON配列で出力すること。")
    lines.append('各要素は {"utterance": string, "type": da_type} の形式にすること。')
    lines.append("複数文の場合は必ず1文ごとに分割すること。")
    lines.append("1文に対して1つのtypeのみ付与すること。")
    lines.append("説明文、注釈、Markdown、コードブロックは禁止。")
    lines.append("utterance は自然な日本語の1文にすること。")
    lines.append("")

    if style.get("neutral", 0) == 1:
        lines.append("【base_style】")
        lines.extend(_base_style_lines(base))
        lines.append("")

    lines.extend(_da_instruction_lines(techniques))
    lines.append("")
    lines.append("必ずJSON配列のみを返すこと。")

    return "\n".join(lines)