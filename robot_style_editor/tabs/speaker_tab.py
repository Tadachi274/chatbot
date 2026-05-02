import tkinter as tk
from tkinter import messagebox

from ..config import PERSON
from .. import ui_style as ui


class SpeakerTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        self.selected_person = tk.StringVar(
            value=self.profile_store.get("speaker", PERSON[0])
        )

        self.speaker_text = tk.StringVar(
            value=self.profile_store.get("speaker_test_text", "話し手が変更されました")
        )

        self.build_ui()

    def build_ui(self):
        page = ui.frame(self, bg="main_card")
        page.pack(fill="both", expand=True, padx=24, pady=24)

        ui.label(
            page,
            text="話し手を選ぶ",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            page,
            text="声の印象を比べながら、ロボットに合う話し手を選びます。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(4, 18))

        self.build_person_choices(page)
        self.build_test_area(page)

    def build_person_choices(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(0, 18))

        ui.label(
            section,
            text="選択肢",
            font="section_title",
            bg="panel",
        ).pack(anchor="w", padx=18, pady=(18, 8))

        choice_row = ui.frame(section, bg="panel")
        choice_row.pack(fill="x", padx=18, pady=(0, 18))

        for person in PERSON:
            card = ui.bordered_frame(choice_row, bg="card", border="border")
            card.pack(side="left", fill="both", expand=True, padx=(0, 12))

            ui.radio(
                card,
                text=self.person_display_name(person),
                variable=self.selected_person,
                value=person,
                command=self.save_selection_only,
                bg="card",
            ).pack(anchor="w", padx=14, pady=(12, 2))

            ui.label(
                card,
                text=person,
                font="mono",
                bg="card",
                fg="muted",
            ).pack(anchor="w", padx=38, pady=(0, 12))

    def build_test_area(self, parent):
        bottom = ui.frame(parent, bg="main_card")
        bottom.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        sample_row = ui.frame(bottom, bg="main_card")
        sample_row.pack(fill="x")

        input_area = ui.frame(sample_row, bg="main_card")
        input_area.pack(side="left", fill="x", expand=True)

        ui.label(
            input_area,
            text="読み上げる文",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w")

        ui.entry(
            input_area,
            textvariable=self.speaker_text,
            font="input",
        ).pack(fill="x", ipady=8)

        play_button_area = ui.frame(sample_row, bg="main_card")
        play_button_area.pack(side="right", anchor="s", padx=(ui.SPACING["gap"], 0))

        ui.sub_button(
            play_button_area,
            text="再生",
            command=self.apply_speaker_and_speak,
        ).pack(anchor="s")

        # 2段目：保存して次へだけ右下
        save_row = ui.frame(bottom, bg="main_card")
        save_row.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.action_button(
            save_row,
            text="保存して次へ",
            command=self.save_and_next,
        ).pack(side="right")

        

    def person_display_name(self, person):
        if person.startswith("nozomi"):
            return "のぞみ"
        if person.startswith("kenta"):
            return "けんた"
        return person

    def save_selection_only(self):
        self.profile_store.set("speaker", self.selected_person.get(), auto_save=False)
        self.profile_store.set("speaker_test_text", self.speaker_text.get(), auto_save=True)
        self.status_var.set("話者設定を保存しました")

    def save_and_next(self):
        self.save_selection_only()

        if self.on_saved is not None:
            self.on_saved()

    def apply_speaker_and_speak(self):
        text = self.speaker_text.get().strip()

        if not text:
            messagebox.showwarning("確認", "読み上げる文を入力してください。")
            return

        speaker = self.selected_person.get()

        self.save_selection_only()

        self.tts_client.change_speaker_and_speak(
            text=text,
            speaker=speaker,
        )

        self.status_var.set(f"話者を変更して再生しました: {speaker}")