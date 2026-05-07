import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .. import ui_style as ui
from ..config import SAVE_JSON_DIR
from ..config_default_profile import build_default_profile


class DefaultProfileTab(tk.Frame):
    def __init__(
        self,
        parent,
        profile_store,
        status_var,
        tts_client=None,
        on_create_user=None,
        on_load_user=None,
        on_continue_user=None,
        on_finish=None,
        can_use_default_talk=None,
    ):
        super().__init__(parent, bg=ui.COLORS["main_card"])
        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_create_user = on_create_user
        self.on_load_user = on_load_user
        self.on_continue_user = on_continue_user
        self.on_finish = on_finish
        self.can_use_default_talk = can_use_default_talk
        self.default_profile = build_default_profile()
        self.filename_var = tk.StringVar()
        self.saved_message_var = tk.StringVar(value="")
        self.saved_actions_frame = None
        self.inner_notebook = None
        self.default_talk_tab = None
        self.default_talk_frame = None
        self.build_ui()

    def build_ui(self):
        page = ui.frame(self, bg="main_card")
        page.pack(
            fill="both",
            expand=True,
            padx=ui.SPACING["page_x"],
            pady=ui.SPACING["page_y"],
        )

        ui.label(page, text="デフォルト設定", font="page_title", bg="main_card").pack(anchor="w")
        ui.label(
            page,
            text="研究用の標準設定を一括で適用し、この値を基準にロボット接客を試します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        self.inner_notebook = ttk.Notebook(page, style="Research.TNotebook")
        self.inner_notebook.pack(fill="both", expand=True)
        self.inner_notebook.bind("<<NotebookTabChanged>>", self.on_inner_tab_changed)

        settings_tab = ui.frame(self.inner_notebook, bg="main_card")
        self.settings_tab = settings_tab
        self.inner_notebook.add(settings_tab, text="デフォルト設定")
        content = ui.scrollable_frame(settings_tab)
        self.build_user_area(content)
        self.build_summary_area(content)
        self.build_bottom_area(settings_tab)

        self.default_talk_frame = ui.frame(self.inner_notebook, bg="main_card")
        self.inner_notebook.add(self.default_talk_frame, text="デフォルトで話す")

    def on_inner_tab_changed(self, _event=None):
        if self.inner_notebook is None or self.default_talk_frame is None:
            return
        if self.inner_notebook.select() != str(self.default_talk_frame):
            return
        if self.can_use_default_talk is not None and not self.can_use_default_talk():
            self.inner_notebook.select(self.settings_tab)
            self.status_var.set("先にユーザー名を入力してください")
            return
        self.ensure_default_talk_tab()

    def ensure_default_talk_tab(self):
        if self.default_talk_tab is not None:
            return self.default_talk_tab

        from .default_talk_tab import DefaultTalkTab

        self.default_talk_tab = DefaultTalkTab(
            self.default_talk_frame,
            profile_store=self.profile_store,
            status_var=self.status_var,
            tts_client=self.tts_client,
        )
        self.default_talk_tab.pack(fill="both", expand=True)
        return self.default_talk_tab

    def build_user_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        ui.label(section, text="ユーザー開始", font="section_title", bg="panel").pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        ui.label(
            card,
            text="新しいユーザー名",
            font="small",
            bg="card",
            fg="muted",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]))

        row = ui.frame(card, bg="card")
        row.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))

        ui.entry(row, self.filename_var).pack(side="left", fill="x", expand=True)
        ui.action_button(
            row,
            text="新しいユーザーを開始",
            command=self.start_new_user,
        ).pack(side="left", padx=(ui.SPACING["small_gap"], 0))
        ui.sub_button(
            row,
            text="既存ユーザーを変更する",
            command=self.load_saved_profile,
        ).pack(side="left", padx=(ui.SPACING["small_gap"], 0))

        self.saved_actions_frame = ui.bordered_frame(section, bg="card", border="border")

        ui.variable_label(
            self.saved_actions_frame,
            textvariable=self.saved_message_var,
            font="body_bold",
            bg="card",
            fg="text",
            justify="left",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]))

        action_row = ui.frame(self.saved_actions_frame, bg="card")
        action_row.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))
        ui.action_button(
            action_row,
            text="同じユーザーで続ける",
            command=self.continue_user,
        ).pack(side="left")
        ui.sub_button(
            action_row,
            text="ユーザーを変更する",
            command=self.reset_user_entry,
        ).pack(side="left", padx=(ui.SPACING["small_gap"], 0))
        ui.sub_button(
            action_row,
            text="終わる",
            command=self.finish_app,
        ).pack(side="left", padx=(ui.SPACING["small_gap"], 0))

    def build_summary_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        ui.label(section, text="適用される内容", font="section_title", bg="panel").pack(
            anchor="w",
            padx=ui.SPACING["section_x"],
            pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]),
        )

        grid = ui.frame(section, bg="panel")
        grid.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

        items = [
            ("話者", "のぞみ"),
            ("スタイル", "軽い尊敬語 / 親しみ 中 / 語彙 中 / 長さ 中"),
            ("話速・間", "話速 1.00倍 / 文間 0.40秒 / 返答 0.40秒"),
            ("姿", "考える・聞く・理解はNeutral基準"),
            ("DA", "全DA: 表情Neutral / 声色Neutral / テクニックなし"),
            ("フィラー", "なし"),
        ]

        for index, (title, value) in enumerate(items):
            card = ui.bordered_frame(grid, bg="card", border="border")
            card.grid(
                row=index // 2,
                column=index % 2,
                sticky="ew",
                padx=(0, ui.SPACING["gap"]),
                pady=(0, ui.SPACING["small_gap"]),
            )
            grid.columnconfigure(index % 2, weight=1)

            ui.label(card, text=title, font="small", bg="card", fg="muted").pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(ui.SPACING["compact_y"], 0),
            )
            ui.label(
                card,
                text=value,
                font="body_bold",
                bg="card",
                fg="text",
                wraplength=440,
                justify="left",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))

    def build_bottom_area(self, parent):
        bottom = ui.frame(parent, bg="main_card")
        bottom.pack(fill="x", pady=(ui.SPACING["small_gap"], 0))

        ui.label(
            bottom,
            text="新規ユーザーは必ずデフォルト設定から開始します。",
            font="small",
            bg="main_card",
            fg="sub_text",
        ).pack(side="left")

    def start_new_user(self):
        filename = self.filename_var.get().strip()
        if not filename:
            messagebox.showwarning("確認", "新しいユーザー名を入力してください。")
            return

        if self.on_create_user is None:
            return

        try:
            self.on_create_user(filename)
        except FileExistsError as e:
            messagebox.showerror("作成できません", str(e))
        except ValueError as e:
            messagebox.showerror("作成できません", str(e))
        except Exception as e:
            messagebox.showerror("作成エラー", str(e))

    def show_default_talk_tab(self):
        if self.inner_notebook is not None and self.default_talk_frame is not None:
            self.inner_notebook.select(self.default_talk_frame)
            tab = self.ensure_default_talk_tab()
            if hasattr(tab, "refresh_from_profile"):
                tab.refresh_from_profile()

    def load_saved_profile(self):
        SAVE_JSON_DIR.mkdir(parents=True, exist_ok=True)
        path = filedialog.askopenfilename(
            title="保存データを読み込む",
            initialdir=str(SAVE_JSON_DIR),
            filetypes=[("JSON files", "*.json")],
        )
        if not path:
            return

        try:
            if self.on_load_user is not None:
                self.on_load_user(path)
            else:
                loaded_path = self.profile_store.load_from(path)
                self.status_var.set(f"保存データを読み込みました: {loaded_path.name}")
        except Exception as e:
            messagebox.showerror("読み込みエラー", str(e))

    def show_saved_actions(self, saved_path, example_path=None):
        if self.saved_actions_frame is None:
            return
        if self.inner_notebook is not None and hasattr(self, "settings_tab"):
            self.inner_notebook.select(self.settings_tab)

        if example_path is not None:
            message = f"保存しました: {saved_path.name}\n接客履歴: {example_path.name}"
        else:
            message = f"保存しました: {saved_path.name}"
        self.saved_message_var.set(message)
        self.saved_actions_frame.pack(fill="x", padx=ui.SPACING["section_x"], pady=(0, ui.SPACING["section_y"]))

    def reset_user_entry(self):
        if self.saved_actions_frame is not None:
            self.saved_actions_frame.pack_forget()
        self.filename_var.set("")
        self.status_var.set("次のユーザー名を入力してください")

    def continue_user(self):
        if self.saved_actions_frame is not None:
            self.saved_actions_frame.pack_forget()
        if self.on_continue_user is not None:
            self.on_continue_user()

    def finish_app(self):
        if self.on_finish is not None:
            self.on_finish()
