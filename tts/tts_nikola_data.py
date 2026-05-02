import threading
from pathlib import Path
from datetime import datetime
import atexit
import requests
from .tts_audioplayer import AudioPlayer

DEFAULT_AUTOREMOVE = True
DEFAULT_PERSON = "nozomi_emo_22_standard"
_player = None
_player_autoremove = None


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


def speak_async(
    text: str,
    instructions: dict,
    url: str,
    autoremove: bool = DEFAULT_AUTOREMOVE,
    person: str = DEFAULT_PERSON,
):
    """robot_console.py から呼び出す想定のメイン関数"""
    thread = threading.Thread(
        target=_synthesize_and_enqueue,
        args=(text, instructions, url, autoremove, person),
        name="TTSWorker"
    )
    thread.daemon = True
    thread.start()
    return thread


def _synthesize_and_enqueue(text, instructions, url, autoremove, person):
    wav_path = _synthesize_to_wav(text, instructions, url, person)

    player = _get_player(autoremove)
    player.play_later(wav_path)
    return wav_path


def _synthesize_to_wav(text, instructions, url, person) -> Path:
    data = {
        "text": text,
        **instructions
    }

    response = requests.post(url, json=data, timeout=30)
    response.raise_for_status()
    raw_audio = response.content

    wav_path = make_tts_filename(text, instructions, person)
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


DEFAULTS = {
    "tts_volume": 1.3,
    "tts_rate": 1.0,
    "tts_pitch": 1.0,
    "tts_emphasis": 1.0,
    "tts_emo_joy": 0.0,
    "tts_emo_angry": 0.0,
    "tts_emo_sad": 0.0
}


def make_tts_filename(text, instructions: dict, person) -> Path:
    BASE_DIR = Path(__file__).parent.resolve()
    temp_dir = (BASE_DIR / "filler" / person)
    temp_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    parts = []

    for k, v in instructions.items():
        default_v = DEFAULTS.get(k)
        if default_v is None or abs(v - default_v) > 1e-6:
            key = k.replace("tts_", "")
            key1 = key.replace("emo_", "")
            parts.append(f"{key1}{v}")

    if parts:
        name = f"{text}_{ts}_{'_'.join(parts)}.wav"
    else:
        name = f"{text}_default_{ts}.wav"

    wav_path = temp_dir / name
    return wav_path