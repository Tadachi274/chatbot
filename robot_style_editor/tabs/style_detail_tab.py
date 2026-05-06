import tkinter as tk

from .. import ui_style as ui
from ..config_style_detail import (
    STYLE_DETAIL_DEFAULTS,
    STYLE_DETAIL_SECTIONS,
    get_style_detail_option,
)


class StyleDetailTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])
        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        data = self.profile_store.get_nested("style_detail", {}) or {}
        selections = data.get("selections", {})

        self.multi_vars = {}
        self.single_vars = {}
        for section in STYLE_DETAIL_SECTIONS:
            key = section["key"]
            if section["mode"] == "multi":
                selected = selections.get(key, STYLE_DETAIL_DEFAULTS.get(key, []))
                self.multi_vars[key] = {
                    opt["id"]: tk.BooleanVar(value=opt["id"] in selected)
                    for opt in section["options"]
                }
            else:
                self.single_vars[key] = tk.StringVar(
                    value=selections.get(key, STYLE_DETAIL_DEFAULTS.get(key, section["default"]))
                )

        self.build_ui()

    def build_ui(self):
        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )

        ui.label(page, text="詳細設定", font="page_title", bg="main_card").pack(anchor="w")
        ui.label(
            page,
            text="DAごとの技法ではなく、全体的な話し方の傾向を決めます。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        content = ui.scrollable_frame(page, pady=(0, ui.SPACING["small_gap"]))

        for section in STYLE_DETAIL_SECTIONS:
            self.build_section(content, section)

        self.build_bottom_area(page)

    def build_section(self, parent, section):
        section_frame = ui.frame(parent, bg="panel")
        section_frame.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))

        ui.label(
            section_frame,
            text=section["label"],
            font="section_title",
            bg="panel",
        ).pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        row = ui.frame(section_frame, bg="panel")
        row.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        for opt in section["options"]:
            card = ui.bordered_frame(row, bg="card", border="border")
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=ui.SPACING["small_gap"],
                pady=ui.SPACING["small_gap"],
            )

            if section["mode"] == "multi":
                check = tk.Checkbutton(
                    card,
                    text=opt["label"],
                    variable=self.multi_vars[section["key"]][opt["id"]],
                    command=lambda: self.save_selection_only(update_status=False),
                    font=ui.FONTS["body_bold"],
                    bg=ui.COLORS["card"],
                    fg=ui.COLORS["text"],
                    activebackground=ui.COLORS["card"],
                    activeforeground=ui.COLORS["text"],
                    selectcolor=ui.COLORS["card"],
                )
                check.pack(anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]))
            else:
                ui.radio(
                    card,
                    text=opt["label"],
                    variable=self.single_vars[section["key"]],
                    value=opt["id"],
                    command=lambda: self.save_selection_only(update_status=False),
                    bg="card",
                ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]))

            ui.label(
                card,
                text=opt["description"],
                font="small",
                bg="card",
                fg="muted",
                wraplength=ui.LAYOUT["card_text_wrap"],
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))

    def build_bottom_area(self, parent):
        bottom = ui.frame(parent, bg="main_card")
        bottom.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.action_button(
            bottom,
            text="保存して次へ",
            command=self.save_and_next,
        ).pack(side="right")

    def get_current_data(self):
        selections = {}
        labels = {}
        prompts = []

        for section in STYLE_DETAIL_SECTIONS:
            key = section["key"]
            if section["mode"] == "multi":
                selected = [
                    opt_id
                    for opt_id, var in self.multi_vars[key].items()
                    if var.get()
                ]
            else:
                selected = self.single_vars[key].get()

            selections[key] = selected
            labels[key] = self.get_selection_label(section, selected)
            prompts.extend(self.get_selection_prompts(section, selected))

        return {
            "label": "詳細設定",
            "selections": selections,
            "labels": labels,
            "prompt": " ".join(prompts),
            "description": "会話全体に反映する話し方の詳細傾向。",
        }

    def get_selection_label(self, section, selected):
        if section["mode"] == "multi":
            labels = []
            for opt_id in selected:
                opt = get_style_detail_option(section["key"], opt_id)
                if opt:
                    labels.append(opt["label"])
            return "、".join(labels) if labels else "なし"

        opt = get_style_detail_option(section["key"], selected)
        return opt["label"] if opt else selected

    def get_selection_prompts(self, section, selected):
        if section["mode"] == "multi":
            ids = selected
        else:
            ids = [selected]

        prompts = []
        for opt_id in ids:
            opt = get_style_detail_option(section["key"], opt_id)
            if opt:
                prompts.append(opt["prompt"])
        return prompts

    def save_selection_only(self, update_status=True):
        self.profile_store.set("style_detail", self.get_current_data(), auto_save=True)
        if update_status:
            self.status_var.set("詳細設定を保存しました")

    def save_and_next(self):
        self.save_selection_only()
        if self.on_saved is not None:
            self.on_saved()
