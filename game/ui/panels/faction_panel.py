# -*- coding: utf-8 -*-
"""势力面板：按「玩家 / 盟友 / 敌对 / 中立」固定分组，势力名带色块。

固定分组用框架的 CUSTOM_GROUPING + build_groups() 扩展点；
色块用 NAME_COLUMN.image 列渲染扩展点。
"""

import tkinter as tk
from dataclasses import dataclass

from .list.panel import GenericListPanel
from .list.columns import Column
from .list.model import Group
from .list.context_menu import MenuItem


@dataclass(frozen=True)
class FactionRow:
    id: str
    name: str
    color: str
    prestige: int
    gold: int
    food: int
    stance: int
    ruler_name: str
    node_count: int = 0      # ★ 新增
    char_count: int = 0      # ★ 新增

    @property
    def stance_text(self):
        return f"+{self.stance}" if self.stance > 0 else f"{self.stance}"

    @classmethod
    def from_faction(cls, f, world, node_count=0, char_count=0):   # ★ 签名扩展
        ruler = world.characters.get(f.ruler_id)
        return cls(
            id=f.id, name=f.name, color=f.color,
            prestige=f.prestige, gold=f.gold, food=f.food, stance=f.stance,
            ruler_name=ruler.name if ruler is not None else "—",
            node_count=node_count, char_count=char_count,          # ★
        )


COLUMNS = (
    Column("ruler",    "君主", 70, "center", lambda r: r.ruler_name),
    Column("prestige", "威望", 60, "e", lambda r: f"{r.prestige:,}", sort_numeric=True),
    Column("gold",     "金",   60, "e", lambda r: f"{r.gold:,}",     sort_numeric=True),
    Column("food",     "粮",   70, "e", lambda r: f"{r.food:,}",     sort_numeric=True),
    Column("nodes",    "据点", 55, "e", lambda r: str(r.node_count), sort_numeric=True),  # ★
    Column("chars",    "人物", 55, "e", lambda r: str(r.char_count), sort_numeric=True),  # ★
    Column("stance",   "关系", 50, "center", lambda r: r.stance_text),
)


