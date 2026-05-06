import tkinter as tk

from .. import ui_style as ui
from ..config_face import (
    REQUEST_FACE_KEEPTIME,
    REQUEST_FACE_OPTIONS,
    REQUEST_FACE_PRIORITY,
)
from ..config_intention import (
    REQUEST_DEFAULT_TEXT,
    REQUEST_TECHNIQUE_DEFS,
    REQUEST_TECHNIQUE_LABELS,
    REQUEST_TECHNIQUE_ORDER,
    REQUEST_TEXT_VARIANTS,
    REQUEST_VOICE_PRESETS,
    apply_request_techniques_to_text,
)
from .simple_intent_tab import SimpleIntentTab


class RequestTab(SimpleIntentTab):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        data = profile_store.get_nested("request", {})
        self.technique_vars = {
            key: tk.BooleanVar(value=(key in data.get("techniques", [])))
            for key in REQUEST_TECHNIQUE_ORDER
        }

        super().__init__(
            parent,
            profile_store=profile_store,
            tts_client=tts_client,
            status_var=status_var,
            intent_key="request",
            intent_label="要求時",
            page_title="要求時の話し方を選ぶ",
            description="相手に行動をお願いするときの本文、テクニック、表情、声色を調整します。",
            text_title="要求文",
            default_text=REQUEST_DEFAULT_TEXT,
            text_variants=REQUEST_TEXT_VARIANTS,
            face_options=REQUEST_FACE_OPTIONS,
            face_priority=REQUEST_FACE_PRIORITY,
            face_keeptime=REQUEST_FACE_KEEPTIME,
            voice_presets=REQUEST_VOICE_PRESETS,
            on_saved=on_saved,
        )

    def build_extra_areas(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        ui.label(section, text="テクニック", font="section_title", bg="panel").pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        grid = ui.frame(card, bg="card")
        grid.pack(fill="x", padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])

        for index, key in enumerate(REQUEST_TECHNIQUE_ORDER):
            item = ui.frame(grid, bg="card")
            item.grid(
                row=0,
                column=index,
                sticky="ew",
                padx=(0, ui.SPACING["gap"]),
                pady=(0, ui.SPACING["small_gap"]),
            )
            grid.columnconfigure(index, weight=1)

            check = tk.Checkbutton(
                item,
                text=REQUEST_TECHNIQUE_LABELS[key],
                variable=self.technique_vars[key],
                command=lambda _key=key: self.on_technique_changed(),
                font=ui.FONTS["body_bold"],
                bg=ui.COLORS["card"],
                fg=ui.COLORS["text"],
                activebackground=ui.COLORS["card"],
                activeforeground=ui.COLORS["text"],
                selectcolor=ui.COLORS["card"],
                anchor="w",
            )
            check.pack(anchor="w")

            ui.label(
                item,
                text=REQUEST_TECHNIQUE_DEFS[key],
                font="small",
                bg="card",
                fg="muted",
                wraplength=300,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=(24, 0))

    def selected_techniques(self):
        return [
            key
            for key in REQUEST_TECHNIQUE_ORDER
            if self.technique_vars[key].get()
        ]

    def on_technique_changed(self):
        self.regenerate_text()

    def apply_text_customization(
        self,
        text,
        politeness_id,
        intimacy_id,
        vocabulary_id,
        length_id,
        person_key,
    ):
        return apply_request_techniques_to_text(
            base_text=text,
            selected_techniques=self.selected_techniques(),
            politeness_id=politeness_id,
            intimacy_id=intimacy_id,
        )

    def get_extra_data(self):
        return {
            "techniques": self.selected_techniques(),
        }
