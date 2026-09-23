# -*- coding: utf-8 -*-
"""势力信息面板。暂时只有占位内容，后续接入 GameState 数据。"""

from tkinter import ttk


class FactionPanel(ttk.Frame):
    def __init__(self, master, game_state):
        super().__init__(master, padding=10)
        self.game_state = game_state

        # ---------- 头部 ----------
        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="势力信息", font=("", 11, "bold")).pack(anchor="w")
        ttk.Separator(self).pack(fill="x", pady=6)

        # ---------- 信息表格 ----------
        # 表格单独放一个子 Frame，和头部的 pack 互不干扰
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self._build_info_grid(body)

    def _build_info_grid(self, parent):
        rows = [
            ("势力名称", self.game_state.player_faction),
            ("君    主", "刘备"),
            ("都    城", "江陵"),
            ("威    望", f"{self.game_state.prestige:,}"),
            ("金    钱", f"{self.game_state.gold:,}"),
            ("军    粮", f"{self.game_state.food:,}"),
            ("城    市", "—"),
            ("武    将", "—"),
            ("部    队", "—"),
        ]
        for i, (label, value) in enumerate(rows):
            ttk.Label(parent, text=label).grid(row=i, column=0,
                                               sticky="w", pady=2)
            ttk.Label(parent, text=value).grid(row=i, column=1,
                                               sticky="w", padx=(12, 0), pady=2)
        parent.columnconfigure(1, weight=1)