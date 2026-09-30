# -*- coding: utf-8 -*-
"""tick 主函数：算意图 → 统一结算 → 逐格推进。

纯逻辑，**不** import pygame。

结算口径（需求 §3.4）：
- 一格一部队，不能重叠；同一 tick 内先各部队算意图，再**统一结算**
- 结算顺序 = 抢格优先级（兵种 `collision_priority` 小者先，同兵种按部队 id 升序）
- 逐格推进并逐格判占位：第 k 格被占 → 停在上一格
- 未抢到者本 tick 停在原地，下一 tick 重新规划
- 路径下一步被占 → 本 tick 停 + 从当前位置重算到原 target（保留 target）
"""

import logging

from battle.core import hexgrid
from battle.sim.command import MoveCommand
from battle.sim.pathfinding import find_path
from battle.sim.spatial import SpatialHash

logger = logging.getLogger("battle.sim.step")


def step(state):
    """推进一个 tick。"""
    state.tick += 1

    movers = [u for u in state.units.values()
              if isinstance(u.command, MoveCommand)]
    if not movers:
        return

    # 结算顺序 = 抢格优先级
    movers.sort(key=lambda u: (u.collision_priority, u.id))

    # 当前占位快照（含全部部队，移动者也在内 —— 未离开前仍占着自己的格）
    spatial = SpatialHash().rebuild(state.units.values())
    occupied = {cell: spatial.unit_at(*cell) for cell in spatial.occupied_cells()}

    # 1) 算意图：下一格被占 → 本 tick 从当前位置重算到原 target
    replanned = 0
    for unit in movers:
        path = unit.command.path
        if not path:
            continue
        nxt = path[0]
        holder = occupied.get(nxt)
        if holder is not None and holder is not unit:
            unit.command.path = find_path(state, unit, unit.command.target) or []
            replanned += 1
    if replanned:
        logger.debug("本 tick 重算路径：%s 支", replanned)

    # 2) 统一结算：按优先级逐个推进
    for unit in movers:
        _advance(unit, occupied, state)


# ------------------------------------------------------------
def _advance(unit, occupied, state):
    """按路径逐格推进；被占则停在上一格。"""
    if not unit.command.path:
        unit.command = None       # 无路可走（或已在目标格）
        return

    target = unit.command.target
    occupied.pop((unit.q, unit.r), None)   # 本 tick 要离开原格

    moved = 0
    while moved < unit.move_points and unit.command.path:
        nxt = unit.command.path[0]
        if not _in_bounds(state, *nxt):
            unit.command = None
            break
        if nxt in occupied:
            if nxt == target:
                # 目标格被占：停在目标最近的空邻格，命令结束
                _finish_at_neighbor(unit, occupied, target, state)
            break                 # 否则停在前一格，下一 tick 重算
        unit.q, unit.r = nxt
        occupied[nxt] = unit
        unit.command.path.pop(0)
        moved += 1

    if moved == 0:
        # 一步没走（被挡 / 越界 / 收尾时没挪动）→ 把自己的格占回去。
        # ★ 不能只在「命令还在」时回填：命令被清掉也不能让格变空，否则别的部队会走进来。
        occupied[(unit.q, unit.r)] = unit

    if unit.command is not None and not unit.command.path:
        unit.command = None                   # 路径走完 = 到达


def _finish_at_neighbor(unit, occupied, target, state):
    """目标格被占：能一步走到目标最近的空邻格就走过去，命令结束。"""
    free = [cell for cell in hexgrid.neighbors(*target)
            if _in_bounds(state, *cell) and cell not in occupied]
    if free:
        nearest = min(free, key=lambda c: hexgrid.distance((unit.q, unit.r), c))
        if hexgrid.distance((unit.q, unit.r), nearest) == 1:
            unit.q, unit.r = nearest
            occupied[nearest] = unit
    unit.command = None


def _in_bounds(state, q, r):
    col, row = hexgrid.axial_to_offset(q, r)
    return 0 <= col < state.cols and 0 <= row < state.rows
