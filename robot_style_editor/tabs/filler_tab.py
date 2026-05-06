import tkinter as tk
from tkinter import messagebox

from .. import ui_style as ui
from ..config_intention import (
    FILLER_OPTIONS,
    FILLER_VOICE_PRESETS,
    voice_params_to_tts_instructions,
)
from ..panels.voice_style_panel import VoiceStylePanel


class FillerTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        data = self.profile_store.get_nested("filler", {})
        selected = data.get("selected_ids", [item["id"] for item in FILLER_OPTIONS[:3]])

        self.enabled_var = tk.BooleanVar(value=bool(data.get("enabled", False)))
        self.option_vars = {
            item["id"]: tk.BooleanVar(value=(item["id"] in selected))
            for item in FILLER_OPTIONS
        }
        self.voice_panel = None
        self.initial_voice_data = data.get("voice", {})
        self.custom_text_var = tk.StringVar(value=data.get("custom_text", ""))

        self.build_ui()

    def build_ui(self):
        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )

        ui.label(page, text="フィラーを設定する", font="page_title", bg="main_card").pack(anchor="w")
        ui.label(
            page,
            text="「そうですね」「えっと」など、考え中や文頭に入る短い発話を使うかどうかと声色を調整します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        content = ui.scrollable_frame(page)
        self.build_enable_area(content)
        self.build_option_area(content)

        self.voice_panel = VoiceStylePanel(
            content,
            initial_data=self.initial_voice_data,
            tts_client=self.tts_client,
            get_text=self.preview_text,
            get_speaker=lambda: self.profile_store.get("speaker", None),
            on_changed=lambda _data: self.save_selection_only(update_status=False),
            voice_presets=FILLER_VOICE_PRESETS,
        )
        self.voice_panel.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        self.build_bottom_area(page)

    def build_enable_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(fill="x", padx=ui.SPACING["section_x"], pady=ui.SPACING["section_y"])

        check = tk.Checkbutton(
            card,
            text="フィラーを使う",
            variable=self.enabled_var,
            command=self.save_selection_only,
            font=ui.FONTS["body_bold"],
            bg=ui.COLORS["card"],
            fg=ui.COLORS["text"],
            activebackground=ui.COLORS["card"],
            activeforeground=ui.COLORS["text"],
            selectcolor=ui.COLORS["card"],
            anchor="w",
        )
        check.pack(anchor="w", padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])

    def build_option_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(section, text="使うフィラー", font="section_title", bg="panel").pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        grid = ui.frame(card, bg="card")
        grid.pack(fill="x", padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])

        for index, item in enumerate(FILLER_OPTIONS):
            check = tk.Checkbutton(
                grid,
                text=item["label"],
                variable=self.option_vars[item["id"]],
                command=self.save_selection_only,
                font=ui.FONTS["body_bold"],
                bg=ui.COLORS["card"],
                fg=ui.COLORS["text"],
                activebackground=ui.COLORS["card"],
                activeforeground=ui.COLORS["text"],
                selectcolor=ui.COLORS["card"],
                anchor="w",
            )
            check.grid(
                row=index // 3,
                column=index % 3,
                sticky="ew",
                padx=(0, ui.SPACING["gap"]),
                pady=(0, ui.SPACING["small_gap"]),
            )
            grid.columnconfigure(index % 3, weight=1)

        custom_row = ui.frame(card, bg="card")
        custom_row.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))
        ui.label(custom_row, text="追加フィラー", font="small", bg="card", fg="muted").pack(side="left")
        entry = tk.Entry(
            custom_row,
            textvariable=self.custom_text_var,
            font=ui.FONTS["input"],
            bg=ui.COLORS["card"],
            fg=ui.COLORS["text"],
            relief="solid",
            bd=1,
        )
        entry.pack(side="left", fill="x", expand=True, padx=(ui.SPACING["small_gap"], 0))
        entry.bind("<KeyRelease>", lambda _event=None: self.save_selection_only(update_status=False))

    def build_bottom_area(self, parent):
        bottom = ui.frame(parent, bg="main_card")
        bottom.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.sub_button(bottom, text="フィラーを試聴", command=self.speak_sample).pack(side="left")
        ui.action_button(bottom, text="保存して次へ", command=self.save_and_next).pack(side="right")

    def selected_options(self):
        return [
            item
            for item in FILLER_OPTIONS
            if self.option_vars[item["id"]].get()
        ]

    def preview_text(self):
        selected = self.selected_options()
        if selected:
            return selected[0]["label"]
        custom = self.custom_text_var.get().strip()
        if custom:
            return custom
        return "そうですね"

    def get_voice_data(self):
        if self.voice_panel is None:
            return {}
        return self.voice_panel.get_data()

    def get_current_data(self):
        voice_data = self.get_voice_data()
        selected = self.selected_options()
        custom = self.custom_text_var.get().strip()
        phrases = [item["label"] for item in selected]
        if custom:
            phrases.append(custom)

        return {
            "enabled": self.enabled_var.get(),
            "selected_ids": [item["id"] for item in selected],
            "phrases": phrases,
            "custom_text": custom,
            "voice": voice_data,
            "tts_instructions": voice_params_to_tts_instructions(voice_data["params"]),
            "prompt": "会話の間や文頭に挿入するフィラー。enabled が true のとき phrases から自然に選ぶ。",
        }

    def save_selection_only(self, update_status=True):
        if self.voice_panel is None:
            return
        self.profile_store.set("filler", self.get_current_data(), auto_save=True)
        if update_status:
            self.status_var.set("フィラー設定を保存しました")

    def save_and_next(self):
        self.save_selection_only()
        if self.on_saved is not None:
            self.on_saved()

    def speak_sample(self):
        text = self.preview_text()
        if not text:
            messagebox.showwarning("確認", "試聴するフィラーを選択してください。")
            return

        self.save_selection_only(update_status=False)
        self.tts_client.speak(
            text=text,
            instructions=voice_params_to_tts_instructions(self.get_voice_data()["params"]),
            person=self.profile_store.get("speaker", None),
        )
        self.status_var.set("フィラーを再生しました")
