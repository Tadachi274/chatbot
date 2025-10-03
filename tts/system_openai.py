import os
import json
from pathlib import Path
from datetime import datetime
from openai import OpenAI  # tts_voicevoxからtts_openaiに変更
import test_chatbot as chatbot
import string_to_file
import sys
from dotenv import load_dotenv
 
CONFIG_PATH = "voice_config_openai.json"
TTS_SERVER = "openai"  # Assuming this is the TTS server you want to use

# ---------- OpenAI API 設定 ----------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("環境変数 OPENAI_API_KEY が設定されていません。")
client = OpenAI(api_key=api_key)
MODEL = "gpt-4o-mini"

# ---------- Config Load/Save ----------
def load_config(path=CONFIG_PATH):
    file = Path(path)
    if file.exists():
        with open(file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        # OpenAI TTS用のデフォルト設定に変更
        return {
            "instructions": "",
            "gpt_system": ""
        }

def save_config(config, path=CONFIG_PATH):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

# ---------- OpenAI Function 定義 ----------
function_definitions = [
    {
        "name": "update_voice_config",
        "description": "ユーザーの指示をもとに voice_config_openai.json の gpt_systemとinstructions を更新する。",
        "parameters": {
            "type": "object",
            "properties": {
                "gpt_system": {"type": "string", "description":"話す内容、話し方を指定するシステムメッセージ。"},
                "instructions": {"type": "string", "description": "OpenAI TTSへの指示プロンプト。話し方、トーン、感情、ペースなどを詳細に記述する。"}
            },
            "required": ["instructions", "gpt_system"]
        }
    }
]

# ---------- Config 更新 via OpenAI ----------
def llm_update_config(user_request: str, config: dict) -> dict:
    # OpenAI TTSのinstructionsとgpt_systemを更新するようにプロンプトを変更
    print(f"Current config: {json.dumps(config, ensure_ascii=False, indent=2)}")
    messages = [
        {"role": "system", "content": "あなたは voice_config_openai.json の `gpt_system` と `instructions` を編集するアシスタントです。ユーザーの要望に基づき、応答内容を規定する `gpt_system` と、TTSの話し方を規定する `instructions` の両方を更新してください。"},
        {"role": "user", "content": f""""
         
        You are given the following configuration:
        ### GPT System Prompt (Response style):
        {config.get('gpt_system', '')}

        ### TTS Instructions (Speaking style):
        {config.get('instructions', '')}

        A user has made the following comment or request:
        "{user_request}"

        If the user comment includes only feedback such as a problem (e.g. "The speed is too slow", "It's hard to understand"), rephrase it into an English request that reflects the intended improvement (e.g. "Please speak faster", "Please make it easier to understand").

        If the comment is already a request, just use it as is.

        Do not add any extra content beyond what the user requested.Do not include any additional information or context.

        Then, generate a **new GPT system prompt and new TTS instructions** that incorporate the user's request.

        Please write prompts in English.
         """
         }
        
    ]
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        functions=function_definitions,
        function_call={"name": "update_voice_config"}
    )
    choice = response.choices[0]
    message = choice.message
    if hasattr(message, 'function_call') and message.function_call:
        fc = message.function_call
        args = json.loads(fc.arguments)
        if 'instructions' in args:
            config['instructions'] = args['instructions'].strip()
        if 'gpt_system' in args:
            config['gpt_system'] = args['gpt_system'].strip()
    return config

# ---------- 対話ループ ----------
def interactive_loop():
    before_config = load_config()
    print("=== OpenAI 動的設定編集モード ===")
    while True:
        try:
            # req = input('[コマンド] 変更内容を入力 (Ctrl+Cで終了): ')
            req = """#### 1\. 声の調子（音声表現の調整）

*   **声のトーン**：少し高めで明るい調子にする → 落ち着いたが元気さを感じる声を意識
*   **話すスピード**：通常よりややゆっくり → 聞き取りやすさを確保
*   **間の取り方**：文と文の間に0.5～1秒程度のポーズを置く → 相手が理解・反応しやすい

#### 2\. 言葉選び（語彙・表現の調整）

*   **難しい言葉の回避**：専門用語や略語は避け、日常的な言葉で言い換える
*   **具体的な表現**：「こちらの商品」より「この赤い袋のお菓子」など視覚的・具体的に伝える
*   **丁寧さ**：「〜してください」より「〜していただけますか？」など、依頼は丁寧に

#### 3\. 会話構造（話し方の進め方）

*   **一文を短く区切る**：長い説明を避け、2〜3文でまとめる
*   **確認を入れる**：「ここまでで大丈夫ですか？」など理解を確認する問いを適度に挟む
*   **復唱・要約**：相手の言葉を繰り返す、要点をまとめることで安心感を与える

#### 4\. 非言語的な工夫（必要に応じて）

*   **声色の変化**：重要な部分でやや強調して抑揚をつける
*   **笑い声や相槌**：「そうですね」「はい」など相槌を多めにする → 共感と安心感を演出"""
        except KeyboardInterrupt:
            print("\nCtrl+C を検知しました。サーバーを終了します。")
            # 現在の設定ファイルをタイムスタンプ付きでバックアップ
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            config_file = Path(CONFIG_PATH)
            backup_path = config_file.parent / f"{config_file.stem}_{ts}{config_file.suffix}"
            config_file.replace(backup_path)
            # 空のデフォルト設定で新規作成
            save_config(
                {"gpt_system": "", "instructions": ""},
                CONFIG_PATH
            )
            print(f"バックアップを作成しました: {backup_path}")
            print(f"{CONFIG_PATH} をリセットしました。")
            break
        after_config = llm_update_config(req, before_config)
        save_config(after_config)
        string_to_file.StringFile(1).add_config(
            str(before_config), req, str(after_config) # 文字列に変換
        )
        print('[更新後設定]', json.dumps(after_config, ensure_ascii=False, indent=2))
        print('サンプル発話を実行します...')
        chatbot.run(CONFIG_PATH,TTS_SERVER)

if __name__ == '__main__':
    interactive_loop()


