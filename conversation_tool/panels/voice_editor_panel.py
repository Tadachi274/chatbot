import tkinter as tk

from .. import ui_style as ui
from ..config import (
    VOICE_BASE_PARAMS,
    VOICE_CONTROL_RANGE,
    VOICE_RANGE,
    compute_voice_params,
    default_voice_data,
    voice_params_to_tts_instructions,
)


VOICE_PARAM_LABELS = {
    "volume": "音量",
    "rate": "速さ",
    "pitch": "高さ",
    "emphasis": "強調",
    "joy": "喜び",
    "anger": "怒り",
    "sadness": "悲しみ",
}


class VoiceEditorPanel(tk.Frame):
    def __init__(self, parent, initial_data=None, on_changed=None):
        super().__init__(parent, bg=ui.COLORS["panel"])

        data = initial_data or default_voice_data()
        controls = data.get("controls", {})
        params = data.get("params", {})

        self.on_changed = on_changed
        self._loading = False
        self.friendly = tk.DoubleVar(value=float(controls.get("friendly", 1.0)))
        self.calm = tk.DoubleVar(value=float(controls.get("calm", 1.0)))
        self.tension = tk.DoubleVar(value=float(controls.get("tension", 1.0)))
        self.param_vars = {
            key: tk.DoubleVar(value=float(params.get(key, VOICE_BASE_PARAMS[key])))
            for key in VOICE_BASE_PARAMS
        }
        self.value_labels = []

        self.build_ui()
        self.attach_traces()
        self.update_labels(notify=False)

    def build_ui(self):
        header = ui.frame(self, bg="panel")
        header.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))
        ui.label(header, text="声色", font="section_title", bg="panel").pack(side="left")
        ui.sub_button(header, text="デフォルトに戻す", command=self.reset_to_default).pack(side="right")
        ui.sub_button(header, text="抽象値を反映", command=self.apply_abstract_controls).pack(
            side="right", padx=(0, ui.SPACING["small_gap"])
        )

        card = ui.bordered_frame(self, bg="card", border="border")
        card.pack(fill="x")

        self.build_slider_row(card, "親しみ", self.friendly, *VOICE_CONTROL_RANGE)
        self.build_slider_row(card, "信頼度", self.calm, *VOICE_CONTROL_RANGE)
        self.build_slider_row(card, "テンション", self.tension, *VOICE_CONTROL_RANGE)

        separator = tk.Frame(card, height=1, bg=ui.COLORS["soft_border"])
        separator.pack(fill="x", padx=ui.SPACING["card_x"], pady=ui.SPACING["small_gap"])

        for key in ("volume", "rate", "pitch", "emphasis", "joy", "anger", "sadness"):
            self.build_slider_row(card, VOICE_PARAM_LABELS[key], self.param_vars[key], *VOICE_RANGE[key])

    def build_slider_row(self, parent, label, variable, vmin, vmax):
        row = ui.frame(parent, bg="card")
        row.pack(fill="x", padx=ui.SPACING["card_x"], pady=(ui.SPACING["small_gap"], 0))

        ui.label(row, text=label, font="body", bg="card", fg="sub_text", width=9, anchor="w").pack(side="left")
        value_label = tk.StringVar(value=f"{variable.get():.2f}")
        self.value_labels.append((variable, value_label))
        ui.variable_label(row, value_label, font="small", bg="card", fg="muted", width=5, anchor="e").pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.scale(
            row,
            variable=variable,
            from_=vmin,
            to=vmax,
            command=lambda _value=None: self.update_labels(),
        ).pack(side="left", fill="x", expand=True)

    def attach_traces(self):
        for var in (self.friendly, self.calm, self.tension, *self.param_vars.values()):
            var.trace_add("write", lambda *_: self.update_labels())

    def apply_abstract_controls(self):
        self._loading = True
        try:
            params = compute_voice_params(
                friendly=self.friendly.get(),
                calm=self.calm.get(),
                tension=self.tension.get(),
            )
            for key, value in params.items():
                self.param_vars[key].set(float(value))
        finally:
            self._loading = False
        self.update_labels()

    def reset_to_default(self):
        self._loading = True
        try:
            self.friendly.set(1.0)
            self.calm.set(1.0)
            self.tension.set(1.0)
            for key, value in VOICE_BASE_PARAMS.items():
                self.param_vars[key].set(float(value))
        finally:
            self._loading = False
        self.update_labels()

    def update_labels(self, notify=True):
        for var, label_var in self.value_labels:
            label_var.set(f"{var.get():.2f}")

        if notify and not self._loading and self.on_changed is not None:
            self.on_changed(self.get_data())

    def get_controls(self):
        return {
            "friendly": round(float(self.friendly.get()), 2),
            "calm": round(float(self.calm.get()), 2),
            "tension": round(float(self.tension.get()), 2),
        }

    def get_params(self):
        return {
            key: round(float(var.get()), 2)
            for key, var in self.param_vars.items()
        }

    def get_data(self):
        return {
            "controls": self.get_controls(),
            "params": self.get_params(),
            "tts_instructions": voice_params_to_tts_instructions(self.get_params()),
        }
