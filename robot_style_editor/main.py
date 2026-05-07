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
from .config_default_profile import build_default_profile
from .config_example import EXAMPLE_VENUES

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
        self.geometry("1300x1000")
        self.minsize(1100, 650)

        ui.apply_app_style(self)

        self.profile_store = ProfileStore()
        self.tts_client = TTSClient()
        self.status_var = tk.StringVar(value="準備完了")
        self.session_active = False

        self.build_ui()

        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def build_ui(self):
        outer = ui.frame(self, bg="app_bg")
        outer.pack(fill="both", expand=True, padx=18, pady=18)

        header = ui.frame(outer, bg="app_bg")
        header.pack(fill="x", pady=(0, 10))

        ui.label(
            header,
            text="ロボット話し方設定",
            font="app_title",
            bg="app_bg",
        ).pack(side="left")

        ui.label(
            header,
            text="各項目を選択し、音声を確認してください",
            font="body",
            bg="app_bg",
            fg="sub_text",
        ).pack(side="right", padx=8)

        main_card = ui.bordered_frame(
            outer,
            bg="main_card",
            border="frame_border",
            thickness=5,
        )
        main_card.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(main_card, style="Research.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=16, pady=16)

        self.add_tabs()
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        footer = ui.frame(main_card, bg="main_card")
        footer.pack(fill="x", padx=16, pady=(0, 12))

        ui.variable_label(
            footer,
            textvariable=self.status_var,
            font="small",
            bg="main_card",
            fg="sub_text",
        ).pack(side="left")

        ui.action_button(
            footer,
            text="全体を保存",
            command=self.save_all,
        ).pack(side="right")

    def add_tabs(self):
        self.tab_sequence = []
        self.tab_locations = {}
        self.group_notebooks = {}
        self.child_notebook_parents = {}

        style_frame, style_notebook = self.create_group_notebook()
        response_frame, response_notebook = self.create_group_notebook()
        da_frame, da_notebook = self.create_group_notebook()
        example_frame, example_notebook = self.create_group_notebook()

        self.default_tab = DefaultProfileTab(
            self.notebook,
            profile_store=self.profile_store,
            tts_client=self.tts_client,
            status_var=self.status_var,
            on_create_user=self.create_new_user_session,
            on_load_user=self.load_user_session,
            on_continue_user=self.continue_current_user,
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

        greeting_tab = self.lazy_tab(da_notebook, GreetingTab)
        explanation_tab = self.lazy_tab(da_notebook, ExplanationTab)
        question_tab = self.lazy_tab(da_notebook, QuestionTab)
        acceptance_tab = self.lazy_tab(da_notebook, AcceptanceTab)
        request_tab = self.lazy_tab(da_notebook, RequestTab)
        apology_tab = self.lazy_tab(da_notebook, ApologyTab)
        gratitude_tab = self.lazy_tab(da_notebook, GratitudeTab)
        smalltalk_tab = self.lazy_tab(da_notebook, SmalltalkTab)
        filler_tab = self.lazy_tab(da_notebook, FillerTab)

        settings_review_tab = self.lazy_tab(self.notebook, SettingsReviewTab)

        self.example_scene_tabs = [
            self.lazy_example_tab(example_notebook, venue["label"])
            for venue in EXAMPLE_VENUES
        ]
        self.example_scene_tab = self.example_scene_tabs[0]

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

        self.add_child_tab(da_notebook, greeting_tab, "挨拶")
        self.add_child_tab(da_notebook, explanation_tab, "説明")
        self.add_child_tab(da_notebook, question_tab, "質問")
        self.add_child_tab(da_notebook, acceptance_tab, "承諾")
        self.add_child_tab(da_notebook, request_tab, "要求")
        self.add_child_tab(da_notebook, apology_tab, "謝罪")
        self.add_child_tab(da_notebook, gratitude_tab, "感謝")
        self.add_child_tab(da_notebook, smalltalk_tab, "雑談")
        self.add_child_tab(da_notebook, filler_tab, "フィラー")
        self.notebook.add(da_frame, text="DA")

        self.add_top_tab(settings_review_tab, "設定確認")

        for venue, example_scene_tab in zip(EXAMPLE_VENUES, self.example_scene_tabs):
            self.add_child_tab(example_notebook, example_scene_tab, venue["label"])
        self.notebook.add(example_frame, text="接客例")

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
        self.profile_store.data = build_default_profile()
        saved_path = self.profile_store.start_new_session(filename)
        self.session_active = True
        self.status_var.set(f"新しいユーザーを開始しました: {saved_path.name}")
        self.rebuild_tabs_from_profile()
        self.select_actual_tab(self.default_tab)
        self.default_tab.show_default_talk_tab()
        return saved_path

    def load_user_session(self, path):
        loaded_path = self.profile_store.load_from(path)
        self.session_active = True
        self.status_var.set(f"保存データを読み込みました: {loaded_path.name}")
        self.rebuild_tabs_from_profile()
        if len(self.tab_sequence) > 1:
            self.select_actual_tab(self.tab_sequence[1])
        return loaded_path

    def continue_current_user(self):
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
