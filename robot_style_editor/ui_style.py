import tkinter as tk
from tkinter import ttk


COLORS = {
    # base
    "app_bg": "#f5f6f8",
    "main_card": "#ffffff",
    "panel": "#ffffff",
    "card": "#ffffff",

    # line / surface
    "border": "#d9dde3",
    "soft_border": "#e6e9ee",
    "frame_border": "#d9dde3",

    # text
    "text": "#1f2933",
    "sub_text": "#5f6b7a",
    "muted": "#8a94a3",
    "blue_text": "#2563eb",

    # actions
    "accent": "#2563eb",
    "accent_active": "#1d4ed8",
    "sub_button": "#eef2f7",
    "sub_button_active": "#e2e8f0",

    # tabs
    "tab_bg": "#eef2f7",
    "tab_selected": "#ffffff",
}

FONTS = {
    "app_title": ("Yu Gothic UI", 22, "bold"),
    "page_title": ("Yu Gothic UI", 20, "bold"),
    "section_title": ("Yu Gothic UI", 14, "bold"),
    "body": ("Yu Gothic UI", 11),
    "body_bold": ("Yu Gothic UI", 11, "bold"),
    "small": ("Yu Gothic UI", 10),
    "input": ("Yu Gothic UI", 12),
    "input_big": ("Yu Gothic UI", 13),
    "button": ("Yu Gothic UI", 11, "bold"),
    "button_big": ("Yu Gothic UI", 12, "bold"),
    "mono": ("Consolas", 10),
}

SPACING = {
    "page_x": 24,
    "page_y": 24,
    "section_x": 18,
    "section_y": 18,
    "card_x": 14,
    "card_y": 12,
    "gap": 12,
    "small_gap": 6,
    "compact_y": 6,
    "compact_x": 10,
}

LAYOUT = {
    "card_text_wrap": 315,
}

def apply_app_style(root):
    root.configure(bg=COLORS["app_bg"])

    style = ttk.Style()
    style.theme_use("clam")

    style.configure(
        "Research.TNotebook",
        background=COLORS["app_bg"],
        borderwidth=0,
    )

    style.configure(
        "Research.TNotebook.Tab",
        font=FONTS["body_bold"],
        padding=(18, 8),
        background=COLORS["tab_bg"],
        foreground=COLORS["sub_text"],
        borderwidth=1,
    )

    style.map(
        "Research.TNotebook.Tab",
        background=[("selected", COLORS["tab_selected"])],
        foreground=[("selected", COLORS["text"])],
    )


def frame(parent, bg="main_card", **kwargs):
    return tk.Frame(parent, bg=COLORS[bg], **kwargs)


def bordered_frame(parent, bg="card", border="border", thickness=1, **kwargs):
    return tk.Frame(
        parent,
        bg=COLORS[bg],
        highlightthickness=thickness,
        highlightbackground=COLORS[border],
        **kwargs,
    )


def scrollable_frame(parent, bg="main_card", bind_mousewheel=True, **pack_kwargs):
    outer = frame(parent, bg=bg)
    outer.pack(fill="both", expand=True, **pack_kwargs)

    canvas = tk.Canvas(
        outer,
        bg=COLORS[bg],
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

    content = frame(canvas, bg=bg)
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

    if bind_mousewheel:
        def on_mousewheel(event):
            if event.delta > 0:
                canvas.yview_scroll(-1, "units")
            elif event.delta < 0:
                canvas.yview_scroll(1, "units")

        def bind_wheel(_event=None):
            canvas.bind_all("<MouseWheel>", on_mousewheel)

        def unbind_wheel(_event=None):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", bind_wheel)
        canvas.bind("<Leave>", unbind_wheel)

    return content


def label(parent, text="", font="body", bg="panel", fg="text", **kwargs):
    return tk.Label(
        parent,
        text=text,
        font=FONTS[font],
        bg=COLORS[bg],
        fg=COLORS[fg],
        **kwargs,
    )


def variable_label(parent, textvariable, font="body", bg="panel", fg="text", **kwargs):
    return tk.Label(
        parent,
        textvariable=textvariable,
        font=FONTS[font],
        bg=COLORS[bg],
        fg=COLORS[fg],
        **kwargs,
    )


def entry(parent, textvariable, font="input", **kwargs):
    return tk.Entry(
        parent,
        textvariable=textvariable,
        font=FONTS[font],
        relief="solid",
        bd=1,
        bg=COLORS["card"],
        fg=COLORS["text"],
        insertbackground=COLORS["text"],
        highlightthickness=1,
        highlightbackground=COLORS["border"],
        highlightcolor=COLORS["accent"],
        **kwargs,
    )


def action_button(parent, text, command, big=False, **kwargs):
    button = tk.Button(
        parent,
        text=text,
        command=command,
        font=FONTS["button_big" if big else "button"],
        bg=COLORS["accent"],
        fg=COLORS["text"],
        activebackground=COLORS["accent_active"],
        activeforeground=COLORS["text"],
        relief="raised",
        bd=1,
        padx=16,
        pady=10 if big else 8,
        cursor="hand2",
        **kwargs,
    )

    _attach_button_feedback(
        button,
        normal_bg=COLORS["accent"],
        active_bg=COLORS["accent_active"],
    )

    return button


def sub_button(parent, text, command, **kwargs):
    button = tk.Button(
        parent,
        text=text,
        command=command,
        font=FONTS["button"],
        bg=COLORS["sub_button"],
        fg=COLORS["text"],
        activebackground=COLORS["sub_button_active"],
        activeforeground=COLORS["text"],
        relief="raised",
        bd=1,
        padx=16,
        pady=8,
        cursor="hand2",
        **kwargs,
    )

    _attach_button_feedback(
        button,
        normal_bg=COLORS["sub_button"],
        active_bg=COLORS["sub_button_active"],
    )

    return button

def _attach_button_feedback(button, normal_bg, active_bg):
    def on_press(_event):
        button.configure(
            bg=active_bg,
            relief="sunken",
        )

    def on_release(_event):
        button.configure(
            bg=normal_bg,
            relief="raised",
        )

    def on_enter(_event):
        button.configure(
            bg=active_bg,
        )

    def on_leave(_event):
        button.configure(
            bg=normal_bg,
            relief="raised",
        )

    button.bind("<ButtonPress-1>", on_press)
    button.bind("<ButtonRelease-1>", on_release)
    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)


def radio(parent, text, variable, value, command=None, bg="card", **kwargs):
    return tk.Radiobutton(
        parent,
        text=text,
        variable=variable,
        value=value,
        command=command,
        font=FONTS["body_bold"],
        bg=COLORS[bg],
        fg=COLORS["text"],
        activebackground=COLORS[bg],
        activeforeground=COLORS["text"],
        selectcolor=COLORS["card"],
        **kwargs,
    )

def scale(parent, variable, from_, to, command=None, orient="horizontal", **kwargs):
    return tk.Scale(
        parent,
        variable=variable,
        from_=from_,
        to=to,
        resolution=0.05,
        orient=orient,
        command=command,
        showvalue=False,
        bg=COLORS["panel"],
        fg=COLORS["text"],
        troughcolor=COLORS["soft_border"],
        highlightthickness=0,
        bd=0,
        **kwargs,
    )
