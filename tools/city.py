import json
import numpy as np
from collections import Counter
from scipy.spatial import Voronoi, cKDTree
from shapely.geometry import Polygon, Point
from shapely.ops import transform, unary_union
from shapely.validation import make_valid
from pyproj import CRS, Transformer


AREA_TOL = 1e-6   # 面积阈值（度²），小于此值视为 rounding 误差


# ============================================================
# 基础工具
# ============================================================

def ring_to_coords(ring):
    return [(float(p[0]), float(p[1])) for p in ring]


def parse_state_boundary(boundary):
    polys = []
    for poly_rings in boundary:
        if not poly_rings:
            continue
        exterior = ring_to_coords(poly_rings[0])
        if len(exterior) < 3:
            continue
        holes = [ring_to_coords(h) for h in poly_rings[1:] if len(h) >= 3]
        try:
            p = Polygon(exterior, holes)
        except Exception:
            continue
        if not p.is_valid:
            try:
                p = p.buffer(0)
            except Exception:
                continue
        if not p.is_empty:
            polys.append(p)
    if not polys:
        return None
    return polys[0] if len(polys) == 1 else unary_union(polys)


def parse_county_boundary(boundary):
    coords = ring_to_coords(boundary)
    if len(coords) < 3:
        return None
    try:
        p = Polygon(coords)
    except Exception:
        return None
    if not p.is_valid:
        try:
            p = p.buffer(0)
        except Exception:
            return None
    return p if not p.is_empty else None


def to_polygons(geom):
    if geom is None or geom.is_empty:
        return []
    t = geom.geom_type
    if t == "Polygon":
        return [geom]
    if t == "MultiPolygon":
        return list(geom.geoms)
    if t == "GeometryCollection":
        out = []
        for g in geom.geoms:
            out.extend(to_polygons(g))
        return out
    return []


def poly_to_boundary(poly):
    polys = to_polygons(poly)
    if not polys:
        return None
    biggest = max(polys, key=lambda p: p.area)
    coords = list(biggest.exterior.coords)
    if coords[0] != coords[-1]:
        coords.append(coords[0])
    if len(coords) < 4:
        return None
    return [[round(x, 8), round(y, 8)] for x, y in coords]


def multipoly_to_boundary(poly):
    polys = to_polygons(poly)
    if not polys:
        return []
    result = []
    for p in polys:
        rings = [list(p.exterior.coords)]
        for interior in p.interiors:
            rings.append(list(interior.coords))
        poly_rings = []
        for ring in rings:
            if ring[0] != ring[-1]:
                ring.append(ring[0])
            poly_rings.append([[round(x, 8), round(y, 8)] for x, y in ring])
        result.append(poly_rings)
    return result


def robust_intersect(a, b):
    try:
        inter = a.intersection(b)
    except Exception:
        try:
            inter = a.buffer(0).intersection(b.buffer(0))
        except Exception:
            return None
    if inter is None or inter.is_empty:
        return None
    polys = to_polygons(inter)
    if not polys:
        return None
    return unary_union(polys)


def largest_polygon_no_holes(geom):
    polys = to_polygons(geom)
    if not polys:
        return None
    biggest = max(polys, key=lambda p: p.area)
    if biggest.interiors:
        biggest = Polygon(biggest.exterior)
    return biggest if not biggest.is_empty else None


def merge_to_single(poly, delta=0.0):
    if poly is None or poly.is_empty:
        return None
    polys = to_polygons(poly)
    if not polys:
        return None
    if len(polys) == 1:
        return polys[0]
    if delta > 0:
        try:
            closed = poly.buffer(delta, resolution=2).buffer(-delta, resolution=2)
            cp = to_polygons(closed)
            if cp:
                return max(cp, key=lambda p: p.area)
        except Exception:
            pass
    return max(polys, key=lambda p: p.area)


def point_inside_polygon(pt, poly, tol=1e-6):
    try:
        if poly.contains(pt) or poly.touches(pt) or poly.distance(pt) < tol:
            return True
    except Exception:
        pass
    return False


# ============================================================
# 标准 Voronoi
# ============================================================

