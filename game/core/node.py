# -*- coding: utf-8 -*-
"""据点。

id 为六位字符串 "州(2)+郡(2)+县(2)"，例如 "010101"。
由此可推 state_id / county_id，不需要额外索引。

静态字段（来自 map.geojson）：
    id / name / coords / type / level / is_capital
动态字段（来自剧本覆盖）：
    owner / troops / gold / food
"""


class Node:
    def __init__(self, nid, name, coords, type_="城",
                 level=5, is_capital=False,
                 owner=None, troops=0, gold=0, food=0):
        # 静态
        self.id = nid
        self.name = name
        self.coords = tuple(coords)
        self.type = type_
        self.level = int(level)
        self.is_capital = bool(is_capital)

        # 动态
        self.owner = owner          # 势力 id 或 None
        self.troops = int(troops)
        self.gold = int(gold)
        self.food = int(food)

    @property
    def state_id(self):
        return self.id[:2]

    @property
    def county_id(self):
        return self.id[:4]

    def is_owned(self):
        return self.owner is not None

    def to_dict(self):
        """序列化（编辑用）。写全字段，含静态 + 动态。"""
        return {
            "owner": self.owner,
            "troops": self.troops,
            "gold": self.gold,
            "food": self.food,
            "type": self.type,
            "level": self.level,
            "is_capital": self.is_capital,
        }

    def __repr__(self):
        return (f"<Node {self.id} {self.name} "
                f"{self.type} Lv{self.level}>")