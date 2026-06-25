from pathlib import Path
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from . import ui_style as ui
from .config import (
    FACE_EXPRESSION_OPTIONS,
    SAVE_DIR,
    SCENARIO_OPTIONS,
    SMILE_COMPATIBLE_EMOTIONS,
    default_face_data,
    default_voice_data,
    face_axis_commands,
)
from .panels.face_axis_editor_panel import FaceAxisEditorPanel
from .panels.voice_editor_panel import VoiceEditorPanel
from .scenario_store import ScenarioStore
from .tabs.editor_tab import ConversationEditorTab
from .tabs.robot_run_tab import RobotRunTab
from ..robot_style_editor.config import (
    MIC_SILENCE_HOLD_SEC_DEFAULT,
    apply_robot_command_environment,
    apply_robot_tts_environment,
    get_default_mic_activity_mode,
    get_robot_tcp_config,
    get_robot_tts_play_url,
    get_tts_engine,
    get_tts_playback_target,
    set_mic_activity_mode,
    set_tts_engine,
    set_tts_playback_target,
)


PRIMARY_SCENARIO_IDS = ("direction_guidance", "housework")


class ConversationToolApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("接客会話編集ツール")
        self.geometry(self.initial_geometry())
        self.minsize(980, 620)

        ui.apply_app_style(self)

        self.status_var = tk.StringVar(value="ユーザー名を入力してください")
        self.tts_playback_var = tk.StringVar(value=get_tts_playback_target())
        self.tts_engine_var = tk.StringVar(value=get_tts_engine())
        self.mic_activity_var = tk.StringVar(value=get_default_mic_activity_mode())
        self.mic_silence_hold_var = tk.DoubleVar(value=float(MIC_SILENCE_HOLD_SEC_DEFAULT))
        self.apply_initial_runtime_choices()
        self.new_user_var = tk.StringVar()
        self.active_user = None
        self.active_scenario = None
        self.demo_shortcut_active = False
        self.store = None
        self.editor_tab = None
        self.run_tab = None
        self.demo_tts_client = None
        self.demo_robot_client = None
        self.demo_axis_base_var = tk.StringVar(value="ニュートラル")
        self.demo_face_keepalive_after_id = None
        self.demo_face_keepalive_data = None
        self.demo_face_keepalive_active = False
        self.notebook = None
        self.main_area = None
        self.selector_area = None
        self.session_bar = None

        self.build_ui()

    def apply_initial_runtime_choices(self):
        if self.tts_playback_var.get() == "robot":
            apply_robot_tts_environment("real")
            apply_robot_command_environment("real")
        if self.mic_activity_var.get() != "mic":
            self.mic_activity_var.set(set_mic_activity_mode("mic"))

    def initial_geometry(self):
        width = min(1320, max(1000, self.winfo_screenwidth() - 90))
        height = min(980, max(640, self.winfo_screenheight() - 130))
        return f"{width}x{height}"

    def build_ui(self):
        root = ui.frame(self, bg="app_bg")
        root.pack(fill="both", expand=True, padx=ui.SPACING["small_gap"], pady=ui.SPACING["small_gap"])

        main = ui.bordered_frame(root, bg="main_card", border="border", thickness=1)
        main.pack(fill="both", expand=True)

        self.selector_area = ui.frame(main, bg="main_card")
        self.selector_area.pack(fill="x", padx=ui.SPACING["page_x"], pady=(ui.SPACING["page_y"], ui.SPACING["section_y"]))
        self.build_user_selection(self.selector_area)

        self.session_bar = ui.frame(main, bg="main_card")

        self.main_area = ui.frame(main, bg="main_card")
        self.main_area.pack(fill="both", expand=True)

        footer = ui.frame(main, bg="main_card")
        footer.pack(fill="x", padx=ui.SPACING["page_x"], pady=(0, ui.SPACING["section_y"]))
        ui.variable_label(
            footer,
            self.status_var,
            font="small",
            bg="main_card",
            fg="sub_text",
            anchor="w",
        ).pack(fill="x", pady=(0, ui.SPACING["small_gap"]))
        runtime_row = ui.frame(footer, bg="main_card")
        runtime_row.pack(fill="x")
        self.build_runtime_controls(runtime_row)

        self.render_empty_state()

    def build_runtime_controls(self, footer):
        playback_frame = ui.frame(footer, bg="main_card")
        playback_frame.pack(side="right", padx=(ui.SPACING["gap"], 0))
        ui.label(playback_frame, text="音声", font="small", bg="main_card", fg="sub_text").pack(side="left")
        ui.radio(
            playback_frame,
            text="ノートPC",
            variable=self.tts_playback_var,
            value="local",
            command=self.on_tts_playback_changed,
            bg="main_card",
        ).pack(side="left")
        ui.radio(
            playback_frame,
            text="ニコラ",
            variable=self.tts_playback_var,
            value="robot",
            command=self.on_tts_playback_changed,
            bg="main_card",
        ).pack(side="left")

        engine_frame = ui.frame(footer, bg="main_card")
        engine_frame.pack(side="right", padx=(ui.SPACING["gap"], 0))
        ui.label(engine_frame, text="TTS", font="small", bg="main_card", fg="sub_text").pack(side="left")
        ui.radio(
            engine_frame,
            text="日本語",
            variable=self.tts_engine_var,
            value="aitalk",
            command=self.on_tts_engine_changed,
            bg="main_card",
        ).pack(side="left")
        ui.radio(
            engine_frame,
            text="English",
            variable=self.tts_engine_var,
            value="openai",
            command=self.on_tts_engine_changed,
            bg="main_card",
        ).pack(side="left")

        mic_frame = ui.frame(footer, bg="main_card")
        mic_frame.pack(side="right", padx=(ui.SPACING["gap"], 0))
        ui.label(mic_frame, text="検出", font="small", bg="main_card", fg="sub_text").pack(side="left")
        ui.radio(
            mic_frame,
            text="ロボットact",
            variable=self.mic_activity_var,
            value="robot_act",
            command=self.on_mic_activity_changed,
            bg="main_card",
        ).pack(side="left")
        ui.radio(
            mic_frame,
            text="Macマイク",
            variable=self.mic_activity_var,
            value="mic",
            command=self.on_mic_activity_changed,
            bg="main_card",
        ).pack(side="left")
        ui.label(mic_frame, text="終了秒", font="small", bg="main_card", fg="sub_text").pack(
            side="left", padx=(ui.SPACING["small_gap"], 0)
        )
        silence_spin = tk.Spinbox(
            mic_frame,
            from_=0.2,
            to=1.0,
            increment=0.1,
            textvariable=self.mic_silence_hold_var,
            command=self.on_mic_silence_hold_changed,
            width=4,
            format="%.1f",
            font=ui.FONTS["small"],
            bg=ui.COLORS["card"],
            fg=ui.COLORS["text"],
            relief="solid",
            bd=1,
        )
        silence_spin.pack(side="left", padx=(ui.SPACING["small_gap"], 0))
        silence_spin.bind("<Return>", lambda _event=None: self.on_mic_silence_hold_changed())
        silence_spin.bind("<FocusOut>", lambda _event=None: self.on_mic_silence_hold_changed())

    def on_tts_playback_changed(self):
        target = set_tts_playback_target(self.tts_playback_var.get())
        if target == "robot":
            apply_robot_tts_environment("real")
            apply_robot_command_environment("real")
            self.reset_robot_clients()
        self.tts_playback_var.set(target)
        if self.run_tab is not None:
            self.run_tab.set_tts_playback_target(target)
        label = "ニコラ" if target == "robot" else "ノートPC"
        url_note = ""
        if target == "robot":
            tcp = get_robot_tcp_config()
            url_note = f" / {get_robot_tts_play_url()} / cmd {tcp['host']}:{tcp['port']}"
        self.status_var.set(f"音声再生先を{label}にしました{url_note}")

    def on_tts_engine_changed(self):
        engine = set_tts_engine(self.tts_engine_var.get())
        self.tts_engine_var.set(engine)
        if self.run_tab is not None:
            self.run_tab.set_tts_engine(engine)
        if self.editor_tab is not None:
            self.editor_tab.set_tts_engine(engine)
        if self.demo_tts_client is not None:
            self.demo_tts_client.set_tts_engine(engine)
        label = "English(OpenAI)" if engine == "openai" else "日本語(AIトーク)"
        suffix = "。OPENAI_API_KEY が必要です" if engine == "openai" else ""
        self.status_var.set(f"TTSを{label}にしました{suffix}")

    def on_mic_activity_changed(self):
        mode = set_mic_activity_mode(self.mic_activity_var.get())
        self.mic_activity_var.set(mode)
        refreshed = True
        if self.run_tab is not None:
            refreshed = self.run_tab.refresh_mic_activity_mode()
        label = "Macマイク" if mode == "mic" else "ロボットact"
        suffix = "" if refreshed else "。実演中のため次回から反映します"
        self.status_var.set(f"発話検出を{label}にしました{suffix}")

    def get_mic_silence_hold_sec(self):
        try:
            value = float(self.mic_silence_hold_var.get())
        except (tk.TclError, ValueError):
            value = float(MIC_SILENCE_HOLD_SEC_DEFAULT)
        value = max(0.2, min(1.0, round(value, 1)))
        self.mic_silence_hold_var.set(value)
        return value

    def on_mic_silence_hold_changed(self):
        value = self.get_mic_silence_hold_sec()
        refreshed = True
        if self.run_tab is not None:
            refreshed = self.run_tab.refresh_mic_activity_mode()
        suffix = "" if refreshed else "。実演中のため次回から反映します"
        self.status_var.set(f"発話終わり判定を{value:.1f}秒にしました{suffix}")

    def reset_robot_clients(self):
        if self.run_tab is not None:
            self.run_tab.reset_robot_client()
        if self.editor_tab is not None:
            self.editor_tab.reset_robot_client()
        if self.demo_robot_client is not None:
            try:
                self.demo_robot_client.close()
            except Exception:
                pass
        self.demo_robot_client = None

    def clear_frame(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    def show_user_selection(self):
        self.session_bar.pack_forget()
        self.clear_frame(self.selector_area)
        self.selector_area.pack(fill="x", padx=ui.SPACING["page_x"], pady=(ui.SPACING["page_y"], ui.SPACING["section_y"]))
        self.build_user_selection(self.selector_area)
        self.render_empty_state()
        self.status_var.set("ユーザー名を入力してください")

    def show_session_bar(self):
        self.selector_area.pack_forget()
        self.clear_frame(self.session_bar)
        self.session_bar.pack(fill="x", padx=ui.SPACING["page_x"], pady=(ui.SPACING["page_y"], ui.SPACING["gap"]))

        label = f"ユーザー: {self.active_user} / シナリオ: {self.active_scenario['label']}"
        ui.sub_button(
            self.session_bar,
            text="デモ選択へ戻る" if self.demo_shortcut_active else "ユーザーやシナリオを変更",
            command=self.change_user_or_scenario,
        ).pack(side="right", padx=(ui.SPACING["gap"], 0))
        ui.label(
            self.session_bar,
            text=label,
            font="section_title",
            bg="main_card",
            anchor="w",
        ).pack(side="left", fill="x", expand=True)

    def build_user_selection(self, parent):
        ui.label(parent, text="ユーザー開始", font="page_title", bg="main_card").pack(anchor="w")

        cards = ui.frame(parent, bg="main_card")
        cards.pack(fill="x", pady=(ui.SPACING["gap"], 0))

        new_card = ui.bordered_frame(cards, bg="card", border="border")
        new_card.pack(side="left", fill="both", expand=True, padx=(0, ui.SPACING["gap"]))
        ui.label(new_card, text="新しいユーザー", font="section_title", bg="card").pack(
            anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"])
        )
        ui.label(
            new_card,
            text="ユーザー名を入力すると、道案内と家事の会話場面を作成して開始します。",
            font="small",
            bg="card",
            fg="muted",
            wraplength=420,
            justify="left",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["small_gap"]))

        new_row = ui.frame(new_card, bg="card")
        new_row.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["small_gap"]))
        ui.label(new_row, text="名前", font="small", bg="card", fg="sub_text", width=8, anchor="w").pack(side="left")
        ui.entry(new_row, self.new_user_var, font="input").pack(side="left", fill="x", expand=True)

        action_row = ui.frame(new_card, bg="card")
        action_row.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))
        ui.action_button(action_row, text="ユーザーを開始", command=self.start_new_user_session).pack(side="left")

        existing_card = ui.bordered_frame(cards, bg="card", border="border")
        existing_card.pack(side="left", fill="both", expand=True)
        ui.label(existing_card, text="既存ユーザー", font="section_title", bg="card").pack(
            anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"])
        )
        ui.label(
            existing_card,
            text="保存済みのシナリオJSONを選んで、そのユーザーとシナリオを読み込みます。",
            font="small",
            bg="card",
            fg="muted",
            wraplength=420,
            justify="left",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["small_gap"]))

        existing_row = ui.frame(existing_card, bg="card")
        existing_row.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))
        ui.sub_button(existing_row, text="既存ユーザーのファイルを選択", command=self.load_existing_user_file).pack(side="left")

    def render_empty_state(self):
        for child in self.main_area.winfo_children():
            child.destroy()

        self.build_nikola_demo_panel(self.main_area)

        card = ui.bordered_frame(self.main_area, bg="card", border="soft_border")
        card.pack(fill="x", padx=ui.SPACING["page_x"], pady=ui.SPACING["section_y"])
        ui.label(
            card,
            text="ユーザー名を入力して開始してください。",
            font="section_title",
            bg="card",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])

    def build_nikola_demo_panel(self, parent):
        card = ui.bordered_frame(parent, bg="card", border="accent")
        card.pack(fill="x", padx=ui.SPACING["page_x"], pady=(0, ui.SPACING["gap"]))

        ui.label(card, text="話し方を比べる", font="section_title", bg="card").pack(
            anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"])
        )

        rows = ui.frame(card, bg="card")
        rows.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))

        greeting_row = ui.frame(rows, bg="card")
        greeting_row.pack(fill="x")
        ui.label(greeting_row, text="いらっしゃいませ", font="small", bg="card", fg="sub_text", width=14, anchor="w").pack(
            side="left"
        )
        ui.sub_button(
            greeting_row,
            text="ニュートラル",
            command=lambda: self.demo_greeting_style(
                label="ニュートラル",
                face=("neutral", None),
                instructions={},
            ),
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))
        ui.sub_button(
            greeting_row,
            text="ゆっくり",
            command=lambda: self.demo_greeting_style(
                label="ゆっくり",
                face=("neutral", None),
                instructions={"tts_rate": 0.8},
            ),
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))
        ui.sub_button(
            greeting_row,
            text="柔らかく笑顔あり",
            command=lambda: self.demo_greeting_style(
                label="柔らかく笑顔あり",
                face=("WarmSmile", 2),
                instructions={
                    "tts_rate": 0.9,
                    "tts_pitch": 1.05,
                    "tts_emo_joy": 0.35,
                    "tts_emphasis": 0.9,
                },
            ),
        ).pack(side="left")

        separator = tk.Frame(rows, height=1, bg=ui.COLORS["soft_border"])
        separator.pack(fill="x", pady=ui.SPACING["small_gap"])

        ui.label(rows, text="部品ごとに試す", font="body_bold", bg="card").pack(anchor="w", pady=(0, ui.SPACING["small_gap"]))

        speech_row = ui.frame(rows, bg="card")
        speech_row.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))
        ui.label(speech_row, text="言葉", font="small", bg="card", fg="sub_text", width=8, anchor="w").pack(side="left")
        ui.sub_button(speech_row, text="いらっしゃいませ", command=lambda: self.demo_speak("いらっしゃいませ")).pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.sub_button(speech_row, text="やあ", command=lambda: self.demo_speak("やあ")).pack(side="left")

        face_row = ui.frame(rows, bg="card")
        face_row.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))
        ui.label(face_row, text="表情", font="small", bg="card", fg="sub_text", width=8, anchor="w").pack(side="left")
        ui.sub_button(face_row, text="ニュートラル", command=lambda: self.demo_emotion("neutral", None)).pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.sub_button(face_row, text="WarmSmile 2", command=lambda: self.demo_emotion("WarmSmile", 2)).pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.sub_button(face_row, text="sorry 2", command=lambda: self.demo_emotion("sorry", 2)).pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.sub_button(face_row, text="AffiliativeSmile 3", command=lambda: self.demo_emotion("AffiliativeSmile", 3)).pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.sub_button(face_row, text="AmusedDisgust 2", command=lambda: self.demo_emotion("AmusedDisgust", 2)).pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.sub_button(face_row, text="Releaf 2", command=lambda: self.demo_emotion("Releaf", 2)).pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.sub_button(face_row, text="FearfulSurprise 2", command=lambda: self.demo_emotion("FearfulSurprise", 2)).pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.sub_button(face_row, text="Flirty 2", command=lambda: self.demo_emotion("Flirty", 2)).pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.sub_button(face_row, text="軸ごとの調整", command=self.demo_face_axes).pack(side="left")

        voice_row = ui.frame(rows, bg="card")
        voice_row.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))
        ui.label(voice_row, text="声色", font="small", bg="card", fg="sub_text", width=8, anchor="w").pack(side="left")
        ui.sub_button(
            voice_row,
            text="速さ1.25倍",
            command=lambda: self.demo_voice("速さ1.25倍", {"tts_rate": 1.25}),
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))
        ui.sub_button(
            voice_row,
            text="高さ1.1倍",
            command=lambda: self.demo_voice("高さ1.1倍", {"tts_pitch": 1.1}),
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))
        ui.sub_button(
            voice_row,
            text="悲しみ1.0",
            command=lambda: self.demo_voice("悲しみ1.0", {"tts_emo_sad": 1.0}),
        ).pack(side="left")
        ui.sub_button(
            voice_row,
            text="喜び1.0",
            command=lambda: self.demo_voice("喜び1.0", {"tts_emo_joy": 1.0}),
        ).pack(side="left", padx=(ui.SPACING["small_gap"], 0))
        ui.sub_button(
            voice_row,
            text="怒り1.0",
            command=lambda: self.demo_voice("怒り1.0", {"tts_emo_angry": 1.0}),
        ).pack(side="left", padx=(ui.SPACING["small_gap"], 0))
        ui.sub_button(
            voice_row,
            text="軸ごとの調整",
            command=self.demo_voice_axes,
        ).pack(side="left", padx=(ui.SPACING["small_gap"], 0))

        motion_row = ui.frame(rows, bg="card")
        motion_row.pack(fill="x")
        ui.label(motion_row, text="動作", font="small", bg="card", fg="sub_text", width=8, anchor="w").pack(side="left")
        ui.sub_button(motion_row, text="お辞儀", command=self.demo_bow).pack(side="left")

        demo_row = ui.frame(rows, bg="card")
        demo_row.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))
        ui.label(demo_row, text="会話デモ", font="small", bg="card", fg="sub_text", width=8, anchor="w").pack(side="left")
        ui.action_button(
            demo_row,
            text="忠地 高級ホテル チェックインを開く",
            command=self.open_tadachi_hotel_checkin_demo,
        ).pack(side="left")

    def ensure_demo_runtime(self):
        apply_robot_tts_environment("real")
        apply_robot_command_environment("real")
        self.tts_playback_var.set(set_tts_playback_target("robot"))
        if self.demo_tts_client is None:
            from ..robot_style_editor.clients.tts_client import TTSClient

            self.demo_tts_client = TTSClient()
        self.demo_tts_client.set_playback_target("robot")
        self.demo_tts_client.set_tts_engine(self.tts_engine_var.get())
        if self.demo_robot_client is None:
            from ..robot_style_editor.clients.robot_command_client import RobotCommandClient

            self.demo_robot_client = RobotCommandClient()
        return self.demo_tts_client, self.demo_robot_client

    def demo_speak(self, text):
        try:
            tts_client, _robot = self.ensure_demo_runtime()
            tts_client.speak(text=text)
            self.status_var.set(f"ニコラで発話します: {text}")
        except Exception as exc:
            self.status_var.set(f"デモ発話エラー: {exc}")

    def demo_greeting_style(self, label, face, instructions):
        try:
            tts_client, robot = self.ensure_demo_runtime()
            emotion, level = face
            command = "/emotion neutral 1 5 3000" if level is None else f"/emotion {emotion} {int(level)} 3 3000"
            print(f"[DEMO GREETING] {label}: {command}", flush=True)
            if level is None or emotion not in SMILE_COMPATIBLE_EMOTIONS:
                robot.send("/smile end")
            robot.send(command)
            tts_client.speak(text="いらっしゃいませ", instructions=instructions)
            self.status_var.set(f"話し方デモを再生します: {label}")
        except Exception as exc:
            self.status_var.set(f"話し方デモエラー: {exc}")

    def demo_emotion(self, emotion, level):
        try:
            _tts_client, robot = self.ensure_demo_runtime()
            command = "/emotion neutral 1 5 3000" if level is None else f"/emotion {emotion} {int(level)} 3 3000"
            print(f"[DEMO FACE] {command}", flush=True)
            if level is None or emotion not in SMILE_COMPATIBLE_EMOTIONS:
                robot.send("/smile end")
            robot.send(command)
            label = emotion if level is None else f"{emotion} {level}"
            self.status_var.set(f"表情デモを送信しました: {label}")
        except Exception as exc:
            self.status_var.set(f"表情デモエラー: {exc}")

    def demo_face_axes(self):
        dialog = tk.Toplevel(self)
        dialog.title("軸ごとの表情調整")
        dialog.transient(self)
        dialog.geometry("760x680")

        body = ui.frame(dialog, bg="main_card")
        body.pack(fill="both", expand=True, padx=22, pady=18)

        ui.label(body, text="笑顔を軸ごとに調整", font="page_title", bg="main_card").pack(anchor="w")

        base_row = ui.frame(body, bg="main_card")
        base_row.pack(fill="x", pady=(ui.SPACING["section_y"], ui.SPACING["gap"]))
        ui.label(base_row, text="基準表情", font="body_bold", bg="main_card", width=8, anchor="w").pack(side="left")
        base_values = [label for label in ("ニュートラル", "通常") if label in FACE_EXPRESSION_OPTIONS]
        if not base_values:
            base_values = ["ニュートラル"]
        if self.demo_axis_base_var.get() not in base_values:
            self.demo_axis_base_var.set(base_values[0])
        ttk.Combobox(
            base_row,
            textvariable=self.demo_axis_base_var,
            values=base_values,
            state="readonly",
            width=14,
        ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))
        ui.sub_button(base_row, text="基準表情に戻す", command=self.demo_send_axis_base_face).pack(side="left")

        actions = ui.frame(body, bg="main_card")
        actions.pack(side="bottom", fill="x", pady=(ui.SPACING["section_y"], 0))

        def close_dialog():
            self.stop_demo_face_keepalive()
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)
        ui.sub_button(actions, text="閉じる", command=close_dialog).pack(side="left")

        panel_area = ui.scrollable_frame(body, bg="main_card")
        panel = FaceAxisEditorPanel(
            panel_area,
            initial_data=default_face_data("笑顔"),
            on_changed=self.demo_preview_face_axes,
        )
        panel.pack(fill="x")
        ui.sub_button(
            actions,
            text="ニュートラルから見る",
            command=lambda: self.demo_preview_face_from_neutral(panel.get_data()),
        ).pack(side="right")

        self.demo_send_axis_base_face()
        self.demo_face_keepalive_active = True
        self.status_var.set("笑顔の軸調整デモを開きました")

    def demo_send_axis_base_face(self):
        face = default_face_data(self.demo_axis_base_var.get())
        self.demo_send_face_data(face, keeptime=3000, label="基準表情")

    def demo_preview_face_axes(self, face_data, force=False, changed_axes=None):
        self.update_demo_face_keepalive(face_data)
        self.demo_send_face_data(face_data, keeptime=3000, label="笑顔の軸調整", changed_axes=changed_axes)

    def demo_preview_face_from_neutral(self, face_data):
        import copy

        self.stop_demo_face_keepalive()
        self.demo_emotion("neutral", None)
        self.status_var.set("ニュートラルに戻してから笑顔の軸調整を送ります")
        delay_ms = 4000 if face_data.get("command", {}).get("type") != "emotion" else 2000
        self.after(delay_ms, lambda data=copy.deepcopy(face_data): self.demo_preview_face_after_neutral(data))

    def demo_preview_face_after_neutral(self, face_data):
        self.demo_face_keepalive_active = True
        self.update_demo_face_keepalive(face_data)
        self.demo_send_face_data(face_data, keeptime=3000, label="笑顔の軸調整", changed_axes=None)

    def update_demo_face_keepalive(self, face_data):
        if not self.demo_face_keepalive_active:
            return
        if face_data.get("command", {}).get("type") == "emotion":
            return
        import copy

        self.demo_face_keepalive_data = copy.deepcopy(face_data)
        if self.demo_face_keepalive_after_id is None:
            self.demo_face_keepalive_after_id = self.after(2800, self.send_demo_face_keepalive)

    def send_demo_face_keepalive(self):
        self.demo_face_keepalive_after_id = None
        if not self.demo_face_keepalive_active or self.demo_face_keepalive_data is None:
            return
        self.demo_send_face_data(
            self.demo_face_keepalive_data,
            keeptime=3000,
            label="笑顔の軸調整 維持",
            changed_axes=None,
        )
        if self.demo_face_keepalive_active and self.demo_face_keepalive_data is not None:
            self.demo_face_keepalive_after_id = self.after(2800, self.send_demo_face_keepalive)

    def stop_demo_face_keepalive(self):
        self.demo_face_keepalive_active = False
        self.demo_face_keepalive_data = None
        if self.demo_face_keepalive_after_id is not None:
            try:
                self.after_cancel(self.demo_face_keepalive_after_id)
            except Exception:
                pass
            self.demo_face_keepalive_after_id = None

    def demo_send_face_data(self, face_data, keeptime=3000, label="表情", changed_axes=None):
        try:
            _tts_client, robot = self.ensure_demo_runtime()
            command = face_data.get("command", {})
            if command.get("type") == "smile":
                level = int(command.get("level", 2))
                priority = int(command.get("priority", 3))
                command_text = f"/smile start {level} {priority} {int(keeptime)}"
                print(f"[DEMO FACE] {label}: {command_text}", flush=True)
                robot.send(command_text)
                return
            if command.get("type") == "emotion":
                emotion = command.get("emotion", "neutral")
                smile_overlay = face_data.get("smile_overlay", {})
                use_smile_overlay = bool(smile_overlay.get("enabled", False))
                if not use_smile_overlay and emotion not in SMILE_COMPATIBLE_EMOTIONS:
                    print("[DEMO FACE] smile end: /smile end", flush=True)
                    robot.send("/smile end")
                if command.get("emotion") == "neutral":
                    command_text = command.get("text", "/emotion neutral 1 5 3000")
                else:
                    level = int(command.get("level", 1))
                    priority = int(command.get("priority", 3))
                    command_text = f"/emotion {emotion} {level} {priority} {int(keeptime)}"
                print(f"[DEMO FACE] {label}: {command_text}", flush=True)
                robot.send(command_text)
                if use_smile_overlay:
                    level = int(smile_overlay.get("level", 3))
                    priority = int(smile_overlay.get("priority", 3))
                    smile_text = f"/smile start {level} {priority} {int(keeptime)}"
                    print(f"[DEMO FACE] {label} smile: {smile_text}", flush=True)
                    robot.send(smile_text)
                return

            commands = face_axis_commands(face_data, keeptime=keeptime)
            if changed_axes is not None:
                target_axes = {str(axis) for axis in changed_axes}
                commands = [
                    command
                    for command in commands
                    if str(command["axis"]) in target_axes
                ]
            if not commands:
                return
            axis_summary = ", ".join(f"{cmd['axis']}={cmd['value']}" for cmd in commands)
            print(f"[DEMO FACE] {label}: axes({axis_summary})", flush=True)
            robot.send("/smile end")
            for command in commands:
                robot.send_face_axis(
                    axis=str(command["axis"]),
                    value=int(command["value"]),
                    velocity=int(command.get("velocity", 2000)),
                    priority=int(command.get("priority", 3)),
                    keeptime=int(command.get("keeptime", 3000)),
                )
            self.status_var.set(f"{label}を送信しました")
        except Exception as exc:
            self.status_var.set(f"軸調整デモエラー: {exc}")

    def demo_voice(self, label, instructions):
        try:
            tts_client, _robot = self.ensure_demo_runtime()
            tts_client.speak(text="いらっしゃいませ", instructions=instructions)
            self.status_var.set(f"声色デモを再生します: {label}")
        except Exception as exc:
            self.status_var.set(f"声色デモエラー: {exc}")

    def demo_voice_axes(self):
        dialog = tk.Toplevel(self)
        dialog.title("声色を軸ごとに調整")
        dialog.transient(self)
        dialog.geometry("760x720")

        body = ui.frame(dialog, bg="main_card")
        body.pack(fill="both", expand=True, padx=22, pady=18)
        ui.label(body, text="声色を軸ごとに調整", font="page_title", bg="main_card").pack(anchor="w")

        text_row = ui.frame(body, bg="main_card")
        text_row.pack(fill="x", pady=(ui.SPACING["section_y"], ui.SPACING["gap"]))
        ui.label(text_row, text="言葉", font="body_bold", bg="main_card", width=8, anchor="w").pack(side="left")
        text_var = tk.StringVar(value="いらっしゃいませ")
        ui.entry(text_row, text_var, font="input").pack(side="left", fill="x", expand=True)

        actions = ui.frame(body, bg="main_card")
        actions.pack(side="bottom", fill="x", pady=(ui.SPACING["section_y"], 0))
        ui.sub_button(actions, text="閉じる", command=dialog.destroy).pack(side="left")

        panel_area = ui.scrollable_frame(body, bg="main_card")
        panel = VoiceEditorPanel(panel_area, initial_data=default_voice_data())
        panel.pack(fill="x")

        def play_current_voice():
            text = text_var.get().strip()
            if not text:
                messagebox.showwarning("確認", "発話する言葉を入力してください")
                return
            try:
                tts_client, _robot = self.ensure_demo_runtime()
                tts_client.speak(text=text, instructions=panel.get_data()["tts_instructions"])
                self.status_var.set(f"調整した声色で再生します: {text}")
            except Exception as exc:
                self.status_var.set(f"声色調整デモエラー: {exc}")

        ui.action_button(actions, text="この声色で再生", command=play_current_voice).pack(side="right")
        self.status_var.set("声色の軸調整デモを開きました")

    def demo_bow(self):
        try:
            _tts_client, robot = self.ensure_demo_runtime()
            robot.send_nod(amplitude=22, duration=700, times=1, priority=3)
            self.status_var.set("お辞儀デモを送信しました")
        except Exception as exc:
            self.status_var.set(f"お辞儀デモエラー: {exc}")

    def open_tadachi_hotel_checkin_demo(self):
        path = SAVE_DIR / "忠地" / "luxury_hotel.json"
        if not path.exists():
            messagebox.showerror("デモを開けません", f"保存済みデモが見つかりません。\n{path}")
            return

        scenario = self.selected_scenario("高級ホテル")
        self.load_session(
            path=path,
            username="忠地",
            scenario=scenario,
            create=False,
            active_scene_id="hotel_checkin",
            demo_shortcut=True,
        )
        self.status_var.set("デモ会話を開きました: 忠地 / 高級ホテル / チェックイン")

    def start_new_user_session(self):
        username = self.new_user_var.get().strip()
        if not username:
            messagebox.showwarning("確認", "ユーザー名を入力してください")
            return

        created = self.ensure_primary_scenario_files(username)
        scenario = self.scenario_by_id("direction_guidance")
        path = self.scenario_path(username, scenario["id"])
        self.load_session(path=path, username=username, scenario=scenario, create=created)

    def ensure_primary_scenario_files(self, username):
        created_any = False
        for scenario in self.primary_scenarios():
            path = self.scenario_path(username, scenario["id"])
            if path.exists():
                continue
            store = ScenarioStore(path=path)
            self.initialize_store_for_scenario(store, username, scenario)
            store.save()
            created_any = True
        return created_any

    def initialize_store_for_scenario(self, store, username, scenario):
        scene_option = self.primary_scene_option(scenario)
        store.data["user_name"] = username
        store.data["scenario_id"] = scenario["id"]
        store.data["scenario_label"] = scenario["label"]
        store.data["scenario_title"] = scenario["default_title"]
        store.data["conversation_type_id"] = scene_option["id"]
        store.data["conversation_intent"] = scene_option["intent"]
        store.data["active_scene_id"] = scene_option["id"]

    def primary_scene_option(self, scenario):
        from .config import conversation_scene_options

        return conversation_scene_options(scenario["id"])[0]

    def load_existing_user_file(self):
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.askopenfilename(
            title="保存済みシナリオJSONを選択",
            initialdir=str(SAVE_DIR),
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        path = Path(path)
        try:
            temp_store = ScenarioStore(path=path)
            scenario = self.scenario_from_data_or_path(temp_store.data, path)
            username = temp_store.data.get("user_name") or path.parent.name
            self.load_session(path=path, username=username, scenario=scenario, create=False)
        except Exception as exc:
            messagebox.showerror("読み込みエラー", str(exc))

    def load_session(self, path, username, scenario, create, active_scene_id=None, demo_shortcut=False):
        self.store = ScenarioStore(path=path)
        self.store.data["user_name"] = username
        self.store.data["scenario_id"] = scenario["id"]
        self.store.data["scenario_label"] = scenario["label"]
        self.store.data.setdefault("scenario_title", scenario["default_title"])
        if active_scene_id is not None:
            self.store.data["active_scene_id"] = active_scene_id
        self.store.save()
        self.active_user = username
        self.active_scenario = scenario
        self.demo_shortcut_active = bool(demo_shortcut)

        self.build_tabs()
        self.show_session_bar()
        action = "開始しました" if create else "読み込みました"
        self.status_var.set(f"{username} / {scenario['label']} を{action}")

    def switch_primary_scenario(self, label):
        scenario = self.selected_primary_scenario(label)
        if scenario is None:
            return False
        if self.active_scenario and self.active_scenario.get("id") == scenario["id"]:
            return True
        if not self.confirm_save_before_change():
            return False

        username = self.active_user
        if not username:
            return False
        self.ensure_primary_scenario_files(username)
        path = self.scenario_path(username, scenario["id"])
        self.load_session(path=path, username=username, scenario=scenario, create=False)
        return True

    def change_user_or_scenario(self):
        if not self.demo_shortcut_active and not self.confirm_save_before_change():
            return

        self.store = None
        self.editor_tab = None
        self.run_tab = None
        self.notebook = None
        self.active_user = None
        self.active_scenario = None
        self.demo_shortcut_active = False
        self.show_user_selection()

    def confirm_save_before_change(self):
        if self.store is None:
            return True

        result = messagebox.askyesnocancel(
            "保存確認",
            "ユーザーやシナリオを変更する前に、現在の内容を保存しますか？",
        )
        if result is None:
            return False
        if result:
            self.save_current_session()
        return True

    def save_current_session(self):
        if self.editor_tab is not None:
            self.editor_tab.sync_texts()
            self.editor_tab.save_workspace_to_active_scene()
        if self.store is not None:
            self.store.save()

    def build_tabs(self):
        for child in self.main_area.winfo_children():
            child.destroy()

        self.notebook = ttk.Notebook(self.main_area, style="Research.TNotebook")
        self.notebook.pack(fill="both", expand=True, padx=ui.SPACING["page_x"], pady=(0, ui.SPACING["gap"]))

        self.editor_tab = ConversationEditorTab(
            self.notebook,
            store=self.store,
            status_var=self.status_var,
            on_try_robot=self.open_robot_run_tab,
            get_tts_engine=lambda: self.tts_engine_var.get(),
            scene_switch_options=self.primary_scenarios() if self.is_primary_session() else None,
            active_scene_label=self.active_scenario["label"] if self.is_primary_session() else None,
            on_scene_switch=self.switch_primary_scenario if self.is_primary_session() else None,
        )
        self.run_tab = RobotRunTab(
            self.notebook,
            get_turns=self.editor_tab.scenario_turns,
            status_var=self.status_var,
            get_mic_silence_hold_sec=self.get_mic_silence_hold_sec,
            get_tts_engine=lambda: self.tts_engine_var.get(),
        )

        self.notebook.add(self.editor_tab, text="会話設定")
        self.notebook.add(self.run_tab, text="実演")

    def open_robot_run_tab(self, turns=None, label=None):
        self.save_current_session()
        if self.run_tab is not None:
            self.run_tab.show_overview(turns=turns, label=label)
        if self.notebook is not None and self.run_tab is not None:
            self.notebook.select(self.run_tab)
        if self.run_tab is not None:
            self.run_tab.reset_face_to_neutral()
        if label:
            self.status_var.set(f"保存しました。実演タブで確認できます: {label}")
        else:
            self.status_var.set("保存しました。実演タブで確認できます")

    def selected_scenario(self, label):
        for option in SCENARIO_OPTIONS:
            if option["label"] == label:
                return option
        return SCENARIO_OPTIONS[0]

    def scenario_by_id(self, scenario_id):
        for option in SCENARIO_OPTIONS:
            if option["id"] == scenario_id:
                return option
        return SCENARIO_OPTIONS[0]

    def primary_scenarios(self):
        return [self.scenario_by_id(scenario_id) for scenario_id in PRIMARY_SCENARIO_IDS]

    def selected_primary_scenario(self, label):
        for option in self.primary_scenarios():
            if option["label"] == label:
                return option
        return None

    def is_primary_session(self):
        return (
            not self.demo_shortcut_active
            and self.active_scenario is not None
            and self.active_scenario.get("id") in PRIMARY_SCENARIO_IDS
        )

    def scenario_from_data_or_path(self, data, path):
        scenario_id = data.get("scenario_id") or path.stem
        scenario_label = data.get("scenario_label")
        for option in SCENARIO_OPTIONS:
            if option["id"] == scenario_id or option["label"] == scenario_label:
                return option
        raise ValueError("選択したJSONのシナリオを判定できませんでした")

    def scenario_path(self, username, scenario_id):
        safe_user = self.safe_filename(username)
        safe_scenario = self.safe_filename(scenario_id)
        return SAVE_DIR / safe_user / f"{safe_scenario}.json"

    def safe_filename(self, value):
        value = re.sub(r"[\\/:*?\"<>|\\s]+", "_", value.strip())
        return Path(value).name or "user"


def main():
    app = ConversationToolApp()
    app.mainloop()
