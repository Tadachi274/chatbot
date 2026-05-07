import os
import threading
from pathlib import Path
from datetime import datetime
import json
import atexit
import requests 
from .tts_audioplayer import AudioPlayer

DEFAULT_AUTOREMOVE = True
_player = None
_player_autoremove = None
print(f"AUTO_REMOVE:{DEFAULT_AUTOREMOVE}")

def _get_player(autoremove: bool):
    global _player, _player_autoremove

    if _player is None or _player_autoremove != autoremove:
        if _player is not None:
            try:
                _player.stop()
            except Exception:
                pass

        _player = AudioPlayer(autoremove=autoremove)
        _player_autoremove = autoremove

    return _player

## 非同期音声合成
def speak_async(
    text: str,
    *,
    config_path: str | None = None,
    instructions: dict | None = None,
    autoremove: bool = DEFAULT_AUTOREMOVE,
    url: str,
    play: bool = True,
    near_end_sec: float = 2.0,
    near_end_callback=None,
):
    done_event = threading.Event()
    thread = threading.Thread(
        target=_synthesize_and_enqueue,
        args=(text,),
        kwargs={
            "config_path": config_path,
            "instructions" : instructions,
            "url": url,
            "autoremove":autoremove,
            "play": play,
            "done_event": done_event,
            "near_end_sec": near_end_sec,
            "near_end_callback": near_end_callback,
        },
        name="TTSWorker",
    )
    thread.daemon = True
    thread.start()
    return thread, done_event


def _synthesize_and_enqueue(
    text: str,
    config_path: str,
    instructions: str,
    url: str,
    autoremove:bool,
    play: bool = True,
    done_event=None,
    near_end_sec: float = 2.0,
    near_end_callback=None,
):
    wav_path = synthesize_to_wav(text, config_path, instructions, url)
    _get_player(autoremove)
    if play:
        _player.play_later(
            wav_path,
            done_event=done_event,
            near_end_sec=near_end_sec,
            near_end_callback=near_end_callback,
        )
    return wav_path

def play_wav(
    wav_path: Path,
    *,
    autoremove: bool= DEFAULT_AUTOREMOVE,
    done_event=None,
    near_end_sec: float = 2.0,
    near_end_callback=None,
):
    _get_player(autoremove)
    _player.play_later(
        wav_path,
        done_event=done_event,
        near_end_sec=near_end_sec,
        near_end_callback=near_end_callback,
    )

def synthesize_to_wav(
    text: str,
    config_path: str | None,
    instructions: dict | None,
    url:str
) -> Path:
    # 設定読み込み
    if instructions is None:
        cfg = Path(config_path)
        with cfg.open("r", encoding="utf-8") as f:
            config = json.load(f)
        instructions = config.get("instructions")
    # print(instructions)
    data = {
        "text": text,
        **instructions 
    }

    # TTSリクエスト
    response =  requests.post(url, json=data, timeout=30)
    response.raise_for_status()
    raw_audio = response.content

    #
    wav_path = make_tts_filename(instructions, prefix="tts_nikola") 
    wav_path.write_bytes(raw_audio)

    return wav_path


@atexit.register
def _shutdown_audio():
    global _player
    if _player is not None:
        try:
            _player.stop()
        except Exception:
            pass

## 
DEFAULTS = {
    "tts_volume": 1.3,    
    "tts_rate": 1.0,          
    "tts_pitch": 1.0,       
    "tts_emphasis": 1.0,     
    "tts_emo_joy": 0.0,       
    "tts_emo_angry": 0.0,     
    "tts_emo_sad": 0.0
}

def make_tts_filename(instructions: dict, prefix="tts")-> Path:
    BASE_DIR = Path(__file__).parent.resolve()
    temp_dir = (BASE_DIR / "temp_audio")
    temp_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S%f")
    parts = []

    for k,v in instructions.items():
        default_v = DEFAULTS.get(k)
        if default_v is None or abs(v - default_v) > 1e-6:
            key = k.replace("tts_","")
            key1 = key.replace("emo_","")
            parts.append(f"{key1}{v}")

    if parts:
        name = f"{prefix}_{ts}_{'_'.join(parts)}.wav"
    else:
        name = f"{prefix}_default_{ts}.wav"
    wav_path = temp_dir / name
    
    return wav_path
