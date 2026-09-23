# -*- coding: utf-8 -*-
"""势力。

约定：势力 id 即君主的人物 id（四位数字字符串）。
"""


class Faction:
    def __init__(self, fid, name, color="#888888",
                 prestige=0, gold=0, food=0):
        self.id = fid                # = 君主人物 id
        self.name = name
        self.color = color
        self.prestige = int(prestige)
        self.gold = int(gold)
        self.food = int(food)

    @property
    def ruler_id(self):
        return self.id

    def __repr__(self):
        return f"<Faction {self.id} {self.name}>"