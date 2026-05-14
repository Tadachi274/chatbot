import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


def load_env_file():
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].strip()
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file()

from . import ui_style as ui
from .clients.tts_client import TTSClient
from .config import SAVE_JSON_DIR, get_person_key_from_speaker
from .config_default_profile import build_default_profile
from .config_example import EXAMPLE_SCENES, EXAMPLE_VENUES
from .profile_store import ProfileStore


class ComparisonApp(tk.Tk):
    MAX_USERS = 3

    def __init__(self):
        super().__init__()
        self.title("話し方比較")
        self.geometry(self.initial_geometry())
        self.minsize(1100, 620)
        ui.configure_density(self)
        ui.apply_app_style(self)

        self.tts_client = TTSClient()
        self.status_var = tk.StringVar(value="比較する場面とユーザーを選択してください")
        self.venue_var = tk.StringVar(value=EXAMPLE_VENUES[0]["label"])
        self.scene_var = tk.StringVar()
        self.user_slots = []
        self.columns_frame = None
        self.scene_combo = None
        self.venue_tabs = {}
        self.venue_notebook = None

        self.build_ui()
        self.refresh_scene_choices()

    def initial_geometry(self):
        width = min(1500, max(1100, self.winfo_screenwidth() - 80))
        height = min(980, max(620, self.winfo_screenheight() - 100))
        return f"{width}x{height}"

    def build_ui(self):
        outer = ui.frame(self, bg="app_bg")
        outer.pack(fill="both", expand=True, padx=ui.SPACING["small_gap"], pady=ui.SPACING["small_gap"])

        main = ui.bordered_frame(outer, bg="main_card", border="frame_border")
        main.pack(fill="both", expand=True)

        footer = ui.frame(main, bg="main_card")
        footer.pack(side="bottom", fill="x", padx=ui.SPACING["compact_x"], pady=(0, ui.SPACING["compact_y"]))
        ui.variable_label(
            footer,
            textvariable=self.status_var,
            font="small",
            bg="main_card",
            fg="sub_text",
        ).pack(side="left", fill="x", expand=True)

        page = ui.frame(main, bg="main_card")
        page.pack(side="top", fill="both", expand=True, padx=ui.SPACING["page_x"], pady=ui.SPACING["page_y"])

        self.build_selector_area(page)
        self.build_user_area(page)
        self.build_comparison_area(page)

    def build_selector_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        ui.label(section, text="ユーザー比較", font="page_title", bg="panel").pack(anchor="w")
        ui.label(
            section,
            text="場面を選び、最大3人の保存データを読み込んで、デフォルトと横並びで比較します。",
            font="body",
            bg="panel",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))

        self.venue_notebook = ttk.Notebook(section, style="Research.TNotebook")
        self.venue_notebook.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))
        self.venue_notebook.bind("<<NotebookTabChanged>>", self.on_venue_changed)
        for venue in EXAMPLE_VENUES:
            tab = ui.frame(self.venue_notebook, bg="panel")
            self.venue_notebook.add(tab, text=venue["label"])
            self.venue_tabs[str(tab)] = venue["label"]

        card = ui.bordered_frame(section, bg="card", border="border")
        card.pack(fill="x", pady=(0, ui.SPACING["section_y"]))
        ui.label(card, text="場面選択", font="small", bg="card", fg="muted").pack(
            anchor="w",
            padx=ui.SPACING["card_x"],
            pady=(ui.SPACING["compact_y"], ui.SPACING["small_gap"]),
        )
        self.scene_combo = ttk.Combobox(card, textvariable=self.scene_var, state="readonly")
        self.scene_combo.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["compact_y"]))
        self.scene_combo.bind("<<ComboboxSelected>>", lambda _event=None: self.render_comparison())

    def build_user_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="x")

        header = ui.frame(section, bg="panel")
        header.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))
        ui.label(header, text="ユーザー選択", font="section_title", bg="panel").pack(side="left")
        ui.sub_button(header, text="ユーザーフォルダを追加", command=self.add_user_folder).pack(side="right")
        ui.sub_button(header, text="JSONを追加", command=self.add_user_json).pack(
            side="right",
            padx=(0, ui.SPACING["small_gap"]),
        )

        self.user_list_frame = ui.bordered_frame(section, bg="card", border="border")
        self.user_list_frame.pack(fill="x", pady=(0, ui.SPACING["section_y"]))
        self.render_user_list()

    def build_comparison_area(self, parent):
        section = ui.frame(parent, bg="panel")
        section.pack(fill="both", expand=True)
        ui.label(section, text="比較", font="section_title", bg="panel").pack(
            anchor="w",
            pady=(0, ui.SPACING["small_gap"]),
        )
        self.columns_frame = ui.frame(section, bg="panel")
        self.columns_frame.pack(fill="both", expand=True)

    def on_venue_changed(self, _event=None):
        if not self.venue_notebook or not self.venue_notebook.select():
            return
        label = self.venue_tabs.get(self.venue_notebook.select())
        if label and label != self.venue_var.get():
            self.venue_var.set(label)
            self.refresh_scene_choices()

    def refresh_scene_choices(self):
        scenes = self.current_venue_scenes()
        values = [scene["title"] for scene in scenes]
        self.scene_combo.configure(values=values)
        if values:
            self.scene_var.set(values[0])
        self.render_comparison()
        self.render_user_list()

    def current_venue(self):
        label = self.venue_var.get()
        for venue in EXAMPLE_VENUES:
            if venue["label"] == label:
                return venue
        return EXAMPLE_VENUES[0]

    def current_venue_scenes(self):
        venue_id = self.current_venue()["id"]
        return [scene for scene in EXAMPLE_SCENES if scene["venue"] == venue_id]

    def current_scene(self):
        title = self.scene_var.get()
        scenes = self.current_venue_scenes()
        for scene in scenes:
            if scene["title"] == title:
                return scene
        return scenes[0]

    def add_user_folder(self):
        if len(self.user_slots) >= self.MAX_USERS:
            messagebox.showinfo("確認", "比較できるユーザーは3人までです。", parent=self)
            return
        path = filedialog.askdirectory(
            title="ユーザーフォルダを選択",
            initialdir=str(SAVE_JSON_DIR),
            parent=self,
        )
        if not path:
            return
        self.add_user_path(Path(path))

    def add_user_json(self):
        if len(self.user_slots) >= self.MAX_USERS:
            messagebox.showinfo("確認", "比較できるユーザーは3人までです。", parent=self)
            return
        path = filedialog.askopenfilename(
            title="店舗JSONを選択",
            initialdir=str(SAVE_JSON_DIR),
            filetypes=[("JSON files", "*.json")],
            parent=self,
        )
        if not path:
            return
        self.add_user_path(Path(path))

    def add_user_path(self, path):
        try:
            slot = self.load_user_slot(path)
        except Exception as e:
            messagebox.showerror("読み込みエラー", str(e), parent=self)
            return
        self.user_slots.append(slot)
        self.render_user_list()
        self.render_comparison()

    def load_user_slot(self, path):
        path = Path(path)
        venue = self.current_venue()
        if path.is_dir():
            profile_path = path / f"{venue['id']}.json"
            if not profile_path.exists():
                raise FileNotFoundError(f"{venue['label']}の設定が見つかりません: {profile_path.name}")
            user_label = path.name
        else:
            profile_path = path
            user_label = path.stem

        store = ProfileStore(path=profile_path)
        store.load_from(profile_path, persist_active=False)
        return {
            "label": user_label,
            "source": path,
            "profile_path": profile_path,
            "store": store,
        }

    def reload_user_slot_for_current_venue(self, slot):
        source = Path(slot["source"])
        venue = self.current_venue()
        if source.is_dir():
            profile_path = source / f"{venue['id']}.json"
            if not profile_path.exists():
                slot["missing"] = f"{venue['label']}未設定"
                return slot
        else:
            profile_path = source

        store = ProfileStore(path=profile_path)
        store.load_from(profile_path, persist_active=False)
        slot["profile_path"] = profile_path
        slot["store"] = store
        slot.pop("missing", None)
        return slot

    def render_user_list(self):
        for child in self.user_list_frame.winfo_children():
            child.destroy()

        if not self.user_slots:
            ui.label(
                self.user_list_frame,
                text="まだユーザーが選択されていません。デフォルトだけ表示しています。",
                font="body",
                bg="card",
                fg="sub_text",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])
            return

        for index, slot in enumerate(self.user_slots):
            row = ui.frame(self.user_list_frame, bg="card")
            row.pack(fill="x", padx=ui.SPACING["card_x"], pady=(ui.SPACING["compact_y"], 0))
            ui.label(row, text=f"{index + 1}. {slot['label']}", font="body_bold", bg="card").pack(side="left")
            ui.label(
                row,
                text=str(slot.get("profile_path", slot["source"])),
                font="small",
                bg="card",
                fg="muted",
            ).pack(side="left", fill="x", expand=True, padx=(ui.SPACING["gap"], 0))
            ui.sub_button(row, text="外す", command=lambda i=index: self.remove_user(i)).pack(side="right")

    def remove_user(self, index):
        if 0 <= index < len(self.user_slots):
            self.user_slots.pop(index)
        self.render_user_list()
        self.render_comparison()

    def comparison_slots(self):
        slots = [
            {
                "label": "デフォルト",
                "source": None,
                "profile_path": None,
                "store": self.default_store(),
                "default": True,
            }
        ]
        refreshed = []
        for slot in self.user_slots:
            refreshed.append(self.reload_user_slot_for_current_venue(slot))
        self.user_slots = refreshed
        slots.extend(self.user_slots[: self.MAX_USERS])
        return slots

    def default_store(self):
        store = ProfileStore()
        store.data = build_default_profile()
        store.example_results = {}
        store.current_venue_id = self.current_venue()["id"]
        store.current_venue_label = self.current_venue()["label"]
        return store

    def render_comparison(self):
        if self.columns_frame is None:
            return

        for child in self.columns_frame.winfo_children():
            child.destroy()

        slots = self.comparison_slots()
        self.render_user_list()
        for column, slot in enumerate(slots):
            card = ui.bordered_frame(self.columns_frame, bg="card", border="border")
            card.grid(row=0, column=column, sticky="nsew", padx=(0, ui.SPACING["small_gap"]))
            self.columns_frame.columnconfigure(column, weight=1, uniform="comparison")
            self.render_slot(card, slot)

    def render_slot(self, parent, slot):
        header = ui.frame(parent, bg="card")
        header.pack(fill="x", padx=ui.SPACING["card_x"], pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]))
        ui.label(header, text=slot["label"], font="section_title", bg="card").pack(side="left")

        if slot.get("missing"):
            ui.label(
                parent,
                text=slot["missing"],
                font="body_bold",
                bg="card",
                fg="sub_text",
            ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))
            return

        ui.sub_button(header, text="この話し方で試す", command=lambda s=slot: self.open_trial_window(s)).pack(side="right")
        self.render_profile_summary(parent, slot["store"].data)
        self.render_dialogue(parent, slot)

    def render_profile_summary(self, parent, profile):
        summary = " / ".join(
            [
                f"話者: {self.speaker_label(profile)}",
                f"敬語: {self.data_label(profile, 'politeness')}",
                f"親しみ: {self.data_label(profile, 'intimacy')}",
                f"語彙: {self.data_label(profile, 'vocabulary')}",
                f"長さ: {self.data_label(profile, 'length')}",
            ]
        )
        ui.label(
            parent,
            text=summary,
            font="small",
            bg="card",
            fg="sub_text",
            justify="left",
            wraplength=330,
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["small_gap"]))

    def render_dialogue(self, parent, slot):
        content = ui.scrollable_frame(parent, bg="card", pady=(0, ui.SPACING["card_y"]))
        for turn in self.slot_turns(slot):
            role = "客" if turn.get("role") == "customer" else "ロボット"
            bg = "card" if turn.get("role") == "customer" else "panel"
            bubble = ui.bordered_frame(content, bg=bg, border="border")
            bubble.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["small_gap"]))
            ui.label(bubble, text=role, font="small", bg=bg, fg="muted").pack(
                anchor="w",
                padx=ui.SPACING["compact_x"],
                pady=(ui.SPACING["compact_y"], 0),
            )
            ui.label(
                bubble,
                text=turn.get("text", turn.get("base_text", "")),
                font="body_bold" if turn.get("role") == "staff" else "body",
                bg=bg,
                fg="text",
                justify="left",
                wraplength=330,
            ).pack(anchor="w", padx=ui.SPACING["compact_x"], pady=(0, ui.SPACING["compact_y"]))

    def slot_turns(self, slot):
        scene = self.current_scene()
        if slot.get("default"):
            return self.base_turns(scene)

        store = slot["store"]
        record = (store.get_example_results() or {}).get(scene["id"], {})
        active = int(record.get("active", -1))
        versions = record.get("versions", [])
        if 0 <= active < len(versions):
            return versions[active].get("turns", self.base_turns(scene))
        return self.base_turns(scene)

    def base_turns(self, scene):
        turns = []
        for turn in scene.get("turns", []):
            data = dict(turn)
            if data.get("role") == "staff":
                data["text"] = data.get("base_text", data.get("text", ""))
            turns.append(data)
        return turns

    def open_trial_window(self, slot):
        if slot.get("missing"):
            return

        window = tk.Toplevel(self)
        window.title(f"接客例を試す - {slot['label']}")
        window.geometry(self.initial_geometry())
        window.minsize(980, 560)

        status_var = tk.StringVar(value=f"{slot['label']}の話し方を試します")
        footer = ui.frame(window, bg="main_card")
        footer.pack(side="bottom", fill="x", padx=ui.SPACING["compact_x"], pady=ui.SPACING["compact_y"])
        ui.variable_label(footer, textvariable=status_var, font="small", bg="main_card", fg="sub_text").pack(
            side="left",
            fill="x",
            expand=True,
        )
        ui.sub_button(footer, text="閉じる", command=window.destroy).pack(side="right")

        body = ui.frame(window, bg="main_card")
        body.pack(side="top", fill="both", expand=True)

        from .tabs.example_scene_tab import ExampleSceneTab

        tab = ExampleSceneTab(
            body,
            profile_store=slot["store"],
            status_var=status_var,
            tts_client=self.tts_client,
            venue_label=self.current_venue()["label"],
            default_only=False,
        )
        tab.pack(fill="both", expand=True)
        try:
            tab.scene_var.set(self.scene_var.get())
            tab.on_scene_changed()
        except Exception:
            pass

    def speaker_label(self, profile):
        speaker = profile.get("speaker", "")
        person = get_person_key_from_speaker(speaker)
        if person == "kenta":
            return "けんた"
        if person == "nozomi":
            return "のぞみ"
        return "未設定"

    def data_label(self, profile, key):
        value = profile.get(key, {}) or {}
        if isinstance(value, dict):
            return value.get("label", value.get("id", "未設定"))
        return str(value or "未設定")


if __name__ == "__main__":
    app = ComparisonApp()
    app.mainloop()
