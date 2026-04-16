# speaking_style_file.py
from pathlib import Path
import json

STYLE_STATE_PATH = Path("command/speaking_style_state.json")

def load_style() -> dict:
    if not STYLE_STATE_PATH.exists():
        return {"neutral": 0, "base_style": {}, "techniques": {}}

    try:
        return json.loads(STYLE_STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"neutral": 0, "base_style": {}, "techniques": {}}


def _base_style_lines(base: dict) -> list[str]:
    lines = []

    # politeness
    v = base.get("politeness", 0)
    if v == 1:
        lines.append(
            "絶対に丁寧な敬語で話す。です・ます調を基本とし、「恐れ入りますが」「かしこまりました」などの表現を必ず含める。"
        )
    elif v == -1:
        lines.append(
            "絶対に敬語を弱め、常体またはカジュアルな口調で話す。です・ます調は極力使わない。"
        )

    # length
    v = base.get("length", 0)
    if v == 1:
        lines.append(
            "絶対にやや長めに話す。理由や補足説明を一文以上追加する。"
        )
    elif v == -1:
        lines.append(
            "絶対に短く簡潔に話す。余分な説明を削り、必要最低限の内容だけにする。"
        )

    # vocabulary
    v = base.get("vocabulary", 0)
    if v == 1:
        lines.append(
            "絶対にやや高度で洗練された語彙を使う。抽象語や丁寧な言い換えを積極的に用いる。"
        )
    elif v == -1:
        lines.append(
            "絶対にやさしく単純で分かりやすい語彙を使う。難しい言葉や専門語は避ける。"
        )

    # friendliness
    v = base.get("friendliness", 0)
    if v == 1:
        lines.append(
           "絶対に相手を既知の顧客として扱う。初対面の接客表現（いらっしゃいませ等）は使用せず、再来訪を前提とした挨拶に変換する。「お久しぶりです」「またのご利用ありがとうございます」などを必ず含め、距離の近い会話として開始する。"
        )
    elif v == -1:
        lines.append(
            "絶対に距離を保った話し方にする。馴れ馴れしい表現は避ける。"
        )

    # emotion_strength
    v = base.get("emotion_strength", 0)
    if v == 1:
        lines.append(
           "絶対に感情表現をやや強めにする。発話の冒頭で歓迎の感情を示し、その後に案内や質問を続ける。「お待ちしておりました」「お越しいいただきありがとうございます」などの歓迎表現は必ず文の最初に自然な形で入れる。文の途中や末尾に不自然に追加することは禁止する。"
        )
    elif v == -1:
        lines.append(
            "絶対に感情表現を抑え、淡々とした事務的な話し方にする。"
        )

    return lines

def _enabled_technique_lines(techniques: dict) -> list[str]:
    defs = {
       "empathy": "相手の感情や状況を言語化し、絶対に共感を示す一文を入れる。「ご不安ですよね」などの形で必ず明示する。",        
       "consideration": "相手への配慮を絶対に入れる。負担を気遣う表現や「もしよろしければ」などの柔らかい言い回しを必ず含める。",        "seasonal_topic": "季節に関する話題を絶対に入れる。気温や天候、時期感（暑いですね、寒いですね等）に必ず一度触れる。",        
       "time_topic": "時間帯に関する話題を絶対に入れる。朝・昼・夜や「お仕事帰り」など、現在の時間状況に言及する。",
        "self_disclosure": "軽い自己開示を絶対に入れる。店員側の経験や傾向を一文だけ入れ、親しみを生む。",
        "evidence": "発言に対する理由や根拠を絶対に入れる。「なぜなら?」などで判断理由を明示する。",
        "expertise": "専門的な知識や用語を絶対に一つ以上入れる。ただし必要に応じて簡単な説明も添える。",
        "paraphrase": "一度述べた内容を別の言い方で絶対に言い換える。難しい表現の後に分かりやすい説明を続ける。",
        "summary": "相手の発言や状況を短くまとめる一文を絶対に入れる。「つまり?ということですね」などで整理する。",
        "step_by_step": "手順や説明を絶対に段階的に分ける。1ステップずつ順番に説明する形にする。",
        "initiative": "絶対に会話を主導する。相手に選択を委ねず、必要な行動をこちらが決定して提示する。「〜していただけますか」ではなく「〜をお願いいたします」「〜をご提示ください」など、指示・依頼の形で明確に伝える。",
        "confirmation": "内容確認の一文を絶対に入れる。「〜でよろしいでしょうか」などで認識の一致を確認する。",
        "clarification_question": "曖昧な点について絶対に質問する。不足情報を具体化する質問を一つ以上入れる。",
        "hypothesis": "相手の意図を推測し、絶対に仮説として提示する。「〜ということでしょうか」などで確認する。",
        "options": "複数の選択肢を絶対に提示する。最低でも2つの案とその違いを簡単に示す。",
        "proactive": "相手が次に必要としそうな情報や行動を先回りして、絶対に提案として入れる。",
        "goal_clarity": "会話の目的やゴールを最初または途中で絶対に明示する。「これから〜をご案内します」など。",
        "permission": "行動や説明の前に絶対に許可を取る。「よろしいでしょうか」といった確認を必ず入れる。",
        "alternative": "別の方法や代替案を絶対に提示する。現在の案に加えて他の選択肢も示す。",
        "positive_reframe": "否定的な状況でも絶対に前向きな言い方に変換する。メリットや良い面を必ず示す。",
        "name_call": "相手の名前が分かる前提で、絶対に名前を呼ぶ形の一文を入れる。",
        "closing": "発話の最後に絶対に締めの一言を入れる。感謝や案内の完了を示す。",
    }

    return [
        f"- {k}: {defs[k]}"
        for k, v in techniques.items()
        if v == 1 and k in defs
    ]


def build_prompt(style: dict | None = None) -> str:
    if style is None:
        style = load_style()

    # neutral=0 → プロンプトなし
    if style.get("neutral", 0) == 0:
        return ""

    base = style.get("base_style", {})
    techniques = style.get("techniques", {})

    lines = []
    lines.append("以下の話し方指定を絶対に守って発話してください。")
    lines.append("説明・注釈は禁止。最終発話のみ出力してください。")
    lines.append("")

    # base_style（全部）
    lines.append("【base_style】")
    lines.extend(_base_style_lines(base))

    # techniques（1だけ）
    enabled = _enabled_technique_lines(techniques)
    if enabled:
        lines.append("")
        lines.append("【techniques】以下は絶対に含めること")
        lines.extend(enabled)

    lines.append("")
    lines.append("すべての条件を可能な限り同時に満たすこと。")

    print("\n".join(lines))

    return "\n".join(lines)