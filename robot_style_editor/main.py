import tkinter as tk
from tkinter import ttk

from .profile_store import ProfileStore
from .tts_client import TTSClient
from . import ui_style as ui

from .tabs.speaker_tab import SpeakerTab
from .tabs.politeness_tab import PolitenessTab
from .tabs.intimacy_tab import IntimacyTab
from .tabs.vocabulary_tab import VocabularyTab
from .tabs.length_tab import LengthTab

class RobotStyleEditorApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("ロボット話し方設定")
        self.geometry("1300x1000-1200-1100")
        self.minsize(1100, 650)

        ui.apply_app_style(self)

        self.profile_store = ProfileStore()
        self.tts_client = TTSClient()
        self.status_var = tk.StringVar(value="準備完了")

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
        speaker_tab = SpeakerTab(
            self.notebook,
            profile_store=self.profile_store,
            tts_client=self.tts_client,
            status_var=self.status_var,
            on_saved=self.go_next_tab,
        )

        politeness_tab = PolitenessTab(
            self.notebook,
            profile_store=self.profile_store,
            tts_client=self.tts_client,
            status_var=self.status_var,
            on_saved=self.go_next_tab,
        )

        intimacy_tab = IntimacyTab(
            self.notebook,
            profile_store=self.profile_store,
            tts_client=self.tts_client,
            status_var=self.status_var,
            on_saved=self.go_next_tab,
        )

        vocabulary_tab = VocabularyTab(
            self.notebook,
            profile_store=self.profile_store,
            tts_client=self.tts_client,
            status_var=self.status_var,
            on_saved=self.go_next_tab,
        )

        length_tab = LengthTab(
            self.notebook,
            profile_store=self.profile_store,
            tts_client=self.tts_client,
            status_var=self.status_var,
            on_saved=self.go_next_tab,
        )

        self.notebook.add(speaker_tab, text="話者")
        self.notebook.add(politeness_tab, text="敬語")
        self.notebook.add(intimacy_tab, text="親しみ")
        self.notebook.add(vocabulary_tab, text="語彙")
        self.notebook.add(length_tab, text="長さ")

    def go_next_tab(self):
        current = self.notebook.index(self.notebook.select())
        total = self.notebook.index("end")

        if current + 1 < total:
            self.notebook.select(current + 1)
            selected = self.notebook.nametowidget(self.notebook.select())
            if hasattr(selected, "refresh_from_profile"):
                selected.refresh_from_profile()

    def on_tab_changed(self, _event):
        selected = self.notebook.nametowidget(self.notebook.select())

        if hasattr(selected, "refresh_from_profile"):
            selected.refresh_from_profile()

    def save_all(self):
        self.profile_store.save()
        self.status_var.set("全体を保存しました")

    def on_close(self):
        self.profile_store.save()
        self.destroy()


if __name__ == "__main__":
    app = RobotStyleEditorApp()
    app.mainloop()