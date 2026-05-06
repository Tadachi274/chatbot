import copy
import tkinter as tk
from tkinter import filedialog, messagebox

from .. import ui_style as ui
from ..config import SAVE_JSON_DIR
from ..config_default_profile import build_default_profile


class DefaultProfileTab(tk.Frame):
    def __init__(
        self,
        parent,
        profile_store,
        status_var,
        on_saved=None,
        on_examples=None,
        on_applied=None,
    ):
        super().__init__(parent, bg=ui.COLORS["main_card"])
        self.profile_store = profile_store
        self.status_var = status_var
        self.on_saved = on_saved
        self.on_examples = on_examples
        self.on_applied = on_applied
        self.default_profile = build_default_profile()
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

        content = ui.scrollable_frame(page)
        self.build_summary_area(content)
        self.build_bottom_area(page)

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
            ("話速・間", "話速 1.00倍 / 文間 0.20秒 / 返答 0.40秒"),
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

        ui.sub_button(
            bottom,
            text="デフォルトを適用して次へ",
            command=self.apply_and_next,
        ).pack(side="left")

        ui.sub_button(
            bottom,
            text="保存データを読み込む",
            command=self.load_saved_profile,
        ).pack(side="left", padx=(ui.SPACING["small_gap"], 0))

        ui.action_button(
            bottom,
            text="デフォルトで接客例へ",
            command=self.apply_and_examples,
        ).pack(side="right")

    def apply_default_profile(self):
        self.profile_store.data = copy.deepcopy(self.default_profile)
        self.profile_store.save()
        if self.on_applied is not None:
            self.on_applied()
        self.status_var.set("デフォルト設定を適用しました")

    def apply_and_next(self):
        self.apply_default_profile()
        if self.on_saved is not None:
            self.on_saved()

    def apply_and_examples(self):
        self.apply_default_profile()
        if self.on_examples is not None:
            self.on_examples()

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
            loaded_path = self.profile_store.load_from(path)
            if self.on_applied is not None:
                self.on_applied()
            self.status_var.set(f"保存データを読み込みました: {loaded_path.name}")
        except Exception as e:
            messagebox.showerror("読み込みエラー", str(e))
