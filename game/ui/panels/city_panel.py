# -*- coding: utf-8 -*-
"""城市列表面板。数据先留空，之后从 CityDatabase 拉取。"""

import tkinter as tk
from tkinter import ttk


class CityPanel(ttk.Frame):
    COLUMNS = [
        ("name",   "城市", 90),
        ("state",  "州",   60),
        ("owner",  "归属", 70),
        ("gold",   "金钱", 60),
        ("food",   "粮草", 70),
    ]

    def __init__(self, master, game_state):
        super().__init__(master, padding=6)
        self.game_state = game_state

        self._build_toolbar()
        self._build_tree()

    def _build_toolbar(self):
        bar = ttk.Frame(self)
        bar.pack(fill="x", pady=(0, 4))
        ttk.Label(bar, text="城市列表", font=("", 10, "bold")).pack(side="left")
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
            self.tree.column(key, width=width, anchor="w")

        vsb = ttk.Scrollbar(container, orient="vertical",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self._on_double_click)

    def refresh(self):
        """占位：后续接入 CityDatabase 后填充数据。"""
        self.tree.delete(*self.tree.get_children())

    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            city = self.tree.item(item, "values")[0]
            print(f"[双击城市] {city}")