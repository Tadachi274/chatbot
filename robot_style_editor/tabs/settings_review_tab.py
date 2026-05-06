import tkinter as tk

from .. import ui_style as ui
from ..config import get_person_key_from_speaker


class SettingsReviewTab(tk.Frame):
    INTENTS = [
        ("挨拶", "greeting"),
        ("説明", "explanation"),
        ("質問", "question"),
        ("承諾", "acceptance"),
        ("要求", "request"),
        ("謝罪", "apology"),
        ("感謝", "gratitude"),
        ("雑談", "smalltalk"),
    ]

    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])
        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved
        self.content = None
        self.build_ui()

    def build_ui(self):
        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )

        header = ui.frame(page, bg="main_card")
        header.pack(fill="x")
        ui.label(header, text="設定確認", font="page_title", bg="main_card").pack(side="left")
        ui.sub_button(header, text="再読み込み", command=self.refresh_from_profile).pack(side="right")

        ui.label(
            page,
            text="設定した内容を、選択ラベルだけで簡潔に確認します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        self.content = ui.scrollable_frame(page, pady=(0, ui.SPACING["small_gap"]))
        self.render_summary()
        self.build_bottom_area(page)

    def build_bottom_area(self, parent):
        bottom = ui.frame(parent, bg="main_card")
        bottom.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))
        ui.action_button(bottom, text="接客例へ進む", command=self.save_and_next).pack(side="right")

    def refresh_from_profile(self):
        if self.content is not None:
            self.render_summary()

    def render_summary(self):
        for child in self.content.winfo_children():
            child.destroy()

        self.render_group("話者", [("話者", self.speaker_label())])
        self.render_group("スタイル", self.style_items())
        self.render_group("応答・間合い", self.response_items())
        self.render_group("姿", self.pose_items())
        self.render_group("Dialog Act", self.intent_items())
        self.render_group("フィラー", self.filler_items())

    def render_group(self, title, items):
        section = ui.frame(self.content, bg="panel")
        section.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))

        ui.label(
            section,
            text=title,
            font="section_title",
            bg="panel",
        ).pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        for label, value in items:
            self.render_row(section, label, value)

    def render_row(self, parent, label, value):
        card = ui.bordered_frame(parent, bg="card", border="border")
        card.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["small_gap"]))

        row = ui.frame(card, bg="card")
        row.pack(fill="x", padx=ui.SPACING["card_x"], pady=ui.SPACING["compact_y"])

        ui.label(
            row,
            text=label,
            font="body_bold",
            bg="card",
            fg="text",
            width=14,
            anchor="w",
        ).pack(side="left")

        ui.label(
            row,
            text=value,
            font="body",
            bg="card",
            fg="sub_text",
            justify="left",
            anchor="w",
            wraplength=920,
        ).pack(side="left", fill="x", expand=True)

    def speaker_label(self):
        speaker = self.profile_store.get("speaker", "")
        person = get_person_key_from_speaker(speaker)
        if person == "kenta":
            return "けんた"
        if person == "nozomi":
            return "のぞみ"
        return "未設定"

    def style_items(self):
        return [
            ("敬語", self.data_label("politeness")),
            ("親しみ", self.data_label("intimacy")),
            ("語彙", self.data_label("vocabulary")),
            ("長さ", self.data_label("length")),
            ("詳細設定", self.style_detail_label()),
            ("特別考慮", self.special_consideration_label()),
        ]

    def response_items(self):
        speed = self.profile_store.get_nested("speech_speed", {}) or {}
        pause = self.profile_store.get_nested("sentence_pause", {}) or {}
        delay = self.profile_store.get_nested("response_delay", {}) or {}
        return [
            ("話速", speed.get("label", "未設定")),
            ("文間", pause.get("label", "未設定")),
            ("返答の間", self.response_delay_label(delay)),
        ]

    def pose_items(self):
        thinking = self.profile_store.get_nested("thinking_pose", {}) or {}
        listening = self.profile_store.get_nested("listening_pose", {}) or {}
        understanding = self.profile_store.get_nested("understanding_pose", {}) or {}
        return [
            ("考え姿", self.thinking_pose_label(thinking)),
            ("聴く姿", self.listening_pose_label(listening)),
            ("理解", self.understanding_pose_label(understanding)),
        ]

    def intent_items(self):
        return [
            (label, self.intent_label(key))
            for label, key in self.INTENTS
        ]

    def filler_items(self):
        filler = self.profile_store.get_nested("filler", {}) or {}
        enabled = bool(filler.get("enabled", False))
        if not enabled:
            return [("フィラー", "入れない")]

        phrases = filler.get("phrases") or []
        phrase_label = "、".join(phrases) if phrases else "文言未設定"
        voice = self.voice_label(filler.get("voice", {}))
        return [("フィラー", f"入れる / 文言: {phrase_label} / 声色: {voice}")]

    def data_label(self, key):
        data = self.profile_store.get_nested(key, {}) or {}
        return data.get("label", data.get("id", "未設定"))

    def style_detail_label(self):
        detail = self.profile_store.get_nested("style_detail", {}) or {}
        labels = detail.get("labels", {})
        if not labels:
            return "未設定"
        return " / ".join(f"{key}: {value}" for key, value in labels.items())

    def special_consideration_label(self):
        data = self.profile_store.get_nested("special_consideration", {}) or {}
        text = (data.get("text") or "").strip()
        return text if text else "なし"

    def response_delay_label(self, delay):
        normal = delay.get("label", "未設定")
        thinking = delay.get("thinking_label", "未設定")
        return f"通常: {normal} / 考え中: {thinking}"

    def thinking_pose_label(self, data):
        return " / ".join(
            [
                f"表情: {self.face_label(data.get('face', {}))}",
                f"視線: {self.gaze_label(data.get('gaze', {}))}",
            ]
        )

    def listening_pose_label(self, data):
        return " / ".join(
            [
                f"表情: {self.face_label(data.get('face', {}))}",
                f"目: {self.eye_label(data.get('eye_open', {}))}",
                f"うなづき: {self.nod_label(data.get('nod', {}))}",
                f"相槌: {self.backchannel_label(data.get('backchannel_voice', {}))}",
                f"相槌量: {self.label_from(data.get('amount', {}))}",
            ]
        )

    def understanding_pose_label(self, data):
        return " / ".join(
            [
                f"表情: {self.face_label(data.get('face', {}))}",
                f"うなづき: {self.nod_label(data.get('nod', {}))}",
                f"言葉: {self.word_label(data.get('word', {}))}",
            ]
        )

    def intent_label(self, key):
        data = self.profile_store.get_nested(key, {}) or {}
        parts = [
            f"文: {data.get('text', '未設定')}",
            f"表情: {self.face_label(data.get('face', {}))}",
            f"声色: {self.voice_label(data.get('voice', {}))}",
            f"テクニック: {self.technique_label(data.get('techniques', []))}",
        ]
        bow = data.get("bow")
        if bow:
            parts.append(f"お辞儀: {self.bow_label(bow)}")
        return " / ".join(parts)

    def face_label(self, data):
        return self.label_from(data)

    def gaze_label(self, data):
        return self.label_from(data)

    def eye_label(self, data):
        return self.label_from(data) or data.get("id", "未設定")

    def nod_label(self, data):
        return self.label_from(data)

    def voice_label(self, data):
        return self.label_from(data)

    def bow_label(self, data):
        return self.label_from(data)

    def word_label(self, data):
        text = data.get("custom_text") or data.get("text")
        return text or self.label_from(data)

    def backchannel_label(self, data):
        mode = data.get("mode", "none")
        if mode == "none":
            return "なし"
        text = data.get("custom_text") or data.get("text") or data.get("word_id")
        return text or mode

    def technique_label(self, techniques):
        if not techniques:
            return "なし"
        return "、".join(techniques)

    def label_from(self, data):
        if not data:
            return "未設定"
        return data.get("label") or data.get("id") or data.get("type") or "未設定"

    def save_and_next(self):
        self.profile_store.save()
        self.status_var.set("設定確認を保存しました")
        if self.on_saved is not None:
            self.on_saved()