def voronoi_finite_polygons_2d(vor, radius=None):
    if vor.points.shape[1] != 2:
        raise ValueError("Requires 2D input")

    new_regions = []
    new_vertices = vor.vertices.tolist()

    center = vor.points.mean(axis=0)
    if radius is None:
        radius = float(np.ptp(vor.points, axis=0).max()) * 10
        if radius <= 0:
            radius = 1.0

    all_ridges = {}
    for (p1, p2), (v1, v2) in zip(vor.ridge_points, vor.ridge_vertices):
        all_ridges.setdefault(p1, []).append((p2, v1, v2))
        all_ridges.setdefault(p2, []).append((p1, v1, v2))

    for p1, region in enumerate(vor.point_region):
        vertices = vor.regions[region]
        if all(v >= 0 for v in vertices):
            new_regions.append(vertices)
            continue

        ridges = all_ridges.get(p1, [])
        new_region = [v for v in vertices if v >= 0]

        for p2, v1, v2 in ridges:
            if v2 < 0:
                v1, v2 = v2, v1
            if v1 >= 0:
                continue
            t = vor.points[p2] - vor.points[p1]
            t_norm = np.linalg.norm(t)
            if t_norm < 1e-12:
                continue
            t = t / t_norm
            n = np.array([-t[1], t[0]])
            midpoint = vor.points[[p1, p2]].mean(axis=0)
            direction = np.sign(np.dot(midpoint - center, n)) * n
            far_point = vor.vertices[v2] + direction * radius
            new_region.append(len(new_vertices))
            new_vertices.append(far_point.tolist())

        if not new_region:
            new_regions.append([])
            continue

        vs = np.asarray([new_vertices[v] for v in new_region])
        c = vs.mean(axis=0)
        angles = np.arctan2(vs[:, 1] - c[1], vs[:, 0] - c[0])
        new_region = np.array(new_region)[np.argsort(angles)]

        new_regions.append(new_region.tolist())

    return new_regions, np.asarray(new_vertices)


# ============================================================
# 兜底与校验
# ============================================================

def fallback_buffer(pt_xy, county_poly, diag):
    pt = Point(pt_xy[0], pt_xy[1])
    for r in [diag * 0.005, diag * 0.02, diag * 0.1, diag * 0.5]:
        try:
            inter = pt.buffer(r).intersection(county_poly)
        except Exception:
            continue
        if not inter.is_empty:
            m = merge_to_single(inter, delta=0.0)
            if m is not None and not m.is_empty:
                return m
    try:
        if not point_inside_polygon(pt, county_poly):
            nearest = county_poly.exterior.interpolate(
                county_poly.exterior.project(pt))
            buf = nearest.buffer(diag * 0.02)
            inter = buf.intersection(county_poly)
            if not inter.is_empty:
                m = merge_to_single(inter, delta=0.0)
                if m is not None and not m.is_empty:
                    return m
    except Exception:
        pass
    return county_poly


def ensure_point_inside(poly, pt_xy, county_poly, diag):
    pt = Point(pt_xy[0], pt_xy[1])
    if poly is not None and not poly.is_empty and point_inside_polygon(pt, poly):
        return poly
    for r in [diag * 0.0005, diag * 0.002, diag * 0.01, diag * 0.05]:
        try:
            buf = pt.buffer(r)
            base = poly if (poly is not None and not poly.is_empty) else Polygon()
            merged = base.union(buf).intersection(county_poly)
        except Exception:
            continue
        m = merge_to_single(merged, delta=0.0)
        if m is not None and not m.is_empty and point_inside_polygon(pt, m):
            return m
    return fallback_buffer(pt_xy, county_poly, diag)


# ============================================================
# Voronoi 区域构建
# ============================================================

def build_regions(points_arr, county_proj, do_fill=True):
    n = len(points_arr)
    if n == 0:
        return []
    if n == 1:
        return [county_proj]

    minx, miny, maxx, maxy = county_proj.bounds
    diag = ((maxx - minx) ** 2 + (maxy - miny) ** 2) ** 0.5
    if diag <= 0:
        diag = 1.0
    radius = max(diag * 20, 1.0)

    pts = points_arr.copy()
    if n >= 2:
        p0 = pts[0]
        d = pts - p0
        dir_v = pts[1] - p0
        cross = d[:, 0] * dir_v[1] - d[:, 1] * dir_v[0]
        if np.allclose(cross, 0, atol=1e-3):
            rng = np.random.default_rng(42)
            pts = pts + rng.normal(0, diag * 1e-4, pts.shape)

    try:
        vor = Voronoi(pts)
    except Exception:
        return [county_proj] * n

    try:
        regions, vertices = voronoi_finite_polygons_2d(vor, radius=radius)
    except Exception:
        return [county_proj] * n

    polygons = []
    for i, region in enumerate(regions):
        poly = None
        if region:
            try:
                poly = Polygon([vertices[j] for j in region])
                if not poly.is_valid:
                    poly = poly.buffer(0)
            except Exception:
                poly = None

        if poly is not None and not poly.is_empty:
            try:
                poly = poly.intersection(county_proj)
            except Exception:
                poly = None

        if poly is not None and not poly.is_empty:
            poly = merge_to_single(poly, delta=0.0)

        min_area = county_proj.area * 1e-9
        if poly is None or poly.is_empty or poly.area < min_area:
            poly = fallback_buffer(points_arr[i], county_proj, diag)

        polygons.append(poly)

    if do_fill:
        polygons, _, _, _ = fill_gaps_kdtree(polygons, points_arr, county_proj)

    for i in range(len(polygons)):
        polygons[i] = ensure_point_inside(
            polygons[i], points_arr[i], county_proj, diag)

    return polygons


