import time
import tkinter as tk
from tkinter import ttk, messagebox

from .. import ui_style as ui
from ..config import get_person_key_from_speaker
from ..clients.robot_command_client import RobotCommandClient
from ..config_face import (
    EXPLANATION_FACE_OPTIONS,
    EXPLANATION_FACE_PRIORITY,
    EXPLANATION_FACE_KEEPTIME,
)
from ..config_intention import (
    EXPLANATION_TECHNIQUE_ORDER,
    EXPLANATION_VOICE_PRESETS,
    TECHNIQUE_DEFS,
    TECHNIQUE_LABELS,
    voice_params_to_tts_instructions,
)
from ..face_preset_store import load_face_presets
from ..panels.face_editor_panel import FaceEditorPanel
from ..panels.voice_style_panel import VoiceStylePanel


class ExplanationTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        data = self.profile_store.get_nested("explanation", {})
        self.initial_voice_data = data.get("voice", {})

        self.technique_vars = {
            key: tk.BooleanVar(value=(key in data.get("techniques", [])))
            for key in EXPLANATION_TECHNIQUE_ORDER
        }

        self.initial_text = data.get("text") or self.build_explanation_text()
        self._loading_text = False
        self._style_signature = self.get_style_signature()
        self.style_label_vars = {}

        face = data.get("face", {})
        self.face_presets = load_face_presets()
        initial_face_id = face.get("id", EXPLANATION_FACE_OPTIONS[0]["id"])
        initial_custom_name = ""

        if face.get("custom") or initial_face_id.startswith("custom:"):
            initial_custom_name = face.get("type") or face.get("label", "")
            if initial_custom_name:
                initial_face_id = f"custom:{initial_custom_name}"

        if not initial_custom_name and self.face_presets:
            initial_custom_name = sorted(self.face_presets.keys())[0]

        self.selected_face = tk.StringVar(value=initial_face_id)
        self.custom_face_name = tk.StringVar(value=initial_custom_name)
        self.robot_client = RobotCommandClient()
        self.voice_panel = None

        self.build_main_view()

    def clear_views(self):
        for child in self.winfo_children():
            child.destroy()

    def build_main_view(self):
        current_text = self.get_current_text_or_initial()
        current_voice = self.profile_store.get_nested("explanation", {}).get(
            "voice",
            self.initial_voice_data,
        )

        self.clear_views()
        self.build_ui(current_text, current_voice)

    def get_current_text_or_initial(self):
        if hasattr(self, "text_box") and self.text_box.winfo_exists():
            text = self.get_text()
            if text:
                return text

        return self.initial_text

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
            text="説明時の話し方を選ぶ",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            page,
            text="説明するときの本文、テクニック、表情、声色を調整します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        content = ui.scrollable_frame(page)

        self.build_style_source_area(content)
        self.build_text_area(content, initial_text)
        self.build_technique_area(content)
        self.build_face_area(content)
        self.voice_panel = VoiceStylePanel(
            content,
            initial_data=voice_data,
            tts_client=self.tts_client,
            get_text=self.get_text,
            get_speaker=lambda: self.profile_store.get("speaker", None),
            on_changed=lambda _data: self.save_selection_only(update_status=False),
            voice_presets=EXPLANATION_VOICE_PRESETS,
        )
        self.voice_panel.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        self.build_bottom_area(page)

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

        self.build_style_card(row, "話者", "speaker", self.get_speaker_label())

        for title, key in (
            ("敬語", "politeness"),
            ("親しみ", "intimacy"),
            ("語彙", "vocabulary"),
            ("長さ", "length"),
        ):
            data = self.profile_store.get_nested(key, {})
            self.build_style_card(
                row,
                title,
                key,
                data.get("label", data.get("id", "未設定")),
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
            text="説明文",
            font="section_title",
            bg="panel",
        ).pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        self.text_box = tk.Text(
            card,
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
        self.text_box.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]),
        )
        self.text_box.insert("1.0", initial_text)
        self.text_box.bind("<KeyRelease>", lambda _event=None: self.on_text_changed())

        button_row = ui.frame(card, bg="card")
        button_row.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))

        ui.sub_button(
            button_row,
            text="設定から文を作る",
            command=self.regenerate_text,
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
        card.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        grid = ui.frame(card, bg="card")
        grid.pack(fill="x", padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])

        for index, key in enumerate(EXPLANATION_TECHNIQUE_ORDER):
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
                command=self.on_technique_changed,
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

    def build_face_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

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
        row.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        for opt in EXPLANATION_FACE_OPTIONS:
            card = ui.bordered_frame(row, bg="card", border="border")
            card.pack(side="left", fill="both", expand=True, padx=(0, ui.SPACING["small_gap"]))

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
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))

        other_card = ui.bordered_frame(row, bg="card", border="border")
        other_card.pack(side="left", fill="both", expand=True, padx=(0, ui.SPACING["small_gap"]))

        other_row = ui.frame(other_card, bg="card")
        other_row.pack(fill="x", padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])

        ui.radio(
            other_row,
            text="その他",
            variable=self.selected_face,
            value=f"custom:{self.custom_face_name.get()}",
            command=self.on_custom_face_selected,
            bg="card",
        ).pack(side="left", padx=(0, ui.SPACING["gap"]))

        preset_names = sorted(self.face_presets.keys())
        if preset_names:
            if self.custom_face_name.get() not in preset_names:
                self.custom_face_name.set(preset_names[0])

            combo = ttk.Combobox(
                other_row,
                values=preset_names,
                textvariable=self.custom_face_name,
                state="readonly",
                width=20,
            )
            combo.pack(side="left", fill="x", expand=True)
            combo.bind("<<ComboboxSelected>>", lambda _event=None: self.on_custom_face_selected())

            ui.sub_button(
                other_row,
                text="使う",
                command=self.on_custom_face_selected,
            ).pack(side="left", padx=(ui.SPACING["small_gap"], 0))

        ui.sub_button(
            other_row,
            text="作成",
            command=self.build_editor_view,
        ).pack(side="right", padx=(ui.SPACING["small_gap"], 0))

    def build_editor_view(self):
        self.clear_views()

        editor = FaceEditorPanel(
            self,
            robot_client=self.robot_client,
            on_back=self.build_main_view,
            on_saved=self.on_custom_face_saved,
        )
        editor.pack(fill="both", expand=True)

    def build_bottom_area(self, parent):
        bottom = ui.frame(parent, bg="main_card")
        bottom.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.sub_button(
            bottom,
            text="この設定でロボットを試す",
            command=self.play_full_preview,
        ).pack(side="left")

        ui.action_button(
            bottom,
            text="保存して次へ",
            command=self.save_and_next,
        ).pack(side="right")

    def on_technique_changed(self):
        self.set_text(self.build_explanation_text())
        self.save_selection_only(update_status=False)

    def build_explanation_text(self):
        person_key = self.get_person_key()
        politeness_id = self.normalize_style_id("politeness", "formal")
        intimacy_id = self.normalize_style_id("intimacy", "middle")
        vocabulary_id = self.normalize_style_id("vocabulary", "middle")
        length_id = self.normalize_style_id("length", "middle")
        selected = set(self.get_selected_techniques())

        core = self.build_core_sentence(politeness_id, vocabulary_id)

        if length_id == "short":
            return self.apply_style_to_sentence(
                self.build_short_explanation(core, selected, politeness_id),
                politeness_id,
                intimacy_id,
                person_key,
            )

        if length_id == "long":
            text = self.join_sentences(
                [
                    self.build_intro_sentence(selected, politeness_id, vocabulary_id),
                    self.build_empathy_sentence(selected, politeness_id),
                    core,
                    self.build_reason_sentence(selected, politeness_id, vocabulary_id),
                    self.build_rephrase_sentence(selected, politeness_id, vocabulary_id),
                    self.build_step_sentence(selected, politeness_id, vocabulary_id),
                    self.build_proactive_sentence(selected, politeness_id, vocabulary_id),
                    self.build_long_extra_sentence(politeness_id, vocabulary_id),
                ]
            )
            return self.apply_style_to_sentence(text, politeness_id, intimacy_id, person_key)

        text = self.join_sentences(
            [
                self.build_intro_sentence(selected, politeness_id, vocabulary_id),
                self.build_empathy_sentence(selected, politeness_id),
                core,
                self.build_reason_sentence(selected, politeness_id, vocabulary_id),
                self.build_rephrase_sentence(selected, politeness_id, vocabulary_id),
                self.build_step_sentence(selected, politeness_id, vocabulary_id),
                self.build_proactive_sentence(selected, politeness_id, vocabulary_id),
            ]
        )
        return self.apply_style_to_sentence(text, politeness_id, intimacy_id, person_key)

    def build_short_explanation(self, core, selected, politeness_id):
        if "permission" in selected:
            if politeness_id == "casual":
                return "先に時間だけ言うね。" + core
            return "先に時間だけお伝えします。" + core
        if "goal_clarity" in selected:
            if politeness_id == "casual":
                return "チェックアウト時間の案内だよ。" + core
            return "チェックアウト時間の案内です。" + core
        if "summary" in selected or "paraphrase" in selected:
            if politeness_id == "casual":
                return "つまり、11時までだよ。"
            return "つまり、11時までです。"
        if "step_by_step" in selected:
            if politeness_id == "casual":
                return core + "11時までにフロントに来てね。"
            return core + "11時までにフロントへお越しください。"
        if "proactive" in selected:
            if politeness_id == "casual":
                return core + "延長したいなら確認できるよ。"
            return core + "延長希望なら確認できます。"
        if "evidence" in selected:
            if politeness_id == "casual":
                return core + "清掃準備があるからだよ。"
            return core + "清掃準備があるためです。"
        if "expertise" in selected:
            if politeness_id == "casual":
                return core + "延長枠とは別の時間だよ。"
            return core + "延長枠とは別の時間です。"
        if "empathy" in selected:
            if politeness_id == "casual":
                return "朝はバタバタするよね。" + core
            return "朝は慌ただしいですよね。" + core
        return core

    def build_intro_sentence(self, selected, politeness_id, vocabulary_id):
        if "permission" in selected and "goal_clarity" in selected:
            if politeness_id == "casual":
                return "先にチェックアウト時間を案内してもいい？"
            return "先にチェックアウト時間についてご案内してもよろしいでしょうか。"

        if "permission" in selected:
            if politeness_id == "casual":
                return "先に時間を伝えてもいい？"
            return "先にチェックアウト時間をお伝えしてもよろしいでしょうか。"

        if "goal_clarity" in selected:
            if politeness_id == "casual":
                return "チェックアウト時間の案内だよ。"
            return "チェックアウト時間についてご案内します。"

        return ""

    def build_empathy_sentence(self, selected, politeness_id):
        if "empathy" not in selected:
            return ""

        if politeness_id == "casual":
            return "朝は支度でバタバタしやすいよね。"

        return "朝のお支度で慌ただしいですよね。"

    def build_reason_sentence(self, selected, politeness_id, vocabulary_id):
        if "evidence" not in selected and "expertise" not in selected:
            return ""

        if "evidence" in selected and "expertise" in selected:
            if politeness_id == "casual":
                return "清掃と次の準備があるから、館内では時間を分けて管理しているよ。"
            if vocabulary_id == "hard":
                return "客室清掃と次のお客様の準備を行うため、館内運用上、レイトチェックアウト枠とは別に管理しております。"
            return "清掃と次のお客様の準備があるため、館内では通常のチェックアウト時間として管理しています。"

        if "evidence" in selected:
            if politeness_id == "casual":
                return "清掃と次の準備があるからだよ。"
            return "清掃と次のお客様の準備があるためです。"

        if politeness_id == "casual":
            return "館内では、延長できる枠とは分けて管理しているよ。"
        if vocabulary_id == "easy":
            return "延長できる時間とは別に、通常の時間として決まっています。"
        return "館内運用上、レイトチェックアウト枠とは別に管理しています。"

    def build_rephrase_sentence(self, selected, politeness_id, vocabulary_id):
        if "summary" in selected:
            if politeness_id == "casual":
                return "つまり、11時までに部屋を出れば大丈夫だよ。"
            if vocabulary_id == "hard":
                return "要点としては、11時までにご退室いただく形です。"
            return "まとめると、11時までにお部屋を出ていただく形です。"

        if "paraphrase" in selected:
            if politeness_id == "casual":
                return "言い換えると、11時までに部屋を出れば大丈夫。"
            return "つまり、11時までにお部屋を出ていただく形です。"

        return ""

    def build_step_sentence(self, selected, politeness_id, vocabulary_id):
        if "step_by_step" not in selected:
            return ""

        if politeness_id == "casual":
            return "荷物をまとめて、11時までにフロントに来てね。"
        if vocabulary_id == "hard":
            return "お荷物をおまとめのうえ、11時までにフロントへお越しください。"
        return "まずお荷物をまとめて、11時までにフロントへお越しください。"

    def build_proactive_sentence(self, selected, politeness_id, vocabulary_id):
        if "proactive" not in selected:
            return ""

        if politeness_id == "casual":
            return "延長したいときは、空きがあるか確認できるよ。"
        if vocabulary_id == "easy":
            return "延長したい場合は、空きがあるかこちらで確認できます。"
        return "延長をご希望の場合は、空き状況をこちらで確認できます。"

    def build_long_extra_sentence(self, politeness_id, vocabulary_id):
        if politeness_id == "casual":
            return "わからないところがあれば、そのまま聞いてね。"
        if vocabulary_id == "easy":
            return "わからないことがあれば、その場で確認できます。"
        if vocabulary_id == "hard":
            return "ご不明点がございましたら、続けて確認いたします。"
        return "ご不明な点があれば、続けて確認できます。"

    def build_core_sentence(self, politeness_id, vocabulary_id):
        if politeness_id == "very_formal":
            return "チェックアウトは11時でございます。"
        if politeness_id == "formal":
            return "チェックアウトは11時となっております。"
        if politeness_id == "polite":
            return "チェックアウトは11時です。"
        if vocabulary_id == "easy":
            return "チェックアウトは11時だよ。"
        return "チェックアウトは11時。"

    def apply_style_to_sentence(self, text, politeness_id, intimacy_id, person_key):
        if not text:
            return ""

        text = self.apply_vocabulary_to_text(text, self.normalize_style_id("vocabulary", "middle"))
        text = self.apply_intimacy_to_text(text, politeness_id, intimacy_id, person_key)
        return text

    def apply_vocabulary_to_text(self, text, vocabulary_id):
        if vocabulary_id == "easy":
            return (
                text.replace("ご退室", "お部屋を出ること")
                .replace("お越し", "来て")
                .replace("空き状況", "空き")
                .replace("館内運用上", "ホテルの決まりとして")
                .replace("レイトチェックアウト枠", "延長できる時間")
            )

        if vocabulary_id == "hard":
            return (
                text.replace("部屋を出る", "退室する")
                .replace("お部屋を出て", "ご退室")
                .replace("空き", "空き状況")
                .replace("決まっています", "設定されています")
            )

        return text

    def apply_intimacy_to_text(self, text, politeness_id, intimacy_id, person_key):
        if intimacy_id == "low":
            return text.replace("〜。", "。")

        if intimacy_id != "high":
            return text

        if person_key == "kenta":
            return self.apply_kenta_high_tone(text)

        if politeness_id == "casual":
            return text.replace("だよ。", "だよ〜。").replace("ね。", "ね〜。")

        return text.replace("。", "〜。")

    def apply_kenta_high_tone(self, text):
        text = text.replace("ですよね。", "っすよね。")
        text = text.replace("です。", "っす。")
        text = text.replace("だよ。", "っす。")
        text = text.replace("だよ〜。", "っすね。")
        text = text.replace("してもいい？", "してもいいっすか。")
        text = text.replace("来てね。", "来てほしいっす。")
        text = text.replace("できるよ。", "できるっす。")
        return text

    def regenerate_text(self):
        self.set_text(self.build_explanation_text())
        self.save_selection_only()

    def set_text(self, text):
        self._loading_text = True
        try:
            self.text_box.delete("1.0", "end")
            self.text_box.insert("1.0", text)
        finally:
            self._loading_text = False

    def on_text_changed(self):
        if self._loading_text:
            return

        self.save_selection_only(update_status=False)

    def get_text(self):
        return self.text_box.get("1.0", "end").strip()

    def get_selected_techniques(self):
        return [
            key
            for key in EXPLANATION_TECHNIQUE_ORDER
            if self.technique_vars[key].get()
        ]

    def normalize_style_id(self, key, fallback):
        value = self.profile_store.get_nested(key, {}).get("id", fallback)
        if value == "other":
            return fallback
        return value

    def get_style_signature(self):
        return (
            self.profile_store.get("speaker", ""),
            self.profile_store.get_nested("politeness", {}).get("id", ""),
            self.profile_store.get_nested("intimacy", {}).get("id", ""),
            self.profile_store.get_nested("vocabulary", {}).get("id", ""),
            self.profile_store.get_nested("length", {}).get("id", ""),
        )

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

    def join_sentences(self, sentences):
        return "".join(sentence for sentence in sentences if sentence)

    def get_voice_data(self):
        if self.voice_panel is None:
            return {}

        return self.voice_panel.get_data()

    def get_tts_instructions(self):
        voice_data = self.get_voice_data()
        return voice_params_to_tts_instructions(voice_data["params"])

    def infer_custom_face_level(self, name):
        if name and name[-1].isdigit():
            value = int(name[-1])
            if value in (1, 2, 3):
                return value
        return 1

    def get_custom_face_option(self, name):
        name = (name or "").strip()
        if not name:
            return None

        return {
            "id": f"custom:{name}",
            "label": name,
            "type": name,
            "level": self.infer_custom_face_level(name),
            "custom": True,
        }

    def on_custom_face_selected(self):
        opt = self.get_custom_face_option(self.custom_face_name.get())
        if opt is None:
            messagebox.showwarning("確認", "使用する表情を選択してください。")
            return

        self.selected_face.set(opt["id"])
        self.on_face_selected(opt)

    def on_custom_face_saved(self, name, _data):
        self.face_presets = load_face_presets()
        self.custom_face_name.set(name)

        opt = self.get_custom_face_option(name)
        if opt is not None:
            self.selected_face.set(opt["id"])
            self.save_selection_only(update_status=True)

        self.build_main_view()

    def on_face_selected(self, opt):
        try:
            self.robot_client.send_emotion(
                face_type=opt["type"],
                level=int(opt["level"]),
                priority=EXPLANATION_FACE_PRIORITY,
                keeptime=EXPLANATION_FACE_KEEPTIME,
            )
            self.save_selection_only(update_status=False)
            self.status_var.set(f"説明時の表情を送信しました: {opt['label']}")
        except Exception as e:
            self.status_var.set(f"説明時の表情送信エラー: {e}")

    def find_face_option(self):
        selected_id = self.selected_face.get()

        for opt in EXPLANATION_FACE_OPTIONS:
            if opt["id"] == selected_id:
                return opt

        if selected_id.startswith("custom:"):
            name = selected_id.replace("custom:", "", 1)
            custom = self.get_custom_face_option(name)
            if custom is not None:
                return custom

        return EXPLANATION_FACE_OPTIONS[0]

    def get_current_data(self):
        voice_data = self.get_voice_data()
        face = self.find_face_option()

        return {
            "intent": "explanation",
            "label": "説明時",
            "text": self.get_text(),
            "face": {
                "id": face["id"],
                "label": face["label"],
                "type": face["type"],
                "level": int(face["level"]),
                **({"custom": True} if face.get("custom") else {}),
            },
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
                "説明時の発話。保存された text を読み上げる。"
                "必要に応じて techniques の方針を自然な説明文として反映する。"
            ),
        }

    def save_selection_only(self, update_status=True):
        if self.voice_panel is None:
            return

        self.profile_store.set(
            "explanation",
            self.get_current_data(),
            auto_save=True,
        )

        if update_status:
            self.status_var.set("説明時の話し方を保存しました")

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

        self.tts_client.speak(
            text=text,
            instructions=self.get_tts_instructions(),
            person=self.profile_store.get("speaker", None),
        )

        self.status_var.set("説明時の文章を再生しました")

    def play_full_preview(self):
        text = self.get_text()
        if not text:
            messagebox.showwarning("確認", "読み上げる文を入力してください。")
            return

        self.save_selection_only(update_status=False)
        face = self.find_face_option()

        try:
            self.robot_client.send_emotion(
                face_type="neutral",
                level=1,
                priority=EXPLANATION_FACE_PRIORITY,
                keeptime=EXPLANATION_FACE_KEEPTIME,
            )
            time.sleep(1.0)
            self.robot_client.send_emotion(
                face_type=face["type"],
                level=int(face["level"]),
                priority=EXPLANATION_FACE_PRIORITY,
                keeptime=EXPLANATION_FACE_KEEPTIME,
            )
            self.tts_client.speak(
                text=text,
                instructions=self.get_tts_instructions(),
                person=self.profile_store.get("speaker", None),
            )
            self.status_var.set("説明時の表情と音声を再生しました")
        except Exception as e:
            self.status_var.set(f"説明時の統合プレビューエラー: {e}")

    def refresh_from_profile(self):
        new_signature = self.get_style_signature()
        if new_signature == self._style_signature:
            return

        self._style_signature = new_signature
        self.refresh_style_labels()
        self.regenerate_text()

    def refresh_style_labels(self):
        for key, label_var in self.style_label_vars.items():
            if key == "speaker":
                label_var.set(self.get_speaker_label())
            else:
                data = self.profile_store.get_nested(key, {})
                label_var.set(data.get("label", data.get("id", "未設定")))

    def destroy(self):
        try:
            self.robot_client.close()
        except Exception:
            pass

        super().destroy()
