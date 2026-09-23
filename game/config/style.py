# -*- coding: utf-8 -*-
"""主题配色、字体、地图绘制样式。

UI 部分改 THEME，地图部分改 MAP_STYLE，两不干扰。
"""

# ============================================================
# UI 主题
# ============================================================
THEME = {
    "info_bg":         "#2C3E50",   # 顶部信息栏底色
    "info_fg":         "#ECF0F1",
    "info_hover_bg":   "#3D566E",
    "info_sep":        "#4A6076",

    "status_bg":       "#E4E7EA",
    "status_fg":       "#333333",
    "status_sep":      "#B0B8C0",

    "panel_bg":        "#FAFBFC",
    "panel_header_bg": "#E8EDF2",
    "canvas_bg":       "#EEF2F7",

    "toolbar_bg":      "#F5F7FA",
}

# ============================================================
# 字体
# ============================================================
FONT_CANDIDATES = (
    "Microsoft YaHei", "SimHei", "PingFang SC", "Hiragino Sans GB",
    "WenQuanYi Micro Hei", "Noto Sans CJK SC", "Source Han Sans CN",
    "Droid Sans Fallback", "Arial Unicode MS",
)

# 各类 UI 元素的字号（相对基准字体大小的偏移量）
FONT_SIZES = {
    "info_bar":   10,
    "menu":       10,
    "status_bar": 9,
    "panel_title": 10,
    "panel_body": 9,
}

# ============================================================
# 地图绘制样式
# ============================================================
MAP_STYLE = {
    "polygon": {
        "fill":    "#DCD6C8",
        "outline": "#8B7355",
        "width":   1,
    },
    "line": {
        "color": "#8B7355",
        "width": 1,
    },
    "point": {
        "fill": "#3b2a1a",          # 原有填充色，保持不变
        "outline": "#f2e6cc",       # 新增：描边色（浅色，暗底上提亮轮廓）
        "outline_width": 0.6,       # 新增：描边宽（像素）
        "size_divisor": 1100,       # 新增：地图总像素宽 ÷ 此值 = 基准半径
        "min_radius": 0.9,          # 新增：半径下限（像素）
        "max_radius": 5.5,          # 新增：半径上限（像素）
        "shape_by_level": {         # 新增：level → 形状
            1: "circle",  2: "circle",  3: "circle",
            4: "diamond", 5: "diamond", 6: "diamond",
            7: "square",  8: "square",
            9: "triangle", 10: "triangle",
        },
        "radius_by_level": {        # 新增：level → 半径倍率
            1: 1.80, 2: 1.60, 3: 1.42, 4: 1.26, 5: 1.12,
            6: 1.00, 7: 0.90, 8: 0.80, 9: 0.70, 10: 0.62,
        },
    },
    "water_polygon": {
        "fill":    "#A9D2F0",   # 湖泊浅蓝
        "outline": "#5B9BD5",
        "width":   1,
    },
    "water_line": {
        "color": "#1E90FF",     # 河流蓝
        "width": 1,
    },
    "road": {
        "color": "#a8895f",          # 土黄/驼色，和州面、郡界拉开对比
        "width_divisor": 2600,        # 地图总像素宽 ÷ 此值 = 基准宽度
        "min_width": 0.2,            # 绝对下限（像素）
        "max_width": 2.0,            # 绝对上限（像素）
        "difficulty_floor": 1.0,     # difficulty 下限，防止极端值把线宽炸掉
    },

    # size_divisor 越小字越大。
    # min_scale / max_scale 是显示区间的上下界（像素/度）：
    #   低于 min_scale 或 达到 max_scale 都隐藏。
    # 放大到 max_scale 时隐藏州/郡名，让县名接管，避免字叠字。
    "label_state": {
        "color": "#1A1A1A", "halo": "#FFFFFF",
        "size_divisor": 55, "min_size": 11, "max_size": 44,
        "min_scale": 0, "max_scale": 40,
    },
    "label_county": {
        "color": "#333333", "halo": "#FFFFFF",
        "size_divisor": 105, "min_size": 9, "max_size": 22,
        "min_scale": 12, "max_scale": 150,
    },
    "label_city": {
        "color": "#7A3B00", "halo": "#FFFFFF",
        "size_divisor": 140, "min_size": 8, "max_size": 16,
        "min_scale": 30,
    },
}

# ============================================================
# 县名按 level 显隐
# ============================================================
# key 是县的 level（越小越重要），value 是显示该级县名所需的
# 最小缩放比例（像素/度）。初始视野 scale ≈ 27，数值越大越要放大才显示。
# 注意：无论 level 多少，县的「点位」始终绘制；这里只控制「名称」是否显示。
CITY_LEVEL_MIN_SCALE = {
    # 1: 0,
    # 2: 10,
    # 3: 25,
    # 4: 50,
    # 5: 150,
    # 6: 250,
    # 7: 350,
    # 8: 350,
    # 9: 350,
    # 10: 350,

    1: 0,
    2: 10,
    3: 25,
    4: 50,
    5: 150,
    6: 250,
    7: 350,
    8: 500,
    9: 600,
    10: 700,
}