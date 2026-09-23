# -*- coding: utf-8 -*-
"""据点面板。

数据源：game_state.world.nodes（World 加载后可用）。
"""

from tkinter import ttk


class NodePanel(ttk.Frame):
    _COLUMNS = (
        ("id",      "ID",     70),
        ("name",    "名称",   80),
        ("type",    "类型",   60),
        ("level",   "规模",   44),
        ("owner",   "势力",   70),
        ("troops",  "兵力",   60),
        ("gold",    "金钱",   60),
        ("food",    "军粮",   70),
    )

    def __init__(self, master, game_state):
        super().__init__(master)
        self.game_state = game_state
        self._build_ui()

    def _build_ui(self):
        cols = [c[0] for c in self._COLUMNS]
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for key, title, width in self._COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=2, pady=2)

    def refresh(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        world = getattr(self.game_state, "world", None)
        if world is None:
            return

        for node in world.nodes.values():
            owner_name = "—"
            if node.owner:
                f = world.faction(node.owner)
                if f:
                    owner_name = f.name
            self.tree.insert(
                "", "end",
                values=(node.id, node.name, node.type, node.level,
                        owner_name, node.troops, node.gold, node.food),
            )