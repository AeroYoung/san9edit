# -*- coding: utf-8 -*-
"""势力面板：按"玩家 / 盟友 / 敌对 / 中立"分组的列表。

分组规则（势力相对玩家的 stance）：
    玩家：f.id == world.player_faction_id      —— 永远第一组
    盟友：stance >  80
    敌对：stance <  0
    中立：其余
空组也显示（带 (0) 计数），结构稳定。

势力名左侧带一个势力色小方块（PhotoImage）。
"""

import tkinter as tk
from tkinter import ttk


class FactionPanel(ttk.Frame):
    # 每个分组的 key / 标题
    _GROUPS = [
        ("player",  "玩家势力"),
        ("ally",    "盟友"),
        ("hostile", "敌对"),
        ("neutral", "中立"),
    ]
    
    def __init__(self, master, game_state):
        super().__init__(master, padding=8)
        self.game_state = game_state

        # ★ 色块缓存：PhotoImage 必须保活，否则 GC 后显示空白
        self._swatches = {}
        # ★ 动态算色块边长 = 略小于行高
        
        self._SWATCH_SIZE = self._compute_swatch_size()
        print(f"[FactionPanel] 行高={self._SWATCH_SIZE + 2}, 色块={self._SWATCH_SIZE}")
        # ---------- 头部 ----------
        header = ttk.Frame(self)
        header.pack(fill="x")
        ttk.Label(header, text="势力一览", font=("", 11, "bold")).pack(anchor="w")
        ttk.Separator(self).pack(fill="x", pady=6)

        # ---------- Treeview ----------
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)

        columns = ("ruler", "prestige", "gold", "food", "stance")
        self.tree = ttk.Treeview(
            body,
            columns=columns,
            show="tree headings",
            selectmode="browse",
        )
        self.tree.heading("#0", text="势力")
        self.tree.heading("ruler", text="君主")
        self.tree.heading("prestige", text="威望")
        self.tree.heading("gold", text="金")
        self.tree.heading("food", text="粮")
        self.tree.heading("stance", text="关系")

        self.tree.column("#0", width=110, anchor="w", stretch=True)
        self.tree.column("ruler", width=70, anchor="center", stretch=False)
        self.tree.column("prestige", width=60, anchor="e", stretch=False)
        self.tree.column("gold", width=60, anchor="e", stretch=False)
        self.tree.column("food", width=70, anchor="e", stretch=False)
        self.tree.column("stance", width=50, anchor="center", stretch=False)

        vsb = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # 配色（组头 / 行）
        self.tree.tag_configure("group_player",  background="#DBEAFE",
                                                       font=("", 10, "bold"))
        self.tree.tag_configure("group_ally",    background="#DCFCE7",
                                                       font=("", 10, "bold"))
        self.tree.tag_configure("group_hostile", background="#FEE2E2",
                                                       font=("", 10, "bold"))
        self.tree.tag_configure("group_neutral", background="#F3F4F6",
                                                       font=("", 10, "bold"))
        self.tree.tag_configure("row_player",  foreground="#1E40AF")
        self.tree.tag_configure("row_ally",    foreground="#166534")
        self.tree.tag_configure("row_hostile", foreground="#991B1B")
        self.tree.tag_configure("row_neutral", foreground="#374151")

        # 首次刷新（此时 world 可能还是 None，refresh 里会安全返回）
        self.refresh()

    @staticmethod
    def _compute_swatch_size():
        """读 ttk 主题行高，返回比行高略小的色块边长。

        优先级：
            1. Style.lookup("Treeview", "rowheight")
            2. TkDefaultFont 的 linespace + 6（补偿 ttk padding）
        """
        import tkinter.font as tkfont

        row_h = None
        try:
            style = ttk.Style()
            v = style.lookup("Treeview", "rowheight")
            if v:
                row_h = int(v)
        except Exception:
            pass

        if not row_h:
            try:
                f = tkfont.nametofont("TkDefaultFont")
                row_h = f.metrics("linespace") + 6
            except Exception:
                row_h = 20

        # 色块比行高小 2 像素 —— "小一点点"
        return max(8, row_h - 6)

    # ------------------------------------------------------------
    # 色块
    # ------------------------------------------------------------
    def _make_swatch(self, color):
        """生成一个带黑色边框的纯色小方块 PhotoImage。

        做法：先整块填黑，再在内部 (1,1)-(size-1,size-1) 填势力色，
        自然形成 1 像素黑色边框。
        """
        size = self._SWATCH_SIZE
        img = tk.PhotoImage(width=size, height=size)

        # 1) 整块填黑（当边框用）
        img.put("#000000", to=(0, 0, size, size))

        # 2) 内部填势力色（留 1 像素边框）
        try:
            img.put(color, to=(1, 1, size - 1, size - 1))
        except tk.TclError:
            img.put("#888888", to=(1, 1, size - 1, size - 1))
        return img

    # ------------------------------------------------------------
    def refresh(self):
        # 清空
        for item in self.tree.get_children():
            self.tree.delete(item)
        self._swatches.clear()      # ★ 释放旧的色块引用

        world = getattr(self.game_state, "world", None)
        if world is None or not getattr(world, "factions", None):
            return

        buckets = self._bucket_factions(world)
        for key, title in self._GROUPS:
            factions = buckets[key]
            header = self.tree.insert(
                "", "end",
                text=f"{title} ({len(factions)})",
                open=True,
                tags=(f"group_{key}",),
            )
            for f in factions:
                # ★ 生成 + 缓存色块
                swatch = self._make_swatch(f.color)
                self._swatches[f.id] = swatch

                self.tree.insert(
                    header, "end",
                    text=f.name,           # 势力名
                    image=swatch,          # ★ 色块（在名字左边）
                    values=(
                        self._ruler_name(world, f),
                        f"{f.prestige:,}",
                        f"{f.gold:,}",
                        f"{f.food:,}",
                        self._stance_text(f),
                    ),
                    tags=(f"row_{key}",),
                )

    # ------------------------------------------------------------
    @staticmethod
    def _bucket_factions(world):
        """把 world.factions 按组归桶。"""
        buckets = {"player": [], "ally": [], "hostile": [], "neutral": []}
        player_id = world.player_faction_id

        for f in world.factions.values():
            if f.id == player_id:
                buckets["player"].append(f)
            elif f.stance > 80:
                buckets["ally"].append(f)
            elif f.stance < 0:
                buckets["hostile"].append(f)
            else:
                buckets["neutral"].append(f)

        # 组内按威望降序
        for key in buckets:
            buckets[key].sort(key=lambda x: (-x.prestige, x.name))
        return buckets

    @staticmethod
    def _ruler_name(world, faction):
        ruler = world.characters.get(faction.ruler_id)
        return ruler.name if ruler is not None else "—"

    @staticmethod
    def _stance_text(faction):
        """展示带符号的关系值，如 -50 / +90 / 0。"""
        if faction.stance > 0:
            return f"+{faction.stance}"
        return f"{faction.stance}"