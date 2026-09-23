# -*- coding: utf-8 -*-
"""部队列表面板。"""

import tkinter as tk
from tkinter import ttk


class TroopPanel(ttk.Frame):
    COLUMNS = [
        ("name",    "部队", 100),
        ("general", "主将", 80),
        ("troops",  "兵力", 70),
        ("morale",  "士气", 60),
        ("state",   "状态", 80),
    ]

    def __init__(self, master, game_state):
        super().__init__(master, padding=6)
        self.game_state = game_state
        self._build_toolbar()
        self._build_tree()

    def _build_toolbar(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 4))
        ttk.Label(bar, text="部队列表", font=("", 10, "bold")).pack(side="left")
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