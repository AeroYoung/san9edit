# -*- coding: utf-8 -*-
"""右侧 Tab 集合容器。"""

from tkinter import ttk

from .panels.faction_panel import FactionPanel
from .panels.node_panel import NodePanel
from .panels.character_panel import CharacterPanel
from .panels.troop_panel import TroopPanel


class SidePanel(ttk.Frame):
    TAB_KEYS = ("faction", "node", "character", "troop")

    def __init__(self, master, game_state, map_controller=None):
        super().__init__(master, width=340)
        self.game_state = game_state
        self.map_controller = map_controller
        self.pack_propagate(False)
        self.panels = {}          # key -> panel widget

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
        for tab_id in self.notebook.tabs():
            widget = self.notebook.nametowidget(tab_id)
            if hasattr(widget, "refresh"):
                widget.refresh()