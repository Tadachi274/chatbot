# chatbot/robot_style_editor/response_delay_player.py

import threading
import time
from pathlib import Path

from chatbot.tts.tts_audioplayer import AudioPlayer
from .wav_silence import trim_silence_to_temp_wav


class ResponseDelayPlayer:
    def __init__(self):
        self.player = AudioPlayer(autoremove=False)
        self._stop = threading.Event()
        self._thread = None

    def schedule_response(self, wav_path: Path, delay_sec: float):
        wav_path = Path(wav_path)

        if not wav_path.exists():
            raise FileNotFoundError(f"WAV file not found: {wav_path}")

        self.stop()

        self._stop.clear()
        self._thread = threading.Thread(
            target=self._worker,
            args=(wav_path, float(delay_sec)),
            daemon=True,
        )
        self._thread.start()

    def _worker(self, wav_path: Path, delay_sec: float):
        temp_path = None

        try:
            start = time.monotonic()
            while time.monotonic() - start < delay_sec:
                if self._stop.is_set():
                    return
                time.sleep(0.01)

            if self._stop.is_set():
                return

            temp_path = trim_silence_to_temp_wav(wav_path)
            self.player.play_later(temp_path)

        finally:
            # AudioPlayerが再生中の可能性があるので、ここでは即削除しない
            # 必要ならAudioPlayer側のdone_eventで削除する設計にする
            pass

    def stop(self):
        self._stop.set()

        try:
            self.player.stop_current()
        except Exception:
            pass

    def cleanup(self):
        self.stop()

        try:
            self.player.stop()
        except Exception:
            pass