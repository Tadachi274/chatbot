import time
import tkinter as tk
from tkinter import ttk, messagebox

from .. import ui_style as ui
from ..config import get_person_key_from_speaker
from ..clients.robot_command_client import RobotCommandClient
from ..config_face import (
    QUESTION_FACE_OPTIONS,
    QUESTION_FACE_PRIORITY,
    QUESTION_FACE_KEEPTIME,
)
from ..config_intention import (
    QUESTION_VOICE_PRESETS,
    voice_params_to_tts_instructions,
)
from ..face_preset_store import load_face_presets
from ..panels.face_editor_panel import FaceEditorPanel
from ..panels.voice_style_panel import VoiceStylePanel


class QuestionTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        data = self.profile_store.get_nested("question", {})
        self.initial_voice_data = data.get("voice", {})
        self.initial_text = data.get("text") or self.build_question_text()
        self._loading_text = False
        self._style_signature = self.get_style_signature()
        self.style_label_vars = {}

        face = data.get("face", {})
        self.face_presets = load_face_presets()
        initial_face_id = face.get("id", QUESTION_FACE_OPTIONS[0]["id"])
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
        current_voice = self.profile_store.get_nested("question", {}).get(
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
            text="質問時の話し方を選ぶ",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            page,
            text="相手に確認するときの本文、表情、声色を調整します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        content = ui.scrollable_frame(page)

        self.build_style_source_area(content)
        self.build_text_area(content, initial_text)
        self.build_face_area(content)
        self.voice_panel = VoiceStylePanel(
            content,
            initial_data=voice_data,
            tts_client=self.tts_client,
            get_text=self.get_text,
            get_speaker=lambda: self.profile_store.get("speaker", None),
            on_changed=lambda _data: self.save_selection_only(update_status=False),
            voice_presets=QUESTION_VOICE_PRESETS,
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
            text="質問文",
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

        for opt in QUESTION_FACE_OPTIONS:
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

    def build_question_text(self):
        person_key = self.get_person_key()
        politeness_id = self.normalize_style_id("politeness", "formal")
        intimacy_id = self.normalize_style_id("intimacy", "middle")
        vocabulary_id = self.normalize_style_id("vocabulary", "middle")
        length_id = self.normalize_style_id("length", "middle")

        core = self.build_core_sentence(politeness_id, vocabulary_id)

        if length_id == "short":
            text = self.build_short_question(politeness_id, vocabulary_id)
        elif length_id == "long":
            text = self.join_sentences(
                [
                    self.build_preface_sentence(politeness_id),
                    core,
                    self.build_long_extra_sentence(politeness_id, vocabulary_id),
                ]
            )
        else:
            text = core

        return self.apply_intimacy_to_text(text, politeness_id, intimacy_id, person_key)

    def build_core_sentence(self, politeness_id, vocabulary_id):
        if politeness_id == "casual":
            if vocabulary_id == "hard":
                return "今日は一泊の予定で合ってる？"
            return "今日は一泊でいい？"
        if politeness_id == "very_formal":
            return "本日は一泊でよろしいでしょうか。"
        if politeness_id == "formal":
            return "本日は一泊でよろしいでしょうか。"
        if politeness_id == "polite":
            return "今日は一泊でよろしいですか。"
        if vocabulary_id == "hard":
            return "今日は一泊のご予定で合っていますか。"
        return "今日は一泊でよろしいですか。"

    def build_short_question(self, politeness_id, vocabulary_id):
        if politeness_id == "very_formal":
            return "一泊でよろしいでしょうか。"
        if politeness_id == "formal":
            return "一泊でよろしいでしょうか。"
        if politeness_id == "polite":
            return "一泊でいいですか。"
        if vocabulary_id == "hard":
            return "一泊の予定で合ってる？"
        return "一泊でいい？"

    def build_preface_sentence(self, politeness_id):
        if politeness_id == "casual":
            return "確認させてね。"
        if politeness_id == "polite":
            return "確認しますね。"
        return "ご宿泊内容を確認いたします。"

    def build_long_extra_sentence(self, politeness_id, vocabulary_id):
        if politeness_id == "casual":
            return "違っていたら教えてね。"
        if vocabulary_id == "easy":
            return "違っている場合は、教えてください。"
        if vocabulary_id == "hard":
            return "相違がございましたら、お知らせください。"
        return "違っている場合は、お知らせください。"

    def apply_intimacy_to_text(self, text, politeness_id, intimacy_id, person_key):
        if intimacy_id == "low":
            return text.replace("〜。", "。")

        if intimacy_id != "high":
            return text

        if person_key == "kenta":
            return self.apply_kenta_high_tone(text)

        if politeness_id == "casual":
            return text.replace("ね。", "ね〜。").replace("？", "〜？")

        return text.replace("。", "〜。")

    def apply_kenta_high_tone(self, text):
        text = text.replace("でしょうか。", "っすか。")
        text = text.replace("ですか。", "っすか。")
        text = text.replace("いい？", "いいっすか。")
        text = text.replace("合ってる？", "合ってるっすか。")
        text = text.replace("ね。", "っすね。")
        text = text.replace("ください。", "ほしいっす。")
        return text

    def regenerate_text(self):
        self.set_text(self.build_question_text())
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
                priority=QUESTION_FACE_PRIORITY,
                keeptime=QUESTION_FACE_KEEPTIME,
            )
            self.save_selection_only(update_status=False)
            self.status_var.set(f"質問時の表情を送信しました: {opt['label']}")
        except Exception as e:
            self.status_var.set(f"質問時の表情送信エラー: {e}")

    def find_face_option(self):
        selected_id = self.selected_face.get()

        for opt in QUESTION_FACE_OPTIONS:
            if opt["id"] == selected_id:
                return opt

        if selected_id.startswith("custom:"):
            name = selected_id.replace("custom:", "", 1)
            custom = self.get_custom_face_option(name)
            if custom is not None:
                return custom

        return QUESTION_FACE_OPTIONS[0]

    def get_current_data(self):
        voice_data = self.get_voice_data()
        face = self.find_face_option()

        return {
            "intent": "question",
            "label": "質問時",
            "text": self.get_text(),
            "face": {
                "id": face["id"],
                "label": face["label"],
                "type": face["type"],
                "level": int(face["level"]),
                **({"custom": True} if face.get("custom") else {}),
            },
            "voice": voice_data,
            "tts_instructions": voice_params_to_tts_instructions(voice_data["params"]),
            "style_sources": {
                "politeness": self.profile_store.get_nested("politeness", {}),
                "intimacy": self.profile_store.get_nested("intimacy", {}),
                "vocabulary": self.profile_store.get_nested("vocabulary", {}),
                "length": self.profile_store.get_nested("length", {}),
            },
            "prompt": "質問時の発話。保存された text を読み上げる。",
        }

    def save_selection_only(self, update_status=True):
        if self.voice_panel is None:
            return

        self.profile_store.set(
            "question",
            self.get_current_data(),
            auto_save=True,
        )

        if update_status:
            self.status_var.set("質問時の話し方を保存しました")

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

        self.status_var.set("質問時の文章を再生しました")

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
                priority=QUESTION_FACE_PRIORITY,
                keeptime=QUESTION_FACE_KEEPTIME,
            )
            time.sleep(1.0)
            self.robot_client.send_emotion(
                face_type=face["type"],
                level=int(face["level"]),
                priority=QUESTION_FACE_PRIORITY,
                keeptime=QUESTION_FACE_KEEPTIME,
            )
            self.tts_client.speak(
                text=text,
                instructions=self.get_tts_instructions(),
                person=self.profile_store.get("speaker", None),
            )
            self.status_var.set("質問時の表情と音声を再生しました")
        except Exception as e:
            self.status_var.set(f"質問時の統合プレビューエラー: {e}")

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
