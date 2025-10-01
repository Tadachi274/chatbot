import os
import threading
import uuid
from pathlib import Path
from datetime import datetime
import json

import openai
from pydub import AudioSegment
from playsound import playsound
from simpleaudio import WaveObject, PlayObject

# APIキーの読み込み
openai.api_key = os.getenv("OPENAI_API_KEY")

def _synthesize(text: str, config_path: str, model: str = "tts-1", voice: str = "alloy",  play: bool = True):
    # 一時ファイル名の生成
    temp_dir = Path("temp_audio")
    temp_dir.mkdir(exist_ok=True)

    mp3_path = temp_dir / f"tts_{uuid.uuid4().hex}.mp3"
    wav_path = mp3_path.with_suffix(".wav")

    # 設定ファイルの読み込み
    instructions = None
    config_file = Path(config_path)
    if config_file.exists():
        with open(config_file, "r", encoding="utf-8") as f:
            config = json.load(f)
        if "instructions" in config:
            instructions = config["instructions"]
        else:
            print("⚠ 'instructions' not found in config.")
    else:
        print(f"⚠ Config file {config_path} not found. Proceeding with default settings.")


    # TTS リクエスト
    response = openai.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice=voice,
        input=text,
        instructions=instructions
    )

    # MP3 ファイルに保存
    response.stream_to_file(mp3_path)

    # MP3 → WAV に変換
    audio_segment = AudioSegment.from_mp3(str(mp3_path)) # mp3_pathを文字列に変換
    audio_segment.export(str(wav_path), format="wav") # wav_pathを文字列に変換

    # 音声再生
    if play:
        print(f"playsound:{datetime.now()}")
        playsound(str(wav_path)) # wav_pathを文字列に変換

    return wav_path # 保存したWAVファイルのパスを返す

def speak_async(text: str, **kwargs):
    """
    非同期で音声合成を行う
    """
    thread = threading.Thread(target=_synthesize, args=(text,), kwargs=kwargs)
    thread.start()
    return thread

def save_audio(text: str, output_path: str, config_path: str, **kwargs):
    """
    音声合成を行い、指定されたパスに保存する
    """
    kwargs.pop('output_path', None) # output_pathはsynthesizeに渡さない
    # 音声は生成するが、ここでは再生しない
    wav_path = _synthesize(text, config_path,**kwargs, play=False)
    if wav_path:
        Path(output_path).parent.mkdir(exist_ok=True, parents=True)
        # ファイルを移動
        os.rename(str(wav_path), output_path) # wav_pathを文字列に変換
        print(f"Audio saved to {output_path}")
        # 移動後に再生
        print(f"playsound:{datetime.now()}")
        playsound(output_path)

