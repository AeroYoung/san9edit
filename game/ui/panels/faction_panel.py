# -*- coding: utf-8 -*-
"""势力面板：分组可切（玩家/盟友/敌对/中立 · 宗主），势力名带色块。

分组走框架的 GROUP_DIMS + GroupBar（用户可切维度，需求 §3.12）：
    stance_group  玩家势力 / 盟友 / 敌对 / 中立（固定组序，默认）
    overlord      按宗主归组：附庸进「宗主势力名」组，**宗主本人也在该组里当第一行**；
                  有附庸的独立势力自成一组（组名 = 自己），其余独立势力归「独立」组
组头与行的配色由 _apply_group_tags / row_tags 补回（框架的默认分组不带 tag）。
色块用 NAME_COLUMN.image 列渲染扩展点，颜色取**派生显示色**（§3.4）。
"""

import logging
import tkinter as tk
from dataclasses import dataclass

from game.core.faction_color import faction_display_color

from .list.panel import GenericListPanel
from .list.columns import Column
from .list.context_menu import MenuItem

logger = logging.getLogger(__name__)

# 固定分组名（组头 / 行配色按它匹配，与分组顺序无关）
PLAYER_GROUP = "玩家势力"
ALLY_GROUP = "盟友"
HOSTILE_GROUP = "敌对"
NEUTRAL_GROUP = "中立"

INDEPENDENT_LABEL = "独立"      # 无附庸的独立势力在宗主维度里的组名 / 列文本


@dataclass(frozen=True)
class FactionRow:
    id: str
    name: str
    color: str
    prestige: int
    gold: int
    food: int
    troops: int
    stance: int
    ruler_name: str
    node_count: int = 0      # ★ 新增
    char_count: int = 0      # ★ 新增
    vassal_text: str = INDEPENDENT_LABEL  # ★ 独立/附庸列（独立 或 宗主势力名）
    stance_group: str = NEUTRAL_GROUP  # ★ 玩家/盟友/敌对/中立（分组维度取值）
    lord_group: str = INDEPENDENT_LABEL  # ★ 宗主维度的组名
    is_lord: bool = False                # ★ 本势力是否是别人的宗主（组内排第一）

    @property
    def stance_text(self):
        return f"+{self.stance}" if self.stance > 0 else f"{self.stance}"

    @classmethod
    def from_faction(cls, f, world, node_count=0, char_count=0,
                     player_id=None, lord_ids=frozenset()):   # ★ 签名扩展
        ruler = world.characters.get(f.ruler_id)
        overlord = (world.factions.get(f.overlord_id)
                    if f.overlord_id else None)
        overlord_name = overlord.name if overlord else None
        is_lord = f.id in lord_ids
        return cls(
            id=f.id, name=f.name,
            color=faction_display_color(f, world.factions),   # ★ 派生显示色
            prestige=f.prestige, gold=f.gold, food=f.food,
            troops=f.troops,                # ★ 新增
            stance=f.stance,
            ruler_name=ruler.name if ruler is not None else "—",
            node_count=node_count, char_count=char_count,
            vassal_text=f.vassal_label(overlord_name),
            stance_group=cls.stance_group_of(f, player_id),
            lord_group=cls.lord_group_of(f, overlord_name, is_lord),
            is_lord=is_lord,
        )

    @staticmethod
    def lord_group_of(f, overlord_name, is_lord):
        """宗主维度的组名。

        附庸 → 宗主势力名；有附庸的独立势力 → 自己（宗主本人在自己那组里）；
        其余独立势力 →「独立」。
        """
        if not f.independent and f.overlord_id:
            return overlord_name or f.overlord_id
        if is_lord:
            return f.name
        return INDEPENDENT_LABEL

    @staticmethod
    def stance_group_of(f, player_id):
        """玩家 / 盟友 / 敌对 / 中立（与旧 build_groups 的判定一致）。"""
        if player_id is not None and f.id == player_id:
            return PLAYER_GROUP
        if f.stance > 80:
            return ALLY_GROUP
        if f.stance < 0:
            return HOSTILE_GROUP
        return NEUTRAL_GROUP


COLUMNS = (
    Column("ruler",    "君主", 70, "center", lambda r: r.ruler_name),
    Column("prestige", "威望", 60, "e", lambda r: f"{r.prestige:,}", sort_numeric=True),
    Column("gold",     "金",   60, "e", lambda r: f"{r.gold:,}",     sort_numeric=True),
    Column("food",     "粮",   70, "e", lambda r: f"{r.food:,}",     sort_numeric=True),
    Column("troops",   "兵力", 70, "e", lambda r: f"{r.troops:,}",   sort_numeric=True),  # ★ 新增
    Column("nodes",    "据点", 55, "e", lambda r: str(r.node_count), sort_numeric=True),  # ★
    Column("chars",    "人物", 55, "e", lambda r: str(r.char_count), sort_numeric=True),  # ★
    Column("stance",   "关系", 50, "center", lambda r: r.stance_text),
    # ★ 新增列按 §8.3 第 26 条：用户旧配置里没有它 → 插在声明位置附近（此处「关系」后）并显示
    Column("vassal",   "独立/附庸", 80, "center", lambda r: r.vassal_text),
)