def fill_gaps_kdtree(polygons, points_arr, county_proj, max_iter=50):
    """填充 gap。优先选相邻的 city，避免产生多块。"""
    try:
        tree = cKDTree(points_arr)
    except Exception:
        return polygons, 0, 0.0, county_proj.area

    valid = [p for p in polygons if p is not None and not p.is_empty]
    if not valid:
        return polygons, 0, county_proj.area, county_proj.area

    try:
        union = unary_union(valid)
        uncovered = county_proj.difference(union)
        initial_gap = uncovered.area if not uncovered.is_empty else 0.0
    except Exception:
        initial_gap = 0.0

    filled = 0
    for _ in range(max_iter):
        valid_idx = [i for i, p in enumerate(polygons)
                     if p is not None and not p.is_empty]
        if not valid_idx:
            break
        try:
            union = unary_union([polygons[i] for i in valid_idx])
            uncovered = county_proj.difference(union)
        except Exception:
            break
        if uncovered.is_empty:
            break
        gaps = to_polygons(uncovered)
        if not gaps:
            break

        any_change = False
        for gap in gaps:
            if gap.area < 1e-12:
                continue

            # ============ 新增：优先选相邻的 city ============
            adjacent_i = None
            try:
                for i in valid_idx:
                    if polygons[i].distance(gap) < 1e-9:
                        adjacent_i = i
                        break
            except Exception:
                adjacent_i = None

            if adjacent_i is not None:
                best_i = adjacent_i
            else:
                # KD-tree 采样投票
                samples = []
                try:
                    samples.extend(list(gap.exterior.coords))
                    for interior in gap.interiors:
                        samples.extend(list(interior.coords))
                except Exception:
                    pass
                try:
                    samples.append(list(gap.centroid.coords[0]))
                except Exception:
                    pass
                if not samples:
                    continue
                try:
                    _, idxs = tree.query(np.array(samples))
                except Exception:
                    continue
                votes = Counter(idxs.tolist())
                best_i = votes.most_common(1)[0][0]

            if polygons[best_i] is None or polygons[best_i].is_empty:
                polygons[best_i] = gap
            else:
                try:
                    merged = unary_union([polygons[best_i], gap])
                    plist = to_polygons(merged)
                    polygons[best_i] = max(plist, key=lambda p: p.area)
                except Exception:
                    continue
            filled += 1
            any_change = True

        if not any_change:
            break

    valid_idx = [i for i, p in enumerate(polygons)
                 if p is not None and not p.is_empty]
    if valid_idx:
        try:
            union = unary_union([polygons[i] for i in valid_idx])
            remaining = county_proj.difference(union)
            remaining_gap = remaining.area if not remaining.is_empty else 0.0
        except Exception:
            remaining_gap = 0.0
    else:
        remaining_gap = county_proj.area

    return polygons, filled, initial_gap, remaining_gap


# ============================================================
# 州间空隙修复
# ============================================================

def fix_state_gaps(data, min_hole_area=1e-9, max_hole_area=0.5, max_fill_ratio=0.5):
    empty = {"holes_count": 0, "filled_count": 0,
             "states_modified": [], "holes_detail": []}
    state_polys = [(s, s["_poly"]) for s in data["states"] if s.get("_poly") is not None]
    if len(state_polys) < 2:
        return empty, []
    try:
        merged = unary_union([p for _, p in state_polys])
    except Exception as e:
        print(f"  ! 州合并失败: {e}")
        return empty, []
    holes = []
    for poly in to_polygons(merged):
        for interior in poly.interiors:
            try:
                hole = Polygon(interior)
                if hole.area >= min_hole_area:
                    holes.append(hole)
            except Exception:
                continue
    states_modified = set()
    holes_detail = []
    unfilled = []
    filled = 0
    for hole in holes:
        hole_area = hole.area
        if hole_area > max_hole_area:
            unfilled.append((hole_area, f"面积 {hole_area:.4f} 超过阈值"))
            continue
        best_state = None
        best_dist = float('inf')
        for state, poly in state_polys:
            try:
                d = poly.distance(hole)
                if d < best_dist:
                    best_dist = d
                    best_state = state
            except Exception:
                continue
        if best_state is None:
            unfilled.append((hole_area, "无邻近州"))
            continue
        try:
            if hole_area > best_state["_poly"].area * max_fill_ratio:
                unfilled.append((hole_area, f"面积占 {best_state['name']} 比例过大"))
                continue
        except Exception:
            pass
        try:
            new_poly = unary_union([best_state["_poly"], hole])
            best_state["_poly"] = new_poly
            best_state["boundary"] = multipoly_to_boundary(new_poly)
            states_modified.add(best_state["name"])
            holes_detail.append((best_state["name"], hole_area, best_dist))
            filled += 1
        except Exception as e:
            unfilled.append((hole_area, f"合并失败: {e}"))
    return {
        "holes_count": len(holes),
        "filled_count": filled,
        "states_modified": list(states_modified),
        "holes_detail": holes_detail,
    }, unfilled


