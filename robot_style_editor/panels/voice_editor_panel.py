import tkinter as tk
from tkinter import ttk, messagebox

from .. import ui_style as ui
from ..config_intention import (
    VOICE_BASE_PARAMS,
    VOICE_CONTROL_RANGE,
    VOICE_PRESETS,
    VOICE_RANGE,
    compute_voice_params,
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
    def __init__(
        self,
        parent,
        initial_data=None,
        tts_client=None,
        get_text=None,
        get_speaker=None,
        on_changed=None,
        voice_presets=None,
    ):
        super().__init__(parent, bg=ui.COLORS["panel"])

        initial_data = initial_data or {}
        controls = initial_data.get("controls", {})
        params = initial_data.get("params", {})

        self.tts_client = tts_client
        self.get_text = get_text
        self.get_speaker = get_speaker
        self.on_changed = on_changed
        self.voice_presets = voice_presets or VOICE_PRESETS
        self._loading = False

        default_preset_id = self.voice_presets[0]["id"]
        preset_id = initial_data.get("base_preset", default_preset_id)
        preset = self.find_preset(preset_id)

        self.preset_id = tk.StringVar(value=preset_id)
        self.friendly = tk.DoubleVar(value=float(controls.get("friendly", preset["friendly"])))
        self.calm = tk.DoubleVar(value=float(controls.get("calm", preset["calm"])))
        self.tension = tk.DoubleVar(value=float(controls.get("tension", preset["tension"])))

        self.param_vars = {
            key: tk.DoubleVar(value=float(params.get(key, VOICE_BASE_PARAMS[key])))
            for key in VOICE_BASE_PARAMS
        }
        self.control_labels = []
        self.param_labels = []

        self.build_ui()
        self.attach_traces()

        if not params:
            self.apply_abstract_controls(notify=False)
        else:
            self.update_all_labels(notify=False)

    def build_ui(self):
        section = ui.frame(self, bg="panel")
        section.pack(fill="x")

        header = ui.frame(section, bg="panel")
        header.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        ui.label(
            header,
            text="声色の詳細調整",
            font="section_title",
            bg="panel",
        ).pack(side="left")

        ui.sub_button(
            header,
            text="この文章で試聴",
            command=self.speak_current_text,
        ).pack(side="right")

        ui.sub_button(
            header,
            text="デフォルトに戻す",
            command=self.reset_to_default,
        ).pack(side="right", padx=(0, ui.SPACING["small_gap"]))

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["section_y"]),
        )

        preset_row = ui.frame(card, bg="card")
        preset_row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]),
        )

        ui.label(
            preset_row,
            text="読み込み",
            font="body",
            bg="card",
            fg="sub_text",
            width=8,
            anchor="w",
        ).pack(side="left")

        combo = ttk.Combobox(
            preset_row,
            values=[opt["label"] for opt in self.voice_presets if opt["id"] != "other"],
            state="readonly",
            width=16,
        )
        combo.pack(side="left")
        combo.set(self.find_preset(self.preset_id.get())["label"])
        combo.bind("<<ComboboxSelected>>", lambda _event=None, widget=combo: self.on_preset_combo_selected(widget.get()))

        ui.sub_button(
            preset_row,
            text="抽象値を7項目へ反映",
            command=self.apply_abstract_controls,
        ).pack(side="right")

        self.build_control_slider(card, "親しみ", self.friendly)
        self.build_control_slider(card, "落ち着き度", self.calm)
        self.build_control_slider(card, "テンション", self.tension)

        separator = tk.Frame(card, height=1, bg=ui.COLORS["soft_border"])
        separator.pack(fill="x", padx=ui.SPACING["card_x"], pady=ui.SPACING["small_gap"])

        for key in ("volume", "rate", "pitch", "emphasis", "joy", "anger", "sadness"):
            self.build_param_slider(
                card,
                key=key,
                label=VOICE_PARAM_LABELS[key],
                variable=self.param_vars[key],
            )

    def build_control_slider(self, parent, label, variable):
        vmin, vmax = VOICE_CONTROL_RANGE
        self.build_slider_row(
            parent,
            label=label,
            variable=variable,
            vmin=vmin,
            vmax=vmax,
            target=self.control_labels,
        )

    def build_param_slider(self, parent, key, label, variable):
        vmin, vmax = VOICE_RANGE[key]
        self.build_slider_row(
            parent,
            label=label,
            variable=variable,
            vmin=vmin,
            vmax=vmax,
            target=self.param_labels,
        )

    def build_slider_row(self, parent, label, variable, vmin, vmax, target):
        row = ui.frame(parent, bg="card")
        row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], 0),
        )

        ui.label(
            row,
            text=label,
            font="body",
            bg="card",
            fg="sub_text",
            width=9,
            anchor="w",
        ).pack(side="left")

        value_label = tk.StringVar(value=f"{variable.get():.2f}")
        target.append((variable, value_label))

        ui.variable_label(
            row,
            textvariable=value_label,
            font="small",
            bg="card",
            fg="muted",
            width=5,
            anchor="e",
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))

        slider_area = ui.frame(row, bg="card")
        slider_area.pack(side="left", fill="x", expand=True)

        ui.scale(
            slider_area,
            variable=variable,
            from_=vmin,
            to=vmax,
            command=lambda _value=None: self.on_slider_changed(),
        ).pack(fill="x")

    def attach_traces(self):
        for var in (
            self.friendly,
            self.calm,
            self.tension,
            *self.param_vars.values(),
        ):
            var.trace_add("write", lambda *_: self.update_all_labels())

    def on_slider_changed(self):
        self.update_all_labels()

    def on_preset_combo_selected(self, label):
        for opt in self.voice_presets:
            if opt["label"] == label:
                self.load_preset(opt)
                return

    def load_preset(self, opt):
        self._loading = True
        try:
            self.preset_id.set(opt["id"])
            self.friendly.set(float(opt["friendly"]))
            self.calm.set(float(opt["calm"]))
            self.tension.set(float(opt["tension"]))
            params = compute_voice_params(
                friendly=self.friendly.get(),
                calm=self.calm.get(),
                tension=self.tension.get(),
            )
            for key, value in params.items():
                self.param_vars[key].set(float(value))
        finally:
            self._loading = False

        self.update_all_labels()

    def apply_abstract_controls(self, notify=True):
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

        self.update_all_labels(notify=notify)

    def reset_to_default(self):
        preset = self.get_default_preset()
        self._loading = True
        try:
            self.preset_id.set(preset["id"])
            self.friendly.set(1.0)
            self.calm.set(1.0)
            self.tension.set(1.0)
            for key, value in VOICE_BASE_PARAMS.items():
                self.param_vars[key].set(float(value))
        finally:
            self._loading = False

        self.update_all_labels()

    def update_all_labels(self, notify=True):
        for var, label_var in (*self.control_labels, *self.param_labels):
            label_var.set(f"{var.get():.2f}")

        if notify and not self._loading and self.on_changed is not None:
            self.on_changed(self.get_data())

    def find_preset(self, preset_id):
        for opt in self.voice_presets:
            if opt["id"] == preset_id:
                return opt

        return self.get_default_preset()

    def get_default_preset(self):
        for opt in self.voice_presets:
            if opt["id"] != "other":
                return opt

        return VOICE_PRESETS[0]

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
            "base_preset": self.preset_id.get(),
            "controls": self.get_controls(),
            "params": self.get_params(),
        }

    def get_tts_instructions(self):
        return voice_params_to_tts_instructions(self.get_params())

    def speak_current_text(self):
        if self.tts_client is None or self.get_text is None:
            return

        text = self.get_text().strip()
        if not text:
            messagebox.showwarning("確認", "読み上げる文を入力してください。")
            return

        speaker = self.get_speaker() if self.get_speaker is not None else None
        self.tts_client.speak(
            text=text,
            instructions=self.get_tts_instructions(),
            person=speaker,
        )
