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
        self.axis_enabled_vars = {}
        self.value_labels = {}
        self.preview_changed_axes = None

        self.build_ui()
        self.load_face_data(self.face_data, notify=False)

    def normalize_face_data(self, data):
        label = data.get("label", "笑顔")
        normalized = default_face_data(label)
        saved_axes = {str(axis): int(value) for axis, value in data.get("axes", {}).items()}
        if data.get("axes"):
            normalized["axes"].update(saved_axes)
        if data.get("groups"):
            saved_groups = {
                group.get("id"): dict(group)
                for group in data["groups"]
                if group.get("id")
            }
            normalized_groups = []
            for default_group in normalized.get("groups", []):
                group = dict(default_group)
                saved_group = saved_groups.pop(group["id"], None)
                axes = [str(axis) for axis in group.get("axes", [])]
                group["axes"] = axes
                group.setdefault("mode", "set")
                if saved_group and saved_group.get("values"):
                    group["values"] = {
                        str(axis): int(value)
                        for axis, value in saved_group.get("values", {}).items()
                        if str(axis) in axes
                    }
                group.setdefault("values", {})
                if not group["values"]:
                    group["values"] = {
                        str(axis): int(normalized["axes"].get(str(axis), group.get("default", 0)))
                        for axis in axes
                    }
                group["values"] = {
                    str(axis): int(value)
                    for axis, value in group.get("values", {}).items()
                }
                for axis in axes:
                    axis = str(axis)
                    if axis in saved_axes:
                        group["values"][axis] = int(saved_axes[axis])
                    else:
                        group["values"].setdefault(
                            axis,
                            int(normalized["axes"].get(axis, group.get("default", 0))),
                        )
                if saved_group and "enabled_axes" in saved_group:
                    enabled_axes = [
                        str(axis)
                        for axis in saved_group.get("enabled_axes", [])
                        if str(axis) in axes
                    ]
                    group["enabled_axes"] = enabled_axes or list(axes)
                else:
                    group["enabled_axes"] = list(axes)
                normalized["axes"].update(group["values"])
                normalized_groups.append(group)
            for group in saved_groups.values():
                axes = [str(axis) for axis in group.get("axes", [])]
                if not axes:
                    continue
                group["axes"] = axes
                group.setdefault("mode", "set")
                group.setdefault("values", {})
                group["values"] = {
                    str(axis): int(value)
                    for axis, value in group.get("values", {}).items()
                }
                for axis in axes:
                    if axis in saved_axes:
                        group["values"][axis] = int(saved_axes[axis])
                group["enabled_axes"] = [
                    str(axis)
                    for axis in group.get("enabled_axes", axes)
                ]
                normalized["axes"].update(group["values"])
                normalized_groups.append(group)
            normalized["groups"] = normalized_groups
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
        self.axis_enabled_vars = {}
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

        axes = [str(axis) for axis in group.get("axes", [])]
        first_axis = axes[0]
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
            command=lambda _value=None, g=group: self.on_group_value_changed(g),
        )
        scale.pack(side="left", fill="x", expand=True)
        scale.bind(
            "<ButtonRelease-1>",
            lambda _event=None, g=group: self.notify_changed(
                force=True,
                changed_axes=self.enabled_axes_for_group(g),
            ),
            add="+",
        )

        check_row = ui.frame(block, bg="card")
        check_row.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))
        ui.label(check_row, text="送信", font="small", bg="card", fg="muted").pack(side="left")
        enabled_axes = {str(axis) for axis in group.get("enabled_axes", axes)}
        for axis in axes:
            enabled_var = tk.BooleanVar(value=axis in enabled_axes)
            self.axis_enabled_vars[(group["id"], axis)] = enabled_var
            axis_label = f"軸{axis}"
            if FACE_AXIS_LABELS.get(axis):
                axis_label = f"{axis_label} {FACE_AXIS_LABELS[axis]}"
            check = tk.Checkbutton(
                check_row,
                text=axis_label,
                variable=enabled_var,
                command=lambda g=group: self.on_group_enabled_changed(g),
                font=ui.FONTS["small"],
                bg=ui.COLORS["card"],
                fg=ui.COLORS["text"],
                activebackground=ui.COLORS["card"],
                activeforeground=ui.COLORS["text"],
                selectcolor=ui.COLORS["card"],
                padx=4,
            )
            check.pack(side="left", padx=(ui.SPACING["small_gap"], 0))

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

    def on_group_value_changed(self, group):
        value = int(self.axis_vars[group["id"]].get())
        self.value_labels[group["id"]].set(str(value))
        values = {axis: value for axis in group.get("axes", [])}
        group["values"] = values
        self.face_data["axes"].update(values)
        self.preview_changed_axes = self.enabled_axes_for_group(group)
        self.notify_changed()

    def on_group_enabled_changed(self, group):
        group["enabled_axes"] = self.enabled_axes_for_group(group)
        self.preview_changed_axes = list(group["enabled_axes"])
        self.notify_changed(force=True, changed_axes=self.preview_changed_axes)

    def enabled_axes_for_group(self, group):
        enabled = []
        for axis in group.get("axes", []):
            var = self.axis_enabled_vars.get((group["id"], str(axis)))
            if var is None or var.get():
                enabled.append(str(axis))
        return enabled

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
