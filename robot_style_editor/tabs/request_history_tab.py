import copy
import tkinter as tk

from .. import ui_style as ui
from ..config_example import EXAMPLE_SCENES, EXAMPLE_VENUES


class RequestHistoryTab(tk.Frame):
    def __init__(
        self,
        parent,
        profile_store,
        tts_client,
        status_var,
        on_saved=None,
        venue_label=None,
    ):
        super().__init__(parent, bg=ui.COLORS["main_card"])
        self.profile_store = profile_store
        self.tts_client = tts_client
        self.status_var = status_var
        self.on_saved = on_saved
        self.venue_label = venue_label or EXAMPLE_VENUES[0]["label"]
        self.content = None

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
        header.pack(fill="x", pady=(0, ui.SPACING["section_y"]))

        title_area = ui.frame(header, bg="main_card")
        title_area.pack(side="left", fill="x", expand=True)

        ui.label(
            title_area,
            text="詳細要望一覧",
            font="page_title",
            bg="main_card",
        ).pack(anchor="w")

        ui.label(
            title_area,
            text="接客例で出した要望と、GPTが変更した店員発話を場面ごとに確認します。",
            font="body",
            bg="main_card",
            fg="sub_text",
        ).pack(anchor="w", pady=(ui.SPACING["small_gap"], 0))

        ui.sub_button(header, text="再読み込み", command=self.refresh_from_profile).pack(side="right")

        self.content = ui.scrollable_frame(page, bg="main_card")
        self.render_current_venue()

    def refresh_from_profile(self):
        self.render_current_venue()

    def current_venue(self):
        for venue in EXAMPLE_VENUES:
            if venue["label"] == self.venue_label:
                return venue
        return EXAMPLE_VENUES[0]

    def render_current_venue(self):
        if self.content is None:
            return

        for child in self.content.winfo_children():
            child.destroy()

        venue = self.current_venue()
        entries = self.collect_venue_entries(venue["id"])

        if not entries:
            self.render_empty(self.content, venue)
            return

        for entry in entries:
            self.render_entry(self.content, entry)

    def render_empty(self, parent, venue):
        card = ui.bordered_frame(parent, bg="card", border="border")
        card.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))
        ui.label(
            card,
            text=f"{venue['label']}の詳細要望履歴はまだありません。",
            font="body_bold",
            bg="card",
            fg="text",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]))
        ui.label(
            card,
            text="接客例タブで全体要望または発話ごとの要望を入力して再生成すると、ここに残ります。",
            font="body",
            bg="card",
            fg="sub_text",
            wraplength=980,
            justify="left",
        ).pack(anchor="w", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["card_y"]))

    def render_entry(self, parent, entry):
        card = ui.bordered_frame(parent, bg="card", border="border")
        card.pack(fill="x", pady=(0, ui.SPACING["small_gap"]))

        header = ui.frame(card, bg="card")
        header.pack(fill="x", padx=ui.SPACING["card_x"], pady=(ui.SPACING["card_y"], ui.SPACING["small_gap"]))

        ui.label(
            header,
            text=f"{entry['scene_title']} / {entry['kind_label']}",
            font="section_title",
            bg="card",
            fg="text",
        ).pack(side="left", anchor="w")

        ui.label(
            header,
            text=entry["created_at"] or "日時なし",
            font="small",
            bg="card",
            fg="muted",
        ).pack(side="right", anchor="e")

        meta = ui.frame(card, bg="card")
        meta.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["small_gap"]))
        self.render_meta_chip(meta, "場面", entry["scene_title"])
        self.render_meta_chip(meta, "対象", entry["target_label"])
        self.render_meta_chip(meta, "要望", entry["request"], wide=True)

        if entry["summary"]:
            self.render_text_block(card, "GPTの変更理由・要約", entry["summary"], bg="card")

        self.render_text_block(card, "変更前", entry["before_text"], bg="card")
        self.render_text_block(card, "変更後", entry["after_text"], bg="card")

    def render_meta_chip(self, parent, title, value, wide=False):
        chip = ui.bordered_frame(parent, bg="main_card", border="soft_border")
        chip.pack(
            side="left",
            fill="both",
            expand=wide,
            padx=(0, ui.SPACING["small_gap"]),
        )
        ui.label(chip, text=title, font="small", bg="main_card", fg="muted").pack(
            anchor="w",
            padx=ui.SPACING["compact_x"],
            pady=(ui.SPACING["compact_y"], 0),
        )
        ui.label(
            chip,
            text=value,
            font="body_bold",
            bg="main_card",
            fg="text",
            wraplength=520 if wide else 260,
            justify="left",
        ).pack(anchor="w", padx=ui.SPACING["compact_x"], pady=(0, ui.SPACING["compact_y"]))

    def render_text_block(self, parent, title, text, bg="card"):
        block = ui.frame(parent, bg=bg)
        block.pack(fill="x", padx=ui.SPACING["card_x"], pady=(0, ui.SPACING["small_gap"]))
        ui.label(block, text=title, font="small", bg=bg, fg="muted").pack(anchor="w")
        ui.label(
            block,
            text=text or "なし",
            font="body",
            bg=bg,
            fg="text",
            wraplength=1040,
            justify="left",
        ).pack(anchor="w", fill="x")

    def collect_venue_entries(self, venue_id):
        entries = []
        results = self.profile_store.get_example_results() or {}
        scenes = [scene for scene in EXAMPLE_SCENES if scene.get("venue") == venue_id]

        for scene in scenes:
            record = results.get(scene["id"], {}) or {}
            versions = record.get("versions", []) or []
            for index, version in enumerate(versions):
                entries.extend(self.version_entries(scene, versions, index, version))

        return entries

    def version_entries(self, scene, versions, index, version):
        previous_turns = self.previous_turns(scene, versions, version)
        current_turns = version.get("turns", []) or []
        request = (version.get("request") or "").strip() or "要望なし（選択場面を生成）"
        summary = version.get("summary", "")
        created_at = version.get("created_at", "")
        kind = version.get("kind", "whole")
        kind_label = "全体要望" if kind == "whole" else "発話ごとの要望"

        changed_indexes = self.changed_staff_indexes(previous_turns, current_turns)
        target_index = version.get("target_turn_index")
        if kind == "turn" and isinstance(target_index, int):
            changed_indexes = [target_index]

        entries = []
        for turn_index in changed_indexes:
            before = self.turn_at(previous_turns, turn_index)
            after = self.turn_at(current_turns, turn_index)
            if not after or after.get("role") != "staff":
                continue

            entries.append(
                {
                    "scene_title": scene["title"],
                    "version_index": index,
                    "created_at": created_at,
                    "kind_label": kind_label,
                    "target_label": f"{turn_index + 1}番目の店員発話",
                    "request": request,
                    "summary": summary,
                    "before_text": before.get("text", "変更前を取得できませんでした") if before else "変更前を取得できませんでした",
                    "after_text": after.get("text", ""),
                }
            )

        return entries

    def previous_turns(self, scene, versions, version):
        previous_active = version.get("previous_active", -1)
        if isinstance(previous_active, int) and 0 <= previous_active < len(versions):
            return copy.deepcopy(versions[previous_active].get("turns", []) or [])
        return self.base_turns(scene)

    def changed_staff_indexes(self, previous_turns, current_turns):
        indexes = []
        max_len = max(len(previous_turns), len(current_turns))
        for index in range(max_len):
            before = self.turn_at(previous_turns, index)
            after = self.turn_at(current_turns, index)
            if not after or after.get("role") != "staff":
                continue
            if not before or before.get("text") != after.get("text"):
                indexes.append(index)
        return indexes

    def turn_at(self, turns, index):
        if not isinstance(index, int):
            return None
        if 0 <= index < len(turns):
            return turns[index]
        return None

    def base_turns(self, scene):
        return [
            {
                "role": turn["role"],
                "text": turn.get("text", turn.get("base_text", "")),
                "intent_parts": turn.get("intent_parts", []),
            }
            for turn in scene["turns"]
        ]
