# -*- coding: utf-8 -*-
"""势力面板：按"玩家 / 盟友 / 敌对 / 中立"分组的列表。

分组规则（势力相对玩家的 stance）：
    玩家：f.id == world.player_faction_id      —— 永远第一组
    盟友：stance >  80
    敌对：stance <  0
    中立：其余
空组也显示（带 (0) 计数），结构稳定。
"""

from tkinter import ttk


class FactionPanel(ttk.Frame):
    # 每个分组的 key / 标题 / 标签后缀
    _GROUPS = [
        ("player",  "玩家势力"),
        ("ally",    "盟友"),
        ("hostile", "敌对"),
        ("neutral", "中立"),
    ]

    def __init__(self, master, game_state):
        super().__init__(master, padding=8)
        self.game_state = game_state

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

    # ------------------------------------------------------------
    def refresh(self):
        # 清空
        for item in self.tree.get_children():
            self.tree.delete(item)

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
                self.tree.insert(
                    header, "end",
                    text=f.name,
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

        # 组内按威望降序（好看一点）
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