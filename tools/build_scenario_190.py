# -*- coding: utf-8 -*-
"""从 characters.json + map.geojson，生成 190 年剧本 scenarios/default.json。

用法：
    python tools/build_scenario_190.py

地盘原则：
    - territories 里 4 位 = 整郡，6 位 = 单县
    - max_cities 限制该势力总县数（按 level 优先大城市）
    - 目标：全图约 700 县有主

人物原则：
    - CORE 手写每势力核心
    - 自动扩展：义兄弟 / 父母配偶 / liked 双向投票
    - affinity 兜底：剩余合格人物按相性最近分配（保证不在野）
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
SCEN = ROOT / "scenarios"
YEAR = 190


# ============================================================
# 52 家势力
#   颜色锁定：刘备绿 / 袁绍黄 / 曹操蓝 / 孙坚红
# ============================================================
FACTIONS = {
    # ---------------- 司州 ----------------
    "0736": {  # 董卓：河南尹 + 弘农 + 京兆尹 + 左冯翊 + 右扶风 + 河东，40 县
        "name": "董卓", "color": "#5B2B2B", "stance": -80,
        "capital": "070701",
        "territories": ["0701", "0702", "0703", "0704", "0705", "0707"],
        "max_cities": 40,
    },
    "0047": {  # 王匡：河内，14 县
        "name": "王匡", "color": "#7A6F50", "stance": -10,
        "capital": "070601", "territories": ["0706"],
        "max_cities": 14,
    },

    # ---------------- 凉州 ----------------
    "0771": {  # 马腾：汉阳 + 陇西，20 县
        "name": "马腾", "color": "#B87A40", "stance": -50,
        "capital": "050201", "territories": ["0502", "0503"],
        "max_cities": 20,
    },
    "0166": {  # 韩遂：金城，12 县
        "name": "韩遂", "color": "#8B5F3F", "stance": -50,
        "capital": "050415", "territories": ["0504"],
        "max_cities": 12,
    },
    "0592": {  # 段煨：张掖 + 酒泉，14 县
        "name": "段煨", "color": "#9B7F5F", "stance": -50,
        "capital": "050801", "territories": ["0508", "0510"],
        "max_cities": 14,
    },

    # ---------------- 并州 ----------------
    "0081": {  # 于夫罗：3 郡，20 县
        "name": "于夫罗", "color": "#9070A0", "stance":  0,
        "capital": "010801", "territories": ["0107", "0108", "0109"],
        "max_cities": 20,
    },
    "0661": {  # 张杨：上党，10 县
        "name": "张杨", "color": "#A08B5F", "stance": -10,
        "capital": "010101", "territories": ["0101"],
        "max_cities": 10,
    },
    "0169": {  # 韩暹（白波贼）：西河，6 县
        "name": "韩暹", "color": "#6B5F3F", "stance": -50,
        "capital": "010601", "territories": ["0106"],
        "max_cities": 6,
    },

    # ---------------- 幽州 ----------------
    "0932": {  # 刘虞：3 郡，18 县
        "name": "刘虞", "color": "#80B880", "stance":  0,
        "capital": "120401", "territories": ["1203", "1204", "1205"],
        "max_cities": 18,
    },
    "0266": {  # 公孙瓒：右北平 + 辽西，10 县
        "name": "公孙瓒", "color": "#C8C8C8", "stance": -50,
        "capital": "120601", "territories": ["1206", "1207"],
        "max_cities": 10,
    },
    "0268": {  # 公孙度：辽东 + 玄菟 + 乐浪，25 县
        "name": "公孙度", "color": "#6B8B8B", "stance":  30,
        "capital": "120901", "territories": ["1209", "1210", "1211"],
        "max_cities": 25,
    },

    # ---------------- 冀州 ----------------
    "0035": {  # 袁绍：渤海，9 县  ★ 黄
        "name": "袁绍", "color": "#E8C500", "stance":  30,
        "capital": "020801", "territories": ["0208"],
        "max_cities": 9,
    },
    "0182": {  # 韩馥：魏郡，12 县
        "name": "韩馥", "color": "#7A8B99", "stance": -10,
        "capital": "020101", "territories": ["0201"],
        "max_cities": 12,
    },
    "0601": {  # 张燕（黑山贼）：常山，8 县
        "name": "张燕", "color": "#9B5F8B", "stance": -10,
        "capital": "020301", "territories": ["0203"],
        "max_cities": 8,
    },
    "0018": {  # 于毒（黑山贼）：中山，5 县
        "name": "于毒", "color": "#704050", "stance": -10,
        "capital": "020401", "territories": ["0204"],
        "max_cities": 5,
    },
    "0470": {  # 眭固（黑山贼）：巨鹿，5 县
        "name": "眭固", "color": "#8B5F70", "stance": -10,
        "capital": "020501", "territories": ["0205"],
        "max_cities": 5,
    },

    # ---------------- 兖州 ----------------
    "0521": {  # 曹操：陈留东 8 县 + 梁国 6 县  ★ 蓝
        "name": "曹操", "color": "#2928EF", "stance":   0,
        "capital": "130301",
        "territories": ["130301", "130303", "130304", "130305",
                        "130307", "130308", "130309", "130312",
                        "1306"],
        "max_cities": 14,
    },
    "0653": {  # 张邈：陈留西 9 县
        "name": "张邈", "color": "#B8A080", "stance":   0,
        "capital": "130310",
        "territories": ["130310", "130311", "130314", "130315",
                        "130316", "130317", "130318", "130319", "130320"],
        "max_cities": 9,
    },
    "0209": {  # 桥瑁：东郡，10 县
        "name": "桥瑁", "color": "#A08B60", "stance": -10,
        "capital": "090201", "territories": ["0902"],
        "max_cities": 10,
    },
    "0947": {  # 刘岱：济阴，9 县
        "name": "刘岱", "color": "#8B7A5F", "stance": -10,
        "capital": "090301", "territories": ["0903"],
        "max_cities": 9,
    },
    "0024": {  # 袁遗：山阳，8 县
        "name": "袁遗", "color": "#D0B860", "stance":   0,
        "capital": "090401", "territories": ["0904"],
        "max_cities": 8,
    },
    "0826": {  # 鲍信：济北，6 县
        "name": "鲍信", "color": "#5F7AA0", "stance":   0,
        "capital": "090701", "territories": ["0907"],
        "max_cities": 6,
    },
    "0062": {  # 应劭：泰山，8 县
        "name": "应劭", "color": "#708B80", "stance":   0,
        "capital": "090801", "territories": ["0908"],
        "max_cities": 8,
    },

    # ---------------- 青州 ----------------
    "0952": {  # 刘备：平原一县  ★ 暗绿（刘关张）
        "name": "刘备", "color": "#3B8B3B", "stance":   0,
        "capital": "060101", "territories": ["060101"],
        "max_cities": 1,
    },
    "0280": {  # 孔融：北海，10 县
        "name": "孔融", "color": "#B0C0D0", "stance":  30,
        "capital": "060501", "territories": ["0605"],
        "max_cities": 10,
    },
    "0710": {  # 田楷：齐国，4 县
        "name": "田楷", "color": "#90A0C0", "stance": -10,
        "capital": "060301", "territories": ["0603"],
        "max_cities": 4,
    },
    "0165": {  # 管承（海贼）：东莱，6 县
        "name": "管承", "color": "#607090", "stance": -10,
        "capital": "060601", "territories": ["0606"],
        "max_cities": 6,
    },

    # ---------------- 徐州 ----------------
    "0724": {  # 陶谦：东海 + 下邳 + 彭城，22 县
        "name": "陶谦", "color": "#A05060", "stance": -50,
        "capital": "080401", "territories": ["0801", "0802", "0804"],
        "max_cities": 22,
    },
    "0647": {  # 张超：广陵，8 县
        "name": "张超", "color": "#C08080", "stance": -10,
        "capital": "080501", "territories": ["0805"],
        "max_cities": 8,
    },

    # ---------------- 豫州 ----------------
    "0270": {  # 孔伷：颍川 + 沛国，15 县
        "name": "孔伷", "color": "#6090B0", "stance": -10,
        "capital": "130101", "territories": ["1301", "1305"],
        "max_cities": 15,
    },
    "0090": {  # 何仪（汝南黄巾北）
        "name": "何仪", "color": "#905040", "stance": -10,
        "capital": "130401",
        "territories": ["130401", "130402", "130404", "130405", "130406",
                        "130407", "130408", "130409", "130410", "130411",
                        "130412", "130413", "130414", "130415", "130416",
                        "130417", "130420", "130425", "130426", "130427",
                        "130428", "130429"],
        "max_cities": 10,
    },
    "0958": {  # 刘辟（汝南黄巾南）
        "name": "刘辟", "color": "#806040", "stance": -10,
        "capital": "130421",
        "territories": ["130421", "130422", "130423", "130430",
                        "130431", "130432", "130434", "130435", "130436"],
        "max_cities": 7,
    },

    # ---------------- 扬州 ----------------
    "0963": {  # 刘繇：九江，10 县
        "name": "刘繇", "color": "#80A0B0", "stance": -50,
        "capital": "100604", "territories": ["1006"],
        "max_cities": 10,
    },
    "0933": {  # 刘勋：庐江，10 县
        "name": "刘勋", "color": "#7080A0", "stance": -50,
        "capital": "100701", "territories": ["1007"],
        "max_cities": 10,
    },
    "0080": {  # 王朗：会稽，8 县
        "name": "王朗", "color": "#90C0A0", "stance":   0,
        "capital": "100201", "territories": ["1002"],
        "max_cities": 8,
    },
    "0091": {  # 华歆：豫章，9 县
        "name": "华歆", "color": "#5F8B70", "stance":   0,
        "capital": "100101", "territories": ["1001"],
        "max_cities": 9,
    },
    "0239": {  # 严白虎：吴郡，8 县
        "name": "严白虎", "color": "#A0A050", "stance": -10,
        "capital": "100501", "territories": ["1005"],
        "max_cities": 8,
    },
    "0364": {  # 周昕：丹阳，9 县
        "name": "周昕", "color": "#6090A0", "stance": -10,
        "capital": "100401", "territories": ["1004"],
        "max_cities": 9,
    },

    # ---------------- 荆州 ----------------
    "0953": {  # 刘表：南郡 + 江夏治所，14 县
        "name": "刘表", "color": "#5090B0", "stance":   0,
        "capital": "040501", "territories": ["0405", "0406"],
        "max_cities": 14,
    },
    "0551": {  # 孙坚：长沙 + 桂阳治所，12 县  ★ 红
        "name": "孙坚", "color": "#C83030", "stance":   0,
        "capital": "040401", "territories": ["0401", "0404"],
        "max_cities": 12,
    },
    "0032": {  # 袁术：南阳，15 县
        "name": "袁术", "color": "#D0A040", "stance": -50,
        "capital": "040701", "territories": ["0407"],
        "max_cities": 15,
    },
    "0360": {  # 沙摩柯（五溪蛮）：武陵，6 县
        "name": "沙摩柯", "color": "#D08030", "stance": -10,
        "capital": "040301", "territories": ["0403"],
        "max_cities": 6,
    },
    "0642": {  # 张羡：零陵，7 县
        "name": "张羡", "color": "#A07060", "stance":   0,
        "capital": "040201", "territories": ["0402"],
        "max_cities": 7,
    },

    # ---------------- 益州 ----------------
    "0925": {  # 刘焉：蜀郡 + 广汉 + 犍为，16 县
        "name": "刘焉", "color": "#408070", "stance":   0,
        "capital": "110501", "territories": ["1104", "1105", "1106"],
        "max_cities": 16,
    },
    "0666": {  # 张鲁：汉中 + 武都，8 县
        "name": "张鲁", "color": "#C0A070", "stance":   0,
        "capital": "110104", "territories": ["0501", "1101"],
        "max_cities": 8,
    },
    "0310": {  # 吴懿（刘焉部）：巴郡，6 县
        "name": "吴懿", "color": "#50A090", "stance":   0,
        "capital": "110301", "territories": ["1103"],
        "max_cities": 6,
    },
    "0272": {  # 高定：越嶲，6 县
        "name": "高定", "color": "#C09060", "stance":   0,
        "capital": "110801", "territories": ["1108"],
        "max_cities": 6,
    },
    "0855": {  # 雍闿：益州郡，7 县
        "name": "雍闿", "color": "#B07040", "stance":   0,
        "capital": "111101", "territories": ["1111"],
        "max_cities": 7,
    },
    "0391": {  # 朱褒：牂牁，7 县
        "name": "朱褒", "color": "#A06070", "stance":   0,
        "capital": "110901", "territories": ["1109"],
        "max_cities": 7,
    },

    # ---------------- 交州 ----------------
    "0341": {  # 士燮：交趾 + 九真 + 日南，12 县
        "name": "士燮", "color": "#60A0A0", "stance":   0,
        "capital": "030601", "territories": ["0306", "0307", "0308"],
        "max_cities": 12,
    },
    "0332": {  # 士壹：合浦，4 县
        "name": "士壹", "color": "#709090", "stance":   0,
        "capital": "030401", "territories": ["0304"],
        "max_cities": 4,
    },
    "0334": {  # 士徽：南海，6 县
        "name": "士徽", "color": "#507070", "stance":   0,
        "capital": "030101", "territories": ["0301"],
        "max_cities": 6,
    },
}

# ============================================================
# 核心人物清单（CORE）
# ============================================================
CORE = {
    "0736": ["0736", "0907", "0987", "0144", "0893", "0097", "0782",
             "0638", "0199", "0301", "0428", "0254", "0663", "0193",
             "0507", "0258", "0908"],
    "0047": ["0047", "0818", "0835"],
    "0771": ["0771", "0759", "0867", "0758"],
    "0166": ["0166", "0475", "0474", "0074", "0969"],
    "0592": ["0592"],
    "0081": ["0081", "0954", "0306"],
    "0661": ["0661"],
    "0169": ["0169", "0894", "0880"],
    "0932": ["0932", "0927", "0490", "0031", "0712"],
    "0266": ["0266", "0269", "0261", "0267", "0233", "0473"],
    "0268": ["0268", "0264", "0263", "0265", "0788", "0990"],
    "0035": ["0035", "0186", "0812", "0618", "0281", "0713", "0535",
             "0464", "0822", "0105", "0217", "0395", "0184", "0466",
             "0037", "0034", "0029"],
    "0182": ["0182", "0277", "0797"],
    "0601": ["0601"],
    "0018": ["0018", "0754"],
    "0470": ["0470"],
    "0521": ["0521", "0124", "0114", "0518", "0511", "0514",
             "0102", "0913", "0709", "0393", "0402", "0689",
             "0192", "0016", "0842", "0844", "0735", "0848",
             "0460", "0253", "0516", "0515", "0526", "0510",
             "0999", "0392", "0333", "0615", "0911", "0673",
             "0424", "0672", "0505", "0122", "0123", "0115",
             "0500", "0502", "0509"],
    "0653": ["0653", "0512"],
    "0209": ["0209"],
    "0947": ["0947", "0067", "0884"],
    "0024": ["0024"],
    "0826": ["0826", "0829", "0824"],
    "0062": ["0062"],
    "0952": ["0952", "0147", "0656", "0185", "0552", "0793", "0795", "0792"],
    "0280": ["0280", "0594", "0063"],
    "0710": ["0710", "0493"],
    "0165": ["0165"],
    "0724": ["0724", "0749", "0527", "0751", "0785", "0747"],
    "0647": ["0647"],
    "0270": ["0270"],
    "0090": ["0090"],
    "0958": ["0958", "0208"],
    "0963": ["0963", "0598", "0783", "0019", "0586", "0330"],
    "0933": ["0933", "0962"],
    "0080": ["0080", "0225"],
    "0091": ["0091", "0335"],
    "0239": ["0239", "0240"],
    "0364": ["0364", "0365", "0367"],
    "0953": ["0953", "0325", "0084", "0085", "0807", "0167", "0951",
             "0321", "0319", "0324", "0595", "0642", "0585",
             "0260", "0158", "0223", "0654", "0949"],
    "0551": ["0551", "0557", "0176", "0247", "0703", "0538",
             "0567", "0572", "0988", "0412", "0974", "0973",
             "0574", "0289", "0443"],
    "0032": ["0032", "0219", "0206", "0614", "0861", "0226", "0036",
             "0400", "0670", "0098", "0917", "0970", "0919", "0218"],
    "0360": ["0360"],
    "0642": ["0642", "0644"],
    "0925": ["0925", "0938", "0961", "0823", "0928", "0719", "0637", "0744",
             "0632", "0827", "0849", "0950"],
    "0666": ["0666", "0597", "0862", "0869", "0038", "0868", "0876"],
    "0310": ["0310", "0241", "0315", "0886"],
    "0272": ["0272"],
    "0855": ["0855"],
    "0391": ["0391"],
    "0341": ["0341", "0337", "0336", "0340", "0354"],
    "0332": ["0332"],
    "0334": ["0334"],
}


# ============================================================
# 工具
# ============================================================
def build_city_level_index():
    """县 id → {county, level, is_capital}"""
    raw = json.loads((ASSETS / "map.geojson").read_text(encoding="utf-8"))
    idx = {}
    for state in raw.get("states", []):
        for county in state.get("counties", []):
            for city in county.get("cities", []):
                idx[city["id"]] = {
                    "county": county["id"],
                    "level": city.get("level", 5),
                    "is_capital": city.get("is_capital", False),
                }
    return idx


def build_county_index():
    raw = json.loads((ASSETS / "map.geojson").read_text(encoding="utf-8"))
    idx = {}
    for state in raw.get("states", []):
        for county in state.get("counties", []):
            idx[county["id"]] = [c["id"] for c in county.get("cities", [])]
    return idx


def expand_territory(code, county_to_cities):
    if len(code) == 4:
        return list(county_to_cities.get(code, []))
    if len(code) == 6:
        return [code]
    return []


def pick_cities(info, county_to_cities, city_info):
    """首都 + 按 level 优先取大城市，最多 max_cities 个。"""
    capital = info["capital"]
    max_cities = info.get("max_cities", 999)

    all_ids = set()
    for code in info["territories"]:
        for cid in expand_territory(code, county_to_cities):
            all_ids.add(cid)

    all_ids.discard(capital)
    picked = [capital]

    rest = sorted(all_ids,
                  key=lambda c: (city_info.get(c, {}).get("level", 5), c))
    for cid in rest:
        if len(picked) >= max_cities:
            break
        picked.append(cid)

    return picked


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


def expand_all(core_by_faction, all_chars, year):
    """CORE 起步 → 投票迭代扩展 → affinity 兜底。"""
    assigned = {
        fid: {cid for cid in ids if eligible(all_chars.get(cid), year)}
        for fid, ids in core_by_faction.items()
    }
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
    # 圆形距离：affinity 取值 0-149 是环，两个 affinity 的差 <= 75
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
    raw = json.loads((ASSETS / "characters.json").read_text(encoding="utf-8"))
    chars = raw["characters"]
    chars = {cid: c for cid, c in chars.items() if int(cid) <= 1000}
    county_to_cities = build_county_index()
    city_info = build_city_level_index()

    # 1. 分配人物
    assigned, leftover = expand_all(CORE, chars, YEAR)

    # 2. 据点
    nodes = {}
    for fid, info in FACTIONS.items():
        picked = pick_cities(info, county_to_cities, city_info)
        capital = info["capital"]
        for cid in picked:
            if cid == capital:
                nodes[cid] = {"owner": fid, "troops": 8000,
                              "gold": 1000, "food": 20000}
            else:
                nodes[cid] = {"owner": fid, "troops": 2000,
                              "gold": 200, "food": 3000}

    # 3. 人物覆盖
    characters = {}
    for fid in FACTIONS:
        if fid not in assigned:
            continue
        capital = FACTIONS[fid]["capital"]
        for cid in assigned[fid]:
            characters[cid] = {
                "faction":  fid,
                "node":     capital,
                "location": capital,
                "role":     "君主" if cid == fid else "一般",
            }

    # 4. 组装
    out = {
        "version": 2,
        "id": "default",
        "name": "十八路诸侯 · 190",
        "desc": "190年正月，关东诸侯起兵讨董；曹操据陈留，袁绍据渤海，刘关张在平原。",
        "start": {"year": 190, "month": 1, "xun": 1},
        "player_faction": "0521",
        "character_id_range": [1, 1000],   # ★ 新增：只加载编号 1-1000 的人
        "factions": {
            fid: {
                "name": i["name"],
                "color": i["color"],
                "prestige": 1000,
                "gold": 5000,
                "food": 20000,
                "stance": i["stance"],
            }
            for fid, i in FACTIONS.items()
        },
        "characters": characters,
        "nodes": nodes,
    }

    SCEN.mkdir(parents=True, exist_ok=True)
    out_path = SCEN / "default.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                        encoding="utf-8")

    total = sum(len(v) for v in assigned.values())
    print(f"[完成] 势力 {len(FACTIONS)} 家 / 人物 {total} 人 / 据点 {len(nodes)} 处")
    print(f"       affinity 兜底分配 {leftover} 人")
    print(f"       输出 → {out_path}")


if __name__ == "__main__":
    main()