import tkinter as tk

from .. import ui_style as ui


GAZE_9_OPTIONS = [
    {"id": "up_left", "label": "左上", "lookaway": "lu"},
    {"id": "up", "label": "上", "lookaway": "u"},
    {"id": "up_right", "label": "右上", "lookaway": "ru"},
    {"id": "left", "label": "左", "lookaway": "l"},
    {"id": "front", "label": "正面", "lookaway": "f"},
    {"id": "right", "label": "右", "lookaway": "r"},
    {"id": "down_left", "label": "左下", "lookaway": "ld"},
    {"id": "down", "label": "下", "lookaway": "d"},
    {"id": "down_right", "label": "右下", "lookaway": "rd"},
]


class GazeDirectionPanel(tk.Frame):
    def __init__(
        self,
        parent,
        selected_gaze,
        on_select,
        on_back=None,
        title="視線の方向を選ぶ",
        description="視線方向を9方向から選びます。",
    ):
        super().__init__(parent, bg=ui.COLORS["main_card"])

        self.selected_gaze = selected_gaze
        self.on_select = on_select
        self.on_back = on_back
        self.title = title
        self.description = description

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

        ui.label(
            header,
            text=self.title,
            font="page_title",
            bg="main_card",
        ).pack(side="left", anchor="w")

        if self.on_back is not None:
            ui.sub_button(
                header,
                text="戻る",
                command=self.on_back,
            ).pack(side="right")

        ui.label(
            page,
            text=self.description,
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(
            anchor="w",
            pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]),
        )

        section = ui.frame(page, bg="panel")
        section.pack(fill="x")

        grid = ui.frame(section, bg="panel")
        grid.pack(
            fill="x",
            padx=ui.SPACING["section_x"],
            pady=ui.SPACING["section_y"],
        )

        for col in range(3):
            grid.grid_columnconfigure(col, weight=1)

        for index, opt in enumerate(GAZE_9_OPTIONS):
            card = ui.bordered_frame(grid, bg="card", border="border")
            card.grid(
                row=index // 3,
                column=index % 3,
                sticky="nsew",
                padx=ui.SPACING["small_gap"],
                pady=ui.SPACING["small_gap"],
            )

            ui.radio(
                card,
                text=opt["label"],
                variable=self.selected_gaze,
                value=opt["id"],
                command=lambda item=opt: self.on_select(item),
                bg="card",
            ).pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
            )

            ui.label(
                card,
                text=f"/lookaway {opt['lookaway']}",
                font="small",
                bg="card",
                fg="muted",
            ).pack(
                anchor="w",
                padx=ui.SPACING["card_x"],
                pady=(0, ui.SPACING["compact_y"]),
            )

        bottom = ui.frame(page, bg="main_card")
        bottom.pack(
            fill="x",
            pady=(ui.SPACING["small_gap"], 0),
        )

        if self.on_back is not None:
            ui.action_button(
                bottom,
                text="この視線にする",
                command=self.on_back,
            ).pack(side="right")


def find_gaze_option(gaze_id: str):
    for opt in GAZE_9_OPTIONS:
        if opt["id"] == gaze_id:
            return opt
    return None