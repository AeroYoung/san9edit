# -*- coding: utf-8 -*-
"""六宫格几何与坐标变换（平顶 flat-top）。

纯函数，**不** import pygame。

坐标口径（与整体需求 §5 一致）：
- 存储 / JSON：odd-q 偏移坐标 `(col, row)`
- 内部计算：轴向坐标 `(q, r)`
- 渲染：世界像素坐标 `(x, y)`

`hex_size`（外接圆半径）一律由调用方注入，不在本模块写死。
其余模块**不得**自行实现坐标公式。
"""

import math

# 轴向邻居方向（6 个）
_DIRECTIONS = (
    (1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1),
)

_SQRT3 = math.sqrt(3.0)


# ============================================================
# 坐标变换
# ============================================================
def offset_to_axial(col, row):
    """odd-q 偏移 → 轴向。"""
    q = col
    r = row - (col - (col & 1)) // 2
    return q, r


def axial_to_offset(q, r):
    """轴向 → odd-q 偏移。"""
    col = q
    row = r + (q - (q & 1)) // 2
    return col, row


def axial_to_world(q, r, hex_size):
    """轴向 → 世界像素（格中心）。"""
    x = hex_size * 1.5 * q
    y = hex_size * _SQRT3 * (r + q / 2.0)
    return x, y


def world_to_axial(x, y, hex_size):
    """世界像素 → 轴向（鼠标拾取用），已做最近格取整。"""
    qf = (2.0 / 3.0) * x / hex_size
    rf = (-1.0 / 3.0 * x + _SQRT3 / 3.0 * y) / hex_size
    return _axial_round(qf, rf)


def _axial_round(qf, rf):
    """浮点轴向 → 最近整数轴向（立方体取整）。"""
    x = qf
    z = rf
    y = -x - z
    rx, ry, rz = round(x), round(y), round(z)
    dx, dy, dz = abs(rx - x), abs(ry - y), abs(rz - z)
    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy > dz:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return int(rx), int(rz)


# ============================================================
# 距离 / 邻域
# ============================================================
def distance(a, b):
    """两个轴向坐标的格距。"""
    dq = a[0] - b[0]
    dr = a[1] - b[1]
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def neighbors(q, r):
    """6 个邻居的轴向坐标列表。"""
    return [(q + dq, r + dr) for dq, dr in _DIRECTIONS]


def ring(q, r, n):
    """半径 n 的环（含 n = 0 → 自身）。"""
    if n <= 0:
        return [(q, r)]
    out = []
    # 从「左下」方向的邻居起步，绕一圈
    cur_q = q + _DIRECTIONS[4][0] * n
    cur_r = r + _DIRECTIONS[4][1] * n
    for dq, dr in _DIRECTIONS:
        for _ in range(n):
            out.append((cur_q, cur_r))
            cur_q += dq
            cur_r += dr
    return out


# ============================================================
# 地图范围与顶点（供相机 / 渲染层复用）
# ============================================================
def world_bounds(cols, rows, hex_size):
    """整张地图的世界包围盒尺寸 (width, height)。"""
    width = hex_size * 1.5 * (cols - 1) + hex_size * 2.0
    height = hex_size * _SQRT3 * rows
    return width, height


def hex_corners(cx, cy, hex_size):
    """平顶六边形的 6 个顶点（世界坐标），从右侧顶点起逆时针。"""
    return [
        (cx + hex_size * math.cos(math.radians(60 * i)),
         cy + hex_size * math.sin(math.radians(60 * i)))
        for i in range(6)
    ]
