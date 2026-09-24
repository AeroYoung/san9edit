#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三国路网生成脚本 v7 —— 固定道路作为种子网络 + 禁止道路组合

新增：
  fixed_roads.json 支持 forbidden_roads 字段，
  所有生成步骤（候选、贪心加边、连通兜底）都会跳过禁止组合。
  若同一对同时出现在 roads 和 forbidden_roads，以 forbidden 为准。

适配：
  读取 map_processed.geojson（预处理后：县→城，渡口/津→渡口）。

依赖：
  pip install shapely numpy
"""

import json
import math
import os
from collections import defaultdict

import numpy as np
from shapely.geometry import Point, LineString, Polygon
from shapely.strtree import STRtree


# ==================== 配置 ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MAP_FILE          = os.path.join(BASE_DIR, "map_processed.geojson")
WATER_FILE        = os.path.join(BASE_DIR, "water.geojson")
MOUNTAIN_FILE     = os.path.join(BASE_DIR, "mountains.geojson")
FIXED_ROADS_FILE  = os.path.join(BASE_DIR, "fixed_roads.json")
OUTPUT_FILE       = os.path.join(BASE_DIR, "roads.geojson")

CORRIDOR_WIDTH        = 0.05
CORRIDOR_PRUNE_RATIO  = 0.35
CORRIDOR_EDGE_MARGIN  = 0.02

SAME_LEVEL_MAX_DIST = 0.35

NODE_TOL         = 0.02
SPECIAL_NODE_TOL = 0.03

MAX_INTERSECTION_ROUNDS = 12

BASE_DIFF       = 1.3
MOUNTAIN_BONUS  = 0.3
RIVER_BONUS     = 0.05
BIG_RIVER_BONUS = 0.15
SEA_BONUS       = 0.6

BIG_RIVER_KEYS = ("江", "黄河", "（黄）河")
SEA_KEYS       = ("海", "泽", "湖")


# ==================== 基础工具 ====================
def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def edge_key(na, nb):
    """无向边统一 key"""
    return tuple(sorted([na["id"], nb["id"]]))


def tree_query(tree, geom):
    if tree is None:
        return []
    try:
        return [int(i) for i in tree.query(geom, predicate="intersects")]
    except TypeError:
        return [int(i) for i in tree.query(geom)]


def dist_deg(x1, y1, x2, y2):
    return math.hypot(x2 - x1, y2 - y1)


def dist_km(x1, y1, x2, y2):
    avg_lat = (y1 + y2) * 0.5
    cos_lat = math.cos(math.radians(avg_lat))
    dx = (x2 - x1) * 111.32 * cos_lat
    dy = (y2 - y1) * 111.32
    return math.hypot(dx, dy)


def point_to_segment_dist(px, py, seg):
    x1, y1 = seg[0]
    x2, y2 = seg[1]
    dx, dy = x2 - x1, y2 - y1
    if abs(dx) < 1e-12 and abs(dy) < 1e-12:
        return math.hypot(px - x1, py - y1)
    t = ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def extract_points(geom):
    if geom.is_empty:
        return []
    t = geom.geom_type
    if t == "Point":
        return [geom]
    if t == "MultiPoint":
        return list(geom.geoms)
    if t == "LineString":
        return [Point(geom.coords[0]), Point(geom.coords[-1])]
    if t == "GeometryCollection":
        pts = []
        for g in geom.geoms:
            pts.extend(extract_points(g))
        return pts
    return []


def classify_road(na, nb):
    if na["state_id"] != nb["state_id"]:
        return "州间道"
    if na["county_id"] != nb["county_id"]:
        return "郡间道"
    return "郡内道"


# ==================== 数据加载 ====================
def load_map_nodes(map_data):
    nodes = []
    for state in map_data.get("states", []):
        for county in state.get("counties", []):
            for city in county.get("cities", []):
                nodes.append({
                    "id":         city["id"],
                    "name":       city["name"],
                    "x":          float(city["coords"][0]),
                    "y":          float(city["coords"][1]),
                    "type":       city.get("type", "城"),
                    "level":      int(city.get("level", 5)),
                    "is_capital": bool(city.get("is_capital", False)),
                    "county":     county["name"],
                    "county_id":  county["id"],
                    "state":      state["name"],
                    "state_id":   state["id"],
                })
    return nodes


def load_geometries(path):
    if not os.path.exists(path):
        print(f"  [提示] 未找到 {path}，跳过")
        return [], []

    data = load_json(path)
    geoms, names = [], []
    for feat in data.get("features", []):
        g = feat.get("geometry", {}) or {}
        props = feat.get("properties", {}) or {}
        name = props.get("title") or props.get("name") or "未知"
        gtype = g.get("type")
        coords = g.get("coordinates")
        if coords is None:
            continue
        try:
            if gtype == "Polygon":
                poly = Polygon(coords[0])
                if not poly.is_valid: poly = poly.buffer(0)
                if not poly.is_empty:
                    geoms.append(poly); names.append(name)
            elif gtype == "MultiPolygon":
                for c in coords:
                    poly = Polygon(c[0])
                    if not poly.is_valid: poly = poly.buffer(0)
                    if not poly.is_empty:
                        geoms.append(poly); names.append(name)
            elif gtype == "LineString":
                geoms.append(LineString(coords)); names.append(name)
            elif gtype == "MultiLineString":
                for c in coords:
                    geoms.append(LineString(c)); names.append(name)
        except Exception as e:
            print(f"  [警告] 加载 {name} 失败: {e}")
    return geoms, names

def _parse_edge_specs(spec_list, label, node_by_id, node_by_name):
    """
    解析 {from,to} 或 [from,to] 列表（用于 forbidden_roads 或旧格式单边），
    返回 [(na, nb), ...]，附带跳过统计。
    """
    result = []
    seen = {}
    skipped_bad = 0
    skipped_dup = 0

    for idx, item in enumerate(spec_list):
        line_no = idx + 1

        if isinstance(item, dict):
            f, t = item.get("from"), item.get("to")
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            f, t = item[0], item[1]
        else:
            print(f"  [警告] {label} 第 {line_no} 项格式错误: {item!r}")
            skipped_bad += 1
            continue

        na = node_by_id.get(f) or node_by_name.get(f)
        nb = node_by_id.get(t) or node_by_name.get(t)
        if na is None:
            print(f"  [警告] {label} 第 {line_no} 项起点未找到: {f!r}")
            skipped_bad += 1
            continue
        if nb is None:
            print(f"  [警告] {label} 第 {line_no} 项终点未找到: {t!r}")
            skipped_bad += 1
            continue
        if na["id"] == nb["id"]:
            print(f"  [警告] {label} 第 {line_no} 项起终相同: {na['name']}→{nb['name']}")
            skipped_bad += 1
            continue

        key = edge_key(na, nb)
        if key in seen:
            first_line, first_dir = seen[key]
            tag = "完全重复" if first_dir == (na["id"], nb["id"]) else "反向重复"
            print(f"  [去重] {label} 第 {line_no} 项与第 {first_line} 项重复 "
                  f"({tag}: {na['name']}→{nb['name']})，已跳过")
            skipped_dup += 1
            continue

        seen[key] = (line_no, (na["id"], nb["id"]))
        result.append((na, nb))

    return result, skipped_bad, skipped_dup


def _parse_fixed_paths(spec_list, label, node_by_id, node_by_name):
    """
    解析固定道路路径数组。
    每个元素可以是：
      - 路径数组，如 ["A", "B", "C"]，表示 A-B, B-C
      - 旧格式 {from, to}
    返回 [(na, nb), ...]，附带跳过统计。
    """
    result = []
    seen = {}
    skipped_bad = 0
    skipped_dup = 0

    for idx, item in enumerate(spec_list):
        line_no = idx + 1

        # 旧格式：单边 {from, to}
        if isinstance(item, dict):
            pairs = [(item.get("from"), item.get("to"))]
        # 新格式：路径数组
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            pairs = []
            for k in range(len(item) - 1):
                pairs.append((item[k], item[k + 1]))
        else:
            print(f"  [警告] {label} 第 {line_no} 项格式错误: {item!r}")
            skipped_bad += 1
            continue

        for f, t in pairs:
            if f is None or t is None:
                print(f"  [警告] {label} 第 {line_no} 项缺少节点: {f!r} → {t!r}")
                skipped_bad += 1
                continue

            na = node_by_id.get(f) or node_by_name.get(f)
            nb = node_by_id.get(t) or node_by_name.get(t)
            if na is None:
                print(f"  [警告] {label} 第 {line_no} 项起点未找到: {f!r}")
                skipped_bad += 1
                continue
            if nb is None:
                print(f"  [警告] {label} 第 {line_no} 项终点未找到: {t!r}")
                skipped_bad += 1
                continue
            if na["id"] == nb["id"]:
                print(f"  [警告] {label} 第 {line_no} 项起终相同: {na['name']}→{nb['name']}")
                skipped_bad += 1
                continue

            key = edge_key(na, nb)
            if key in seen:
                first_line, first_dir = seen[key]
                tag = "完全重复" if first_dir == (na["id"], nb["id"]) else "反向重复"
                print(f"  [去重] {label} 第 {line_no} 项与第 {first_line} 项重复 "
                      f"({tag}: {na['name']}→{nb['name']})，已跳过")
                skipped_dup += 1
                continue

            seen[key] = (line_no, (na["id"], nb["id"]))
            result.append((na, nb))

    return result, skipped_bad, skipped_dup


def load_fixed_roads(path, node_by_id, node_by_name):
    """
    加载固定道路 + 禁止道路。
    返回 (fixed_edges, forbidden_keys)
      - fixed_edges: [(na, nb), ...]，已剔除与 forbidden 冲突的
      - forbidden_keys: set of (id_a, id_b) 排序后的元组
    """
    if not os.path.exists(path):
        print(f"  [提示] 未找到 {path}，无固定道路")
        return [], set()

    data = load_json(path)
    fixed_specs = data.get("roads", [])
    forbidden_specs = data.get("forbidden_roads", [])

    # 固定道路：支持路径数组 + 旧格式单边
    fixed_result, bad1, dup1 = _parse_fixed_paths(
        fixed_specs, "roads", node_by_id, node_by_name
    )
    # 禁止道路：仍用 {from,to} 格式
    forbidden_result, bad2, dup2 = _parse_edge_specs(
        forbidden_specs, "forbidden_roads", node_by_id, node_by_name
    )

    forbidden_keys = {edge_key(na, nb) for na, nb in forbidden_result}

    # 从 fixed 中剔除与 forbidden 冲突的
    conflict = []
    final_fixed = []
    for na, nb in fixed_result:
        if edge_key(na, nb) in forbidden_keys:
            conflict.append((na, nb))
        else:
            final_fixed.append((na, nb))

    if conflict:
        print(f"  [冲突] 以下固定道路同时出现在 forbidden_roads 中，"
              f"以 forbidden 为准，已从固定道路中剔除：")
        for na, nb in conflict:
            print(f"    {na['name']} ↔ {nb['name']}")

    summary_fixed = f"  加载固定道路: {len(final_fixed)} 条"
    extra = []
    if dup1: extra.append(f"跳过重复 {dup1}")
    if bad1: extra.append(f"无效 {bad1}")
    if extra:
        summary_fixed += " (" + "，".join(extra) + ")"
    print(summary_fixed)

    summary_forbid = f"  加载禁止道路: {len(forbidden_keys)} 条"
    extra = []
    if dup2: extra.append(f"跳过重复 {dup2}")
    if bad2: extra.append(f"无效 {bad2}")
    if extra:
        summary_forbid += " (" + "，".join(extra) + ")"
    print(summary_forbid)

    return final_fixed, forbidden_keys

# ==================== 走廊路径 ====================
def build_corridor_path(a, b, all_nodes, exclude_ids=None, preferred_ids=None):
    if exclude_ids is None:
        exclude_ids = set()
    if preferred_ids is None:
        preferred_ids = set()

    L_ab = dist_deg(a["x"], a["y"], b["x"], b["y"])
    if L_ab < 1e-9:
        return [a, b]

    ux = (b["x"] - a["x"]) / L_ab
    uy = (b["y"] - a["y"]) / L_ab

    candidates = []
    for n in all_nodes:
        if n["id"] == a["id"] or n["id"] == b["id"]:
            continue
        if n["id"] in exclude_ids:
            continue
        px = n["x"] - a["x"]
        py = n["y"] - a["y"]
        t = px * ux + py * uy
        if t <= L_ab * CORRIDOR_EDGE_MARGIN:
            continue
        if t >= L_ab * (1 - CORRIDOR_EDGE_MARGIN):
            continue
        perp = abs(px * (-uy) + py * ux)
        if perp > CORRIDOR_WIDTH:
            continue
        is_pref = 0 if n["id"] in preferred_ids else 1
        candidates.append((t, is_pref, perp, n))

    if not candidates:
        return [a, b]

    candidates.sort(key=lambda x: (x[0], x[1], x[2]))
    path = [a] + [c[3] for c in candidates] + [b]

    threshold = CORRIDOR_WIDTH * CORRIDOR_PRUNE_RATIO
    changed = True
    while changed and len(path) > 2:
        changed = False
        worst_idx = -1
        worst_gain = 0.0
        for i in range(1, len(path) - 1):
            p = path[i - 1]; n = path[i]; q = path[i + 1]
            old_len = dist_deg(p["x"], p["y"], n["x"], n["y"]) + \
                      dist_deg(n["x"], n["y"], q["x"], q["y"])
            new_len = dist_deg(p["x"], p["y"], q["x"], q["y"])
            gain = old_len - new_len
            if n["id"] in preferred_ids:
                gain *= 0.6
            if gain > worst_gain:
                worst_gain = gain
                worst_idx = i
        if worst_idx > 0 and worst_gain > threshold:
            del path[worst_idx]
            changed = True

    return path


# ==================== 候选边构建 ====================
def find_nearest_connected(node, node_by_id, connected_ids):
    best_d = float('inf')
    best = None
    nx, ny = node["x"], node["y"]
    for cid in connected_ids:
        c = node_by_id.get(cid)
        if c is None:
            continue
        d = dist_deg(nx, ny, c["x"], c["y"])
        if d < best_d:
            best_d = d
            best = c
    return best


def build_candidate_edges(all_nodes, fixed_edges, forbidden_keys=None):
    if forbidden_keys is None:
        forbidden_keys = set()

    def _forbidden(na, nb):
        return edge_key(na, nb) in forbidden_keys

    node_by_id = {n["id"]: n for n in all_nodes}
    by_level = defaultdict(list)
    for n in all_nodes:
        by_level[n["level"]].append(n)

    if not by_level:
        return [], None

    levels_sorted = sorted(by_level.keys())
    top_level = levels_sorted[0]

    root = None
    for n in by_level[top_level]:
        if n["name"] == "雒阳":
            root = n
            break
    if root is None:
        root = by_level[top_level][0]

    print(f"  ▶ 根节点: {root['name']} (level {root['level']})")

    connected = set()
    for na, nb in fixed_edges:
        connected.add(na["id"])
        connected.add(nb["id"])

    if fixed_edges:
        sample = "、".join(f"{a['name']}-{b['name']}"
                          for a, b in fixed_edges[:4])
        more = f" 等 {len(fixed_edges)} 条" if len(fixed_edges) > 4 else ""
        print(f"  ▶ 固定道路骨架: {sample}{more}")
        print(f"     端点已作为种子: {len(connected)} 个节点")
    else:
        connected.add(root["id"])
        print(f"  ▶ 无固定道路，使用雒阳作为种子")

    cand = []
    skipped_forbidden = 0

    for level in levels_sorted:
        nodes = by_level[level]
        print(f"\n  [构建] level {level}  ({len(nodes)} 个据点)")

        new_attached = 0
        for node in nodes:
            if node["id"] in connected:
                continue
            target = find_nearest_connected(node, node_by_id, connected)
            if target is None:
                continue
            path = build_corridor_path(node, target, all_nodes,
                                       preferred_ids=connected)
            for i in range(len(path) - 1):
                na, nb = path[i], path[i + 1]
                if _forbidden(na, nb):
                    skipped_forbidden += 1
                    continue
                lv = min(na["level"], nb["level"])
                ln = dist_deg(na["x"], na["y"], nb["x"], nb["y"])
                cand.append(((lv, ln), na, nb, classify_road(na, nb)))
            connected.update(p["id"] for p in path)
            new_attached += 1

        added_same = 0
        if level >= 2:
            for node in nodes:
                if node["id"] not in connected:
                    continue
                best_d = SAME_LEVEL_MAX_DIST
                best = None
                for other in nodes:
                    if other["id"] == node["id"]: continue
                    if other["id"] not in connected: continue
                    d = dist_deg(node["x"], node["y"], other["x"], other["y"])
                    if d < best_d:
                        best_d = d
                        best = other
                if best is not None:
                    if _forbidden(node, best):
                        skipped_forbidden += 1
                        continue
                    lv = min(node["level"], best["level"])
                    ln = dist_deg(node["x"], node["y"], best["x"], best["y"])
                    cand.append(((lv + 0.5, ln), node, best, classify_road(node, best)))
                    added_same += 1

        msg = f"    新挂载 {new_attached}"
        if added_same:
            msg += f"，同级横联 {added_same}"
        msg += f"  |  已连接 {len(connected)}/{len(all_nodes)}"
        print(msg)

    if skipped_forbidden:
        print(f"\n  ▶ 候选边因禁止组合跳过 {skipped_forbidden} 条")

    return cand, root


# ==================== 平面图贪婪加边 ====================
def greedy_planar_add(cand, fixed_edges, all_nodes, forbidden_keys=None):
    if forbidden_keys is None:
        forbidden_keys = set()

    def _forbidden(na, nb):
        return edge_key(na, nb) in forbidden_keys

    node_pts_np = np.array([[n["x"], n["y"]] for n in all_nodes], dtype=np.float64)

    def at_any_node(p, tol=NODE_TOL):
        tol2 = tol * tol
        d2 = (node_pts_np[:, 0] - p.x) ** 2 + (node_pts_np[:, 1] - p.y) ** 2
        return bool(np.any(d2 <= tol2))

    accepted = []
    accepted_lines = []
    accepted_tree = None
    accepted_pairs = set()

    # 1. 固定边先入（已经过滤过冲突，这里再保险检查一次）
    print(f"\n  优先加入固定道路 {len(fixed_edges)} 条...")
    skipped_fixed = 0
    for na, nb in fixed_edges:
        if _forbidden(na, nb):
            skipped_fixed += 1
            print(f"    [跳过] 固定边被 forbidden 拦截: {na['name']} ↔ {nb['name']}")
            continue
        key = edge_key(na, nb)
        if key in accepted_pairs:
            continue
        line = LineString([(na["x"], na["y"]), (nb["x"], nb["y"])])
        accepted.append((na, nb, "固定道", line))
        accepted_lines.append(line)
        accepted_pairs.add(key)
    if accepted_lines:
        accepted_tree = STRtree(accepted_lines)
    print(f"    已加入固定边: {len(accepted)}"
          + (f"（跳过禁止 {skipped_fixed}）" if skipped_fixed else ""))

    # 2. 候选边
    cand.sort(key=lambda x: x[0])

    added = 0
    rejected = 0
    skipped_forbid = 0
    for prio, na, nb, rt in cand:
        if _forbidden(na, nb):
            skipped_forbid += 1
            continue
        key = edge_key(na, nb)
        if key in accepted_pairs:
            continue
        line = LineString([(na["x"], na["y"]), (nb["x"], nb["y"])])

        ok = True
        if accepted_tree is not None:
            for i in tree_query(accepted_tree, line):
                el = accepted_lines[i]
                if not line.intersects(el):
                    continue
                inter = line.intersection(el)
                pts = extract_points(inter)
                if not pts:
                    continue
                if not all(at_any_node(p) for p in pts):
                    ok = False
                    break

        if not ok:
            rejected += 1
            continue

        accepted_pairs.add(key)
        accepted.append((na, nb, rt, line))
        accepted_lines.append(line)
        accepted_tree = STRtree(accepted_lines)
        added += 1

    print(f"    候选边加入: {added} 条"
          f"（因交叉跳过 {rejected} 条"
          + (f"，因禁止跳过 {skipped_forbid} 条" if skipped_forbid else "")
          + "）")
    return accepted


# ==================== 交叉反复清理 ====================
def iterative_fix_intersections(accepted, fixed_keys, all_nodes,
                                max_rounds=MAX_INTERSECTION_ROUNDS):
    node_pts_np = np.array([[n["x"], n["y"]] for n in all_nodes], dtype=np.float64)

    def at_any_node(p, tol=NODE_TOL):
        tol2 = tol * tol
        d2 = (node_pts_np[:, 0] - p.x) ** 2 + (node_pts_np[:, 1] - p.y) ** 2
        return bool(np.any(d2 <= tol2))

    for round_num in range(max_rounds):
        if len(accepted) < 2:
            break

        lines = [x[3] for x in accepted]
        tree = STRtree(lines)

        to_remove = set()
        fixed_conflict_cnt = 0

        for i in range(len(lines)):
            if i in to_remove:
                continue
            for j in tree_query(tree, lines[i]):
                if j <= i or j in to_remove:
                    continue
                inter = lines[i].intersection(lines[j])
                pts = extract_points(inter)
                if not pts:
                    continue
                if all(at_any_node(p) for p in pts):
                    continue

                ki = edge_key(accepted[i][0], accepted[i][1])
                kj = edge_key(accepted[j][0], accepted[j][1])
                fi = ki in fixed_keys
                fj = kj in fixed_keys

                if fi and fj:
                    fixed_conflict_cnt += 1
                    if round_num == 0:
                        print(f"    ⚠ 两条固定道路互相交叉（请手工修正）: "
                              f"{accepted[i][0]['name']}-{accepted[i][1]['name']} × "
                              f"{accepted[j][0]['name']}-{accepted[j][1]['name']}")
                    continue

                if fi:
                    to_remove.add(j)
                elif fj:
                    to_remove.add(i)
                else:
                    li = min(accepted[i][0]["level"], accepted[i][1]["level"])
                    lj = min(accepted[j][0]["level"], accepted[j][1]["level"])
                    if li > lj:
                        to_remove.add(i); break
                    elif lj > li:
                        to_remove.add(j)
                    else:
                        if accepted[i][3].length >= accepted[j][3].length:
                            to_remove.add(i); break
                        else:
                            to_remove.add(j)

        if not to_remove:
            print(f"    第 {round_num+1} 轮: 无非法交叉 ✓"
                  + (f" (固定边冲突 {fixed_conflict_cnt} 处，已保留)"
                     if fixed_conflict_cnt else ""))
            return accepted

        print(f"    第 {round_num+1} 轮: 删除非法交叉边 {len(to_remove)} 条")
        accepted = [x for k, x in enumerate(accepted) if k not in to_remove]

    print(f"    ⚠ 达到最大轮数 {max_rounds}，可能有残余交叉")
    return accepted


# ==================== 连通性兜底 ====================
def ensure_connected(accepted, all_nodes, root_id, forbidden_keys=None):
    if forbidden_keys is None:
        forbidden_keys = set()

    def _forbidden(na, nb):
        return edge_key(na, nb) in forbidden_keys

    node_by_id = {n["id"]: n for n in all_nodes}
    node_pts_np = np.array([[n["x"], n["y"]] for n in all_nodes], dtype=np.float64)

    def at_any_node(p, tol=NODE_TOL):
        tol2 = tol * tol
        d2 = (node_pts_np[:, 0] - p.x) ** 2 + (node_pts_np[:, 1] - p.y) ** 2
        return bool(np.any(d2 <= tol2))

    def edge_conflict(line, accepted_lines, accepted_tree):
        if accepted_tree is None:
            return False
        for i in tree_query(accepted_tree, line):
            el = accepted_lines[i]
            if not line.intersects(el):
                continue
            inter = line.intersection(el)
            pts = extract_points(inter)
            if not pts:
                continue
            if not all(at_any_node(p) for p in pts):
                return True
        return False

    for iteration in range(30):
        adj = defaultdict(set)
        used_ids = set()
        for na, nb, rt, line in accepted:
            adj[na["id"]].add(nb["id"])
            adj[nb["id"]].add(na["id"])
            used_ids.add(na["id"]); used_ids.add(nb["id"])
        for n in all_nodes:
            if n["id"] not in used_ids:
                adj[n["id"]]

        visited = set(); comps = []
        for nid in adj:
            if nid in visited: continue
            comp = set(); stack = [nid]
            while stack:
                cur = stack.pop()
                if cur in visited: continue
                visited.add(cur); comp.add(cur)
                for nb in adj[cur]:
                    if nb not in visited: stack.append(nb)
            comps.append(comp)

        if len(comps) <= 1:
            print(f"    ✔ 路网已连通（{len(adj)} 个据点，1 个分量）")
            return accepted

        print(f"    ⚠ 发现 {len(comps)} 个独立路网，正在连接...")

        best_d = float('inf')
        best_pair = None
        for i in range(len(comps)):
            for j in range(i + 1, len(comps)):
                for ai in comps[i]:
                    a = node_by_id.get(ai)
                    if a is None: continue
                    for bj in comps[j]:
                        b = node_by_id.get(bj)
                        if b is None: continue
                        if _forbidden(a, b):
                            continue
                        d = dist_deg(a["x"], a["y"], b["x"], b["y"])
                        if d < best_d:
                            best_d = d
                            best_pair = (a, b)

        if best_pair is None:
            print("    ⚠ 剩余分量之间均被 forbidden 阻断，跳过")
            break

        a, b = best_pair
        path = build_corridor_path(a, b, all_nodes)
        accepted_lines = [x[3] for x in accepted]
        accepted_tree = STRtree(accepted_lines) if accepted_lines else None
        existing_keys = {edge_key(x[0], x[1]) for x in accepted}

        added = False
        for k in range(len(path) - 1):
            na, nb = path[k], path[k + 1]
            if _forbidden(na, nb):
                continue
            key = edge_key(na, nb)
            if key in existing_keys:
                continue
            line = LineString([(na["x"], na["y"]), (nb["x"], nb["y"])])
            if edge_conflict(line, accepted_lines, accepted_tree):
                continue
            accepted.append((na, nb, "连接道", line))
            accepted_lines.append(line)
            accepted_tree = STRtree(accepted_lines)
            existing_keys.add(key)
            added = True

        if not added:
            if _forbidden(a, b):
                print(f"      ⚠ 强制直连被禁止: {a['name']} ↔ {b['name']}，放弃")
            else:
                line = LineString([(a["x"], a["y"]), (b["x"], b["y"])])
                accepted.append((a, b, "连接道(直连)", line))
                print(f"      ⚠ 强制直连: {a['name']} → {b['name']}")

    return accepted


# ==================== 生成 Feature ====================
def make_road(na, nb, road_type, m_tree, m_geoms, m_names,
              w_tree, w_geoms, w_names):
    coords = [[na["x"], na["y"]], [nb["x"], nb["y"]]]
    line = LineString(coords)

    mountains_crossed = []
    if m_tree is not None:
        for i in tree_query(m_tree, line):
            if m_geoms[i].intersects(line) and m_names[i] not in mountains_crossed:
                mountains_crossed.append(m_names[i])

    waters_crossed = []
    if w_tree is not None:
        for i in tree_query(w_tree, line):
            if w_geoms[i].intersects(line) and w_names[i] not in waters_crossed:
                waters_crossed.append(w_names[i])

    mountain_bonus = MOUNTAIN_BONUS if mountains_crossed else 0.0
    water_bonus = 0.0
    for wn in waters_crossed:
        if any(k in wn for k in SEA_KEYS):
            water_bonus = max(water_bonus, SEA_BONUS)
        elif any(k in wn for k in BIG_RIVER_KEYS):
            water_bonus = max(water_bonus, BIG_RIVER_BONUS)
        else:
            water_bonus = max(water_bonus, RIVER_BONUS)

    difficulty = BASE_DIFF + mountain_bonus + water_bonus
    length_km  = dist_km(na["x"], na["y"], nb["x"], nb["y"])
    length_deg = dist_deg(na["x"], na["y"], nb["x"], nb["y"])

    return {
        "type": "Feature",
        "properties": {
            "name":              f"{na['name']}—{nb['name']}",
            "road_type":         road_type,
            "from_id":           na["id"],
            "from_name":         na["name"],
            "from_type":         na["type"],
            "from_level":        na["level"],
            "from_county":       na["county"],
            "from_county_id":    na["county_id"],
            "from_state":        na["state"],
            "from_state_id":     na["state_id"],
            "to_id":             nb["id"],
            "to_name":           nb["name"],
            "to_type":           nb["type"],
            "to_level":          nb["level"],
            "to_county":         nb["county"],
            "to_county_id":      nb["county_id"],
            "to_state":          nb["state"],
            "to_state_id":       nb["state_id"],
            "mountain_pass":     None,
            "mountain_pass_id":  None,
            "ferry":             None,
            "ferry_id":          None,
            "bridge":            "需设桥/渡" if waters_crossed else None,
            "mountains_crossed": mountains_crossed,
            "waters_crossed":    waters_crossed,
            "length_km":         round(length_km, 2),
            "length_deg":        round(length_deg, 4),
            "point_count":       2,
            "difficulty":        round(difficulty, 2),
            "effective_length_km": round(length_km * difficulty, 2),
            "diff_detail": {
                "base":           BASE_DIFF,
                "mountain_bonus": mountain_bonus,
                "water_bonus":    water_bonus,
                "region":         None,
                "region_adj":     0.0,
            },
            "note": "",
        },
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
    }


# ==================== 关隘/渡口标注 ====================
def annotate_special_nodes(roads, all_nodes):
    special = defaultdict(list)
    for nd in all_nodes:
        if nd["type"] in ("关隘", "渡口"):
            special[nd["type"]].append(nd)

    if not special:
        return roads

    for road in roads:
        coords = road["geometry"]["coordinates"]
        for s in special.get("关隘", []):
            if point_to_segment_dist(s["x"], s["y"], coords) <= SPECIAL_NODE_TOL:
                road["properties"]["mountain_pass"]    = s["name"]
                road["properties"]["mountain_pass_id"] = s["id"]
                break
        for s in special.get("渡口", []):
            if point_to_segment_dist(s["x"], s["y"], coords) <= SPECIAL_NODE_TOL:
                road["properties"]["ferry"]    = s["name"]
                road["properties"]["ferry_id"] = s["id"]
                break
    return roads


# ==================== 主流程 ====================
def main():
    print("=" * 62)
    print("三国路网生成脚本 v7 —— 固定道路作为种子网络 + 禁止道路组合")
    print("=" * 62)

    print("\n[1/6] 加载地图...")
    map_data = load_json(MAP_FILE)
    all_nodes = load_map_nodes(map_data)
    node_by_id   = {n["id"]: n   for n in all_nodes}
    node_by_name = {n["name"]: n for n in all_nodes}
    print(f"  据点总数: {len(all_nodes)}")

    print("\n[2/6] 加载山脉...")
    m_geoms, m_names = load_geometries(MOUNTAIN_FILE)
    print(f"      {len(m_geoms)} 个几何体")

    print("\n[3/6] 加载水体...")
    w_geoms, w_names = load_geometries(WATER_FILE)
    print(f"      {len(w_geoms)} 个几何体")

    print("\n[4/6] 加载固定道路 / 禁止道路...")
    fixed_edges, forbidden_keys = load_fixed_roads(
        FIXED_ROADS_FILE, node_by_id, node_by_name
    )
    fixed_keys = {edge_key(a, b) for a, b in fixed_edges}

    m_tree = STRtree(m_geoms) if m_geoms else None
    w_tree = STRtree(w_geoms) if w_geoms else None

    print("\n[5/6] 构建路网...")
    cand, root = build_candidate_edges(all_nodes, fixed_edges, forbidden_keys)
    print(f"\n  候选边总数: {len(cand)}")

    print("\n  ▶ 平面图贪婪加边（固定边优先，禁止边跳过）...")
    accepted = greedy_planar_add(cand, fixed_edges, all_nodes, forbidden_keys)
    print(f"  接受边数: {len(accepted)}")

    print("\n  ▶ 交叉迭代清理...")
    accepted = iterative_fix_intersections(accepted, fixed_keys, all_nodes)

    print("\n  ▶ 连通性兜底...")
    accepted = ensure_connected(accepted, all_nodes,
                                root["id"] if root else None,
                                forbidden_keys)

    print(f"\n[6/6] 生成 Feature（共 {len(accepted)} 条）...")
    roads = []
    for na, nb, rt, line in accepted:
        road = make_road(na, nb, rt, m_tree, m_geoms, m_names,
                         w_tree, w_geoms, w_names)
        roads.append(road)

    roads = annotate_special_nodes(roads, all_nodes)

    out = {
        "type": "FeatureCollection",
        "name": "三国道路网",
        "features": roads,
    }
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 62)
    print(f"✔ 完成 → {OUTPUT_FILE}")
    print(f"  共 {len(roads)} 条道路")

    types = defaultdict(int)
    for r in roads:
        types[r["properties"]["road_type"]] += 1
    for k, v in sorted(types.items()):
        print(f"  {k}: {v} 条")

    # 连通性统计
    adj = defaultdict(set)
    for r in roads:
        fid = r["properties"]["from_id"]
        tid = r["properties"]["to_id"]
        adj[fid].add(tid); adj[tid].add(fid)
    visited = set(); comps = []
    for nid in adj:
        if nid in visited: continue
        comp = set(); stack = [nid]
        while stack:
            cur = stack.pop()
            if cur in visited: continue
            visited.add(cur); comp.add(cur)
            for nb in adj[cur]:
                if nb not in visited: stack.append(nb)
        comps.append(comp)
    print(f"\n  连通分量数: {len(comps)}")

    # 禁止组合验证
    print("\n  禁止组合验证...")
    road_keys = {tuple(sorted([r["properties"]["from_id"],
                               r["properties"]["to_id"]])) for r in roads}
    if forbidden_keys:
        bad = [k for k in forbidden_keys if k in road_keys]
        if bad:
            print(f"    ❌ 仍有 {len(bad)} 条禁止边出现在路网中：")
            for k in bad:
                print(f"      {k}")
        else:
            print(f"    ✔ 所有 {len(forbidden_keys)} 条禁止组合均未出现")
    else:
        print("    (无禁止组合)")

    # 最终交叉检查
    print("\n  最终交叉检查...")
    lines = [LineString(r["geometry"]["coordinates"]) for r in roads]
    tree = STRtree(lines) if lines else None
    node_pts_np = np.array([[n["x"], n["y"]] for n in all_nodes], dtype=np.float64)

    def at_any_node(p, tol=NODE_TOL):
        tol2 = tol * tol
        d2 = (node_pts_np[:, 0] - p.x) ** 2 + (node_pts_np[:, 1] - p.y) ** 2
        return bool(np.any(d2 <= tol2))

    illegal = 0
    for i in range(len(lines)):
        if tree is None: break
        for j in tree_query(tree, lines[i]):
            if j <= i: continue
            inter = lines[i].intersection(lines[j])
            pts = extract_points(inter)
            if not pts: continue
            if all(at_any_node(p) for p in pts): continue
            illegal += 1
            if illegal <= 5:
                print(f"    ⚠ {roads[i]['properties']['name']} × "
                      f"{roads[j]['properties']['name']}")
    if illegal == 0:
        print("    ✔ 无非法交叉")
    else:
        print(f"    剩余非法交叉: {illegal} 处")


if __name__ == "__main__":
    main()