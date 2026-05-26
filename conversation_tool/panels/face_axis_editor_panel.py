import tkinter as tk
from tkinter import ttk

from .. import ui_style as ui
from ..config import (
    FACE_AXIS_LABELS,
    FACE_AXIS_RANGE,
    FACE_EXPRESSION_DEFINITIONS,
    default_face_data,
    face_definition_by_label,
)


class FaceAxisEditorPanel(tk.Frame):
    def __init__(self, parent, initial_data=None, on_changed=None):
        super().__init__(parent, bg=ui.COLORS["panel"])

        initial_data = initial_data or default_face_data()
        self.on_changed = on_changed
        self._loading = False
        self.face_data = self.normalize_face_data(initial_data)
        self.expression_label = tk.StringVar(value=self.face_data["label"])
        self.axis_vars = {}
        self.value_labels = {}
        self.preview_changed_axes = None

        self.build_ui()
        self.load_face_data(self.face_data, notify=False)

    def normalize_face_data(self, data):
        label = data.get("label", "笑顔")
        normalized = default_face_data(label)
        if data.get("axes"):
            normalized["axes"].update({str(axis): int(value) for axis, value in data["axes"].items()})
        if data.get("groups"):
            normalized["groups"] = data["groups"]
        if data.get("command"):
            normalized["command"].update(data["command"])
        return normalized

    def build_ui(self):
        header = ui.frame(self, bg="panel")
        header.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))
        ui.label(header, text="表情", font="section_title", bg="panel").pack(side="left")

        combo = ttk.Combobox(
            header,
            values=[definition["label"] for definition in FACE_EXPRESSION_DEFINITIONS.values()],
            textvariable=self.expression_label,
            state="readonly",
            width=14,
        )
        combo.pack(side="right")
        combo.bind("<<ComboboxSelected>>", lambda _event=None: self.load_expression(self.expression_label.get()))

        self.card = ui.bordered_frame(self, bg="card", border="border")
        self.card.pack(fill="x")

    def rebuild_axis_controls(self):
        for child in self.card.winfo_children():
            child.destroy()

        self.axis_vars = {}
        self.value_labels = {}
        if not self.face_data.get("groups"):
            command = self.face_data.get("command", {}).get("text", "/emotion neutral")
            ui.label(
                self.card,
                text=f"この表情は軸調整ではなく {command} を送ります。",
                font="body",
                bg="card",
                fg="sub_text",
                anchor="w",
                justify="left",
            ).pack(fill="x", padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])
            return

        for group in self.face_data.get("groups", []):
            self.build_group_control(group)

    def build_group_control(self, group):
        block = ui.frame(self.card, bg="card")
        block.pack(fill="x", padx=ui.SPACING["card_x"], pady=(ui.SPACING["small_gap"], 0))

        title = ui.frame(block, bg="card")
        title.pack(fill="x")
        axes_label = " / ".join(
            f"軸{axis} {FACE_AXIS_LABELS.get(axis, '')}".strip()
            for axis in group.get("axes", [])
        )
        ui.label(title, text=group["label"], font="body_bold", bg="card").pack(side="left")
        ui.label(title, text=axes_label, font="small", bg="card", fg="muted").pack(side="left", padx=(ui.SPACING["gap"], 0))

        if group.get("mode") == "symmetric":
            first_axis = group["axes"][0]
            value = int(group.get("values", {}).get(first_axis, self.face_data["axes"].get(first_axis, 0)))
            var = tk.IntVar(value=value)
            label_var = tk.StringVar(value=str(value))
            self.value_labels[group["id"]] = label_var
            self.axis_vars[group["id"]] = var

            row = ui.frame(block, bg="card")
            row.pack(fill="x")
            ui.variable_label(row, label_var, font="small", bg="card", fg="muted", width=4, anchor="e").pack(
                side="left", padx=(0, ui.SPACING["small_gap"])
            )
            scale = ui.scale(
                row,
                variable=var,
                from_=FACE_AXIS_RANGE[0],
                to=FACE_AXIS_RANGE[1],
                resolution=1,
                command=lambda _value=None, g=group: self.on_symmetric_changed(g),
            )
            scale.pack(side="left", fill="x", expand=True)
            scale.bind(
                "<ButtonRelease-1>",
                lambda _event=None, g=group: self.notify_changed(
                    force=True,
                    changed_axes=list(g.get("axes", [])),
                ),
                add="+",
            )
            return

        for axis in group.get("axes", []):
            value = int(group.get("values", {}).get(axis, self.face_data["axes"].get(axis, 0)))
            var = tk.IntVar(value=value)
            label_var = tk.StringVar(value=str(value))
            self.value_labels[axis] = label_var
            self.axis_vars[axis] = var

            row = ui.frame(block, bg="card")
            row.pack(fill="x")
            ui.label(row, text=f"軸{axis}", font="small", bg="card", fg="sub_text", width=5, anchor="w").pack(side="left")
            ui.variable_label(row, label_var, font="small", bg="card", fg="muted", width=4, anchor="e").pack(
                side="left", padx=(0, ui.SPACING["small_gap"])
            )
            scale = ui.scale(
                row,
                variable=var,
                from_=FACE_AXIS_RANGE[0],
                to=FACE_AXIS_RANGE[1],
                resolution=1,
                command=lambda _value=None, a=axis: self.on_axis_changed(a),
            )
            scale.pack(side="left", fill="x", expand=True)
            scale.bind(
                "<ButtonRelease-1>",
                lambda _event=None, a=axis: self.notify_changed(force=True, changed_axes=[a]),
                add="+",
            )

    def load_expression(self, label):
        self.load_face_data(default_face_data(label), force_notify=True)

    def load_face_data(self, data, notify=True, force_notify=False):
        self._loading = True
        try:
            self.face_data = self.normalize_face_data(data)
            self.expression_label.set(self.face_data["label"])
            self.rebuild_axis_controls()
        finally:
            self._loading = False
        if notify:
            self.notify_changed(force=force_notify)

    def on_symmetric_changed(self, group):
        value = int(self.axis_vars[group["id"]].get())
        self.value_labels[group["id"]].set(str(value))
        values = {axis: value for axis in group.get("axes", [])}
        group["values"] = values
        self.face_data["axes"].update(values)
        self.preview_changed_axes = list(group.get("axes", []))
        self.notify_changed()

    def on_axis_changed(self, axis):
        value = int(self.axis_vars[axis].get())
        self.value_labels[axis].set(str(value))
        self.face_data["axes"][axis] = value
        self.preview_changed_axes = [axis]
        for group in self.face_data.get("groups", []):
            if axis in group.get("axes", []):
                group.setdefault("values", {})[axis] = value
                break
        self.notify_changed()

    def notify_changed(self, force=False, changed_axes=None):
        if self._loading or self.on_changed is None:
            return
        axes = changed_axes if changed_axes is not None else self.preview_changed_axes
        self.on_changed(self.get_data(), force=force, changed_axes=axes)

    def get_data(self):
        return {
            "id": self.face_data["id"],
            "label": self.face_data["label"],
            "groups": self.face_data["groups"],
            "axes": {axis: int(value) for axis, value in self.face_data["axes"].items()},
            "command": self.face_data["command"],
        }
