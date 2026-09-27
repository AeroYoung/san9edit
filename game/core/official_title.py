# -*- coding: utf-8 -*-
"""外官官名生成（纯函数，无 UI / 第三方依赖）。

行政区 id → 官名（需求 §3.2 / §3.3 / §3.4）：

    州（2 位）  司州 → 「司隶校尉」；其余 → {州名} + 牧 / 刺史（由外部常量表指定）
    郡（4 位）  以「尹」结尾    → 原样（河南尹 / 京兆尹）
                以「属国」结尾  → 原样 + 都尉（蜀郡属国 → 蜀郡属国都尉）
                以「国」结尾    → 前缀 ≥ 2 字：去「国」+ 相（中山国 → 中山相）
                                 前缀 = 1 字：保留「国」+ 相（赵国 → 赵国相）
                其余            → 去「郡」+ 太守（前缀 1 字时保留「郡」：
                                 东郡 → 东郡太守、蜀郡 → 蜀郡太守）
    县（6 位）  城 · level < 9   → 去「县」+ 令（阳翟 → 阳翟令）
                城 · level ≥ 9   → 去「县」+ 长（樊县 → 樊长）
                 ★ 去「县」只在**前缀 ≥ 2 字**时做（与郡 / 国同一条守卫）：
                   XX县 → XX + 令/长；X县 → X县 + 令/长（范县 → 范县长）。
                   这条守卫同时满足需求 §3.4 的示例（樊县 → 樊县长）。
                关隘 · level < 6 → 原样 + 都尉（玉门关 → 玉门关都尉）
                关隘 · level ≥ 6 → 原样 + 障尉（桥门 → 桥门障尉）
                渡口             → 末尾为「津」才去「津」，再 + 津长
                                  （瓜里津 → 瓜里津长、棘津城 → 棘津城津长）

★ level 方向：数字越小越重要（1 = 首都级，10 = 边远）。
★ 州牧 / 州刺史 不在本模块判定：调用方给 mu_states 常量表，运行时只按 name 后缀区分。
"""

SI_STATE_ID = "07"          # 司州
SI_TITLE = "司隶校尉"

RANK_STATE = "州"
RANK_COUNTY = "郡"
RANK_CITY = "县"

CITY_TYPE_CITY = "城"
CITY_TYPE_PASS = "关隘"
CITY_TYPE_FERRY = "渡口"

CITY_LEVEL_LING = 9         # 城：level ≥ 此值用「长」，否则「令」
PASS_LEVEL_DUWEI = 6        # 关隘：level ≥ 此值用「障尉」，否则「都尉」


def strip_suffix(text, suffix):
    """去掉结尾的 suffix；不以它结尾则原样返回。"""
    if text and text.endswith(suffix):
        return text[: -len(suffix)]
    return text


def state_title(state_id, state_name, mu_states=()):
    """州官名。司州 → 司隶校尉；其余 → {州名}牧 / {州名}刺史。

    mu_states：用「牧」的州 id 集合（其余一律「刺史」），由调用方的常量表给定。
    """
    if state_id == SI_STATE_ID:
        return SI_TITLE
    suffix = "牧" if state_id in set(mu_states) else "刺史"
    return f"{strip_suffix(state_name, '州')}州{suffix}"


def county_title(county_name):
    """郡官名（尹 / 属国都尉 / 相 / 太守）。"""
    if not county_name:
        return ""
    if county_name.endswith("尹"):
        return county_name                          # 河南尹 / 京兆尹
    if county_name.endswith("属国"):
        return county_name + "都尉"                 # 蜀郡属国 → 蜀郡属国都尉
    if county_name.endswith("国"):
        prefix = strip_suffix(county_name, "国")
        if len(prefix) >= 2:
            return prefix + "相"                    # 中山国 → 中山相
        return county_name + "相"                   # 赵国 → 赵国相
    prefix = strip_suffix(county_name, "郡")
    if len(prefix) >= 2:
        return prefix + "太守"                      # 颍川郡 → 颍川太守
    return county_name + "太守"                     # 东郡 → 东郡太守


def city_title(city_name, type_=CITY_TYPE_CITY, level=5):
    """县官名（令 / 长 / 都尉 / 障尉 / 津长）。"""
    if not city_name:
        return ""
    if type_ == CITY_TYPE_PASS:
        return city_name + ("障尉" if level >= PASS_LEVEL_DUWEI else "都尉")
    if type_ == CITY_TYPE_FERRY:
        return strip_suffix(city_name, "津") + "津长"
    base = strip_suffix(city_name, "县")
    if len(base) == 1:               # 「范县」→ 范县长（前缀 1 字时保留「县」）
        base = city_name
    return base + ("长" if level >= CITY_LEVEL_LING else "令")


def rank_of(region_id):
    """行政区 id → 等级：2 位 = 州 / 4 位 = 郡 / 6 位 = 县；其它 → None。"""
    return {"2": RANK_STATE, "4": RANK_COUNTY, "6": RANK_CITY}.get(
        str(len(region_id or "")))


def make_title(region_id, *, state_name=None, county_name=None, city_name=None,
               type_=CITY_TYPE_CITY, level=5, mu_states=()):
    """按 region_id 的位数分派到州 / 郡 / 县规则。参数缺失则该档返回空串。"""
    rank = rank_of(region_id)
    if rank == RANK_STATE:
        return state_title(str(region_id), state_name or "", mu_states)
    if rank == RANK_COUNTY:
        return county_title(county_name or "")
    if rank == RANK_CITY:
        return city_title(city_name or "", type_, level)
    return ""
