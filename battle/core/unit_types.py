# -*- coding: utf-8 -*-
"""兵种定义的查询层（纯逻辑，**不** import pygame）。

定义本体是纯数据，在 `battle/balance.py` 的 `UNIT_TYPES` / `COUNTER_MATRIX`；
本模块只做查询与取值，不重复定义、不改写表。
"""

import logging
from typing import Optional

from battle import balance

logger = logging.getLogger("battle.core.unit_types")


def get(key) -> Optional[dict]:
    """兵种 key → 定义 dict；未知 / 空 → None。"""
    if not key:
        return None
    return balance.UNIT_TYPES.get(key)


def exists(key) -> bool:
    """该兵种 key 是否在表内。"""
    return get(key) is not None


def category_of(key) -> Optional[str]:
    """兵种 key → 类别（骑 / 步 / 弓）；未知 → None。"""
    t = get(key)
    return t["category"] if t else None


def counter_multiplier(attacker_category, defender_category) -> float:
    """克制倍率：COUNTER_MATRIX[攻方类别][守方类别]；任一未知 → 1.0。"""
    row = balance.COUNTER_MATRIX.get(attacker_category)
    if not row:
        return 1.0
    return row.get(defender_category, 1.0)
