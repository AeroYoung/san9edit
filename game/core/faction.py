# -*- coding: utf-8 -*-
"""势力。

约定：势力 id 即君主的人物 id（四位数字字符串）。

stance：该势力相对【玩家】的关系值，范围 -100 ~ 100。
    <  0  → 敌对
    > 80  → 盟友
    其余  → 中立
玩家自身的 stance 无意义（永远归在"玩家"组）。

gold / food 为派生值（§6.1）：名下据点求和，不落盘、不可赋值。
"""


class Faction:
    def __init__(self, fid, name, color="#888888",
                 prestige=0, stance=0):
        self.id = fid                # = 君主人物 id
        self.name = name
        self.color = color
        self.prestige = int(prestige)
        self.stance = int(stance)
        self._nodes_ref = None       # ★ World 注入（world.nodes dict 引用）

    @property
    def ruler_id(self):
        return self.id

    @property
    def gold(self):
        """名下据点金钱求和。无主据点不计。"""
        if self._nodes_ref is None:
            return 0
        return sum(n.gold for n in self._nodes_ref.values()
                   if n.owner == self.id)

    @property
    def food(self):
        """名下据点军粮求和。"""
        if self._nodes_ref is None:
            return 0
        return sum(n.food for n in self._nodes_ref.values()
                   if n.owner == self.id)

    @classmethod
    def from_dict(cls, fid, d):
        """从剧本 dict 构造。不再读 gold / food。"""
        return cls(
            fid=fid,
            name=d.get("name", fid),
            color=d.get("color", "#888888"),
            prestige=d.get("prestige", 0),
            stance=d.get("stance", 0),
        )

    def to_dict(self):
        """序列化。不写 gold / food（派生值）。"""
        return {
            "name": self.name,
            "color": self.color,
            "prestige": self.prestige,
            "stance": self.stance,
        }

    def stance_label(self):
        """返回相对玩家的关系标签。"""
        if self.stance < 0:
            return "敌对"
        if self.stance > 80:
            return "盟友"
        return "中立"

    def __repr__(self):
        return f"<Faction {self.id} {self.name} stance={self.stance}>"
