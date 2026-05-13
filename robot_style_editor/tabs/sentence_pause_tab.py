import tkinter as tk
from tkinter import messagebox
import random
import threading
    
from .. import ui_style as ui
from ..config import (
        SENTENCE_PAUSE_DEFAULT, 
        SENTENCE_PAUSE_MIN,
        SENTENCE_PAUSE_MAX,
    SENTENCE_PAUSE_SAMPLE_WAV_1,
    SENTENCE_PAUSE_SAMPLE_WAV_2,
    SENTENCE_PAUSE_TRIMMED_SAMPLE_WAV_1,
    SENTENCE_PAUSE_TRIMMED_SAMPLE_WAV_2,
)

from ..config_face import (
    SENTENCE_PAUSE_GAZE_OPTIONS,
    SENTENCE_PAUSE_GAZE_PRIORITY,
    SENTENCE_PAUSE_GAZE_KEEPTIME,
)
from ..panels.gaze_direction_panel import GazeDirectionPanel, find_gaze_option
from ..clients.robot_command_client import RobotCommandClient
from ..audio.wav_silence import trim_silence_to_wav

class SentencePauseTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        pause_data = self.profile_store.get_nested("sentence_pause", {})

        self.pause_sec = tk.DoubleVar(
            value=float(pause_data.get("value", SENTENCE_PAUSE_DEFAULT))
        )

        self.pause_label = tk.StringVar(
            value=self.format_pause(self.pause_sec.get())
        )

        gaze = pause_data.get("gaze", {})

        self.selected_gaze = tk.StringVar(
            value=gaze.get("id", "horizontal")
        )

        self.robot_client = RobotCommandClient()
        self.trimmed_sample_wav_1 = None
        self.trimmed_sample_wav_2 = None

        self.build_ui()
        self.prewarm_trimmed_sentence_pause_samples()

    def clear_views(self):
        for child in self.winfo_children():
            child.destroy()


    def build_main_view(self):
        self.clear_views()
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
            text="文と文の間を選ぶ",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            page,
            text="ロボットがターンを保持して話し続けるときの、一文と一文の間の時間を調整します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(
            anchor="w",
            pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]),
        )

        self.build_pause_area(page)

        self.build_gaze_area(page)
        self.build_bottom_area(page)

    def build_pause_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        ui.label(
            section,
            text="間の長さ",
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
            text="現在の間",
            font="body",
            bg="card",
            fg="sub_text",
        ).pack(side="left")

        ui.variable_label(
            value_row,
            textvariable=self.pause_label,
            font="section_title",
            bg="card",
            fg="text",
        ).pack(side="right")

        example_card = ui.frame(card, bg="card")
        example_card.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["small_gap"]),
        )

        ui.label(
            example_card,
            text="例：誠にありがとうございます。 → 確認が取れました。",
            font="body",
            bg="card",
            fg="text",
            justify="left",
            anchor="w",
        ).pack(anchor="w")

        scale_row = ui.frame(card, bg="card")
        scale_row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["card_y"]),
        )

        ui.label(
            scale_row,
            text=f"{SENTENCE_PAUSE_MIN:.1f}秒",
            font="small",
            bg="card",
            fg="muted",
        ).pack(side="left")

        slider_area = ui.frame(scale_row, bg="card")
        slider_area.pack(side="left", fill="x", expand=True)

        ui.scale(
            slider_area,
            variable=self.pause_sec,
            from_=SENTENCE_PAUSE_MIN,
            to=SENTENCE_PAUSE_MAX,
            command=self.on_pause_changed,
        ).pack(fill="x")

        ui.label(
            scale_row,
            text=f"{SENTENCE_PAUSE_MAX:.1f}秒",
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
            text="確認用の例",
            font="body",
            bg="main_card",
            fg="sub_text",
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

    def format_pause(self, value):
        return f"{float(value):.2f} 秒"

    def on_pause_changed(self, value):
        self.pause_label.set(self.format_pause(value))
        self.save_selection_only(update_status=False)

    def build_gaze_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(
            section,
            text="文間の視線移動",
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

        for opt in SENTENCE_PAUSE_GAZE_OPTIONS:
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

        current_gaze = self.find_sentence_pause_gaze_option()
        current_in_basic = any(
            opt["id"] == current_gaze["id"]
            for opt in SENTENCE_PAUSE_GAZE_OPTIONS
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

    def build_gaze_editor_view(self):
        self.clear_views()

        panel = GazeDirectionPanel(
            self,
            selected_gaze=self.selected_gaze,
            on_select=self.on_gaze_selected,
            on_back=self.build_main_view,
            title="文間の視線方向を選ぶ",
            description="ロボットが文と文の間で視線を外す方向を9方向から選びます。",
        )
        panel.pack(fill="both", expand=True)

    def on_gaze_selected(self, opt):
        self.selected_gaze.set(opt["id"])

        try:
            lookaway = opt["lookaway"]

            if lookaway == "horizontal_random":
                preview_lookaway = preview_lookaway = random.choice(["l", "r"])
            else:
                preview_lookaway = lookaway

            self.robot_client.send_lookaway(
                direction=preview_lookaway,
                priority=SENTENCE_PAUSE_GAZE_PRIORITY,
                keeptime=SENTENCE_PAUSE_GAZE_KEEPTIME,
            )

            self.save_selection_only(update_status=False)
            self.status_var.set(f"文間の視線を送信しました: {opt['label']}")

        except Exception as e:
            self.status_var.set(f"視線送信エラー: {e}")

    def find_sentence_pause_gaze_option(self):
        selected_id = self.selected_gaze.get()

        for opt in SENTENCE_PAUSE_GAZE_OPTIONS:
            if opt["id"] == selected_id:
                return opt

        opt = find_gaze_option(selected_id)
        if opt is not None:
            return opt

        current = self.profile_store.get_nested("sentence_pause", {}).get("gaze")
        if current:
            return current

        return SENTENCE_PAUSE_GAZE_OPTIONS[0]

    def get_current_data(self):
        value = round(float(self.pause_sec.get()), 2)
        gaze = self.find_sentence_pause_gaze_option()

        return {
            "value": value,
            "label": self.format_pause(value),
            "gaze": {
                "id": gaze["id"],
                "label": gaze["label"],
                "lookaway": gaze["lookaway"],
                "priority": SENTENCE_PAUSE_GAZE_PRIORITY,
                "keeptime": SENTENCE_PAUSE_GAZE_KEEPTIME,
            },
            "description": "ターンを保持している間の一文と一文の間の時間",
            "example": "こんにちは。 / 今日はどのようなご用件でしょうか？",
            "prompt": (
                f"一文と一文の間は約{value:.2f}秒空けてください。"
                "これは発話中にターンを保持している状態での文間ポーズです。"
            ),
        }

    def save_selection_only(self, update_status=True):
        self.profile_store.set(
            "sentence_pause",
            self.get_current_data(),
            auto_save=True,
        )

        if update_status:
            self.status_var.set("文間の設定を保存しました")

    def save_and_next(self):
        self.save_selection_only()

        if self.on_saved is not None:
            self.on_saved()

    def play_sample(self):
        self.save_selection_only(update_status=False)

        try:
            wav1, wav2 = self.get_trimmed_sentence_pause_samples()
            self.tts_client.play_wav_pair_with_pause(
                wav1=wav1,
                wav2=wav2,
                pause_sec=float(self.pause_sec.get()),
                on_pause_start=self.send_sentence_pause_gaze,
                trim=False,
            )

            self.status_var.set(
                f"文間 {self.format_pause(self.pause_sec.get())} で再生しています"
            )

        except Exception as e:
            messagebox.showerror("再生エラー", str(e))
            self.status_var.set(f"再生エラー: {e}")

    def get_trimmed_sentence_pause_samples(self):
        if self.trimmed_sample_wav_1 is None or not SENTENCE_PAUSE_TRIMMED_SAMPLE_WAV_1.exists():
            self.trimmed_sample_wav_1 = trim_silence_to_wav(
                SENTENCE_PAUSE_SAMPLE_WAV_1,
                SENTENCE_PAUSE_TRIMMED_SAMPLE_WAV_1,
            )
        else:
            self.trimmed_sample_wav_1 = SENTENCE_PAUSE_TRIMMED_SAMPLE_WAV_1

        if self.trimmed_sample_wav_2 is None or not SENTENCE_PAUSE_TRIMMED_SAMPLE_WAV_2.exists():
            self.trimmed_sample_wav_2 = trim_silence_to_wav(
                SENTENCE_PAUSE_SAMPLE_WAV_2,
                SENTENCE_PAUSE_TRIMMED_SAMPLE_WAV_2,
            )
        else:
            self.trimmed_sample_wav_2 = SENTENCE_PAUSE_TRIMMED_SAMPLE_WAV_2

        return self.trimmed_sample_wav_1, self.trimmed_sample_wav_2

    def prewarm_trimmed_sentence_pause_samples(self):
        def worker():
            try:
                self.get_trimmed_sentence_pause_samples()
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def send_sentence_pause_gaze(self):
        gaze = self.find_sentence_pause_gaze_option()
        lookaway = gaze["lookaway"]

        if lookaway == "horizontal_random":
            preview_lookaway = random.choice(
                ["l", "r"]
            )
        else:
            preview_lookaway = lookaway

        self.robot_client.send_lookaway(
            direction=preview_lookaway,
            priority=SENTENCE_PAUSE_GAZE_PRIORITY,
            keeptime=SENTENCE_PAUSE_GAZE_KEEPTIME,
        )

        self.status_var.set(f"文間の視線を送信しました: {gaze['label']}")

    def destroy(self):
        try:
            self.robot_client.close()
        except Exception:
            pass

        super().destroy()
