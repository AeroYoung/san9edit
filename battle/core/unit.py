# -*- coding: utf-8 -*-
"""部队数据模型（纯逻辑，**不** import pygame）。

一个部队 = 一个棋子。JSON 只存
`id` / `side` / `type` / `col` / `row` / `troops` / `morale` / `stamina` /
`facing` / `general_id`；兵力上限与能力值一律**查兵种表**，不在单位上硬编码。
"""

from battle.core import hexgrid
from battle.core import unit_types


class Unit:
    """棋子。构造后字段可读；派生值走 property。"""

    def __init__(self, uid, side, type_key, q, r,
                 troops, morale=100.0, stamina=100.0,
                 facing=0, general_id=None):
        self.id = uid
        self.side = side
        self.type = type_key
        self.q = q
        self.r = r
        self.troops = troops
        self.morale = morale
        self.stamina = stamina
        self.facing = facing
        self.general_id = general_id

        # 运行时字段：本步恒定
        self.alive = True
        self.death_reason = None
        self.command = None

    # ============================================================
    # 只读派生值（不落盘，一律查兵种表）
    # ============================================================
    @property
    def type_def(self):
        """兵种定义 dict；未知兵种 → None。"""
        return unit_types.get(self.type)

    @property
    def name(self):
        """兵种显示名（如「具装甲骑」）；未知 → 空串。"""
        t = self.type_def
        return t["name"] if t else ""

    @property
    def category(self):
        """兵种类别（骑 / 步 / 弓）；未知 → None。"""
        return unit_types.category_of(self.type)

    @property
    def troops_max(self):
        return self._from_type("troops_max", 0)

    @property
    def move_points(self):
        return self._from_type("move_points", 0)

    @property
    def attack(self):
        """近程攻击力（远程另取 attack_ranged，本步不消费）。"""
        return self._from_type("attack_melee", 0)

    @property
    def defense(self):
        return self._from_type("defense", 0)

    @property
    def attack_range(self):
        return self._from_type("attack_range", 1)

    @property
    def attack_cooldown(self):
        return self._from_type("attack_cooldown", 0)

    @property
    def collision_priority(self):
        """抢格优先级（越小越优先，兵种表 1–10）；未知兵种 → 最大号（最后处理）。"""
        return self._from_type("collision_priority", 99)

    def _from_type(self, field, default):
        t = self.type_def
        return t[field] if t else default

    # ============================================================
    # 坐标
    # ============================================================
    def offset(self):
        """存储用的 odd-q 偏移坐标 (col, row)。"""
        return hexgrid.axial_to_offset(self.q, self.r)

    # ============================================================
    # 构造
    # ============================================================
    @classmethod
    def from_dict(cls, d, side):
        """读 JSON 一条记录构造 Unit。

        `side` 参数**优先于** `d["side"]`（防脏数据）。
        前置条件：`d` 已通过校验（id / type / col / row 齐全，数值已钳制）——
        校验与丢弃在 `core/battle_state.py` 里做。
        """
        col = int(d["col"])
        row = int(d["row"])
        q, r = hexgrid.offset_to_axial(col, row)
        return cls(
            uid=str(d["id"]),
            side=side,
            type_key=str(d["type"]),
            q=q, r=r,
            troops=int(d["troops"]),
            morale=float(d.get("morale", 100.0)),
            stamina=float(d.get("stamina", 100.0)),
            facing=int(d.get("facing", 0)),
            general_id=d.get("general_id"),
        )
