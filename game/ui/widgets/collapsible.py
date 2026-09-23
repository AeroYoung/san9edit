# -*- coding: utf-8 -*-
"""可折叠分组控件。

用法：
    box = CollapsibleSection(parent, title="县点样式",
                             desc="...", on_reset=self._reset_group)
    box.body        # 内容区，往这里塞控件
    box.set_expanded(True)
"""

import tkinter as tk

from game.config.style import THEME, FONT_SIZES


class CollapsibleSection(tk.Frame):
    def __init__(self, master, title, desc="", on_reset=None,
                 expanded=False, font_family="TkDefaultFont"):
        super().__init__(master, bg=THEME["panel_bg"],
                         highlightthickness=1,
                         highlightbackground=THEME["status_sep"])
        self.font_family = font_family
        self._expanded = bool(expanded)

        # ---------- 标题条 ----------
        bar = tk.Frame(self, bg=THEME["panel_header_bg"], cursor="hand2")
        bar.pack(fill="x")

        self._arrow = tk.Label(
            bar, text="▶", width=2,
            bg=THEME["panel_header_bg"], fg="#444444",
            font=(font_family, FONT_SIZES["panel_title"]),
        )
        self._arrow.pack(side="left", padx=(6, 0), pady=6)

        title_lbl = tk.Label(
            bar, text=title, anchor="w",
            bg=THEME["panel_header_bg"], fg="#222222",
            font=(font_family, FONT_SIZES["panel_title"], "bold"),
        )
        title_lbl.pack(side="left", pady=6)

        if on_reset is not None:
            reset_btn = tk.Label(
                bar, text="↺ 恢复本组默认", cursor="hand2",
                bg=THEME["panel_header_bg"], fg="#2C6EAF",
                font=(font_family, FONT_SIZES["panel_body"]),
            )
            reset_btn.pack(side="right", padx=8, pady=6)
            reset_btn.bind("<Button-1>",
                           lambda e: on_reset(self))
            reset_btn.bind("<Enter>",
                lambda e: reset_btn.configure(fg="#1B4F82"))
            reset_btn.bind("<Leave>",
                lambda e: reset_btn.configure(fg="#2C6EAF"))

        for w in (bar, self._arrow, title_lbl):
            w.bind("<Button-1>", lambda e: self.toggle())

        # ---------- 描述行 ----------
        if desc:
            desc_lbl = tk.Label(
                self, text=desc, justify="left", anchor="w", wraplength=800,
                bg=THEME["panel_bg"], fg="#666666",
                font=(font_family, FONT_SIZES["panel_body"]),
            )
            desc_lbl.pack(fill="x", padx=10, pady=(4, 0))

        # ---------- 内容区 ----------
        self.body = tk.Frame(self, bg=THEME["panel_bg"])
        # 初始按 expanded 决定是否 pack

        self.set_expanded(self._expanded)

    def toggle(self):
        self.set_expanded(not self._expanded)

    def set_expanded(self, flag):
        self._expanded = bool(flag)
        if self._expanded:
            self.body.pack(fill="x", padx=10, pady=(4, 8))
            self._arrow.configure(text="▼")
        else:
            self.body.pack_forget()
            self._arrow.configure(text="▶")