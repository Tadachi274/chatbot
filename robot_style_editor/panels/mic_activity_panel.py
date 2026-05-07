import tkinter as tk
from tkinter import messagebox
import os
import queue
import threading
import time

from ..config import (
    MIC_VOLUME_START_THRESHOLD_DEFAULT,
    MIC_VOLUME_END_THRESHOLD_DEFAULT,
    MIC_START_HOLD_SEC_DEFAULT,
    MIC_SILENCE_HOLD_SEC_DEFAULT,
    MIC_METER_UPDATE_INTERVAL_SEC,
)
from ..audio.voice_activity_source import MacMicVolumeActivitySource, RobotActActivitySource
from .. import ui_style as ui


class MicActivityPanel(tk.Frame):
    def __init__(
        self,
        parent,
        title="マイク入力",
        description="マイク入力を使って確認します。",
        sample_text=None,
        on_speech_start=None,
        on_speech_end=None,
        on_volume_update=None,
        status_var=None,
        start_threshold=MIC_VOLUME_START_THRESHOLD_DEFAULT,
        end_threshold=MIC_VOLUME_END_THRESHOLD_DEFAULT,
        start_hold_sec=MIC_START_HOLD_SEC_DEFAULT,
        silence_hold_sec=MIC_SILENCE_HOLD_SEC_DEFAULT,
        activity_mode="mic",
        act_threshold=1,
    ):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.title = title
        self.description = description
        self.sample_text = sample_text

        self.on_speech_start_callback = on_speech_start
        self.on_speech_end_callback = on_speech_end
        self.on_volume_update_callback = on_volume_update
        self.status_var = status_var

        self.start_threshold = start_threshold
        self.end_threshold = end_threshold
        self.start_hold_sec = start_hold_sec
        self.silence_hold_sec = silence_hold_sec
        self.activity_mode = activity_mode
        self.act_threshold = act_threshold

        self.state_label = tk.StringVar(value="停止中")
        self.result_label = tk.StringVar(value="")
        self.volume_label = tk.StringVar(value="act: 0" if self.activity_mode == "robot_act" else "音量: 0.000")

        self.activity_source = None
        self.xyz_client = None
        self.ignore_until_t = 0.0
        self.paused_label_text = "再生中"
        self._event_queue = queue.SimpleQueue()
        self._meter_thread = None
        self._meter_running = False
        self._event_read_fd = None
        self._event_write_fd = None
        self._filehandler_registered = False

        self.build_ui()
        self.setup_ui_event_pipe()
        self.start_meter_updates()

    def build_ui(self):
        section = ui.frame(self, bg="panel")
        section.pack(fill="x")

        ui.label(
            section,
            text=self.title,
            font="section_title",
            bg="panel",
        ).pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["section_y"]),
        )

        if self.description:
            ui.label(
                card,
                text=self.description,
                font="small",
                bg="card",
                fg="muted",
                justify="left",
                anchor="w",
            ).pack(
                fill="x",
                padx=ui.SPACING["card_x"],
                pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
            )

        if self.sample_text:
            ui.label(
                card,
                text=f"例文：{self.sample_text}",
                font="body",
                bg="card",
                fg="text",
                justify="left",
                anchor="w",
            ).pack(
                fill="x",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["compact_y"]),
            )

        state_row = ui.frame(card, bg="card")
        state_row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )

        ui.variable_label(
            state_row,
            textvariable=self.state_label,
            font="body_bold",
            bg="card",
            fg="text",
        ).pack(side="left")

        ui.variable_label(
            state_row,
            textvariable=self.result_label,
            font="body_bold",
            bg="card",
            fg="blue_text",
        ).pack(side="left", padx=(ui.SPACING["gap"], 0))

        ui.variable_label(
            state_row,
            textvariable=self.volume_label,
            font="small",
            bg="card",
            fg="muted",
        ).pack(side="right")

        meter_row = ui.frame(card, bg="card")
        meter_row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["small_gap"]),
        )

        self.volume_bar = tk.Canvas(
            meter_row,
            height=18,
            bg=ui.COLORS["soft_border"],
            highlightthickness=0,
        )
        self.volume_bar.pack(fill="x")

        button_row = ui.frame(card, bg="card")
        button_row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["card_y"]),
        )

        ui.sub_button(
            button_row,
            text="認識開始",
            command=self.start,
        ).pack(side="left")

        ui.sub_button(
            button_row,
            text="認識終了",
            command=self.stop,
        ).pack(side="left", padx=(ui.SPACING["small_gap"], 0))

    def start(self):
        try:
            self.stop()

            self.result_label.set("")

            self.activity_source = self.create_activity_source()

            self.activity_source.start()
            self.state_label.set("認識中")

            if self.status_var is not None:
                self.status_var.set("マイク認識を開始しました")

        except Exception as e:
            messagebox.showerror("マイクエラー", str(e))
            if self.status_var is not None:
                self.status_var.set(f"マイクエラー: {e}")

    def create_activity_source(self):
        if self.activity_mode == "robot_act":
            try:
                from chatbot.tts.command.xyz_server import XYZClient
            except Exception as e:
                raise RuntimeError(f"XYZClient を読み込めませんでした: {e}") from e

            self.xyz_client = XYZClient()
            self.xyz_client.start()
            return RobotActActivitySource(
                xyz_client=self.xyz_client,
                act_threshold=self.act_threshold,
                silence_hold_sec=self.silence_hold_sec,
                on_start=self.on_speech_start,
                on_end=self.on_speech_end,
            )

        return MacMicVolumeActivitySource(
            start_threshold=self.start_threshold,
            end_threshold=self.end_threshold,
            start_hold_sec=self.start_hold_sec,
            silence_hold_sec=self.silence_hold_sec,
            on_start=self.on_speech_start,
            on_end=self.on_speech_end,
        )

    def stop(self):
        if self.activity_source is not None:
            try:
                self.activity_source.stop()
            except Exception:
                pass
            self.activity_source = None
        if self.xyz_client is not None:
            try:
                self.xyz_client.stop()
            except Exception:
                pass
            self.xyz_client = None

        self.state_label.set("停止中")
        self.result_label.set("")

    def on_speech_start(self, t):
        if self.is_paused():
            return

        self.queue_ui_event("speech_start", t)

    def on_speech_end(self, t):
        if self.is_paused():
            return

        self.queue_ui_event("speech_end", t)

    def pause_for(self, duration_sec: float, label: str = "再生中"):
        """
        ロボット自身の音声再生中など、マイク入力を反応させたくない時間だけ無視する。
        マイクストリーム自体は止めず、発話開始/終了イベントとvolume callbackを無視する。
        """
        duration_sec = max(0.0, float(duration_sec))
        self.ignore_until_t = max(self.ignore_until_t, time.monotonic() + duration_sec)
        self.paused_label_text = label
        self.set_state_threadsafe(label)
        self.set_result_threadsafe("")


    def is_paused(self):
        return time.monotonic() < self.ignore_until_t


    def get_remaining_pause_sec(self):
        return max(0.0, self.ignore_until_t - time.monotonic())

    def start_meter_updates(self):
        if self._meter_running:
            return

        self._meter_running = True
        self._meter_thread = threading.Thread(
            target=self.meter_update_loop,
            daemon=True,
        )
        self._meter_thread.start()


    def stop_meter_updates(self):
        self._meter_running = False

        if self._meter_thread is not None:
            self._meter_thread.join(timeout=1.0)
            self._meter_thread = None


    def meter_update_loop(self):
        while self._meter_running:
            self.queue_ui_event("meter")
            time.sleep(MIC_METER_UPDATE_INTERVAL_SEC)


    def queue_ui_event(self, event_type, payload=None):
        self._event_queue.put((event_type, payload))

        self.wake_ui_event_loop()


    def setup_ui_event_pipe(self):
        self.bind("<<MicActivityPanelQueue>>", self._handle_virtual_event, add="+")

        create_filehandler = getattr(self.tk, "createfilehandler", None)
        if create_filehandler is None:
            return

        self._event_read_fd, self._event_write_fd = os.pipe()
        os.set_blocking(self._event_read_fd, False)
        os.set_blocking(self._event_write_fd, False)
        create_filehandler(
            self._event_read_fd,
            tk.READABLE,
            self._handle_pipe_event,
        )
        self._filehandler_registered = True


    def wake_ui_event_loop(self):
        if self._event_write_fd is None:
            if threading.current_thread() is threading.main_thread():
                self._handle_queued_events()
            else:
                self.generate_queue_event()
            return

        try:
            os.write(self._event_write_fd, b"1")
        except (BlockingIOError, OSError):
            pass
        self.generate_queue_event()


    def _handle_pipe_event(self, _fd=None, _mask=None):
        self.drain_event_pipe()
        self._handle_queued_events()


    def _handle_virtual_event(self, _event=None):
        self._handle_queued_events()


    def generate_queue_event(self):
        try:
            self.event_generate("<<MicActivityPanelQueue>>", when="tail")
        except Exception:
            pass


    def drain_event_pipe(self):
        if self._event_read_fd is None:
            return

        while True:
            try:
                data = os.read(self._event_read_fd, 1024)
            except BlockingIOError:
                break
            except OSError:
                break

            if not data:
                break


    def _handle_queued_events(self, _event=None):
        while True:
            try:
                event_type, payload = self._event_queue.get_nowait()
            except queue.Empty:
                break

            if event_type == "meter":
                self.update_meter()
            elif event_type == "speech_start":
                self.handle_speech_start(payload)
            elif event_type == "speech_end":
                self.handle_speech_end(payload)
            elif event_type == "set_state":
                self.state_label.set(payload)
            elif event_type == "set_result":
                self.result_label.set(payload)


    def handle_speech_start(self, t):
        if self.is_paused():
            return

        self.state_label.set("発話中")
        self.result_label.set("")

        if self.on_speech_start_callback is not None:
            self.on_speech_start_callback(t)


    def handle_speech_end(self, t):
        if self.is_paused():
            return

        self.state_label.set("認識中")

        if self.on_speech_end_callback is not None:
            self.on_speech_end_callback(t)


    def update_meter(self):
        if self.activity_source is not None:
            state = self.activity_source.get_state()
            volume = state.volume
            speaking = state.speaking
        else:
            volume = 0.0
            speaking = False

        if self.is_paused():
            remain = self.get_remaining_pause_sec()
            self.state_label.set(f"{self.paused_label_text} {remain:.1f}s")
            self.result_label.set("")
            self.volume_label.set("act: --" if self.activity_mode == "robot_act" else "音量: --")
            self.draw_volume_bar(0.0)
            return

        if self.activity_mode == "robot_act":
            self.volume_label.set(f"act: {int(volume)}")
        else:
            self.volume_label.set(f"音量: {volume:.3f}")
        self.draw_volume_bar(volume)

        if self.on_volume_update_callback is not None:
            self.on_volume_update_callback(volume, speaking)

    def draw_volume_bar(self, volume):
        self.volume_bar.delete("all")

        width = max(1, self.volume_bar.winfo_width())
        height = max(1, self.volume_bar.winfo_height())

        threshold = float(self.act_threshold if self.activity_mode == "robot_act" else self.start_threshold)
        ratio = min(1.0, volume / max(0.001, threshold))
        fill_width = int(width * ratio)

        self.volume_bar.create_rectangle(
            0,
            0,
            fill_width,
            height,
            fill=ui.COLORS["accent"],
            outline="",
        )

        if self.activity_mode == "robot_act":
            threshold_ratio = 1.0
        else:
            threshold_ratio = min(1.0, self.end_threshold / max(0.001, self.start_threshold))

        threshold_x = int(width * threshold_ratio)

        self.volume_bar.create_line(
            threshold_x,
            0,
            threshold_x,
            height,
            fill=ui.COLORS["text"],
        )

    def set_state(self, text):
        self.state_label.set(text)

    def set_result(self, text):
        self.result_label.set(text)

    def set_state_threadsafe(self, text):
        self.queue_ui_event("set_state", text)

    def set_result_threadsafe(self, text):
        self.queue_ui_event("set_result", text)

    def destroy(self):
        self.stop()
        self.stop_meter_updates()
        self.close_ui_event_pipe()
        super().destroy()

    def close_ui_event_pipe(self):
        if self._filehandler_registered and self._event_read_fd is not None:
            delete_filehandler = getattr(self.tk, "deletefilehandler", None)
            if delete_filehandler is not None:
                try:
                    delete_filehandler(self._event_read_fd)
                except tk.TclError:
                    pass

        for fd in (self._event_read_fd, self._event_write_fd):
            if fd is not None:
                try:
                    os.close(fd)
                except OSError:
                    pass

        self._event_read_fd = None
        self._event_write_fd = None
        self._filehandler_registered = False
