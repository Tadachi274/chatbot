import tkinter as tk
from tkinter import messagebox

from ..config import SPEED_SAMPLE_WAV_PATH
from ..audio.speed_audio_player import SpeedAudioPlayer
from .. import ui_style as ui


class SpeedTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        speed_data = self.profile_store.get_nested("speech_speed", {})

        self.speed = tk.DoubleVar(
            value=float(speed_data.get("value", 1.0))
        )

        self.speed_label = tk.StringVar(
            value=self.format_speed(self.speed.get())
        )

        self.player = SpeedAudioPlayer()

        self.build_ui()

    def build_ui(self):
        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )

        ui.label(
            page,
            text="話すスピードを選ぶ",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            page,
            text="事前に用意した音声を、0.5倍から2.0倍の範囲で再生して確認します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(
            anchor="w",
            pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]),
        )

        self.build_speed_area(page)
        self.build_bottom_area(page)

    def build_speed_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        ui.label(
            section,
            text="スピード",
            font="section_title",
            bg="panel",
        ).pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["section_y"]),
        )

        value_row = ui.frame(card, bg="card")
        value_row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]),
        )

        ui.label(
            value_row,
            text="現在の速度",
            font="body",
            bg="card",
            fg="sub_text",
        ).pack(side="left")

        ui.variable_label(
            value_row,
            textvariable=self.speed_label,
            font="section_title",
            bg="card",
            fg="text",
        ).pack(side="right")

        scale_row = ui.frame(card, bg="card")
        scale_row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["card_y"]),
        )

        ui.label(
            scale_row,
            text="0.5倍",
            font="small",
            bg="card",
            fg="muted",
        ).pack(side="left")

        slider_area = ui.frame(scale_row, bg="card")
        slider_area.pack(side="left", fill="x", expand=True)

        ui.scale(
            slider_area,
            variable=self.speed,
            from_=0.5,
            to=2.0,
            command=self.on_speed_changed,
        ).pack(fill="x")

        ui.label(
            scale_row,
            text="2.0倍",
            font="small",
            bg="card",
            fg="muted",
        ).pack(side="left")

    def build_bottom_area(self, parent):
        bottom = ui.frame(parent, bg="main_card")
        bottom.pack(
            fill="x",
            pady=(ui.SPACING["small_gap"], 0),
        )

        sample_row = ui.frame(bottom, bg="main_card")
        sample_row.pack(fill="x")

        info_area = ui.frame(sample_row, bg="main_card")
        info_area.pack(side="left", fill="x", expand=True)

        ui.label(
            info_area,
            text="再生する音声",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w")

        ui.label(
            info_area,
            text=str(SPEED_SAMPLE_WAV_PATH),
            font="small",
            bg="main_card",
            fg="muted",
        ).pack(anchor="w")

        play_button_area = ui.frame(sample_row, bg="main_card")
        play_button_area.pack(
            side="right",
            anchor="s",
            padx=(ui.SPACING["gap"], 0),
        )

        ui.sub_button(
            play_button_area,
            text="再生",
            command=self.play_sample,
        ).pack(anchor="s")

        save_row = ui.frame(bottom, bg="main_card")
        save_row.pack(
            fill="x",
            pady=(ui.SPACING["small_gap"], 0),
        )

        ui.action_button(
            save_row,
            text="保存して次へ",
            command=self.save_and_next,
        ).pack(side="right")

    def format_speed(self, value):
        return f"{float(value):.2f} 倍"

    def on_speed_changed(self, value):
        self.speed_label.set(self.format_speed(value))
        self.save_selection_only(update_status=False)

    def get_current_data(self):
        value = round(float(self.speed.get()), 2)

        return {
            "value": value,
            "label": self.format_speed(value),
            "prompt": (
                f"話すスピードは通常の {value:.2f} 倍程度にしてください。"
                "ただし不自然に聞こえない範囲で調整してください。"
            ),
        }

    def save_selection_only(self, update_status=True):
        self.profile_store.set(
            "speech_speed",
            self.get_current_data(),
            auto_save=True,
        )

        if update_status:
            self.status_var.set("話すスピード設定を保存しました")

    def save_and_next(self):
        self.save_selection_only()

        if self.on_saved is not None:
            self.on_saved()

    def play_sample(self):
        try:
            self.save_selection_only(update_status=False)
            
            self.player.play(
                src_path=SPEED_SAMPLE_WAV_PATH,
                speed=float(self.speed.get()),
            )
            self.status_var.set(f"{self.format_speed(self.speed.get())}で再生しました")

        except Exception as e:
            messagebox.showerror("再生エラー", str(e))
            self.status_var.set(f"再生エラー: {e}")

    def destroy(self):
        try:
            self.player.cleanup()
        except Exception:
            pass

        super().destroy()