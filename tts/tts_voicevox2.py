import requests
import json
import pyaudio
import wave
import os
from pathlib import Path
from datetime import datetime
from playsound import playsound
import time


def speak_async(
    response: str = "私の名前はずんだもんです。東北地方の応援マスコットをしています。得意なことはしゃべることです。",
    config_path: str = "voice_config.json",
    speaker: int = 1
):
    """
    VoiceVox の audio_query と synthesis を用いて非同期再生を行います。
    """
    text = response

    # --- audio_query の作成 ---
    res1 = requests.post(
        'http://127.0.0.1:50021/audio_query',
        params={'text': text, 'speaker': speaker}
    )
    query = res1.json()

    # 設定ファイルからパラメータを上書き
    cfg = Path(config_path)
    if cfg.exists():
        with open(cfg, "r", encoding="utf-8") as f:
            config = json.load(f)
        if "voicevox" in config:
            for k, v in config["voicevox"].items():
                if k in query:
                    query[k] = v
    else:
        print(f"⚠ 設定ファイル {config_path} が見つかりません。デフォルト設定で進行します。")

    # --- synthesis 実行 ---
    res2 = requests.post(
        'http://127.0.0.1:50021/synthesis',
        params={'speaker': speaker},
        data=json.dumps(query),
        headers={"Content-Type": "application/json"}
    )
    pcm_data = res2.content

    # 再生
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=24000,
        output=True
    )
    time.sleep(0.2)
    print(f"playsound:{datetime.now()}")
    stream.write(pcm_data)
    stream.stop_stream()
    stream.close()
    p.terminate()


def save_audio(
    text: str,
    output_path: str,
    config_path: str = "voice_config.json",
    speaker: int = 1
):
    """
    音声を合成して WAV ファイルとして保存し、再生します。
    """
    # --- audio_query の作成 ---
    res1 = requests.post(
        'http://127.0.0.1:50021/audio_query',
        params={'text': text, 'speaker': speaker}
    )
    query = res1.json()

    # 設定ファイルからパラメータを上書き
    cfg = Path(config_path)
    if cfg.exists():
        with open(cfg, "r", encoding="utf-8") as f:
            config = json.load(f)
        if "voicevox" in config:
            for k, v in config["voicevox"].items():
                if k in query:
                    query[k] = v
    else:
        print(f"⚠ 設定ファイル {config_path} が見つかりません。デフォルト設定で進行します。")

    # --- synthesis 実行 ---
    res2 = requests.post(
        'http://127.0.0.1:50021/synthesis',
        params={'speaker': speaker},
        data=json.dumps(query),
        headers={"Content-Type": "application/json"}
    )
    pcm_data = res2.content

    # 出力先ディレクトリの作成
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # WAV ファイルとして書き込み
    with wave.open(str(out_path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(24000)
        wf.writeframes(pcm_data)

    print(f"Audio saved to {output_path}")
    # 再生
    playsound(str(out_path))


if __name__ == "__main__":
    # サンプル実行: テキストを 'output.wav' に保存して再生
    sample_text = "こんにちは、VoiceVox でテキストを音声に変換します。"
    save_audio(sample_text, "output.wav")
