import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from ..panels.face_editor_panel import FaceEditorPanel
from ..face_preset_store import load_face_presets

from .. import ui_style as ui
from ..config_face import (
    UNDERSTANDING_FACE_OPTIONS,
    UNDERSTANDING_FACE_PRIORITY,
    UNDERSTANDING_FACE_KEEPTIME,
    UNDERSTANDING_NOD_OPTIONS,
    UNDERSTANDING_NOD_PRIORITY,
    UNDERSTANDING_WORD_OPTIONS,
    UNDERSTANDING_SAMPLE_TEXT,
    UNDERSTANDING_RESPONSE_DELAY_FALLBACK_SEC,
    FACE_EDITOR_VELOCITY,
    FACE_EDITOR_PRIORITY,
    FACE_EDITOR_KEEPTIME,
)
from ..panels.mic_activity_panel import MicActivityPanel
from ..clients.robot_command_client import RobotCommandClient


class UnderstandingPoseTab(tk.Frame):
    def __init__(self, parent, profile_store, tts_client, status_var, on_saved=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved

        data = self.profile_store.get_nested("understanding_pose", {})

        face = data.get("face", {})
        self.face_presets = load_face_presets()

        initial_face_id = face.get("id", "reward_smile3")
        initial_custom_name = ""

        if face.get("custom") or initial_face_id.startswith("custom:"):
            initial_custom_name = face.get("type") or face.get("label", "")
            if initial_custom_name:
                initial_face_id = f"custom:{initial_custom_name}"

        if not initial_custom_name and self.face_presets:
            initial_custom_name = sorted(self.face_presets.keys())[0]

        self.selected_face = tk.StringVar(value=initial_face_id)
        self.custom_face_name = tk.StringVar(value=initial_custom_name)

        nod = data.get("nod", {})
        self.selected_nod = tk.StringVar(value=nod.get("id", "large_once"))

        word = data.get("word", {})
        self.selected_word_id = tk.StringVar(value=word.get("word_id", "hai"))
        self.custom_word_text = tk.StringVar(value=word.get("custom_text", ""))

        self.robot_client = RobotCommandClient()
        self.mic_panel = None
        self._understanding_stop = None
        self._understanding_thread = None

        self.build_main_view()

    def clear_views(self):
        for child in self.winfo_children():
            child.destroy()
    
    def build_main_view(self):
        self.clear_views()
        self.build_ui()


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
            text="理解した姿を選ぶ",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            page,
            text="相手の話を聞き終えたあとに、理解したことを表す表情・うなづき・言葉を調整します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(
            anchor="w",
            pady=(ui.SPACING["small_gap"], 0),
        )

        content = self.create_scrollable_content_area(page)

        self.build_face_area(content)
        self.build_nod_area(content)
        self.build_word_area(content)
        self.build_test_area(content)

        self.build_bottom_area(page)

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

        for opt in UNDERSTANDING_FACE_OPTIONS:
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
        else:
            ui.label(
                other_card,
                text="保存済みの表情はまだありません。",
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

        ui.sub_button(
            other_card,
            text="作成する",
            command=self.build_editor_view,
        ).pack(
            anchor="e",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
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


    def on_custom_face_saved(self, name, data):
        self.face_presets = load_face_presets()
        self.custom_face_name.set(name)

        opt = self.get_custom_face_option(name)
        self.selected_face.set(opt["id"])

        self.save_selection_only(update_status=True)

    def on_face_selected(self, opt):
        try:
            self.robot_client.send_emotion(
                face_type=opt["type"],
                level=int(opt["level"]),
                priority=UNDERSTANDING_FACE_PRIORITY,
                keeptime=UNDERSTANDING_FACE_KEEPTIME,
            )
            self.save_selection_only(update_status=False)
            self.status_var.set(f"理解した表情を送信しました: {opt['label']}")
        except Exception as e:
            messagebox.showerror("送信エラー", str(e))

    # =========================
    # うなづき
    # =========================

    def build_nod_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(
            section,
            text="うなづき",
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
            ).pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["compact_y"]),
            )

    def on_nod_selected(self, opt):
        self.send_understanding_nod(opt)
        self.save_selection_only(update_status=False)

    # =========================
    # 言葉
    # =========================

    def build_word_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(
            section,
            text="言葉",
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

        word_row = ui.frame(card, bg="card")
        word_row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["compact_y"]),
        )

        for opt in UNDERSTANDING_WORD_OPTIONS:
            if opt["id"] == "other":
                continue

            ui.radio(
                word_row,
                text=opt["label"],
                variable=self.selected_word_id,
                value=opt["id"],
                command=lambda item=opt: self.on_word_selected(item),
                bg="card",
            ).pack(side="left", padx=(0, ui.SPACING["gap"]))

        other_row = ui.frame(card, bg="card")
        other_row.pack(
            fill="x",
            padx=ui.SPACING["card_x"],
            pady=(0, ui.SPACING["compact_y"]),
        )

        ui.radio(
            other_row,
            text="その他",
            variable=self.selected_word_id,
            value="other",
            command=lambda: self.save_selection_only(update_status=False),
            bg="card",
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))

        ui.entry(
            other_row,
            textvariable=self.custom_word_text,
            font="input",
        ).pack(side="left", fill="x", expand=True, ipady=4)

        ui.sub_button(
            other_row,
            text="TTSで作成して再生",
            command=self.speak_custom_word,
        ).pack(side="right", padx=(ui.SPACING["small_gap"], 0))

    def on_word_selected(self, opt):
        self.selected_word_id.set(opt["id"])
        self.save_selection_only(update_status=False)

        if opt["type"] == "wav":
            try:
                self.tts_client.play_preview_wav(opt["wav_path"])
                self.status_var.set(f"理解した言葉を再生しました: {opt['text']}")
            except Exception as e:
                messagebox.showerror("再生エラー", str(e))

    def speak_custom_word(self):
        text = self.custom_word_text.get().strip()

        if not text:
            messagebox.showwarning("確認", "その他の言葉を入力してください。")
            return

        self.selected_word_id.set("other")
        self.save_selection_only(update_status=False)

        try:
            self.tts_client.speak_current_speaker(text=text)
            self.status_var.set(f"その他の言葉をTTSで再生しました: {text}")
        except Exception as e:
            messagebox.showerror("TTSエラー", str(e))

    # =========================
    # マイクテスト
    # =========================

    def build_test_area(self, parent):
        self.mic_panel = MicActivityPanel(
            parent,
            title="理解した姿のテスト",
            description=(
                "下の文を声に出して読んでください。"
                "話し終わったあと、返答の間で設定したタイミングで理解した姿を出します。"
            ),
            sample_text=UNDERSTANDING_SAMPLE_TEXT,
            on_speech_start=self.on_user_speech_start,
            on_speech_end=self.on_user_speech_end,
            status_var=self.status_var,
        )
        self.mic_panel.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

    def on_user_speech_start(self, _t):
        self.apply_listening_pose()
        if self.mic_panel is not None:
            self.mic_panel.set_result("聴いている姿")

    def on_user_speech_end(self, _t):
        if self.mic_panel is not None:
            self.mic_panel.set_result("認識完了")
            self.mic_panel.set_state("理解待ち")

        wait_sec = self.get_response_delay_wait_sec()
        word_duration = self.get_understanding_word_duration_sec()
        buffer_sec = 0.15

        self.mic_panel.pause_for(
                wait_sec + word_duration + buffer_sec,
                label="理解表現待ち/再生中",
            )

        self.schedule_understanding_pose(wait_sec)

        

    def get_response_delay_wait_sec(self):
        delay_data = self.profile_store.get_nested("response_delay", {})
        return float(
            delay_data.get(
                "wait_after_detection",
                UNDERSTANDING_RESPONSE_DELAY_FALLBACK_SEC,
            )
        )
    
    def get_understanding_word_duration_sec(self):
        word = self.find_word_option()

        if word["id"] == "other":
            text = self.custom_word_text.get().strip()
            if not text:
                return 0.0

            return UNDERSTANDING_RESPONSE_DELAY_FALLBACK_SEC

        if word["type"] == "wav":
            try:
                return self.tts_client.get_wav_duration_sec(word["wav_path"])
            except Exception:
                return UNDERSTANDING_RESPONSE_DELAY_FALLBACK_SEC

        return 0.0

    # =========================
    # 実行処理
    # =========================

    def schedule_understanding_pose(self, wait_sec):
        self.cancel_scheduled_understanding_pose()
        stop_event = threading.Event()
        self._understanding_stop = stop_event
        self._understanding_thread = threading.Thread(
            target=self._understanding_pose_worker,
            args=(float(wait_sec), stop_event),
            daemon=True,
        )
        self._understanding_thread.start()

    def cancel_scheduled_understanding_pose(self):
        if self._understanding_stop is not None:
            self._understanding_stop.set()

    def _understanding_pose_worker(self, wait_sec, stop_event):
        start = time.monotonic()
        while time.monotonic() - start < wait_sec:
            if stop_event.is_set():
                return
            time.sleep(0.01)

        if stop_event.is_set():
            return

        self.play_understanding_pose(update_ui=False)

        if self.mic_panel is not None:
            self.mic_panel.set_result_threadsafe("理解表現")

    def play_understanding_pose(self, update_ui=True):
        face = self.find_face_option()
        word = self.find_word_option()
        nod = self.find_nod_option()

        try:
            self.robot_client.send_emotion(
                face_type=face["type"],
                level=int(face["level"]),
                priority=UNDERSTANDING_FACE_PRIORITY,
                keeptime=UNDERSTANDING_FACE_KEEPTIME,
            )

            self.send_understanding_nod(nod)
            self.play_understanding_word(word)

            if update_ui and self.mic_panel is not None:
                self.mic_panel.set_result("理解表現")

            if update_ui:
                self.status_var.set("理解した姿を再生しました")

        except Exception as e:
            if update_ui:
                self.status_var.set(f"理解した姿の再生エラー: {e}")
            elif self.mic_panel is not None:
                self.mic_panel.set_result_threadsafe(f"再生エラー: {e}")

    def send_understanding_nod(self, nod):
        self.robot_client.send_nod(
                amplitude=int(nod["amplitude"]),
                duration=int(nod["duration"]),
                times=int(nod["count"]),
                priority=UNDERSTANDING_NOD_PRIORITY,
            )

    def play_understanding_word(self, word):
        if word["id"] == "other":
            text = self.custom_word_text.get().strip()
            if text:
                self.tts_client.speak_current_speaker(text=text)
            return

        if word["type"] == "wav":
            self.tts_client.play_preview_wav(word["wav_path"])

    def apply_listening_pose(self):
        listening = self.profile_store.get_nested("listening_pose", {})

        face = listening.get("face", {})
        if face:
            self.robot_client.send_emotion(
                face_type=face["type"],
                level=int(face["level"]),
                priority=UNDERSTANDING_FACE_PRIORITY,
                keeptime=UNDERSTANDING_FACE_KEEPTIME,
            )

        eye = listening.get("eye_open", {})
        axes = eye.get("axes", {})
        if axes:
            self.robot_client.send_face_axes(
                axes=axes,
                velocity=FACE_EDITOR_VELOCITY,
                priority=FACE_EDITOR_PRIORITY,
                keeptime=FACE_EDITOR_KEEPTIME,
            )

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

        for opt in UNDERSTANDING_FACE_OPTIONS:
            if opt["id"] == selected_id:
                return opt

        if selected_id.startswith("custom:"):
            name = selected_id.replace("custom:", "", 1)
            custom = self.get_custom_face_option(name)
            if custom is not None:
                return custom

        return UNDERSTANDING_FACE_OPTIONS[1]

    def find_nod_option(self):
        for opt in UNDERSTANDING_NOD_OPTIONS:
            if opt["id"] == self.selected_nod.get():
                return opt

        return UNDERSTANDING_NOD_OPTIONS[0]

    def find_word_option(self):
        selected_id = self.selected_word_id.get()

        for opt in UNDERSTANDING_WORD_OPTIONS:
            if opt["id"] == selected_id:
                return opt

        return UNDERSTANDING_WORD_OPTIONS[0]

    def get_word_data(self):
        word = self.find_word_option()

        if word["id"] == "other":
            text = self.custom_word_text.get().strip()
            return {
                "word_id": "other",
                "word_type": "tts",
                "text": text,
                "custom_text": text,
                "wav_path": None,
            }

        return {
            "word_id": word["id"],
            "word_type": word["type"],
            "text": word["text"],
            "custom_text": self.custom_word_text.get().strip(),
            "wav_path": str(word["wav_path"]),
        }

    def get_current_data(self):
        face = self.find_face_option()
        nod = self.find_nod_option()

        return {
            "face": {
                "id": face["id"],
                "label": face["label"],
                "type": face["type"],
                "level": int(face["level"]),
                **({"custom": True} if face.get("custom") else {}),
            },
            "nod": {
                "id": nod["id"],
                "label": nod["label"],
                "amplitude": int(nod["amplitude"]),
                "duration": int(nod["duration"]),
                "count": int(nod["count"]),
                "priority": UNDERSTANDING_NOD_PRIORITY,
            },
            "word": self.get_word_data(),
            "response_delay_source": "response_delay.wait_after_detection",
            "description": "相手の発話を理解した直後に出す表情・うなづき・短い言葉",
        }

    def save_selection_only(self, update_status=True):
        self.profile_store.set(
            "understanding_pose",
            self.get_current_data(),
            auto_save=True,
        )

        if update_status:
            self.status_var.set("理解した姿を保存しました")

    def save_and_next(self):
        self.save_selection_only()

        if self.on_saved is not None:
            self.on_saved()

    def destroy(self):
        self.cancel_scheduled_understanding_pose()

        try:
            if self.mic_panel is not None:
                self.mic_panel.stop()
        except Exception:
            pass

        try:
            self.robot_client.close()
        except Exception:
            pass

        super().destroy()
