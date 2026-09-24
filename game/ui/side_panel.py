# -*- coding: utf-8 -*-
"""右侧 Tab 集合容器。"""

from tkinter import ttk

from .panels.faction_panel import FactionPanel
from .panels.node import NodePanel
from .panels.character_panel import CharacterPanel
from .panels.troop_panel import TroopPanel


class SidePanel(ttk.Frame):
    def __init__(self, master, game_state, map_controller=None):
        super().__init__(master, width=340)
        self.game_state = game_state
        self.map_controller = map_controller
        self.pack_propagate(False)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=2, pady=2)
        self._add_tabs()

    def _add_tabs(self):
        self.notebook.add(FactionPanel(self.notebook, self.game_state),
                          text=" 势力 ")
        self.notebook.add(
            NodePanel(self.notebook, self.game_state, self.map_controller),  # ★
            text=" 据点 ",
        )
        self.notebook.add(CharacterPanel(self.notebook, self.game_state),
                          text=" 人物 ")
        self.notebook.add(TroopPanel(self.notebook, self.game_state),
                          text=" 部队 ")

    def refresh_all(self):
        for tab_id in self.notebook.tabs():
            widget = self.notebook.nametowidget(tab_id)
            if hasattr(widget, "refresh"):
                widget.refresh()