# ============================================================
# 县点归属清洗
# ============================================================

def clean_city_assignments(data):
    all_entries = []
    for state in data["states"]:
        for county in state["counties"]:
            cp = parse_county_boundary(county["boundary"])
            if cp is None:
                continue
            all_entries.append({
                "state": state, "county": county, "poly": cp,
            })

    moves = []
    move_info = {}

    for entry in all_entries:
        state = entry["state"]
        county = entry["county"]
        county_poly = entry["poly"]

        for city in county.get("cities", []):
            coords = city.get("coords")
            if not coords or len(coords) < 2:
                continue
            pt = Point(coords[0], coords[1])

            inside_self = False
            try:
                if county_poly.contains(pt) or county_poly.touches(pt):
                    inside_self = True
            except Exception:
                pass
            if inside_self:
                continue

            target = None
            for entry2 in all_entries:
                if entry2 is entry:
                    continue
                try:
                    if entry2["poly"].contains(pt) or entry2["poly"].touches(pt):
                        target = entry2
                        break
                except Exception:
                    continue

            extend_radius = 0.0
            reason = ""

            if target is not None:
                reason = "落在其他郡"
            else:
                best_d = float('inf')
                best_entry = None
                for entry2 in all_entries:
                    try:
                        d = entry2["poly"].distance(pt)
                        if d < best_d:
                            best_d = d
                            best_entry = entry2
                    except Exception:
                        continue
                if best_entry is not None and best_entry is not entry:
                    target = best_entry
                    extend_radius = best_d + 0.001
                    reason = f"不在任何郡，移至最近郡 (距离 {best_d:.4f})"
                else:
                    continue

            if target is None:
                continue

            move_info[city["id"]] = {
                "city_name": city["name"],
                "from_state": state["name"],
                "from_county": county["name"],
                "to_state": target["state"]["name"],
                "to_county": target["county"]["name"],
                "reason": reason,
                "extend_radius": extend_radius,
            }
            moves.append({
                "city_id": city["id"],
                "target_entry": target,
                "extend_radius": extend_radius,
            })

    moved_ids = set(m["city_id"] for m in moves)
    moved_cities = {}
    for state in data["states"]:
        for county in state["counties"]:
            cities = county.get("cities", [])
            for city in list(cities):
                if city["id"] in moved_ids:
                    moved_cities[city["id"]] = city
                    cities.remove(city)

    extended_counties = set()
    extended_states = set()

    for m in moves:
        city = moved_cities.get(m["city_id"])
        if city is None:
            continue
        target = m["target_entry"]
        target["county"].setdefault("cities", []).append(city)

        r = m["extend_radius"]
        if r > 0:
            try:
                pt = Point(city["coords"][0], city["coords"][1])
                buf = pt.buffer(r)
                extended = unary_union([target["poly"], buf])
                m2 = largest_polygon_no_holes(extended)
                if m2 is not None and not m2.is_empty:
                    target["poly"] = m2
                    target["county"]["boundary"] = poly_to_boundary(m2)
                    target["county"]["_poly"] = m2
                    extended_counties.add(
                        (target["state"]["name"], target["county"]["name"]))
                    extended_states.add(target["state"]["name"])
            except Exception:
                pass

    for state in data["states"]:
        if state["name"] not in extended_states:
            continue
        county_polys = []
        for county in state["counties"]:
            cp = parse_county_boundary(county["boundary"])
            if cp is not None:
                county_polys.append(cp)
        if county_polys:
            try:
                merged = unary_union(county_polys)
                state["_poly"] = merged
                state["boundary"] = multipoly_to_boundary(merged)
            except Exception:
                pass

    return move_info, extended_counties, extended_states


# ============================================================
# 修复前检查
# ============================================================

def check_before(data, area_tol=AREA_TOL):
    result = {"state_invalid": [], "county_invalid": [],
              "county_outside": [], "county_outside_ignored": 0}
    state_polys = {}
    for state in data["states"]:
        poly = parse_state_boundary(state["boundary"])
        if poly is None or not poly.is_valid:
            result["state_invalid"].append(state["name"])
            continue
        state_polys[state["name"]] = poly
    for state in data["states"]:
        sp = state_polys.get(state["name"])
        for county in state["counties"]:
            cp = parse_county_boundary(county["boundary"])
            if cp is None or not cp.is_valid:
                result["county_invalid"].append((state["name"], county["name"]))
                continue
            if sp is not None:
                try:
                    outside = cp.difference(sp)
                    area = outside.area if not outside.is_empty else 0.0
                    if area > area_tol:
                        result["county_outside"].append(
                            (state["name"], county["name"], area))
                    elif area > 0:
                        result["county_outside_ignored"] += 1
                except Exception:
                    pass
    return result


