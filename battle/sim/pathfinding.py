# -*- coding: utf-8 -*-
"""A* 寻路（纯逻辑，**不** import pygame）。

坐标全程走 `core/hexgrid.py`，本模块不自写换算公式。

- 「其他部队当前所在格」是**高代价非禁行**（路径避让），保证有解。
- 本步无地形，除被占格外所有格代价相同。
"""

import heapq
import logging

from battle.core import hexgrid

logger = logging.getLogger("battle.sim.pathfinding")

# 「其他部队所在格」的附加代价（基础代价 1 + 该值）；高代价非禁行
OCCUPIED_COST = 8


def find_path(state, unit, target):
    """A* 求 `unit` 当前位置到 `target` 的路径（**不含起点格**）。

    返回：
        列表 —— 路径（每项为轴向 (q, r)）
        `[]` —— 起点即目标（无需移动）
        `None` —— 目标越界 / 无解
    """
    tq, tr = int(target[0]), int(target[1])
    if not _in_bounds(state, tq, tr):
        logger.warning("寻路目标越界：(q=%s, r=%s)", tq, tr)
        return None

    start = (unit.q, unit.r)
    goal = (tq, tr)
    if start == goal:
        return []

    blocked = {(u.q, u.r) for u in state.units.values() if u is not unit}

    frontier = [(hexgrid.distance(start, goal), 0, start)]
    came_from = {start: None}
    best = {start: 0}
    expansions = 0
    limit = max(1, state.cols * state.rows)

    while frontier:
        _f, g, current = heapq.heappop(frontier)
        if current == goal:
            return _reconstruct(came_from, start, goal)
        if g > best.get(current, float("inf")):
            continue        # 堆里的过期条目

        expansions += 1
        if expansions > limit:
            logger.warning("A* 展开节点超限，判定不可达：%s → %s", start, goal)
            return None

        for cell in hexgrid.neighbors(*current):
            if not _in_bounds(state, *cell):
                continue
            step_cost = 1 + (OCCUPIED_COST if cell in blocked else 0)
            ng = g + step_cost
            if ng < best.get(cell, float("inf")):
                best[cell] = ng
                came_from[cell] = current
                heapq.heappush(frontier,
                               (ng + hexgrid.distance(cell, goal), ng, cell))

    return None


# ------------------------------------------------------------
def _in_bounds(state, q, r):
    """轴向坐标是否落在地图内（经 hexgrid 转偏移坐标后比较）。"""
    col, row = hexgrid.axial_to_offset(q, r)
    return 0 <= col < state.cols and 0 <= row < state.rows


def _reconstruct(came_from, start, goal):
    """回溯路径，去掉起点格。"""
    path = []
    cell = goal
    while cell is not None and cell != start:
        path.append(cell)
        cell = came_from[cell]
    path.reverse()
    return path
