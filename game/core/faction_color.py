# -*- coding: utf-8 -*-
"""势力显示色（运行时派生，需求 §3.4）。

显示色是**派生值**：不写回 `Faction.color`（color 仍按落盘值保存，
附庸势力落盘的是它自己的默认色）。纯函数、不依赖 UI，
由 renderer / panel / dialog 共用。

规则：

| 对象 | 显示色 |
|---|---|
| 独立势力 | `Faction.color` |
| 董卓 | 固定 `DONGZHUO_COLOR`（覆盖其落盘 color 的显示） |
| 附庸势力 | 以宗主显示色为基色，按 vassal_value 混合附庸自身落盘色 |
| 同宗主多附庸 | 按附庸值降序分配色相偏移（首项 0°，其后 ±5°、±10°…） |

vassal_value 越大越接近宗主色（权重 = vassal_value / 100）。
"""

import colorsys

DONGZHUO_NAME = "董卓"          # 按势力名识别（势力 id 由剧本决定，不写死）
DONGZHUO_COLOR = "#5C4033"      # 深棕，董卓的固定显示色
DEFAULT_COLOR = "#888888"       # 势力缺失 / 无色时的兜底

HUE_STEP = 5.0                  # 同宗主相邻附庸的色相偏移步长（度）
MAX_HUE_SHIFT = 30.0            # 色相偏移上限，避免偏出可辨认范围


# ============================================================
# 对外入口
# ============================================================
def faction_display_color(faction, factions):
    """势力的显示色（hex 字符串）。

    faction  —— 目标 Faction（None → DEFAULT_COLOR）
    factions —— {id: Faction}，用于查宗主与同宗主附庸；缺省也能工作
    """
    return _resolve(faction, factions or {}, ())


def faction_display_color_by_id(faction_id, factions):
    """按势力 id 取显示色（据点面板 / 地图按 owner 上色时用）。"""
    if not faction_id or not factions:
        return DEFAULT_COLOR
    return _resolve(factions.get(faction_id), factions, ())


# ============================================================
# 内部
# ============================================================
def _resolve(faction, factions, seen):
    if faction is None:
        return DEFAULT_COLOR
    own = getattr(faction, "color", None) or DEFAULT_COLOR
    if getattr(faction, "name", None) == DONGZHUO_NAME:
        return DONGZHUO_COLOR                  # 董卓固定深棕，与是否独立无关
    if getattr(faction, "independent", True):
        return own
    overlord_id = getattr(faction, "overlord_id", None)
    # 宗主缺失 / 自指 / 成环 → 退回自身落盘色（加载期校验已保证正常情况下不会走到）
    if not overlord_id or overlord_id == faction.id or overlord_id in seen:
        return own
    overlord = factions.get(overlord_id)
    if overlord is None:
        return own
    base = _resolve(overlord, factions, seen + (faction.id,))
    value = _clamp_value(getattr(faction, "vassal_value", 0))
    mixed = _mix(own, base, value / 100.0)
    return _shift_hue(mixed, _hue_offset(faction, factions))


def _clamp_value(value):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, value))


def _hue_offset(faction, factions):
    """同宗主附庸按附庸值降序排位 → 首项 0°，其后 ±5°、±10°…

    偏移方向：奇数位 +，偶数位 −（1 → +5、2 → −5、3 → +10、4 → −10…）。
    """
    siblings = [f for f in factions.values()
                if not getattr(f, "independent", True)
                and getattr(f, "overlord_id", None) == faction.overlord_id]
    if not siblings:
        return 0.0
    siblings.sort(key=lambda f: (-_clamp_value(getattr(f, "vassal_value", 0)),
                                 getattr(f, "id", "")))
    index = next((i for i, f in enumerate(siblings)
                  if f.id == faction.id), 0)
    if index == 0:
        return 0.0
    steps = (index + 1) // 2
    sign = 1 if index % 2 == 1 else -1
    return sign * min(steps * HUE_STEP, MAX_HUE_SHIFT)


# ============================================================
# 颜色工具（hex ↔ hsv）
# ============================================================
def _to_rgb(hex_color):
    try:
        text = str(hex_color).strip().lstrip("#")
        if len(text) != 6:
            raise ValueError(text)
        r, g, b = (int(text[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except (TypeError, ValueError):
        r, g, b = (0.53, 0.53, 0.53)           # DEFAULT_COLOR
    return r, g, b


def _to_hex(r, g, b):
    return "#%02X%02X%02X" % (round(max(0.0, min(1.0, r)) * 255),
                              round(max(0.0, min(1.0, g)) * 255),
                              round(max(0.0, min(1.0, b)) * 255))


def _mix(color_a, color_b, weight):
    """按 weight 把 color_a 往 color_b 混（weight=0 → a，1 → b）。"""
    weight = max(0.0, min(1.0, weight))
    ar, ag, ab = _to_rgb(color_a)
    br, bg, bb = _to_rgb(color_b)
    return _to_hex(ar + (br - ar) * weight,
                   ag + (bg - ag) * weight,
                   ab + (bb - ab) * weight)


def _shift_hue(hex_color, degrees):
    """色相旋转（保持饱和度 / 明度）。degrees 为 0 时原样返回。"""
    if not degrees:
        return hex_color
    r, g, b = _to_rgb(hex_color)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    h = (h + degrees / 360.0) % 1.0
    return _to_hex(*colorsys.hsv_to_rgb(h, s, v))
