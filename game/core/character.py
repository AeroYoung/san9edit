# -*- coding: utf-8 -*-
"""人物。

id 为四位数字字符串（"0001"–"9999"），全局唯一。
五维上限 100。faction / node 可为 None（在野 / 无所属据点）。
"""

_DEFAULT_STAT = 50


class Character:
    def __init__(self, cid, name, faction=None, node=None,
                 leadership=_DEFAULT_STAT, might=_DEFAULT_STAT,
                 intelligence=_DEFAULT_STAT, politics=_DEFAULT_STAT,
                 charisma=_DEFAULT_STAT):
        self.id = cid
        self.name = name
        self.faction = faction
        self.node = node
        self.leadership = int(leadership)
        self.might = int(might)
        self.intelligence = int(intelligence)
        self.politics = int(politics)
        self.charisma = int(charisma)

    def is_ruler(self):
        """是否为其所属势力的君主（势力 id = 君主 id 的约定）。"""
        return self.faction is not None and self.faction == self.id

    def is_free(self):
        """是否在野（无所属势力）。"""
        return self.faction is None

    def __repr__(self):
        return f"<Character {self.id} {self.name}>"