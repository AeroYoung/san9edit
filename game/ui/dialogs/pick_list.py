# -*- coding: utf-8 -*-
"""弹窗里用的通用单选列表。

GenericListPanel 的裁剪副本：强制单选、不分组、无右键菜单、Ctrl+A 无效。
列与取值由调用方在构造时给 —— 默认不读 PANEL_COLUMNS（`PANEL_KEY = None`），
避免弹窗里的临时列表串到面板的用户列配置；要复用面板列配置的子类
（如 NodePickList）自己把 PANEL_KEY 指过去即可。
"""

import logging
from dataclasses import dataclass

from game.ui.panels.list.panel import GenericListPanel

logger = logging.getLogger(__name__)


@dataclass
class WorldHolder:
    """GenericListPanel 只要求 game_state.world。"""
    world: object


class PickList(GenericListPanel):
    SELECT_MODE = "browse"        # 强制单选
    GROUP_DIMS = {}               # 空 → 不建分组条
    DEFAULT_GROUP = ()
    GROUP_TITLE_COUNT = False     # 弹窗列表不需要「（N）」
    PANEL_KEY = None              # 不读 PANEL_COLUMNS
    COLUMNS = ()
    NAME_COLUMN = None

    def __init__(self, master, game_state, columns, name_column,
                 rows_fn, key_fn):
        # 实例属性优先于类属性（同 FactionPanel 的 NAME_COLUMN 做法）
        self.COLUMNS = tuple(columns)
        self.NAME_COLUMN = name_column
        self._rows_fn = rows_fn
        self._key_fn = key_fn
        super().__init__(master, game_state)

    # ------------------------------------------------------------
    # GenericListPanel 钩子
    # ------------------------------------------------------------
    def fetch_rows(self):
        return list(self._rows_fn())

    def row_key(self, row):
        return self._key_fn(row)

    def context_menu_items(self, ctx):
        return []                     # 空列表 → 不弹右键菜单

    def _on_select_all(self, event=None):
        return "break"                # 禁用 Ctrl+A 全选

    # ------------------------------------------------------------
    # 对外
    # ------------------------------------------------------------
    def selected_row(self):
        selection = self.tree.selection()
        if not selection:
            return None
        return self._item_rows.get(selection[0])

    def select_key(self, key):
        """按 row_key 选中一行；命中返回 True。"""
        item = self._row_items.get(key)
        if item is None:
            return False
        self.tree.selection_set(item)
        self.tree.see(item)
        return True
