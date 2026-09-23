# -*- coding: utf-8 -*-
"""人物面板。

数据源：game_state.world.characters。
"""

from tkinter import ttk


class CharacterPanel(ttk.Frame):
    _COLUMNS = (
        ("id",     "ID",    60),
        ("name",   "姓名",  80),
        ("faction","势力",  70),
        ("node",   "所在",  80),
        ("lead",   "统率",  44),
        ("might",  "武力",  44),
        ("int",    "智力",  44),
        ("pol",    "政治",  44),
        ("cha",    "魅力",  44),
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

        for c in world.characters.values():
            faction_name = "—"
            if c.faction:
                f = world.faction(c.faction)
                if f:
                    faction_name = f.name
            node_name = "—"
            if c.node:
                n = world.node(c.node)
                if n:
                    node_name = n.name
            self.tree.insert(
                "", "end",
                values=(c.id, c.name, faction_name, node_name,
                        c.leadership, c.might, c.intelligence,
                        c.politics, c.charisma),
            )