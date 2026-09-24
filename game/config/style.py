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
        "fill":    "",   
        "outline": "#000000",   
        "width":   2,
    },
    "line": {
        "color": "#000000",     
        "width": 1,
    },
    "city_line": {
        "color": "#000000",  
        "width": 1,
        "dash": (3, 5),      # 3 像素实线 + 3 像素间隔；调大 = 更稀疏
    },

    "road": {
        "color": "#B5442C",     # 暗砖红：道路明显偏暖偏红，一眼区分
        "width_divisor": 2600,
        "min_width": 0.2,
        "max_width": 2.0,
        "difficulty_floor": 1.0,
    },

    "point": {
        "fill": "#3b2a1a",          # 填充色
        "outline": "#f2e6cc",       # 描边色（浅色，暗底上提亮轮廓）
        "outline_width": 0.6,       # 描边宽（像素）
        
        "hollow_outline": "#000000",        # 新增：空心点的轮廓色
        "hollow_outline_width": 1.4,        # 新增：空心点的轮廓宽
        
        "size_divisor": 820,        # 地图总像素宽 ÷ 此值 = 基准半径
        "min_radius": 1.3,          # 半径下限（像素）
        "max_radius": 7.0,          # 半径上限（像素）
        "shape_by_level": {         # level → 形状
            1: "circle",  2: "circle",  3: "circle",
            4: "square",  5: "square",  6: "square",
            7: "diamond", 8: "diamond",
            9: "triangle", 10: "triangle",
        },
        "radius_by_level": {        # level → 半径倍率
            1: 2.00, 2: 1.80, 3: 1.60, 4: 1.42, 5: 1.26,
            6: 1.12, 7: 0.90, 8: 0.80, 9: 0.70, 10: 0.62,
        },
        "hollow_by_level": {        # True = 空心（只留描边，中心透出底图）
            1: False, 2: False,  3: False,
            4: False, 5: False, 6: False,
            7: False, 8: False,
            9: False, 10: False,
        },
        "ring_by_level": {          # True = 额外套一圈同心外环
            1: True, 2: True,  3: False,
            4: False, 5: False, 6: False,
            7: False, 8: False,
            9: False, 10: False,
        },
        "ring_scale": 1.3,         # 外环半径 = 点半径 × 此值
        "ring_width": 0.9,          # 外环线宽（像素）
        "ring_color": "#000000",    # 外环颜色（缺省跟 outline 一致）
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
    "territory": {              # ★ 势力染色
        "major_fade": 0.4,      # 主要势力（50%~80%）郡面的变浅比例。
                                # 0 = 原色，1 = 纯白。
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
        "font_family": "楷体",
        "size_divisor": 124, 
        "min_size": 8,
        "max_size": 19,
        "min_scale": 12, "max_scale": 150,
    },
    "label_city": {
        "color": "#000000", 
        "halo": "#FFFFFF",
        "size_divisor": 140, "min_size": 8, "max_size": 16,
        "min_scale": 30,
        "point_gap": 6,        # 新增：点边缘到文字中心之间的额外间隙（像素）
    },
}

# ============================================================
# 县名按 level 显隐
# ============================================================
# key 是县的 level（越小越重要），value 是显示该级县名所需的
# 最小缩放比例（像素/度）。初始视野 scale ≈ 27，数值越大越要放大才显示。
# 注意：无论 level 多少，县的「点位」始终绘制；这里只控制「名称」是否显示。
CITY_LEVEL_MIN_SCALE = {
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

# ============================================================
# 图层显隐总开关
# ============================================================
# True = 绘制该图层；False = 完全跳过。
# 修改后由设置窗口保存即可立即生效（无需重启）。
# 说明：water / mountain 对应的数据文件当前尚未接入渲染，
#       默认先置 False，等相应图层接入后会自动生效。
LAYER_VISIBILITY = {
    "polygon":      True,    # 州面
    "line":         True,    # 郡界
    "point":        True,    # 县点
    "road":         True,    # 道路
    "water":        False,   # 水域（湖泊 / 河流）
    "mountain":     False,   # 山地
    "label_state":  True,    # 州名标签
    "label_county": True,    # 郡名标签
    "label_city":   True,    # 县名标签
    "territory": True,      # ★ 郡面势力染色
    "city": True,
}