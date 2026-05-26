from pathlib import Path
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from . import ui_style as ui
from .config import SAVE_DIR, SCENARIO_OPTIONS
from .scenario_store import ScenarioStore
from .tabs.editor_tab import ConversationEditorTab
from .tabs.robot_run_tab import RobotRunTab
from ..robot_style_editor.config import (
    apply_robot_command_environment,
    apply_robot_tts_environment,
    get_default_mic_activity_mode,
    get_robot_tcp_config,
    get_robot_tts_play_url,
    get_tts_playback_target,
    set_mic_activity_mode,
    set_tts_playback_target,
)


class ConversationToolApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("接客会話編集ツール")
        self.geometry(self.initial_geometry())
        self.minsize(980, 620)

        ui.apply_app_style(self)

        self.status_var = tk.StringVar(value="ユーザーとシナリオを選択してください")
        self.tts_playback_var = tk.StringVar(value=get_tts_playback_target())
        self.mic_activity_var = tk.StringVar(value=get_default_mic_activity_mode())
        self.apply_initial_runtime_choices()
        self.new_user_var = tk.StringVar()
        self.new_scenario_var = tk.StringVar(value=SCENARIO_OPTIONS[0]["label"])
        self.active_user = None
        self.active_scenario = None
        self.store = None
        self.editor_tab = None
        self.run_tab = None
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
        ui.variable_label(footer, self.status_var, font="small", bg="main_card", fg="sub_text").pack(
            side="left", fill="x", expand=True
        )
        self.build_runtime_controls(footer)

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

    def on_mic_activity_changed(self):
        mode = set_mic_activity_mode(self.mic_activity_var.get())
        self.mic_activity_var.set(mode)
        refreshed = True
        if self.run_tab is not None:
            refreshed = self.run_tab.refresh_mic_activity_mode()
        label = "Macマイク" if mode == "mic" else "ロボットact"
        suffix = "" if refreshed else "。実演中のため次回から反映します"
        self.status_var.set(f"発話検出を{label}にしました{suffix}")

    def reset_robot_clients(self):
        if self.run_tab is not None:
            self.run_tab.reset_robot_client()
        if self.editor_tab is not None:
            self.editor_tab.reset_robot_client()

    def clear_frame(self, frame):
        for child in frame.winfo_children():
            child.destroy()

    def show_user_selection(self):
        self.session_bar.pack_forget()
        self.clear_frame(self.selector_area)
        self.selector_area.pack(fill="x", padx=ui.SPACING["page_x"], pady=(ui.SPACING["page_y"], ui.SPACING["section_y"]))
        self.build_user_selection(self.selector_area)
        self.render_empty_state()
        self.status_var.set("ユーザーとシナリオを選択してください")

    def show_session_bar(self):
        self.selector_area.pack_forget()
        self.clear_frame(self.session_bar)
        self.session_bar.pack(fill="x", padx=ui.SPACING["page_x"], pady=(ui.SPACING["page_y"], ui.SPACING["gap"]))

        label = f"ユーザー: {self.active_user} / 店舗: {self.active_scenario['label']}"
        ui.label(self.session_bar, text=label, font="section_title", bg="main_card").pack(side="left")
        ui.sub_button(
            self.session_bar,
            text="ユーザーやシナリオを変更",
            command=self.change_user_or_scenario,
        ).pack(side="right")

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
            text="新しいユーザー名を作成し、最初に編集する店舗シナリオを選びます。",
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

        scenario_row = ui.frame(new_card, bg="card")
        scenario_row.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))
        ui.label(scenario_row, text="店舗", font="small", bg="card", fg="sub_text", width=8, anchor="w").pack(side="left")
        ttk.Combobox(
            scenario_row,
            textvariable=self.new_scenario_var,
            values=[option["label"] for option in SCENARIO_OPTIONS],
            state="readonly",
            width=30,
        ).pack(side="left", fill="x", expand=True)
        ui.action_button(scenario_row, text="新しいユーザーを開始", command=self.start_new_user_session).pack(
            side="left", padx=(ui.SPACING["small_gap"], 0)
        )

        existing_card = ui.bordered_frame(cards, bg="card", border="border")
        existing_card.pack(side="left", fill="both", expand=True)
        ui.label(existing_card, text="既存ユーザー", font="section_title", bg="card").pack(
            anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"])
        )
        ui.label(
            existing_card,
            text="保存済みのシナリオJSONを選んで、そのユーザーと店舗シナリオを読み込みます。",
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

        card = ui.bordered_frame(self.main_area, bg="card", border="soft_border")
        card.pack(fill="x", padx=ui.SPACING["page_x"], pady=ui.SPACING["section_y"])
        ui.label(
            card,
            text="ユーザー名を入力し、シナリオを選択して開始してください。",
            font="section_title",
            bg="card",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])

    def start_new_user_session(self):
        username = self.new_user_var.get().strip()
        if not username:
            messagebox.showwarning("確認", "ユーザー名を入力してください")
            return

        scenario = self.selected_scenario(self.new_scenario_var.get())
        path = self.scenario_path(username, scenario["id"])
        if path.exists():
            messagebox.showerror(
                "作成できません",
                f"同じユーザーの同じ店舗シナリオが既にあります。\n既存ユーザーからファイルを選択してください。\n\n{path}",
            )
            return

        self.load_session(path=path, username=username, scenario=scenario, create=True)

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

    def load_session(self, path, username, scenario, create):
        self.store = ScenarioStore(path=path)
        self.store.data["user_name"] = username
        self.store.data["scenario_id"] = scenario["id"]
        self.store.data["scenario_label"] = scenario["label"]
        self.store.data.setdefault("scenario_title", scenario["default_title"])
        self.store.save()
        self.active_user = username
        self.active_scenario = scenario

        self.build_tabs()
        self.show_session_bar()
        action = "開始しました" if create else "読み込みました"
        self.status_var.set(f"{username} / {scenario['label']} を{action}")

    def change_user_or_scenario(self):
        if not self.confirm_save_before_change():
            return

        self.store = None
        self.editor_tab = None
        self.run_tab = None
        self.notebook = None
        self.active_user = None
        self.active_scenario = None
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
        )
        self.run_tab = RobotRunTab(
            self.notebook,
            get_turns=self.editor_tab.scenario_turns,
            status_var=self.status_var,
        )

        self.notebook.add(self.editor_tab, text="会話設定")
        self.notebook.add(self.run_tab, text="実演")

    def open_robot_run_tab(self):
        self.save_current_session()
        if self.run_tab is not None:
            self.run_tab.show_overview()
        if self.notebook is not None and self.run_tab is not None:
            self.notebook.select(self.run_tab)
        self.status_var.set("保存しました。実演タブで確認できます")

    def selected_scenario(self, label):
        for option in SCENARIO_OPTIONS:
            if option["label"] == label:
                return option
        return SCENARIO_OPTIONS[0]

    def scenario_from_data_or_path(self, data, path):
        scenario_id = data.get("scenario_id") or path.stem
        scenario_label = data.get("scenario_label")
        for option in SCENARIO_OPTIONS:
            if option["id"] == scenario_id or option["label"] == scenario_label:
                return option
        raise ValueError("選択したJSONの店舗シナリオを判定できませんでした")

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
