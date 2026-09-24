# -*- coding: utf-8 -*-
"""搜索框：实时过滤，带清空按钮。

预留扩展点 parse_query：
    - 跨字段搜索（field:value）
    - 正则（/.../）
    - 拼音 / 缩写模糊
  都在这里扩展，不影响框架。
"""

import tkinter as tk
from tkinter import ttk


class SearchBar(ttk.Frame):
    def __init__(self, master, on_change, font_family=None):
        super().__init__(master)
        self._on_change = on_change

        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var)
        self.entry.pack(side="left", fill="x", expand=True, padx=(2, 2))

        self.clear_btn = ttk.Button(self, text="×", width=3, command=self.clear)
        self.clear_btn.pack(side="right")

        self.var.trace_add("write", self._on_write)

    def query(self):
        return self.var.get()

    def clear(self):
        self.var.set("")

    def parse_query(self, raw):
        """把原始查询解析成 token 列表。默认：多词 AND 包含匹配。

        预留：正则 / 跨字段 / 拼音等高级语法在此扩展。
        """
        return [t for t in raw.strip().lower().split() if t]

    def _on_write(self, *args):
        self._on_change()
