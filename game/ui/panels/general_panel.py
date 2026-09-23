# -*- coding: utf-8 -*-
"""武将列表面板。"""

import tkinter as tk
from tkinter import ttk


class GeneralPanel(ttk.Frame):
    COLUMNS = [
        ("name",     "姓名", 80),
        ("faction",  "势力", 70),
        ("lead",     "统率", 50),
        ("war",      "武力", 50),
        ("intel",    "智力", 50),
        ("politics", "政治", 50),
        ("location", "所在", 80),
    ]

    def __init__(self, master, game_state):
        super().__init__(master, padding=6)
        self.game_state = game_state
        self._build_toolbar()
        self._build_tree()

    def _build_toolbar(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 4))
        ttk.Label(bar, text="武将列表", font=("", 10, "bold")).pack(side="left")
        ttk.Button(bar, text="刷新", width=6,
                   command=self.refresh).pack(side="right")

    def _build_tree(self):
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        cols = [c[0] for c in self.COLUMNS]
        self.tree = ttk.Treeview(container, columns=cols, show="headings",
                                 selectmode="browse")
        for key, title, width in self.COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor="center")

        vsb = ttk.Scrollbar(container, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

    def refresh(self):
        self.tree.delete(*self.tree.get_children())