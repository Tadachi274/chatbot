import copy
from datetime import datetime
import os
from pathlib import Path
import queue
import random
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

from .. import ui_style as ui
from ..audio.wav_silence import trim_silence_to_temp_wav
from ..clients.example_generation_client import ExampleGenerationClient
from ..clients.robot_command_client import RobotCommandClient
from ..config import get_person_key_from_speaker
from ..config_default_profile import build_default_profile
from ..config_example import EXAMPLE_SCENES, EXAMPLE_VENUES
from ..panels.mic_activity_panel import MicActivityPanel


class ExampleSceneTab(tk.Frame):
    def __init__(
        self,
        parent,
        profile_store,
        status_var,
        tts_client=None,
        on_saved=None,
        venue_label=None,
        default_only=False,
    ):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.status_var = status_var
        self.tts_client = tts_client
        self.on_saved = on_saved
        self.generation_client = ExampleGenerationClient()
        self.robot_client = RobotCommandClient()
        self.fixed_venue_label = venue_label
        self.default_only = default_only
        self.default_profile = build_default_profile()

        self.venue_var = tk.StringVar(value=venue_label or EXAMPLE_VENUES[0]["label"])
        self.scene_var = tk.StringVar()
        self.staff_turn_var = tk.StringVar()
        self.version_var = tk.StringVar(value="案なし")
        self.scene_by_id = {scene["id"]: scene for scene in EXAMPLE_SCENES}

        self.style_summary_frame = None
        self.dialogue_frame = None
        self.expanded_meta = set()
        self.expanded_behavior = set()
        self.global_request_box = None
        self.turn_request_box = None
        self.scene_combo = None
        self.staff_turn_combo = None
        self.venue_notebook = None
        self.venue_tab_labels = {}
        self.generation_busy = False
        self.generation_thread = None
        self.generation_message_var = tk.StringVar(value="")
        self.generation_spinner = None
        self.generation_buttons = []
        self.prepared_dialogue = None
        self.generated_wav_paths = []
        self.delete_generated_wav_var = tk.BooleanVar(value=True)
        self.prep_queue = queue.SimpleQueue()
        self.prep_thread = None
        self._event_read_fd = None
        self._event_write_fd = None
        self._filehandler_registered = False
        self.run_state = "idle"
        self.run_index = 0
        self.lyric_frame = None
        self.mic_panel = None

        self.build_ui()
        self.setup_ui_event_pipe()
        self.refresh_scene_choices()

    def build_ui(self):
        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )

        if not self.default_only:
            ui.label(page, text="接客場面で試す", font="page_title", bg="main_card").pack(anchor="w")
            ui.label(
                page,
                text="保存した話し方設定を使って、場面ごとの店員発話をGPTで生成・修正します。",
                font="body",
                bg="main_card",
                fg="sub_text",
            ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        content = ui.scrollable_frame(page)

        self.build_selector_area(content)
        self.build_style_summary_area(content)
        self.build_dialogue_area(content)
        if not self.default_only:
            self.build_feedback_area(content)
        self.build_bottom_area(page)

    def build_selector_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        ui.label(section, text="場面選択", font="section_title", bg="panel").pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        if self.fixed_venue_label is None:
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

        row = ui.frame(section, bg="panel")
        row.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        scene_card = ui.bordered_frame(row, bg="card", border="border")
        scene_card.pack(side="left", fill="both", expand=True, padx=(0, ui.SPACING["small_gap"]))
        ui.label(scene_card, text="具体場面", font="small", bg="card", fg="muted").pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )
        self.scene_combo = ttk.Combobox(scene_card, textvariable=self.scene_var, state="readonly")
        self.scene_combo.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))
        self.scene_combo.bind("<<ComboboxSelected>>", lambda _event=None: self.on_scene_changed())

        if self.default_only:
            return

        version_card = ui.bordered_frame(row, bg="card", border="border")
        version_card.pack(side="left", fill="both", expand=True, padx=(0, ui.SPACING["small_gap"]))
        ui.label(version_card, text="生成履歴", font="small", bg="card", fg="muted").pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], 0),
        )
        ui.variable_label(
            version_card,
            textvariable=self.version_var,
            font="body_bold",
            bg="card",
            fg="text",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))

        nav_row = ui.frame(version_card, bg="card")
        nav_row.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))
        ui.sub_button(nav_row, text="デフォルトで試す", command=self.select_default_version).pack(side="left")
        ui.sub_button(nav_row, text="前案", command=lambda: self.move_version(-1)).pack(
            side="left",
            padx=(ui.SPACING["small_gap"], 0),
        )
        ui.sub_button(nav_row, text="次案", command=lambda: self.move_version(1)).pack(
            side="left",
            padx=(ui.SPACING["small_gap"], 0),
        )

    def build_combo_card(self, row, title, values, variable, on_selected):
        card = ui.bordered_frame(row, bg="card", border="border")
        card.pack(side="left", fill="both", expand=True, padx=(0, ui.SPACING["small_gap"]))
        ui.label(card, text=title, font="small", bg="card", fg="muted").pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )
        combo = ttk.Combobox(card, values=values, textvariable=variable, state="readonly")
        combo.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))
        combo.bind("<<ComboboxSelected>>", on_selected)

    def on_venue_tab_changed(self, _event=None):
        if self.venue_notebook is None or not self.venue_notebook.select():
            return

        tab_name = self.venue_notebook.select()
        label = self.venue_tab_labels.get(tab_name)
        if not label:
            return

        if self.venue_var.get() != label:
            self.venue_var.set(label)
            self.expanded_meta.clear()
            if self.scene_combo is not None:
                self.refresh_scene_choices()

    def build_style_summary_area(self, parent):
        if self.default_only:
            return

        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(section, text="現在の話し方設定", font="section_title", bg="panel").pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        self.style_summary_frame = ui.frame(section, bg="panel")
        self.style_summary_frame.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["section_y"]),
        )

    def build_dialogue_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(section, text="会話", font="section_title", bg="panel").pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        self.dialogue_frame = ui.frame(card, bg="card")
        self.dialogue_frame.pack(fill="x", padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])

    def build_feedback_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(section, text="修正要望", font="section_title", bg="panel").pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        ui.label(card, text="全体要望", font="body_bold", bg="card").pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]),
        )
        self.global_request_box = tk.Text(
            card,
            height=4,
            font=ui.FONTS["input"],
            bg=ui.COLORS["card"],
            fg=ui.COLORS["text"],
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=ui.COLORS["border"],
            highlightcolor=ui.COLORS["accent"],
            wrap="word",
        )
        self.global_request_box.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))

        whole_button = ui.sub_button(card, text="全体を再生成", command=self.generate_whole_scene)
        whole_button.pack(
            anchor="e",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["card_y"]),
        )
        self.generation_buttons.append(whole_button)

        ui.label(card, text="個別修正", font="body_bold", bg="card").pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["small_gap"]),
        )
        self.staff_turn_combo = ttk.Combobox(card, textvariable=self.staff_turn_var, state="readonly")
        self.staff_turn_combo.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["small_gap"]))

        self.turn_request_box = tk.Text(
            card,
            height=4,
            font=ui.FONTS["input"],
            bg=ui.COLORS["card"],
            fg=ui.COLORS["text"],
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=ui.COLORS["border"],
            highlightcolor=ui.COLORS["accent"],
            wrap="word",
        )
        self.turn_request_box.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))

        turn_button = ui.sub_button(card, text="選択した店員発話だけ再生成", command=self.generate_one_turn)
        turn_button.pack(
            anchor="e",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["card_y"]),
        )
        self.generation_buttons.append(turn_button)

    def build_bottom_area(self, parent):
        bottom = ui.frame(parent, bg="main_card")
        bottom.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))
        if self.default_only:
            ui.action_button(bottom, text="デフォルトでロボット実演", command=self.prepare_robot_run).pack(
                side="left",
            )
            tk.Checkbutton(
                bottom,
                text="実演後に生成WAVを削除",
                variable=self.delete_generated_wav_var,
                font=ui.FONTS["small"],
                bg=ui.COLORS["main_card"],
                fg=ui.COLORS["sub_text"],
                activebackground=ui.COLORS["main_card"],
                activeforeground=ui.COLORS["text"],
                selectcolor=ui.COLORS["card"],
            ).pack(side="left", padx=(ui.SPACING["gap"], 0))
            return

        generate_button = ui.action_button(bottom, text="選択場面を生成", command=self.generate_whole_scene)
        generate_button.pack(side="left")
        self.generation_buttons.append(generate_button)

        robot_button = ui.action_button(bottom, text="実際のロボットで試す", command=self.prepare_robot_run)
        robot_button.pack(
            side="left",
            padx=(ui.SPACING["small_gap"], 0),
        )
        self.generation_buttons.append(robot_button)

        generation_status = ui.frame(bottom, bg="main_card")
        generation_status.pack(side="left", fill="x", expand=True, padx=(ui.SPACING["gap"], 0))
        self.generation_spinner = ttk.Progressbar(generation_status, mode="indeterminate", length=140)
        ui.variable_label(
            generation_status,
            textvariable=self.generation_message_var,
            font="small",
            bg="main_card",
            fg="sub_text",
        ).pack(side="left")

        tk.Checkbutton(
            bottom,
            text="実演後に生成WAVを削除",
            variable=self.delete_generated_wav_var,
            font=ui.FONTS["small"],
            bg=ui.COLORS["main_card"],
            fg=ui.COLORS["sub_text"],
            activebackground=ui.COLORS["main_card"],
            activeforeground=ui.COLORS["text"],
            selectcolor=ui.COLORS["card"],
        ).pack(side="left", padx=(ui.SPACING["gap"], 0))

        ui.action_button(bottom, text="全体を保存", command=self.save_all).pack(side="right")

    def set_generation_busy(self, busy, message=""):
        self.generation_busy = busy
        self.generation_message_var.set(message)

        state = "disabled" if busy else "normal"
        for button in self.generation_buttons:
            try:
                button.configure(state=state)
            except tk.TclError:
                pass

        if self.scene_combo is not None:
            self.scene_combo.configure(state="disabled" if busy else "readonly")
        if self.staff_turn_combo is not None:
            self.staff_turn_combo.configure(state="disabled" if busy else "readonly")

        if self.generation_spinner is None:
            return

        if busy:
            self.generation_spinner.pack(side="left", padx=(ui.SPACING["small_gap"], 0))
            self.generation_spinner.start(12)
        else:
            self.generation_spinner.stop()
            self.generation_spinner.pack_forget()

    def refresh_scene_choices(self):
        venue_id = self.current_venue_id()
        scenes = [scene for scene in EXAMPLE_SCENES if scene["venue"] == venue_id]
        values = [scene["title"] for scene in scenes]
        self.scene_combo.configure(values=values)
        if values:
            self.scene_var.set(values[0])
        self.on_scene_changed()

    def on_scene_changed(self):
        self.render_current_scene()

    def current_venue_id(self):
        label = self.venue_var.get()
        for venue in EXAMPLE_VENUES:
            if venue["label"] == label:
                return venue["id"]
        return EXAMPLE_VENUES[0]["id"]

    def current_scene(self):
        title = self.scene_var.get()
        venue_id = self.current_venue_id()
        for scene in EXAMPLE_SCENES:
            if scene["venue"] == venue_id and scene["title"] == title:
                return scene
        return next(scene for scene in EXAMPLE_SCENES if scene["venue"] == venue_id)

    def get_results(self):
        if self.default_only:
            return {}
        return self.profile_store.get_example_results() or {}

    def get_scene_record(self, scene_id):
        return self.get_results().get(scene_id, {"active": -1, "versions": []})

    def is_default_profile_active(self, scene_id=None):
        if self.default_only:
            return True
        scene = self.current_scene() if scene_id is None else self.scene_by_id[scene_id]
        record = self.get_scene_record(scene["id"])
        return int(record.get("active", -1)) == -1 and bool(record.get("use_default_profile", False))

    def active_profile_data(self):
        if self.is_default_profile_active():
            return self.default_profile
        _active, version = self.get_active_version()
        if version and version.get("profile") and not self.current_profile_differs_from_version(version):
            return version["profile"]
        return self.profile_store.data

    def normalized_profile_snapshot(self, profile_data):
        snapshot = copy.deepcopy(profile_data or {})
        snapshot.pop("example_results", None)
        self.strip_style_sources(snapshot)
        speaker = snapshot.get("speaker", "")
        snapshot["speaker_person"] = get_person_key_from_speaker(speaker)
        return snapshot

    def strip_style_sources(self, value):
        if isinstance(value, dict):
            value.pop("style_sources", None)
            for child in value.values():
                self.strip_style_sources(child)
        elif isinstance(value, list):
            for child in value:
                self.strip_style_sources(child)

    def current_profile_snapshot(self):
        if self.is_default_profile_active():
            return self.normalized_profile_snapshot(self.default_profile)
        return self.normalized_profile_snapshot(self.profile_store.data)

    def current_profile_differs_from_version(self, version):
        saved_profile = version.get("profile")
        if not saved_profile:
            return False
        return self.current_profile_snapshot() != self.normalized_profile_snapshot(saved_profile)

    def active_profile_get(self, key, default=None):
        return self.active_profile_data().get(key, default)

    def active_profile_get_nested(self, key, default=None):
        value = self.active_profile_data().get(key)
        if value is None:
            return default
        return value

    def get_active_version(self, scene_id=None):
        scene = self.current_scene() if scene_id is None else self.scene_by_id[scene_id]
        record = self.get_scene_record(scene["id"])
        active = int(record.get("active", -1))
        versions = record.get("versions", [])
        if 0 <= active < len(versions):
            return active, versions[active]
        return -1, None

    def save_scene_version(self, scene_id, version):
        results = self.get_results()
        record = results.get(scene_id, {"active": -1, "versions": []})
        versions = record.get("versions", [])
        versions.append(version)
        record["versions"] = versions
        record["active"] = len(versions) - 1
        record["use_default_profile"] = False
        results[scene_id] = record
        self.profile_store.set_example_results(results)

    def set_active_version(self, scene_id, active, use_default_profile=None):
        results = self.get_results()
        record = results.get(scene_id, {"active": -1, "versions": []})
        versions = record.get("versions", [])
        if active == -1 or 0 <= active < len(versions):
            record["active"] = active
            if use_default_profile is None:
                use_default_profile = active == -1
            record["use_default_profile"] = bool(use_default_profile)
            results[scene_id] = record
            self.profile_store.set_example_results(results)

    def select_default_version(self):
        scene = self.current_scene()
        self.set_active_version(scene["id"], -1, use_default_profile=True)
        self.render_current_scene()
        self.status_var.set("接客例をデフォルト文・デフォルト動作に戻しました。生成履歴は保持しています")

    def move_version(self, direction):
        scene = self.current_scene()
        record = self.get_scene_record(scene["id"])
        versions = record.get("versions", [])
        if not versions:
            if direction <= 0:
                self.select_default_version()
            return
        active = int(record.get("active", 0)) + direction
        active = max(-1, min(active, len(versions) - 1))
        self.set_active_version(scene["id"], active)
        self.render_current_scene()

    def render_current_scene(self):
        scene = self.current_scene()
        active, version = self.get_active_version(scene["id"])
        turns = version["turns"] if version else self.base_turns(scene)
        turns = self.apply_speaker_tone_to_turns(turns)
        turns = self.apply_fillers_to_turns(turns)

        self.render_style_summary()

        for child in self.dialogue_frame.winfo_children():
            child.destroy()

        for index, turn in enumerate(turns):
            if self.should_insert_thinking_card(turns, index):
                self.render_thinking_card(self.dialogue_frame, index)
            self.render_turn_card(self.dialogue_frame, index, turn)

        self.refresh_staff_turn_choices(turns)

        record = self.get_scene_record(scene["id"])
        versions = record.get("versions", [])
        if version:
            self.version_var.set(f"{active + 1} / {len(versions)}")
        else:
            self.version_var.set(f"デフォルト / {len(versions)}案")

    def render_style_summary(self):
        if self.style_summary_frame is None:
            return

        for child in self.style_summary_frame.winfo_children():
            child.destroy()

        values = [
            ("設定元", self.active_profile_source_label()),
            ("話者", self.get_speaker_label()),
            ("敬語", self.get_setting_label("politeness")),
            ("親しみ", self.get_setting_label("intimacy")),
            ("語彙", self.get_setting_label("vocabulary")),
            ("長さ", self.get_setting_label("length")),
            ("詳細", self.get_style_detail_summary()),
            ("特別考慮", self.get_special_consideration_summary()),
        ]

        for title, value in values:
            chip = ui.bordered_frame(self.style_summary_frame, bg="card", border="border")
            chip.pack(side="left", fill="x", expand=True, padx=(0, ui.SPACING["small_gap"]))
            ui.label(
                chip,
                text=f"{title}: {value}",
                font="body_bold",
                bg="card",
                fg="text",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=ui.SPACING["compact_y"])

    def active_profile_source_label(self):
        if self.is_default_profile_active():
            return "デフォルト"

        _active, version = self.get_active_version()
        if version and version.get("profile"):
            if self.current_profile_differs_from_version(version):
                return "現在の設定（未保存・未生成）"
            created_at = version.get("created_at", "")
            suffix = f" {created_at}" if created_at else ""
            return f"生成時設定{suffix}"
        if version:
            return "生成履歴（設定未保存）"
        return "現在の設定"

    def render_summary_chip(self, parent, title, value, wide=False):
        card = ui.bordered_frame(parent, bg="card", border="border")
        card.pack(
            side="left",
            fill="both",
            expand=wide,
            padx=(0, ui.SPACING["small_gap"]),
        )
        ui.label(card, text=title, font="small", bg="card", fg="muted").pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], 0),
        )
        ui.label(card, text=value, font="body_bold", bg="card", fg="text", wraplength=260).pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

    def render_turn_card(self, parent, index, turn):
        row = ui.frame(parent, bg="card")
        row.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))

        is_staff = turn["role"] == "staff"
        bubble_bg = "main_card" if is_staff else "panel"
        text_card = ui.bordered_frame(row, bg=bubble_bg, border="border")
        if is_staff:
            text_card.pack(fill="x", expand=True, padx=(0, ui.SPACING["small_gap"]))
        else:
            text_card.pack(side="left", fill="x", expand=True, padx=(0, ui.SPACING["small_gap"]))

        role = "店員" if is_staff else "客"
        ui.label(
            text_card,
            text=f"{index + 1}. {role}",
            font="small",
            bg=bubble_bg,
            fg="muted",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["compact_y"], 0))
        ui.label(
            text_card,
            text=turn["text"],
            font="body",
            bg=bubble_bg,
            fg="text",
            wraplength=980 if is_staff else 620,
            justify="left",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))

        if is_staff:
            meta = ui.bordered_frame(row, bg="panel", border="soft_border")
            meta.pack(fill="x", expand=True, pady=(ui.SPACING["small_gap"], 0))
            self.render_staff_meta(meta, turn, index)
        else:
            meta = ui.bordered_frame(row, bg="panel", border="soft_border")
            meta.pack(side="left", fill="y", padx=(0, ui.SPACING["small_gap"]))
            self.render_customer_behavior_meta(meta, index)

    def render_customer_behavior_meta(self, parent, index):
        header = ui.frame(parent, bg="panel")
        header.pack(fill="x")

        key = f"customer:{index}"
        expanded = key in self.expanded_behavior
        ui.sub_button(
            header,
            text=("▼ 聴く姿 / 理解した姿" if expanded else "▶ 聴く姿 / 理解した姿"),
            command=lambda item_key=key: self.toggle_behavior_meta(item_key),
        ).pack(
            anchor="w",
            padx=ui.SPACING["compact_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )

        if not expanded:
            return

        listening = self.active_profile_get_nested("listening_pose", {}) or {}
        understanding = self.active_profile_get_nested("understanding_pose", {}) or {}

        self.render_behavior_detail(
            parent,
            title="客の発話中",
            body=self.listening_behavior_text(listening),
        )
        self.render_behavior_detail(
            parent,
            title="客の発話直後",
            body=self.understanding_behavior_text(understanding),
        )

    def render_thinking_card(self, parent, index):
        thinking = self.active_profile_get_nested("thinking_pose", {}) or {}
        row = ui.frame(parent, bg="card")
        row.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))

        card = ui.bordered_frame(row, bg="panel", border="soft_border")
        card.pack(fill="x", padx=(ui.SPACING["section_x"], ui.SPACING["section_x"]))

        header = ui.frame(card, bg="panel")
        header.pack(fill="x")

        key = f"thinking:{index}"
        expanded = key in self.expanded_behavior
        ui.sub_button(
            header,
            text=("▼ 考え中" if expanded else "▶ 考え中"),
            command=lambda item_key=key: self.toggle_behavior_meta(item_key),
        ).pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )

        ui.label(
            card,
            text="すぐに返答が難しいため、返答前に考える姿を入れます。",
            font="small",
            bg="panel",
            fg="muted",
            wraplength=920,
            justify="left",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))

        if expanded:
            self.render_behavior_detail(
                card,
                title="考えている姿",
                body=self.thinking_behavior_text(thinking),
            )

    def render_behavior_detail(self, parent, title, body):
        bubble = ui.bordered_frame(parent, bg="card", border="border")
        bubble.pack(fill="x", padx=ui.SPACING["compact_x"], pady=(0, ui.SPACING["small_gap"]))
        ui.label(
            bubble,
            text=title,
            font="body_bold",
            bg="card",
            fg="text",
            justify="left",
        ).pack(anchor="w", padx=ui.SPACING["compact_x"], pady=(ui.SPACING["compact_y"], 0))
        ui.label(
            bubble,
            text=body,
            font="small",
            bg="card",
            fg="muted",
            wraplength=360,
            justify="left",
        ).pack(anchor="w", fill="x", padx=ui.SPACING["compact_x"], pady=(0, ui.SPACING["compact_y"]))

    def render_staff_meta(self, parent, turn, index):
        parts = turn.get("intent_parts") or [{"intent": "explanation", "text": turn["text"]}]
        header = ui.frame(parent, bg="panel")
        header.pack(fill="x")

        expanded = index in self.expanded_meta
        ui.sub_button(
            header,
            text=("▼ Dialog Act / 適用設定" if expanded else "▶ Dialog Act / 適用設定"),
            command=lambda turn_index=index: self.toggle_staff_meta(turn_index),
        ).pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )

        if not expanded:
            return

        for part in parts:
            intent = part.get("intent", "explanation")
            bubble = ui.bordered_frame(parent, bg="card", border="border")
            bubble.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["small_gap"]))

            intent_data = self.get_intent_data(intent)
            ui.label(
                bubble,
                text=f"{self.intent_label(intent)}: {part.get('text', '')}",
                font="small",
                bg="card",
                fg="text",
                wraplength=920,
                justify="left",
            ).pack(anchor="w", fill="x", padx=ui.SPACING["compact_x"], pady=(ui.SPACING["compact_y"], 0))

            details = self.intent_detail_text(intent, intent_data)
            ui.label(
                bubble,
                text=details,
                font="small",
                bg="card",
                fg="muted",
                wraplength=920,
                justify="left",
            ).pack(anchor="w", fill="x", padx=ui.SPACING["compact_x"], pady=(0, ui.SPACING["compact_y"]))

    def toggle_staff_meta(self, index):
        if index in self.expanded_meta:
            self.expanded_meta.remove(index)
        else:
            self.expanded_meta.add(index)
        self.render_current_scene()

    def toggle_behavior_meta(self, key):
        if key in self.expanded_behavior:
            self.expanded_behavior.remove(key)
        else:
            self.expanded_behavior.add(key)
        self.render_current_scene()

    def get_setting_label(self, key):
        data = self.active_profile_get_nested(key, {}) or {}
        return data.get("label", data.get("id", "未設定"))

    def get_style_detail_summary(self):
        data = self.active_profile_get_nested("style_detail", {}) or {}
        labels = data.get("labels", {})
        if not labels:
            return "未設定"
        values = [value for value in labels.values() if value and value != "なし"]
        return " / ".join(values[:3]) if values else "なし"

    def get_special_consideration_summary(self):
        data = self.active_profile_get_nested("special_consideration", {}) or {}
        text = (data.get("text") or "").strip()
        if not text:
            return "なし"
        return text[:28] + ("..." if len(text) > 28 else "")

    def get_speaker_person_key(self):
        speaker = self.active_profile_get("speaker", "nozomi_emo_22_standard")
        return get_person_key_from_speaker(speaker)

    def get_speaker_label(self):
        person_key = self.get_speaker_person_key()
        if person_key == "kenta":
            return "けんた"
        if person_key == "nozomi":
            return "のぞみ"
        return self.active_profile_get("speaker", "未設定")

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

    def intent_detail_text(self, intent, data):
        face = data.get("face", {})
        voice = data.get("voice", {})
        bow = data.get("bow", {})
        techniques = data.get("techniques", [])

        chunks = [
            f"表情: {face.get('label', face.get('id', '未設定'))}",
            f"声色: {voice.get('label', voice.get('id', '未設定'))}",
        ]

        if techniques:
            chunks.append(f"テクニック: {', '.join(self.technique_label(t) for t in techniques)}")
        else:
            chunks.append("テクニック: なし")

        if bow:
            chunks.append(f"お辞儀: {bow.get('label', bow.get('id', '未設定'))}")

        if intent == "smalltalk":
            style = data.get("style", {})
            if style:
                chunks.append(
                    "雑談話し方: "
                    f"敬語 {style.get('politeness', '-')} / "
                    f"親しみ {style.get('intimacy', '-')} / "
                    f"語彙 {style.get('vocabulary', '-')} / "
                    f"長さ {style.get('length', '-')}"
                )

        if intent == "filler":
            chunks.append(f"使用: {'あり' if data.get('enabled') else 'なし'}")
            phrases = data.get("phrases", [])
            if phrases:
                chunks.append(f"候補: {', '.join(phrases)}")

        return "  |  ".join(chunks)

    def technique_label(self, key):
        return {
            "seasonal_topic": "季節",
            "time_topic": "時間",
            "consideration": "配慮",
            "empathy": "共感",
            "evidence": "根拠",
            "expertise": "専門",
            "paraphrase": "言換",
            "summary": "要約",
            "step_by_step": "段階",
            "proactive": "先回り",
            "goal_clarity": "目的",
            "purpose": "目的",
            "permission": "許可",
            "alternative": "代替",
            "positive_reframe": "前向き",
            "name_call": "名前",
            "rich_emotion": "感情豊か",
        }.get(key, key)

    def face_detail_text(self, face):
        if not face:
            return "表情: 未設定"

        label = face.get("label", face.get("id", "未設定"))
        face_type = face.get("type", "-")
        level = face.get("level", "-")
        return f"表情: {label} / /emotion {face_type} {level}"

    def nod_detail_text(self, nod):
        if not nod:
            return "うなづき: 未設定"

        label = nod.get("label", nod.get("id", "未設定"))
        amplitude = nod.get("amplitude", "-")
        duration = nod.get("duration", "-")
        count = nod.get("count", nod.get("times", "-"))
        return f"うなづき: {label} / /nod {amplitude} {duration} × {count}"

    def gaze_detail_text(self, gaze):
        if not gaze:
            return "視線: 未設定"

        label = gaze.get("label", gaze.get("id", "未設定"))
        lookaway = gaze.get("lookaway", "-")
        return f"視線: {label} / lookaway={lookaway}"

    def listening_behavior_text(self, listening):
        face = listening.get("face", {})
        nod = listening.get("nod", {})
        amount = listening.get("amount", {})
        voice = listening.get("backchannel_voice", {})

        timing = amount.get("label", amount.get("id", "未設定"))
        silence = amount.get("silence_sec", "-")
        voice_mode = voice.get("mode_label", voice.get("mode", "未設定"))
        word = voice.get("text", voice.get("word_id", "未設定"))

        return "  |  ".join(
            [
                f"タイミング: 客の発話中、文節の間や短い沈黙で相槌 / 量: {timing} / 沈黙目安: {silence}秒",
                self.face_detail_text(face),
                self.nod_detail_text(nod),
                f"音声相槌: {voice_mode} / 候補: {word}",
            ]
        )

    def understanding_behavior_text(self, understanding):
        face = understanding.get("face", {})
        nod = understanding.get("nod", {})
        delay_source = understanding.get("response_delay_source", "response_delay.wait_after_detection")
        return "  |  ".join(
            [
                "タイミング: 客の発話が終わった直後、言葉を理解したことを示す",
                self.face_detail_text(face),
                self.nod_detail_text(nod),
                f"待ち時間: {delay_source}",
                "理解の言葉: 接客例では使わない",
            ]
        )

    def thinking_behavior_text(self, thinking):
        face = thinking.get("face", {})
        gaze = thinking.get("gaze", {})
        return "  |  ".join(
            [
                "タイミング: 回答を考える必要があるスタッフ発話の直前",
                self.face_detail_text(face),
                self.gaze_detail_text(gaze),
            ]
        )

    def should_insert_thinking_card(self, turns, index):
        turn = turns[index]
        if turn.get("role") != "staff" or index == 0:
            return False

        previous = turns[index - 1]
        if previous.get("role") != "customer":
            return False

        previous_text = previous.get("text", "")
        if not self.is_difficult_customer_prompt(previous_text):
            return False

        parts = turn.get("intent_parts") or []
        intents = {part.get("intent") for part in parts}
        if intents and intents <= {"acceptance", "request", "gratitude", "greeting"}:
            return False

        return bool(intents & {"explanation", "question", "smalltalk", "filler"})

    def is_difficult_customer_prompt(self, text):
        markers = (
            "おすすめ",
            "ありますか",
            "できますか",
            "行けますか",
            "似合いますか",
            "いいですか",
            "どう",
            "どこ",
            "どれ",
            "どの",
            "はぐれ",
            "汚れて",
            "在庫",
            "時間",
            "初めて",
            "不安",
            "?",
            "？",
        )
        return any(marker in text for marker in markers)

    def refresh_staff_turn_choices(self, turns):
        if self.staff_turn_combo is None:
            return

        values = [
            f"{index + 1}. {turn['text'][:48]}"
            for index, turn in enumerate(turns)
            if turn["role"] == "staff"
        ]
        self.staff_turn_combo.configure(values=values)
        if values:
            self.staff_turn_var.set(values[0])
        else:
            self.staff_turn_var.set("")

    def base_turns(self, scene):
        return [
            {
                "role": turn["role"],
                "text": turn.get("text", turn.get("base_text", "")),
                "intent_parts": turn.get("intent_parts", []),
            }
            for turn in scene["turns"]
        ]

    def apply_speaker_tone_to_turns(self, turns):
        politeness_id = self.active_profile_get_nested("politeness", {}).get("id", "")
        if self.get_speaker_person_key() != "nozomi" or politeness_id != "casual":
            return turns

        rendered = copy.deepcopy(turns)
        for turn in rendered:
            if turn.get("role") != "staff":
                continue

            turn["text"] = self.remove_kenta_casual_suffix(turn.get("text", ""))
            for part in turn.get("intent_parts") or []:
                part["text"] = self.remove_kenta_casual_suffix(part.get("text", ""))

        return rendered

    def remove_kenta_casual_suffix(self, text):
        replacements = (
            ("っすか。", "かな。"),
            ("っすか？", "かな？"),
            ("っすね。", "だね。"),
            ("っすね？", "だよね？"),
            ("っすよ。", "だよ。"),
            ("っす。", "だよ。"),
            ("っす", ""),
        )
        for before, after in replacements:
            text = text.replace(before, after)
        return text

    def apply_fillers_to_turns(self, turns):
        filler = self.active_profile_get_nested("filler", {}) or {}
        if not filler.get("enabled"):
            return turns

        phrases = filler.get("phrases", [])
        if not phrases:
            return turns

        phrase = phrases[0]
        rendered = copy.deepcopy(turns)

        for index, turn in enumerate(rendered):
            if not self.should_insert_filler(rendered, index, phrase):
                continue

            filler_text = f"{phrase}、"
            turn["text"] = f"{filler_text}{turn['text']}"
            turn["intent_parts"] = [
                {"intent": "filler", "text": filler_text},
                *(turn.get("intent_parts") or []),
            ]

        return rendered

    def should_insert_filler(self, turns, index, phrase):
        turn = turns[index]
        if turn.get("role") != "staff":
            return False

        if turn.get("text", "").startswith(phrase):
            return False

        parts = turn.get("intent_parts") or []
        intents = {part.get("intent") for part in parts}
        if "filler" in intents:
            return False

        if intents & {"greeting", "apology", "gratitude", "acceptance", "request"}:
            return False

        if not intents & {"explanation", "question", "smalltalk"}:
            return False

        if index == 0 or turns[index - 1].get("role") != "customer":
            return False

        previous_text = turns[index - 1].get("text", "")
        question_markers = ("?", "？", "か。", "ありますか", "できますか", "いいですか", "ですか", "ますか")
        return any(marker in previous_text for marker in question_markers)

    def profile_snapshot(self):
        return self.current_profile_snapshot()

    def current_turns(self):
        scene = self.current_scene()
        _active, version = self.get_active_version(scene["id"])
        turns = version["turns"] if version else self.base_turns(scene)
        return self.apply_speaker_tone_to_turns(turns)

    def get_global_request(self):
        return self.global_request_box.get("1.0", "end").strip()

    def get_turn_request(self):
        return self.turn_request_box.get("1.0", "end").strip()

    def generate_whole_scene(self):
        if self.generation_busy:
            return

        scene = self.current_scene()
        self.profile_store.save()
        active, version = self.get_active_version(scene["id"])
        global_request = self.get_global_request()
        current_dialogue = version["turns"] if version else None
        profile = self.profile_snapshot()

        self.status_var.set("接客場面を生成中です")
        self.set_generation_busy(True, "生成中です。少しお待ちください")

        self.generation_thread = threading.Thread(
            target=self.generate_whole_scene_worker,
            args=(scene, profile, global_request, current_dialogue, active),
            daemon=True,
        )
        self.generation_thread.start()

    def generate_whole_scene_worker(self, scene, profile, global_request, current_dialogue, active):
        try:
            if current_dialogue is not None:
                result = self.generation_client.revise_scene(
                    scene=scene,
                    profile=profile,
                    current_dialogue=current_dialogue,
                    global_request=global_request,
                )
            else:
                result = self.generation_client.generate_scene(
                    scene=scene,
                    profile=profile,
                    global_request=global_request,
                )

            self.prep_queue.put(
                {
                    "type": "scene_generation_done",
                    "scene_id": scene["id"],
                    "request": global_request,
                    "result": result,
                    "profile": profile,
                    "previous_active": active,
                }
            )
            self.wake_ui_event_loop()
        except Exception as e:
            self.prep_queue.put({"type": "scene_generation_error", "message": str(e)})
            self.wake_ui_event_loop()

    def generate_one_turn(self):
        if self.generation_busy:
            return

        scene = self.current_scene()
        request = self.get_turn_request()
        if not request:
            messagebox.showwarning("確認", "修正したい理由や方向性を入力してください。")
            return

        selected_index = self.selected_staff_turn_index()
        if selected_index is None:
            messagebox.showwarning("確認", "修正する店員発話を選択してください。")
            return

        self.profile_store.save()
        current_turns = self.current_turns()
        profile = self.profile_snapshot()
        active, _version = self.get_active_version(scene["id"])

        self.status_var.set("選択した店員発話を再生成中です")
        self.set_generation_busy(True, "選択した発話を生成中です。少しお待ちください")

        self.generation_thread = threading.Thread(
            target=self.generate_one_turn_worker,
            args=(scene, profile, current_turns, selected_index, request, active),
            daemon=True,
        )
        self.generation_thread.start()

    def generate_one_turn_worker(self, scene, profile, current_turns, selected_index, request, active):
        try:
            result = self.generation_client.revise_turn(
                scene=scene,
                profile=profile,
                current_dialogue=current_turns,
                turn_index=selected_index,
                turn_request=request,
            )
            self.prep_queue.put(
                {
                    "type": "turn_generation_done",
                    "scene_id": scene["id"],
                    "request": request,
                    "result": result,
                    "current_turns": current_turns,
                    "profile": profile,
                    "target_turn_index": selected_index,
                    "previous_active": active,
                }
            )
            self.wake_ui_event_loop()
        except Exception as e:
            self.prep_queue.put({"type": "turn_generation_error", "message": str(e)})
            self.wake_ui_event_loop()

    def prepare_robot_run(self):
        if self.tts_client is None:
            messagebox.showerror("確認", "TTSクライアントが未設定です。")
            return

        turns = self.apply_fillers_to_turns(
            self.apply_speaker_tone_to_turns(self.current_turns())
        )

        staff_parts = self.count_tts_units(turns)
        self.cleanup_generated_wavs()
        self.generated_wav_paths = []

        self.clear_page()
        self.build_preparing_view(total=max(1, staff_parts))

        self.prep_thread = threading.Thread(
            target=self.prepare_robot_run_worker,
            args=(turns,),
            daemon=True,
        )
        self.prep_thread.start()

    def clear_page(self):
        if self.mic_panel is not None:
            try:
                self.mic_panel.stop()
            except Exception:
                pass
            self.mic_panel = None

        for child in self.winfo_children():
            child.destroy()

    def build_preparing_view(self, total):
        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )

        ui.label(page, text="ロボット実演の準備中", font="page_title", bg="main_card").pack(anchor="w")
        ui.label(
            page,
            text="各スタッフ発話をDAごとの声色でWAV化しています。",
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

        progress = ttk.Progressbar(
            card,
            variable=self.prep_progress_var,
            maximum=total,
            mode="determinate",
        )
        progress.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["small_gap"]))

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

    def prepare_robot_run_worker(self, turns):
        total = self.count_tts_units(turns)
        total = max(1, total)
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
                    text = part.get("text", "").strip()
                    if not text:
                        continue

                    intent_data = self.get_intent_data(intent)
                    instructions = intent_data.get("tts_instructions", {})
                    for segment in self.split_speech_units(text):
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
                        self.emit_prep_progress(
                            completed,
                            total,
                            f"{completed} / {total} 件のWAVを生成しました",
                        )

                prepared["prepared_parts"] = prepared_parts
                prepared_turns.append(prepared)

            self.prepared_dialogue = prepared_turns
            self.prep_queue.put({"type": "done"})
            self.wake_ui_event_loop()
        except Exception as e:
            self.prep_queue.put({"type": "error", "message": str(e)})
            self.wake_ui_event_loop()

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
        self.wake_ui_event_loop()

    def on_robot_prep_progress(self, _event=None):
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
            elif item["type"] == "error":
                messagebox.showerror("TTS生成エラー", item["message"])
                self.status_var.set(f"TTS生成エラー: {item['message']}")
                self.return_to_example_view()
            elif item["type"] == "run_advance":
                self.advance_robot_run()
            elif item["type"] == "scene_generation_done":
                self.on_scene_generation_done(item)
            elif item["type"] == "scene_generation_error":
                self.set_generation_busy(False)
                messagebox.showerror("生成エラー", item["message"])
                self.status_var.set(f"接客場面生成エラー: {item['message']}")
            elif item["type"] == "turn_generation_done":
                self.on_turn_generation_done(item)
            elif item["type"] == "turn_generation_error":
                self.set_generation_busy(False)
                messagebox.showerror("生成エラー", item["message"])
                self.status_var.set(f"店員発話生成エラー: {item['message']}")

    def on_scene_generation_done(self, item):
        result = item["result"]
        self.save_scene_version(
            item["scene_id"],
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "kind": "whole",
                "request": item["request"],
                "summary": result.get("summary", ""),
                "turns": result["turns"],
                "profile": item["profile"],
                "previous_active": item["previous_active"],
            },
        )
        self.set_generation_busy(False)
        self.render_current_scene()
        self.status_var.set("接客場面を生成しました")

    def on_turn_generation_done(self, item):
        result = item["result"]
        new_turns = copy.deepcopy(item["current_turns"])
        replacement = result["turn"]
        replacement["role"] = "staff"
        new_turns[item["target_turn_index"]] = replacement

        self.save_scene_version(
            item["scene_id"],
            {
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "kind": "turn",
                "request": item["request"],
                "summary": result.get("reason", ""),
                "turns": new_turns,
                "profile": item["profile"],
                "target_turn_index": item["target_turn_index"],
                "previous_active": item["previous_active"],
            },
        )
        self.set_generation_busy(False)
        self.render_current_scene()
        self.status_var.set("選択した店員発話を再生成しました")

    def setup_ui_event_pipe(self):
        self.bind("<<ExampleSceneTabQueue>>", self._handle_queue_event, add="+")

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
                self.on_robot_prep_progress()
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
        self.on_robot_prep_progress()

    def _handle_queue_event(self, _event=None):
        self.on_robot_prep_progress()

    def generate_queue_event(self):
        try:
            self.event_generate("<<ExampleSceneTabQueue>>", when="tail")
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

    def build_robot_run_view(self):
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

        if not self.default_only:
            ui.label(page, text="ロボットで接客例を試す", font="page_title", bg="main_card").pack(anchor="w")
            ui.label(
                page,
                text="客の発話終了をマイクで検出し、理解した姿を見せてからロボット発話へ進みます。",
                font="body",
                bg="main_card",
                fg="sub_text",
            ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        self.lyric_frame = ui.frame(page, bg="main_card")
        self.lyric_frame.pack(fill="both", expand=True)
        self.render_lyrics_view()

        controls = ui.frame(page, bg="main_card")
        controls.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))
        ui.action_button(controls, text="実演開始", command=self.start_robot_run).pack(side="left")
        ui.sub_button(controls, text="停止", command=self.stop_robot_run).pack(
            side="left",
            padx=(ui.SPACING["small_gap"], 0),
        )
        ui.sub_button(controls, text="接客例に戻る", command=self.return_to_example_view).pack(side="right")

        self.mic_panel = MicActivityPanel(
            page,
            title="客発話の切れ目検出",
            description="実環境の act 値が 1 以上の間を客の発話中として扱い、発話終了後に次へ進みます。",
            on_speech_start=self.on_run_customer_speech_start,
            on_speech_end=self.on_run_customer_speech_end,
            status_var=self.status_var,
            activity_mode="robot_act",
            act_threshold=1,
        )
        self.mic_panel.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))
        self.status_var.set("ロボット実演の準備ができました")

    def render_lyrics_view(self):
        if self.lyric_frame is None:
            return

        for child in self.lyric_frame.winfo_children():
            child.destroy()

        turns = self.prepared_dialogue or []
        start = max(0, self.run_index - 2)
        end = min(len(turns), self.run_index + 3)

        spacer_top = ui.frame(self.lyric_frame, bg="main_card")
        spacer_top.pack(fill="both", expand=True)

        for idx in range(start, end):
            turn = turns[idx]
            is_current = idx == self.run_index
            role = "客" if turn.get("role") == "customer" else "ロボット"
            bg = "panel" if is_current else "card"
            font = "section_title" if is_current else "body"
            card = ui.bordered_frame(self.lyric_frame, bg=bg, border="border")
            card.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["small_gap"]))
            ui.label(
                card,
                text=f"{idx + 1}. {role}",
                font="small",
                bg=bg,
                fg="muted",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["compact_y"], 0))
            ui.label(
                card,
                text=turn.get("text", ""),
                font=font,
                bg=bg,
                fg="text",
                wraplength=980,
                justify="left",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))

        spacer_bottom = ui.frame(self.lyric_frame, bg="main_card")
        spacer_bottom.pack(fill="both", expand=True)

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
        self.status_var.set("ロボット実演を停止しました")

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

        self.apply_understanding_pose_for_run(
            use_thinking_delay=self.should_use_thinking_after_customer()
        )
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
            self.wake_ui_event_loop()
        except Exception as e:
            self.prep_queue.put({"type": "error", "message": str(e)})
            self.wake_ui_event_loop()

    def play_prepared_wav(self, wav_path):
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
            self.robot_client.send_emotion(
                face_type=face.get("type", "neutral"),
                level=int(face.get("level", 1)),
                priority=3,
                keeptime=3000,
            )

        bow = data.get("bow", {})
        if bow:
            self.robot_client.send_nod(
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
            self.robot_client.send_lookaway(
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
            self.robot_client.send_emotion(
                face_type=face.get("type", "neutral"),
                level=int(face.get("level", 1)),
                priority=3,
                keeptime=3000,
            )
        if nod and nod.get("id") != "none":
            self.robot_client.send_nod(
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
        return self.should_insert_thinking_card(turns, next_index)

    def apply_thinking_pose_for_run(self):
        thinking = self.active_profile_get_nested("thinking_pose", {}) or {}
        face = thinking.get("face", {})
        gaze = thinking.get("gaze", {})
        if face:
            self.robot_client.send_emotion(
                face_type=face.get("type", "neutral"),
                level=int(face.get("level", 1)),
                priority=3,
                keeptime=3000,
            )
        if gaze:
            self.robot_client.send_lookaway(
                direction=gaze.get("lookaway", "f"),
                priority=int(gaze.get("priority", 4)),
                keeptime=int(gaze.get("keeptime", 1500)),
            )

    def apply_understanding_pose_for_run(self, use_thinking_delay=False):
        understanding = self.active_profile_get_nested("understanding_pose", {}) or {}
        face = understanding.get("face", {})
        nod = understanding.get("nod", {})
        delay_data = self.active_profile_get_nested("response_delay", {}) or {}
        if use_thinking_delay:
            self.apply_thinking_pose_for_run()
            delay = delay_data.get(
                "thinking_wait_after_detection",
                delay_data.get("wait_after_detection", 0.0),
            )
        else:
            delay = delay_data.get("wait_after_detection", 0.0)
        time.sleep(max(0.0, float(delay)))
        if face:
            self.robot_client.send_emotion(
                face_type=face.get("type", "neutral"),
                level=int(face.get("level", 1)),
                priority=3,
                keeptime=3000,
            )
        if nod:
            self.robot_client.send_nod(
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
        self.status_var.set("接客例の実演が終了しました")

    def on_robot_run_advance(self, _event=None):
        self.advance_robot_run()

    def return_to_example_view(self):
        self.cleanup_generated_wavs()
        self.clear_page()
        self.build_ui()
        self.refresh_scene_choices()

    def selected_staff_turn_index(self):
        value = self.staff_turn_var.get()
        if not value:
            return None
        try:
            return int(value.split(".", 1)[0]) - 1
        except Exception:
            return None

    def save_all(self):
        self.profile_store.save_current_with_examples()
        saved_path = self.profile_store.path
        example_path = getattr(self.profile_store, "last_example_results_path", None)
        if example_path is not None:
            self.status_var.set(f"保存しました: {saved_path.name} / {example_path.name}")
        else:
            self.status_var.set(f"保存しました: {saved_path.name}")

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
            self.robot_client.close()
        except Exception:
            pass

        delete_filehandler = getattr(self.tk, "deletefilehandler", None)
        if self._filehandler_registered and delete_filehandler is not None and self._event_read_fd is not None:
            try:
                delete_filehandler(self._event_read_fd)
            except Exception:
                pass
            self._filehandler_registered = False

        for fd_name in ("_event_read_fd", "_event_write_fd"):
            fd = getattr(self, fd_name, None)
            if fd is None:
                continue
            try:
                os.close(fd)
            except OSError:
                pass
            setattr(self, fd_name, None)

        super().destroy()
