# -*- coding: utf-8 -*-
"""人物面板（纯配置，玩家势力置顶）。"""

import logging
from dataclasses import dataclass
from tkinter import messagebox
from typing import Optional

from .list.panel import GenericListPanel
from .list.columns import Column
from .list.context_menu import MenuItem

logger = logging.getLogger(__name__)

# 未登场行整行文字色（含名称列 #0）
UNAPPEARED_FG = "#888888"
ROW_TAG_UNAPPEARED = "unappeared"


@dataclass(frozen=True)
class CharacterRow:
    id: str
    name: str
    family_name: str
    sex: str
    faction_id: Optional[str]
    faction_name: str
    node_id: Optional[str]
    node_name: str
    role: Optional[str]
    appeared: bool
    leadership: int
    might: int
    intelligence: int
    politics: int
    charisma: int
    coords: Optional[tuple]

    @property
    def display_name(self):
        if self.family_name:
            return f"{self.name}（{self.family_name}）"
        return self.name

    @classmethod
    def from_character(cls, ch, world):
        faction_name = "—"
        if ch.faction and world:
            f = world.faction(ch.faction)
            if f is not None:
                faction_name = f.name

        node_name = "—"
        coords = None
        if ch.node and world:
            n = world.node(ch.node)
            if n is not None:
                node_name = n.name
                coords = n.coords

        return cls(
            id=ch.id,
            name=ch.name,
            family_name=ch.family_name,
            sex=ch.sex,
            faction_id=ch.faction,
            faction_name=faction_name,
            node_id=ch.node,
            node_name=node_name,
            role=ch.role,
            appeared=bool(ch.appeared),
            leadership=ch.leadership,
            might=ch.might,
            intelligence=ch.intelligence,
            politics=ch.politics,
            charisma=ch.charisma,
            coords=coords,
        )


COLUMNS = (
    Column("faction", "势力", 60, "center", lambda r: r.faction_name),
    Column("node",    "所在", 76, "center", lambda r: r.node_name),
    Column("role",    "身份", 48, "center", lambda r: r.role or "—"),
    Column("lead",    "统",   34, "center", lambda r: r.leadership,   sort_numeric=True),
    Column("might",   "武",   34, "center", lambda r: r.might,        sort_numeric=True),
    Column("int",     "智",   34, "center", lambda r: r.intelligence, sort_numeric=True),
    Column("pol",     "政",   34, "center", lambda r: r.politics,     sort_numeric=True),
    Column("cha",     "魅",   34, "center", lambda r: r.charisma,     sort_numeric=True),
    # 登场：显示 ✓/✗，排序按 bool（升序 = ✓ 在前）。声明序最后一位
    Column("appeared", "登场", 50, "center",
           lambda r: "✓" if r.appeared else "✗",
           sort_numeric=True,
           sort_key=lambda r: 0 if r.appeared else 1),
)

NAME_COLUMN = Column("name", "姓名", 110, "w", lambda r: r.name)

GROUP_DIMS = {
    "faction": ("势力", lambda r: r.faction_name or "在野"),
    "node":    ("所在", lambda r: r.node_name or "（无）"),
    "role":    ("身份", lambda r: r.role or "（无）"),
    "sex":     ("性别", lambda r: r.sex or "（未知）"),
    # 固定组序：已登场在前（不依赖中文字符串排序）
    "appear":  ("登场", lambda r: "已登场" if r.appeared else "未登场",
                ("已登场", "未登场")),
}


