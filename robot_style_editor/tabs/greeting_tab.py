import tkinter as tk
from tkinter import messagebox

from .. import ui_style as ui
from ..config import get_person_key_from_speaker
from ..config_intention import (
    GREETING_LONG_EXTRA,
    GREETING_NEED_SENTENCE,
    GREETING_OPENING_TEXT,
    GREETING_SHORT_TECHNIQUE_COMBO_SENTENCES,
    GREETING_TECHNIQUE_ORDER,
    GREETING_TECHNIQUE_COMBO_SENTENCES,
    TECHNIQUE_DEFS,
    TECHNIQUE_LABELS,
    voice_params_to_tts_instructions,
)
from ..panels.voice_style_panel import VoiceStylePanel


class GreetingTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        data = self.profile_store.get_nested("greeting", {})

        self.technique_vars = {
            key: tk.BooleanVar(value=(key in data.get("techniques", [])))
            for key in GREETING_TECHNIQUE_ORDER
        }

        initial_text = data.get("text") or self.build_greeting_text()
        self._loading_text = False
        self._style_signature = self.get_style_signature()
        self.style_label_vars = {}

        self.voice_panel = None
        self.build_ui(initial_text=initial_text, voice_data=data.get("voice", {}))

    def build_ui(self, initial_text, voice_data):
        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )

        ui.label(
            page,
            text="挨拶を選ぶ",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            page,
            text="会話の最初に使う一文、声色、挨拶のテクニックを調整します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(
            anchor="w",
            pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]),
        )

        content = self.create_scrollable_content_area(page)

        self.build_style_source_area(content)
        self.build_text_area(content, initial_text)
        self.build_technique_area(content)
        self.voice_panel = VoiceStylePanel(
            content,
            initial_data=voice_data,
            tts_client=self.tts_client,
            get_text=self.get_text,
            get_speaker=lambda: self.profile_store.get("speaker", None),
            on_changed=lambda _data: self.save_selection_only(update_status=False),
        )
        self.voice_panel.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        self.build_bottom_area(page)

    def create_scrollable_content_area(self, parent):
        outer = ui.frame(parent, bg="main_card")
        outer.pack(fill="both", expand=True)

        canvas = tk.Canvas(
            outer,
            bg=ui.COLORS["main_card"],
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")
        canvas.configure(yscrollcommand=scrollbar.set)

        content = ui.frame(canvas, bg="main_card")
        canvas_window = canvas.create_window((0, 0), window=content, anchor="nw")

        def on_content_configure(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        content.bind("<Configure>", on_content_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        return content

    def build_style_source_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        ui.label(
            section,
            text="参照中の話し方設定",
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

        self.build_style_card(
            row=row,
            title="話者",
            key="speaker",
            value=self.get_speaker_label(),
        )

        for title, key in (
            ("敬語", "politeness"),
            ("親しみ", "intimacy"),
            ("語彙", "vocabulary"),
            ("長さ", "length"),
        ):
            data = self.profile_store.get_nested(key, {})
            self.build_style_card(
                row=row,
                title=title,
                key=key,
                value=data.get("label", data.get("id", "未設定")),
            )

    def build_style_card(self, row, title, key, value):
        card = ui.bordered_frame(row, bg="card", border="border")
        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, ui.SPACING["small_gap"]),
        )

        ui.label(
            card,
            text=title,
            font="small",
            bg="card",
            fg="muted",
        ).pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], 0),
        )

        self.style_label_vars[key] = tk.StringVar(value=value)

        ui.variable_label(
            card,
            textvariable=self.style_label_vars[key],
            font="body_bold",
            bg="card",
            fg="text",
        ).pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

    def build_text_area(self, parent, initial_text):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        ui.label(
            section,
            text="挨拶文",
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

        text_row = ui.frame(card, bg="card")
        text_row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]),
        )

        self.text_box = tk.Text(
            text_row,
            height=4,
            font=ui.FONTS["input"],
            bg=ui.COLORS["card"],
            fg=ui.COLORS["text"],
            insertbackground=ui.COLORS["text"],
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightbackground=ui.COLORS["border"],
            highlightcolor=ui.COLORS["accent"],
            wrap="word",
        )
        self.text_box.pack(fill="x")
        self.text_box.insert("1.0", initial_text)
        self.text_box.bind("<KeyRelease>", lambda _event=None: self.save_selection_only(update_status=False))

        button_row = ui.frame(card, bg="card")
        button_row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["card_y"]),
        )

        ui.sub_button(
            button_row,
            text="設定から文を作る",
            command=self.regenerate_text_from_profile,
        ).pack(side="left")

        ui.sub_button(
            button_row,
            text="再生",
            command=self.speak_sample,
        ).pack(side="right")

    def build_technique_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(
            section,
            text="テクニック",
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

        grid = ui.frame(card, bg="card")
        grid.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=ui.SPACING["card_y"],
        )

        for index, key in enumerate(GREETING_TECHNIQUE_ORDER):
            item = ui.frame(grid, bg="card")
            item.grid(
                row=index // 3,
                column=index % 3,
                sticky="ew",
                padx=(0, ui.SPACING["gap"]),
                pady=(0, ui.SPACING["small_gap"]),
            )
            grid.columnconfigure(index % 3, weight=1)

            check = tk.Checkbutton(
                item,
                text=TECHNIQUE_LABELS[key],
                variable=self.technique_vars[key],
                command=lambda tech=key: self.on_technique_changed(tech),
                font=ui.FONTS["body_bold"],
                bg=ui.COLORS["card"],
                fg=ui.COLORS["text"],
                activebackground=ui.COLORS["card"],
                activeforeground=ui.COLORS["text"],
                selectcolor=ui.COLORS["card"],
                anchor="w",
            )
            check.pack(anchor="w")

            ui.label(
                item,
                text=TECHNIQUE_DEFS[key],
                font="small",
                bg="card",
                fg="muted",
                wraplength=260,
                justify="left",
                anchor="w",
            ).pack(fill="x", padx=(24, 0))

    def build_bottom_area(self, parent):
        bottom = ui.frame(parent, bg="main_card")
        bottom.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.action_button(
            bottom,
            text="保存して次へ",
            command=self.save_and_next,
        ).pack(side="right")

    def on_technique_changed(self, _technique_id):
        self.set_text(self.build_greeting_text())
        self.save_selection_only(update_status=False)

    def regenerate_text_from_profile(self):
        self.set_text(self.build_greeting_text())
        self.save_selection_only()

    def set_text(self, text):
        self._loading_text = True
        try:
            self.text_box.delete("1.0", "end")
            self.text_box.insert("1.0", text)
        finally:
            self._loading_text = False

    def get_text(self):
        return self.text_box.get("1.0", "end").strip()

    def get_selected_techniques(self):
        return [
            key
            for key in GREETING_TECHNIQUE_ORDER
            if self.technique_vars[key].get()
        ]

    def get_style_signature(self):
        return (
            self.profile_store.get("speaker", ""),
            self.profile_store.get_nested("politeness", {}).get("id", ""),
            self.profile_store.get_nested("intimacy", {}).get("id", ""),
            self.profile_store.get_nested("vocabulary", {}).get("id", ""),
            self.profile_store.get_nested("length", {}).get("id", ""),
        )

    def build_greeting_text(self):
        person_key = self.get_person_key()
        politeness_id = self.normalize_style_id("politeness", "formal")
        intimacy_id = self.normalize_style_id("intimacy", "middle")
        vocabulary_id = self.normalize_style_id("vocabulary", "middle")
        length_id = self.normalize_style_id("length", "middle")

        opening = self.resolve_person_text(
            GREETING_OPENING_TEXT[politeness_id][intimacy_id],
            person_key,
        )
        need = self.resolve_person_text(
            GREETING_NEED_SENTENCE[politeness_id][vocabulary_id][intimacy_id],
            person_key,
        )
        technique_text = self.build_technique_text(
            person_key=person_key,
            politeness_id=politeness_id,
            intimacy_id=intimacy_id,
            vocabulary_id=vocabulary_id,
            short=(length_id == "short"),
        )

        if length_id == "short":
            return self.join_sentences([opening, technique_text])

        if length_id == "long":
            return self.join_sentences(
                [
                    opening,
                    technique_text,
                    need,
                    self.apply_intimacy_to_technique(
                        GREETING_LONG_EXTRA[politeness_id],
                        intimacy_id,
                        person_key,
                    ),
                ]
            )

        return self.join_sentences([opening, technique_text, need])

    def normalize_style_id(self, key, fallback):
        value = self.profile_store.get_nested(key, {}).get("id", fallback)
        if value == "other":
            return fallback
        return value

    def get_person_key(self):
        speaker = self.profile_store.get("speaker", "nozomi_emo_22_standard")
        return get_person_key_from_speaker(speaker)

    def get_speaker_label(self):
        speaker = self.profile_store.get("speaker", "nozomi_emo_22_standard")
        person_key = get_person_key_from_speaker(speaker)
        if person_key == "kenta":
            return "けんた"
        if person_key == "nozomi":
            return "のぞみ"
        return speaker

    def resolve_person_text(self, value, person_key):
        if isinstance(value, dict):
            return value.get(person_key, value.get("nozomi", ""))
        return value

    def build_technique_text(self, person_key, politeness_id, intimacy_id, vocabulary_id, short=False):
        selected = tuple(self.get_selected_techniques())
        source = (
            GREETING_SHORT_TECHNIQUE_COMBO_SENTENCES
            if short
            else GREETING_TECHNIQUE_COMBO_SENTENCES
        )
        text = source.get(selected, "")

        if not text:
            return ""

        text = self.apply_politeness_to_technique(text, politeness_id)
        text = self.apply_vocabulary_to_technique(text, vocabulary_id)
        text = self.apply_intimacy_to_technique(text, intimacy_id, person_key)
        return text

    def apply_politeness_to_technique(self, text, politeness_id):
        if politeness_id == "very_formal":
            return (
                text.replace("今日は", "本日は")
                .replace("でしょうか", "でございますか")
                .replace("ご案内します", "ご案内いたします")
                .replace("無理のない範囲でゆっくり", "ご負担のない範囲で")
            )

        if politeness_id == "casual":
            return (
                text.replace("でしょうか", "ですか")
                .replace("ご案内します", "案内します")
                .replace("案内します", "案内するよ")
                .replace("もしよろしければ、", "よければ、")
                .replace("無理のない範囲で", "無理せず")
                .replace("でしたら", "なら")
                .replace("お仕事帰り", "帰り")
                .replace("お帰り", "帰り")
                .replace("ごゆっくり", "ゆっくり")
            )

        return text

    def apply_vocabulary_to_technique(self, text, vocabulary_id):
        if vocabulary_id == "easy":
            return (
                text.replace("気候", "天気")
                .replace("ご案内", "案内")
                .replace("範囲", "ペース")
            )

        if vocabulary_id == "hard":
            return (
                text.replace("過ごしやすい", "心地よい")
                .replace("案内", "ご案内")
                .replace("ごご案内", "ご案内")
            )

        return text

    def apply_intimacy_to_technique(self, text, intimacy_id, person_key):
        if intimacy_id == "high":
            if person_key == "kenta":
                return self.apply_kenta_high_tone(text)
            return text.replace("。", "〜。")

        if intimacy_id == "low":
            return text.replace("〜。", "。")

        return text

    def apply_kenta_high_tone(self, text):
        text = text.replace("ですね。", "っすね。")
        text = text.replace("ですか。", "っすか。")
        text = text.replace("でしょうか。", "っすか。")
        text = text.replace("します。", "するっす。")
        text = text.replace("するよ。", "するっす。")
        text = text.replace("見ていこう。", "見ていくっす。")
        text = text.replace("どうぞ。", "どうぞっす。")
        return text

    def join_sentences(self, sentences):
        return "".join(sentence for sentence in sentences if sentence)

    def get_voice_data(self):
        if self.voice_panel is None:
            return {}

        return self.voice_panel.get_data()

    def get_tts_instructions(self):
        voice_data = self.get_voice_data()
        return voice_params_to_tts_instructions(voice_data["params"])

    def get_current_data(self):
        voice_data = self.get_voice_data()

        return {
            "intent": "greeting",
            "label": "挨拶",
            "text": self.get_text(),
            "techniques": self.get_selected_techniques(),
            "technique_defs": {
                key: TECHNIQUE_DEFS[key]
                for key in self.get_selected_techniques()
            },
            "voice": voice_data,
            "tts_instructions": voice_params_to_tts_instructions(voice_data["params"]),
            "style_sources": {
                "politeness": self.profile_store.get_nested("politeness", {}),
                "intimacy": self.profile_store.get_nested("intimacy", {}),
                "vocabulary": self.profile_store.get_nested("vocabulary", {}),
                "length": self.profile_store.get_nested("length", {}),
            },
            "prompt": (
                "会話開始時の挨拶。保存された text を読み上げる。"
                "必要に応じて techniques の方針を反映する。"
            ),
        }

    def save_selection_only(self, update_status=True):
        if self.voice_panel is None:
            return

        self.profile_store.set(
            "greeting",
            self.get_current_data(),
            auto_save=True,
        )

        if update_status:
            self.status_var.set("挨拶を保存しました")

    def save_and_next(self):
        self.save_selection_only()

        if self.on_saved is not None:
            self.on_saved()

    def speak_sample(self):
        text = self.get_text()

        if not text:
            messagebox.showwarning("確認", "読み上げる文を入力してください。")
            return

        self.save_selection_only(update_status=False)

        speaker = self.profile_store.get("speaker", None)
        self.tts_client.speak(
            text=text,
            instructions=self.get_tts_instructions(),
            person=speaker,
        )

        self.status_var.set("挨拶を再生しました")

    def refresh_from_profile(self):
        new_signature = self.get_style_signature()
        if new_signature == self._style_signature:
            return

        self._style_signature = new_signature
        self.refresh_style_labels()
        self.regenerate_text_from_profile()

    def refresh_style_labels(self):
        for key, label_var in self.style_label_vars.items():
            if key == "speaker":
                label_var.set(self.get_speaker_label())
            else:
                data = self.profile_store.get_nested(key, {})
                label_var.set(data.get("label", data.get("id", "未設定")))
