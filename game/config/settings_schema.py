# -*- coding: utf-8 -*-
"""设置项元数据：分组 + 条目。

纯数据模块，供设置窗口 UI 使用。与 style.py 的具体值解耦：
- GROUPS 描述“折叠分组”，每组的 restart 决定保存后是否提示“需重启”。
- ITEMS 描述“每个可编辑项”，path 用点号指向 style 结构中的位置。

type 取值：
    color / int / float / bool / choice / level_table

level_table 附加字段：
    value_type   每行控件的类型（int / float / choice）
    choices      value_type=choice 时的选项列表 [(值, 中文), ...]
    min/max/step value_type 为数值时的范围
    value_suffix 显示在输入框后的单位文字（可省）
"""

# ============================================================
# Tab（一级分区）
# ============================================================
TABS = [
    {"key": "appearance", "title": "外观"},
    {"key": "operation",  "title": "操作"},
    {"key": "game",       "title": "游戏"},
]

# ============================================================
# 分组
# ============================================================
GROUPS = [
    {"key": "theme", "tab": "appearance", "title": "界面主题",
     "desc": "顶部信息栏 / 状态栏 / 面板 / 画布底色。修改后需重启游戏生效。",
     "restart": True},
    {"key": "font", "tab": "appearance", "title": "字体与字号",
     "desc": "各 UI 元素的字号。修改后需重启游戏生效。",
     "restart": True},

    {"key": "polygon", "tab": "appearance", "title": "州面样式",
     "desc": "各州填充面与描边。"},
    {"key": "line", "tab": "appearance", "title": "郡界样式",
     "desc": "各郡分界线。"},
    {"key": "point", "tab": "appearance", "title": "县点样式",
     "desc": "各县治所小点的颜色、大小、描边与形状分级。"},
    {"key": "road", "tab": "appearance", "title": "道路样式",
     "desc": "道路线段的颜色与宽度。"},
    {"key": "water", "tab": "appearance", "title": "水域样式",
     "desc": "湖泊与河流的颜色（需 water.geojson 接入后生效）。"},

    {"key": "label_state", "tab": "appearance", "title": "州名标签",
     "desc": "州名文字的显隐区间与字号。"},
    {"key": "label_county", "tab": "appearance", "title": "郡名标签",
     "desc": "郡名文字的显隐区间与字号。"},
    {"key": "label_city", "tab": "appearance", "title": "县名标签",
     "desc": "县名文字的显隐区间与字号。县名与县点共用分级阈值。"},

    {"key": "lod", "tab": "appearance", "title": "分级显隐",
     "desc": "县点与县名按 level 决定显示所需的最小缩放。级别越小越重要，越早出现。"},
    {"key": "visibility", "tab": "appearance", "title": "图层显隐",
     "desc": "各图层总开关。关闭后该层完全不绘制。"},
]

