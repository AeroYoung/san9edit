# -*- coding: utf-8 -*-
"""右侧 Tab 集合容器。"""

import logging
from tkinter import ttk

from .panels.faction_panel import FactionPanel
from .panels.node_panel import NodePanel
from .panels.character_panel import CharacterPanel
from .panels.troop_panel import TroopPanel

logger = logging.getLogger(__name__)


class SidePanel(ttk.Frame):
    TAB_KEYS = ("faction", "node", "character", "troop")

    def __init__(self, master, game_state, map_controller=None):
        super().__init__(master, width=340)
        self.game_state = game_state
        self.map_controller = map_controller
        self.pack_propagate(False)
        self.panels = {}          # key -> panel widget

        # 编辑会话回调（由 MainWindow 注入）
        self._edit_callback = None
        self._open_dialog_callback = None

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=2, pady=2)
        self._add_tabs()

    def _add_tabs(self):
        labels = {
            "faction":   " 势力 ",
            "node":      " 据点 ",
            "character": " 人物 ",
            "troop":     " 部队 ",
        }
        self.panels["faction"] = FactionPanel(
            self.notebook, self.game_state, self.map_controller)
        self.panels["node"] = NodePanel(
            self.notebook, self.game_state, self.map_controller)
        self.panels["character"] = CharacterPanel(
            self.notebook, self.game_state, self.map_controller)
        self.panels["troop"] = TroopPanel(
            self.notebook, self.game_state)
        for key in self.TAB_KEYS:
            self.notebook.add(self.panels[key], text=labels[key])
        logger.debug("注册面板：%s", list(self.panels.keys()))

    def panel(self, key):
        return self.panels.get(key)

    def select_panel(self, key):
        """切到 key 对应 tab，并返回该面板。key: faction/node/character/troop。"""
        if key not in self.TAB_KEYS:
            return None
        idx = self.TAB_KEYS.index(key)
        self.notebook.select(idx)
        return self.panels.get(key)

    def refresh_all(self):
        logger.debug("刷新全部面板")
        for tab_id in self.notebook.tabs():
            widget = self.notebook.nametowidget(tab_id)
            if hasattr(widget, "refresh"):
                widget.refresh()

    def reload_panel_columns(self):
        """设置保存后刷新所有面板的列。panels 是 {key: panel} 字典。"""
        logger.debug("重载面板列")
        panels = getattr(self, "panels", None) or {}
        for p in panels.values():
            hook = getattr(p, "reload_columns", None)
            if callable(hook):
                try:
                    hook()
                except Exception:
                    logger.warning("面板列重载失败：%s",
                                   type(p).__name__, exc_info=True)

    def set_edit_session(self, session, on_edit=None, open_dialog=None):
        """后置注入编辑会话。MainWindow 建好 session 后调用。"""
        logger.debug("注入 EditSession")
        self._edit_callback = on_edit
        self._open_dialog_callback = open_dialog
        for p in self.panels.values():
            p.edit_session = session

    def on_panel_edit(self):
        """面板编辑执行后：刷新所有面板 + 转发给 MainWindow。"""
        logger.debug("面板编辑回调")
        self.refresh_all()
        cb = getattr(self, "_edit_callback", None)
        if callable(cb):
            cb()

    def open_edit_dialog(self, dlg_factory):
        """面板通过 master 链找到本方法，转发给 MainWindow.open_edit_dialog。"""
        cb = getattr(self, "_open_dialog_callback", None)
        if callable(cb):
            return cb(dlg_factory)
        return dlg_factory()