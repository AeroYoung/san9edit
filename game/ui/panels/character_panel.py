# -*- coding: utf-8 -*-
"""人物面板（纯配置，玩家势力置顶）。"""

from dataclasses import dataclass
from typing import Optional

from .list.panel import GenericListPanel
from .list.columns import Column
from .list.context_menu import MenuItem


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
)

NAME_COLUMN = Column("name", "姓名", 110, "w", lambda r: r.display_name)

GROUP_DIMS = {
    "faction": ("势力", lambda r: r.faction_name or "在野"),
    "node":    ("所在", lambda r: r.node_name or "（无）"),
    "role":    ("身份", lambda r: r.role or "（无）"),
    "sex":     ("性别", lambda r: r.sex or "（未知）"),
}


class CharacterPanel(GenericListPanel):
    PANEL_KEY = "character"
    COLUMNS = COLUMNS
    NAME_COLUMN = NAME_COLUMN
    GROUP_DIMS = GROUP_DIMS
    DEFAULT_GROUP = ("faction",)

    def fetch_rows(self):
        world = getattr(self.game_state, "world", None)
        if world is None:
            return []
        return [CharacterRow.from_character(c, world)
                for c in world.characters.values()]

    def row_key(self, row):
        return row.id

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
            MenuItem("人物情报", lambda: self._intel(ctx.selected_rows)),
            MenuItem("复制编号", lambda: self._copy_id(row.id)),
            MenuItem.sep(),
            MenuItem("定位到据点", lambda: self.locate_on_map(row)),
            MenuItem.sep(),
            MenuItem("全部展开", lambda: self._toggle_all(True)),
            MenuItem("全部折叠", lambda: self._toggle_all(False)),
        ]

    def _intel(self, rows):
        names = "、".join(r.display_name for r in rows[:5])
        more = f" 等 {len(rows)} 个" if len(rows) > 5 else ""
        print(f"[人物情报] characters={names}{more}")

    def _copy_id(self, cid):
        try:
            self.clipboard_clear()
            self.clipboard_append(cid)
        except Exception:
            pass