# ============================================================
# 主流程
# ============================================================

def main():
    print("读取 map_processed.geojson ...")
    with open("map_processed.geojson", encoding="utf-8") as f:
        data = json.load(f)

    print("\n[0] 修复前状态检查 ...")
    before = check_before(data)
    print(f"  州边界无效: {len(before['state_invalid'])} 个")
    print(f"  郡边界无效: {len(before['county_invalid'])} 个")
    print(f"  郡在州外:   {len(before['county_outside'])} 个"
          f" (另有 {before['county_outside_ignored']} 个小于阈值已忽略)")

    # ---------- Step 1 ----------
    print("\n[1] 修复州边界有效性 ...")
    state_fixed = []
    state_still_invalid = []
    for state in data["states"]:
        poly = parse_state_boundary(state["boundary"])
        if poly is None:
            state_still_invalid.append(state["name"])
            continue
        was_valid = poly.is_valid
        if not was_valid:
            fixed = to_polygons(make_valid(poly))
            if fixed:
                poly = unary_union(fixed)
        if poly is None or not poly.is_valid or poly.is_empty:
            state_still_invalid.append(state["name"])
            continue
        state["_poly"] = poly
        state["boundary"] = multipoly_to_boundary(poly)
        if not was_valid:
            state_fixed.append(state["name"])
    print(f"  修复无效州: {len(state_fixed)} 个")
    print(f"  仍无效州:   {len(state_still_invalid)} 个")

    # ---------- Step 2 ----------
    print("\n[2] 检测并修复州间空隙 ...")
    gap_info, unfilled_gaps = fix_state_gaps(data)
    print(f"  发现空洞:   {gap_info['holes_count']} 个")
    print(f"  已填补:     {gap_info['filled_count']} 个")
    print(f"  无法填补:   {len(unfilled_gaps)} 个")

    # ---------- Step 3 ----------
    print("\n[3] 修复郡边界并裁剪到州内 ...")
    county_fixed = []
    county_clipped = []
    county_still_invalid = []
    for state in data["states"]:
        state_poly = state.get("_poly")
        if state_poly is None:
            continue
        for county in state["counties"]:
            county_poly = parse_county_boundary(county["boundary"])
            if county_poly is None:
                county_still_invalid.append((state["name"], county["name"]))
                continue
            was_valid = county_poly.is_valid
            if not was_valid:
                county_poly = county_poly.buffer(0)
                if county_poly.is_empty:
                    county_still_invalid.append((state["name"], county["name"]))
                    continue
                county_fixed.append((state["name"], county["name"]))
            original_area = county_poly.area
            inter = robust_intersect(county_poly, state_poly)
            if inter is None or inter.is_empty:
                new_poly = largest_polygon_no_holes(county_poly)
                if new_poly is not None:
                    county["_poly"] = new_poly
                    county["boundary"] = poly_to_boundary(new_poly)
                continue
            new_poly = largest_polygon_no_holes(inter)
            if new_poly is None:
                new_poly = largest_polygon_no_holes(county_poly)
                if new_poly is not None:
                    county["_poly"] = new_poly
                    county["boundary"] = poly_to_boundary(new_poly)
                continue
            if new_poly.area < original_area - 1e-10:
                ratio = 1 - new_poly.area / original_area
                county_clipped.append((state["name"], county["name"], ratio))
            county["_poly"] = new_poly
            county["boundary"] = poly_to_boundary(new_poly)
    print(f"  修复无效郡: {len(county_fixed)} 个")
    print(f"  裁剪到州内: {len(county_clipped)} 个")
    print(f"  仍无效郡:   {len(county_still_invalid)} 个")

    # ---------- Step 4 ----------
    print("\n[4] 清洗县点归属 ...")
    move_info, extended_counties, extended_states = clean_city_assignments(data)
    print(f"  需要移动:       {len(move_info)} 个县点")
    if move_info:
        for cid, info in list(move_info.items())[:10]:
            print(f"    · {info['city_name']} "
                  f"({info['from_county']}/{info['from_state']}) → "
                  f"{info['to_county']}/{info['to_state']}  "
                  f"[{info['reason']}]")
        if len(move_info) > 10:
            print(f"    ... 还有 {len(move_info) - 10} 个")
    print(f"  扩展郡界:       {len(extended_counties)} 个郡")
    if extended_counties:
        for s, c in list(extended_counties)[:10]:
            print(f"    · {c} ({s})")
    if extended_states:
        print(f"  更新州界:       {len(extended_states)} 个州")

    for state in data["states"]:
        for county in state["counties"]:
            cp = parse_county_boundary(county["boundary"])
            if cp is not None:
                county["_poly"] = cp
        sp = parse_state_boundary(state["boundary"])
        if sp is not None:
            state["_poly"] = sp

    # ---------- Step 5 ----------
    print("\n[5] 生成县级边界 ...")
    city_ok = 0
    city_fallback = 0
    city_fail = 0
    coverage_fixed = []
    coverage_before = 0
    coverage_total_gap = 0.0
    multi_block_info = []

    for state in data["states"]:
        for county in state["counties"]:
            county_poly = county.get("_poly")
            if county_poly is None or county_poly.is_empty:
                continue
            cities = county.get("cities", [])
            if not cities:
                continue

            c = county_poly.centroid
            zone = int((c.x + 180) / 6) + 1
            epsg = 32600 + zone if c.y >= 0 else 32700 + zone
            crs_utm = CRS.from_epsg(epsg)
            t_utm = Transformer.from_crs("EPSG:4326", crs_utm, always_xy=True)
            t_wgs = Transformer.from_crs(crs_utm, "EPSG:4326", always_xy=True)
            county_proj = transform(t_utm.transform, county_poly)

            unique_pts = []
            unique_to_cities = []
            seen = {}
            for city in cities:
                coords = city.get("coords")
                if not coords or len(coords) < 2:
                    continue
                pt = Point(coords[0], coords[1])
                pj = transform(t_utm.transform, pt)
                key = (round(pj.x, 6), round(pj.y, 6))
                if key not in seen:
                    seen[key] = len(unique_pts)
                    unique_pts.append((pj.x, pj.y))
                    unique_to_cities.append([])
                unique_to_cities[seen[key]].append(city)

            if not unique_pts:
                continue
            pts_arr = np.array(unique_pts)

            if len(pts_arr) == 1:
                b = poly_to_boundary(transform(t_wgs.transform, county_proj))
                if b:
                    for city in unique_to_cities[0]:
                        city["boundary"] = b
                    city_ok += len(unique_to_cities[0])
                else:
                    city_fail += len(unique_to_cities[0])
                continue

            try:
                preview = build_regions(pts_arr, county_proj, do_fill=False)
                valid = [p for p in preview if p is not None and not p.is_empty]
                if valid:
                    union = unary_union(valid)
                    uncovered = county_proj.difference(union)
                    if not uncovered.is_empty and uncovered.area > 1e-12:
                        coverage_before += 1
                        coverage_total_gap += uncovered.area
                        coverage_fixed.append(
                            (state["name"], county["name"], uncovered.area))
            except Exception:
                pass

            try:
                polygons = build_regions(pts_arr, county_proj)
            except Exception as e:
                print(f"  ! {county['name']} 生成失败: {e}")
                polygons = [county_proj] * len(unique_pts)

            for i, poly in enumerate(polygons):
                used_fallback = False
                if poly is None or poly.is_empty:
                    minx, miny, maxx, maxy = county_proj.bounds
                    diag = ((maxx - minx) ** 2 + (maxy - miny) ** 2) ** 0.5
                    poly = fallback_buffer(pts_arr[i], county_proj, max(diag, 1.0))
                    used_fallback = True

                try:
                    poly_wgs = transform(t_wgs.transform, poly)
                    poly_wgs = poly_wgs.intersection(county_poly)
                    poly_wgs = merge_to_single(poly_wgs, delta=0.0)
                except Exception:
                    poly_wgs = None

                if poly_wgs is not None and not poly_wgs.is_empty:
                    pt_wgs = transform(t_wgs.transform, Point(pts_arr[i]))
                    if not point_inside_polygon(pt_wgs, poly_wgs):
                        try:
                            minx2, miny2, maxx2, maxy2 = county_poly.bounds
                            diag_w = ((maxx2 - minx2) ** 2 + (maxy2 - miny2) ** 2) ** 0.5
                            for r in [diag_w * 0.001, diag_w * 0.005, diag_w * 0.02]:
                                buf = pt_wgs.buffer(r)
                                merged = poly_wgs.union(buf).intersection(county_poly)
                                m = merge_to_single(merged, delta=0.0)
                                if m is not None and not m.is_empty \
                                        and point_inside_polygon(pt_wgs, m):
                                    poly_wgs = m
                                    used_fallback = True
                                    break
                        except Exception:
                            pass

                if poly_wgs is not None and not poly_wgs.is_empty:
                    plist = to_polygons(poly_wgs)
                    if len(plist) > 1:
                        areas = sorted([p.area for p in plist], reverse=True)
                        for c in unique_to_cities[i]:
                            multi_block_info.append({
                                "state": state["name"],
                                "county": county["name"],
                                "city": c["name"],
                                "n_blocks": len(plist),
                                "areas": areas,
                            })

                b = poly_to_boundary(poly_wgs) if poly_wgs is not None else None
                if b is None:
                    b = poly_to_boundary(county_poly)
                    used_fallback = True

                if b:
                    for city in unique_to_cities[i]:
                        city["boundary"] = b
                    if used_fallback:
                        city_fallback += len(unique_to_cities[i])
                    else:
                        city_ok += len(unique_to_cities[i])
                else:
                    city_fail += len(unique_to_cities[i])

    for state in data["states"]:
        state.pop("_poly", None)
        for county in state["counties"]:
            county.pop("_poly", None)

    out = "map_with_boundaries.geojson"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n已输出: {out}")

    # ---------- Step 6 ----------
    print("\n[6] 修复后检查 ...")
    after = check_before(data)

    city_no_boundary = []
    city_outside = []
    city_outside_ignored = 0
    city_multipoly = []
    city_point_outside = []
    county_gaps = []
    county_gaps_ignored = 0

    for state in data["states"]:
        for county in state["counties"]:
            county_poly = parse_county_boundary(county["boundary"])
            if county_poly is None:
                continue
            city_polys = []
            for city in county.get("cities", []):
                cb = city.get("boundary")
                if not cb:
                    city_no_boundary.append((county["name"], city["name"]))
                    continue
                try:
                    city_poly = Polygon(ring_to_coords(cb))
                    if not city_poly.is_valid:
                        city_poly = city_poly.buffer(0)
                    if city_poly.is_empty:
                        city_no_boundary.append((county["name"], city["name"]))
                        continue
                    if city_poly.geom_type == "MultiPolygon":
                        city_multipoly.append((county["name"], city["name"]))
                    outside = city_poly.difference(county_poly)
                    area = outside.area if not outside.is_empty else 0.0
                    if area > AREA_TOL:
                        city_outside.append(
                            (county["name"], city["name"], area))
                    elif area > 0:
                        city_outside_ignored += 1
                    coords = city.get("coords")
                    if coords and len(coords) >= 2:
                        pt = Point(coords[0], coords[1])
                        if not (city_poly.contains(pt) or city_poly.touches(pt)
                                or city_poly.distance(pt) < 1e-6):
                            city_point_outside.append(
                                (county["name"], city["name"]))
                    city_polys.append(city_poly)
                except Exception:
                    pass

            if city_polys:
                try:
                    union = unary_union(city_polys)
                    gap = county_poly.difference(union)
                    area = gap.area if not gap.is_empty else 0.0
                    if area > AREA_TOL:
                        county_gaps.append(
                            (state["name"], county["name"], area))
                    elif area > 0:
                        county_gaps_ignored += 1
                except Exception:
                    pass

    total_cities = sum(len(c.get("cities", []))
                       for s in data["states"] for c in s["counties"])

    # ---------- 报告 ----------
    print("\n" + "=" * 60)
    print("                       修 复 报 告")
    print("=" * 60)
    print(f"  （面积阈值：{AREA_TOL} 度²，约 {AREA_TOL * 12321 * 1e6:.0f} m²；")
    print(f"   低于此值视为浮点舍入误差，不计入问题）")

    print("\n【州边界有效性】")
    print(f"  修复前无效:     {len(before['state_invalid'])} 个")
    print(f"  本次已修复:     {len(state_fixed)} 个")
    print(f"  修复后仍无效:   {len(after['state_invalid'])} 个")
    if before['state_invalid']:
        rate = (len(before['state_invalid']) - len(after['state_invalid'])) / len(before['state_invalid']) * 100
        print(f"  修复率:         {rate:.1f}%  {'✓' if rate >= 99.99 else '×'}")
    else:
        print("  无需修复  ✓")

    print("\n【州间空隙】")
    print(f"  发现空洞:       {gap_info['holes_count']} 个")
    print(f"  本次已填补:     {gap_info['filled_count']} 个")
    if gap_info['states_modified']:
        print(f"  受影响州 ({len(gap_info['states_modified'])}):  "
              f"{', '.join(gap_info['states_modified'])}")
    print(f"  无法填补:       {len(unfilled_gaps)} 个")
    if gap_info['holes_count']:
        rate = gap_info['filled_count'] / gap_info['holes_count'] * 100
        print(f"  修复率:         {rate:.1f}%  {'✓' if rate >= 99.99 else '×'}")
    else:
        print("  无需修复  ✓")

    print("\n【郡边界有效性】")
    print(f"  修复前无效:     {len(before['county_invalid'])} 个")
    print(f"  本次已修复:     {len(county_fixed)} 个")
    print(f"  修复后仍无效:   {len(county_still_invalid)} 个")
    if before['county_invalid']:
        rate = (len(before['county_invalid']) - len(county_still_invalid)) / len(before['county_invalid']) * 100
        print(f"  修复率:         {rate:.1f}%  {'✓' if rate >= 99.99 else '×'}")
    else:
        print("  无需修复  ✓")

    print("\n【郡在州内】")
    print(f"  修复前在外:     {len(before['county_outside'])} 个"
          f" (另有 {before['county_outside_ignored']} 个小于阈值已忽略)")
    if before['county_outside']:
        for s, c, a in before['county_outside'][:5]:
            print(f"    · {c} ({s}): 面积 {a:.3e}")
        if len(before['county_outside']) > 5:
            print(f"    ... 还有 {len(before['county_outside']) - 5} 个")
    print(f"  本次已裁剪:     {len(county_clipped)} 个")
    print(f"  修复后仍在外:   {len(after['county_outside'])} 个"
          f" (另有 {after['county_outside_ignored']} 个小于阈值已忽略)")
    if after['county_outside']:
        for s, c, a in after['county_outside'][:10]:
            print(f"    × {c} ({s}): 面积 {a:.3e}")
    if before['county_outside']:
        rate = (len(before['county_outside']) - len(after['county_outside'])) / len(before['county_outside']) * 100
        print(f"  修复率:         {rate:.1f}%  {'✓' if rate >= 99.99 else '×'}")
    else:
        print("  无需修复  ✓")

    print("\n【县点归属清洗】")
    print(f"  需要移动:       {len(move_info)} 个县点")
    print(f"  扩展郡界:       {len(extended_counties)} 个郡")
    print(f"  更新州界:       {len(extended_states)} 个州")
    if move_info:
        for cid, info in list(move_info.items())[:10]:
            print(f"    · {info['city_name']}: "
                  f"{info['from_county']}({info['from_state']}) → "
                  f"{info['to_county']}({info['to_state']})")
    else:
        print("  无需移动  ✓")

    print("\n【郡内覆盖（县与县之间无空白）】")
    print(f"  修复前空隙:     {coverage_before} 个郡")
    if coverage_before:
        print(f"  空隙总面积:     {coverage_total_gap:.3e}")
    print(f"  修复后仍空隙:   {len(county_gaps)} 个郡"
          f" (另有 {county_gaps_ignored} 个小于阈值已忽略)")
    if county_gaps:
        print("  按面积从大到小：")
        for s, c, a in sorted(county_gaps, key=lambda x: -x[2])[:15]:
            print(f"    × {c} ({s}): 面积 {a:.3e}")
        if len(county_gaps) > 15:
            print(f"    ... 还有 {len(county_gaps) - 15} 个")
    if coverage_before:
        rate = (coverage_before - len(county_gaps)) / coverage_before * 100
        print(f"  修复率:         {rate:.1f}%  {'✓' if rate >= 99.99 else '×'}")
    else:
        print("  无需修复  ✓")

    print("\n【多块县明细（原始几何）】")
    print(f"  多块县:         {len(multi_block_info)} 个")
    if multi_block_info:
        for info in multi_block_info[:30]:
            top_areas = info["areas"][:3]
            area_str = ", ".join(f"{a:.3e}" for a in top_areas)
            if len(info["areas"]) > 3:
                area_str += f", ... 共{len(info['areas'])}块"
            print(f"    · {info['city']} ({info['county']}/{info['state']}): "
                  f"{info['n_blocks']} 块 [{area_str}]")
        if len(multi_block_info) > 30:
            print(f"    ... 还有 {len(multi_block_info) - 30} 个")
    else:
        print("  全部单块  ✓")

    print("\n【县点落在县界内】")
    print(f"  点在外:         {len(city_point_outside)} 个")
    if city_point_outside:
        for cn, ct in city_point_outside[:20]:
            print(f"    × {ct} ({cn})")
    else:
        print("  全部点均在边界内  ✓")

    print("\n【县级边界生成】")
    print(f"  县总数:         {total_cities} 个")
    print(f"  Voronoi 成功:   {city_ok} 个")
    print(f"  兜底生成:       {city_fallback} 个")
    print(f"  生成失败:       {city_fail} 个")
    if total_cities:
        rate = (city_ok + city_fallback) / total_cities * 100
        print(f"  成功率:         {rate:.1f}%  {'✓' if rate >= 99.99 else '×'}")

    print("\n【县在郡内】")
    print(f"  无边界:         {len(city_no_boundary)} 个")
    print(f"  部分在郡外:     {len(city_outside)} 个"
          f" (另有 {city_outside_ignored} 个小于阈值已忽略)")
    if city_no_boundary:
        for cn, ct in city_no_boundary[:10]:
            print(f"    × {ct} ({cn})")
    if city_outside:
        print("  按面积从大到小：")
        for cn, ct, a in sorted(city_outside, key=lambda x: -x[2])[:15]:
            print(f"    × {ct} ({cn}): 面积 {a:.3e}")
    if not city_no_boundary and not city_outside:
        print("  ✓ 全部县有边界且在郡内")

    print("\n" + "=" * 60)
    print("  完成。输出文件：map_with_boundaries.geojson")
    print("=" * 60)


if __name__ == "__main__":
    main()