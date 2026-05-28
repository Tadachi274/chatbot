import copy
import os
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from .. import ui_style as ui
from ..config import (
    DEFAULT_PAUSE_DURATION,
    DEFAULT_SENTENCE_DURATION,
    face_axis_commands,
    default_face_data,
    default_voice_data,
    voice_params_to_tts_instructions,
)

class RobotRunTab(tk.Frame):
    def __init__(self, parent, get_turns, status_var):
        super().__init__(parent, bg=ui.COLORS["main_card"])
        self.get_turns = get_turns
        self.status_var = status_var
        self.tts_client = None
        self.robot_client = None
        self.mic_panel = None
        self.run_state = "idle"
        self.run_index = 0
        self.prepared_dialogue = None
        self.turns_override = None
        self.turns_label = None
        self.generated_wav_paths = []
        self.run_queue = queue.SimpleQueue()
        self.lyric_frame = None
        self.start_after_prepare = False
        self.prep_message_var = None
        self.prep_progress_var = None
        self.prep_count_var = None
        self.prep_total = 1
        self._event_read_fd = None
        self._event_write_fd = None
        self.face_event_generation = 0

        self.bind("<<ConversationRunQueue>>", self.handle_run_queue_event, add="+")
        self.setup_run_queue_pipe()
        self.build_main_view()

    def clear_views(self):
        if self.mic_panel is not None:
            try:
                self.mic_panel.stop()
            except Exception:
                pass
            self.mic_panel = None
        for child in self.winfo_children():
            child.destroy()

    def build_main_view(self):
        self.clear_views()

        page = ui.frame(self, bg="main_card")
        page.pack(fill="both", expand=True, padx=ui.SPACING["page_x"], pady=ui.SPACING["page_y"])

        ui.label(page, text="ロボットで試す", font="page_title", bg="main_card").pack(anchor="w")
        ui.label(
            page,
            text="客の発話終了をマイクで検出し、店員発話の音声と表情・視線・頷きをタイムライン通りに再生します。",
            font="body",
            bg="main_card",
            fg="sub_text",
            wraplength=980,
            justify="left",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        controls = ui.frame(page, bg="main_card")
        controls.pack(fill="x", pady=(0, ui.SPACING["gap"]))
        ui.sub_button(controls, text="実演準備", command=self.prepare_robot_run).pack(side="left")
        ui.action_button(controls, text="実演開始", command=self.start_robot_run).pack(side="left", padx=(ui.SPACING["small_gap"], 0))
        ui.sub_button(controls, text="停止", command=self.stop_robot_run).pack(side="left", padx=(ui.SPACING["small_gap"], 0))
        ui.sub_button(controls, text="客発話完了", command=lambda: self.on_run_customer_speech_end(None)).pack(
            side="left", padx=(ui.SPACING["small_gap"], 0)
        )

        self.lyric_frame = ui.frame(page, bg="main_card")
        self.lyric_frame.pack(fill="x", pady=(0, ui.SPACING["gap"]))
        self.render_lyrics_view()

        if self.prepared_dialogue is not None:
            MicActivityPanel = self.mic_panel_class()
            self.mic_panel = MicActivityPanel(
                page,
                title="客発話の切れ目検出",
                description="実環境の act 値が 1 以上の間を客の発話中として扱い、発話終了後に次へ進みます。",
                on_speech_start=self.on_run_customer_speech_start,
                on_speech_end=self.on_run_customer_speech_end,
                status_var=self.status_var,
                act_threshold=1,
                show_controls=False,
            )
            self.mic_panel.pack(fill="x")

    def ensure_tts_client(self):
        if self.tts_client is None:
            from ...robot_style_editor.clients.tts_client import TTSClient

            self.tts_client = TTSClient()
        return self.tts_client


    def set_tts_playback_target(self, target):
        if self.tts_client is not None:
            self.tts_client.set_playback_target(target)


    def refresh_mic_activity_mode(self):
        if self.run_state == "running":
            return False
        if self.mic_panel is not None:
            try:
                self.mic_panel.stop()
            except Exception:
                pass
        if self.prepared_dialogue is not None and self.run_state != "running":
            self.build_main_view()
        return True


    def ensure_robot_client(self):
        if self.robot_client is None:
            from ...robot_style_editor.clients.robot_command_client import RobotCommandClient

            self.robot_client = RobotCommandClient()
        return self.robot_client


    def reset_robot_client(self):
        if self.robot_client is not None:
            try:
                self.robot_client.close()
            except Exception:
                pass
        self.robot_client = None


    def mic_panel_class(self):
        from ...robot_style_editor.panels.mic_activity_panel import MicActivityPanel

        return MicActivityPanel


    def render_lyrics_view(self):
        if self.lyric_frame is None:
            return

        for child in self.lyric_frame.winfo_children():
            child.destroy()

        turns = self.prepared_dialogue or self.current_turns()
        if not turns:
            ui.label(
                self.lyric_frame,
                text="実演する発話がありません。",
                font="small",
                bg="main_card",
                fg="muted",
            ).pack(anchor="w")
            return

        if self.run_state == "running":
            start = max(0, self.run_index - 1)
            end = min(len(turns), self.run_index + 2)
        else:
            start = 0
            end = len(turns)

        for idx in range(start, end):
            turn = turns[idx]
            is_current = self.run_state == "running" and idx == self.run_index
            role = "客" if turn.get("role") == "customer" else "ロボット"
            bg = "panel" if is_current else "card"
            card = ui.bordered_frame(self.lyric_frame, bg=bg, border="border")
            card.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))
            ui.label(card, text=f"{idx + 1}. {role}", font="small", bg=bg, fg="muted").pack(
                anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["small_gap"], 0)
            )
            ui.label(
                card,
                text=turn.get("text", ""),
                font="section_title" if is_current else "body",
                bg=bg,
                fg="text",
                wraplength=980,
                justify="left",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["small_gap"]))


    def current_turns(self):
        return copy.deepcopy(self.turns_override) if self.turns_override is not None else self.get_turns()


    def set_turns_override(self, turns, label=None):
        self.turns_override = copy.deepcopy(turns) if turns is not None else None
        self.turns_label = label


    def show_overview(self, turns=None, label=None):
        if self.run_state == "running":
            self.stop_robot_run()
        self.set_turns_override(turns, label)
        self.prepared_dialogue = None
        self.run_state = "idle"
        self.run_index = 0
        self.build_main_view()
        if self.turns_label:
            self.status_var.set(f"実演する範囲を確認できます: {self.turns_label}")
        else:
            self.status_var.set("実演する会話を確認できます")


    def prepare_robot_run(self, start_after=False):
        turns = self.current_turns()
        if not turns:
            messagebox.showwarning("確認", "実演する発話を入力してください")
            return

        self.start_after_prepare = bool(start_after)
        self.prepared_dialogue = None
        self.cleanup_generated_wavs()
        self.prep_total = max(1, self.count_tts_units(turns))
        self.build_preparing_view(self.prep_total)
        self.status_var.set("実演用のTTS音声を準備しています")
        threading.Thread(target=self.prepare_robot_run_worker, args=(turns,), daemon=True).start()

    def build_preparing_view(self, total):
        self.clear_views()

        page = ui.frame(self, bg="main_card")
        page.pack(fill="both", expand=True, padx=ui.SPACING["page_x"], pady=ui.SPACING["page_y"])

        ui.label(page, text="ロボット実演の準備中", font="page_title", bg="main_card").pack(anchor="w")
        ui.label(
            page,
            text="各店員発話を声色設定に合わせてTTS音声化しています。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        card = ui.bordered_frame(page, bg="card", border="border")
        card.pack(fill="x")

        self.prep_message_var = tk.StringVar(value="TTS生成を開始します")
        self.prep_progress_var = tk.DoubleVar(value=0)
        self.prep_count_var = tk.StringVar(value=f"0 / {total}")

        ui.variable_label(
            card,
            textvariable=self.prep_message_var,
            font="body_bold",
            bg="card",
            fg="text",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]))

        ttk.Progressbar(
            card,
            variable=self.prep_progress_var,
            maximum=total,
            mode="determinate",
        ).pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["small_gap"]))

        ui.variable_label(
            card,
            textvariable=self.prep_count_var,
            font="small",
            bg="card",
            fg="muted",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))

        spinner = ttk.Progressbar(card, mode="indeterminate")
        spinner.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))
        spinner.start(12)

    def count_tts_units(self, turns):
        total = 0
        for turn in turns:
            if turn.get("role") != "staff":
                continue
            for segment in turn.get("segments", []):
                if segment.get("type") == "sentence" and segment.get("text", "").strip():
                    total += 1
        return total

    def emit_prep_progress(self, completed, total, message):
        self.run_queue.put(
            {
                "type": "prep_progress",
                "completed": completed,
                "total": total,
                "message": message,
            }
        )
        self.wake_run_queue()


    def prepare_robot_run_worker(self, turns):
        prepared_turns = []
        total = max(1, self.count_tts_units(turns))
        completed = 0
        try:
            tts_client = self.ensure_tts_client()
            for turn_index, turn in enumerate(turns):
                prepared = copy.deepcopy(turn)
                if turn.get("role") != "staff":
                    prepared_turns.append(prepared)
                    continue

                prepared_segments = []
                for segment in turn.get("segments", []):
                    prepared_segment = copy.deepcopy(segment)
                    if segment.get("type") != "sentence":
                        prepared_segments.append(prepared_segment)
                        continue

                    text = segment.get("text", "").strip()
                    if not text:
                        continue
                    self.emit_prep_progress(
                        completed,
                        total,
                        f"{turn_index + 1}. 店員発話を生成中: {text[:28]}",
                    )
                    voice_data = segment.get("voice", default_voice_data())
                    instructions = voice_data.get("tts_instructions")
                    if instructions is None:
                        instructions = voice_params_to_tts_instructions(
                            voice_data.get("params", default_voice_data()["params"])
                        )

                    if tts_client.is_robot_playback():
                        remote = tts_client.prepare_remote_audio(text=text, instructions=instructions)
                        if not remote:
                            continue
                        prepared_segment["remote_audio_id"] = remote["audio_id"]
                        prepared_segment["duration"] = float(
                            remote.get("duration", segment.get("duration", DEFAULT_SENTENCE_DURATION))
                        )
                    else:
                        wav_path = tts_client.synthesize_to_wav(text=text, instructions=instructions)
                        if wav_path is None:
                            continue
                        self.generated_wav_paths.append(str(wav_path))
                        prepared_segment["wav_path"] = str(wav_path)
                        prepared_segment["duration"] = float(tts_client.get_wav_duration_sec(wav_path))

                    prepared_segments.append(prepared_segment)
                    completed += 1
                    self.emit_prep_progress(
                        completed,
                        total,
                        f"{completed} / {total} 件のTTS音声を生成しました",
                    )

                prepared["segments"] = prepared_segments
                prepared_turns.append(prepared)

            self.run_queue.put({"type": "prepared", "turns": prepared_turns})
            self.wake_run_queue()
        except Exception as exc:
            self.run_queue.put({"type": "error", "message": str(exc)})
            self.wake_run_queue()


    def start_robot_run(self):
        self.prepare_robot_run(start_after=True)


    def start_prepared_robot_run(self):
        if self.prepared_dialogue is None:
            return
        self.run_state = "running"
        self.run_index = 0
        self.face_event_generation = 0
        self.render_lyrics_view()
        self.advance_robot_run()


    def stop_robot_run(self):
        self.run_state = "stopped"
        self.face_event_generation += 1
        if self.mic_panel is not None:
            self.mic_panel.stop()
        if self.tts_client is not None:
            try:
                self.tts_client.stop_preview()
            except Exception:
                pass
        self.cleanup_generated_wavs()
        self.status_var.set("ロボット実演を停止しました")
        self.render_lyrics_view()


    def advance_robot_run(self):
        if self.run_state != "running":
            return

        turns = self.prepared_dialogue or []
        if self.run_index >= len(turns):
            self.finish_robot_run()
            return

        self.render_lyrics_view()
        turn = turns[self.run_index]
        if turn.get("role") == "customer":
            if self.use_mic_detection_for_run():
                self.status_var.set("客の発話待ちです")
                if self.mic_panel is not None:
                    self.mic_panel.clear_pause()
                    self.mic_panel.start()
            else:
                self.status_var.set("客発話後に「客発話完了」を押してください")
            return

        if self.mic_panel is not None:
            self.mic_panel.stop()
        threading.Thread(target=self.play_staff_turn_worker, args=(turn,), daemon=True).start()


    def use_mic_detection_for_run(self):
        return os.environ.get("ROBOT_RUN_USE_MIC", "1") != "0"


    def on_run_customer_speech_start(self, _t):
        if self.run_state != "running":
            return
        self.status_var.set("客の発話中です")


    def on_run_customer_speech_end(self, _t):
        if self.run_state != "running":
            return
        turns = self.prepared_dialogue or []
        if self.run_index >= len(turns) or turns[self.run_index].get("role") != "customer":
            return
        if self.mic_panel is not None:
            self.mic_panel.stop()
        threading.Thread(target=self.customer_speech_end_worker, daemon=True).start()


    def customer_speech_end_worker(self):
        try:
            self.run_index += 1
            self.run_queue.put({"type": "advance"})
            self.wake_run_queue()
        except Exception as exc:
            self.run_queue.put({"type": "error", "message": str(exc)})
            self.wake_run_queue()


    def play_staff_turn_worker(self, turn):
        try:
            motion_thread = threading.Thread(target=self.play_timed_events_worker, args=(turn,), daemon=True)
            motion_thread.start()

            for segment in turn.get("segments", []):
                if self.run_state != "running":
                    return
                if segment.get("type") == "pause":
                    time.sleep(max(0.0, float(segment.get("duration", DEFAULT_PAUSE_DURATION))))
                    continue
                self.play_prepared_segment(segment)

            self.run_index += 1
            self.run_queue.put({"type": "advance"})
            self.wake_run_queue()
        except Exception as exc:
            self.run_queue.put({"type": "error", "message": str(exc)})
            self.wake_run_queue()


    def play_prepared_segment(self, segment):
        tts_client = self.ensure_tts_client()
        if tts_client.is_robot_playback() and segment.get("remote_audio_id"):
            duration = float(segment.get("duration", DEFAULT_SENTENCE_DURATION))
            if self.mic_panel is not None:
                self.mic_panel.pause_for(duration + 0.2, label="ロボット発話中")
            tts_client.play_remote_audio(segment["remote_audio_id"], wait=True, timeout=duration + 5.0)
            return

        self.play_prepared_wav(segment["wav_path"])


    def play_prepared_wav(self, wav_path):
        from ...robot_style_editor.audio.wav_silence import trim_silence_to_temp_wav

        tts_client = self.ensure_tts_client()
        trimmed = trim_silence_to_temp_wav(wav_path)
        done = threading.Event()
        duration = tts_client.get_wav_duration_sec(trimmed)
        if self.mic_panel is not None:
            self.mic_panel.pause_for(duration + 0.2, label="ロボット発話中")
        try:
            tts_client.preview_player.play_later(trimmed, done_event=done)
            if not done.wait(timeout=duration + 5.0):
                tts_client.preview_player.stop_current()
        finally:
            try:
                trimmed.unlink(missing_ok=True)
            except Exception:
                pass


    def play_timed_events_worker(self, turn):
        started = time.monotonic()
        events = sorted(turn.get("events", []), key=lambda event: float(event.get("time", 0.0)))
        face_events = [event for event in events if event.get("lane") == "face"]
        turn_duration = float(turn.get("duration", self.turn_duration_from_segments(turn)))
        for face_index, face_event in enumerate(face_events):
            start = float(face_event.get("time", 0.0))
            duration = float(face_event.get("duration", 0.0))
            next_start = None
            if face_index + 1 < len(face_events):
                next_start = float(face_events[face_index + 1].get("time", 0.0))
            return_until = next_start if next_start is not None else turn_duration
            face_event["_return_duration"] = max(0.0, return_until - (start + duration))
            face_event["_default_face"] = copy.deepcopy(turn.get("default_face") or default_face_data("ニュートラル"))
        for event in events:
            if self.run_state != "running":
                return
            target = started + float(event.get("time", 0.0))
            wait_sec = target - time.monotonic()
            if wait_sec > 0:
                time.sleep(wait_sec)
            if self.run_state != "running":
                return
            self.apply_timeline_event(event)


    def turn_duration_from_segments(self, turn):
        duration = 0.0
        for segment in turn.get("segments", []):
            duration += float(segment.get("duration", DEFAULT_PAUSE_DURATION))
        return duration


    def apply_timeline_event(self, event):
        lane = event.get("lane")
        if lane == "face":
            self.apply_face_event(event)
        elif lane == "gaze":
            self.apply_gaze_event(event)
        elif lane == "nod":
            self.apply_nod_event(event)


    def apply_face_event(self, event):
        face = event.get("face") or default_face_data(event.get("value", "笑顔"))
        duration_sec = max(0.0, float(event.get("duration", 0.0)))
        keeptime = max(1, int(round(duration_sec * 1000)))
        self.face_event_generation += 1
        generation = self.face_event_generation
        self.send_face_data(face, keeptime, label=event.get("value", "表情"))
        self.schedule_face_default(
            duration_sec,
            generation,
            event.get("_default_face") or default_face_data("ニュートラル"),
            float(event.get("_return_duration", 0.0)),
        )


    def send_face_data(self, face, keeptime, label=None):
        robot = self.ensure_robot_client()
        command = face.get("command", {})
        face_label = face.get("label") or label or "表情"
        if command.get("type") == "emotion":
            if command.get("emotion") == "neutral":
                command_text = command.get("text", "/emotion neutral")
            else:
                emotion = command.get("emotion", "neutral")
                level = int(command.get("level", 1))
                priority = int(command.get("priority", 3))
                command_text = f"/emotion {emotion} {level} {priority} {keeptime}"
            print(f"[FACE] {face_label}: {command_text}", flush=True)
            robot.send(command_text)
            return

        axis_commands = face_axis_commands(face, keeptime=keeptime)
        if not axis_commands:
            return
        axis_summary = ", ".join(f"{cmd['axis']}={int(cmd['value'])}" for cmd in axis_commands)
        print(f"[FACE] {face_label}: /movemulti5 axes({axis_summary})", flush=True)
        for axis_command in axis_commands:
            robot.send_face_axis(
                axis=str(axis_command["axis"]),
                value=int(axis_command["value"]),
                velocity=int(axis_command.get("velocity", 2000)),
                priority=int(axis_command.get("priority", 3)),
                keeptime=int(axis_command.get("keeptime", 3000)),
            )


    def schedule_face_default(self, duration_sec, generation, default_face, return_duration_sec):
        if duration_sec <= 0:
            return

        def send_default_after_duration():
            time.sleep(duration_sec)
            if self.run_state != "running" or self.face_event_generation != generation:
                return
            try:
                keeptime = max(1, int(round(max(0.1, return_duration_sec) * 1000)))
                self.send_face_data(default_face, keeptime, label="基本表情")
            except Exception as exc:
                self.run_queue.put({"type": "error", "message": f"基本表情送信エラー: {exc}"})
                self.wake_run_queue()

        threading.Thread(target=send_default_after_duration, daemon=True).start()


    def apply_gaze_event(self, event):
        direction = self.gaze_label_to_lookaway(event.get("value", "客の方"))
        self.ensure_robot_client().send_lookaway(direction=direction, priority=4, keeptime=800)


    def gaze_label_to_lookaway(self, label):
        return {
            "客の方": "f",
            "正面": "f",
            "上": "u",
            "下": "d",
            "右": "r",
            "左": "l",
            "右上": "ru",
            "左上": "lu",
            "右下": "rd",
            "左下": "ld",
        }.get(label, "f")


    def apply_nod_event(self, event):
        value = event.get("value", "普通")
        preset = {
            "小さく": {"amplitude": 7, "duration": 300, "times": 1},
            "普通": {"amplitude": 12, "duration": 400, "times": 1},
            "深く": {"amplitude": 18, "duration": 550, "times": 1},
            "お辞儀": {"amplitude": 22, "duration": 700, "times": 1},
            "その他": {"amplitude": 12, "duration": 400, "times": 1},
        }.get(value, {"amplitude": 12, "duration": 400, "times": 1})
        self.ensure_robot_client().send_nod(
            amplitude=preset["amplitude"],
            duration=preset["duration"],
            times=preset["times"],
            priority=3,
        )


    def finish_robot_run(self):
        self.run_state = "finished"
        if self.mic_panel is not None:
            self.mic_panel.stop()
        self.cleanup_generated_wavs()
        self.status_var.set("ロボット実演が終了しました")
        self.render_lyrics_view()


    def cleanup_generated_wavs(self):
        for wav_path in self.generated_wav_paths:
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass
        self.generated_wav_paths = []


    def wake_run_queue(self):
        if self._event_write_fd is not None:
            try:
                os.write(self._event_write_fd, b"1")
            except (BlockingIOError, OSError):
                pass
            return
        if threading.current_thread() is threading.main_thread():
            self.handle_run_queue_event()
            return
        try:
            self.event_generate("<<ConversationRunQueue>>", when="tail")
        except Exception:
            pass


    def setup_run_queue_pipe(self):
        create_filehandler = getattr(self.tk, "createfilehandler", None)
        if create_filehandler is None or self._event_read_fd is not None:
            return

        self._event_read_fd, self._event_write_fd = os.pipe()
        os.set_blocking(self._event_read_fd, False)
        os.set_blocking(self._event_write_fd, False)
        create_filehandler(
            self._event_read_fd,
            tk.READABLE,
            self._handle_pipe_event,
        )


    def _handle_pipe_event(self, _fd=None, _mask=None):
        self.drain_event_pipe()
        self.handle_run_queue_event()


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


    def handle_run_queue_event(self, _event=None):
        while True:
            try:
                item = self.run_queue.get_nowait()
            except queue.Empty:
                break
            if item.get("type") == "prep_progress":
                if self.prep_progress_var is not None:
                    self.prep_progress_var.set(item.get("completed", 0))
                if self.prep_count_var is not None:
                    self.prep_count_var.set(f"{item.get('completed', 0)} / {item.get('total', self.prep_total)}")
                if self.prep_message_var is not None:
                    self.prep_message_var.set(item.get("message", "TTS音声を生成しています"))
            elif item.get("type") == "prepared":
                self.prepared_dialogue = item["turns"]
                self.run_index = 0
                self.run_state = "ready"
                self.status_var.set("実演準備ができました")
                self.build_main_view()
                self.render_lyrics_view()
                if self.start_after_prepare:
                    self.start_after_prepare = False
                    self.start_prepared_robot_run()
            elif item.get("type") == "advance":
                self.advance_robot_run()
            elif item.get("type") == "error":
                self.run_state = "stopped"
                self.start_after_prepare = False
                self.status_var.set(f"実演エラー: {item.get('message')}")
                messagebox.showerror("実演エラー", item.get("message", "不明なエラー"))
                self.build_main_view()
