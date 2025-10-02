import requests
import json
import pyaudio
import time
from pathlib import Path
from datetime import datetime

def speak_async(
    response="私の名前はずんだもんです。東北地方の応援マスコットをしています。得意なことはしゃべることです。",
    config_path="voice_config.json"
):
    text = response

    # クエリの初期作成
    res1 = requests.post(
        'http://127.0.0.1:50021/audio_query',
        params={'text': text, 'speaker': 2}
    )
    query = res1.json()

    # JSONファイルからパラメータを読み込んで上書き
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        # voicevox設定が含まれている場合は反映
        if "voicevox" in config:
            voicevox_config = config["voicevox"]
            for key, value in voicevox_config.items():
                if key in query:
                    query[key] = value
        else:
            print("⚠ 'voicevox'設定が見つかりません。")
            
    else:
        print(f"⚠ 設定ファイル {config_path} が見つかりません。デフォルト設定で進行します。")

    # 音声合成データの作成
    res2 = requests.post(
        'http://127.0.0.1:50021/synthesis',
        params={'speaker': 1},
        data=json.dumps(query),
        headers={"Content-Type": "application/json"}
    )
    data = res2.content

    # 音声の再生
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=24000,
                    output=True)
    time.sleep(0.2)
    print(f"playsound:{datetime.now()}")
    stream.write(data)
    stream.stop_stream()
    stream.close()
    p.terminate()

if __name__ == "__main__":
    print("play_sound")
    speak_async()
    

    