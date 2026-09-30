# -*- coding: utf-8 -*-
"""空间哈希：按轴向格聚合单位，供寻路 / 抢格结算查询。

纯逻辑，**不** import pygame。只做查询，不承担寻路。
"""

from battle.core import hexgrid


class SpatialHash:
    """按 (q, r) 索引单位的快照表；由调用方每 tick 重建一次。"""

    def __init__(self):
        self._cells = {}

    # ============================================================
    def rebuild(self, units):
        """按当前单位位置重建索引。"""
        self._cells = {}
        for unit in units:
            self._cells[(unit.q, unit.r)] = unit
        return self

    def unit_at(self, q, r):
        """该格的单位；空 → None。"""
        return self._cells.get((q, r))

    def is_occupied(self, q, r):
        return (q, r) in self._cells

    def occupied_cells(self):
        """已被占用的格集合。"""
        return set(self._cells)

    def units_within(self, q, r, radius=1):
        """以 (q, r) 为中心、半径 radius 内（含中心）的单位列表。"""
        cells = [(q, r)]
        for n in range(1, max(0, int(radius)) + 1):
            cells.extend(hexgrid.ring(q, r, n))
        return [self._cells[cell] for cell in cells if cell in self._cells]
