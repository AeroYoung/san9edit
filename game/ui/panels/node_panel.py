# -*- coding: utf-8 -*-
"""据点面板（纯配置）。"""

import logging
from dataclasses import dataclass
from typing import Optional

from .list.panel import GenericListPanel
from .list.columns import Column
from .list.context_menu import MenuItem

logger = logging.getLogger(__name__)


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
    governor_name: str = "—"     # ★ 县外官姓名（无则「—」）
    person_count: int = 0        # ★ 所属人物数（未登场不计），由 fetch_rows 聚合传入

    @property
    def display_type(self):
        return "郡治" if self.is_capital else self.type

    @classmethod
    def from_node(cls, node, world, person_count=0):
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
            governor_name=cls._governor_name(node, world),
            person_count=person_count,
        )

    @staticmethod
    def _governor_name(node, world):
        """主官 = 该**县**外官（6 位键）；州 / 郡外官进分组标题（需求 §4）。"""
        item = world.official_of(node.id) if world else None
        if item is None:
            return "—"
        ch = world.character(item.get("character_id"))
        return ch.name if ch is not None else (item.get("name") or "—")


# 列宽按「侧栏约 530px − 竖向滚动条」分配：合计 ≈ 374，加上 #0 自适应的
# 129（组标题 + 最长县名）仍不撑出横向滚动条
COLUMNS = (
    Column("state",    "州",   46, "center", lambda r: r.state_name),
    Column("county",   "郡",   52, "center", lambda r: r.county_name),
    Column("level",    "等级", 38, "center", lambda r: r.level, sort_numeric=True),
    Column("type",     "类型", 42, "center", lambda r: r.display_type),
    Column("owner",    "势力", 54, "center", lambda r: r.owner_name),
    Column("governor", "主官", 104, "center", lambda r: r.governor_name),
    Column("persons",  "人物", 38, "center", lambda r: r.person_count, sort_numeric=True),
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
        char_counts = world.count_characters_by_node()      # 循环外算一次
        return [
            NodeRow.from_node(n, world,
                              person_count=char_counts.get(n.id, 0))
            for n in world.nodes.values()
        ]

    def row_key(self, row):
        return row.node_id

    def group_values(self, dim_key, group_name, rows):
        """州 / 郡组头把外官「官名-姓名」放进「主官」列（不挤 #0 列）。

        本区没有外官时退一步显示下辖首位外官「等 N 个」（多值不换行，
        完整列表走 group_tooltip）。县外官不进组头，它们在数据行的「主官」列里。
        """
        own, subs = self._region_officials(dim_key, rows)
        if own:
            return {"governor": own}
        if len(subs) == 1:
            return {"governor": subs[0]}
        if subs:
            return {"governor": f"{subs[0]} 等 {len(subs)} 个"}
        return {}

    def group_tooltip(self, dim_key, group_name, rows):
        """组头悬停：完整的外官「官名-姓名」列表（本区 + 下辖）。"""
        own, subs = self._region_officials(dim_key, rows)
        lines = []
        if own:
            lines.append(f"{group_name}：{own}")
        lines.extend(subs)
        return "\n".join(lines)

    def _region_officials(self, dim_key, rows):
        """(本区外官「官名-姓名」| None, 下辖各区的外官列表)。"""
        world = getattr(self.game_state, "world", None)
        if world is None or not rows:
            return None, []
        node_id = rows[0].node_id
        if dim_key == "state":
            own = world.official_label(node_id[:2])
            subs = [world.official_label(co) for co in
                    sorted({r.node_id[:4] for r in rows})]
        elif dim_key == "county":
            own = world.official_label(node_id[:4])
            subs = [world.official_label(r.node_id) for r in
                    sorted(rows, key=lambda r: r.node_id)]
        else:
            return None, []
        return (own or None), [s for s in subs if s]

    def context_menu_items(self, ctx):
        row = ctx.right_click_row
        single = len(ctx.selected_rows) == 1
        return [
            MenuItem(row.name, enabled=False),
            MenuItem.sep(),
            # 编辑 / 情报同一个窗：非编辑模式只读展示（标签随模式变）
            MenuItem(self._edit_label(), lambda: self._edit(row), enabled=single),
            MenuItem("批量修改所属",
                     lambda: self._change_owner(ctx.selected_rows), edit=True),
            MenuItem.sep(),
            MenuItem(self._label("编辑人物", "人物情报"),
                     lambda: self._open_ruler(row)),
            MenuItem(self._label("编辑势力", "势力情报"),
                     lambda: self._open_faction(row)),
            MenuItem.sep(),
            MenuItem("定位到地图", lambda: self.locate_on_map(row)),
            MenuItem.sep(),
            MenuItem("全部展开", lambda: self._toggle_all(True)),
            MenuItem("全部折叠", lambda: self._toggle_all(False)),
        ]

    def _edit_label(self):
        """据点面板的主入口标签：编辑模式「编辑据点」，游戏模式「据点情报」。"""
        return self._label("编辑据点", "据点情报")

    def _label(self, edit_text, info_text):
        """按模式取标签：有编辑会话 = 编辑模式（与 MenuItem(edit=True) 同一判据）。"""
        return edit_text if self.edit_session is not None else info_text

    def _open_ruler(self, row):
        """人物情报：本据点的君主（无主 → 不动作）。"""
        world = getattr(self.game_state, "world", None)
        node = world.node(row.node_id) if world else None
        if node is None or not node.owner:
            logger.debug("据点 %s 无主，人物情报不可用", row.node_id)
            return
        from game.ui.character_info_window import CharacterInfoWindow
        ch = world.character(node.owner)
        if ch is None:
            logger.warning("据点 %s 的 owner=%s 没有对应人物", node.id, node.owner)
            return
        top = self.winfo_toplevel()
        CharacterInfoWindow(self, ch, world=world,
                            font_family=getattr(top, "font_family",
                                                "TkDefaultFont"),
                            session=self.edit_session,
                            on_saved=self._notify_edit)

    def _open_faction(self, row):
        """势力情报 / 编辑势力：本据点所属势力的同一个窗。"""
        world = getattr(self.game_state, "world", None)
        node = world.node(row.node_id) if world else None
        if node is None or not node.owner:
            logger.debug("据点 %s 无主，势力情报不可用", row.node_id)
            return
        f = world.faction(node.owner)
        if f is None:
            logger.warning("据点 %s 的 owner=%s 没有对应势力", node.id, node.owner)
            return
        from game.ui.dialogs.faction_edit import edit_faction
        if edit_faction(self, world, f, self.edit_session, self._open_dialog):
            self._notify_edit()

    def _edit(self, row):
        world = getattr(self.game_state, "world", None)
        node = world.nodes.get(row.node_id) if world else None
        from game.ui.dialogs.node_edit import edit_node
        if edit_node(self, world, node, self.edit_session, self._open_dialog):
            self._notify_edit()

    def _change_owner(self, rows):
        """批量修改所属：弹窗选新 owner（可勾选同步调整人物归属）。"""
        world = getattr(self.game_state, "world", None)
        if self.edit_session is None or world is None or not rows:
            return
        from game.ui.dialogs.node_owner import change_node_owner
        if change_node_owner(self, world, rows, self.edit_session,
                             self._open_dialog):
            self._notify_edit()

    def _intel(self, kind, rows):
        names = "、".join(r.name for r in rows[:5])
        logger.debug("据点情报：kind=%s nodes=%s（共 %d）",
                     kind, names, len(rows))
