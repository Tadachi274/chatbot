import os
import threading
from pathlib import Path
from datetime import datetime
import json
import atexit
from queue import Queue, Empty
import platform
import subprocess
import shutil

import openai
# simpleaudio is optional; we will prefer afplay on macOS to avoid segfaults
try:
    import simpleaudio as sa
except Exception:
    sa = None
from pydub import AudioSegment

# APIキーの読み込み
openai.api_key = os.getenv("OPENAI_API_KEY")

def speak_async(text: str, **kwargs):
    """
    非同期で音声合成を行う
    """
    thread = threading.Thread(target=_synthesize_and_enqueue, args=(text,), kwargs=kwargs, name="TTSWorker")
    thread.daemon = False
    thread.start()
    return thread

def _synthesize_and_enqueue(
    text: str,
    config_path: str,
    model: str = "gpt-4o-mini-tts",
    voice: str = "alloy",
    play: bool = True
):
    wav_path = _synthesize_to_wav(text, config_path, model=model, voice=voice)
    if play:
        _player.play_later(wav_path)   # 非同期で再生
    return wav_path

def _synthesize_to_wav(
    text: str,
    config_path: str,
    model: str = "gpt-4o-mini-tts",
    voice: str = "alloy",
) -> Path:
    temp_dir = Path("temp_audio")
    temp_dir.mkdir(exist_ok=True)

    # Use a filename safe for macOS (no spaces/colons)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    raw_path = temp_dir / f"tts_{ts}.bin"
    wav_path = raw_path.with_suffix(".wav")

    # 設定読み込み
    instructions = None
    cfg = Path(config_path)
    if cfg.exists():
        with cfg.open("r", encoding="utf-8") as f:
            config = json.load(f)
        instructions = config.get("instructions")

    # TTS（SDKがformat無視する可能性があるため一旦.binで受ける）
    response = openai.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        instructions=instructions,
        # format="wav",
    )
    response.stream_to_file(raw_path)

    # ヘッダで判定→WAVへ
    filetype = _detect_audio_type(raw_path)
    if filetype == "wav":
        raw_path.replace(wav_path)
    elif filetype == "mp3":
        audio = AudioSegment.from_file(raw_path, format="mp3")
        audio.export(wav_path, format="wav")
        raw_path.unlink(missing_ok=True)
    else:
        audio = AudioSegment.from_file(raw_path)
        audio.export(wav_path, format="wav")
        raw_path.unlink(missing_ok=True)

    return wav_path


def _detect_audio_type(path: Path) -> str:
    with path.open("rb") as f:
        head = f.read(12)
    if head.startswith(b"RIFF"):
        return "wav"
    if head.startswith(b"ID3"):
        return "mp3"
    if len(head) >= 2 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0:
        return "mp3"
    return "unknown"

class AudioPlayer:
    def __init__(self, autoremove=True):
        self.q = Queue()
        self._th = threading.Thread(target=self._worker, name="AudioPlayer")
        self._th.daemon = False           # 終了まで確実に生かす
        self._stop = threading.Event()
        self.autoremove = autoremove      # 再生後に一時WAVを削除するか

        # Prefer afplay on macOS to avoid simpleaudio segfaults
        self._afplay = shutil.which("afplay") if platform.system() == "Darwin" else None
        prefer_simple = os.getenv("USE_SIMPLEAUDIO", "0") == "1"
        if prefer_simple and sa is not None:
            self._backend = "simpleaudio"
        elif self._afplay:
            self._backend = "afplay"
        elif sa is not None:
            self._backend = "simpleaudio"
        else:
            self._backend = "afplay"  # will fail clearly if not present

        self._th.start()

    def play_later(self, wav_path: Path):
        """WAVファイルのパスをキューに積む（非ブロッキング）"""
        self.q.put(wav_path)

    def _worker(self):
        while not self._stop.is_set():
            try:
                wav_path = self.q.get(timeout=0.2)
            except Empty:
                continue
            try:
                print(f"playsound:{datetime.now()}")
                if self._backend == "afplay":
                    # Blocking until playback finishes
                    subprocess.run([self._afplay, str(wav_path)], check=False)
                else:
                    wave_obj = sa.WaveObject.from_wave_file(str(wav_path))
                    play_obj = wave_obj.play()
                    play_obj.wait_done()
            except Exception as e:
                print(f"[AudioPlayer] playback error: {e}")
            finally:
                if self.autoremove:
                    try:
                        wav_path.unlink(missing_ok=True)
                    except Exception:
                        pass
                self.q.task_done()

    def stop(self):
        """アプリ終了時に呼ぶ。キュー消化後に停止"""
        self.q.join()
        self._stop.set()
        self._th.join()

# グローバルなプレイヤー（プロセス中1つ）
_player = AudioPlayer(autoremove=True)

@atexit.register
def _shutdown_audio():
    try:
        _player.stop()
    except Exception:
        pass
