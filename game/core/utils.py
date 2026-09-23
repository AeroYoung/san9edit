# -*- coding: utf-8 -*-
"""与业务无关的通用工具。"""


def walk_coords(coords):
    """递归展开 GeoJSON 的任意嵌套坐标数组，产出 (lon, lat) 对。"""
    if not coords:
        return
    if isinstance(coords[0], (int, float)):
        yield coords[0], coords[1]
    else:
        for sub in coords:
            yield from walk_coords(sub)


def midpoint_of_line(coords):
    """取折线首尾两端的中点。"""
    if len(coords) == 1:
        return coords[0][0], coords[0][1]
    (lon0, lat0), (lon1, lat1) = coords[0], coords[-1]
    return (lon0 + lon1) / 2, (lat0 + lat1) / 2


def point_in_polygon(x, y, ring):
    """射线法判断点是否在多边形内。ring 是 [(x, y), ...] 顶点列表。"""
    n = len(ring)
    if n < 3:
        return False
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and \
           (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside