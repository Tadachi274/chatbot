import tkinter as tk
from tkinter import messagebox

from ..config import POLITENESS_OPTIONS
from .. import ui_style as ui
from .style_sample_audio import StyleSampleAudioMixin


class PolitenessTab(StyleSampleAudioMixin, tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        politeness = self.profile_store.get_nested("politeness", {})

        self.selected_politeness = tk.StringVar(
            value=politeness.get("id", "formal")
        )

        self.other_example1 = tk.StringVar(
            value=politeness.get("other_example1", "")
        )

        self.other_example2 = tk.StringVar(
            value=politeness.get("other_example2", "")
        )

        self.politeness_test_text = tk.StringVar(
            value=self.profile_store.get(
                "politeness_test_text",
                "今日はどのようなご用件でしょうか。",
            )
        )

        self.build_ui()

    # =========================
    # UI
    # =========================

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
            text="敬語の強さを選ぶ",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            page,
            text="各選択肢の例文を見比べながら、ロボットに求める話し方を選んでください。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        self.build_choices(page)
        self.build_bottom_area(page)

    def build_choices(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        ui.label(
            section,
            text="選択肢",
            font="section_title",
            bg="panel",
        ).pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        choice_area = ui.frame(section, bg="panel")
        choice_area.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["section_y"]),
        )

        top_row = ui.frame(choice_area, bg="panel")
        top_row.pack(fill="x")

        bottom_row = ui.frame(choice_area, bg="panel")
        bottom_row.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        top_options = POLITENESS_OPTIONS[:3]
        bottom_options = POLITENESS_OPTIONS[3:]
        self.prewarm_style_sample_wavs(POLITENESS_OPTIONS)

        for opt in top_options:
            card = ui.bordered_frame(top_row, bg="card", border="border")
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=ui.SPACING["small_gap"],
                pady=ui.SPACING["small_gap"],
            )

            self.build_choice_card(card, opt)

        spacer_left = ui.frame(bottom_row, bg="panel")
        spacer_left.pack(side="left", fill="both", expand=True)

        for opt in bottom_options:
            card = ui.bordered_frame(bottom_row, bg="card", border="border")
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=ui.SPACING["small_gap"],
                pady=ui.SPACING["small_gap"],
            )

            self.build_choice_card(card, opt)

        spacer_right = ui.frame(bottom_row, bg="panel")
        spacer_right.pack(side="left", fill="both", expand=True)

    def build_choice_card(self, parent, opt):
        ui.radio(
            parent,
            text=opt["label"],
            variable=self.selected_politeness,
            value=opt["id"],
            command=self.on_changed,
            bg="card",
        ).pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]),
        )

        if opt["id"] == "other":
            self.build_other_inputs(parent)
        else:
            ui.label(
                parent,
                text=f"例1：{opt['example1']}",
                font="body",
                bg="card",
                fg="text",
                wraplength=ui.LAYOUT["card_text_wrap"],
                justify="left",
                anchor="w",
            ).pack(
                fill="x",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["small_gap"]),
            )
            ui.sub_button(
                parent,
                text="例2を再生",
                command=lambda item=opt: self.play_option_example(item, 2),
            ).pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["small_gap"]),
            )

            ui.label(
                parent,
                text=f"例2：{opt['example2']}",
                font="body",
                bg="card",
                fg="text",
                wraplength=ui.LAYOUT["card_text_wrap"],
                justify="left",
                anchor="w",
            ).pack(
                fill="x",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["card_y"]),
            )

    def build_other_inputs(self, parent):
        row1 = ui.frame(parent, bg="card")
        row1.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

        ui.label(
            row1,
            text="例1",
            font="small",
            bg="card",
            fg="sub_text",
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))

        ui.entry(
            row1,
            textvariable=self.other_example1,
            font="input",
        ).pack(side="left", fill="x", expand=True, ipady=3)

        row2 = ui.frame(parent, bg="card")
        row2.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

        ui.label(
            row2,
            text="例2",
            font="small",
            bg="card",
            fg="sub_text",
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))

        ui.entry(
            row2,
            textvariable=self.other_example2,
            font="input",
        ).pack(side="left", fill="x", expand=True, ipady=3)

        ui.label(
            parent,
            text="自分で入力した例に近い話し方にします。",
            font="small",
            bg="card",
            fg="muted",
            justify="left",
            anchor="w",
        ).pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

        self.other_example1.trace_add("write", lambda *_: self.save_selection_only())
        self.other_example2.trace_add("write", lambda *_: self.save_selection_only())

    def build_bottom_area(self, parent):
        bottom = ui.frame(parent, bg="main_card")
        bottom.pack(fill="x", pady=(ui.SPACING["section_y"], 0))

        sample_row = ui.frame(bottom, bg="main_card")
        sample_row.pack(fill="x")

        input_area = ui.frame(sample_row, bg="main_card")
        input_area.pack(side="left", fill="x", expand=True)

        ui.label(
            input_area,
            text="読み上げる文",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w")

        ui.entry(
            input_area,
            textvariable=self.politeness_test_text,
            font="input",
        ).pack(fill="x", ipady=8)

        button_area = ui.frame(sample_row, bg="main_card")
        button_area.pack(side="right", anchor="se", padx=(ui.SPACING["gap"], 0))

        ui.sub_button(
            button_area,
            text="再生",
            command=self.speak_sample,
        ).pack(anchor="s")

        save_row = ui.frame(bottom, bg="main_card")
        save_row.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.action_button(
            save_row,
            text="保存して次へ",
            command=self.save_and_next,
        ).pack(side="right")

    # =========================
    # データ処理
    # =========================

    def find_option(self, option_id):
        for opt in POLITENESS_OPTIONS:
            if opt["id"] == option_id:
                return opt

        return POLITENESS_OPTIONS[1]

    def get_current_data(self):
        opt = self.find_option(self.selected_politeness.get())

        data = {
            "id": opt["id"],
            "label": opt["label"],
            "example1": opt["example1"],
            "example2": opt["example2"],
            "prompt": opt["prompt"],
        }

        if opt["id"] == "other":
            ex1 = self.other_example1.get().strip()
            ex2 = self.other_example2.get().strip()

            data["other_example1"] = ex1
            data["other_example2"] = ex2
            data["example1"] = ex1
            data["example2"] = ex2
            data["prompt"] = (
                "以下の例文の話し方に近づけてください。"
                f"例1：「{ex1}」"
                f"例2：「{ex2}」"
            )

        return data

    def save_selection_only(self):
        self.profile_store.set(
            "politeness",
            self.get_current_data(),
            auto_save=False,
        )

        self.profile_store.set(
            "politeness_test_text",
            self.politeness_test_text.get(),
            auto_save=True,
        )

        self.status_var.set("敬語設定を保存しました")

    def save_and_next(self):
        self.save_selection_only()

        if self.on_saved is not None:
            self.on_saved()

    def on_changed(self):
        self.save_selection_only()
        self.play_option_example(self.find_option(self.selected_politeness.get()), 1)

    def play_option_example(self, opt, example_no=1):
        text = opt.get(f"example{example_no}", "")
        self.play_style_sample_text(text, label=f"敬語 {opt.get('label', '')} 例{example_no}")

    # =========================
    # TTS
    # =========================

    def speak_sample(self):
        text = self.politeness_test_text.get().strip()

        if not text:
            messagebox.showwarning("確認", "読み上げる文を入力してください。")
            return

        self.save_selection_only()

        self.tts_client.speak_current_speaker(
            text=text,
        )

        self.status_var.set(f"敬語サンプルを再生しました: {text}")
