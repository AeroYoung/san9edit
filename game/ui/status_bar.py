# -*- coding: utf-8 -*-
"""底部状态栏。左：系统提示；右：缩放比例、鼠标位置 / 地区名。"""

import tkinter as tk

from game.config.style import THEME, FONT_SIZES


class StatusBar(tk.Frame):
    def __init__(self, master, font_family):
        super().__init__(master, bg=THEME["status_bg"], height=26)
        self.pack_propagate(False)
        self.font_family = font_family

        self.message_var = tk.StringVar(value="就绪")
        self.zoom_var = tk.StringVar(value="")
        self.location_var = tk.StringVar(value="")

        tk.Label(
            self, textvariable=self.message_var,
            bg=THEME["status_bg"], fg=THEME["status_fg"],
            font=(font_family, FONT_SIZES["status_bar"]),
            anchor="w",
        ).pack(side="left", padx=10)

        tk.Label(
            self, textvariable=self.location_var,
            bg=THEME["status_bg"], fg="#555555",
            font=(font_family, FONT_SIZES["status_bar"]),
            anchor="e",
        ).pack(side="right", padx=10)

        tk.Label(
            self, textvariable=self.zoom_var,
            bg=THEME["status_bg"], fg="#555555",
            font=(font_family, FONT_SIZES["status_bar"]),
            anchor="e",
        ).pack(side="right", padx=10)

        # 中间分隔线
        sep = tk.Frame(self, bg=THEME["status_sep"], height=1)
        sep.place(x=0, y=0, relwidth=1)

    # ==========================================================
    def set_message(self, text):
        self.message_var.set(text)

    def set_zoom(self, text):
        self.zoom_var.set(text)

    def set_location(self, text):
        self.location_var.set(text)