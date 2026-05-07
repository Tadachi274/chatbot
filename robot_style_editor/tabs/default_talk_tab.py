import copy
from pathlib import Path
import queue
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from .. import ui_style as ui
from ..config_default_profile import build_default_profile
from ..config_example import EXAMPLE_SCENES, EXAMPLE_VENUES


class DefaultTalkTab(tk.Frame):
    def __init__(self, parent, profile_store, status_var, tts_client=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])
        self.profile_store = profile_store
        self.status_var = status_var
        self.tts_client = tts_client
        self.default_profile = build_default_profile()
        self.robot_client = None

        self.venue_var = tk.StringVar(value=EXAMPLE_VENUES[0]["label"])
        self.scene_var = tk.StringVar()
        self.delete_generated_wav_var = tk.BooleanVar(value=True)
        self.prep_queue = queue.SimpleQueue()
        self.prepared_dialogue = None
        self.generated_wav_paths = []
        self.run_state = "idle"
        self.run_index = 0
        self.venue_tab_labels = {}
        self.venue_notebook = None
        self.scene_combo = None
        self.dialogue_frame = None
        self.lyric_frame = None
        self.mic_panel = None

        self.bind("<<DefaultTalkTabQueue>>", self.on_queue_event, add="+")
        self.build_ui()
        self.refresh_scene_choices()

    def ensure_robot_client(self):
        if self.robot_client is None:
            from ..clients.robot_command_client import RobotCommandClient

            self.robot_client = RobotCommandClient()
        return self.robot_client

    def build_ui(self):
        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )

        content = ui.scrollable_frame(page)
        self.build_selector_area(content)
        self.build_dialogue_area(content)

        bottom = ui.frame(page, bg="main_card")
        bottom.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))
        ui.action_button(
            bottom,
            text="デフォルトでロボット実演",
            command=self.prepare_robot_run,
        ).pack(side="left")
        tk.Checkbutton(
            bottom,
            text="実演後に生成WAVを削除する",
            variable=self.delete_generated_wav_var,
            font=ui.FONTS["small"],
            bg=ui.COLORS["main_card"],
            fg=ui.COLORS["sub_text"],
            activebackground=ui.COLORS["main_card"],
            activeforeground=ui.COLORS["text"],
            selectcolor=ui.COLORS["card"],
        ).pack(side="left", padx=(ui.SPACING["gap"], 0))

    def build_selector_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        ui.label(section, text="デフォルト会話", font="section_title", bg="panel").pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        self.venue_notebook = ttk.Notebook(section, style="Research.TNotebook")
        self.venue_notebook.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["small_gap"]),
        )
        self.venue_notebook.bind("<<NotebookTabChanged>>", self.on_venue_tab_changed)
        for venue in EXAMPLE_VENUES:
            tab = ui.frame(self.venue_notebook, bg="panel")
            self.venue_notebook.add(tab, text=venue["label"])
            self.venue_tab_labels[str(tab)] = venue["label"]

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))
        ui.label(card, text="具体場面", font="small", bg="card", fg="muted").pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )
        self.scene_combo = ttk.Combobox(card, textvariable=self.scene_var, state="readonly")
        self.scene_combo.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))
        self.scene_combo.bind("<<ComboboxSelected>>", lambda _event=None: self.render_current_scene())

    def build_dialogue_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="both", expand=True, pady=(ui.SPACING["small_gap"], 0))
        ui.label(section, text="会話", font="section_title", bg="panel").pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )
        self.dialogue_frame = ui.frame(section, bg="panel")
        self.dialogue_frame.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["section_y"]),
        )

    def on_venue_tab_changed(self, _event=None):
        if self.venue_notebook is None or not self.venue_notebook.select():
            return
        label = self.venue_tab_labels.get(self.venue_notebook.select())
        if label and self.venue_var.get() != label:
            self.venue_var.set(label)
            self.refresh_scene_choices()

    def current_venue_id(self):
        for venue in EXAMPLE_VENUES:
            if venue["label"] == self.venue_var.get():
                return venue["id"]
        return EXAMPLE_VENUES[0]["id"]

    def refresh_scene_choices(self):
        scenes = [scene for scene in EXAMPLE_SCENES if scene["venue"] == self.current_venue_id()]
        values = [scene["title"] for scene in scenes]
        self.scene_combo.configure(values=values)
        if values:
            self.scene_var.set(values[0])
        self.render_current_scene()

    def current_scene(self):
        venue_id = self.current_venue_id()
        for scene in EXAMPLE_SCENES:
            if scene["venue"] == venue_id and scene["title"] == self.scene_var.get():
                return scene
        return next(scene for scene in EXAMPLE_SCENES if scene["venue"] == venue_id)

    def current_turns(self):
        return [
            {
                "role": turn["role"],
                "text": turn.get("text", turn.get("base_text", "")),
                "intent_parts": copy.deepcopy(turn.get("intent_parts", [])),
            }
            for turn in self.current_scene()["turns"]
        ]

    def render_current_scene(self):
        if self.dialogue_frame is None:
            return
        for child in self.dialogue_frame.winfo_children():
            child.destroy()

        for turn in self.current_turns():
            role = "客" if turn["role"] == "customer" else "ロボット"
            bg = "card" if turn["role"] == "customer" else "panel"
            card = ui.bordered_frame(self.dialogue_frame, bg=bg, border="border")
            card.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))
            ui.label(card, text=role, font="small", bg=bg, fg="muted").pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(ui.SPACING["compact_y"], 0),
            )
            ui.label(
                card,
                text=turn["text"],
                font="body_bold" if turn["role"] == "staff" else "body",
                bg=bg,
                fg="text",
                wraplength=980,
                justify="left",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))

    def active_profile_get(self, key, default=None):
        return self.default_profile.get(key, default)

    def active_profile_get_nested(self, key, default=None):
        return self.default_profile.get(key, default)

    def get_intent_data(self, intent):
        key = {
            "greeting": "greeting",
            "explanation": "explanation",
            "question": "question",
            "acceptance": "acceptance",
            "request": "request",
            "apology": "apology",
            "gratitude": "gratitude",
            "smalltalk": "smalltalk",
            "filler": "filler",
        }.get(intent, "explanation")
        return self.active_profile_get_nested(key, {}) or {}

    def intent_label(self, intent):
        return {
            "greeting": "挨拶",
            "explanation": "説明",
            "question": "質問",
            "acceptance": "承諾",
            "request": "要求",
            "apology": "謝罪",
            "gratitude": "感謝",
            "smalltalk": "雑談",
            "filler": "フィラー",
        }.get(intent, intent)

    def prepare_robot_run(self):
        if self.tts_client is None:
            messagebox.showerror("確認", "TTSクライアントが未設定です。")
            return
        self.ensure_robot_client()

        turns = self.current_turns()
        total = self.count_tts_units(turns)
        self.cleanup_generated_wavs()
        self.generated_wav_paths = []
        self.clear_page()
        self.build_preparing_view(total)

        threading.Thread(target=self.prepare_robot_run_worker, args=(turns,), daemon=True).start()

    def build_preparing_view(self, total):
        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )
        ui.label(page, text="デフォルト実演の準備中", font="page_title", bg="main_card").pack(anchor="w")

        card = ui.bordered_frame(page, bg="card", border="border")
        card.pack(fill="x", pady=(ui.SPACING["section_y"], 0))
        self.prep_message_var = tk.StringVar(value="TTS生成を開始します")
        self.prep_progress_var = tk.DoubleVar(value=0)
        self.prep_count_var = tk.StringVar(value=f"0 / {total}")

        ui.variable_label(card, textvariable=self.prep_message_var, font="body_bold", bg="card", fg="text").pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]),
        )
        ttk.Progressbar(card, variable=self.prep_progress_var, maximum=total, mode="determinate").pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["small_gap"]),
        )
        ui.variable_label(card, textvariable=self.prep_count_var, font="small", bg="card", fg="muted").pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["card_y"]),
        )
        spinner = ttk.Progressbar(card, mode="indeterminate")
        spinner.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))
        spinner.start(12)

    def prepare_robot_run_worker(self, turns):
        total = self.count_tts_units(turns)
        completed = 0
        prepared_turns = []
        try:
            for turn_index, turn in enumerate(turns):
                prepared = copy.deepcopy(turn)
                if turn.get("role") != "staff":
                    prepared_turns.append(prepared)
                    continue

                prepared_parts = []
                parts = turn.get("intent_parts") or [{"intent": "explanation", "text": turn.get("text", "")}]
                for part in parts:
                    intent = part.get("intent", "explanation")
                    intent_data = self.get_intent_data(intent)
                    instructions = intent_data.get("tts_instructions", {})
                    for segment in self.split_speech_units(part.get("text", "")):
                        self.emit_prep_progress(
                            completed,
                            total,
                            f"{turn_index + 1}. {self.intent_label(intent)} を生成中: {segment[:28]}",
                        )
                        wav_path = self.tts_client.synthesize_to_wav(
                            text=segment,
                            instructions=instructions,
                            person=self.active_profile_get("speaker", None),
                        )
                        if wav_path is not None:
                            self.generated_wav_paths.append(str(wav_path))
                        prepared_parts.append(
                            {
                                "intent": intent,
                                "text": segment,
                                "wav_path": str(wav_path),
                                "intent_data": intent_data,
                            }
                        )
                        completed += 1
                        self.emit_prep_progress(completed, total, f"{completed} / {total} 件のWAVを生成しました")

                prepared["prepared_parts"] = prepared_parts
                prepared_turns.append(prepared)

            self.prepared_dialogue = prepared_turns
            self.prep_queue.put({"type": "done"})
            self.wake_ui()
        except Exception as e:
            self.prep_queue.put({"type": "error", "message": str(e)})
            self.wake_ui()

    def split_speech_units(self, text):
        units = []
        current = []
        for char in text:
            current.append(char)
            if char in "。！？?!":
                unit = "".join(current).strip()
                if unit:
                    units.append(unit)
                current = []
        rest = "".join(current).strip()
        if rest:
            units.append(rest)
        return units or [text]

    def count_tts_units(self, turns):
        total = 0
        for turn in turns:
            if turn.get("role") != "staff":
                continue
            parts = turn.get("intent_parts") or [{"intent": "explanation", "text": turn.get("text", "")}]
            for part in parts:
                total += len(self.split_speech_units(part.get("text", "")))
        return max(1, total)

    def emit_prep_progress(self, completed, total, message):
        self.prep_queue.put(
            {
                "type": "progress",
                "completed": completed,
                "total": total,
                "message": message,
            }
        )
        self.wake_ui()

    def wake_ui(self):
        try:
            self.event_generate("<<DefaultTalkTabQueue>>", when="tail")
        except Exception:
            pass

    def on_queue_event(self, _event=None):
        while True:
            try:
                item = self.prep_queue.get_nowait()
            except queue.Empty:
                break

            if item["type"] == "progress":
                self.prep_progress_var.set(item["completed"])
                self.prep_count_var.set(f"{item['completed']} / {item['total']}")
                self.prep_message_var.set(item["message"])
            elif item["type"] == "done":
                self.build_robot_run_view()
            elif item["type"] == "run_advance":
                self.advance_robot_run()
            elif item["type"] == "error":
                messagebox.showerror("TTS生成エラー", item["message"])
                self.status_var.set(f"TTS生成エラー: {item['message']}")
                self.return_to_default_view()

    def clear_page(self):
        if self.mic_panel is not None:
            try:
                self.mic_panel.stop()
            except Exception:
                pass
            self.mic_panel = None
        for child in self.winfo_children():
            child.destroy()

    def build_robot_run_view(self):
        from ..panels.mic_activity_panel import MicActivityPanel

        self.clear_page()
        self.run_state = "ready"
        self.run_index = 0

        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )
        self.lyric_frame = ui.frame(page, bg="main_card")
        self.lyric_frame.pack(fill="both", expand=True)
        self.render_lyrics_view()

        controls = ui.frame(page, bg="main_card")
        controls.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))
        ui.action_button(controls, text="実演開始", command=self.start_robot_run).pack(side="left")
        ui.sub_button(controls, text="停止", command=self.stop_robot_run).pack(side="left", padx=(ui.SPACING["small_gap"], 0))
        ui.sub_button(controls, text="デフォルト会話に戻る", command=self.return_to_default_view).pack(side="right")

        self.mic_panel = MicActivityPanel(
            page,
            title="客発話の切れ目検出",
            description="実環境の act 値が 1 以上の間を客の発話中として扱います。",
            on_speech_start=self.on_run_customer_speech_start,
            on_speech_end=self.on_run_customer_speech_end,
            status_var=self.status_var,
            activity_mode="robot_act",
            act_threshold=1,
        )
        self.mic_panel.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))
        self.status_var.set("デフォルト実演の準備ができました")

    def render_lyrics_view(self):
        if self.lyric_frame is None:
            return
        for child in self.lyric_frame.winfo_children():
            child.destroy()

        turns = self.prepared_dialogue or []
        start = max(0, self.run_index - 2)
        end = min(len(turns), self.run_index + 3)
        ui.frame(self.lyric_frame, bg="main_card").pack(fill="both", expand=True)
        for idx in range(start, end):
            turn = turns[idx]
            role = "客" if turn.get("role") == "customer" else "ロボット"
            bg = "panel" if idx == self.run_index else "card"
            font = "section_title" if idx == self.run_index else "body"
            card = ui.bordered_frame(self.lyric_frame, bg=bg, border="border")
            card.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["small_gap"]))
            ui.label(card, text=f"{idx + 1}. {role}", font="small", bg=bg, fg="muted").pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(ui.SPACING["compact_y"], 0),
            )
            ui.label(
                card,
                text=turn.get("text", ""),
                font=font,
                bg=bg,
                fg="text",
                wraplength=980,
                justify="left",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))
        ui.frame(self.lyric_frame, bg="main_card").pack(fill="both", expand=True)

    def start_robot_run(self):
        if not self.prepared_dialogue:
            return
        self.run_state = "running"
        self.run_index = 0
        self.render_lyrics_view()
        self.advance_robot_run()

    def stop_robot_run(self):
        self.run_state = "stopped"
        if self.mic_panel is not None:
            self.mic_panel.stop()
        try:
            self.tts_client.stop_preview()
        except Exception:
            pass
        self.cleanup_generated_wavs()
        self.status_var.set("デフォルト実演を停止しました")

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
            self.status_var.set("客の発話待ちです")
            if self.mic_panel is not None:
                self.mic_panel.start()
            return

        if self.mic_panel is not None:
            self.mic_panel.stop()
        threading.Thread(target=self.play_staff_turn_worker, args=(turn,), daemon=True).start()

    def on_run_customer_speech_start(self, _t):
        self.apply_listening_pose_for_run()
        self.status_var.set("客の発話中です")

    def on_run_customer_speech_end(self, _t):
        if self.run_state != "running":
            return
        if self.mic_panel is not None:
            self.mic_panel.stop()
        self.apply_understanding_pose_for_run(use_thinking_delay=self.should_use_thinking_after_customer())
        self.run_index += 1
        self.advance_robot_run()

    def play_staff_turn_worker(self, turn):
        try:
            parts = turn.get("prepared_parts", [])
            for part_index, part in enumerate(parts):
                if self.run_state != "running":
                    return
                self.apply_intent_motion(part)
                self.play_prepared_wav(part["wav_path"])
                if part_index + 1 < len(parts):
                    self.apply_sentence_pause()

            self.run_index += 1
            self.prep_queue.put({"type": "run_advance"})
            self.wake_ui()
        except Exception as e:
            self.prep_queue.put({"type": "error", "message": str(e)})
            self.wake_ui()

    def play_prepared_wav(self, wav_path):
        from ..audio.wav_silence import trim_silence_to_temp_wav

        trimmed = trim_silence_to_temp_wav(wav_path)
        done = threading.Event()
        duration = self.tts_client.get_wav_duration_sec(trimmed)
        if self.mic_panel is not None:
            self.mic_panel.pause_for(duration + 0.2, label="ロボット発話中")
        self.tts_client.preview_player.play_later(trimmed, done_event=done)
        done.wait()
        try:
            trimmed.unlink(missing_ok=True)
        except Exception:
            pass

    def apply_intent_motion(self, part):
        data = part.get("intent_data", {}) or {}
        face = data.get("face", {})
        if face:
            self.ensure_robot_client().send_emotion(
                face_type=face.get("type", "neutral"),
                level=int(face.get("level", 1)),
                priority=3,
                keeptime=3000,
            )
        bow = data.get("bow", {})
        if bow:
            self.ensure_robot_client().send_nod(
                amplitude=int(bow.get("amplitude", 7)),
                duration=int(bow.get("duration", 300)),
                times=1,
                priority=3,
            )

    def apply_sentence_pause(self):
        pause = self.active_profile_get_nested("sentence_pause", {}) or {}
        value = float(pause.get("value", 0.0))
        gaze = pause.get("gaze", {})
        lookaway = gaze.get("lookaway")
        if lookaway:
            if lookaway == "horizontal_random":
                lookaway = random.choice(["l", "r"])
            self.ensure_robot_client().send_lookaway(
                direction=lookaway,
                priority=int(gaze.get("priority", 4)),
                keeptime=int(gaze.get("keeptime", 800)),
            )
        time.sleep(max(0.0, value))

    def apply_listening_pose_for_run(self):
        listening = self.active_profile_get_nested("listening_pose", {}) or {}
        face = listening.get("face", {})
        nod = listening.get("nod", {})
        if face:
            self.ensure_robot_client().send_emotion(
                face_type=face.get("type", "neutral"),
                level=int(face.get("level", 1)),
                priority=3,
                keeptime=3000,
            )
        if nod and nod.get("id") != "none":
            self.ensure_robot_client().send_nod(
                amplitude=int(nod.get("amplitude", 10)),
                duration=int(nod.get("duration", 400)),
                times=int(nod.get("times", 1)),
                priority=int(nod.get("priority", 3)),
            )

    def should_use_thinking_after_customer(self):
        turns = self.prepared_dialogue or []
        next_index = self.run_index + 1
        if next_index >= len(turns):
            return False
        return self.should_insert_thinking(turns, next_index)

    def should_insert_thinking(self, turns, index):
        turn = turns[index]
        if turn.get("role") != "staff" or index == 0:
            return False
        previous = turns[index - 1]
        if previous.get("role") != "customer":
            return False
        markers = ("おすすめ", "どこ", "どれ", "時間", "初めて", "不安", "?", "？")
        if not any(marker in previous.get("text", "") for marker in markers):
            return False
        intents = {part.get("intent") for part in turn.get("intent_parts") or []}
        return bool(intents & {"explanation", "question", "smalltalk", "filler"})

    def apply_thinking_pose_for_run(self):
        thinking = self.active_profile_get_nested("thinking_pose", {}) or {}
        face = thinking.get("face", {})
        gaze = thinking.get("gaze", {})
        if face:
            self.ensure_robot_client().send_emotion(
                face_type=face.get("type", "neutral"),
                level=int(face.get("level", 1)),
                priority=3,
                keeptime=3000,
            )
        if gaze:
            self.ensure_robot_client().send_lookaway(
                direction=gaze.get("lookaway", "f"),
                priority=int(gaze.get("priority", 4)),
                keeptime=int(gaze.get("keeptime", 1500)),
            )

    def apply_understanding_pose_for_run(self, use_thinking_delay=False):
        understanding = self.active_profile_get_nested("understanding_pose", {}) or {}
        delay_data = self.active_profile_get_nested("response_delay", {}) or {}
        if use_thinking_delay:
            self.apply_thinking_pose_for_run()
            delay = delay_data.get("thinking_wait_after_detection", delay_data.get("wait_after_detection", 0.0))
        else:
            delay = delay_data.get("wait_after_detection", 0.0)
        time.sleep(max(0.0, float(delay)))

        face = understanding.get("face", {})
        nod = understanding.get("nod", {})
        if face:
            self.ensure_robot_client().send_emotion(
                face_type=face.get("type", "neutral"),
                level=int(face.get("level", 1)),
                priority=3,
                keeptime=3000,
            )
        if nod:
            self.ensure_robot_client().send_nod(
                amplitude=int(nod.get("amplitude", 10)),
                duration=int(nod.get("duration", 400)),
                times=int(nod.get("count", 1)),
                priority=int(nod.get("priority", 3)),
            )

    def finish_robot_run(self):
        self.run_state = "finished"
        if self.mic_panel is not None:
            self.mic_panel.stop()
        self.render_lyrics_view()
        self.cleanup_generated_wavs()
        self.status_var.set("デフォルト実演が終了しました")

    def return_to_default_view(self):
        self.cleanup_generated_wavs()
        self.clear_page()
        self.build_ui()
        self.refresh_scene_choices()

    def cleanup_generated_wavs(self, force=False):
        if not force and not self.delete_generated_wav_var.get():
            return
        for wav_path in list(self.generated_wav_paths):
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass
        self.generated_wav_paths = []

    def refresh_from_profile(self):
        self.render_current_scene()

    def destroy(self):
        self.run_state = "stopped"
        self.cleanup_generated_wavs()
        try:
            if self.mic_panel is not None:
                self.mic_panel.stop()
        except Exception:
            pass
        try:
            if self.tts_client is not None:
                self.tts_client.stop_preview()
        except Exception:
            pass
        try:
            if self.robot_client is not None:
                self.robot_client.close()
        except Exception:
            pass
        super().destroy()
