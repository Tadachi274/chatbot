import threading
from pathlib import Path
from datetime import datetime
from queue import Queue, Empty
import pygame
import logging 
import time
import simpleaudio as sa
import wave

class AudioPlayer:
    def __init__(self, autoremove=True):
        self.q = Queue()
        self._th = threading.Thread(target=self._worker, name="AudioPlayer")
        self._th.daemon = True         # 終了まで確実に生かす
        self._stop = threading.Event()
        self.autoremove = autoremove      # 再生後に一時WAVを削除する
        
        pygame.mixer.init()
        self._th.start()

    def _get_wav_duration(self, wav_path: Path) -> float:
        with wave.open(str(wav_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate <= 0:
                return 0.0
            return frames / float(rate)

    def play_later(self, wav_path: Path, 
                   done_event: threading.Event | None = None,
                   near_end_sec: float | None = None,
                   near_end_callback=None,
                   ):
        """WAVファイルのパスをキューに積む（非ブロッキング）"""
        self.q.put((wav_path, done_event, near_end_sec, near_end_callback))

    def _worker(self):
        while not self._stop.is_set():
            try:
                wav_path, done_event, near_end_sec, near_end_callback = self.q.get(timeout=0.2)
            except Empty:
                continue

            near_end_timer = None

            try:
                duration = self._get_wav_duration(wav_path)
                print(f"[AudioPlayer] playstart {wav_path} duration={duration:.3f}s")

                # 終了2秒前通知
                if near_end_callback is not None and near_end_sec is not None:
                    fire_after = max(0.0, duration - near_end_sec)
                    near_end_timer = threading.Timer(fire_after, near_end_callback)
                    near_end_timer.daemon = True
                    near_end_timer.start()

                pygame.mixer.music.load(str(wav_path))
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.05)
                print(f"[AudioPlayer] finish playing {time.monotonic()}")
                pygame.mixer.music.stop()
                try:
                    pygame.mixer.music.unload()
                except pygame.error:
                    pass
            except Exception as e:
                print(f"[AudioPlayer] playback error: {e}")
            finally:
                if near_end_timer is not None:
                    near_end_timer.cancel()
                if done_event is not None:
                    done_event.set()
                if self.autoremove:
                    try:
                        wav_path.unlink(missing_ok=True)
                    except Exception as e:
                        logging.warning(f"unlink error: {e}")
                self.q.task_done()

    def stop_current(self):
        try:
            pygame.mixer.music.stop()
            try:
                pygame.mixer.music.unload()
            except pygame.error:
                pass
        except Exception as e:
            logging.warning(f"stop_current error: {e}")

    def stop(self):
        """アプリ終了時に呼ぶ。キュー消化後に停止"""
        self.q.join()
        self._stop.set()
        self._th.join(timeout=10)