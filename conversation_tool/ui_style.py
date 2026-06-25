import tkinter as tk
from tkinter import ttk


COLORS = {
    "app_bg": "#f3f5f8",
    "main_card": "#ffffff",
    "panel": "#ffffff",
    "card": "#ffffff",
    "rail": "#f7f9fc",
    "border": "#d8dee8",
    "soft_border": "#e9edf3",
    "text": "#1f2933",
    "sub_text": "#617083",
    "muted": "#8a95a5",
    "accent": "#1d73b7",
    "accent_active": "#155a92",
    "staff": "#0ea5e9",
    "staff_soft": "#e8f6fd",
    "customer": "#16a34a",
    "customer_soft": "#eaf8ef",
    "event_face": "#f9c74f",
    "event_voice": "#90be6d",
    "event_gaze": "#43aa8b",
    "event_nod": "#f9844a",
    "event_pause": "#9b5de5",
    "sub_button": "#eef2f7",
    "sub_button_active": "#e1e7ef",
}

FONTS = {
    "app_title": ("Yu Gothic UI", 21, "bold"),
    "page_title": ("Yu Gothic UI", 18, "bold"),
    "section_title": ("Yu Gothic UI", 13, "bold"),
    "body": ("Yu Gothic UI", 11),
    "body_bold": ("Yu Gothic UI", 11, "bold"),
    "small": ("Yu Gothic UI", 10),
    "input": ("Yu Gothic UI", 12),
    "button": ("Yu Gothic UI", 10, "bold"),
}

SPACING = {
    "page_x": 22,
    "page_y": 18,
    "section_x": 16,
    "section_y": 14,
    "card_x": 14,
    "card_y": 10,
    "gap": 10,
    "small_gap": 6,
}


def apply_app_style(root):
    root.configure(bg=COLORS["app_bg"])
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Research.TNotebook",
        background=COLORS["main_card"],
        borderwidth=0,
    )
    style.configure(
        "Research.TNotebook.Tab",
        font=FONTS["body_bold"],
        padding=(16, 7),
        background=COLORS["sub_button"],
        foreground=COLORS["sub_text"],
    )
    style.map(
        "Research.TNotebook.Tab",
        background=[("selected", COLORS["card"])],
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

    canvas = tk.Canvas(outer, bg=COLORS[bg], highlightthickness=0, bd=0)
    canvas.pack(side="left", fill="both", expand=True)

    scrollbar = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
    scrollbar.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=scrollbar.set)

    content = frame(canvas, bg=bg)
    canvas_window = canvas.create_window((0, 0), window=content, anchor="nw")

    def on_content_configure(_event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def on_canvas_configure(event):
        canvas.itemconfig(canvas_window, width=event.width)

    content.bind("<Configure>", on_content_configure)
    canvas.bind("<Configure>", on_canvas_configure)

    if bind_mousewheel:
        def pointer_inside_outer():
            try:
                x = outer.winfo_pointerx()
                y = outer.winfo_pointery()
                left = outer.winfo_rootx()
                top = outer.winfo_rooty()
                right = left + outer.winfo_width()
                bottom = top + outer.winfo_height()
                return left <= x <= right and top <= y <= bottom
            except tk.TclError:
                return False

        def on_mousewheel(event):
            if not pointer_inside_outer():
                return
            delta = getattr(event, "delta", 0)
            if delta == 0:
                return
            steps = int(-delta / 120) if abs(delta) >= 120 else (-1 if delta > 0 else 1)
            canvas.yview_scroll(steps, "units")
            return "break"

        def on_linux_mousewheel(event):
            if not pointer_inside_outer():
                return
            if event.num == 4:
                canvas.yview_scroll(-1, "units")
            elif event.num == 5:
                canvas.yview_scroll(1, "units")
            return "break"

        canvas.bind_all("<MouseWheel>", on_mousewheel, add="+")
        canvas.bind_all("<Shift-MouseWheel>", on_mousewheel, add="+")
        canvas.bind_all("<Button-4>", on_linux_mousewheel, add="+")
        canvas.bind_all("<Button-5>", on_linux_mousewheel, add="+")

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


def action_button(parent, text, command, **kwargs):
    return _button(
        parent,
        text=text,
        command=command,
        bg=COLORS["sub_button"],
        active_bg=COLORS["sub_button_active"],
        fg=COLORS["accent"],
        **kwargs,
    )


def sub_button(parent, text, command, **kwargs):
    return _button(
        parent,
        text=text,
        command=command,
        bg=COLORS["sub_button"],
        active_bg=COLORS["sub_button_active"],
        fg=COLORS["text"],
        **kwargs,
    )


def _button(parent, text, command, bg, active_bg, fg, **kwargs):
    button = tk.Button(
        parent,
        text=text,
        command=command,
        font=FONTS["button"],
        bg=bg,
        fg=fg,
        activebackground=active_bg,
        activeforeground=fg,
        relief="raised",
        bd=1,
        padx=14,
        pady=6,
        cursor="hand2",
        **kwargs,
    )

    def on_press(_event):
        button.configure(bg=active_bg, relief="sunken")

    def on_release(_event):
        button.configure(bg=bg, relief="raised")

    def on_enter(_event):
        button.configure(bg=active_bg)

    def on_leave(_event):
        button.configure(bg=bg, relief="raised")

    button.bind("<ButtonPress-1>", on_press)
    button.bind("<ButtonRelease-1>", on_release)
    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)
    return button


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


def scale(parent, variable, from_, to, command=None, orient="horizontal", resolution=0.05, **kwargs):
    return tk.Scale(
        parent,
        variable=variable,
        from_=from_,
        to=to,
        resolution=resolution,
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
