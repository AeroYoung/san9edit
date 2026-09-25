# -*- coding: utf-8 -*-
"""据点面板（纯配置）。"""

from dataclasses import dataclass
from typing import Optional

from .list.panel import GenericListPanel
from .list.columns import Column
from .list.context_menu import MenuItem


@dataclass(frozen=True)
class NodeRow:
    node_id: str
    name: str
    type: str
    level: int
    coords: tuple
    state_name: str
    county_name: str
    owner_id: Optional[str]
    owner_name: str
    is_capital: bool = False
    governor_name: str = "—"     # 预留
    person_count: int = 0        # 预留

    @property
    def display_type(self):
        return "郡治" if self.is_capital else self.type

    @classmethod
    def from_node(cls, node, world):
        owner_name = "—"
        if node.owner:
            f = world.faction(node.owner) if world else None
            if f is not None:
                owner_name = f.name
        return cls(
            node_id=node.id,
            name=node.name,
            type=node.type,
            level=node.level,
            coords=node.coords,
            state_name=world.state_name(node.state_id),
            county_name=world.county_name(node.county_id),
            owner_id=node.owner,
            owner_name=owner_name,
            is_capital=node.is_capital,
        )


COLUMNS = (
    Column("state",    "州",   52, "center", lambda r: r.state_name),
    Column("county",   "郡",   62, "center", lambda r: r.county_name),
    Column("level",    "规模", 42, "center", lambda r: r.level, sort_numeric=True),
    Column("type",     "类型", 46, "center", lambda r: r.display_type),
    Column("owner",    "势力", 64, "center", lambda r: r.owner_name),
    Column("governor", "主官", 56, "center", lambda r: r.governor_name),
    Column("persons",  "人物", 42, "center", lambda r: r.person_count, sort_numeric=True),
)

NAME_COLUMN = Column("name", "县", 110, "w", lambda r: r.name)

GROUP_DIMS = {
    "faction": ("势力", lambda r: r.owner_name or "无主"),
    "state":   ("州",   lambda r: r.state_name or "（无）"),
    "county":  ("郡",   lambda r: r.county_name or "（无）"),
    "type":    ("类型", lambda r: r.type or "（无）"),
}


class NodePanel(GenericListPanel):
    PANEL_KEY = "node"
    COLUMNS = COLUMNS
    NAME_COLUMN = NAME_COLUMN
    GROUP_DIMS = GROUP_DIMS
    DEFAULT_GROUP = ("state", "county")

    def fetch_rows(self):
        world = getattr(self.game_state, "world", None)
        if world is None:
            return []
        return [NodeRow.from_node(n, world) for n in world.nodes.values()]

    def row_key(self, row):
        return row.node_id

    def context_menu_items(self, ctx):
        row = ctx.right_click_row
        single = len(ctx.selected_rows) == 1
        return [
            MenuItem(row.name, enabled=False),
            MenuItem.sep(),
            # edit=True 标识：非编辑模式由 build_menu 统一置灰
            MenuItem("编辑", lambda: self._edit(row), enabled=single, edit=True),
            MenuItem.sep(),
            MenuItem("据点情报", lambda: self._intel("node", ctx.selected_rows)),
            MenuItem("人物情报", lambda: self._intel("character", ctx.selected_rows)),
            MenuItem("势力情报", lambda: self._intel("faction", ctx.selected_rows)),
            MenuItem.sep(),
            MenuItem("定位到地图", lambda: self.locate_on_map(row)),
            MenuItem.sep(),
            MenuItem("全部展开", lambda: self._toggle_all(True)),
            MenuItem("全部折叠", lambda: self._toggle_all(False)),
        ]

    def _edit(self, row):
        world = getattr(self.game_state, "world", None)
        node = world.nodes.get(row.node_id) if world else None
        from game.ui.dialogs.node_edit import edit_node
        if edit_node(self, world, node, self.edit_session, self._open_dialog):
            self._notify_edit()

    def _intel(self, kind, rows):
        names = "、".join(r.name for r in rows[:5])
        more = f" 等 {len(rows)} 个" if len(rows) > 5 else ""
        print(f"[据点情报] kind={kind} nodes={names}{more}")