class CharacterPanel(GenericListPanel):
    PANEL_KEY = "character"
    COLUMNS = COLUMNS
    NAME_COLUMN = NAME_COLUMN
    GROUP_DIMS = GROUP_DIMS
    DEFAULT_GROUP = ("faction",)
    KEEP_VIEW_ON_EDIT = True      # ★ 登场开关后走就地刷新（保滚动 / 选中 / 展开）

    def fetch_rows(self):
        world = getattr(self.game_state, "world", None)
        if world is None:
            return []
        return [CharacterRow.from_character(c, world)
                for c in world.characters.values()]

    def row_key(self, row):
        return row.id

    # ------------------------------------------------------------
    # 行着色 / 组内排序
    # ------------------------------------------------------------
    def _configure_tags(self):
        # 未登场整行深灰（含名称列 #0）
        self.tree.tag_configure(ROW_TAG_UNAPPEARED, foreground=UNAPPEARED_FG)

    def row_tags(self, row):
        if not row.appeared:
            return (ROW_TAG_UNAPPEARED,)
        return ()

    def row_priority(self, group_keys):
        """分组含「势力」时：君主置顶 → 登场在前 → 未登场在后。

        组内子分组（如「势力 > 所在」）内同样生效——未登场后置在
        「势力 > 登场」的叶子组里是常量，不会打乱子分组。
        其他分组路径不加任何优先键。
        """
        if "faction" not in group_keys:
            return None
        return lambda r: (0 if r.faction_id == r.id else 1,
                          0 if r.appeared else 1)

    def priority_name(self):
        """玩家势力名（用于置顶）。"""
        world = getattr(self.game_state, "world", None)
        if world is None:
            return None
        pfid = getattr(world, "player_faction_id", None)
        if not pfid:
            return None
        f = world.faction(pfid)
        return f.name if f else None

    def context_menu_items(self, ctx):
        row = ctx.right_click_row
        return [
            MenuItem(row.display_name, enabled=False),
            MenuItem.sep(),
            MenuItem("人物情报", lambda: self._open_info_window(row)),
            MenuItem("复制编号", lambda: self._copy_id(row.id)),
            MenuItem.sep(),
            # 目标状态写在标签里（符号在前），对**整个选中集**生效
            # edit=True：非编辑模式由 build_menu 统一置灰（§8.3 第 40 条）
            MenuItem("✓ 设为登场",
                     lambda: self._set_appeared(ctx.selected_rows, True),
                     edit=True),
            MenuItem("✗ 设为未登场",
                     lambda: self._set_appeared(ctx.selected_rows, False),
                     edit=True),
            MenuItem.sep(),
            MenuItem("定位到据点", lambda: self.locate_on_map(row)),
            MenuItem.sep(),
            MenuItem("全部展开", lambda: self._toggle_all(True)),
            MenuItem("全部折叠", lambda: self._toggle_all(False)),
        ]

    def _open_info_window(self, row):
        from game.ui.character_info_window import CharacterInfoWindow
        world = getattr(self.game_state, "world", None)
        if world is None:
            return
        ch = world.character(row.id)
        if ch is None:
            return
        top = self.winfo_toplevel()
        font_family = getattr(top, "font_family", "TkDefaultFont")
        logger.debug("人物情报：%s %s", ch.id, ch.name)
        CharacterInfoWindow(self, ch, world=world, font_family=font_family)

    def _set_appeared(self, rows, target):
        """批量设为登场 / 未登场：对选中集统一设置目标状态。

        只改 appeared，**不碰** faction / node / location / role ——
        「设为登场」后仍是「在野」，「设为未登场」保留已有归属（可逆）。
        君主不能设为未登场（跳过 + 提示），其余行照常提交。
        只对状态与目标不同的行生成命令：已是目标状态的行不产生多余 dirty。
        """
        session = self.edit_session
        world = getattr(self.game_state, "world", None)
        if session is None or world is None:
            return

        candidates = list(rows)
        skipped = 0
        if target is False:
            rulers = [r for r in candidates if r.faction_id == r.id]
            if rulers:
                skipped = len(rulers)
                blocked = {id(r) for r in rulers}
                candidates = [r for r in candidates if id(r) not in blocked]
                logger.info("设为未登场跳过君主 %d 人：%s",
                            skipped, "、".join(r.name for r in rulers[:5]))
                messagebox.showwarning(
                    "君主不能设为未登场",
                    "君主必须保持登场状态。\n\n"
                    "需先解散势力，才能修改该人物的登场状态。\n\n"
                    "已跳过：%s" % "、".join(r.name for r in rulers[:5]),
                )

        from game.core.edit_commands import CharacterEditCommand
        from game.core.edit_session import CompositeCommand

        cmds = []
        for r in candidates:
            ch = world.character(r.id)
            if ch is None:
                logger.warning("人物不存在：%s", r.id)
                continue
            current = bool(ch.appeared)
            if current == target:
                continue
            cmds.append(CharacterEditCommand(
                ch.id, {"appeared": current}, {"appeared": target},
            ))

        if len(cmds) == 1:
            session.execute(cmds[0])
        elif cmds:
            session.execute(CompositeCommand(cmds, "批量设置登场"))
        logger.info("批量设置登场：命中 %d 人 / 跳过 %d 人 → %s",
                    len(cmds), skipped, target)
        if cmds:
            self._notify_edit(keep_view=True)

    def _copy_id(self, cid):
        try:
            self.clipboard_clear()
            self.clipboard_append(cid)
            logger.debug("复制人物编号：%s", cid)
        except Exception:
            logger.warning("复制编号失败：%s", cid, exc_info=True)