# ============================================================
# 条目
# ============================================================
ITEMS = [
    # ---------------- 界面主题 ----------------
    {"path": "THEME.info_bg",       "group": "theme", "type": "color",
     "label": "信息栏底色",     "desc": "顶部信息栏与菜单栏的背景色。"},
    {"path": "THEME.info_fg",       "group": "theme", "type": "color",
     "label": "信息栏文字色",   "desc": "顶部信息栏中数字与文字的默认颜色。"},
    {"path": "THEME.info_hover_bg", "group": "theme", "type": "color",
     "label": "信息栏悬停底色", "desc": "鼠标移到信息格上时的高亮底色。"},
    {"path": "THEME.info_sep",      "group": "theme", "type": "color",
     "label": "信息栏分隔线色", "desc": "信息格之间的竖线颜色。"},

    {"path": "THEME.status_bg",     "group": "theme", "type": "color",
     "label": "状态栏底色"},
    {"path": "THEME.status_fg",     "group": "theme", "type": "color",
     "label": "状态栏文字色"},
    {"path": "THEME.status_sep",    "group": "theme", "type": "color",
     "label": "状态栏分隔线色"},

    {"path": "THEME.panel_bg",        "group": "theme", "type": "color",
     "label": "面板底色"},
    {"path": "THEME.panel_header_bg", "group": "theme", "type": "color",
     "label": "面板标题底色"},
    {"path": "THEME.canvas_bg",       "group": "theme", "type": "color",
     "label": "地图画布底色"},
    {"path": "THEME.toolbar_bg",      "group": "theme", "type": "color",
     "label": "工具条底色"},

    # ---------------- 字号 ----------------
    {"path": "FONT_SIZES.info_bar",    "group": "font", "type": "int",
     "label": "信息栏字号",   "min": 6, "max": 32},
    {"path": "FONT_SIZES.menu",        "group": "font", "type": "int",
     "label": "菜单字号",     "min": 6, "max": 32},
    {"path": "FONT_SIZES.status_bar",  "group": "font", "type": "int",
     "label": "状态栏字号",   "min": 6, "max": 32},
    {"path": "FONT_SIZES.panel_title", "group": "font", "type": "int",
     "label": "面板标题字号", "min": 6, "max": 32},
    {"path": "FONT_SIZES.panel_body",  "group": "font", "type": "int",
     "label": "面板正文字号", "min": 6, "max": 32},

    # ---------------- 州面 ----------------
    {"path": "MAP_STYLE.polygon.fill",    "group": "polygon", "type": "color",
     "label": "州面填充色"},
    {"path": "MAP_STYLE.polygon.outline", "group": "polygon", "type": "color",
     "label": "州面描边色"},
    {"path": "MAP_STYLE.polygon.width",   "group": "polygon", "type": "int",
     "label": "描边宽度（像素）", "min": 0, "max": 8},

    # ---------------- 郡界 ----------------
    {"path": "MAP_STYLE.line.color", "group": "line", "type": "color",
     "label": "郡界颜色"},
    {"path": "MAP_STYLE.line.width", "group": "line", "type": "int",
     "label": "线宽（像素）", "min": 0, "max": 8},

    # ---------------- 县点 ----------------
    {"path": "MAP_STYLE.point.fill",          "group": "point", "type": "color",
     "label": "县点填充色"},
    {"path": "MAP_STYLE.point.outline",       "group": "point", "type": "color",
     "label": "县点描边色"},
    {"path": "MAP_STYLE.point.outline_width", "group": "point", "type": "float",
     "label": "描边宽度（像素）", "min": 0.0, "max": 5.0, "step": 0.1},
    {"path": "MAP_STYLE.point.size_divisor",  "group": "point", "type": "int",
     "label": "半径分母", "min": 100, "max": 5000,
     "desc": "地图总像素宽 ÷ 此值 = 基准半径。数值越大，点越小。"},
    {"path": "MAP_STYLE.point.min_radius",    "group": "point", "type": "float",
     "label": "半径下限（像素）", "min": 0.1, "max": 20.0, "step": 0.1},
    {"path": "MAP_STYLE.point.max_radius",    "group": "point", "type": "float",
     "label": "半径上限（像素）", "min": 0.1, "max": 40.0, "step": 0.1},
    {"path": "MAP_STYLE.point.shape_by_level", "group": "point",
     "type": "level_table", "label": "各等级形状",
     "desc": "level → 形状。级别越小越重要。",
     "value_type": "choice",
     "choices": [("circle",   "圆形"),
                 ("diamond",  "菱形"),
                 ("square",   "方形"),
                 ("triangle", "三角")]},
    {"path": "MAP_STYLE.point.radius_by_level", "group": "point",
     "type": "level_table", "label": "各等级半径倍率",
     "desc": "level → 半径倍率。通常级别越小越大。",
     "value_type": "float", "min": 0.0, "max": 5.0, "step": 0.01},

    {"path": "MAP_STYLE.point.hollow_by_level", "group": "point",
     "type": "level_table", "label": "各等级空心",
     "desc": "level → 是否空心。空心点中心透明，只留描边。",
     "value_type": "bool"},

    # ---------------- 道路 ----------------
    {"path": "MAP_STYLE.road.color",            "group": "road", "type": "color",
     "label": "道路颜色"},
    {"path": "MAP_STYLE.road.width_divisor",    "group": "road", "type": "int",
     "label": "线宽分母", "min": 100, "max": 10000,
     "desc": "地图总像素宽 ÷ 此值 = 基准线宽。数值越大，线越细。"},
    {"path": "MAP_STYLE.road.min_width",        "group": "road", "type": "float",
     "label": "线宽下限（像素）", "min": 0.0, "max": 10.0, "step": 0.1},
    {"path": "MAP_STYLE.road.max_width",        "group": "road", "type": "float",
     "label": "线宽上限（像素）", "min": 0.0, "max": 20.0, "step": 0.1},
    {"path": "MAP_STYLE.road.difficulty_floor", "group": "road", "type": "float",
     "label": "difficulty 下限", "min": 0.1, "max": 10.0, "step": 0.1,
     "desc": "防止极端 difficulty 把线宽炸掉。"},

    # ---------------- 水域 ----------------
    {"path": "MAP_STYLE.water_polygon.fill",    "group": "water", "type": "color",
     "label": "湖泊填充色"},
    {"path": "MAP_STYLE.water_polygon.outline", "group": "water", "type": "color",
     "label": "湖泊描边色"},
    {"path": "MAP_STYLE.water_polygon.width",   "group": "water", "type": "int",
     "label": "湖泊描边宽", "min": 0, "max": 8},
    {"path": "MAP_STYLE.water_line.color",      "group": "water", "type": "color",
     "label": "河流颜色"},
    {"path": "MAP_STYLE.water_line.width",      "group": "water", "type": "int",
     "label": "河流线宽", "min": 0, "max": 8},

    # ---------------- 州名标签 ----------------
    {"path": "MAP_STYLE.label_state.color",        "group": "label_state", "type": "color",
     "label": "字色"},
    {"path": "MAP_STYLE.label_state.halo",         "group": "label_state", "type": "color",
     "label": "描边色"},
    {"path": "MAP_STYLE.label_state.size_divisor", "group": "label_state", "type": "int",
     "label": "字号分母", "min": 10, "max": 500,
     "desc": "数值越小，字越大。"},
    {"path": "MAP_STYLE.label_state.min_size",     "group": "label_state", "type": "int",
     "label": "字号下限", "min": 4, "max": 60},
    {"path": "MAP_STYLE.label_state.max_size",     "group": "label_state", "type": "int",
     "label": "字号上限", "min": 4, "max": 120},
    {"path": "MAP_STYLE.label_state.min_scale",    "group": "label_state", "type": "float",
     "label": "最小显示缩放", "min": 0.0, "max": 1000.0, "step": 1.0,
     "desc": "低于此缩放不显示。"},
    {"path": "MAP_STYLE.label_state.max_scale",    "group": "label_state", "type": "float",
     "label": "最大显示缩放", "min": 0.0, "max": 2000.0, "step": 1.0,
     "desc": "达到此缩放后隐藏，把空间让给县名。"},

    # ---------------- 郡名标签 ----------------
    {"path": "MAP_STYLE.label_county.color",        "group": "label_county", "type": "color",
     "label": "字色"},
    {"path": "MAP_STYLE.label_county.halo",         "group": "label_county", "type": "color",
     "label": "描边色"},
    {"path": "MAP_STYLE.label_county.size_divisor", "group": "label_county", "type": "int",
     "label": "字号分母", "min": 10, "max": 500},
    {"path": "MAP_STYLE.label_county.min_size",     "group": "label_county", "type": "int",
     "label": "字号下限", "min": 4, "max": 60},
    {"path": "MAP_STYLE.label_county.max_size",     "group": "label_county", "type": "int",
     "label": "字号上限", "min": 4, "max": 120},
    {"path": "MAP_STYLE.label_county.min_scale",    "group": "label_county", "type": "float",
     "label": "最小显示缩放", "min": 0.0, "max": 1000.0, "step": 1.0},
    {"path": "MAP_STYLE.label_county.max_scale",    "group": "label_county", "type": "float",
     "label": "最大显示缩放", "min": 0.0, "max": 2000.0, "step": 1.0},

    # ---------------- 县名标签 ----------------
    {"path": "MAP_STYLE.label_city.color",        "group": "label_city", "type": "color",
     "label": "字色"},
    {"path": "MAP_STYLE.label_city.halo",         "group": "label_city", "type": "color",
     "label": "描边色"},
    {"path": "MAP_STYLE.label_city.size_divisor", "group": "label_city", "type": "int",
     "label": "字号分母", "min": 10, "max": 500},
    {"path": "MAP_STYLE.label_city.min_size",     "group": "label_city", "type": "int",
     "label": "字号下限", "min": 4, "max": 60},
    {"path": "MAP_STYLE.label_city.max_size",     "group": "label_city", "type": "int",
     "label": "字号上限", "min": 4, "max": 120},
    {"path": "MAP_STYLE.label_city.min_scale",    "group": "label_city", "type": "float",
     "label": "最小显示缩放", "min": 0.0, "max": 1000.0, "step": 1.0},

    # ---------------- 分级显隐 ----------------
    {"path": "CITY_LEVEL_MIN_SCALE", "group": "lod",
     "type": "level_table", "label": "各级显隐阈值",
     "desc": "level → 显示该级县点与县名所需的最小缩放（像素/度）。"
             "同一 level 的点与名共用此阈值。级别越小越重要，越早出现。",
     "value_type": "int", "min": 0, "max": 5000, "step": 1,
     "value_suffix": " px/度"},

    # ---------------- 图层显隐 ----------------
    {"path": "LAYER_VISIBILITY.polygon",      "group": "visibility", "type": "bool",
     "label": "州面"},
    {"path": "LAYER_VISIBILITY.line",         "group": "visibility", "type": "bool",
     "label": "郡界"},
    {"path": "LAYER_VISIBILITY.point",        "group": "visibility", "type": "bool",
     "label": "县点"},
    {"path": "LAYER_VISIBILITY.road",         "group": "visibility", "type": "bool",
     "label": "道路"},
    {"path": "LAYER_VISIBILITY.water",        "group": "visibility", "type": "bool",
     "label": "水域（湖泊 / 河流）"},
    {"path": "LAYER_VISIBILITY.mountain",     "group": "visibility", "type": "bool",
     "label": "山地", "hidden": True},
    {"path": "LAYER_VISIBILITY.label_state",  "group": "visibility", "type": "bool",
     "label": "州名标签"},
    {"path": "LAYER_VISIBILITY.label_county", "group": "visibility", "type": "bool",
     "label": "郡名标签"},
    {"path": "LAYER_VISIBILITY.label_city",   "group": "visibility", "type": "bool",
     "label": "县名标签"},
]


# ============================================================
# 便捷查询
# ============================================================

def groups_of_tab(tab_key):
    return [g for g in GROUPS if g.get("tab") == tab_key]


def items_of_group(group_key):
    return [it for it in ITEMS if it["group"] == group_key]


def group_of(path):
    for it in ITEMS:
        if it["path"] == path:
            return it["group"]
    return None


def paths_of_group(group_key):
    return [it["path"] for it in items_of_group(group_key)]


def group_meta(group_key):
    for g in GROUPS:
        if g["key"] == group_key:
            return g
    return None