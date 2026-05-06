import tkinter as tk

from .. import ui_style as ui
from ..config_intention import (
    VOICE_PRESETS,
    compute_voice_params,
)
from .voice_editor_panel import VoiceEditorPanel


class VoiceStylePanel(tk.Frame):
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

        self.tts_client = tts_client
        self.get_text = get_text
        self.get_speaker = get_speaker
        self.on_changed = on_changed
        self.voice_presets = voice_presets or VOICE_PRESETS
        self._loading = False

        default_voice_id = self.voice_presets[0]["id"]
        self.selected_voice = tk.StringVar(value=initial_data.get("id", default_voice_id))
        self.editor = None
        self.editor_host = None
        self.editor_data = initial_data.get("editor", {})

        if initial_data.get("id") == "other" and not self.editor_data:
            self.editor_data = {
                "base_preset": initial_data.get("base_preset", self.get_default_preset()["id"]),
                "controls": initial_data.get("controls", {}),
                "params": initial_data.get("params", {}),
            }

        self.build_ui()
        self.refresh_editor_visibility(notify=False)

    def build_ui(self):
        section = ui.frame(self, bg="panel")
        section.pack(fill="x")

        ui.label(
            section,
            text="声色",
            font="section_title",
            bg="panel",
        ).pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        preset_row = ui.frame(section, bg="panel")
        preset_row.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["small_gap"]),
        )

        for opt in self.voice_presets:
            card = ui.bordered_frame(preset_row, bg="card", border="border")
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=(0, ui.SPACING["small_gap"]),
            )

            ui.radio(
                card,
                text=opt["label"],
                variable=self.selected_voice,
                value=opt["id"],
                command=lambda item=opt: self.on_preset_selected(item),
                bg="card",
            ).pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
            )

            ui.label(
                card,
                text=opt["description"],
                font="small",
                bg="card",
                fg="muted",
                wraplength=ui.LAYOUT["card_text_wrap"],
                justify="left",
                anchor="w",
            ).pack(
                fill="x",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["compact_y"]),
            )

        self.editor_host = ui.frame(section, bg="panel")
        self.editor_host.pack(fill="x")

    def on_preset_selected(self, opt):
        if opt["id"] == "other":
            if not self.editor_data:
                self.editor_data = self.build_editor_data_from_preset(self.get_default_preset())
        else:
            self.editor_data = self.build_editor_data_from_preset(opt)

        self.refresh_editor_visibility()

    def refresh_editor_visibility(self, notify=True):
        for child in self.editor_host.winfo_children():
            child.destroy()

        self.editor = None

        if self.selected_voice.get() == "other":
            self.editor = VoiceEditorPanel(
                self.editor_host,
                initial_data=self.editor_data,
                tts_client=self.tts_client,
                get_text=self.get_text,
                get_speaker=self.get_speaker,
                on_changed=self.on_editor_changed,
                voice_presets=self.voice_presets,
            )
            self.editor.pack(fill="x")

        if notify and self.on_changed is not None:
            self.on_changed(self.get_data())

    def on_editor_changed(self, data):
        self.editor_data = data
        if self.on_changed is not None:
            self.on_changed(self.get_data())

    def build_editor_data_from_preset(self, opt):
        controls = {
            "friendly": float(opt["friendly"]),
            "calm": float(opt["calm"]),
            "tension": float(opt["tension"]),
        }
        params = compute_voice_params(**controls)

        return {
            "base_preset": opt["id"],
            "controls": controls,
            "params": params,
        }

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

    def get_voice_params(self):
        if self.selected_voice.get() == "other":
            if self.editor is not None:
                self.editor_data = self.editor.get_data()
            return self.editor_data.get("params", compute_voice_params())

        opt = self.find_preset(self.selected_voice.get())
        return compute_voice_params(
            friendly=opt["friendly"],
            calm=opt["calm"],
            tension=opt["tension"],
        )

    def get_data(self):
        selected_id = self.selected_voice.get()
        preset = self.find_preset(selected_id)
        params = self.get_voice_params()

        data = {
            "id": selected_id,
            "label": preset["label"] if selected_id != "other" else "その他",
            "params": params,
        }

        if selected_id == "other":
            if self.editor is not None:
                self.editor_data = self.editor.get_data()
            data["editor"] = self.editor_data
            data["controls"] = self.editor_data.get("controls", {})
            data["base_preset"] = self.editor_data.get("base_preset", "friendly")
        else:
            data["controls"] = {
                "friendly": float(preset["friendly"]),
                "calm": float(preset["calm"]),
                "tension": float(preset["tension"]),
            }

        return data
