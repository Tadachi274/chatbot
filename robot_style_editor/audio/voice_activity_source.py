# chatbot/robot_style_editor/voice_activity_source.py

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import sounddevice as sd


@dataclass
class VoiceActivityState:
    volume: float = 0.0
    speaking: bool = False
    started_at: float | None = None
    ended_at: float | None = None


class BaseVoiceActivitySource:
    def start(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def get_state(self) -> VoiceActivityState:
        raise NotImplementedError


class MacMicVolumeActivitySource(BaseVoiceActivitySource):
    """
    Macのマイク入力音量から話している/話していないを判定する。
    開始閾値と終了閾値を分けて、長い発話中の音量変動に強くする。
    """

    def __init__(
        self,
        start_threshold: float = 0.006,
        end_threshold: float = 0.003,
        start_hold_sec: float = 0.08,
        silence_hold_sec: float = 0.45,
        samplerate: int = 16000,
        blocksize: int = 1024,
        on_start=None,
        on_end=None,
    ):
        self.start_threshold = start_threshold
        self.end_threshold = end_threshold
        self.start_hold_sec = start_hold_sec
        self.silence_hold_sec = silence_hold_sec
        self.samplerate = samplerate
        self.blocksize = blocksize
        self.on_start = on_start
        self.on_end = on_end

        self._state = VoiceActivityState()
        self._lock = threading.Lock()
        self._stream = None
        self._running = False

        self._above_start_since = None
        self._last_above_end_t = time.monotonic()

    def start(self):
        if self._running:
            return

        self._running = True
        self._above_start_since = None
        self._last_above_end_t = time.monotonic()

        self._stream = sd.InputStream(
            channels=1,
            samplerate=self.samplerate,
            blocksize=self.blocksize,
            callback=self._audio_callback,
        )
        self._stream.start()

    def stop(self):
        self._running = False

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            finally:
                self._stream = None

        with self._lock:
            self._state.speaking = False

    def get_state(self) -> VoiceActivityState:
        with self._lock:
            return VoiceActivityState(
                volume=self._state.volume,
                speaking=self._state.speaking,
                started_at=self._state.started_at,
                ended_at=self._state.ended_at,
            )

    def _audio_callback(self, indata, frames, time_info, status):
        if not self._running:
            return

        volume = float(np.sqrt(np.mean(indata.astype(np.float32) ** 2)))
        now = time.monotonic()

        with self._lock:
            was_speaking = self._state.speaking
            self._state.volume = volume

            # -------------------------
            # まだ発話中ではない場合
            # -------------------------
            if not was_speaking:
                if volume >= self.start_threshold:
                    if self._above_start_since is None:
                        self._above_start_since = now

                    if now - self._above_start_since >= self.start_hold_sec:
                        self._state.speaking = True
                        self._state.started_at = now
                        self._state.ended_at = None
                        self._last_above_end_t = now
                        self._above_start_since = None

                        if self.on_start:
                            self.on_start(now)
                else:
                    self._above_start_since = None

                return

            # -------------------------
            # 発話中の場合
            # -------------------------
            if volume >= self.end_threshold:
                self._last_above_end_t = now
                return

            if now - self._last_above_end_t >= self.silence_hold_sec:
                self._state.speaking = False
                self._state.ended_at = now

                if self.on_end:
                    self.on_end(now)


class RobotActActivitySource(BaseVoiceActivitySource):
    """
    本番環境用の差し替え先。
    filler_controller.py の _get_act() と同じ考え方で、
    xyz.get_latest().act を使って話者の発話状態を読む。
    """

    def __init__(
        self,
        xyz_client,
        act_threshold: int = 1,
        silence_hold_sec: float = 0.45,
        poll_interval: float = 0.03,
        on_start: Optional[Callable[[float], None]] = None,
        on_end: Optional[Callable[[float], None]] = None,
    ):
        self.xyz_client = xyz_client
        self.act_threshold = act_threshold
        self.silence_hold_sec = silence_hold_sec
        self.poll_interval = poll_interval
        self.on_start = on_start
        self.on_end = on_end

        self._state = VoiceActivityState()
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._last_active_t = 0.0

    def start(self):
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

        if self._thread is not None:
            self._thread.join(timeout=1.0)
            self._thread = None

        with self._lock:
            self._state.speaking = False

    def get_state(self) -> VoiceActivityState:
        with self._lock:
            return VoiceActivityState(
                volume=self._state.volume,
                speaking=self._state.speaking,
                started_at=self._state.started_at,
                ended_at=self._state.ended_at,
            )

    def _get_act(self) -> int:
        s = self.xyz_client.get_latest()
        return int(getattr(s, "act", 0)) if s else 0

    def _poll_loop(self):
        while self._running:
            now = time.monotonic()
            act = self._get_act()
            active = act >= self.act_threshold

            with self._lock:
                was_speaking = self._state.speaking
                self._state.volume = float(act)

                if active:
                    self._last_active_t = now

                    if not was_speaking:
                        self._state.speaking = True
                        self._state.started_at = now
                        self._state.ended_at = None

                        if self.on_start:
                            self.on_start(now)

                else:
                    if was_speaking and (now - self._last_active_t) >= self.silence_hold_sec:
                        self._state.speaking = False
                        self._state.ended_at = now

                        if self.on_end:
                            self.on_end(now)

            time.sleep(self.poll_interval)
