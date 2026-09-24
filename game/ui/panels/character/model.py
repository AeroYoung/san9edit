# -*- coding: utf-8 -*-
"""人物列表的一行数据（纯展示层）。"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class CharacterRow:
    id: str
    name: str
    family_name: str
    sex: str
    faction_id: Optional[str]
    faction_name: str
    node_id: Optional[str]
    node_name: str
    role: Optional[str]
    leadership: int
    might: int
    intelligence: int
    politics: int
    charisma: int
    coords: Optional[tuple]

    @property
    def display_name(self):
        if self.family_name:
            return f"{self.name}（{self.family_name}）"
        return self.name

    @classmethod
    def from_character(cls, ch, world):
        faction_name = "—"
        if ch.faction and world:
            f = world.faction(ch.faction)
            if f is not None:
                faction_name = f.name

        node_name = "—"
        coords = None
        if ch.node and world:
            n = world.node(ch.node)
            if n is not None:
                node_name = n.name
                coords = n.coords

        return cls(
            id=ch.id,
            name=ch.name,
            family_name=ch.family_name,
            sex=ch.sex,
            faction_id=ch.faction,
            faction_name=faction_name,
            node_id=ch.node,
            node_name=node_name,
            role=ch.role,
            leadership=ch.leadership,
            might=ch.might,
            intelligence=ch.intelligence,
            politics=ch.politics,
            charisma=ch.charisma,
            coords=coords,
        )