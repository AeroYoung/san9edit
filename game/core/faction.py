# -*- coding: utf-8 -*-
"""势力。

约定：势力 id 即君主的人物 id（四位数字字符串）。

stance：该势力相对【玩家】的关系值，范围 -100 ~ 100。
    <  0  → 敌对
    > 80  → 盟友
    其余  → 中立
玩家自身的 stance 无意义（永远归在"玩家"组）。
"""


class Faction:
    def __init__(self, fid, name, color="#888888",
                 prestige=0, gold=0, food=0, stance=0):
        self.id = fid                # = 君主人物 id
        self.name = name
        self.color = color
        self.prestige = int(prestige)
        self.gold = int(gold)
        self.food = int(food)
        self.stance = int(stance)

    @property
    def ruler_id(self):
        return self.id

    def stance_label(self):
        """返回相对玩家的关系标签。"""
        if self.stance < 0:
            return "敌对"
        if self.stance > 80:
            return "盟友"
        return "中立"

    def __repr__(self):
        return f"<Faction {self.id} {self.name} stance={self.stance}>"