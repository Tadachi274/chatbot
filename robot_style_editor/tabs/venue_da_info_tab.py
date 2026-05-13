import tkinter as tk

from .. import ui_style as ui


class VenueDAInfoTab(tk.Frame):
    def __init__(
        self,
        parent,
        profile_store,
        tts_client,
        status_var,
        required_intents=None,
        unused_intents=None,
        venue_label=None,
        on_saved=None,
    ):
        super().__init__(parent, bg=ui.COLORS["main_card"])
        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.required_intents = required_intents or []
        self.unused_intents = unused_intents or []
        self.venue_label = venue_label or "選択店舗"
        self.on_saved = on_saved
        self.build_ui()

    def build_ui(self):
        page = ui.scrollable_frame(
            self,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )
        ui.label(page, text="DA設定範囲", font="page_title", bg="main_card").pack(anchor="w")
        ui.label(
            page,
            text=f"{self.venue_label}では、雑談以外のDAを共通で設定します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        self.render_group(page, "この店舗で設定するDA", self.required_intents, "雑談以外を設定します。")
        self.render_group(page, "この店舗では設定しないDA", self.unused_intents, "今回は調整対象外です。")

    def render_group(self, parent, title, items, empty_text):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(0, ui.SPACING["section_y"]))

        ui.label(section, text=title, font="section_title", bg="panel").pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        if not items:
            ui.label(
                card,
                text=empty_text,
                font="body",
                bg="card",
                fg="muted",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])
            return

        for item in items:
            ui.label(
                card,
                text=f"{item['label']}：{item['reason']}",
                font="body",
                bg="card",
                fg="text",
                justify="left",
                anchor="w",
                wraplength=920,
            ).pack(anchor="w", fill="x", padx=ui.SPACING["card_x"], pady=(ui.SPACING["compact_y"], 0))
