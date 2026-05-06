import tkinter as tk

from .. import ui_style as ui


class SpecialConsiderationTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])
        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        data = self.profile_store.get_nested("special_consideration", {}) or {}
        self.initial_text = data.get("text", "")
        self.text_box = None

        self.build_ui()

    def build_ui(self):
        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )

        ui.label(page, text="特別考慮", font="page_title", bg="main_card").pack(anchor="w")
        ui.label(
            page,
            text="参加者や場面に合わせて、強く反映したい話し方の条件を入力します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        section = ui.frame(page, bg="panel")
        section.pack(fill="both", expand=True)

        ui.label(
            section,
            text="プロンプトに強く反映する指示",
            font="section_title",
            bg="panel",
        ).pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(fill="both", expand=True, padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        self.text_box = tk.Text(
            card,
            height=12,
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
        self.text_box.pack(fill="both", expand=True, padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])
        self.text_box.insert("1.0", self.initial_text)
        self.text_box.bind("<KeyRelease>", lambda _event=None: self.save_selection_only(update_status=False))

        self.build_bottom_area(page)

    def build_bottom_area(self, parent):
        bottom = ui.frame(parent, bg="main_card")
        bottom.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.action_button(
            bottom,
            text="保存して次へ",
            command=self.save_and_next,
        ).pack(side="right")

    def get_text(self):
        if self.text_box is None:
            return ""
        return self.text_box.get("1.0", "end").strip()

    def get_current_data(self):
        text = self.get_text()
        return {
            "label": "特別考慮",
            "text": text,
            "prompt": (
                "以下の特別考慮は強い制約として扱い、可能な限り全ての店員発話に反映してください。"
                f"\n{text}"
            ) if text else "",
            "strength": "strong",
            "description": "参加者や場面に合わせて強く反映する自由記述の配慮条件。",
        }

    def save_selection_only(self, update_status=True):
        self.profile_store.set("special_consideration", self.get_current_data(), auto_save=True)
        if update_status:
            self.status_var.set("特別考慮を保存しました")

    def save_and_next(self):
        self.save_selection_only()
        if self.on_saved is not None:
            self.on_saved()
