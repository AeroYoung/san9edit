# -*- coding: utf-8 -*-
"""从 characters.json + map.geojson，生成 190 年剧本 scenarios/default.json。

用法：
    python tools/build_scenario_190.py

外官体系（需求 §3 / §7）：
    - 50 家势力：13 州级（州刺史 / 州牧 / 司隶校尉）+ 37 郡级（太守 / 相 / 令）
    - officials 段：以行政区 id（州 2 位 / 郡 4 位 / 县 6 位）为键，
      值为 {"name": 官名, "character_id": 人物 id, "rank": "州" / "郡" / "县"}
    - 官名规则见 game/core/official_title.py，本脚本只负责选人与校验

地盘原则（需求 §3.6）：
    - 郡级先占满本郡；县级占治所一县；州级再吃州内一个空郡（势力范围别铺太大）
    - 治所所在郡已被占 → 退到州内第一个空郡 → 再退到治所单县
    - 一县只能属于一个势力（Node.owner 单值）

人物原则：
    - CORE 只有各势力君主；其余靠义兄弟 / 父母配偶 / liked 投票扩展 + affinity 兜底
    - 全量人物写进剧本（1049 人），每条带 appeared（判定见 compute_appeared）
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SCEN = ROOT / "scenarios"
YEAR = 190


# ============================================================
# 50 家势力（需求 §7 定稿名单）
#   (君主名, 官职, 治所县 id, 等级, 颜色)
#   势力 id = 君主的人物 id，由 resolve_monarchs() 从 characters.json 反查
# ============================================================
MONARCHS = [
    # ---------------- 州级 13 ----------------
    ("董卓",     "司隶校尉", "070701", "州", "#5B2B2B"),
    ("韩馥",     "冀州牧",   "020101", "州", "#7A8B99"),
    ("刘岱",     "兖州刺史", "090201", "州", "#8B7A5F"),
    ("孔伷",     "豫州刺史", "130401", "州", "#6090B0"),
    ("陶谦",     "徐州牧",   "080401", "州", "#A05060"),
    ("焦和",     "青州刺史", "060301", "州", "#90A0C0"),
    ("刘表",     "荆州刺史", "040512", "州", "#5090B0"),
    ("陈温",     "扬州刺史", "100604", "州", "#7080A0"),
    ("刘焉",     "益州牧",   "110501", "州", "#408070"),
    ("韦端",     "凉州刺史", "050415", "州", "#8B6F4F"),
    ("丁原",     "并州刺史", "010201", "州", "#7A7A8A"),
    ("刘虞",     "幽州牧",   "120401", "州", "#80B880"),
    ("张津",     "交州刺史", "030101", "州", "#6B9070"),
    # ---------------- 郡级 37 ----------------
    ("袁绍",     "渤海太守", "020801", "郡", "#E8C500"),
    ("曹操",     "东郡太守", "090201", "郡", "#2928EF"),
    ("袁术",     "南阳太守", "040701", "郡", "#D0A040"),
    ("孙坚",     "长沙太守", "040401", "郡", "#C83030"),
    ("黄祖",     "江夏太守", "040601", "郡", "#4FA0C0"),
    ("刘备",     "平原令",   "060101", "县", "#3B8B3B"),
    ("公孙瓒",   "涿郡太守", "120304", "郡", "#C8C8C8"),
    ("公孙度",   "辽东太守", "120901", "郡", "#6B8B8B"),
    ("孔融",     "北海相",   "060501", "郡", "#B0C0D0"),
    ("张邈",     "陈留太守", "130301", "郡", "#B8A080"),
    ("张超",     "广陵太守", "080501", "郡", "#C08080"),
    ("鲍信",     "济北相",   "090701", "郡", "#5F7AA0"),
    ("王匡",     "河内太守", "070601", "郡", "#7A6F50"),
    ("袁遗",     "山阳太守", "090401", "郡", "#D0B860"),
    ("张鲁",     "汉中太守", "110104", "郡", "#C0A070"),
    ("刘繇",     "九江太守", "100601", "郡", "#80A0B0"),
    ("王朗",     "会稽太守", "100201", "郡", "#90C0A0"),
    ("华歆",     "豫章太守", "100101", "郡", "#5F8B70"),
    ("马腾",     "武威太守", "050701", "郡", "#B87A40"),
    ("张扬",     "上党太守", "010101", "郡", "#A08B5F"),
    ("张燕",     "常山相",   "020301", "郡", "#9B5F8B"),
    ("赵韪",     "巴郡太守", "110301", "郡", "#50A090"),
    ("张纯",     "渔阳太守", "120501", "郡", "#9B8B7B"),
    ("严白虎",   "吴郡太守", "100501", "郡", "#A0A050"),
    ("周昕",     "丹阳太守", "100401", "郡", "#6090A0"),
    ("笮融",     "下邳相",   "080101", "郡", "#B08A90"),
    ("耿鄙",     "汉阳太守", "050201", "郡", "#B08050"),
    ("士燮",     "交趾太守", "030601", "郡", "#60A0A0"),
    ("士壹",     "合浦太守", "030401", "郡", "#709090"),
    ("士武",     "九真太守", "030701", "郡", "#507880"),
    ("韩遂",     "金城太守", "050401", "郡", "#8B5F3F"),
    ("边章",     "陇西太守", "050301", "郡", "#9B7040"),
    ("北宫伯玉", "汉阳太守", "050201", "郡", "#8A5A4A"),
    ("张济",     "右扶风太守", "070101", "郡", "#A08A70"),
    ("李傕",     "冯翊太守", "070201", "郡", "#6A5A6A"),
    ("郭汜",     "河东太守", "070401", "郡", "#7A5A5A"),
    ("张羡",     "零陵太守", "040201", "郡", "#A07060"),
]

# §7 名单里 characters.json 没有的人物 → 近似替代（需求 §7 注：缺失则替代并记日志）
SUBSTITUTES = {
    "焦和":     "0710",   # 田楷（青州齐国相）
    "陈温":     "0211",   # 许贡（扬州吴郡豪族）
    "韦端":     "0867",   # 杨秋（凉州军阀）
    "张津":     "0285",   # 吴巨（交州苍梧）
    "张扬":     "0661",   # 张杨（§7「张扬」为异写）
    "赵韪":     "0241",   # 吴懿（益州巴郡）
    "耿鄙":     "0895",   # 李堪（凉州关中十部）
    "边章":     "0969",   # 梁兴（凉州关中十部）
    "北宫伯玉": "0474",   # 成宜（凉州关中十部）
}

# 不设势力的郡（夷洲 / 琉球孤悬海外，任何势力都不占）
NO_CLAIM_COUNTIES = {"1003"}

# 州牧 / 州刺史：用「牧」的州 id（其余一律「刺史」；司州固定「司隶校尉」）
MU_STATES = {"02", "08", "11", "12"}

# §7 定稿官名与规则生成不一致时的覆盖（郡名「左冯翊」按定稿记作「冯翊太守」）
TITLE_OVERRIDES = {"0702": "冯翊太守"}

# 地盘覆盖：显式指定郡（董卓据三辅）；限制县数（李傕 / 郭汜只保留治所，不占整郡）
TERRITORY_COUNTIES = {"董卓": ("0707", "0703", "0705")}
TERRITORY_MAX_CITIES = {"李傕": 1, "郭汜": 1}

# 4 位主角色锁定（README §4.5），不参与自动配色
LOCKED_COLORS = {"刘备": "#3B8B3B", "袁绍": "#E8C500",
                 "曹操": "#2928EF", "孙坚": "#C83030"}
CITY_ADJ_DEG = 0.8          # 两势力的县点近于此距离（度）视为相邻 → 配色互斥
MIN_HUE_GAP = 40            # 相邻势力色相差至少这么多度
MIN_VAL_GAP = 0.19          # 或者明度差至少这么多（深红 vs 亮红也算区分）


# ============================================================
# 地图索引
# ============================================================
def build_map_index():
    raw = json.loads((ASSETS / "map.geojson").read_text(encoding="utf-8"))
    idx = {
        "state_name": {},        # "07" -> 司州
        "county_name": {},       # "0707" -> 河南尹
        "county_to_cities": {},  # "0707" -> [县 id...]
        "city": {},              # "070701" -> {name, type, level, county}
    }
    for state in raw.get("states", []):
        idx["state_name"][state["id"]] = state.get("name", "")
        for county in state.get("counties", []):
            cid = county["id"]
            idx["county_name"][cid] = county.get("name", "")
            cities = [c["id"] for c in county.get("cities", [])]
            idx["county_to_cities"][cid] = cities
            for city in county.get("cities", []):
                coords = city.get("coords") or []
                idx["city"][city["id"]] = {
                    "county": cid,
                    "name": city.get("name", ""),
                    "type": city.get("type", "城"),
                    "level": city.get("level", 5),
                    "coords": tuple(coords[:2]) if len(coords) >= 2 else None,
                }
    return idx


def build_character_index():
    """名 -> 人物 id（重名取 id 最小的一个，并记入日志）。"""
    raw = json.loads((ASSETS / "characters.json").read_text(encoding="utf-8"))
    by_name = {}
    for cid, c in (raw.get("characters") or {}).items():
        by_name.setdefault(c["name"], []).append(cid)
    return by_name, raw["characters"]


# ============================================================
# 势力：选人 + 地盘
# ============================================================
def resolve_monarchs(by_name, all_chars):
    """MONARCHS 常量 → 带人物 id 的势力清单（缺失则用 SUBSTITUTES 替代）。"""
    factions = {}
    for name, title, capital, rank, color in MONARCHS:
        ids = by_name.get(name) or []
        if not ids and name in SUBSTITUTES:
            cid = SUBSTITUTES[name]
            print(f"[替代] {name}（{title}）不在人物表中 → 用 {all_chars[cid]['name']} {cid}")
            ids = [cid]
        if not ids:
            print(f"[跳过] {name}（{title}）与其替代者都不存在")
            continue
        if len(ids) > 1:
            print(f"[重名] {name} → {ids}，取 {ids[0]}")
        cid = sorted(ids)[0]
        # 用了替代者 → 势力名随真实君主，避免出现「势力名 ≠ 君主」的错位
        display = all_chars[cid]["name"] if name in SUBSTITUTES else name
        factions[cid] = {
            "id": cid,
            "name": display,
            "spec_name": name,
            "title": title,
            "capital": capital,
            "rank": rank,
            "color": color,
        }
    return factions


def pick_territory(spec, map_idx, owner):
    """按层级给一家势力选地盘（§3.6）。owner = 已被占的县 id 集合。"""
    cap = spec["capital"]
    county_id = map_idx["city"].get(cap, {}).get("county")
    state_id = cap[:2]

    def free(cities):
        return [c for c in cities if c not in owner]

    if county_id in NO_CLAIM_COUNTIES:
        return []                     # 所属郡不许占（如夷洲）

    def limited(cities):
        """县数上限（TERRITORY_MAX_CITIES）：治所优先，其余按 id 序。"""
        limit = TERRITORY_MAX_CITIES.get(spec["spec_name"])
        if not limit or len(cities) <= limit:
            return cities
        ordered = ([cap] if cap in cities else [])             + [c for c in cities if c != cap]
        return ordered[:limit]

    # 显式指定郡（如董卓据河南尹 + 京兆尹 + 弘农）
    counties = TERRITORY_COUNTIES.get(spec["spec_name"])
    if counties:
        cities = []
        for county in counties:
            if county in NO_CLAIM_COUNTIES:
                continue
            cities.extend(free(map_idx["county_to_cities"].get(county, [])))
        if cities:
            return limited(cities)

    # 县级（刘备）：治所一县 → 本郡空县
    if spec["rank"] == "县":
        if cap not in owner:
            return [cap]
        return limited(free(map_idx["county_to_cities"].get(county_id, [])))

    # 郡级 / 州级：本郡 → 州内空郡 → 治所单县
    cities = free(map_idx["county_to_cities"].get(county_id, []))
    if cities:
        return limited(cities)
    for county in sorted(map_idx["county_to_cities"]):
        if county[:2] != state_id or county in NO_CLAIM_COUNTIES:
            continue
        cities = free(map_idx["county_to_cities"][county])
        if cities:
            return limited(cities)
    return [cap] if cap not in owner else []


def assign_territories(factions, map_idx):
    """郡级 → 县级 → 州级 依次占地（一县只属一家）。"""
    owner = set()
    stages = ("郡", "县", "州")
    for stage in stages:
        for spec in sorted(factions.values(), key=lambda s: s["id"]):
            if spec["rank"] != stage:
                continue
            cities = pick_territory(spec, map_idx, owner)
            if not cities:
                print(f"[警告] {spec['name']}（{spec['title']}）没分到地盘")
            spec["cities"] = cities
            # 治所若在自己地盘内就用它，否则用地盘首县
            cap = spec["capital"]
            spec["effective_capital"] = cap if cap in cities else (cities[0] if cities else cap)
            owner.update(cities)
    return owner


# ============================================================
# 配色：按相邻关系贪心染色（需求 §7 相邻势力颜色要能区分）
# ============================================================
def _hsv_hex(hue, sat, val):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb((hue % 360) / 360.0, sat, val)
    return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def _hsv_of(hex_color):
    import colorsys
    r, g, b = (int(hex_color[i:i + 2], 16) / 255.0 for i in (1, 3, 5))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    return h * 360.0, s, v


def _hue_of(hex_color):
    return _hsv_of(hex_color)[0]


def _distinct(c1, c2):
    """两色是否够区分：色相差 ≥ MIN_HUE_GAP，或明度差 ≥ MIN_VAL_GAP。"""
    h1, _, v1 = _hsv_of(c1)
    h2, _, v2 = _hsv_of(c2)
    dh = abs(h1 - h2)
    dh = min(dh, 360 - dh)
    return dh >= MIN_HUE_GAP or abs(v1 - v2) >= MIN_VAL_GAP


def _palette():
    """色相网格（30° 一档）× 三档明度，档间错开 10°。"""
    cols = []
    for tier, val in enumerate((0.88, 0.68, 0.48)):
        sat = (0.80, 0.72, 0.85)[tier]
        for i in range(12):
            hue = (i * 30 + tier * 10) % 360
            cols.append(_hsv_hex(hue, sat, val))
    return cols


def assign_colors(factions, map_idx):
    """县点相近的势力视为相邻 → 贪心染色；同色不得出现在相邻势力，
    并在可行色里挑**当前用得最少**的，避免整张图挤在少数几个颜色上。
    4 位主角色保持锁定色。"""
    specs = sorted(factions.values(), key=lambda item: item["id"])

    # 1. 每家势力的县点坐标 + 包围盒（粗筛用）
    points, boxes = {}, {}
    for spec in specs:
        pts = [map_idx["city"][c]["coords"] for c in spec["cities"]
               if map_idx["city"].get(c, {}).get("coords")]
        points[spec["name"]] = pts
        boxes[spec["name"]] = ((min(p[0] for p in pts), max(p[0] for p in pts),
                                min(p[1] for p in pts), max(p[1] for p in pts))
                               if pts else None)

    def _near(a_name, b_name):
        """任一对县点距离 < CITY_ADJ_DEG 即视为相邻（先做包围盒粗筛）。"""
        a, b = boxes[a_name], boxes[b_name]
        if a is None or b is None:
            return False
        gap = max(a[0] - b[1], b[0] - a[1], a[2] - b[3], b[2] - a[3], 0)
        if gap >= CITY_ADJ_DEG:
            return False
        limit = CITY_ADJ_DEG ** 2
        return any((x[0] - y[0]) ** 2 + (x[1] - y[1]) ** 2 < limit
                   for x in points[a_name] for y in points[b_name])

    # 2. 邻接图
    neighbors = {spec["name"]: set() for spec in specs}
    for i, a in enumerate(specs):
        for b in specs[i + 1:]:
            if _near(a["name"], b["name"]):
                neighbors[a["name"]].add(b["name"])
                neighbors[b["name"]].add(a["name"])

    # 3. 贪心染色：度数大的先染；可行色里挑用得最少的
    palette = _palette()
    colors = dict(LOCKED_COLORS)
    usage = {}
    conflicts = 0
    for spec in sorted(specs, key=lambda item: -len(neighbors[item["name"]])):
        name = spec["name"]
        if name in colors:
            usage[colors[name]] = usage.get(colors[name], 0) + 1
            continue
        used = [colors[n] for n in neighbors[name] if n in colors]
        ok = [c for c in palette if all(_distinct(c, u) for u in used)]
        if not ok:
            conflicts += 1
            ok = palette
        pick = min(ok, key=lambda c: (usage.get(c, 0), palette.index(c)))
        colors[name] = pick
        usage[pick] = usage.get(pick, 0) + 1

    for spec in specs:
        spec["color"] = colors[spec["name"]]
    adj = sum(len(v) for v in neighbors.values()) // 2
    print(f"[配色] {len(specs)} 家 / 相邻关系 {adj} 对 / 用色 {len(usage)} 种"
          f" / 调色板 {len(palette)} 色 / 被迫复用 {conflicts} 家")


# ============================================================
# 官方官名（规则来自 core/official_title.py）
# ============================================================
def build_officials(factions, map_idx):
    """势力清单 → officials 段（以行政区 id 为键）。"""
    import sys
    sys.path.insert(0, str(ROOT))
    from game.core.official_title import make_title, rank_of

    officials = {}
    for spec in sorted(factions.values(), key=lambda s: s["id"]):
        cap = spec["capital"]
        region_id = {"州": cap[:2], "郡": cap[:4], "县": cap}[spec["rank"]]
        if region_id in officials:
            other = officials[region_id]
            print(f"[跳过] {spec['name']}（{spec['title']}）：行政区 {region_id} "
                  f"已有外官 {other['name']}（§3.1 一区一官）")
            continue
        city = map_idx["city"].get(cap, {})
        name = TITLE_OVERRIDES.get(region_id) or make_title(
            region_id,
            state_name=map_idx["state_name"].get(cap[:2], ""),
            county_name=map_idx["county_name"].get(cap[:4], ""),
            city_name=city.get("name", ""),
            type_=city.get("type", "城"),
            level=city.get("level", 5),
            mu_states=MU_STATES,
        )
        if name != spec["title"]:
            print(f"[定稿] {spec['name']} {region_id} 规则生成「{name}」"
                  f" → 按 §7 定稿记作「{spec['title']}」")
            name = spec["title"]
        officials[region_id] = {
            "name": name,
            "character_id": spec["id"],
            "rank": rank_of(region_id) or spec["rank"],
        }
    return officials


# ============================================================
# 人物分配（君主起步 → 投票扩展 → affinity 兜底）
# ============================================================
def eligible(ch, year):
    if ch is None:
        return False
    if ch["birth_year"]:
        if year - ch["birth_year"] < 16:
            return False
        if ch["death_year"] and year > ch["death_year"]:
            return False
    else:
        if ch["appear_year"] and ch["appear_year"] > year:
            return False
    return True


def compute_appeared(cid, ch, fid, year):
    """登场判定（生成期一次算死，写进剧本）。判定顺序即优先级：

        穿越人物（id >= 1001）     → False
        已被分配到势力              → True
        birth_year 缺失             → False
        year - birth_year >= 16     → True
        其余                        → False

    ★ death_year 不参与判定（历史人物长寿化 / 穿越设定）。
    """
    if int(cid) >= 1001:
        return False
    if fid:
        return True
    birth = ch.get("birth_year") or 0
    if not birth:
        return False
    return year - birth >= 16


def expand_all(core_by_faction, all_chars, year):
    """君主起步 → 网络投票迭代扩展 → affinity 兜底。"""
    assigned = {fid: {cid} for fid, cid in core_by_faction.items()
                if eligible(all_chars.get(cid), year)}
    owner = {}
    for fid, ids in assigned.items():
        for i in ids:
            owner[i] = fid

    # --- 阶段 1：网络投票扩展 ---
    changed = True
    while changed:
        changed = False
        for cid, ch in all_chars.items():
            if cid in owner or not eligible(ch, year):
                continue

            votes = {}
            for ref in (ch.get("sworn_brothers") or []):
                if ref in owner:
                    votes[owner[ref]] = votes.get(owner[ref], 0) + 10
            for rel in (ch.get("father"), ch.get("mother"), ch.get("spouse")):
                if rel and rel in owner:
                    votes[owner[rel]] = votes.get(owner[rel], 0) + 20
            for ref in (ch.get("liked") or []):
                if ref in owner:
                    votes[owner[ref]] = votes.get(owner[ref], 0) + 1
            for ref, rch in all_chars.items():
                if ref in owner and cid in (rch.get("liked") or []):
                    votes[owner[ref]] = votes.get(owner[ref], 0) + 1

            if not votes:
                continue
            best = max(votes, key=votes.get)
            assigned[best].add(cid)
            owner[cid] = best
            changed = True

    # --- 阶段 2：affinity 兜底 ---
    def circ_dist(a, b):
        d = abs(a - b) % 150
        return min(d, 150 - d)

    ruler_affinity = {}
    for fid in assigned:
        ruler = all_chars.get(fid)
        if ruler:
            ruler_affinity[fid] = ruler.get("affinity", 0)

    leftover = 0
    for cid, ch in all_chars.items():
        if cid in owner or not eligible(ch, year):
            continue
        if not ruler_affinity:
            continue
        my_aff = ch.get("affinity", 0)
        best_fid = min(ruler_affinity,
                       key=lambda f: circ_dist(my_aff, ruler_affinity[f]))
        assigned[best_fid].add(cid)
        owner[cid] = best_fid
        leftover += 1

    return assigned, leftover


# ============================================================
# 主流程
# ============================================================
def main():
    by_name, all_chars = build_character_index()
    map_idx = build_map_index()
    all_chars_sorted = dict(sorted(all_chars.items(), key=lambda kv: int(kv[0])))

    # 1. 势力 + 地盘
    factions = resolve_monarchs(by_name, all_chars)
    assign_territories(factions, map_idx)
    assign_colors(factions, map_idx)

    # 2. 人物分配（君主为种子）
    hist_chars = {cid: c for cid, c in all_chars.items() if int(cid) <= 1000}
    core = {fid: fid for fid in factions}
    assigned, leftover = expand_all(core, hist_chars, YEAR)

    # 3. 据点：势力地盘内的县
    nodes = {}
    for spec in factions.values():
        cap = spec["effective_capital"]
        for cid in spec["cities"]:
            if cid == cap:
                nodes[cid] = {"owner": spec["id"], "troops": 8000,
                              "gold": 1000, "food": 20000}
            else:
                nodes[cid] = {"owner": spec["id"], "troops": 2000,
                              "gold": 200, "food": 3000}

    # 4. 人物覆盖：全量写，每人 5 字段
    owner = {}
    capital_of = {}
    for spec in factions.values():
        for cid in assigned.get(spec["id"], ()):
            owner[cid] = spec["id"]
            capital_of[cid] = spec["effective_capital"]

    characters = {}
    for cid in all_chars_sorted:
        fid = owner.get(cid)
        capital = capital_of.get(cid) if fid else None
        characters[cid] = {
            "appeared": compute_appeared(cid, all_chars[cid], fid, YEAR),
            "faction":  fid,
            "node":     capital,
            "location": capital,
            "role":     ("君主" if cid == fid else "一般") if fid else None,
        }

    # 5. 外官
    officials = build_officials(factions, map_idx)

    # 6. 组装
    out = {
        "version": 2,
        "id": "default",
        "name": "州郡外官 · 190",
        "desc": "190年正月，关东诸侯起兵讨董；五十家州牧郡守各据一方。",
        "start": {"year": 190, "month": 1, "xun": 1},
        "player_faction": "0521",
        # ★ 不写 character_id_range：全量人物由 appeared 区分登场与否
        "factions": {
            spec["id"]: {
                "name": spec["name"],
                "color": spec["color"],
                "prestige": 1000,
                "stance": 0,
            }
            for spec in sorted(factions.values(), key=lambda s: s["id"])
        },
        "characters": characters,
        "nodes": nodes,
        "officials": officials,
    }

    SCEN.mkdir(parents=True, exist_ok=True)
    out_path = SCEN / "default.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    appeared_n = sum(1 for c in characters.values() if c["appeared"])
    by_rank = {}
    for item in officials.values():
        by_rank[item["rank"]] = by_rank.get(item["rank"], 0) + 1
    print(f"[完成] 势力 {len(factions)} 家 / 人物 {len(characters)} 人 / "
          f"登场 {appeared_n} 人 / 据点 {len(nodes)} 处")
    print(f"       外官 {len(officials)} 条（州 {by_rank.get('州', 0)} / "
          f"郡 {by_rank.get('郡', 0)} / 县 {by_rank.get('县', 0)}）")
    print(f"       affinity 兜底分配 {leftover} 人")
    print(f"       输出 → {out_path}")


if __name__ == "__main__":
    main()
