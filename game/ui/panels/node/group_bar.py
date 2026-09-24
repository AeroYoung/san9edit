# -*- coding: utf-8 -*-
"""分组维度选择条：点选顺序 = 嵌套层级顺序（从外到内）。"""

import tkinter as tk
from tkinter import ttk


class GroupBar(ttk.Frame):
    def __init__(self, master, dims, on_change, initial_selected=None):
        """dims: dict[key -> 显示名]"""
        super().__init__(master)
        self._dims = dict(dims)
        self._on_change = on_change
        self._selected = []          # 按点选顺序
        self._vars = {}              # key -> BooleanVar

        ttk.Label(self, text="分组：").pack(side="left")

        for key, title in self._dims.items():
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(
                self, text=title, variable=var,
                command=lambda k=key: self._toggle(k),
            )
            cb.pack(side="left", padx=1)
            self._vars[key] = var

        self._order_label = ttk.Label(self, text="", foreground="#555")
        self._order_label.pack(side="left", padx=(8, 0))

        # ★ 应用初始选中（不触发 on_change）
        if initial_selected:
            for key in initial_selected:
                if key in self._vars:
                    self._vars[key].set(True)
                    self._selected.append(key)

        self._sync_label()

    def selected(self):
        return list(self._selected)

    def _toggle(self, key):
        if self._vars[key].get():
            if key not in self._selected:
                self._selected.append(key)
        else:
            if key in self._selected:
                self._selected.remove(key)
        self._sync_label()
        self._on_change()

    def _sync_label(self):
        if self._selected:
            text = " > ".join(self._dims[k] for k in self._selected)
            self._order_label.config(text=f"顺序：{text}")
        else:
            self._order_label.config(text="（不分组）")