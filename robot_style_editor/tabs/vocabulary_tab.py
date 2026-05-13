import tkinter as tk
from tkinter import messagebox

from ..config import (
    VOCABULARY_BASE_OPTIONS,
    get_person_key_from_speaker,
    normalize_politeness_id,
    normalize_intimacy_id,
    build_vocabulary_examples,
)
from .. import ui_style as ui
from .style_sample_audio import StyleSampleAudioMixin


class VocabularyTab(StyleSampleAudioMixin, tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        vocabulary = self.profile_store.get_nested("vocabulary", {})

        self.selected_vocabulary = tk.StringVar(
            value=vocabulary.get("id", "middle")
        )

        self.other_example1 = tk.StringVar(
            value=vocabulary.get("other_example1", "")
        )

        self.other_example2 = tk.StringVar(
            value=vocabulary.get("other_example2", "")
        )

        self.vocabulary_test_text = tk.StringVar(
            value=self.profile_store.get(
                "vocabulary_test_text",
                "こちらは、甘味が強く、口に入れるとふわっと溶けるようなお菓子です。",
            )
        )

        self.current_person_key = self.get_person_key()
        self.current_politeness_id = self.get_politeness_id()
        self.current_intimacy_id = self.get_intimacy_id()

        self.build_ui()

    # =========================
    # 現在の条件取得
    # =========================

    def get_person_key(self):
        speaker = self.profile_store.get("speaker", "nozomi_emo_22_standard")
        return get_person_key_from_speaker(speaker)

    def get_politeness_id(self):
        politeness = self.profile_store.get_nested("politeness", {})
        return normalize_politeness_id(politeness.get("id", "formal"))

    def get_intimacy_id(self):
        intimacy = self.profile_store.get_nested("intimacy", {})
        return normalize_intimacy_id(intimacy.get("id", "middle"))

    def get_options(self):
        person_key = self.get_person_key()
        politeness_id = self.get_politeness_id()
        intimacy_id = self.get_intimacy_id()

        options = []

        for opt in VOCABULARY_BASE_OPTIONS:
            item = dict(opt)

            if item["id"] == "other":
                item["example1"] = self.other_example1.get().strip()
                item["example2"] = self.other_example2.get().strip()
            else:
                example1, example2 = build_vocabulary_examples(
                    person_key=person_key,
                    politeness_id=politeness_id,
                    intimacy_id=intimacy_id,
                    vocab_option=item,
                )
                item["example1"] = example1
                item["example2"] = example2

            options.append(item)

        return options

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
            text="語彙を選ぶ",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            page,
            text="現在の話者・敬語・親しみに合わせて、語彙の難しさを比較します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(
            anchor="w",
            pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]),
        )

        self.choice_container = ui.frame(page, bg="main_card")
        self.choice_container.pack(fill="x")

        self.build_choices(self.choice_container)
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

        options = self.get_options()
        self.prewarm_style_sample_wavs(options)

        normal_options = [opt for opt in options if opt["id"] != "other"]
        other_options = [opt for opt in options if opt["id"] == "other"]

        # 上段：簡単・中・難しい
        for opt in normal_options:
            card = ui.bordered_frame(top_row, bg="card", border="border")
            card.pack(
                side="left",
                fill="both",
                expand=True,
                padx=ui.SPACING["small_gap"],
                pady=ui.SPACING["small_gap"],
            )

            self.build_choice_card(card, opt)

        # 下段：その他
        for opt in other_options:
            card = ui.bordered_frame(bottom_row, bg="card", border="border")
            card.pack(
                fill="x",
                padx=ui.SPACING["small_gap"],
                pady=ui.SPACING["small_gap"],
            )

            self.build_choice_card(card, opt)

    def build_choice_card(self, parent, opt):
        ui.radio(
            parent,
            text=opt["label"],
            variable=self.selected_vocabulary,
            value=opt["id"],
            command=self.on_changed,
            bg="card",
        ).pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
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
                pady=(0, ui.SPACING["compact_y"]),
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
                pady=(0, ui.SPACING["compact_y"]),
            )
            ui.sub_button(
                parent,
                text="例2を再生",
                command=lambda item=opt: self.play_option_example(item, 2),
            ).pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["compact_y"]),
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
            text="自分で入力した例に近い語彙にします。",
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
        bottom.pack(
            fill="x",
            pady=(ui.SPACING["small_gap"], 0),
        )

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
            textvariable=self.vocabulary_test_text,
            font="input",
        ).pack(fill="x", ipady=8)

        play_button_area = ui.frame(sample_row, bg="main_card")
        play_button_area.pack(
            side="right",
            anchor="s",
            padx=(ui.SPACING["gap"], 0),
        )

        ui.sub_button(
            play_button_area,
            text="再生",
            command=self.speak_sample,
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

    # =========================
    # 自動更新
    # =========================

    def refresh_from_profile(self):
        new_person_key = self.get_person_key()
        new_politeness_id = self.get_politeness_id()
        new_intimacy_id = self.get_intimacy_id()

        if (
            new_person_key == self.current_person_key
            and new_politeness_id == self.current_politeness_id
            and new_intimacy_id == self.current_intimacy_id
        ):
            return

        self.current_person_key = new_person_key
        self.current_politeness_id = new_politeness_id
        self.current_intimacy_id = new_intimacy_id

        for child in self.choice_container.winfo_children():
            child.destroy()

        self.build_choices(self.choice_container)

        self.status_var.set("話者・敬語・親しみに合わせて語彙候補を更新しました")

    # =========================
    # データ処理
    # =========================

    def find_option(self, option_id):
        for opt in self.get_options():
            if opt["id"] == option_id:
                return opt

        return self.get_options()[1]

    def get_current_data(self):
        opt = self.find_option(self.selected_vocabulary.get())

        data = {
            "id": opt["id"],
            "label": opt["label"],
            "person": self.get_person_key(),
            "politeness": self.get_politeness_id(),
            "intimacy": self.get_intimacy_id(),
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
                "以下の例文の語彙に近づけてください。"
                f"例1：「{ex1}」"
                f"例2：「{ex2}」"
            )

        return data

    def save_selection_only(self):
        self.profile_store.set(
            "vocabulary",
            self.get_current_data(),
            auto_save=False,
        )

        self.profile_store.set(
            "vocabulary_test_text",
            self.vocabulary_test_text.get(),
            auto_save=True,
        )

        self.status_var.set("語彙設定を保存しました")

    def save_and_next(self):
        self.save_selection_only()

        if self.on_saved is not None:
            self.on_saved()

    def on_changed(self):
        self.save_selection_only()
        self.play_option_example(self.find_option(self.selected_vocabulary.get()), 1)

    def play_option_example(self, opt, example_no=1):
        text = opt.get(f"example{example_no}", "")
        self.play_style_sample_text(text, label=f"語彙 {opt.get('label', '')} 例{example_no}")

    # =========================
    # TTS
    # =========================

    def speak_sample(self):
        text = self.vocabulary_test_text.get().strip()

        if not text:
            messagebox.showwarning("確認", "読み上げる文を入力してください。")
            return

        self.save_selection_only()

        self.tts_client.speak_current_speaker(
            text=text,
        )

        self.status_var.set(f"語彙サンプルを再生しました: {text}")
