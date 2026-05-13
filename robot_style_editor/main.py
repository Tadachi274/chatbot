import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox


def load_env_file():
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        if line.startswith("export "):
            line = line[len("export "):].strip()

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()

from .profile_store import ProfileStore
from .clients.tts_client import TTSClient
from . import ui_style as ui
from .config import (
    RUNTIME_ENV_PRESETS,
    apply_runtime_environment,
    get_runtime_environment,
    get_tts_playback_target,
)
from .config_example import EXAMPLE_SCENES, EXAMPLE_VENUES

from .tabs.speaker_tab import SpeakerTab
from .tabs.default_profile_tab import DefaultProfileTab
from .tabs.politeness_tab import PolitenessTab
from .tabs.intimacy_tab import IntimacyTab
from .tabs.vocabulary_tab import VocabularyTab
from .tabs.length_tab import LengthTab
from .tabs.style_detail_tab import StyleDetailTab
from .tabs.special_consideration_tab import SpecialConsiderationTab
from .tabs.greeting_tab import GreetingTab
from .tabs.explanation_tab import ExplanationTab
from .tabs.question_tab import QuestionTab
from .tabs.apology_tab import ApologyTab
from .tabs.gratitude_tab import GratitudeTab
from .tabs.smalltalk_tab import SmalltalkTab
from .tabs.acceptance_tab import AcceptanceTab
from .tabs.request_tab import RequestTab
from .tabs.filler_tab import FillerTab
from .tabs.settings_review_tab import SettingsReviewTab
from .tabs.speed_tab import SpeedTab
from .tabs.sentence_pause_tab import SentencePauseTab
from .tabs.response_delay_tab import ResponseDelayTab
from .tabs.thinking_pose_tab import ThinkingPoseTab
from .tabs.listening_pose_tab import ListeningPoseTab
from .tabs.understanding_pose_tab import UnderstandingPoseTab
from .tabs.request_history_tab import RequestHistoryTab
from .tabs.venue_da_info_tab import VenueDAInfoTab


class LazyTab(tk.Frame):
    def __init__(self, parent, factory, bg_key="main_card"):
        super().__init__(parent, bg=ui.COLORS[bg_key])
        self.factory = factory
        self.content = None

    def ensure_built(self):
        if self.content is not None:
            return self.content

        self.content = self.factory(self)
        self.content.pack(fill="both", expand=True)
        return self.content

    def refresh_from_profile(self):
        content = self.ensure_built()
        if hasattr(content, "refresh_from_profile"):
            content.refresh_from_profile()

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        content = self.ensure_built()
        return getattr(content, name)


class RobotStyleEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("ロボット話し方設定")
        self.geometry(self.initial_geometry())
        self.minsize(980, 560)

        ui.configure_density(self)
        ui.apply_app_style(self)
        self.runtime_env = self.choose_runtime_environment()

        self.profile_store = ProfileStore()
        self.tts_client = TTSClient()
        self.status_var = tk.StringVar(value=f"準備完了: {RUNTIME_ENV_PRESETS[self.runtime_env]['label']}")
        self.tts_playback_var = tk.StringVar(value=get_tts_playback_target())
        self.session_active = False
        self.user_active = False
        self.selected_venue = None

        self.build_ui()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def choose_runtime_environment(self):
        if os.environ.get("ROBOT_STYLE_ENV"):
            return apply_runtime_environment(os.environ["ROBOT_STYLE_ENV"], override=True)

        selected = tk.StringVar(value=get_runtime_environment())
        dialog = tk.Toplevel(self)
        dialog.title("実行環境の選択")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        body = ui.frame(dialog, bg="main_card")
        body.pack(fill="both", expand=True, padx=24, pady=20)

        ui.label(
            body,
            text="実行環境を選択",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")
        ui.label(
            body,
            text="mic、TTS、表情コマンドの接続先をまとめて切り替えます。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        for env_id in ("real", "mac"):
            preset = RUNTIME_ENV_PRESETS[env_id]
            card = ui.bordered_frame(body, bg="card", border="border")
            card.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))
            ui.radio(
                card,
                text=preset["label"],
                variable=selected,
                value=env_id,
                bg="card",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["compact_y"], 0))
            ui.label(
                card,
                text=(
                    f"TTS: {preset['TTS_URL']} / "
                    f"Robot: {preset['ROBOT_TCP_HOST']}:{preset['ROBOT_TCP_PORT']} / "
                    f"Mic: {preset['MIC_ACTIVITY_MODE']}"
                ),
                font="small",
                bg="card",
                fg="muted",
                wraplength=720,
                justify="left",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))

        def confirm():
            apply_runtime_environment(selected.get(), override=True)
            dialog.destroy()

        ui.action_button(body, text="この環境で開始", command=confirm).pack(anchor="e", pady=(ui.SPACING["gap"], 0))

        dialog.protocol("WM_DELETE_WINDOW", confirm)
        self.wait_window(dialog)
        return get_runtime_environment()

    def initial_geometry(self):
        width = min(1300, max(980, self.winfo_screenwidth() - 80))
        height = min(1000, max(620, self.winfo_screenheight() - 120))
        return f"{width}x{height}"

    def build_ui(self):
        outer = ui.frame(self, bg="app_bg")
        outer.pack(fill="both", expand=True, padx=ui.SPACING["small_gap"], pady=ui.SPACING["small_gap"])

        main_card = ui.bordered_frame(
            outer,
            bg="main_card",
            border="frame_border",
            thickness=1,
        )
        main_card.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(main_card, style="Research.TNotebook")

        footer = ui.frame(main_card, bg="main_card")
        footer.pack(
            side="bottom",
            fill="x",
            padx=ui.SPACING["compact_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

        ui.variable_label(
            footer,
            textvariable=self.status_var,
            font="small",
            bg="main_card",
            fg="sub_text",
        ).pack(side="left", fill="x", expand=True)

        playback_frame = ui.frame(footer, bg="main_card")
        playback_frame.pack(side="right", padx=(ui.SPACING["small_gap"], 0))
        ui.label(
            playback_frame,
            text="音声",
            font="small",
            bg="main_card",
            fg="sub_text",
        ).pack(side="left")
        ui.radio(
            playback_frame,
            text="ノートPC",
            variable=self.tts_playback_var,
            value="local",
            command=self.on_tts_playback_changed,
            bg="main_card",
        ).pack(side="left")

        ui.action_button(
            footer,
            text="保存",
            command=self.save_all,
        ).pack(side="right", padx=(ui.SPACING["small_gap"], 0))
        ui.radio(
            playback_frame,
            text="ニコラ",
            variable=self.tts_playback_var,
            value="robot",
            command=self.on_tts_playback_changed,
            bg="main_card",
        ).pack(side="left")

        self.notebook.pack(
            side="top",
            fill="both",
            expand=True,
            padx=ui.SPACING["small_gap"],
            pady=ui.SPACING["small_gap"],
        )

        self.add_tabs()
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tts_playback_changed(self):
        target = self.tts_playback_var.get()
        self.tts_client.set_playback_target(target)
        label = "ニコラPC" if target == "robot" else "ノートPC"
        self.status_var.set(f"音声再生先を{label}にしました")

    def add_tabs(self):
        self.tab_sequence = []
        self.tab_locations = {}
        self.group_notebooks = {}
        self.child_notebook_parents = {}

        style_frame, style_notebook = self.create_group_notebook()
        response_frame, response_notebook = self.create_group_notebook()
        da_frame, da_notebook = self.create_group_notebook()
        example_frame, example_notebook = self.create_group_notebook()
        request_history_frame, request_history_notebook = self.create_group_notebook()
        active_venues = self.active_venues()
        required_intent_keys = self.required_intent_keys()
        required_intents, unused_intents = self.intent_scope_items(required_intent_keys)

        self.default_tab = DefaultProfileTab(
            self.notebook,
            profile_store=self.profile_store,
            tts_client=self.tts_client,
            status_var=self.status_var,
            on_create_user=self.create_new_user_session,
            on_load_user=self.load_user_session,
            on_continue_user=self.continue_current_user,
            on_select_venue=self.select_venue_session,
            on_finish=self.on_close,
            can_use_default_talk=lambda: True,
        )

        speaker_tab = self.lazy_tab(self.notebook, SpeakerTab)
        politeness_tab = self.lazy_tab(style_notebook, PolitenessTab)
        intimacy_tab = self.lazy_tab(style_notebook, IntimacyTab)
        vocabulary_tab = self.lazy_tab(style_notebook, VocabularyTab)
        length_tab = self.lazy_tab(style_notebook, LengthTab)
        style_detail_tab = self.lazy_tab(style_notebook, StyleDetailTab)
        special_consideration_tab = self.lazy_tab(style_notebook, SpecialConsiderationTab)

        speed_tab = self.lazy_tab(response_notebook, SpeedTab)
        sentence_pause_tab = self.lazy_tab(response_notebook, SentencePauseTab)
        response_delay_tab = self.lazy_tab(response_notebook, ResponseDelayTab)
        thinking_pose_tab = self.lazy_tab(response_notebook, ThinkingPoseTab)
        listening_pose_tab = self.lazy_tab(response_notebook, ListeningPoseTab)
        understanding_pose_tab = self.lazy_tab(response_notebook, UnderstandingPoseTab)

        intent_tabs = {
            "greeting": self.lazy_tab(da_notebook, GreetingTab),
            "explanation": self.lazy_tab(da_notebook, ExplanationTab),
            "question": self.lazy_tab(da_notebook, QuestionTab),
            "acceptance": self.lazy_tab(da_notebook, AcceptanceTab),
            "request": self.lazy_tab(da_notebook, RequestTab),
            "apology": self.lazy_tab(da_notebook, ApologyTab),
            "gratitude": self.lazy_tab(da_notebook, GratitudeTab),
            "smalltalk": self.lazy_tab(da_notebook, SmalltalkTab),
        }
        filler_tab = self.lazy_tab(da_notebook, FillerTab)

        settings_review_tab = self.lazy_tab(self.notebook, SettingsReviewTab)

        self.example_scene_tabs = [
            self.lazy_example_tab(example_notebook, venue["label"])
            for venue in active_venues
        ]
        self.example_scene_tab = self.example_scene_tabs[0]
        self.request_history_tabs = [
            self.lazy_request_history_tab(request_history_notebook, venue["label"])
            for venue in active_venues
        ]

        self.add_top_tab(self.default_tab, "デフォルト")
        self.add_top_tab(speaker_tab, "話者")

        self.add_child_tab(style_notebook, politeness_tab, "敬語")
        self.add_child_tab(style_notebook, intimacy_tab, "親しみ")
        self.add_child_tab(style_notebook, vocabulary_tab, "語彙")
        self.add_child_tab(style_notebook, length_tab, "長さ")
        self.add_child_tab(style_notebook, style_detail_tab, "詳細設定")
        self.add_child_tab(style_notebook, special_consideration_tab, "特別考慮")
        self.notebook.add(style_frame, text="スタイル")

        self.add_child_tab(response_notebook, speed_tab, "話速")
        self.add_child_tab(response_notebook, sentence_pause_tab, "文間")
        self.add_child_tab(response_notebook, response_delay_tab, "返答・理解")
        self.add_child_tab(response_notebook, thinking_pose_tab, "考え姿")
        self.add_child_tab(response_notebook, listening_pose_tab, "聴く姿")
        self.add_child_tab(response_notebook, understanding_pose_tab, "理解詳細")
        self.notebook.add(response_frame, text="応答・間合い")

        da_info_tab = self.lazy_da_info_tab(da_notebook, required_intents, unused_intents)
        self.add_child_tab(da_notebook, da_info_tab, "設定範囲")
        for intent_key, label in self.intent_tab_labels():
            if intent_key in required_intent_keys:
                self.add_child_tab(da_notebook, intent_tabs[intent_key], label)
        self.add_child_tab(da_notebook, filler_tab, "フィラー")
        self.notebook.add(da_frame, text="DA")

        self.add_top_tab(settings_review_tab, "設定確認")

        for venue, example_scene_tab in zip(active_venues, self.example_scene_tabs):
            self.add_child_tab(example_notebook, example_scene_tab, venue["label"])
        self.notebook.add(example_frame, text="接客例")

        for venue, request_history_tab in zip(active_venues, self.request_history_tabs):
            self.add_child_tab(request_history_notebook, request_history_tab, venue["label"])
        self.notebook.add(request_history_frame, text="詳細要望一覧")

    def active_venues(self):
        if self.selected_venue is not None:
            return [self.selected_venue]
        venue_id = getattr(self.profile_store, "current_venue_id", None)
        if venue_id:
            for venue in EXAMPLE_VENUES:
                if venue["id"] == venue_id:
                    return [venue]
        return EXAMPLE_VENUES

    def intent_tab_labels(self):
        return [
            ("greeting", "挨拶"),
            ("explanation", "説明"),
            ("question", "質問"),
            ("acceptance", "承諾"),
            ("request", "要求"),
            ("apology", "謝罪"),
            ("gratitude", "感謝"),
            ("smalltalk", "雑談"),
        ]

    def required_intent_keys(self):
        return {key for key, _label in self.intent_tab_labels() if key != "smalltalk"}

    def intent_scope_items(self, required_keys):
        labels = dict(self.intent_tab_labels())
        scene_titles = {}
        venue_ids = {venue["id"] for venue in self.active_venues()}
        for scene in EXAMPLE_SCENES:
            if scene.get("venue") not in venue_ids:
                continue
            for turn in scene.get("turns", []):
                for part in turn.get("intent_parts", []) or []:
                    intent = part.get("intent")
                    if intent:
                        scene_titles.setdefault(intent, set()).add(scene.get("title", "接客例"))

        required = []
        unused = []
        for key, label in self.intent_tab_labels():
            titles = "、".join(sorted(scene_titles.get(key, [])))
            if key in required_keys:
                required.append({"key": key, "label": label, "reason": titles or "全店舗で共通して設定"})
            else:
                unused.append({"key": key, "label": label, "reason": "接客場面設定では対象外"})
        return required, unused

    def lazy_tab(self, parent, tab_class):
        return LazyTab(
            parent,
            lambda container, cls=tab_class: cls(
                container,
                profile_store=self.profile_store,
                tts_client=self.tts_client,
                status_var=self.status_var,
                on_saved=self.go_next_tab,
            ),
        )

    def lazy_example_tab(self, parent, venue_label):
        return LazyTab(
            parent,
            lambda container, label=venue_label: self.create_example_scene_tab(container, label),
        )

    def lazy_request_history_tab(self, parent, venue_label):
        return LazyTab(
            parent,
            lambda container, label=venue_label: RequestHistoryTab(
                container,
                profile_store=self.profile_store,
                tts_client=self.tts_client,
                status_var=self.status_var,
                on_saved=self.go_next_tab,
                venue_label=label,
            ),
        )

    def lazy_da_info_tab(self, parent, required_intents, unused_intents):
        return LazyTab(
            parent,
            lambda container: VenueDAInfoTab(
                container,
                profile_store=self.profile_store,
                tts_client=self.tts_client,
                status_var=self.status_var,
                on_saved=self.go_next_tab,
                required_intents=required_intents,
                unused_intents=unused_intents,
                venue_label=(self.selected_venue or {}).get("label"),
            ),
        )

    def create_example_scene_tab(self, container, venue_label):
        from .tabs.example_scene_tab import ExampleSceneTab

        return ExampleSceneTab(
            container,
            profile_store=self.profile_store,
            status_var=self.status_var,
            tts_client=self.tts_client,
            on_saved=self.go_next_tab,
            venue_label=venue_label,
        )

    def create_group_notebook(self):
        frame = ui.frame(self.notebook, bg="main_card")
        notebook = ttk.Notebook(frame, style="Research.TNotebook")
        notebook.pack(fill="both", expand=True)
        notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)
        self.group_notebooks[frame] = notebook
        self.child_notebook_parents[notebook] = frame
        return frame, notebook

    def add_top_tab(self, tab, text):
        self.notebook.add(tab, text=text)
        self.register_actual_tab(tab, self.notebook)

    def add_child_tab(self, notebook, tab, text):
        notebook.add(tab, text=text)
        self.register_actual_tab(tab, notebook)

    def register_actual_tab(self, tab, notebook):
        self.tab_sequence.append(tab)
        self.tab_locations[tab] = notebook

    def rebuild_tabs_from_profile(self):
        for tab_id in list(self.notebook.tabs()):
            try:
                widget = self.notebook.nametowidget(tab_id)
            except tk.TclError:
                continue
            try:
                widget.destroy()
            except tk.TclError:
                pass

        self.add_tabs()

    def create_new_user_session(self, filename):
        saved_path = self.profile_store.start_new_user_folder(filename)
        self.user_active = True
        self.session_active = False
        self.selected_venue = None
        self.status_var.set(f"新しいユーザーを開始しました: {saved_path.name}")
        self.select_actual_tab(self.default_tab)
        return saved_path

    def load_user_session(self, path):
        loaded_path = self.profile_store.load_user_folder(path)
        self.user_active = True
        self.session_active = False
        self.selected_venue = None
        self.status_var.set(f"ユーザーを読み込みました: {loaded_path.name}")
        self.select_actual_tab(self.default_tab)
        return loaded_path

    def select_venue_session(self, venue):
        saved_path = self.profile_store.select_venue_session(venue["id"], venue["label"])
        self.selected_venue = venue
        self.user_active = True
        self.session_active = True
        self.status_var.set(f"{venue['label']}の設定を開始しました: {saved_path.name}")
        self.rebuild_tabs_from_profile()
        self.select_actual_tab(self.default_tab)
        self.default_tab.show_default_talk_tab(venue["label"])
        return saved_path

    def continue_current_user(self):
        if self.selected_venue is None:
            self.select_actual_tab(self.default_tab)
            self.status_var.set("設定する店舗を選択してください")
            return
        self.session_active = True
        self.status_var.set(f"同じユーザーで続けます: {self.profile_store.path.name}")
        if len(self.tab_sequence) > 1:
            self.select_actual_tab(self.tab_sequence[1])

    def get_current_actual_tab(self):
        selected = self.notebook.nametowidget(self.notebook.select())
        child_notebook = self.group_notebooks.get(selected)

        if child_notebook is None:
            return selected

        if not child_notebook.select():
            return selected

        return child_notebook.nametowidget(child_notebook.select())

    def select_actual_tab(self, tab):
        notebook = self.tab_locations.get(tab)

        if notebook is None:
            return

        if notebook == self.notebook:
            self.notebook.select(tab)
            return

        parent_frame = self.child_notebook_parents[notebook]
        self.notebook.select(parent_frame)
        notebook.select(tab)

    def go_next_tab(self):
        if not self.session_active:
            self.select_actual_tab(self.default_tab)
            self.status_var.set("先にユーザー名を入力してください")
            return

        current_tab = self.get_current_actual_tab()

        if current_tab not in self.tab_sequence:
            return

        current = self.tab_sequence.index(current_tab)

        if current + 1 < len(self.tab_sequence):
            selected = self.tab_sequence[current + 1]
            self.select_actual_tab(selected)
            if hasattr(selected, "refresh_from_profile"):
                selected.refresh_from_profile()

    def on_tab_changed(self, _event):
        selected = self.get_current_actual_tab()
        if not self.session_active and selected is not getattr(self, "default_tab", None):
            self.select_actual_tab(self.default_tab)
            self.status_var.set("先にユーザー名を入力してください")
            return

        if hasattr(selected, "refresh_from_profile"):
            selected.refresh_from_profile()

    def save_all(self):
        if not self.session_active:
            messagebox.showwarning("確認", "先にユーザー名を入力してください。", parent=self)
            self.select_actual_tab(self.default_tab)
            return

        self.profile_store.save_current_with_examples()
        saved_path = self.profile_store.path

        example_path = getattr(self.profile_store, "last_example_results_path", None)
        if example_path is not None:
            self.status_var.set(f"保存しました: {saved_path.name} / {example_path.name}")
        else:
            self.status_var.set(f"保存しました: {saved_path.name}")
        self.session_active = False
        self.select_actual_tab(self.default_tab)
        self.default_tab.show_saved_actions(saved_path, example_path)

    def go_example_tab(self):
        if not self.session_active:
            self.select_actual_tab(self.default_tab)
            self.status_var.set("先にユーザー名を入力してください")
            return

        if hasattr(self, "example_scene_tab"):
            self.select_actual_tab(self.example_scene_tab)
            if hasattr(self.example_scene_tab, "refresh_from_profile"):
                self.example_scene_tab.refresh_from_profile()

    def on_close(self):
        if self.session_active:
            self.profile_store.save()
        self.destroy()


if __name__ == "__main__":
    app = RobotStyleEditorApp()
    app.mainloop()
