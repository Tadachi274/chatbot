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
from ..config_face import UNDERSTANDING_NOD_OPTIONS, UNDERSTANDING_NOD_PRIORITY
from ..panels.mic_activity_panel import MicActivityPanel
from ..audio.response_delay_player import ResponseDelayPlayer
from .. import ui_style as ui


THINKING_RESPONSE_DELAY_DEFAULT = 1.0


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

        self.thinking_delay_sec = tk.DoubleVar(
            value=float(delay_data.get("thinking_total_value", THINKING_RESPONSE_DELAY_DEFAULT))
        )

        self.delay_label = tk.StringVar(value=self.format_delay(self.delay_sec.get()))
        self.thinking_delay_label = tk.StringVar(value=self.format_delay(self.thinking_delay_sec.get()))

        understanding_data = self.profile_store.get_nested("understanding_pose", {}) or {}
        nod_data = understanding_data.get("nod", {})
        self.selected_nod = tk.StringVar(value=nod_data.get("id", "large_once"))
        
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
            text="お客さんが話し終わってから、理解のうなづきや返答に移るまでの間を調整します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(
            anchor="w",
            pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]),
        )

        content = ui.scrollable_frame(
            page,
            pady=(0, ui.SPACING["small_gap"]),
        )

        self.build_delay_area(content)
        self.build_understanding_nod_area(content)
        self.build_mic_area(content)
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

        self.build_delay_card(
            section,
            title="通常時",
            description="質問や説明などで追加の考える姿を入れない時の返答間です。",
            variable=self.delay_sec,
            label_var=self.delay_label,
            command=self.on_delay_changed,
        )

        self.build_delay_card(
            section,
            title="考えている時",
            description="おすすめ相談など、返答前に考えている姿を見せる時の返答間です。",
            variable=self.thinking_delay_sec,
            label_var=self.thinking_delay_label,
            command=self.on_thinking_delay_changed,
            bottom_pady=ui.SPACING["section_y"],
        )

    def build_delay_card(self, parent, title, description, variable, label_var, command, bottom_pady=None):
        card = ui.bordered_frame(parent, bg="card", border="border")
        card.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["small_gap"] if bottom_pady is None else bottom_pady),
        )

        value_row = ui.frame(card, bg="card")
        value_row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]),
        )

        ui.label(
            value_row,
            text=title,
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

        ui.label(
            card,
            text=description,
            font="small",
            bg="card",
            fg="muted",
            justify="left",
            anchor="w",
            wraplength=900,
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["small_gap"]))

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
            variable=variable,
            from_=RESPONSE_DELAY_TOTAL_MIN,
            to=RESPONSE_DELAY_TOTAL_MAX,
            command=command,
        ).pack(fill="x")

        ui.label(
            scale_row,
            text=f"{RESPONSE_DELAY_TOTAL_MAX:.1f}秒",
            font="small",
            bg="card",
            fg="muted",
        ).pack(side="left")

    def build_understanding_nod_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(
            section,
            text="理解のうなづき",
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

        for opt in UNDERSTANDING_NOD_OPTIONS:
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
                variable=self.selected_nod,
                value=opt["id"],
                command=lambda item=opt: self.on_nod_selected(item),
                bg="card",
            ).pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
            )

            ui.label(
                card,
                text=f"/nod {opt['amplitude']} {opt['duration']} × {opt['count']}",
                font="small",
                bg="card",
                fg="muted",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))

    def build_mic_area(self, parent):
        self.mic_panel = MicActivityPanel(
            parent,
            title="実環境入力",
            description=(
                "実環境の act 値が 1 以上の間を客の発話中として扱います。"
                "「チェックインをお願いします」と話すと、話し終わりから設定秒数後に返答音声を再生します。"
            ),
            on_speech_end=self.on_user_speech_end,
            status_var=self.status_var,
            activity_mode="robot_act",
            act_threshold=1,
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

    def on_thinking_delay_changed(self, value):
        self.thinking_delay_label.set(self.format_delay(value))
        self.save_selection_only(update_status=False)

    def on_nod_selected(self, opt):
        self.save_selection_only(update_status=False)
        self.status_var.set(f"理解のうなづきを保存しました: {opt['label']}")

    def get_wait_after_detection_sec(self):
        return self.get_wait_after_detection_from_total(self.delay_sec.get())

    def get_thinking_wait_after_detection_sec(self):
        return self.get_wait_after_detection_from_total(self.thinking_delay_sec.get())

    def get_wait_after_detection_from_total(self, total_value):
        total_delay = float(total_value)
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
        thinking_total_value = round(float(self.thinking_delay_sec.get()), 2)
        wait_after_detection = round(self.get_wait_after_detection_sec(), 2)
        thinking_wait_after_detection = round(self.get_thinking_wait_after_detection_sec(), 2)

        return {
            "total_value": total_value,
            "label": self.format_delay(total_value),
            "wait_after_detection": wait_after_detection,
            "thinking_total_value": thinking_total_value,
            "thinking_label": self.format_delay(thinking_total_value),
            "thinking_wait_after_detection": thinking_wait_after_detection,
            "silence_hold_sec": MIC_SILENCE_HOLD_SEC_DEFAULT,
            "description": (
                "相手の発話終了からロボットが返答を開始するまでの総時間。"
                "通常時と考えている時で別々に設定する。"
            ),
            "prompt": (
                f"通常時は相手の発話が終わってから約{total_value:.2f}秒後、"
                f"考えている時は約{thinking_total_value:.2f}秒後に返答を開始してください。"
            ),
        }

    def find_selected_nod_option(self):
        selected = self.selected_nod.get()
        for opt in UNDERSTANDING_NOD_OPTIONS:
            if opt["id"] == selected:
                return opt
        return UNDERSTANDING_NOD_OPTIONS[0]

    def save_understanding_nod(self):
        existing = self.profile_store.get_nested("understanding_pose", {}) or {}
        nod = self.find_selected_nod_option()
        updated = {
            **existing,
            "nod": {
                "id": nod["id"],
                "label": nod["label"],
                "amplitude": int(nod["amplitude"]),
                "duration": int(nod["duration"]),
                "count": int(nod["count"]),
                "priority": UNDERSTANDING_NOD_PRIORITY,
            },
            "response_delay_source": "response_delay.wait_after_detection / response_delay.thinking_wait_after_detection",
        }
        self.profile_store.set("understanding_pose", updated, auto_save=True)

    def save_selection_only(self, update_status=True):
        self.profile_store.set(
            "response_delay",
            self.get_current_data(),
            auto_save=True,
        )
        self.save_understanding_nod()

        if update_status:
            self.status_var.set("返答の間と理解のうなづきを保存しました")

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
