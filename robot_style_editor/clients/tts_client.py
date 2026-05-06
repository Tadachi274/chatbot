import threading
import wave
import time
import re
import shutil
from datetime import datetime
from pathlib import Path
from uuid import uuid4

from ..config import TTS_URL, DEFAULT_INSTRUCTIONS, TTS_GENERATED_WAV_DIR
from chatbot.tts import tts_nikola_data as tts
from chatbot.tts.tts_audioplayer import AudioPlayer
from ..audio.wav_silence import trim_silence_to_temp_wav

class TTSClient:
    def __init__(self, url=TTS_URL):
        self.url = url

        # UIで使うWAVプレビュー用。
        # 事前音声は消したくないので autoremove=False
        self.preview_player = AudioPlayer(autoremove=False)

        self._preview_stop = threading.Event()
        self._preview_thread = None

    def speak(self, text: str, instructions: dict | None = None, person: str | None = None):
        text = text.strip()
        if not text:
            return None

        merged = {
            **DEFAULT_INSTRUCTIONS,
            **(instructions or {}),
        }

        resolved_person = person or merged.get("tts_speaker_change") or tts.DEFAULT_PERSON

        if resolved_person is None:
            return tts.speak_async(
                text=text,
                instructions=merged,
                url=self.url,
            )

        return tts.speak_async(
            text=text,
            instructions=merged,
            url=self.url,
            person=resolved_person,
        )

    def change_speaker_and_speak(self, text: str, speaker: str):
        instructions = {
            **DEFAULT_INSTRUCTIONS,
            "tts_speaker_change": speaker,
        }

        return self.speak(
            text=text,
            instructions=instructions,
            person=speaker,
        )

    def speak_current_speaker(self, text: str, instructions: dict | None = None):
        return self.speak(
            text=text,
            instructions=instructions or DEFAULT_INSTRUCTIONS,
        )

    def synthesize_to_wav(
        self,
        text: str,
        instructions: dict | None = None,
        person: str | None = None,
        output_dir: Path | None = TTS_GENERATED_WAV_DIR,
    ):
        text = text.strip()
        if not text:
            return None

        merged = {
            **DEFAULT_INSTRUCTIONS,
            **(instructions or {}),
        }
        resolved_person = person or merged.get("tts_speaker_change") or tts.DEFAULT_PERSON

        wav_path = tts._synthesize_to_wav(
            text=text,
            instructions=merged,
            url=self.url,
            person=resolved_person,
        )

        if output_dir is None:
            return wav_path

        return self.move_generated_wav(wav_path, text, resolved_person, output_dir)

    def move_generated_wav(self, wav_path: Path, text: str, person: str, output_dir: Path):
        wav_path = Path(wav_path)
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        safe_text = re.sub(r"[\\/:*?\"<>|\\s]+", "_", text).strip("_")
        safe_text = safe_text[:32] or "tts"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        target = output_dir / f"{timestamp}_{uuid4().hex[:8]}_{person}_{safe_text}.wav"

        if wav_path.resolve() == target.resolve():
            return target

        try:
            shutil.move(str(wav_path), str(target))
        except Exception:
            shutil.copy2(str(wav_path), str(target))
            try:
                wav_path.unlink(missing_ok=True)
            except Exception:
                pass

        return target

    # =========================
    # WAVプレビュー再生
    # =========================

    def play_wav_pair_with_pause(self, wav1: Path, wav2: Path, pause_sec: float, on_pause_start=None):
        """
        wav1を再生 → pause_sec待つ → wav2を再生。
        文間ポーズ確認用。
        """
        wav1 = Path(wav1)
        wav2 = Path(wav2)

        if not wav1.exists():
            raise FileNotFoundError(f"WAV file not found: {wav1}")

        if not wav2.exists():
            raise FileNotFoundError(f"WAV file not found: {wav2}")

        self.stop_preview()

        self._preview_stop.clear()
        self._preview_thread = threading.Thread(
            target=self._play_wav_pair_worker,
            args=(wav1, wav2, float(pause_sec), on_pause_start),
            daemon=True,
        )
        self._preview_thread.start()

    def _play_wav_pair_worker(self, wav1: Path, wav2: Path, pause_sec: float, on_pause_start=None):
        temp_paths = []

        try:
            trimmed_wav1 = trim_silence_to_temp_wav(wav1)
            trimmed_wav2 = trim_silence_to_temp_wav(wav2)

            temp_paths.extend([trimmed_wav1, trimmed_wav2])

            event1 = threading.Event()
            event2 = threading.Event()

            self.preview_player.play_later(trimmed_wav1, done_event=event1)

            while not event1.is_set():
                if self._preview_stop.is_set():
                    self.preview_player.stop_current()
                    return
                time.sleep(0.01)

            start = time.monotonic()
            while time.monotonic() - start < pause_sec:
                if self._preview_stop.is_set():
                    return
                time.sleep(0.01)

            if self._preview_stop.is_set():
                return
            
            if on_pause_start is not None:
                on_pause_start()

            self.preview_player.play_later(trimmed_wav2, done_event=event2)

            while not event2.is_set():
                if self._preview_stop.is_set():
                    self.preview_player.stop_current()
                    return
                time.sleep(0.01)

        finally:
            for path in temp_paths:
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass

    def play_preview_wav(self, wav_path: Path, trim: bool = True):
        wav_path = Path(wav_path)

        if not wav_path.exists():
            raise FileNotFoundError(f"WAV file not found: {wav_path}")

        self.stop_preview()

        temp_path = None
        play_path = wav_path

        if trim:
            temp_path = trim_silence_to_temp_wav(wav_path)
            play_path = temp_path

        done_event = threading.Event()
        self.preview_player.play_later(play_path, done_event=done_event)

        if temp_path is not None:
            def cleanup():
                done_event.wait()
                try:
                    temp_path.unlink(missing_ok=True)
                except Exception:
                    pass

            threading.Thread(target=cleanup, daemon=True).start()  

    def stop_preview(self):
        self._preview_stop.set()

        try:
            self.preview_player.stop_current()
        except Exception:
            pass

    def get_wav_duration_sec(self, wav_path):
        wav_path = Path(wav_path)

        with wave.open(str(wav_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()

        return frames / float(rate) 
    
    def play_preview_wav_trimmed_and_get_duration(self, wav_path, buffer_cleanup_sec=0.3):
        """
        WAVの前後無音をtrimしてからプレビュー再生し、
        trim後WAVの長さを返す。

        相槌再生中にマイク認識を一時停止する時間を決めるために使う。
        """
        wav_path = Path(wav_path)

        if not wav_path.exists():
            raise FileNotFoundError(f"WAV file not found: {wav_path}")

        trimmed_path = trim_silence_to_temp_wav(wav_path)
        duration = self.get_wav_duration_sec(trimmed_path)

        # すでにtrim済みなので、ここではtrim=False
        self.play_preview_wav(trimmed_path, trim=False)

        def cleanup():
            # 再生が終わるくらいまで待ってから一時ファイルを削除
            try:
                import time
                time.sleep(duration + buffer_cleanup_sec)
                trimmed_path.unlink(missing_ok=True)
            except Exception:
                pass

        threading.Thread(target=cleanup, daemon=True).start()

        return duration

    def cleanup(self):
        self.stop_preview()

        try:
            self.preview_player.stop()
        except Exception:
            pass