class FactionPanel(GenericListPanel):
    PANEL_KEY = "faction"
    COLUMNS = COLUMNS              # ★ 补这一行
    CUSTOM_GROUPING = True

    _GROUPS = [
        ("player",  "玩家势力"),
        ("ally",    "盟友"),
        ("hostile", "敌对"),
        ("neutral", "中立"),
    ]
    _GROUP_TAGS = {
        "player":  ("group_player",),
        "ally":    ("group_ally",),
        "hostile": ("group_hostile",),
        "neutral": ("group_neutral",),
    }
    _ROW_TAGS = {
        "player":  "row_player",
        "ally":    "row_ally",
        "hostile": "row_hostile",
        "neutral": "row_neutral",
    }

    def __init__(self, master, game_state, map_controller=None):
        # 色块缓存：PhotoImage 必须保活，否则 GC 后显示空白
        self._swatches = {}
        self._swatch_size = self._compute_swatch_size()
        # NAME_COLUMN 带 image 扩展点（势力色块）
        self.NAME_COLUMN = Column(
            "name", "势力", 110, "w", lambda r: r.name, image=self._swatch_for,
        )
        super().__init__(master, game_state, map_controller)

    # ------------------------------------------------------------
    # 色块
    # ------------------------------------------------------------
    @staticmethod
    def _compute_swatch_size():
        """读 ttk 主题行高，返回比行高略小的色块边长。"""
        import tkinter.font as tkfont
        from tkinter import ttk

        row_h = None
        try:
            style = ttk.Style()
            v = style.lookup("Treeview", "rowheight")
            if v:
                row_h = int(v)
        except Exception:
            pass

        if not row_h:
            try:
                f = tkfont.nametofont("TkDefaultFont")
                row_h = f.metrics("linespace") + 6
            except Exception:
                row_h = 20

        return max(8, row_h - 6)

    def _make_swatch(self, color):
        """生成带黑色边框的纯色小方块 PhotoImage。"""
        size = self._swatch_size
        img = tk.PhotoImage(width=size, height=size)
        img.put("#000000", to=(0, 0, size, size))          # 整块黑 = 边框
        try:
            img.put(color, to=(1, 1, size - 1, size - 1))  # 内部填势力色
        except tk.TclError:
            img.put("#888888", to=(1, 1, size - 1, size - 1))
        return img

    def _swatch_for(self, row):
        img = self._swatches.get(row.id)
        if img is None:
            img = self._make_swatch(row.color)
            self._swatches[row.id] = img
        return img

    # ------------------------------------------------------------
    # 固定分组
    # ------------------------------------------------------------
    def fetch_rows(self):
        world = getattr(self.game_state, "world", None)
        if world is None or not getattr(world, "factions", None):
            return []

        # ★ 聚合只算一次，避免逐行遍历
        node_counts = world.count_nodes_by_owner()
        char_counts = world.count_characters_by_faction()

        return [
            FactionRow.from_faction(
                f, world,
                node_count=node_counts.get(f.id, 0),
                char_count=char_counts.get(f.id, 0),
            )
            for f in world.factions.values()
        ]

    def row_key(self, row):
        return row.id

    def context_menu_items(self, ctx):
        row = ctx.right_click_row
        can_edit = (self.edit_session is not None
                    and len(ctx.selected_rows) == 1)
        return [
            MenuItem(row.name, enabled=False),
            MenuItem.sep(),
            MenuItem("编辑", lambda: self._edit(row), enabled=can_edit),
        ]

    def _edit(self, row):
        if self.edit_session is None:
            return
        world = getattr(self.game_state, "world", None)
        if world is None:
            return
        f = world.factions.get(row.id)
        if f is None:
            return

        from game.ui.dialogs.edit_dialog import EditDialog
        from game.ui.dialogs.faction_fields import FACTION_FIELDS
        from game.core.edit_commands import FactionEditCommand

        dlg = self._open_dialog(lambda: EditDialog(
            self, FACTION_FIELDS, f, world=world, title="编辑势力"))
        if dlg is None or not dlg.ok:
            return

        new_values, old_values = dlg.get_changed()
        if not new_values:
            return

        self.edit_session.execute(
            FactionEditCommand(row.id, old_values, new_values))
        self._notify_edit()

    def build_groups(self, rows):
        world = getattr(self.game_state, "world", None)
        if world is None:
            return []

        buckets = {"player": [], "ally": [], "hostile": [], "neutral": []}
        player_id = world.player_faction_id
        for r in rows:
            if r.id == player_id:
                buckets["player"].append(r)
            elif r.stance > 80:
                buckets["ally"].append(r)
            elif r.stance < 0:
                buckets["hostile"].append(r)
            else:
                buckets["neutral"].append(r)

        for key in buckets:
            buckets[key].sort(key=lambda x: (-x.prestige, x.name))

        return [
            Group(
                title=f"{title} ({len(buckets[key])})",
                children=buckets[key],
                tags=self._GROUP_TAGS[key],
                row_tag=self._ROW_TAGS[key],
            )
            for key, title in self._GROUPS
        ]

    def _before_refresh(self):
        self._swatches.clear()

    # ------------------------------------------------------------
    # 组 / 行配色
    # ------------------------------------------------------------
    def _configure_tags(self):
        self.tree.tag_configure("group_player",  background="#DBEAFE", font=("", 10, "bold"))
        self.tree.tag_configure("group_ally",    background="#DCFCE7", font=("", 10, "bold"))
        self.tree.tag_configure("group_hostile", background="#FEE2E2", font=("", 10, "bold"))
        self.tree.tag_configure("group_neutral", background="#F3F4F6", font=("", 10, "bold"))
        self.tree.tag_configure("row_player",  foreground="#1E40AF")
        self.tree.tag_configure("row_ally",    foreground="#166534")
        self.tree.tag_configure("row_hostile", foreground="#991B1B")
        self.tree.tag_configure("row_neutral", foreground="#374151")
