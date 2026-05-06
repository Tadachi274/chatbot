import json
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

from .. import ui_style as ui
from ..config_face import (
    FACE_AXIS_NAMES,
    FACE_DEFAULT_VALUES,
    FACE_DEFAULT_HEADER,
    FACE_EDITOR_VELOCITY,
    FACE_EDITOR_PRIORITY,
    FACE_EDITOR_KEEPTIME,
    FACE_AXIS_IMAGE_PATH,
)

try:
    from ..config_face import FACE_AXIS_DESCRIPTIONS
except ImportError:
    FACE_AXIS_DESCRIPTIONS = {}

from ..face_preset_store import load_face_presets, save_face_preset


class FaceEditorPanel(tk.Frame):
    def __init__(self, parent, robot_client, on_back=None, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.robot_client = robot_client
        self.on_back = on_back
        self.on_saved = on_saved

        self.face_preset_name = tk.StringVar(value="neutral")
        self.face_selected_level = tk.IntVar(value=1)

        self.face_ms1 = tk.IntVar(value=FACE_DEFAULT_HEADER[0])
        self.face_ms2 = tk.IntVar(value=FACE_DEFAULT_HEADER[1])
        self.face_ms3 = tk.IntVar(value=FACE_DEFAULT_HEADER[2])

        self.face_params = [tk.IntVar(value=v) for v in FACE_DEFAULT_VALUES]
        self.face_default_values = list(FACE_DEFAULT_VALUES)

        self.face_presets = load_face_presets()
        preset_names = sorted(self.face_presets.keys())
        self.selected_preset_name = tk.StringVar(value=preset_names[0] if preset_names else "")

        self.build_ui()

    def build_ui(self):
        self.build_editor_view()

    def clear_views(self):
        for child in self.winfo_children():
            child.destroy()

    def build_editor_view(self):
        self.clear_views()

        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )

        ui.label(
            page,
            text="その他の表情を作る",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            page,
            text="既存表情を読み込んで調整したり、軸を直接動かして新しい表情を作成できます。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(
            anchor="w",
            pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]),
        )

        self.build_top_controls(page)
        self.build_axis_area(page)

    def build_reference_view(self):
        self.clear_views()

        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )

        header = ui.frame(page, bg="main_card")
        header.pack(fill="x")

        ui.label(
            header,
            text="軸の対応を見る",
            font="page_title",
            bg="main_card",
        ).pack(side="left", anchor="w")

        ui.sub_button(
            header,
            text="戻る",
            command=self.build_editor_view,
        ).pack(side="right")

        ui.label(
            page,
            text="スライダーの番号は、写真の番号に対応しています。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(
            anchor="w",
            pady=(ui.SPACING["small_gap"], ui.SPACING["small_gap"]),
        )


        image_area = ui.frame(page, bg="main_card")
        image_area.pack(fill="both", expand=True)

        if FACE_AXIS_IMAGE_PATH.exists():
            img = Image.open(FACE_AXIS_IMAGE_PATH)

            # 半時計回りに90度回転してから、小さめに表示する
            img = img.rotate(90, expand=True)
            img.thumbnail((700, 700))

            self.axis_reference_tk = ImageTk.PhotoImage(img)

            label = tk.Label(
                image_area,
                image=self.axis_reference_tk,
                bg=ui.COLORS["main_card"],
                bd=0,
                highlightthickness=0,
            )
            label.pack(anchor="center")
        else:
            ui.label(
                image_area,
                text=f"画像が見つかりません: {FACE_AXIS_IMAGE_PATH}",
                font="small",
                bg="main_card",
                fg="muted",
            ).pack(anchor="w")

    def build_top_controls(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        # =========================
        # 1段目：保存名・レベル・戻る
        # =========================
        row1 = ui.frame(section, bg="panel")
        row1.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        name_area = ui.frame(row1, bg="panel")
        name_area.pack(side="left", fill="x", expand=True)

        ui.label(
            name_area,
            text="保存名",
            font="body",
            bg="panel",
            fg="sub_text",
        ).pack(anchor="w")

        ui.entry(
            name_area,
            textvariable=self.face_preset_name,
            font="input",
        ).pack(fill="x", ipady=6)

        level_area = ui.frame(row1, bg="panel")
        level_area.pack(side="left", padx=(ui.SPACING["gap"], 0))

        ui.label(
            level_area,
            text="レベル",
            font="body",
            bg="panel",
            fg="sub_text",
        ).pack(anchor="w")

        level_row = ui.frame(level_area, bg="panel")
        level_row.pack(anchor="w")

        for value in (1, 2, 3):
            ui.radio(
                level_row,
                text=str(value),
                variable=self.face_selected_level,
                value=value,
                bg="panel",
            ).pack(side="left", padx=2)

        if self.on_back is not None:
            ui.sub_button(
                row1,
                text="戻る",
                command=self.on_back,
            ).pack(side="right", padx=(ui.SPACING["gap"], 0))

        # =========================
        # 2段目：既存表情読み込み・操作ボタン
        # =========================
        row2 = ui.frame(section, bg="panel")
        row2.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["section_y"]),
        )

        preset_area = ui.frame(row2, bg="panel")
        preset_area.pack(side="left", fill="x", expand=True)

        ui.label(
            preset_area,
            text="既存表情",
            font="body",
            bg="panel",
            fg="sub_text",
        ).pack(anchor="w")

        preset_row = ui.frame(preset_area, bg="panel")
        preset_row.pack(fill="x")

        preset_names = sorted(self.face_presets.keys())

        self.preset_combo = ttk.Combobox(
            preset_row,
            values=preset_names,
            textvariable=self.selected_preset_name,
            width=24,
            state="readonly",
        )
        self.preset_combo.pack(side="left")

        self.preset_combo.bind(
            "<<ComboboxSelected>>",
            self.on_preset_selected,
        )

        ui.sub_button(
            preset_row,
            text="読み込む",
            command=self.load_selected_preset,
        ).pack(side="left", padx=(ui.SPACING["small_gap"], 0))

        button_area = ui.frame(row2, bg="panel")
        button_area.pack(side="right", padx=(ui.SPACING["gap"], 0))

        ui.sub_button(
            button_area,
            text="neutralに戻す",
            command=self.reset_to_default,
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))

        ui.sub_button(
            button_area,
            text="現在値を基準にする",
            command=self.update_face_default,
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))

        ui.sub_button(
            button_area,
            text="軸対応を見る",
            command=self.build_reference_view,
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))

        ui.sub_button(
            button_area,
            text="送信",
            command=self.send_axes,
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))

        ui.action_button(
            button_area,
            text="保存",
            command=self.save_current_preset,
        ).pack(side="left")

    def build_axis_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(
            fill="both",
            expand=True,
            pady=(ui.SPACING["small_gap"], 0),
        )

        grid = ui.scrollable_frame(section, bg="panel")

        # 5列にして縦方向を圧縮
        axis_columns = 5

        for col in range(axis_columns):
            grid.grid_columnconfigure(col, weight=1)

        for i, (axis_name, var) in enumerate(zip(FACE_AXIS_NAMES, self.face_params)):
            cell = ui.bordered_frame(grid, bg="card", border="border")
            cell.grid(
                row=i // axis_columns,
                column=i % axis_columns,
                sticky="ew",
                padx=2,
                pady=2,
            )

            top = ui.frame(cell, bg="card")
            top.pack(
                fill="x",
                padx=6,
                pady=(3, 0),
            )

            ui.label(
                top,
                text=f"軸 {axis_name}",
                font="small",
                bg="card",
                fg="sub_text",
            ).pack(side="left")

            value_label = tk.StringVar(value=str(var.get()))

            ui.variable_label(
                top,
                textvariable=value_label,
                font="small",
                bg="card",
                fg="text",
            ).pack(side="right")

            axis_description = FACE_AXIS_DESCRIPTIONS.get(axis_name, "")

            ui.label(
                cell,
                text=axis_description or f"写真の{axis_name}番",
                font="small",
                bg="card",
                fg="muted",
                wraplength=160,
                justify="left",
                anchor="w",
            ).pack(
                fill="x",
                padx=6,
                pady=(0, 0),
            )

            def on_changed(_value, v=var, label=value_label):
                label.set(str(int(float(v.get()))))

            ui.scale(
                cell,
                variable=var,
                from_=0,
                to=255,
                command=on_changed,
            ).pack(
                fill="x",
                padx=6,
                pady=(0, 2),
            )

    def reset_to_default(self):
        self.face_preset_name.set("neutral")
        self.face_ms1.set(FACE_DEFAULT_HEADER[0])
        self.face_ms2.set(FACE_DEFAULT_HEADER[1])
        self.face_ms3.set(FACE_DEFAULT_HEADER[2])

        for var, value in zip(self.face_params, FACE_DEFAULT_VALUES):
            var.set(value)

    def update_face_default(self):
        self.face_default_values = [int(v.get()) for v in self.face_params]
    
    def on_preset_selected(self, event=None):
        self.load_selected_preset()

    def load_selected_preset(self):
        name = self.selected_preset_name.get().strip()
        preset = self.face_presets.get(name)

        if not preset:
            messagebox.showwarning("確認", f"{name} が見つかりません。")
            return

        ms1, ms2, ms3 = preset["header"]
        values = preset["values"]

        self.face_preset_name.set(name)
        self.face_ms1.set(ms1)
        self.face_ms2.set(ms2)
        self.face_ms3.set(ms3)

        for var, value in zip(self.face_params, values):
            var.set(value)

    def send_axes(self):
        changed_count = 0

        for axis_name, value, default in zip(
            FACE_AXIS_NAMES,
            self.get_current_values(),
            self.face_default_values,
        ):
            if value == default:
                continue

            self.robot_client.send_face_axis(
                axis=axis_name,
                value=value,
                velocity=FACE_EDITOR_VELOCITY,
                priority=FACE_EDITOR_PRIORITY,
                keeptime=FACE_EDITOR_KEEPTIME,
            )
            changed_count += 1

        if changed_count == 0:
            messagebox.showinfo("確認", "変更された軸はありません。")

    def get_current_values(self):
        return [int(v.get()) for v in self.face_params]

    def save_current_preset(self):
        base_name = self.face_preset_name.get().strip() or "noname"
        level = int(self.face_selected_level.get())
        name = f"{base_name}{level}"

        header = (
            int(self.face_ms1.get()),
            int(self.face_ms2.get()),
            int(self.face_ms3.get()),
        )
        values = self.get_current_values()

        try:
            save_face_preset(name, header, values)

            self.face_presets = load_face_presets()
            preset_names = sorted(self.face_presets.keys())
            self.preset_combo["values"] = preset_names
            self.selected_preset_name.set(name)

            if self.on_saved is not None:
                self.on_saved(name, {
                    "name": name,
                    "header": header,
                    "values": values,
                })

            messagebox.showinfo("保存", f"{name} を保存しました。")

        except ValueError as e:
            messagebox.showwarning("確認", str(e))
        except Exception as e:
            messagebox.showerror("保存エラー", str(e))
