import copy
import time
import tkinter as tk
from tkinter import ttk, messagebox

from .. import ui_style as ui
from ..config import (
    DEFAULT_PAUSE_DURATION,
    DEFAULT_SENTENCE_DURATION,
    LANE_BY_ID,
    MIN_EVENT_TIME,
    SPEAKER_CUSTOMER,
    SPEAKER_LABELS,
    SPEAKER_STAFF,
    STAFF_EVENT_LANES,
    TIMELINE_MIN_SECONDS,
    TIMELINE_PIXELS_PER_SECOND,
    TIME_RESOLUTION,
    FACE_EXPRESSION_OPTIONS,
    face_axis_commands,
    default_face_data,
    default_voice_data,
    conversation_scene_options,
    voice_params_to_tts_instructions,
)
from ..panels.face_axis_editor_panel import FaceAxisEditorPanel
from ..panels.voice_editor_panel import VoiceEditorPanel


class ConversationEditorTab(tk.Frame):
    def __init__(self, parent, store, status_var, on_changed=None, on_try_robot=None):
        super().__init__(parent, bg=ui.COLORS["main_card"])
        self.store = store
        self.status_var = status_var
        self.on_changed = on_changed
        self.on_try_robot = on_try_robot
        self.scene_options = conversation_scene_options(self.store.data.get("scenario_id"))
        self.active_scene_id = self.initial_scene_id()
        self.ensure_scene_storage()
        self.load_scene_into_workspace(self.active_scene_id)
        self.type_var = tk.StringVar(value=self.current_conversation_type_label())
        self.default_face_var = tk.StringVar(value=self.current_default_face_label())
        self.selected_utterance_index = None
        self.selected_event_index = None
        self.text_vars = []
        self.event_drag = None
        self.segment_drag = None
        self.robot_client = None
        self.tts_client = None
        self.face_preview_last_t = 0.0
        self.face_preview_keepalive_after_id = None
        self.face_preview_keepalive_data = None
        self.face_preview_keepalive_axes = None
        self.face_preview_keepalive_active = False

        if not self.store.data.get("utterances"):
            self.add_initial_utterances()
            self.save_workspace_to_active_scene()
        else:
            self.migrate_utterances()
            self.save_workspace_to_active_scene()

        self.build_ui()

    def add_initial_utterances(self):
        self.store.data["utterances"] = [
            self.build_utterance(SPEAKER_STAFF, "いらっしゃいませ！"),
            self.build_utterance(SPEAKER_CUSTOMER, "チェックインお願いします"),
        ]

    def current_conversation_type_label(self):
        scene = self.scene_data(self.active_scene_id)
        saved_id = scene.get("conversation_type_id") or self.store.data.get("conversation_type_id")
        saved_label = scene.get("scenario_title") or self.store.data.get("scenario_title")
        for option in self.scene_options:
            if option["id"] == saved_id or option["label"] == saved_label:
                return option["label"]
        return self.scene_options[0]["label"]

    def initial_scene_id(self):
        saved_id = self.store.data.get("active_scene_id") or self.store.data.get("conversation_type_id")
        if self.scene_option_by_id(saved_id) is not None:
            return saved_id
        return self.scene_options[0]["id"]

    def scene_option_by_id(self, scene_id):
        for option in self.scene_options:
            if option["id"] == scene_id:
                return option
        return None

    def scene_option_by_label(self, label):
        for option in self.scene_options:
            if option["label"] == label:
                return option
        return self.scene_options[0]

    def ensure_scene_storage(self):
        scenes = self.store.data.setdefault("scenes", {})
        legacy_utterances = self.store.data.get("utterances")
        legacy_scene_id = self.store.data.get("conversation_type_id")
        if legacy_utterances and legacy_scene_id and legacy_scene_id not in scenes:
            scenes[legacy_scene_id] = {
                "scenario_title": self.store.data.get("scenario_title", legacy_scene_id),
                "conversation_type_id": legacy_scene_id,
                "conversation_intent": self.store.data.get("conversation_intent", "explanation"),
                "default_face_label": self.store.data.get("default_face_label", "ニュートラル"),
                "utterances": copy.deepcopy(legacy_utterances),
            }

        for option in self.scene_options:
            scenes.setdefault(
                option["id"],
                {
                    "scenario_title": option["label"],
                    "conversation_type_id": option["id"],
                    "conversation_intent": option["intent"],
                    "default_face_label": "ニュートラル",
                    "utterances": [],
                },
            )

    def scene_data(self, scene_id):
        self.ensure_scene_storage()
        option = self.scene_option_by_id(scene_id) or self.scene_options[0]
        return self.store.data["scenes"].setdefault(
            option["id"],
            {
                "scenario_title": option["label"],
                "conversation_type_id": option["id"],
                "conversation_intent": option["intent"],
                "default_face_label": "ニュートラル",
                "utterances": [],
            },
        )

    def load_scene_into_workspace(self, scene_id):
        option = self.scene_option_by_id(scene_id) or self.scene_options[0]
        scene = self.scene_data(option["id"])
        self.active_scene_id = option["id"]
        self.store.data["active_scene_id"] = option["id"]
        self.store.data["scenario_title"] = scene.get("scenario_title", option["label"])
        self.store.data["conversation_type_id"] = scene.get("conversation_type_id", option["id"])
        self.store.data["conversation_intent"] = scene.get("conversation_intent", option["intent"])
        self.store.data["default_face_label"] = scene.get("default_face_label", "ニュートラル")
        self.store.data["utterances"] = copy.deepcopy(scene.get("utterances", []))

    def save_workspace_to_active_scene(self):
        option = self.scene_option_by_id(self.active_scene_id) or self.scene_options[0]
        scene = self.scene_data(option["id"])
        scene["scenario_title"] = self.store.data.get("scenario_title", option["label"])
        scene["conversation_type_id"] = self.store.data.get("conversation_type_id", option["id"])
        scene["conversation_intent"] = self.store.data.get("conversation_intent", option["intent"])
        scene["default_face_label"] = self.store.data.get("default_face_label", "ニュートラル")
        scene["utterances"] = copy.deepcopy(self.store.data.get("utterances", []))
        self.store.data["active_scene_id"] = option["id"]


    def current_default_face_label(self):
        scene = self.scene_data(self.active_scene_id)
        label = scene.get("default_face_label") or self.store.data.get("default_face_label") or "ニュートラル"
        return label if label in FACE_EXPRESSION_OPTIONS else "ニュートラル"


    def migrate_utterances(self):
        for utterance in self.store.data.get("utterances", []):
            if "segments" not in utterance:
                text = utterance.get("text", "")
                utterance["segments"] = [self.build_sentence_segment(text, utterance.get("speaker") == SPEAKER_STAFF)]
            if utterance.get("speaker") == SPEAKER_STAFF:
                utterance["events"] = [
                    event
                    for event in utterance.get("events", [])
                    if event.get("lane") in LANE_BY_ID
                ]
                for event in utterance["events"]:
                    if event.get("lane") == "face" and "face" not in event:
                        event["face"] = default_face_data(event.get("value", "笑顔"))
                        event["value"] = event["face"]["label"]
                for segment in utterance.get("segments", []):
                    if segment.get("type") == "sentence" and "voice" not in segment:
                        segment["voice"] = default_voice_data()
                    if segment.get("type") == "pause" and "duration" not in segment:
                        segment["duration"] = DEFAULT_PAUSE_DURATION
            else:
                utterance["text"] = self.customer_text(utterance)
                utterance["segments"] = []
            utterance["duration"] = self.calculate_utterance_duration(utterance)


    def customer_text(self, utterance):
        if utterance.get("text"):
            return utterance.get("text", "")

        parts = [
            segment.get("text", "")
            for segment in utterance.get("segments", [])
            if segment.get("type") == "sentence"
        ]
        return "".join(parts)


    def build_ui(self):
        root = ui.frame(self, bg="app_bg")
        root.pack(fill="both", expand=True, padx=ui.SPACING["small_gap"], pady=ui.SPACING["small_gap"])

        main = ui.bordered_frame(root, bg="main_card", border="border", thickness=1)
        main.pack(fill="both", expand=True)

        header = ui.frame(main, bg="main_card")
        header.pack(fill="x", padx=ui.SPACING["page_x"], pady=(ui.SPACING["page_y"], ui.SPACING["gap"]))

        ui.label(header, text="シナリオ", font="app_title", bg="main_card").pack(side="left")
        type_combo = ttk.Combobox(
            header,
            textvariable=self.type_var,
            values=[option["label"] for option in self.scene_options],
            state="readonly",
            width=32,
        )
        type_combo.pack(side="left", padx=(ui.SPACING["gap"], ui.SPACING["section_y"]))
        type_combo.bind("<<ComboboxSelected>>", lambda _event=None: self.on_scene_selected())

        ui.label(header, text="基本表情", font="small", bg="main_card", fg="sub_text").pack(side="left")
        default_face_combo = ttk.Combobox(
            header,
            textvariable=self.default_face_var,
            values=FACE_EXPRESSION_OPTIONS,
            state="readonly",
            width=18,
        )
        default_face_combo.pack(side="left", padx=(ui.SPACING["small_gap"], ui.SPACING["section_y"]))
        default_face_combo.bind("<<ComboboxSelected>>", lambda _event=None: self.on_default_face_selected())

        ui.sub_button(header, text="店員発話を追加", command=lambda: self.add_utterance(SPEAKER_STAFF)).pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.sub_button(header, text="客発話を追加", command=lambda: self.add_utterance(SPEAKER_CUSTOMER)).pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.action_button(header, text="保存", command=self.save).pack(side="right")

        body = ui.frame(main, bg="main_card")
        body.pack(fill="both", expand=True, padx=ui.SPACING["page_x"], pady=(0, ui.SPACING["gap"]))

        self.timeline_content = ui.scrollable_frame(body, bg="main_card")

        footer = ui.frame(main, bg="main_card")
        footer.pack(fill="x", padx=ui.SPACING["page_x"], pady=(0, ui.SPACING["section_y"]))
        ui.action_button(footer, text="ロボットで試す", command=self.try_robot).pack(side="right")

        self.render_utterances()


    def render_utterances(self):
        for child in self.timeline_content.winfo_children():
            child.destroy()

        self.text_vars = []
        utterances = self.store.data.get("utterances", [])

        for index, utterance in enumerate(utterances):
            self.render_utterance_card(index, utterance)

        add_row = ui.frame(self.timeline_content, bg="main_card")
        add_row.pack(fill="x", pady=(ui.SPACING["gap"], ui.SPACING["section_y"]))
        ui.sub_button(add_row, text="+ 店員発話", command=lambda: self.add_utterance(SPEAKER_STAFF)).pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.sub_button(add_row, text="+ 客発話", command=lambda: self.add_utterance(SPEAKER_CUSTOMER)).pack(side="left")


    def render_utterance_card(self, index, utterance):
        speaker = utterance.get("speaker", SPEAKER_STAFF)
        is_staff = speaker == SPEAKER_STAFF
        accent = "staff" if is_staff else "customer"
        soft = "staff_soft" if is_staff else "customer_soft"

        card = ui.bordered_frame(self.timeline_content, bg="card", border=accent, thickness=2)
        card.pack(fill="x", pady=(0, ui.SPACING["section_y"]))

        head = ui.frame(card, bg=soft)
        head.pack(fill="x")

        ui.label(
            head,
            text=SPEAKER_LABELS.get(speaker, "発話"),
            font="section_title",
            bg=soft,
        ).pack(side="left", padx=ui.SPACING["card_x"], pady=ui.SPACING["small_gap"])

        ui.sub_button(head, text="上へ", command=lambda i=index: self.move_utterance(i, -1)).pack(
            side="right", padx=(0, ui.SPACING["small_gap"]), pady=ui.SPACING["small_gap"]
        )
        ui.sub_button(head, text="下へ", command=lambda i=index: self.move_utterance(i, 1)).pack(
            side="right", padx=(0, ui.SPACING["small_gap"]), pady=ui.SPACING["small_gap"]
        )
        ui.sub_button(head, text="削除", command=lambda i=index: self.delete_utterance(i)).pack(
            side="right", padx=(0, ui.SPACING["card_x"]), pady=ui.SPACING["small_gap"]
        )
        if is_staff:
            ui.sub_button(head, text="この発話を試す", command=lambda i=index: self.try_staff_utterances([i])).pack(
                side="right", padx=(0, ui.SPACING["small_gap"]), pady=ui.SPACING["small_gap"]
            )
            consecutive_indices = self.consecutive_staff_indices(index)
            if len(consecutive_indices) > 1:
                ui.sub_button(
                    head,
                    text="連続店員を試す",
                    command=lambda indices=consecutive_indices: self.try_staff_utterances(indices),
                ).pack(side="right", padx=(0, ui.SPACING["small_gap"]), pady=ui.SPACING["small_gap"])

        if is_staff:
            self.render_timeline(card, index, utterance, is_staff)
        else:
            self.render_customer_text_editor(card, index, utterance)


    def render_customer_text_editor(self, parent, utterance_index, utterance):
        editor = ui.frame(parent, bg="card")
        editor.pack(fill="x", padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])

        text_var = tk.StringVar(value=self.customer_text(utterance))
        self.text_vars.append(("customer_text", utterance_index, 0, text_var))
        ui.label(editor, text="言葉", font="body_bold", bg="card", fg="customer", width=5, anchor="w").pack(side="left")
        text_entry = ui.entry(editor, text_var, font="input")
        text_entry.pack(side="left", fill="x", expand=True)
        text_entry.bind("<FocusOut>", lambda _event=None: self.sync_texts())


    def render_timeline(self, parent, utterance_index, utterance, is_staff):
        timeline = ui.frame(parent, bg="card")
        timeline.pack(fill="x", padx=ui.SPACING["card_x"], pady=ui.SPACING["card_y"])

        toolbar = ui.frame(timeline, bg="card")
        toolbar.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))

        ui.sub_button(toolbar, text="+ 文", command=lambda i=utterance_index: self.add_segment(i, "sentence")).pack(
            side="left", padx=(0, ui.SPACING["small_gap"])
        )
        ui.sub_button(toolbar, text="+ 間", command=lambda i=utterance_index: self.add_segment(i, "pause")).pack(
            side="left", padx=(0, ui.SPACING["gap"])
        )

        if is_staff:
            for lane in STAFF_EVENT_LANES:
                ui.sub_button(
                    toolbar,
                    text=f"+ {lane['label']}",
                    command=lambda i=utterance_index, lane_id=lane["id"]: self.add_event(i, lane_id),
                ).pack(side="left", padx=(0, ui.SPACING["small_gap"]))

        canvas_width = self.timeline_width(utterance)
        event_lane_count = len(STAFF_EVENT_LANES) if is_staff else 0
        canvas_height = 44 + event_lane_count * 34
        canvas = tk.Canvas(
            timeline,
            height=canvas_height,
            bg=ui.COLORS["rail"],
            highlightthickness=1,
            highlightbackground=ui.COLORS["soft_border"],
            bd=0,
        )
        canvas.pack(fill="x", expand=True)

        self.draw_timeline(canvas, utterance_index, utterance, canvas_width, canvas_height, is_staff)


    def draw_timeline(self, canvas, utterance_index, utterance, canvas_width, canvas_height, is_staff):
        left = 92
        top = 14
        lane_h = 30
        utterance["duration"] = self.calculate_utterance_duration(utterance)
        duration = max(self.calculate_timeline_duration(utterance), TIMELINE_MIN_SECONDS)
        total_width = max(canvas_width, left + int(duration * TIMELINE_PIXELS_PER_SECOND) + 24)
        canvas.configure(scrollregion=(0, 0, total_width, canvas_height))

        canvas.create_text(14, top + 12, text="言葉", anchor="w", fill=ui.COLORS["sub_text"], font=ui.FONTS["small"])
        x = left
        for segment_index, segment in enumerate(utterance.get("segments", [])):
            start = self.segment_start_time(utterance, segment_index)
            segment_duration = float(segment.get("duration", DEFAULT_SENTENCE_DURATION))
            width = max(46, int(segment_duration * TIMELINE_PIXELS_PER_SECOND))
            is_pause = segment.get("type") == "pause"
            color = ui.COLORS["event_pause"] if is_pause else ui.COLORS["staff"]
            content_label = "間" if is_pause else segment.get("text", "")
            label = f"{start:.1f}s {content_label} ({segment_duration:.1f}s)"
            tag = f"segment_{utterance_index}_{segment_index}"
            canvas.create_rectangle(x, top, x + width, top + 24, fill=color, outline=color, tags=tag)
            canvas.create_text(
                x + 8,
                top + 12,
                text=label,
                anchor="w",
                fill="#ffffff",
                font=ui.FONTS["body_bold"] if not is_pause else ui.FONTS["small"],
                tags=tag,
            )
            canvas.tag_bind(
                tag,
                "<ButtonPress-1>",
                lambda tk_event, i=utterance_index, s=segment_index, start_x=x, w=width: self.start_segment_drag(
                    tk_event,
                    canvas,
                    i,
                    s,
                    start_x,
                    w,
                ),
            )
            canvas.tag_bind(tag, "<B1-Motion>", self.drag_segment_bar)
            canvas.tag_bind(tag, "<ButtonRelease-1>", self.finish_segment_drag)
            x += width

        if not is_staff:
            return

        events = utterance.get("events", [])
        for lane_index, lane in enumerate(STAFF_EVENT_LANES):
            y = top + 38 + lane_index * lane_h
            canvas.create_text(14, y + 12, text=lane["label"], anchor="w", fill=ui.COLORS["sub_text"], font=ui.FONTS["small"])
            canvas.create_line(left, y + 25, total_width - 18, y + 25, fill=ui.COLORS["soft_border"])

            for event_index, event in enumerate(events):
                if event.get("lane") != lane["id"]:
                    continue
                start = max(MIN_EVENT_TIME, float(event.get("time", 0.0)))
                width = max(44, int(float(event.get("duration", DEFAULT_PAUSE_DURATION)) * TIMELINE_PIXELS_PER_SECOND))
                x = left + int(start * TIMELINE_PIXELS_PER_SECOND)
                color = ui.COLORS.get(f"event_{lane['id']}", ui.COLORS["accent"])
                is_selected = (
                    self.selected_utterance_index == utterance_index
                    and self.selected_event_index == event_index
                )
                outline = "#111827" if is_selected else color
                tag = f"event_{utterance_index}_{event_index}"
                canvas.create_rectangle(
                    x,
                    y,
                    x + width,
                    y + 24,
                    fill=color,
                    outline=outline,
                    width=2 if is_selected else 1,
                    tags=tag,
                )
                event_label = (
                    f"{start:.1f}s {event.get('value', lane['default'])} "
                    f"({float(event.get('duration', DEFAULT_PAUSE_DURATION)):.1f}s)"
                )
                canvas.create_text(
                    x + 6,
                    y + 12,
                    text=event_label,
                    anchor="w",
                    fill="#ffffff",
                    font=ui.FONTS["small"],
                    tags=tag,
                )
                canvas.tag_bind(
                    tag,
                    "<ButtonPress-1>",
                    lambda tk_event, i=utterance_index, e=event_index, start_x=x, w=width: self.start_event_drag(
                        tk_event,
                        canvas,
                        i,
                        e,
                        start_x,
                        w,
                    ),
                )
                canvas.tag_bind(tag, "<B1-Motion>", self.drag_event_bar)
                canvas.tag_bind(tag, "<ButtonRelease-1>", self.finish_event_drag)


    def segment_start_time(self, utterance, segment_index):
        start = 0.0
        for segment in utterance.get("segments", [])[:segment_index]:
            start += float(segment.get("duration", DEFAULT_PAUSE_DURATION))
        return round(start, 2)


    def start_segment_drag(self, tk_event, canvas, utterance_index, segment_index, bar_x, bar_width):
        self.sync_texts()
        segment = self.store.data["utterances"][utterance_index]["segments"][segment_index]
        edge_threshold = 8
        click_x = canvas.canvasx(tk_event.x)
        if abs(click_x - bar_x) <= edge_threshold:
            mode = "resize_left"
        elif abs(click_x - (bar_x + bar_width)) <= edge_threshold:
            mode = "resize_right"
        else:
            mode = "move"

        self.segment_drag = {
            "canvas": canvas,
            "tag": f"segment_{utterance_index}_{segment_index}",
            "utterance_index": utterance_index,
            "segment_index": segment_index,
            "mode": mode,
            "mouse_x": click_x,
            "bar_x": bar_x,
            "bar_width": bar_width,
            "duration": float(segment.get("duration", DEFAULT_PAUSE_DURATION)),
            "moved": False,
        }
        canvas.configure(cursor="sb_h_double_arrow" if mode.startswith("resize") else "fleur")
        return "break"


    def drag_segment_bar(self, tk_event):
        if self.segment_drag is None:
            return "break"

        drag = self.segment_drag
        canvas = drag["canvas"]
        current_x = canvas.canvasx(tk_event.x)
        delta_px = current_x - drag["mouse_x"]
        if abs(delta_px) < 2:
            return "break"

        drag["moved"] = True
        utterance = self.store.data["utterances"][drag["utterance_index"]]
        segment = utterance["segments"][drag["segment_index"]]

        if drag["mode"] == "move":
            dx = delta_px
            dw = 0
        elif drag["mode"] == "resize_left":
            delta_sec = delta_px / TIMELINE_PIXELS_PER_SECOND
            previous = self.previous_segment_for_resize(utterance, drag["segment_index"])
            if previous is not None:
                previous_duration = float(previous.get("duration", DEFAULT_PAUSE_DURATION))
                new_previous_duration = max(TIME_RESOLUTION, previous_duration + delta_sec)
                actual_delta = new_previous_duration - previous_duration
                new_duration = max(TIME_RESOLUTION, drag["duration"] - actual_delta)
                previous["duration"] = self.round_time(new_previous_duration)
            else:
                new_duration = max(TIME_RESOLUTION, drag["duration"] + delta_sec)
            segment["duration"] = self.round_time(new_duration)
            new_width = max(46, int(segment["duration"] * TIMELINE_PIXELS_PER_SECOND))
            dx = drag["bar_width"] - new_width
            dw = new_width - drag["bar_width"]
        else:
            delta_sec = delta_px / TIMELINE_PIXELS_PER_SECOND
            new_duration = max(TIME_RESOLUTION, drag["duration"] + delta_sec)
            segment["duration"] = self.round_time(new_duration)
            new_width = max(46, int(segment["duration"] * TIMELINE_PIXELS_PER_SECOND))
            dx = 0
            dw = new_width - drag["bar_width"]

        for item_id in canvas.find_withtag(drag["tag"]):
            coords = canvas.coords(item_id)
            if len(coords) == 4:
                canvas.coords(item_id, coords[0] + dx, coords[1], coords[2] + dx + dw, coords[3])
            elif len(coords) == 2:
                canvas.coords(item_id, coords[0] + dx, coords[1])

        return "break"


    def previous_segment_for_resize(self, utterance, segment_index):
        if segment_index <= 0:
            return None
        segments = utterance.get("segments", [])
        if segment_index - 1 >= len(segments):
            return None
        return segments[segment_index - 1]


    def finish_segment_drag(self, tk_event):
        if self.segment_drag is None:
            return "break"

        drag = self.segment_drag
        canvas = drag["canvas"]
        utterance_index = drag["utterance_index"]
        segment_index = drag["segment_index"]
        mode = drag["mode"]
        moved = drag["moved"]
        self.segment_drag = None
        canvas.configure(cursor="")

        if not moved:
            self.open_segment_editor(utterance_index, segment_index)
            return "break"

        utterance = self.store.data["utterances"][utterance_index]
        if mode == "move":
            target_x = canvas.canvasx(tk_event.x)
            target_index = self.segment_index_for_x(utterance, target_x)
            self.move_segment_to_index(utterance, segment_index, target_index)

        utterance["duration"] = self.calculate_utterance_duration(utterance)
        self.render_utterances()
        self.status_var.set("文/間バーを更新しました")
        return "break"


    def segment_index_for_x(self, utterance, x):
        left = 92
        current_x = left
        for index, segment in enumerate(utterance.get("segments", [])):
            width = max(46, int(float(segment.get("duration", DEFAULT_PAUSE_DURATION)) * TIMELINE_PIXELS_PER_SECOND))
            if x < current_x + width / 2:
                return index
            current_x += width
        return max(0, len(utterance.get("segments", [])) - 1)


    def move_segment_to_index(self, utterance, source_index, target_index):
        segments = utterance.get("segments", [])
        if source_index < 0 or source_index >= len(segments):
            return
        target_index = max(0, min(target_index, len(segments) - 1))
        if source_index == target_index:
            return
        segment = segments.pop(source_index)
        segments.insert(target_index, segment)


    def start_event_drag(self, tk_event, canvas, utterance_index, event_index, bar_x, bar_width):
        self.sync_texts()
        event = self.store.data["utterances"][utterance_index]["events"][event_index]
        edge_threshold = 8
        click_x = canvas.canvasx(tk_event.x)
        if abs(click_x - bar_x) <= edge_threshold:
            mode = "resize_left"
        elif abs(click_x - (bar_x + bar_width)) <= edge_threshold:
            mode = "resize_right"
        else:
            mode = "move"

        self.event_drag = {
            "canvas": canvas,
            "tag": f"event_{utterance_index}_{event_index}",
            "utterance_index": utterance_index,
            "event_index": event_index,
            "mode": mode,
            "mouse_x": click_x,
            "bar_x": bar_x,
            "bar_width": bar_width,
            "time": float(event.get("time", 0.0)),
            "duration": float(event.get("duration", DEFAULT_PAUSE_DURATION)),
            "moved": False,
        }
        canvas.configure(cursor="sb_h_double_arrow" if mode.startswith("resize") else "fleur")
        return "break"


    def drag_event_bar(self, tk_event):
        if self.event_drag is None:
            return "break"

        drag = self.event_drag
        canvas = drag["canvas"]
        current_x = canvas.canvasx(tk_event.x)
        delta_px = current_x - drag["mouse_x"]
        if abs(delta_px) < 2:
            return "break"

        drag["moved"] = True
        delta_sec = delta_px / TIMELINE_PIXELS_PER_SECOND
        utterance = self.store.data["utterances"][drag["utterance_index"]]
        event = utterance["events"][drag["event_index"]]
        max_time = self.calculate_timeline_duration(utterance) + 3.0

        if drag["mode"] == "move":
            new_time = max(MIN_EVENT_TIME, min(max_time, drag["time"] + delta_sec))
            new_duration = drag["duration"]
        elif drag["mode"] == "resize_left":
            event_end = drag["time"] + drag["duration"]
            new_time = max(MIN_EVENT_TIME, min(event_end - TIME_RESOLUTION, drag["time"] + delta_sec))
            new_duration = max(TIME_RESOLUTION, event_end - new_time)
        else:
            new_time = drag["time"]
            new_duration = max(TIME_RESOLUTION, drag["duration"] + delta_sec)

        event["time"] = self.round_time(new_time)
        event["duration"] = max(TIME_RESOLUTION, self.round_time(new_duration))

        new_x = 92 + int(event["time"] * TIMELINE_PIXELS_PER_SECOND)
        new_width = max(44, int(event["duration"] * TIMELINE_PIXELS_PER_SECOND))
        dx = new_x - drag["bar_x"]
        dw = new_width - drag["bar_width"]

        for item_id in canvas.find_withtag(drag["tag"]):
            coords = canvas.coords(item_id)
            if len(coords) == 4:
                canvas.coords(item_id, coords[0] + dx, coords[1], coords[2] + dx + dw, coords[3])
            elif len(coords) == 2:
                canvas.coords(item_id, coords[0] + dx, coords[1])

        drag["bar_x"] = new_x
        drag["bar_width"] = new_width
        return "break"


    def finish_event_drag(self, _tk_event):
        if self.event_drag is None:
            return "break"

        drag = self.event_drag
        canvas = drag["canvas"]
        utterance_index = drag["utterance_index"]
        event_index = drag["event_index"]
        moved = drag["moved"]
        self.event_drag = None
        canvas.configure(cursor="")

        if moved:
            self.selected_utterance_index = utterance_index
            self.selected_event_index = event_index
            self.render_utterances()
            self.status_var.set("バーの位置/長さを更新しました")
        else:
            self.open_event_editor(utterance_index, event_index)
        return "break"


    def timeline_width(self, utterance):
        duration = max(self.calculate_timeline_duration(utterance), TIMELINE_MIN_SECONDS)
        return 120 + int(duration * TIMELINE_PIXELS_PER_SECOND)


    def build_utterance(self, speaker, text=""):
        if speaker == SPEAKER_CUSTOMER:
            return {
                "speaker": speaker,
                "text": text,
            }

        utterance = {
            "speaker": speaker,
            "segments": [self.build_sentence_segment(text, True)],
            "duration": DEFAULT_SENTENCE_DURATION,
        }
        if speaker == SPEAKER_STAFF:
            utterance["events"] = []
        return utterance


    def build_sentence_segment(self, text="", include_voice=False):
        segment = {
            "type": "sentence",
            "text": text,
            "duration": DEFAULT_SENTENCE_DURATION,
        }
        if include_voice:
            segment["voice"] = default_voice_data()
        return segment


    def build_pause_segment(self):
        return {
            "type": "pause",
            "duration": DEFAULT_PAUSE_DURATION,
        }


    def calculate_utterance_duration(self, utterance):
        if utterance.get("speaker") == SPEAKER_CUSTOMER:
            return 0.0

        duration = 0.0
        for segment in utterance.get("segments", []):
            duration += float(segment.get("duration", DEFAULT_PAUSE_DURATION))
        return round(max(duration, TIME_RESOLUTION), 2)


    def calculate_timeline_duration(self, utterance):
        duration = self.calculate_utterance_duration(utterance)
        for event in utterance.get("events", []):
            end_time = float(event.get("time", 0.0)) + float(event.get("duration", DEFAULT_PAUSE_DURATION))
            duration = max(duration, end_time)
        return round(max(duration, TIME_RESOLUTION), 2)


    def add_utterance(self, speaker):
        self.sync_texts()
        self.store.data.setdefault("utterances", []).append(self.build_utterance(speaker))
        self.selected_utterance_index = None
        self.selected_event_index = None
        self.render_utterances()
        self.status_var.set(f"{SPEAKER_LABELS[speaker]}を追加しました")


    def delete_utterance(self, index):
        self.sync_texts()
        utterances = self.store.data.get("utterances", [])
        if index < 0 or index >= len(utterances):
            return
        if not messagebox.askyesno("削除確認", "この発話を削除しますか？", parent=self):
            return
        del utterances[index]
        self.selected_utterance_index = None
        self.selected_event_index = None
        self.render_utterances()
        self.status_var.set("発話を削除しました")


    def move_utterance(self, index, direction):
        self.sync_texts()
        utterances = self.store.data.get("utterances", [])
        target = index + direction
        if index < 0 or target < 0 or index >= len(utterances) or target >= len(utterances):
            return
        utterances[index], utterances[target] = utterances[target], utterances[index]
        self.render_utterances()
        self.status_var.set("発話の順番を変更しました")


    def add_event(self, utterance_index, lane_id):
        self.sync_texts()
        utterances = self.store.data.get("utterances", [])
        if utterance_index < 0 or utterance_index >= len(utterances):
            return

        utterance = utterances[utterance_index]
        if utterance.get("speaker") != SPEAKER_STAFF:
            return

        lane = LANE_BY_ID[lane_id]
        event = {
            "lane": lane_id,
            "time": self.next_event_time(utterance, lane_id),
            "duration": 1.0,
            "value": lane["default"],
        }
        if lane_id == "face":
            event["face"] = default_face_data(lane["default"])
        utterance.setdefault("events", []).append(event)
        self.selected_utterance_index = utterance_index
        self.selected_event_index = len(utterance["events"]) - 1
        self.render_utterances()
        self.open_event_editor(self.selected_utterance_index, self.selected_event_index)


    def next_event_time(self, utterance, lane_id):
        lane_events = [
            event
            for event in utterance.get("events", [])
            if event.get("lane") == lane_id
        ]
        if not lane_events:
            return 0.0

        latest = max(
            float(event.get("time", 0.0)) + float(event.get("duration", 1.0))
            for event in lane_events
        )
        utterance_end = self.calculate_utterance_duration(utterance)
        return round(min(max(0.0, latest + 0.2), max(0.0, utterance_end - 0.2)), 1)


    def add_segment(self, utterance_index, segment_type):
        self.sync_texts()
        utterances = self.store.data.get("utterances", [])
        if utterance_index < 0 or utterance_index >= len(utterances):
            return

        utterance = utterances[utterance_index]
        if segment_type == "pause":
            utterance.setdefault("segments", []).append(self.build_pause_segment())
            self.status_var.set("間を追加しました")
        else:
            utterance.setdefault("segments", []).append(
                self.build_sentence_segment("", utterance.get("speaker") == SPEAKER_STAFF)
            )
            self.status_var.set("文を追加しました")
        utterance["duration"] = self.calculate_utterance_duration(utterance)
        self.render_utterances()


    def delete_segment(self, utterance_index, segment_index):
        self.sync_texts()
        utterances = self.store.data.get("utterances", [])
        if utterance_index < 0 or utterance_index >= len(utterances):
            return
        segments = utterances[utterance_index].get("segments", [])
        if segment_index < 0 or segment_index >= len(segments):
            return
        if len(segments) <= 1:
            messagebox.showwarning("確認", "発話には少なくとも1つの文または間が必要です")
            return
        del segments[segment_index]
        utterances[utterance_index]["duration"] = self.calculate_utterance_duration(utterances[utterance_index])
        self.render_utterances()
        self.status_var.set("文/間を削除しました")


    def open_segment_editor(self, utterance_index, segment_index):
        utterance = self.store.data["utterances"][utterance_index]
        segment = utterance["segments"][segment_index]
        if segment.get("type") == "pause":
            self.open_pause_editor(utterance_index, segment_index)
        else:
            self.open_voice_editor(utterance_index, segment_index)


    def open_pause_editor(self, utterance_index, segment_index):
        self.sync_texts()
        utterance = self.store.data["utterances"][utterance_index]
        segment = utterance["segments"][segment_index]

        dialog = tk.Toplevel(self)
        dialog.title("間を編集")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        body = ui.frame(dialog, bg="main_card")
        body.pack(fill="both", expand=True, padx=22, pady=18)
        ui.label(body, text="間を編集", font="page_title", bg="main_card").pack(anchor="w")

        duration_var = tk.StringVar(value=str(segment.get("duration", DEFAULT_PAUSE_DURATION)))
        row = ui.frame(body, bg="main_card")
        row.pack(fill="x", pady=(ui.SPACING["section_y"], 0))
        ui.label(row, text="長さ秒", font="body_bold", bg="main_card", width=8, anchor="w").pack(side="left")
        ui.entry(row, duration_var, width=10).pack(side="left")

        actions = ui.frame(body, bg="main_card")
        actions.pack(fill="x", pady=(ui.SPACING["section_y"], 0))

        def save_pause():
            try:
                segment["duration"] = max(TIME_RESOLUTION, self.round_time(float(duration_var.get())))
            except ValueError:
                messagebox.showerror("入力エラー", "長さ秒は数値で入力してください")
                return
            utterance["duration"] = self.calculate_utterance_duration(utterance)
            dialog.destroy()
            self.render_utterances()
            self.status_var.set("間を更新しました")

        ui.sub_button(actions, text="戻る", command=dialog.destroy).pack(
            side="left"
        )
        ui.sub_button(actions, text="削除", command=lambda: self.delete_segment_from_dialog(dialog, utterance_index, segment_index)).pack(
            side="left", padx=(ui.SPACING["small_gap"], 0)
        )
        ui.action_button(actions, text="更新", command=save_pause).pack(side="right")


    def delete_segment_from_dialog(self, dialog, utterance_index, segment_index):
        if not messagebox.askyesno("削除確認", "この要素を削除しますか？", parent=dialog):
            return
        dialog.destroy()
        self.delete_segment(utterance_index, segment_index)


    def open_voice_editor(self, utterance_index, segment_index):
        self.sync_texts()
        utterance = self.store.data["utterances"][utterance_index]
        segment = utterance["segments"][segment_index]
        if segment.get("type") != "sentence":
            return
        if "voice" not in segment:
            segment["voice"] = default_voice_data()

        dialog = tk.Toplevel(self)
        is_staff = utterance.get("speaker") == SPEAKER_STAFF
        dialog.title("文を編集")
        dialog.transient(self)
        dialog.grab_set()
        if is_staff:
            height = min(820, max(700, dialog.winfo_screenheight() - 120))
            dialog.geometry(f"760x{height}")
            dialog.minsize(720, 680)
        else:
            dialog.geometry("560x240")

        body = ui.frame(dialog, bg="main_card")
        body.pack(fill="both", expand=True, padx=22, pady=18)

        ui.label(body, text="文と声色" if is_staff else "文を編集", font="page_title", bg="main_card").pack(anchor="w")

        text_var = tk.StringVar(value=segment.get("text", ""))
        text_row = ui.frame(body, bg="main_card")
        text_row.pack(fill="x", pady=(ui.SPACING["section_y"], ui.SPACING["gap"]))
        ui.label(text_row, text="言葉", font="body_bold", bg="main_card", width=6, anchor="w").pack(side="left")
        ui.entry(text_row, text_var, font="input").pack(side="left", fill="x", expand=True)

        actions = ui.frame(body, bg="main_card")
        actions.pack(side="bottom", fill="x", pady=(ui.SPACING["section_y"], 0))

        panel = None
        if is_staff:
            panel_area = ui.scrollable_frame(body, bg="main_card")
            panel = VoiceEditorPanel(panel_area, initial_data=segment.get("voice"))
            panel.pack(fill="x")

        def save_voice():
            segment["text"] = text_var.get()
            if panel is not None:
                segment["voice"] = panel.get_data()
            if is_staff and segment["text"].strip():
                try:
                    self.status_var.set("TTS音声を生成して文の長さを取得しています")
                    self.update_idletasks()
                    duration = self.fetch_tts_duration(segment["text"].strip(), segment.get("voice", default_voice_data()))
                    segment["duration"] = max(TIME_RESOLUTION, self.round_time(duration))
                    status_message = f"文と声色を更新しました: {segment['duration']:.2f}秒"
                except Exception as exc:
                    duration = self.estimate_tts_duration(segment["text"].strip(), segment.get("voice", default_voice_data()))
                    segment["duration"] = max(TIME_RESOLUTION, self.round_time(duration))
                    status_message = f"TTS取得に失敗したため推定長で更新しました: {exc}"
            else:
                status_message = "文と声色を更新しました" if panel is not None else "文を更新しました"
            utterance["duration"] = self.calculate_utterance_duration(utterance)
            dialog.destroy()
            self.render_utterances()
            self.status_var.set(status_message)

        ui.sub_button(actions, text="戻る", command=dialog.destroy).pack(
            side="left"
        )
        ui.sub_button(actions, text="削除", command=lambda: self.delete_segment_from_dialog(dialog, utterance_index, segment_index)).pack(
            side="left", padx=(ui.SPACING["small_gap"], 0)
        )
        ui.action_button(actions, text="更新", command=save_voice).pack(side="right")
        if is_staff:
            ui.sub_button(
                actions,
                text="試し再生",
                command=lambda: self.preview_sentence_from_dialog(text_var, panel, segment),
            ).pack(side="right", padx=(0, ui.SPACING["small_gap"]))
        else:
            ui.sub_button(
                actions,
                text="試し再生",
                command=lambda: self.preview_sentence_from_dialog(text_var, panel, segment),
            ).pack(side="right", padx=(0, ui.SPACING["small_gap"]))


    def fetch_segment_duration_from_dialog(self, text_var, panel, utterance_index, segment_index):
        utterance = self.store.data["utterances"][utterance_index]
        segment = utterance["segments"][segment_index]
        segment["text"] = text_var.get()
        if panel is not None:
            segment["voice"] = panel.get_data()
        self.fetch_segment_duration(utterance_index, segment_index)


    def ensure_tts_client(self):
        if self.tts_client is None:
            from ...robot_style_editor.clients.tts_client import TTSClient

            self.tts_client = TTSClient()
        return self.tts_client


    def sentence_tts_instructions(self, voice_data):
        instructions = voice_data.get("tts_instructions")
        if instructions is None:
            instructions = voice_params_to_tts_instructions(
                voice_data.get("params", default_voice_data()["params"])
            )
        return instructions


    def preview_sentence_from_dialog(self, text_var, panel, segment):
        text = text_var.get().strip()
        if not text:
            messagebox.showwarning("確認", "先に文を入力してください")
            return

        voice_data = panel.get_data() if panel is not None else segment.get("voice", default_voice_data())
        instructions = self.sentence_tts_instructions(voice_data)
        client = self.ensure_tts_client()

        try:
            if client.is_robot_playback():
                client.speak(text=text, instructions=instructions)
                self.status_var.set("ニコラで文を試し再生しています")
                return

            wav_path = client.synthesize_to_wav(text=text, instructions=instructions)
            if wav_path is None:
                raise RuntimeError("TTS音声を生成できませんでした")
            duration = client.play_preview_wav_trimmed_and_get_duration(wav_path)
            self.status_var.set(f"文を試し再生しています: {duration:.2f}秒")
        except Exception as exc:
            self.status_var.set(f"試し再生エラー: {exc}")
            messagebox.showerror("試し再生エラー", str(exc))


    def fetch_segment_duration(self, utterance_index, segment_index):
        self.sync_texts()
        utterance = self.store.data["utterances"][utterance_index]
        segment = utterance["segments"][segment_index]
        text = segment.get("text", "").strip()
        if not text:
            messagebox.showwarning("確認", "先に文を入力してください")
            return

        try:
            duration = self.fetch_tts_duration(text, segment.get("voice", default_voice_data()))
            self.status_var.set("TTS音声から長さを取得しました")
        except Exception as exc:
            duration = self.estimate_tts_duration(text, segment.get("voice", default_voice_data()))
            self.status_var.set(f"TTS取得に失敗したため推定値を入れました: {exc}")

        segment["duration"] = max(TIME_RESOLUTION, self.round_time(duration))
        utterance["duration"] = self.calculate_utterance_duration(utterance)
        self.render_utterances()


    def fetch_tts_duration(self, text, voice_data):
        from ...robot_style_editor.audio.wav_silence import trim_silence_to_temp_wav

        client = self.ensure_tts_client()
        instructions = self.sentence_tts_instructions(voice_data)
        wav_path = client.synthesize_to_wav(text=text, instructions=instructions)
        if wav_path is None:
            raise RuntimeError("TTS音声を生成できませんでした")
        trimmed_path = trim_silence_to_temp_wav(wav_path)
        try:
            return client.get_wav_duration_sec(trimmed_path)
        finally:
            try:
                trimmed_path.unlink(missing_ok=True)
            except Exception:
                pass


    def estimate_tts_duration(self, text, voice_data):
        params = voice_data.get("params", default_voice_data()["params"])
        rate = max(0.5, float(params.get("rate", 1.0)))
        base = 0.45 + len(text) * 0.12
        return round(max(0.6, base / rate), 2)


    def open_event_editor(self, utterance_index, event_index):
        self.sync_texts()
        utterance = self.store.data["utterances"][utterance_index]
        event = utterance["events"][event_index]
        lane = LANE_BY_ID[event["lane"]]
        if event.get("lane") == "face":
            self.open_face_event_editor(utterance_index, event_index)
            return

        self.selected_utterance_index = utterance_index
        self.selected_event_index = event_index
        self.start_face_preview_keepalive()
        self.render_utterances()

        dialog = tk.Toplevel(self)
        dialog.title(f"{lane['label']}を編集")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)

        body = ui.frame(dialog, bg="main_card")
        body.pack(fill="both", expand=True, padx=22, pady=18)

        ui.label(body, text=f"{lane['label']}を編集", font="page_title", bg="main_card").pack(anchor="w")

        value_var = tk.StringVar(value=event.get("value", lane["default"]))
        time_var = tk.StringVar(value=str(event.get("time", 0.0)))
        duration_var = tk.StringVar(value=str(event.get("duration", 1.0)))

        value_row = ui.frame(body, bg="main_card")
        value_row.pack(fill="x", pady=(ui.SPACING["section_y"], ui.SPACING["small_gap"]))
        ui.label(value_row, text="内容", font="body_bold", bg="main_card", width=8, anchor="w").pack(side="left")
        option = tk.OptionMenu(value_row, value_var, *lane["options"])
        option.configure(font=ui.FONTS["body"], bg=ui.COLORS["card"], fg=ui.COLORS["text"], relief="solid")
        option.pack(side="left", fill="x", expand=True)

        time_row = ui.frame(body, bg="main_card")
        time_row.pack(fill="x", pady=ui.SPACING["small_gap"])
        ui.label(time_row, text="開始秒", font="body_bold", bg="main_card", width=8, anchor="w").pack(side="left")
        ui.entry(time_row, time_var, width=10).pack(side="left")

        duration_row = ui.frame(body, bg="main_card")
        duration_row.pack(fill="x", pady=ui.SPACING["small_gap"])
        ui.label(duration_row, text="長さ秒", font="body_bold", bg="main_card", width=8, anchor="w").pack(side="left")
        ui.entry(duration_row, duration_var, width=10).pack(side="left")

        actions = ui.frame(body, bg="main_card")
        actions.pack(fill="x", pady=(ui.SPACING["section_y"], 0))

        def delete_event():
            if not messagebox.askyesno("削除確認", f"この{lane['label']}を削除しますか？", parent=dialog):
                return
            del utterance["events"][event_index]
            self.selected_utterance_index = None
            self.selected_event_index = None
            dialog.destroy()
            self.render_utterances()
            self.status_var.set("タイミング要素を削除しました")

        def save_event():
            try:
                start = self.round_time(float(time_var.get()))
                duration = max(TIME_RESOLUTION, self.round_time(float(duration_var.get())))
            except ValueError:
                messagebox.showerror("入力エラー", "開始秒と長さ秒は数値で入力してください")
                return

            event["value"] = value_var.get()
            event["time"] = max(MIN_EVENT_TIME, start)
            event["duration"] = duration
            utterance["duration"] = self.calculate_utterance_duration(utterance)
            dialog.destroy()
            self.render_utterances()
            self.status_var.set("タイミング要素を更新しました")

        def close_event_dialog():
            self.selected_utterance_index = None
            self.selected_event_index = None
            dialog.destroy()
            self.render_utterances()

        ui.sub_button(actions, text="戻る", command=close_event_dialog).pack(side="left")
        ui.sub_button(actions, text="削除", command=delete_event).pack(
            side="left", padx=(ui.SPACING["small_gap"], 0)
        )
        ui.action_button(actions, text="更新", command=save_event).pack(side="right")


    def open_face_event_editor(self, utterance_index, event_index):
        utterance = self.store.data["utterances"][utterance_index]
        event = utterance["events"][event_index]
        if "face" not in event:
            event["face"] = default_face_data(event.get("value", "笑顔"))

        self.selected_utterance_index = utterance_index
        self.selected_event_index = event_index
        self.render_utterances()

        dialog = tk.Toplevel(self)
        dialog.title("表情を編集")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("760x620")
        dialog.protocol("WM_DELETE_WINDOW", lambda: close_face_dialog())

        body = ui.frame(dialog, bg="main_card")
        body.pack(fill="both", expand=True, padx=22, pady=18)
        ui.label(body, text="表情を編集", font="page_title", bg="main_card").pack(anchor="w")

        time_var = tk.StringVar(value=str(event.get("time", 0.0)))
        duration_var = tk.StringVar(value=str(event.get("duration", 1.0)))

        timing = ui.frame(body, bg="main_card")
        timing.pack(fill="x", pady=(ui.SPACING["section_y"], ui.SPACING["gap"]))
        ui.label(timing, text="開始秒", font="body_bold", bg="main_card", width=8, anchor="w").pack(side="left")
        ui.entry(timing, time_var, width=10).pack(side="left")
        ui.label(timing, text="長さ秒", font="body_bold", bg="main_card", width=8, anchor="w").pack(
            side="left", padx=(ui.SPACING["gap"], 0)
        )
        ui.entry(timing, duration_var, width=10).pack(side="left")

        actions = ui.frame(body, bg="main_card")
        actions.pack(side="bottom", fill="x", pady=(ui.SPACING["section_y"], 0))

        panel_area = ui.scrollable_frame(body, bg="main_card")
        panel = FaceAxisEditorPanel(panel_area, initial_data=event.get("face"), on_changed=self.preview_face_on_robot)
        panel.pack(fill="x")

        def delete_event():
            if not messagebox.askyesno("削除確認", "この表情を削除しますか？", parent=dialog):
                return
            self.stop_face_preview_keepalive()
            del utterance["events"][event_index]
            self.selected_utterance_index = None
            self.selected_event_index = None
            dialog.destroy()
            self.render_utterances()
            self.status_var.set("表情を削除しました")

        def save_event():
            try:
                start = self.round_time(float(time_var.get()))
                duration = max(TIME_RESOLUTION, self.round_time(float(duration_var.get())))
            except ValueError:
                messagebox.showerror("入力エラー", "開始秒と長さ秒は数値で入力してください")
                return

            face_data = panel.get_data()
            event["value"] = face_data["label"]
            event["face"] = face_data
            event["time"] = max(MIN_EVENT_TIME, start)
            event["duration"] = duration
            utterance["duration"] = self.calculate_utterance_duration(utterance)
            self.stop_face_preview_keepalive()
            dialog.destroy()
            self.render_utterances()
            self.status_var.set("表情を更新しました")

        def close_face_dialog():
            self.selected_utterance_index = None
            self.selected_event_index = None
            self.stop_face_preview_keepalive()
            dialog.destroy()
            self.render_utterances()

        ui.sub_button(actions, text="戻る", command=close_face_dialog).pack(side="left")
        ui.sub_button(actions, text="削除", command=delete_event).pack(
            side="left", padx=(ui.SPACING["small_gap"], 0)
        )
        ui.action_button(actions, text="更新", command=save_event).pack(side="right")


    def ensure_robot_client(self):
        if self.robot_client is None:
            from ...robot_style_editor.clients.robot_command_client import RobotCommandClient

            self.robot_client = RobotCommandClient()
        return self.robot_client


    def reset_robot_client(self):
        if self.robot_client is not None:
            try:
                self.robot_client.close()
            except Exception:
                pass
        self.robot_client = None


    def preview_face_on_robot(self, face_data, force=False, changed_axes=None):
        now = time.monotonic()
        if not force and now - self.face_preview_last_t < 0.18:
            return
        self.face_preview_last_t = now
        self.update_face_preview_keepalive(face_data, changed_axes)

        self.send_face_preview(face_data, changed_axes=changed_axes)


    def send_face_preview(self, face_data, changed_axes=None):
        try:
            robot = self.ensure_robot_client()
            command = face_data.get("command", {})
            label = face_data.get("label", "表情")
            if command.get("type") == "emotion":
                command_text = command.get("text", "/emotion neutral")
                print(f"[FACE PREVIEW] {label}: {command_text}", flush=True)
                robot.send(command_text)
                return

            axis_commands = face_axis_commands(face_data)
            if changed_axes is not None:
                target_axes = {str(axis) for axis in changed_axes}
                axis_commands = [
                    axis_command
                    for axis_command in axis_commands
                    if str(axis_command["axis"]) in target_axes
                ]
            if not axis_commands:
                return

            axis_summary = ", ".join(f"{cmd['axis']}={int(cmd['value'])}" for cmd in axis_commands)
            print(f"[FACE PREVIEW] {label}: /movemulti5 axes({axis_summary})", flush=True)
            for axis_command in axis_commands:
                robot.send_face_axis(
                    axis=str(axis_command["axis"]),
                    value=int(axis_command["value"]),
                    velocity=int(axis_command.get("velocity", 2000)),
                    priority=int(axis_command.get("priority", 3)),
                    keeptime=int(axis_command.get("keeptime", 3000)),
                )
        except Exception as exc:
            self.status_var.set(f"表情プレビュー送信エラー: {exc}")


    def start_face_preview_keepalive(self):
        self.stop_face_preview_keepalive()
        self.face_preview_keepalive_active = True


    def stop_face_preview_keepalive(self):
        self.face_preview_keepalive_active = False
        self.face_preview_keepalive_data = None
        self.face_preview_keepalive_axes = None
        if self.face_preview_keepalive_after_id is not None:
            try:
                self.after_cancel(self.face_preview_keepalive_after_id)
            except Exception:
                pass
            self.face_preview_keepalive_after_id = None


    def update_face_preview_keepalive(self, face_data, changed_axes):
        if not self.face_preview_keepalive_active:
            return
        if face_data.get("command", {}).get("type") == "emotion":
            return
        self.face_preview_keepalive_data = copy.deepcopy(face_data)
        self.face_preview_keepalive_axes = [str(axis) for axis in changed_axes] if changed_axes is not None else None
        if self.face_preview_keepalive_after_id is None:
            self.face_preview_keepalive_after_id = self.after(2800, self.send_face_preview_keepalive)


    def send_face_preview_keepalive(self):
        self.face_preview_keepalive_after_id = None
        if not self.face_preview_keepalive_active or self.face_preview_keepalive_data is None:
            return
        self.send_face_preview(
            self.face_preview_keepalive_data,
            changed_axes=self.face_preview_keepalive_axes,
        )
        if self.face_preview_keepalive_active and self.face_preview_keepalive_data is not None:
            self.face_preview_keepalive_after_id = self.after(2800, self.send_face_preview_keepalive)


    def scenario_turns(self):
        self.sync_texts()
        self.save_workspace_to_active_scene()
        return self.utterances_to_turns(self.store.data.get("utterances", []))


    def utterances_to_turns(self, utterances):
        turns = []
        for utterance in utterances:
            if utterance.get("speaker") == SPEAKER_CUSTOMER:
                text = self.customer_text(utterance).strip()
                if text:
                    turns.append({"role": "customer", "text": text})
                continue

            segments = copy.deepcopy(utterance.get("segments", []))
            if not segments:
                continue
            turns.append(
                {
                    "role": "staff",
                    "segments": segments,
                    "events": copy.deepcopy(utterance.get("events", [])),
                    "default_face": default_face_data(self.store.data.get("default_face_label", "ニュートラル")),
                    "duration": self.calculate_utterance_duration(utterance),
                    "text": self.staff_turn_text(utterance),
                }
            )
        return turns


    def staff_utterance_turn(self, utterance):
        segments = copy.deepcopy(utterance.get("segments", []))
        if not segments:
            return None
        return {
            "role": "staff",
            "segments": segments,
            "events": copy.deepcopy(utterance.get("events", [])),
            "default_face": default_face_data(self.store.data.get("default_face_label", "ニュートラル")),
            "duration": self.calculate_utterance_duration(utterance),
            "text": self.staff_turn_text(utterance),
        }


    def consecutive_staff_indices(self, index):
        utterances = self.store.data.get("utterances", [])
        if index < 0 or index >= len(utterances):
            return []
        if utterances[index].get("speaker") != SPEAKER_STAFF:
            return []

        start = index
        while start > 0 and utterances[start - 1].get("speaker") == SPEAKER_STAFF:
            start -= 1

        end = index
        while end + 1 < len(utterances) and utterances[end + 1].get("speaker") == SPEAKER_STAFF:
            end += 1

        return list(range(start, end + 1))


    def try_staff_utterances(self, indices):
        self.sync_texts()
        self.save_workspace_to_active_scene()
        utterances = self.store.data.get("utterances", [])
        turns = []
        for index in indices:
            if index < 0 or index >= len(utterances):
                continue
            utterance = utterances[index]
            if utterance.get("speaker") != SPEAKER_STAFF:
                continue
            turn = self.staff_utterance_turn(utterance)
            if turn is not None:
                turns.append(turn)

        if not turns:
            messagebox.showwarning("確認", "試す店員発話がありません")
            return

        path = self.store.save()
        label = f"店員発話 {indices[0] + 1}" if len(turns) == 1 else f"店員発話 {indices[0] + 1}-{indices[-1] + 1}"
        self.status_var.set(f"保存しました: {path.name}")
        if self.on_try_robot is not None:
            self.on_try_robot(turns, label)


    def staff_turn_text(self, utterance):
        parts = []
        for segment in utterance.get("segments", []):
            if segment.get("type") == "sentence":
                parts.append(segment.get("text", ""))
        return "".join(parts)


    def round_time(self, value):
        return round(value / TIME_RESOLUTION) * TIME_RESOLUTION


    def sync_title(self):
        label = self.type_var.get().strip() or self.scene_options[0]["label"]
        selected = self.scene_option_by_label(label)
        self.store.data["scenario_title"] = selected["label"]
        self.store.data["conversation_type_id"] = selected["id"]
        self.store.data["conversation_intent"] = selected["intent"]
        default_face_label = self.default_face_var.get().strip() or "ニュートラル"
        if default_face_label not in FACE_EXPRESSION_OPTIONS:
            default_face_label = "ニュートラル"
            self.default_face_var.set(default_face_label)
        self.store.data["default_face_label"] = default_face_label
        self.active_scene_id = selected["id"]


    def on_default_face_selected(self):
        self.sync_title()
        self.save_workspace_to_active_scene()
        self.status_var.set(f"基本表情を設定しました: {self.default_face_var.get()}")

    def on_scene_selected(self):
        old_scene_id = self.active_scene_id
        self.sync_utterance_inputs()
        self.save_workspace_to_active_scene()

        selected = self.scene_option_by_label(self.type_var.get())
        self.load_scene_into_workspace(selected["id"])
        self.type_var.set(selected["label"])
        self.default_face_var.set(self.current_default_face_label())

        if not self.store.data.get("utterances"):
            self.add_initial_utterances()
        else:
            self.migrate_utterances()
        self.save_workspace_to_active_scene()
        self.render_utterances()
        self.status_var.set(f"シーンを読み込みました: {selected['label']}")


    def sync_texts(self, refresh=False):
        self.sync_utterance_inputs()
        self.sync_title()
        self.save_workspace_to_active_scene()
        if refresh:
            self.render_utterances()

    def sync_utterance_inputs(self):
        utterances = self.store.data.get("utterances", [])
        for kind, utterance_index, segment_index, value_var in self.text_vars:
            if utterance_index >= len(utterances):
                continue
            if kind == "customer_text":
                utterances[utterance_index]["text"] = value_var.get()
                utterances[utterance_index]["segments"] = []
                continue
            segments = utterances[utterance_index].get("segments", [])
            if segment_index >= len(segments):
                continue
            segment = segments[segment_index]
            if kind == "pause":
                try:
                    segment["duration"] = max(TIME_RESOLUTION, self.round_time(float(value_var.get())))
                except ValueError:
                    segment["duration"] = DEFAULT_PAUSE_DURATION
            else:
                segment["text"] = value_var.get()
            utterances[utterance_index]["duration"] = self.calculate_utterance_duration(utterances[utterance_index])


    def save(self):
        self.sync_texts()
        self.save_workspace_to_active_scene()
        path = self.store.save()
        self.status_var.set(f"保存しました: {path.name}")


    def try_robot(self):
        self.sync_texts()
        self.save_workspace_to_active_scene()
        path = self.store.save()
        self.status_var.set(f"保存しました: {path.name}")
        if self.on_try_robot is not None:
            self.on_try_robot()
            return
        self.status_var.set(f"保存しました: {path.name}")
