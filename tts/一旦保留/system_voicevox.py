import os  # CHANGED: import os to read API key
import json
from pathlib import Path
from datetime import datetime
import requests
import pyaudio
import time
from openai import OpenAI  # Use v1 client import
import tts.一旦保留.tts_voicevox as tts  # Assuming tts_openai is a custom module for TTS
import test_chatbot as chatbot  # Assuming test_chatbot is a custom module for chatbot functionality
import string_to_file  # Assuming string_to_file is a custom module for logging

CONFIG_PATH = "voice_config1.json"
TTS_SERVER = "voicevox"  # Assuming this is the TTS server you want to use

# ---------- OpenAI API 設定 ----------
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
        return {
            "gpt_system": "",
            "voicevox": {
                "speedScale": 1.0,
                "pitchScale": 0.0,
                "intonationScale": 1.0,
                "volumeScale": 1.0,
                "prePhonemeLength": 0.1,
                "postPhonemeLength": 0.1
            }
        }

def save_config(config, path=CONFIG_PATH):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

# ---------- OpenAI Function 定義 ----------
function_definitions = [
    {
        "name": "update_voice_config",
        "description": "ユーザーの指示をもとに voice_config.json を更新する。pitchScale: 0.1が最も明るく、0.0が通常であることを前提とする。",
        "parameters": {
            "type": "object",
            "properties": {
                "gpt_system": {"type": "string"},
                "voicevox": {
                    "type": "object",
                    "properties": {
                        "speedScale": {"type": "number"},
                        "pitchScale": {"type": "number", "description": "0.10が最も明るく、0.00が通常"},  # Added description
                        "intonationScale": {"type": "number"},
                        "volumeScale": {"type": "number"},
                        "prePhonemeLength": {"type": "number"},
                        "postPhonemeLength": {"type": "number"}
                    }
                }
            }
        }
    }
]

# ---------- Config 更新 via OpenAI ----------
def llm_update_config(user_request: str, config: dict) -> dict:
    # CHANGED: system prompt includes pitchScale semantics
    messages = [
        {"role": "system", "content": "あなたは voice_config.json の編集アシスタントです。pitchScaleの値は0.10が最も明るく、0.00が通常であることを認識してください。"},
        {"role": "user", "content": f"現在の設定は{json.dumps(config)}なので、指示 {user_request}と組み合わせて voice_config.json を更新してください。"},
        {"role": "user", "content": f"現在の話し方は{json.dumps(config['gpt_system'])}であり、指示 {user_request}と組み合わせてvoice_config.jsonのgpt_systemも更新してください"}
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
        print(f"with arguments: {args} ")
        if 'gpt_system' in args:
            config['gpt_system'] = args['gpt_system'].strip()
        if 'voicevox' in args:
            for k, v in args['voicevox'].items():
                if k == 'pitchScale':
                    if isinstance(v, (int, float)) and v <= 0.1:
                        config['voicevox'][k] = v
                    else:
                        continue
                else:
                    config.setdefault('voicevox', {})[k] = v
    return config

# ---------- Speech Function ----------
def speak_async(text: str, config: dict):
    res1 = requests.post(
        'http://127.0.0.1:50021/audio_query',
        params={'text': text, 'speaker': 2}
    )
    query = res1.json()
    for key, val in config.get('voicevox', {}).items():
        if key in query:
            query[key] = val
    res2 = requests.post(
        'http://127.0.0.1:50021/synthesis',
        params={'speaker': 2},
        data=json.dumps(query),
        headers={'Content-Type': 'application/json'}
    )
    audio = res2.content
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)
    time.sleep(0.2)
    print(f"playsound: {datetime.now()}")
    stream.write(audio)
    stream.stop_stream()
    stream.close()
    p.terminate()

# ---------- 対話ループ ----------
def interactive_loop():
    before_config = load_config()
    print("=== OpenAI 動的設定編集モード ===")
    while True:
        try:
            req = input('[コマンド] 変更内容を入力 (Ctrl+Cで終了): ')
        except KeyboardInterrupt:
            print("\nCtrl+C を検知しました。サーバーを終了します。")
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            config_file = Path(CONFIG_PATH)
            backup_path = config_file.parent / f"{config_file.stem}_{ts}{config_file.suffix}"
            config_file.replace(backup_path)
            # 空のデフォルト設定で新規作成
            save_config(
                {
                    "gpt_system": "",
                    "voicevox": {
                        "speedScale": 1.0,
                        "pitchScale": 0.1,
                        "intonationScale": 1.5,
                        "volumeScale": 1.5,
                        "prePhonemeLength": 0.1,
                        "postPhonemeLength": 0.1
                    }
                },
                CONFIG_PATH
            )
            print(f"バックアップを作成しました: {backup_path}")
            print(f"{CONFIG_PATH} をリセットしました。")
            break
        after_config = llm_update_config(req, before_config)
        save_config(after_config)
        string_to_file.StringFile(1).add_config(
            before_config, req, after_config
        )
        print('[更新後設定]', json.dumps(after_config, ensure_ascii=False, indent=2))
        print('サンプル発話を実行します...')
        chatbot.run(CONFIG_PATH,TTS_SERVER)

if __name__ == '__main__':
    interactive_loop()


