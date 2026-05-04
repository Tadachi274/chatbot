# chatbot/robot_style_editor/tabs/response_delay_tab.py

import tkinter as tk
import wave

from ..config import (
    RESPONSE_DELAY_TOTAL_DEFAULT,
    RESPONSE_DELAY_TOTAL_MIN,
    RESPONSE_DELAY_TOTAL_MAX,
    RESPONSE_DELAY_SAMPLE_WAV,
    MIC_SILENCE_HOLD_SEC_DEFAULT,
)
from ..panels.mic_activity_panel import MicActivityPanel
from ..audio.response_delay_player import ResponseDelayPlayer
from .. import ui_style as ui



class ResponseDelayTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        delay_data = self.profile_store.get_nested("response_delay", {})

        self.delay_sec = tk.DoubleVar(
            value=float(delay_data.get("total_value", RESPONSE_DELAY_TOTAL_DEFAULT))
        )


        self.delay_label = tk.StringVar(value=self.format_delay(self.delay_sec.get()))
        
        self.response_player = ResponseDelayPlayer()

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
            text="返答の間を選ぶ",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            page,
            text="お客さんが話し終わってから、店員が返答を始めるまでの総時間を調整します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(
            anchor="w",
            pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]),
        )

        self.build_delay_area(page)
        self.build_mic_area(page)
        self.build_bottom_area(page)

    def build_delay_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        ui.label(
            section,
            text="返答までの総時間",
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
            pady=(0, ui.SPACING["small_gap"]),
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
            textvariable=self.delay_label,
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
            text=f"{RESPONSE_DELAY_TOTAL_MIN:.1f}秒",
            font="small",
            bg="card",
            fg="muted",
        ).pack(side="left")

        slider_area = ui.frame(scale_row, bg="card")
        slider_area.pack(side="left", fill="x", expand=True)

        ui.scale(
            slider_area,
            variable=self.delay_sec,
            from_=RESPONSE_DELAY_TOTAL_MIN,
            to=RESPONSE_DELAY_TOTAL_MAX,
            command=self.on_delay_changed,
        ).pack(fill="x")

        ui.label(
            scale_row,
            text=f"{RESPONSE_DELAY_TOTAL_MAX:.1f}秒",
            font="small",
            bg="card",
            fg="muted",
        ).pack(side="left")

    def build_mic_area(self, parent):
        self.mic_panel = MicActivityPanel(
            parent,
            title="マイク入力",
            description="「チェックインをお願いします」と話すと、話し終わりから設定秒数後に返答音声を再生します。",
            on_speech_end=self.on_user_speech_end,
            status_var=self.status_var,
        )
        self.mic_panel.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

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
            text="確認方法",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w")

        ui.label(
            info_area,
            text="認識開始後に「チェックインをお願いします」と話すと、話し終わりから設定秒数後に返答音声を再生します。",
            font="small",
            bg="main_card",
            fg="muted",
            justify="left",
            anchor="w",
        ).pack(anchor="w")

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

    def format_delay(self, value):
        return f"{float(value):.2f} 秒"

    def on_delay_changed(self, value):
        self.delay_label.set(self.format_delay(value))
        self.save_selection_only(update_status=False)

    def get_wait_after_detection_sec(self):
        total_delay = float(self.delay_sec.get())
        wait_after_detection = total_delay - MIC_SILENCE_HOLD_SEC_DEFAULT
        return max(0.0, wait_after_detection)
    
    def get_wav_duration_sec(self, wav_path):
        with wave.open(str(wav_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()

        return frames / float(rate)

    def on_user_speech_end(self, _t):
        self.mic_panel.set_result("認識完了")
        self.mic_panel.set_state("返答待ち")

        wait_sec = self.get_wait_after_detection_sec()
        wav_duration = self.get_wav_duration_sec(RESPONSE_DELAY_SAMPLE_WAV)
        buffer_sec = 0.15

        # 返答開始までの待ち時間 + 返答WAV再生中はマイク判定を無視する
        self.mic_panel.pause_for(
            wait_sec + wav_duration + buffer_sec,
            label="返答再生待ち/再生中",
        )

        self.response_player.schedule_response(
            wav_path=RESPONSE_DELAY_SAMPLE_WAV,
            delay_sec=wait_sec,
        )
   
    def get_current_data(self):
        total_value = round(float(self.delay_sec.get()), 2)
        wait_after_detection = round(self.get_wait_after_detection_sec(), 2)

        return {
            "total_value": total_value,
            "label": self.format_delay(total_value),
            "wait_after_detection": wait_after_detection,
            "silence_hold_sec": MIC_SILENCE_HOLD_SEC_DEFAULT,
            "description": (
                "相手の発話終了からロボットが返答を開始するまでの総時間。"
                "内部的には終了判定用の無音時間と、終了判定後の追加待機時間に分かれる。"
            ),
            "prompt": (
                f"相手の発話が終わってから、約{total_value:.2f}秒後に返答を開始してください。"
            ),
        }

    def save_selection_only(self, update_status=True):
        self.profile_store.set(
            "response_delay",
            self.get_current_data(),
            auto_save=True,
        )

        if update_status:
            self.status_var.set("返答の間を保存しました")

    def save_and_next(self):
        self.save_selection_only()

        if self.on_saved is not None:
            self.on_saved()

    def destroy(self):
        try:
            self.mic_panel.stop()
        except Exception:
            pass

        try:
            self.response_player.cleanup()
        except Exception:
            pass

        super().destroy()