class FactionPanel(GenericListPanel):
    PANEL_KEY = "faction"
    COLUMNS = COLUMNS              # ★ 补这一行
    GROUP_DIMS = {
        "stance_group": ("玩家/盟友/敌对/中立",
                         lambda r: r.stance_group,
                         (PLAYER_GROUP, ALLY_GROUP, HOSTILE_GROUP,
                          NEUTRAL_GROUP)),
        "overlord": ("宗主", lambda r: r.lord_group),
    }
    DEFAULT_GROUP = ("stance_group",)      # 默认仍是玩家/盟友/敌对/中立

    _GROUP_TAGS = {
        PLAYER_GROUP:  ("group_player",),
        ALLY_GROUP:    ("group_ally",),
        HOSTILE_GROUP: ("group_hostile",),
        NEUTRAL_GROUP: ("group_neutral",),
    }
    _ROW_TAGS = {
        PLAYER_GROUP:  "row_player",
        ALLY_GROUP:    "row_ally",
        HOSTILE_GROUP: "row_hostile",
        NEUTRAL_GROUP: "row_neutral",
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
        lord_ids = frozenset(
            f.overlord_id for f in world.factions.values()
            if not getattr(f, "independent", True) and f.overlord_id)

        return [
            FactionRow.from_faction(
                f, world,
                node_count=node_counts.get(f.id, 0),
                char_count=char_counts.get(f.id, 0),
                player_id=world.player_faction_id,
                lord_ids=lord_ids,
            )
            for f in world.factions.values()
        ]

    def row_priority(self, group_keys):
        """按宗主分组时，宗主排在该组第一行（附庸跟在后面）。"""
        if "overlord" not in (group_keys or ()):
            return None
        return lambda r: (0 if r.is_lord else 1,)

    def row_key(self, row):
        return row.id

    def context_menu_items(self, ctx):
        row = ctx.right_click_row
        single = len(ctx.selected_rows) == 1
        return [
            MenuItem(row.name, enabled=False),
            MenuItem.sep(),
            # 编辑 / 情报同一个窗：非编辑模式只读展示（标签随模式变）
            MenuItem(self._label("编辑势力", "势力情报"),
                     lambda: self._edit(row), enabled=single),
            MenuItem.sep(),
            MenuItem("新建势力", lambda: self._create(), edit=True),
            MenuItem("删除势力", lambda: self._delete(row), enabled=single,
                     edit=True),
        ]

    def _label(self, edit_text, info_text):
        """按模式取标签（与 MenuItem(edit=True) 同一判据：有没有编辑会话）。"""
        return edit_text if self.edit_session is not None else info_text

    def _create(self):
        """新建势力：选无主据点作都城 + 选已登场无势力人物作君主。"""
        if self.edit_session is None:
            return
        world = getattr(self.game_state, "world", None)
        if world is None:
            return
        from game.ui.dialogs.faction_lifecycle import create_faction
        if create_faction(self, world, self.edit_session, self._open_dialog):
            self._notify_edit()

    def _delete(self, row):
        """删除势力：预览名单 → 级联（据点 / 人物 / 外官）→ 一次 undo。"""
        if self.edit_session is None:
            return
        world = getattr(self.game_state, "world", None)
        f = world.factions.get(row.id) if world else None
        if f is None:
            logger.warning("势力不存在：%s", row.id)
            return
        from game.ui.dialogs.faction_lifecycle import delete_faction
        if delete_faction(self, world, f, self.edit_session, self._open_dialog):
            self._notify_edit()

    def _edit(self, row):
        """编辑势力 / 势力情报：同一个窗（session 为 None 时只读）。"""
        world = getattr(self.game_state, "world", None)
        if world is None:
            return
        f = world.factions.get(row.id)
        if f is None:
            logger.warning("势力不存在：%s", row.id)
            return
        logger.debug("编辑势力：%s %s", f.id, f.name)

        # 与地图右键「编辑势力」共用同一套流程
        from game.ui.dialogs.faction_edit import edit_faction
        if edit_faction(self, world, f, self.edit_session, self._open_dialog):
            self._notify_edit()


    def _build_groups(self, rows):
        """框架分组结果上补组头 tag（框架不认业务，颜色由面板自己贴）。"""
        groups = super()._build_groups(rows)
        if groups:
            self._apply_group_tags(groups)
        return groups

    def _apply_group_tags(self, groups):
        for g in groups:
            tags = self._GROUP_TAGS.get(g.title)
            if tags:
                g.tags = tags
            if g.has_subgroups():
                self._apply_group_tags(g.children)

    def row_tags(self, row):
        """行色按玩家/盟友/敌对/中立（换分组维度后依然生效）。"""
        tag = self._ROW_TAGS.get(row.stance_group)
        return (tag,) if tag else ()

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
