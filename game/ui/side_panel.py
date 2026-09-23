# -*- coding: utf-8 -*-
"""右侧 Tab 集合容器。

新增一个 Tab 只需要两行：
    from .panels.xxx_panel import XxxPanel
    self.notebook.add(XxxPanel(self.notebook, game_state), text="标题")
"""

from tkinter import ttk

from .panels.faction_panel import FactionPanel
from .panels.city_panel import CityPanel
from .panels.general_panel import GeneralPanel
from .panels.troop_panel import TroopPanel


class SidePanel(ttk.Frame):
    def __init__(self, master, game_state):
        super().__init__(master, width=340)
        self.game_state = game_state

        # 阻止被内部内容撑大，宽度由外部 PanedWindow 控制
        self.pack_propagate(False)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=2, pady=2)

        self._add_tabs()

    def _add_tabs(self):
        self.notebook.add(FactionPanel(self.notebook, self.game_state),
                          text=" 势力 ")
        self.notebook.add(CityPanel(self.notebook, self.game_state),
                          text=" 城市 ")
        self.notebook.add(GeneralPanel(self.notebook, self.game_state),
                          text=" 武将 ")
        self.notebook.add(TroopPanel(self.notebook, self.game_state),
                          text=" 部队 ")

    def refresh_all(self):
        """切换回合或重大事件后调用，刷新所有 Tab 内容。"""
        for tab_id in self.notebook.tabs():
            widget = self.notebook.nametowidget(tab_id)
            if hasattr(widget, "refresh"):
                widget.refresh()