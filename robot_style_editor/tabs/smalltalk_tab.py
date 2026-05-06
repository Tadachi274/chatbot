import time
import tkinter as tk
from tkinter import ttk, messagebox

from .. import ui_style as ui
from ..config import get_person_key_from_speaker
from ..clients.robot_command_client import RobotCommandClient
from ..config_face import (
    SMALLTALK_FACE_OPTIONS,
    SMALLTALK_FACE_PRIORITY,
    SMALLTALK_FACE_KEEPTIME,
)
from ..config_intention import (
    SMALLTALK_VOICE_PRESETS,
    voice_params_to_tts_instructions,
)
from ..face_preset_store import load_face_presets
from ..panels.face_editor_panel import FaceEditorPanel
from ..panels.voice_style_panel import VoiceStylePanel


SMALLTALK_STYLE_OPTIONS = {
    "politeness": [
        ("very_formal", "尊敬語・謙譲語"),
        ("formal", "軽い尊敬語"),
        ("polite", "丁寧語"),
        ("casual", "カジュアル"),
    ],
    "intimacy": [
        ("low", "低"),
        ("middle", "中"),
        ("high", "高"),
    ],
    "vocabulary": [
        ("easy", "簡単"),
        ("middle", "中"),
        ("hard", "難しい"),
    ],
    "length": [
        ("short", "短い"),
        ("middle", "中"),
        ("long", "長い"),
    ],
}


class SmalltalkTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        data = self.profile_store.get_nested("smalltalk", {})
        self.initial_voice_data = data.get("voice", {})
        style = data.get("style", {})

        self.style_vars = {
            "politeness": tk.StringVar(value=style.get("politeness", "polite")),
            "intimacy": tk.StringVar(value=style.get("intimacy", "middle")),
            "vocabulary": tk.StringVar(value=style.get("vocabulary", "middle")),
            "length": tk.StringVar(value=style.get("length", "middle")),
        }
        self.style_label_vars = {}
        self.initial_text = data.get("text") or self.build_smalltalk_text()
        self._loading_text = False

        face = data.get("face", {})
        self.face_presets = load_face_presets()
        initial_face_id = face.get("id", SMALLTALK_FACE_OPTIONS[0]["id"])
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
        current_voice = self.profile_store.get_nested("smalltalk", {}).get(
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

        ui.label(page, text="雑談時の話し方を選ぶ", font="page_title", bg="main_card").pack(anchor="w")
        ui.label(
            page,
            text="接客時とは別に、雑談用の話し方、本文、表情、声色を調整します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        content = ui.scrollable_frame(page)
        self.build_local_style_area(content)
        self.build_text_area(content, initial_text)
        self.build_face_area(content)
        self.voice_panel = VoiceStylePanel(
            content,
            initial_data=voice_data,
            tts_client=self.tts_client,
            get_text=self.get_text,
            get_speaker=lambda: self.profile_store.get("speaker", None),
            on_changed=lambda _data: self.save_selection_only(update_status=False),
            voice_presets=SMALLTALK_VOICE_PRESETS,
        )
        self.voice_panel.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))
        self.build_bottom_area(page)

    def build_local_style_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")
        ui.label(section, text="雑談用の話し方設定", font="section_title", bg="panel").pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        row = ui.frame(section, bg="panel")
        row.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        for title, key in (
            ("敬語", "politeness"),
            ("親しみ", "intimacy"),
            ("語彙", "vocabulary"),
            ("長さ", "length"),
        ):
            self.build_style_combo(row, title, key)

    def build_style_combo(self, row, title, key):
        card = ui.bordered_frame(row, bg="card", border="border")
        card.pack(side="left", fill="both", expand=True, padx=(0, ui.SPACING["small_gap"]))
        ui.label(card, text=title, font="small", bg="card", fg="muted").pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )

        labels = [label for _value, label in SMALLTALK_STYLE_OPTIONS[key]]
        combo = ttk.Combobox(card, values=labels, state="readonly", width=16)
        combo.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )
        combo.set(self.get_style_label(key))
        combo.bind("<<ComboboxSelected>>", lambda _event=None, style_key=key, widget=combo: self.on_style_changed(style_key, widget.get()))

    def get_style_label(self, key):
        current = self.style_vars[key].get()
        for value, label in SMALLTALK_STYLE_OPTIONS[key]:
            if value == current:
                return label
        return SMALLTALK_STYLE_OPTIONS[key][0][1]

    def on_style_changed(self, key, label):
        for value, option_label in SMALLTALK_STYLE_OPTIONS[key]:
            if option_label == label:
                self.style_vars[key].set(value)
                break
        self.regenerate_text()

    def build_text_area(self, parent, initial_text):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))
        ui.label(section, text="雑談文", font="section_title", bg="panel").pack(
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
        ui.sub_button(button_row, text="設定から文を作る", command=self.regenerate_text).pack(side="left")
        ui.sub_button(button_row, text="再生", command=self.speak_sample).pack(side="right")

    def build_face_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))
        ui.label(section, text="表情", font="section_title", bg="panel").pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )
        row = ui.frame(section, bg="panel")
        row.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        for opt in SMALLTALK_FACE_OPTIONS:
            card = ui.bordered_frame(row, bg="card", border="border")
            card.pack(side="left", fill="both", expand=True, padx=(0, ui.SPACING["small_gap"]))
            ui.radio(
                card,
                text=opt["label"],
                variable=self.selected_face,
                value=opt["id"],
                command=lambda item=opt: self.on_face_selected(item),
                bg="card",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]))
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
            ui.sub_button(other_row, text="使う", command=self.on_custom_face_selected).pack(
                side="left",
                padx=(ui.SPACING["small_gap"], 0),
            )
        ui.sub_button(other_row, text="作成", command=self.build_editor_view).pack(
            side="right",
            padx=(ui.SPACING["small_gap"], 0),
        )

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
        ui.sub_button(bottom, text="この設定でロボットを試す", command=self.play_full_preview).pack(side="left")
        ui.action_button(bottom, text="保存して次へ", command=self.save_and_next).pack(side="right")

    def build_smalltalk_text(self):
        person_key = self.get_person_key()
        politeness_id = self.style_vars["politeness"].get()
        intimacy_id = self.style_vars["intimacy"].get()
        vocabulary_id = self.style_vars["vocabulary"].get()
        length_id = self.style_vars["length"].get()

        core = self.build_core_sentence(politeness_id, vocabulary_id, intimacy_id)
        if length_id == "short":
            text = self.build_short_sentence(politeness_id, vocabulary_id, intimacy_id)
        elif length_id == "long":
            text = self.join_sentences(
                [
                    core,
                    self.build_followup_sentence(politeness_id, vocabulary_id, intimacy_id),
                    self.build_long_extra_sentence(politeness_id, vocabulary_id, intimacy_id),
                ]
            )
        else:
            text = self.join_sentences(
                [core, self.build_followup_sentence(politeness_id, vocabulary_id, intimacy_id)]
            )

        return self.apply_intimacy_to_text(text, politeness_id, intimacy_id, person_key)

    def build_core_sentence(self, politeness_id, vocabulary_id, intimacy_id):
        if politeness_id == "very_formal":
            if vocabulary_id == "easy":
                return "本日は過ごしやすいお天気でございますね。"
            if vocabulary_id == "hard":
                return "本日は穏やかで過ごしやすい気候でございますね。"
            return "本日は過ごしやすい気候でございますね。"
        if politeness_id == "formal":
            if vocabulary_id == "easy":
                return "今日はいい天気ですね。"
            if vocabulary_id == "hard":
                return "今日は穏やかで心地よい気候ですね。"
            return "今日は過ごしやすい気候ですね。"
        if politeness_id == "polite":
            if vocabulary_id == "easy":
                return "今日はいい天気ですね。"
            if vocabulary_id == "hard":
                return "今日は心地よい気候ですね。"
            return "今日は過ごしやすいですね。"
        if intimacy_id == "low":
            if vocabulary_id == "hard":
                return "今日は心地いい気候だね。"
            return "今日はいい天気だね。"
        if vocabulary_id == "hard":
            return "今日は心地いい気候だね。"
        if vocabulary_id == "easy":
            return "今日、いい天気だね。"
        return "今日は過ごしやすいね。"

    def build_short_sentence(self, politeness_id, vocabulary_id, intimacy_id):
        if politeness_id == "very_formal":
            if vocabulary_id == "hard":
                return "心地よい気候でございますね。"
            return "よいお天気でございますね。"
        if politeness_id == "formal":
            if vocabulary_id == "hard":
                return "心地よい気候ですね。"
            return "いい気候ですね。"
        if politeness_id == "polite":
            if vocabulary_id == "hard":
                return "心地よいですね。"
            return "いい天気ですね。"
        if intimacy_id == "low":
            return "いい天気だね。"
        if vocabulary_id == "hard":
            return "心地いいね。"
        return "いい天気だね。"

    def build_followup_sentence(self, politeness_id, vocabulary_id, intimacy_id):
        if politeness_id == "casual":
            if intimacy_id == "high":
                return "ちょっと外に出たくなるよね。"
            if vocabulary_id == "hard":
                return "外を歩くにも心地よさそう。"
            return "外に出るのも気持ちよさそう。"
        if vocabulary_id == "easy":
            return "外に出るのも気持ちよさそうですね。"
        if vocabulary_id == "hard":
            return "外出するにも心地よさそうですね。"
        return "外に出るのも気持ちよさそうですね。"

    def build_long_extra_sentence(self, politeness_id, vocabulary_id, intimacy_id):
        if politeness_id == "casual":
            if intimacy_id == "high":
                return "こういう日は、少し散歩したくなるよね。"
            if vocabulary_id == "hard":
                return "こういう日は、少し散策したくなるよね。"
            return "こういう日は少し歩きたくなるよね。"
        if vocabulary_id == "hard":
            return "こういう日は、少し散策したくなりますね。"
        return "こういう日は、少し歩きたくなりますね。"

    def apply_intimacy_to_text(self, text, politeness_id, intimacy_id, person_key):
        if intimacy_id == "low":
            return (
                text.replace("〜。", "。")
                .replace("ですね。", "です。")
                .replace("だね。", "だよ。")
                .replace("よね。", "よ。")
            )
        if intimacy_id != "high":
            return text
        if person_key == "kenta":
            return self.apply_kenta_high_tone(text)
        if politeness_id == "casual":
            return text.replace("だね。", "だね〜。").replace("よね。", "よね〜。").replace("そう。", "そう〜。")
        return text.replace("ですね。", "ですね〜。").replace("ますね。", "ますね〜。")

    def apply_kenta_high_tone(self, text):
        text = text.replace("ですね。", "っすね。")
        text = text.replace("だね。", "っすね。")
        text = text.replace("よね。", "っすよね。")
        text = text.replace("そう。", "そうっす。")
        return text

    def regenerate_text(self):
        self.set_text(self.build_smalltalk_text())
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

    def get_person_key(self):
        speaker = self.profile_store.get("speaker", "nozomi_emo_22_standard")
        return get_person_key_from_speaker(speaker)

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
                priority=SMALLTALK_FACE_PRIORITY,
                keeptime=SMALLTALK_FACE_KEEPTIME,
            )
            self.save_selection_only(update_status=False)
            self.status_var.set(f"雑談時の表情を送信しました: {opt['label']}")
        except Exception as e:
            self.status_var.set(f"雑談時の表情送信エラー: {e}")

    def find_face_option(self):
        selected_id = self.selected_face.get()
        for opt in SMALLTALK_FACE_OPTIONS:
            if opt["id"] == selected_id:
                return opt
        if selected_id.startswith("custom:"):
            name = selected_id.replace("custom:", "", 1)
            custom = self.get_custom_face_option(name)
            if custom is not None:
                return custom
        return SMALLTALK_FACE_OPTIONS[0]

    def get_current_data(self):
        voice_data = self.get_voice_data()
        face = self.find_face_option()
        return {
            "intent": "smalltalk",
            "label": "雑談時",
            "text": self.get_text(),
            "style": {
                "politeness": self.style_vars["politeness"].get(),
                "intimacy": self.style_vars["intimacy"].get(),
                "vocabulary": self.style_vars["vocabulary"].get(),
                "length": self.style_vars["length"].get(),
            },
            "face": {
                "id": face["id"],
                "label": face["label"],
                "type": face["type"],
                "level": int(face["level"]),
                **({"custom": True} if face.get("custom") else {}),
            },
            "voice": voice_data,
            "tts_instructions": voice_params_to_tts_instructions(voice_data["params"]),
            "prompt": "雑談時の発話。保存された text を読み上げる。雑談用 style は基本設定とは別に保存する。",
        }

    def save_selection_only(self, update_status=True):
        if self.voice_panel is None:
            return
        self.profile_store.set("smalltalk", self.get_current_data(), auto_save=True)
        if update_status:
            self.status_var.set("雑談時の話し方を保存しました")

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
        self.status_var.set("雑談時の文章を再生しました")

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
                priority=SMALLTALK_FACE_PRIORITY,
                keeptime=SMALLTALK_FACE_KEEPTIME,
            )
            time.sleep(1.0)
            self.robot_client.send_emotion(
                face_type=face["type"],
                level=int(face["level"]),
                priority=SMALLTALK_FACE_PRIORITY,
                keeptime=SMALLTALK_FACE_KEEPTIME,
            )
            self.tts_client.speak(
                text=text,
                instructions=self.get_tts_instructions(),
                person=self.profile_store.get("speaker", None),
            )
            self.status_var.set("雑談時の表情と音声を再生しました")
        except Exception as e:
            self.status_var.set(f"雑談時の統合プレビューエラー: {e}")

    def refresh_from_profile(self):
        return

    def destroy(self):
        try:
            self.robot_client.close()
        except Exception:
            pass
        super().destroy()
