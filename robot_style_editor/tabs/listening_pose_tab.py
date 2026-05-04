import tkinter as tk
from tkinter import ttk, messagebox
import time
import random
import wave

from ..config import MIC_VOLUME_END_THRESHOLD_DEFAULT


from ..config_face import (
    LISTENING_FACE_OPTIONS,
    LISTENING_FACE_PRIORITY,
    LISTENING_FACE_KEEPTIME,
    LISTENING_EYE_OPEN_DEFAULTS,
    LISTENING_NOD_OPTIONS,
    LISTENING_NOD_PRIORITY,
    LISTENING_NOD_TIME,
    LISTENING_BACKCHANNEL_AMOUNT_OPTIONS,
    FACE_EDITOR_VELOCITY,
    FACE_EDITOR_PRIORITY,
    FACE_EDITOR_KEEPTIME,
    LISTENING_BACKCHANNEL_VOICE_MODE_OPTIONS,
    LISTENING_BACKCHANNEL_VOICE_PROBABILITY_DEFAULT,
    LISTENING_BACKCHANNEL_SILENCE_HOLD_SEC_DEFAULT,
    LISTENING_BACKCHANNEL_START_HOLD_SEC_DEFAULT,
    LISTENING_BACKCHANNEL_WORD_OPTIONS,
)
from ..panels.face_editor_panel import FaceEditorPanel
from ..face_preset_store import load_face_presets
from ..clients.robot_command_client import RobotCommandClient
from ..panels.mic_activity_panel import MicActivityPanel
from .. import ui_style as ui


class ListeningPoseTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        listening = self.profile_store.get_nested("listening_pose", {})

        self.face_presets = load_face_presets()

        face = listening.get("face", {})
        self.selected_face = tk.StringVar(value=face.get("id", "neutral"))
        self.custom_face_name = tk.StringVar(value=face.get("type", ""))

        eye = listening.get("eye_open", {})
        self.eye_open_mode = tk.StringVar(value=eye.get("id", "normal"))
        

        self.left_upper = tk.IntVar(value=int(eye.get("left_upper", LISTENING_EYE_OPEN_DEFAULTS["normal"]["left_upper"])))
        self.left_lower = tk.IntVar(value=int(eye.get("left_lower", LISTENING_EYE_OPEN_DEFAULTS["normal"]["left_lower"])))
        self.right_upper = tk.IntVar(value=int(eye.get("right_upper", LISTENING_EYE_OPEN_DEFAULTS["normal"]["right_upper"])))
        self.right_lower = tk.IntVar(value=int(eye.get("right_lower", LISTENING_EYE_OPEN_DEFAULTS["normal"]["right_lower"])))

        self.upper_eye = tk.IntVar(
            value=int(eye.get("left_upper", LISTENING_EYE_OPEN_DEFAULTS["normal"]["left_upper"]))
        )
        self.lower_eye = tk.IntVar(
            value=int(eye.get("left_lower", LISTENING_EYE_OPEN_DEFAULTS["normal"]["left_lower"]))
        )

        self.left_upper.set(self.upper_eye.get())
        self.right_upper.set(self.upper_eye.get())
        self.left_lower.set(self.lower_eye.get())
        self.right_lower.set(self.lower_eye.get())

        nod = listening.get("nod", {})
        self.selected_nod = tk.StringVar(value=nod.get("id", "middle"))

        voice = listening.get("backchannel_voice", {})

        self.voice_mode = tk.StringVar(
            value=voice.get("mode", "sometimes")
        )

        self.voice_probability = tk.DoubleVar(
            value=float(
                voice.get(
                    "probability",
                    LISTENING_BACKCHANNEL_VOICE_PROBABILITY_DEFAULT,
                )
            )
        )

        self.voice_probability_label = tk.StringVar(
            value=self.format_probability(self.voice_probability.get())
        )

        self.selected_word_id = tk.StringVar(
            value=voice.get("word_id", "hai")
        )

        self.custom_word_text = tk.StringVar(
            value=voice.get("custom_text", "")
        )

        amount = listening.get("amount", {})
        self.selected_amount = tk.StringVar(value=amount.get("id", "middle"))

        self.robot_client = RobotCommandClient()

        self.current_silence_start_t = None
        self.backchannel_active = False
        self.last_backchannel_t = 0.0
        self.backchannel_mic_panel = None

        self.build_main_view()

    def clear_views(self):
        for child in self.winfo_children():
            child.destroy()

    def create_scrollable_content_area(self, parent):
        outer = ui.frame(parent, bg="main_card")
        outer.pack(
            fill="both",
            expand=True,
            pady=(ui.SPACING["section_y"], 0),
        )

        canvas = tk.Canvas(
            outer,
            bg=ui.COLORS["main_card"],
            highlightthickness=0,
            bd=0,
        )
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = tk.Scrollbar(
            outer,
            orient="vertical",
            command=canvas.yview,
        )
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)

        content = ui.frame(canvas, bg="main_card")

        canvas_window = canvas.create_window(
            (0, 0),
            window=content,
            anchor="nw",
        )

        def on_content_configure(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def on_canvas_configure(event):
            canvas.itemconfig(canvas_window, width=event.width)

        content.bind("<Configure>", on_content_configure)
        canvas.bind("<Configure>", on_canvas_configure)

        def on_mousewheel(event):
            if event.delta > 0:
                canvas.yview_scroll(-1, "units")
            elif event.delta < 0:
                canvas.yview_scroll(1, "units")

        def bind_mousewheel(_event=None):
            canvas.bind_all("<MouseWheel>", on_mousewheel)

        def unbind_mousewheel(_event=None):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", bind_mousewheel)
        canvas.bind("<Leave>", unbind_mousewheel)

        return content
            

    def build_main_view(self):
        self.clear_views()

        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )

        # =========================
        # 固定：タイトル
        # =========================
        ui.label(
            page,
            text="聴いている姿を選ぶ",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            page,
            text="相手の話を聴いている間の表情、目の開き、相槌の出し方を調整します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(
            anchor="w",
            pady=(ui.SPACING["small_gap"], 0),
        )

        # =========================
        # スクロール：設定部分だけ
        # =========================
        content = self.create_scrollable_content_area(page)

        self.build_face_area(content)
        self.build_eye_area(content)
        self.build_nod_area(content)
        self.build_word_area(content)
        self.build_amount_area(content)
        self.build_backchannel_test_area(content)

        # =========================
        # 固定：保存ボタン
        # =========================
        self.build_bottom_area(page)

    def build_editor_view(self):
        self.clear_views()

        editor = FaceEditorPanel(
            self,
            robot_client=self.robot_client,
            on_back=self.build_main_view,
            on_saved=self.on_custom_face_saved,
        )
        editor.pack(fill="both", expand=True)

    # =========================
    # 表情
    # =========================

    def build_face_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

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
        row.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["section_y"]),
        )

        for opt in LISTENING_FACE_OPTIONS:
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
            ).pack(
                anchor="w",
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

        preset_names = sorted(self.face_presets.keys())

        if preset_names:
            if self.custom_face_name.get() not in preset_names:
                self.custom_face_name.set(preset_names[0])

            combo = ttk.Combobox(
                other_card,
                values=preset_names,
                textvariable=self.custom_face_name,
                width=18,
                state="readonly",
            )
            combo.pack(
                fill="x",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["compact_y"]),
            )

            combo.bind(
                "<<ComboboxSelected>>",
                lambda _event=None: self.on_custom_face_selected(),
            )

            ui.sub_button(
                other_card,
                text="この表情を使う",
                command=self.on_custom_face_selected,
            ).pack(
                anchor="e",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["compact_y"]),
            )

        ui.sub_button(
            other_card,
            text="作成する",
            command=self.build_editor_view,
        ).pack(
            anchor="e",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

    def on_face_selected(self, opt):
        try:
            self.robot_client.send_emotion(
                face_type=opt["type"],
                level=int(opt["level"]),
                priority=LISTENING_FACE_PRIORITY,
                keeptime=LISTENING_FACE_KEEPTIME,
            )
            self.save_selection_only(update_status=False)
            self.status_var.set(f"聴いている表情を送信しました: {opt['label']}")
        except Exception as e:
            messagebox.showerror("送信エラー", str(e))

    def infer_custom_face_level(self, name):
        if name and name[-1].isdigit():
            v = int(name[-1])
            if v in (1, 2, 3):
                return v
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

    def on_custom_face_saved(self, name, data):
        self.face_presets = load_face_presets()
        self.custom_face_name.set(name)
        opt = self.get_custom_face_option(name)
        self.selected_face.set(opt["id"])
        self.save_selection_only(update_status=True)

    # =========================
    # 目の開き度合い
    # =========================

    def build_eye_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(
            section,
            text="目の開き度合い",
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

        normal = LISTENING_EYE_OPEN_DEFAULTS["normal"]

        normal_card = ui.bordered_frame(row, bg="card", border="border")
        normal_card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=ui.SPACING["small_gap"],
            pady=ui.SPACING["small_gap"],
        )

        ui.radio(
            normal_card,
            text=normal["label"],
            variable=self.eye_open_mode,
            value=normal["id"],
            command=lambda: self.apply_eye_preset(normal),
            bg="card",
        ).pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )

        ui.label(
            normal_card,
            text="標準の目の開きにします。",
            font="small",
            bg="card",
            fg="muted",
        ).pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

        open_default = LISTENING_EYE_OPEN_DEFAULTS["open"]

        open_card = ui.bordered_frame(row, bg="card", border="border")
        open_card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=ui.SPACING["small_gap"],
            pady=ui.SPACING["small_gap"],
        )

        header = ui.frame(open_card, bg="card")
        header.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )

        ui.radio(
            header,
            text=open_default["label"],
            variable=self.eye_open_mode,
            value=open_default["id"],
            command=self.apply_open_eye_from_sliders,
            bg="card",
        ).pack(side="left")

        ui.label(
            header,
            text="左右連動",
            font="small",
            bg="card",
            fg="muted",
        ).pack(side="right")

        self.build_eye_linked_slider(
            open_card,
            label_text="上瞼 1・2",
            variable=self.upper_eye,
        )

        self.build_eye_linked_slider(
            open_card,
            label_text="下瞼 6・7",
            variable=self.lower_eye,
        )

    def build_eye_linked_slider(self, parent, label_text, variable):
        row = ui.frame(parent, bg="card")
        row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

        ui.label(
            row,
            text=label_text,
            font="small",
            bg="card",
            fg="sub_text",
        ).pack(side="left")

        value_text = tk.StringVar(value=str(variable.get()))

        ui.variable_label(
            row,
            textvariable=value_text,
            font="small",
            bg="card",
            fg="text",
        ).pack(side="right")

        def on_changed(_value):
            value = int(float(variable.get()))
            value_text.set(str(value))

            # スライダーを触ったら「開く」扱いにする
            self.eye_open_mode.set("open")

            self.sync_eye_axes_from_linked_values()
            self.send_eye_axes()
            self.save_selection_only(update_status=False)

        ui.scale(
            row,
            variable=variable,
            from_=0,
            to=255,
            command=on_changed,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=ui.SPACING["small_gap"],
        )

    def sync_eye_axes_from_linked_values(self):
        upper = int(self.upper_eye.get())
        lower = int(self.lower_eye.get())

        self.left_upper.set(upper)
        self.right_upper.set(upper)
        self.left_lower.set(lower)
        self.right_lower.set(lower)

    def apply_eye_preset(self, opt):
        self.eye_open_mode.set(opt["id"])

        upper = int(opt["left_upper"])
        lower = int(opt["left_lower"])

        self.upper_eye.set(upper)
        self.lower_eye.set(lower)

        self.left_upper.set(upper)
        self.right_upper.set(upper)
        self.left_lower.set(lower)
        self.right_lower.set(lower)

        self.send_eye_axes()
        self.save_selection_only(update_status=False)

    def apply_open_eye_from_sliders(self):
        self.eye_open_mode.set("open")
        self.sync_eye_axes_from_linked_values()
        self.send_eye_axes()
        self.save_selection_only(update_status=False)

    def send_eye_axes(self):
        try:
            axes = {
                "1": int(self.left_upper.get()),
                "6": int(self.left_lower.get()),
                "2": int(self.right_upper.get()),
                "7": int(self.right_lower.get()),
            }
            self.robot_client.send_face_axes(
                axes=axes,
                velocity=FACE_EDITOR_VELOCITY,
                priority=FACE_EDITOR_PRIORITY,
                keeptime=FACE_EDITOR_KEEPTIME,
            )
        except Exception as e:
            self.status_var.set(f"目の開き送信エラー: {e}")

    # =========================
    # 相槌：うなづき
    # =========================

    def build_nod_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(
            section,
            text="相槌：うなづき",
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

        for opt in LISTENING_NOD_OPTIONS:
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

            if opt["id"] == "none":
                text = "うなづかない"
            else:
                text = f"/nod {opt['amplitude']} {opt['duration']} {LISTENING_NOD_TIME} {LISTENING_NOD_PRIORITY}"

            ui.label(
                card,
                text=text,
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

    def on_nod_selected(self, opt):
        if opt["id"] == "none":
            self.save_selection_only(update_status=False)
            return

        try:
            self.robot_client.send_nod(
                amplitude=int(opt["amplitude"]),
                duration=int(opt["duration"]),
                times=LISTENING_NOD_TIME,
                priority=LISTENING_NOD_PRIORITY,
            )
            self.save_selection_only(update_status=False)
            self.status_var.set(f"うなづきを送信しました: {opt['label']}")
        except Exception as e:
            messagebox.showerror("送信エラー", str(e))

    # =========================
    # 相槌：言葉
    # =========================

    def build_word_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(
            section,
            text="相槌：言葉",
            font="section_title",
            bg="panel",
        ).pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        mode_row = ui.frame(section, bg="panel")
        mode_row.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["small_gap"]),
        )

        for opt in LISTENING_BACKCHANNEL_VOICE_MODE_OPTIONS:
            card = ui.bordered_frame(mode_row, bg="card", border="border")
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
                variable=self.voice_mode,
                value=opt["id"],
                command=lambda: self.save_selection_only(update_status=False),
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

            if opt["id"] == "sometimes":
                self.build_voice_probability_slider(card)

        word_card = ui.bordered_frame(section, bg="card", border="border")
        word_card.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=(0, ui.SPACING["section_y"]),
        )

        ui.label(
            word_card,
            text="発声する言葉",
            font="body_bold",
            bg="card",
            fg="text",
        ).pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )

        word_row = ui.frame(word_card, bg="card")
        word_row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

        for opt in LISTENING_BACKCHANNEL_WORD_OPTIONS:
            if opt["id"] == "other":
                continue

            ui.radio(
                word_row,
                text=opt["label"],
                variable=self.selected_word_id,
                value=opt["id"],
                command=lambda item=opt: self.on_backchannel_word_selected(item),
                bg="card",
            ).pack(side="left", padx=(0, ui.SPACING["gap"]))

        ui.radio(
            word_row,
            text="その他",
            variable=self.selected_word_id,
            value="other",
            command=lambda: self.save_selection_only(update_status=False),
            bg="card",
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))

        ui.entry(
            word_row,
            textvariable=self.custom_word_text,
            font="input",
        ).pack(side="left", fill="x", expand=True, ipady=4)

        ui.sub_button(
            word_row,
            text="TTSで作成して再生",
            command=self.speak_custom_backchannel_word,
        ).pack(side="right", padx=(ui.SPACING["small_gap"], 0))

    def build_voice_probability_slider(self, parent):
        row = ui.frame(parent, bg="card")
        row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

        ui.label(
            row,
            text="発声割合",
            font="small",
            bg="card",
            fg="sub_text",
        ).pack(side="left")

        ui.variable_label(
            row,
            textvariable=self.voice_probability_label,
            font="small",
            bg="card",
            fg="text",
        ).pack(side="right")

        def on_changed(value):
            self.voice_probability_label.set(
                self.format_probability(float(value))
            )
            self.voice_mode.set("sometimes")
            self.save_selection_only(update_status=False)

        ui.scale(
            row,
            variable=self.voice_probability,
            from_=0.0,
            to=1.0,
            command=on_changed,
        ).pack(
            side="left",
            fill="x",
            expand=True,
            padx=ui.SPACING["small_gap"],
        )

    def format_probability(self, value):
        return f"{int(round(float(value) * 100))}%"
    
    def find_word_option(self):
        selected_id = self.selected_word_id.get()

        for opt in LISTENING_BACKCHANNEL_WORD_OPTIONS:
            if opt["id"] == selected_id:
                return opt

        return LISTENING_BACKCHANNEL_WORD_OPTIONS[1]
    
    def on_backchannel_word_selected(self, opt):
        self.selected_word_id.set(opt["id"])
        self.save_selection_only(update_status=False)

        if opt["type"] == "wav":
            try:
                self.tts_client.play_preview_wav(opt["wav_path"])
                self.status_var.set(f"相槌音声を再生しました: {opt['text']}")
            except Exception as e:
                messagebox.showerror("再生エラー", str(e))
                self.status_var.set(f"再生エラー: {e}")

    def speak_custom_backchannel_word(self):
        text = self.custom_word_text.get().strip()

        if not text:
            messagebox.showwarning("確認", "その他の言葉を入力してください。")
            return

        self.selected_word_id.set("other")
        self.save_selection_only(update_status=False)

        try:
            self.tts_client.speak_current_speaker(text=text)
            self.status_var.set(f"その他の相槌をTTSで再生しました: {text}")
        except Exception as e:
            messagebox.showerror("TTSエラー", str(e))
            self.status_var.set(f"TTSエラー: {e}")

    # =========================
    # 相槌：量
    # =========================

    def build_amount_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(
            section,
            text="相槌：量",
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

        for opt in LISTENING_BACKCHANNEL_AMOUNT_OPTIONS:
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
                variable=self.selected_amount,
                value=opt["id"],
                command=lambda: self.save_selection_only(update_status=False),
                bg="card",
            ).pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
            )

            ui.label(
                card,
                text=f"{opt['silence_sec']}秒程度の沈黙で相槌",
                font="small",
                bg="card",
                fg="muted",
            ).pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["compact_y"]),
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

    # =========================
    # 相槌：テスト
    # =========================

    def build_backchannel_test_area(self, parent):
        self.backchannel_mic_panel = MicActivityPanel(
            parent,
            title="相槌のテスト",
            description=(
                "下の文を声に出して読んでください。"
                "短い沈黙を検出したら、設定中のうなづき・音声相槌を試します。"
                "句点や読点で区切ると、より相槌が入りやすくなります。"
            ),
            sample_text=(
                "新しいセットアップを試したいなと思っているんですけど、"
                "何か最近流行りのものはありますか"
            ),
            on_speech_start=self.on_backchannel_speech_start,
            on_speech_end=self.on_backchannel_speech_end,
            on_volume_update=self.on_backchannel_volume_update,
            status_var=self.status_var,
            start_hold_sec=LISTENING_BACKCHANNEL_START_HOLD_SEC_DEFAULT,
            silence_hold_sec=LISTENING_BACKCHANNEL_SILENCE_HOLD_SEC_DEFAULT,
        )
        self.backchannel_mic_panel.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

    def on_backchannel_volume_update(self, volume, speaking):
        self.check_backchannel_timing(volume, speaking)

    def on_backchannel_speech_start(self, _t):
        self.current_silence_start_t = None
        self.backchannel_active = False

        if self.backchannel_mic_panel is not None:
            self.backchannel_mic_panel.set_result("")

    def on_backchannel_speech_end(self, _t):
        self.current_silence_start_t = None
        self.backchannel_active = False

    def get_wav_duration_sec(self, wav_path):
        with wave.open(str(wav_path), "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()

        return frames / float(rate)


    def check_backchannel_timing(self, volume, speaking):
        if not speaking:
            self.current_silence_start_t = None
            self.backchannel_active = False
            return

        now = time.monotonic()
        silence_sec = float(self.find_amount_option()["silence_sec"])

        is_silent = volume < MIC_VOLUME_END_THRESHOLD_DEFAULT

        if not is_silent:
            self.current_silence_start_t = None
            self.backchannel_active = False
            return

        if self.current_silence_start_t is None:
            self.current_silence_start_t = now
            return

        silence_duration = now - self.current_silence_start_t

        if silence_duration < silence_sec:
            return

        if self.backchannel_active:
            return

        self.trigger_backchannel_preview()
        self.backchannel_active = True
        self.last_backchannel_t = now


    def trigger_backchannel_preview(self):
        if self.backchannel_mic_panel is not None:
            self.backchannel_mic_panel.set_result("相槌")

        self.play_selected_nod()
        self.play_selected_backchannel_voice()

        self.status_var.set("相槌を試しました")


    def play_selected_nod(self):
        nod = self.find_nod_option()

        if nod["id"] == "none":
            return

        try:
            self.robot_client.send_nod(
                amplitude=int(nod["amplitude"]),
                duration=int(nod["duration"]),
                times=LISTENING_NOD_TIME,
                priority=LISTENING_NOD_PRIORITY,
            )
        except Exception as e:
            self.status_var.set(f"うなづき送信エラー: {e}")


    def play_selected_backchannel_voice(self):
        voice = self.get_backchannel_voice_data()

        probability = float(voice["effective_probability"])

        if probability <= 0.0:
            return

        if random.random() > probability:
            return

        try:
            if voice["word_type"] == "wav":
                wav_path = voice["wav_path"]

                duration = self.tts_client.play_preview_wav_trimmed_and_get_duration(wav_path)
                self.backchannel_mic_panel.pause_for(duration + 0.15, label="相槌再生中")

            else:
                text = voice["text"].strip()
                if not text:
                    return

                if self.backchannel_mic_panel is not None:
                    self.backchannel_mic_panel.pause_for(
                        1.2,
                        label="相槌再生中",
                    )

                self.tts_client.speak_current_speaker(text=text)

        except Exception as e:
            self.status_var.set(f"相槌音声エラー: {e}")

    # =========================
    # 保存
    # =========================

    def build_bottom_area(self, parent):
        bottom = ui.frame(parent, bg="main_card")
        bottom.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.action_button(
            bottom,
            text="保存して次へ",
            command=self.save_and_next,
        ).pack(side="right")

    def find_face_option(self):
        selected_id = self.selected_face.get()

        for opt in LISTENING_FACE_OPTIONS:
            if opt["id"] == selected_id:
                return opt

        if selected_id.startswith("custom:"):
            return self.get_custom_face_option(
                selected_id.replace("custom:", "", 1)
            )

        return LISTENING_FACE_OPTIONS[0]

    def find_nod_option(self):
        for opt in LISTENING_NOD_OPTIONS:
            if opt["id"] == self.selected_nod.get():
                return opt
        return LISTENING_NOD_OPTIONS[2]

    def find_amount_option(self):
        for opt in LISTENING_BACKCHANNEL_AMOUNT_OPTIONS:
            if opt["id"] == self.selected_amount.get():
                return opt
        return LISTENING_BACKCHANNEL_AMOUNT_OPTIONS[1]

    def get_current_data(self):
        face = self.find_face_option()
        nod = self.find_nod_option()
        amount = self.find_amount_option()

        return {
            "face": {
                "id": face["id"],
                "label": face["label"],
                "type": face["type"],
                "level": int(face["level"]),
                **({"custom": True} if face.get("custom") else {}),
            },
            "eye_open": {
                "id": self.eye_open_mode.get(),
                "left_upper": int(self.left_upper.get()),
                "left_lower": int(self.left_lower.get()),
                "right_upper": int(self.right_upper.get()),
                "right_lower": int(self.right_lower.get()),
                "axes": {
                    "1": int(self.left_upper.get()),
                    "6": int(self.left_lower.get()),
                    "2": int(self.right_upper.get()),
                    "7": int(self.right_lower.get()),
                },
            },
            "nod": {
                "id": nod["id"],
                "label": nod["label"],
                "amplitude": int(nod["amplitude"]),
                "duration": int(nod["duration"]),
                "times": LISTENING_NOD_TIME,
                "priority": LISTENING_NOD_PRIORITY,
            },
            "backchannel_voice": self.get_backchannel_voice_data(),
            "amount": {
                "id": amount["id"],
                "label": amount["label"],
                "silence_sec": float(amount["silence_sec"]),
                "description": amount["description"],
            },
            "description": "ロボットが相手の話を聴いている間の表情・目の開き・相槌設定",
        }

    def save_selection_only(self, update_status=True):
        self.profile_store.set(
            "listening_pose",
            self.get_current_data(),
            auto_save=True,
        )

        if update_status:
            self.status_var.set("聴いている姿を保存しました")

    def get_backchannel_voice_data(self):
        mode = self.voice_mode.get()
        probability = round(float(self.voice_probability.get()), 2)
        word = self.find_word_option()

        if mode == "always":
            effective_probability = 1.0
        elif mode == "none":
            effective_probability = 0.0
        else:
            effective_probability = probability

        if word["id"] == "other":
            text = self.custom_word_text.get().strip()

            return {
                "mode": mode,
                "probability": probability,
                "effective_probability": effective_probability,
                "word_id": "other",
                "word_type": "tts",
                "text": text,
                "custom_text": text,
                "wav_path": None,
                "description": "うなづき時に、指定割合でTTS生成した相槌を再生する",
            }

        return {
            "mode": mode,
            "probability": probability,
            "effective_probability": effective_probability,
            "word_id": word["id"],
            "word_type": "wav",
            "text": word["text"],
            "custom_text": self.custom_word_text.get().strip(),
            "wav_path": str(word["wav_path"]),
            "description": "うなづき時に、指定割合で既存WAVの相槌を再生する",
        }

    def save_and_next(self):
        self.save_selection_only()

        if self.on_saved is not None:
            self.on_saved()

    def destroy(self):
        try:
            if self.backchannel_mic_panel is not None:
                self.backchannel_mic_panel.stop()
        except Exception:
            pass

        try:
            self.robot_client.close()
        except Exception:
            pass

        super().destroy()