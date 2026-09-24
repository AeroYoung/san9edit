# -*- coding: utf-8 -*-
"""据点列表的一行数据（纯展示层，与 Node 解耦）。"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class NodeRow:
    node_id: str
    name: str
    type: str
    level: int
    coords: tuple
    state_name: str
    county_name: str
    owner_id: Optional[str]
    owner_name: str
    is_capital: bool = False 
    governor_name: str = "—"     # 预留
    person_count: int = 0        # 预留

    @property
    def display_type(self):           # ★ 新增
        return "郡治" if self.is_capital else self.type

    @classmethod
    def from_node(cls, node, world):
        owner_name = "—"
        if node.owner:
            f = world.faction(node.owner) if world else None
            if f is not None:
                owner_name = f.name

        return cls(
            node_id=node.id,
            name=node.name,
            type=node.type,
            level=node.level,
            coords=node.coords,
            state_name=world.state_name(node.state_id),
            county_name=world.county_name(node.county_id),
            owner_id=node.owner,
            owner_name=owner_name,
            is_capital=node.is_capital,     # ★ 新增
        )