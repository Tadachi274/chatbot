import tkinter as tk
from tkinter import ttk, messagebox

from ..config_face import (
    THINKING_FACE_OPTIONS,
    THINKING_GAZE_OPTIONS,
    THINKING_FACE_PRIORITY,
    THINKING_FACE_KEEPTIME,
    THINKING_GAZE_PRIORITY,
    THINKING_GAZE_KEEPTIME,
)
from ..clients.robot_command_client import RobotCommandClient
from ..panels.face_editor_panel import FaceEditorPanel
from ..face_preset_store import load_face_presets
from .. import ui_style as ui
from ..panels.gaze_direction_panel import GazeDirectionPanel, GAZE_9_OPTIONS, find_gaze_option


class ThinkingPoseTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        thinking = self.profile_store.get_nested("thinking_pose", {})
        thinking_face = thinking.get("face", {})

        self.face_presets = load_face_presets()

        initial_face_id = thinking_face.get("id", "neutral")
        initial_custom_name = ""

        if thinking_face.get("custom") or initial_face_id == "custom":
            initial_custom_name = thinking_face.get("type") or thinking_face.get("label", "")
            if initial_custom_name:
                initial_face_id = f"custom:{initial_custom_name}"

        if not initial_custom_name and self.face_presets:
            initial_custom_name = sorted(self.face_presets.keys())[0]

        self.selected_face = tk.StringVar(value=initial_face_id)
        self.custom_face_name = tk.StringVar(value=initial_custom_name)

        self.selected_gaze = tk.StringVar(
            value=thinking.get("gaze", {}).get("id", "down")
        )

        self.robot_client = RobotCommandClient()

        self.main_view = None
        self.editor_view = None
        self.custom_face_combo = None

        self.build_main_view()

    # =========================
    # 画面切り替え
    # =========================

    def clear_views(self):
        for child in self.winfo_children():
            child.destroy()

    def build_main_view(self):
        self.refresh_face_presets()
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
            text="考えている姿を選ぶ",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            page,
            text="ロボットが返答を考えている間の表情と視線方向を調整します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(
            anchor="w",
            pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]),
        )

        self.build_face_area(page)
        self.build_gaze_area(page)
        self.build_bottom_area(page)

    def build_editor_view(self):
        self.clear_views()

        editor = FaceEditorPanel(
            self,
            robot_client=self.robot_client,
            on_back=self.build_main_view,
            on_saved=self.on_custom_face_saved,
        )
        editor.pack(fill="both", expand=True)

    def build_gaze_editor_view(self):
        self.clear_views()

        panel = GazeDirectionPanel(
            self,
            selected_gaze=self.selected_gaze,
            on_select=self.on_gaze_selected,
            on_back=self.build_main_view,
            title="考えている時の視線を選ぶ",
            description="ロボットが返答を考えている間の視線方向を9方向から選びます。",
        )
        panel.pack(fill="both", expand=True)

    # =========================
    # 表情
    # =========================

    def build_face_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        ui.label(
            section,
            text="表情",
            font="section_title",
            bg="panel",
        ).pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        row = ui.frame(section, bg="panel")
        row.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["section_y"]),
        )

        for opt in THINKING_FACE_OPTIONS:
            card = ui.bordered_frame(row, bg="card", border="border")
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=ui.SPACING["small_gap"],
                pady=ui.SPACING["small_gap"],
            )

            ui.radio(
                card,
                text=opt["label"],
                variable=self.selected_face,
                value=opt["id"],
                command=lambda item=opt: self.on_face_selected(item),
                bg="card",
            ).pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
            )

            ui.label(
                card,
                text=f"/emotion {opt['type']} {opt['level']}",
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

        other_card = ui.bordered_frame(row, bg="card", border="border")
        other_card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=ui.SPACING["small_gap"],
            pady=ui.SPACING["small_gap"],
        )

        ui.label(
            other_card,
            text="その他",
            font="body_bold",
            bg="card",
            fg="text",
        ).pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )

        preset_names = sorted(self.face_presets.keys())

        if preset_names:
            if self.custom_face_name.get() not in preset_names:
                self.custom_face_name.set(preset_names[0])

            combo_row = ui.frame(other_card, bg="card")
            combo_row.pack(
                fill="x",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["compact_y"]),
            )

            self.custom_face_combo = ttk.Combobox(
                combo_row,
                values=preset_names,
                textvariable=self.custom_face_name,
                width=18,
                state="readonly",
            )
            self.custom_face_combo.pack(side="left", fill="x", expand=True)
            self.custom_face_combo.bind(
                "<<ComboboxSelected>>",
                lambda _event=None: self.on_custom_face_selected_from_other(),
            )

            ui.sub_button(
                other_card,
                text="この表情を使う",
                command=self.on_custom_face_selected_from_other,
            ).pack(
                anchor="e",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["compact_y"]),
            )
        else:
            ui.label(
                other_card,
                text="保存済みの表情はまだありません。",
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

        ui.sub_button(
            other_card,
            text="作成する",
            command=self.build_editor_view,
        ).pack(
            anchor="e",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

    def refresh_face_presets(self):
        self.face_presets = load_face_presets()

    def infer_custom_face_level(self, name: str) -> int:
        if name and name[-1].isdigit():
            level = int(name[-1])
            if level in (1, 2, 3):
                return level
        return 1

    def get_custom_face_option(self, name: str):
        name = (name or "").strip()
        if not name:
            return None

        preset = self.face_presets.get(name, {})
        level = int(preset.get("level", self.infer_custom_face_level(name)))

        return {
            "id": f"custom:{name}",
            "label": name,
            "type": name,
            "level": level,
            "custom": True,
        }

    def on_custom_face_selected_from_other(self):
        name = self.custom_face_name.get().strip()
        opt = self.get_custom_face_option(name)

        if opt is None:
            messagebox.showwarning("確認", "使用する表情を選択してください。")
            return

        self.selected_face.set(opt["id"])
        self.on_face_selected(opt)

    def on_face_selected(self, opt):
        try:
            self.robot_client.send_emotion(
                face_type=opt["type"],
                level=opt["level"],
                priority=THINKING_FACE_PRIORITY,
                keeptime=THINKING_FACE_KEEPTIME,
            )

            self.save_selection_only(update_status=False)

            self.status_var.set(f"表情を送信しました: {opt['label']}")

        except Exception as e:
            messagebox.showerror("送信エラー", str(e))
            self.status_var.set(f"送信エラー: {e}")

    def on_custom_face_saved(self, name, data):
        self.refresh_face_presets()

        custom_face = self.get_custom_face_option(name)
        if custom_face is None:
            custom_face = {
                "id": f"custom:{name}",
                "label": name,
                "type": name,
                "level": int(data.get("level", self.infer_custom_face_level(name))),
                "custom": True,
            }

        self.custom_face_name.set(name)
        self.selected_face.set(custom_face["id"])

        self.profile_store.set(
            "thinking_pose",
            {
                **self.get_current_data(),
                "face": custom_face,
            },
            auto_save=True,
        )

        self.status_var.set(f"その他の表情を考えている表情に設定しました: {name}")

    # =========================
    # 視線
    # =========================

    def build_gaze_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(
            section,
            text="視線の方向",
            font="section_title",
            bg="panel",
        ).pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        row = ui.frame(section, bg="panel")
        row.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["section_y"]),
        )

        for opt in THINKING_GAZE_OPTIONS:
            card = ui.bordered_frame(row, bg="card", border="border")
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=ui.SPACING["small_gap"],
                pady=ui.SPACING["small_gap"],
            )

            ui.radio(
                card,
                text=opt["label"],
                variable=self.selected_gaze,
                value=opt["id"],
                command=lambda item=opt: self.on_gaze_selected(item),
                bg="card",
            ).pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
            )

            ui.label(
                card,
                text=f"/lookaway {opt['lookaway']}",
                font="small",
                bg="card",
                fg="muted",
            ).pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["compact_y"]),
            )

        other_card = ui.bordered_frame(row, bg="card", border="border")
        other_card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=ui.SPACING["small_gap"],
            pady=ui.SPACING["small_gap"],
        )

        ui.label(
            other_card,
            text="その他",
            font="body_bold",
            bg="card",
            fg="text",
        ).pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )

        current_gaze = self.find_gaze_option()
        current_in_basic = any(
            opt["id"] == current_gaze["id"]
            for opt in THINKING_GAZE_OPTIONS
        )

        ui.label(
            other_card,
            text=(
                f"現在：{current_gaze['label']}"
                if not current_in_basic
                else "9方向から選べます。"
            ),
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

        ui.sub_button(
            other_card,
            text="9方向から選ぶ",
            command=self.build_gaze_editor_view,
        ).pack(
            anchor="e",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

    def on_gaze_selected(self, opt):
        try:
            self.robot_client.send_lookaway(
                direction=opt["lookaway"],
                priority=THINKING_GAZE_PRIORITY,
                keeptime=THINKING_GAZE_KEEPTIME,
            )

            self.save_selection_only(update_status=False)

            self.status_var.set(f"視線を送信しました: {opt['label']}")

        except Exception as e:
            messagebox.showerror("送信エラー", str(e))
            self.status_var.set(f"送信エラー: {e}")

    # =========================
    # 保存
    # =========================

    def build_bottom_area(self, parent):
        bottom = ui.frame(parent, bg="main_card")
        bottom.pack(
            fill="x",
            pady=(ui.SPACING["small_gap"], 0),
        )

        save_row = ui.frame(bottom, bg="main_card")
        save_row.pack(fill="x")

        ui.action_button(
            save_row,
            text="保存して次へ",
            command=self.save_and_next,
        ).pack(side="right")

    def find_face_option(self):
        selected_id = self.selected_face.get()

        for opt in THINKING_FACE_OPTIONS:
            if opt["id"] == selected_id:
                return opt

        if selected_id.startswith("custom:"):
            name = selected_id.replace("custom:", "", 1)
            custom = self.get_custom_face_option(name)
            if custom is not None:
                return custom

        custom = self.profile_store.get_nested("thinking_pose", {}).get("face")
        if custom:
            return custom

        return THINKING_FACE_OPTIONS[0]

    def find_gaze_option(self):
        selected_id = self.selected_gaze.get()

        opt = find_gaze_option(selected_id)
        if opt is not None:
            return opt

        current = self.profile_store.get_nested("thinking_pose", {}).get("gaze")
        if current:
            return current

        return find_gaze_option("down")

    def get_current_data(self):
        face = self.find_face_option()
        gaze = self.find_gaze_option()

        return {
            "face": {
                "id": face["id"],
                "label": face["label"],
                "type": face["type"],
                "level": int(face["level"]),
                **({"custom": True} if face.get("custom") else {}),
            },
            "gaze": {
                "id": gaze["id"],
                "label": gaze["label"],
                "lookaway": gaze["lookaway"],
                "priority": THINKING_GAZE_PRIORITY,
                "keeptime": THINKING_GAZE_KEEPTIME,
            },
            "description": "ロボットが考えている間の表情と視線方向",
        }

    def save_selection_only(self, update_status=True):
        self.profile_store.set(
            "thinking_pose",
            self.get_current_data(),
            auto_save=True,
        )

        if update_status:
            self.status_var.set("考えている姿を保存しました")

    def save_and_next(self):
        self.save_selection_only()

        if self.on_saved is not None:
            self.on_saved()

    def destroy(self):
        try:
            self.robot_client.close()
        except Exception:
            pass

        super().destroy()