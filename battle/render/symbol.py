# -*- coding: utf-8 -*-
"""兵棋符号绘制（纯几何，只读数据）。

外形按兵种类别：菱形（骑）/ 横长方形 + X（步）/ 正方形（弓）；
具体兵种靠**填充模式** + 框上方小字区分。规则见
`battle/docs/步骤02需求.md` §3.5。

所有尺寸都以「格边长」（`camera.zoom * HEX_SIZE`）为基准按比例给，
因此符号随 zoom 等比缩放，不「跳级」；描边线宽固定为屏幕像素。
"""

import math

import pygame

from battle import config
from battle.render import widgets

SHAPE_DIAMOND = "diamond"
SHAPE_RECT = "rect"
SHAPE_SQUARE = "square"

# 外形半宽 / 半高（× 格边长）
_EXTENT = {
    SHAPE_DIAMOND: (0.7, 0.7),
    SHAPE_RECT: (0.8, 0.4),
    SHAPE_SQUARE: (0.5, 0.5),
}

# 步兵横长方形被两条对角线切成的四个三角区（以矩形边命名）
_REGION_TOP = "top"
_REGION_RIGHT = "right"
_REGION_BOTTOM = "bottom"
_REGION_LEFT = "left"

# 填充模式 → 需要实心的区；`solid` / `top_half` / `upper_left_half` 另有分支
_REGION_FILLS = {
    "fill_three": (_REGION_RIGHT, _REGION_BOTTOM, _REGION_LEFT),
    "fill_left_right": (_REGION_RIGHT, _REGION_LEFT),
    "fill_bottom": (_REGION_BOTTOM,),
    "hollow": (),
}

_TEXT_COLOR = (230, 230, 230)
_BAR_BG = (60, 60, 60)
_MORALE_COLOR = (120, 200, 120)
_STAMINA_COLOR = (200, 170, 90)
_BAR_WIDTH = 4
_BAR_GAP = 3


# ============================================================
# 几何
# ============================================================
def extent(shape, size_px):
    """外形的 (半宽, 半高)。"""
    hw, hh = _EXTENT.get(shape, _EXTENT[SHAPE_SQUARE])
    return hw * size_px, hh * size_px


def shape_points(shape, center, size_px):
    """外形顶点（屏幕坐标）。

    返回顺序固定：
    - 菱形：上 / 右 / 下 / 左
    - 正方形与横长方形：左上 / 右上 / 右下 / 左下
    """
    cx, cy = center
    hw, hh = extent(shape, size_px)
    if shape == SHAPE_DIAMOND:
        return [(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)]
    return [(cx - hw, cy - hh), (cx + hw, cy - hh),
            (cx + hw, cy + hh), (cx - hw, cy + hh)]


def fill_polygons(shape, points, fill_mode):
    """该填充模式下需要实心的多边形列表（空列表 = 全空心）。"""
    if fill_mode == "solid":
        return [points]
    if fill_mode == "top_half":
        # 菱形沿水平中线切分，上半实心：上 / 右 / 左 三个顶点
        return [[points[0], points[1], points[3]]]
    if fill_mode == "upper_left_half":
        # 正方形沿「右上—左下」对角线切分，左上三角实心
        return [[points[0], points[1], points[3]]]
    if shape == SHAPE_RECT:
        tl, tr, br, bl = points
        cx = (tl[0] + br[0]) / 2.0
        cy = (tl[1] + br[1]) / 2.0
        center = (cx, cy)
        regions = {
            _REGION_TOP: [tl, tr, center],
            _REGION_RIGHT: [tr, br, center],
            _REGION_BOTTOM: [br, bl, center],
            _REGION_LEFT: [bl, tl, center],
        }
        return [regions[name] for name in _REGION_FILLS.get(fill_mode, ())]
    return []


def _midpoint(a, b):
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


# ============================================================
# 绘制：符号本体
# ============================================================
def draw_symbol(surface, center, type_def, side, size_px):
    """画符号本体（外形 + 填充 + 描边）；不含小字 / 数值 / 小条。

    同一（外形 / 填充 / 阵营 / 取整后的格边长）只在首次绘制时开 alpha 面，
    之后复用缓存 —— 平移时不再逐单位重建小面。缓存容量有上限，按 FIFO 淘汰。
    """
    key = (type_def.get("symbol_shape", SHAPE_SQUARE),
           type_def.get("symbol_fill", "hollow"),
           side, int(round(size_px)))
    cached = _SYMBOL_CACHE.get(key)
    if cached is None:
        cached = _render_symbol(*key)
        if len(_SYMBOL_CACHE) >= _SYMBOL_CACHE_LIMIT:
            _SYMBOL_CACHE.pop(next(iter(_SYMBOL_CACHE)))   # dict 保序 → FIFO
        _SYMBOL_CACHE[key] = cached

    layer, ox, oy = cached
    surface.blit(layer, (int(round(center[0])) - ox,
                         int(round(center[1])) - oy))


def _render_symbol(shape, fill_mode, side, size_px):
    """把符号画成一块以中心为基准的小面。

    返回 (surface, 符号中心在该面内的 x, y)。
    """
    color = config.SIDE_COLOR.get(side, (200, 200, 200))
    points = shape_points(shape, (0.0, 0.0), size_px)
    solids = fill_polygons(shape, points, fill_mode)

    pad = config.SYMBOL_LINE_WIDTH + 2
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    left = int(math.floor(min(xs))) - pad
    top = int(math.floor(min(ys))) - pad
    width = int(math.ceil(max(xs))) + pad - left
    height = int(math.ceil(max(ys))) + pad - top
    layer = pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)

    local_points = [(x - left, y - top) for x, y in points]
    alpha_color = (color[0], color[1], color[2], config.SYMBOL_FILL_ALPHA)
    for poly in solids:
        pygame.draw.polygon(layer, alpha_color,
                            [(x - left, y - top) for x, y in poly])

    pygame.draw.polygon(layer, color, local_points, config.SYMBOL_LINE_WIDTH)
    _draw_extra_lines(layer, shape, local_points, fill_mode, color)
    return layer, -left, -top


def render_thumbnail(type_def, side, size_px):
    """面板「符号」列用的缩略符号面（内容居中）。

    与地图符号**共用**同一套几何 / 填充 / 缓存实现（`_render_symbol`），
    缓存 key 加 `"panel"` 前缀与地图上的尺寸区分。地图符号绘制规则不受影响。
    """
    shape = type_def.get("symbol_shape", SHAPE_SQUARE)
    fill_mode = type_def.get("symbol_fill", "hollow")
    size = int(round(size_px))
    key = ("panel", shape, fill_mode, side, size)

    cached = _SYMBOL_CACHE.get(key)
    if cached is None:
        cached = _render_symbol(shape, fill_mode, side, size)
        if len(_SYMBOL_CACHE) >= _SYMBOL_CACHE_LIMIT:
            _SYMBOL_CACHE.pop(next(iter(_SYMBOL_CACHE)))
        _SYMBOL_CACHE[key] = cached
    return cached[0]


# 符号小面缓存：key = (外形, 填充, 阵营, 取整格边长)，缩略图 key 前置 "panel"
_SYMBOL_CACHE = {}
_SYMBOL_CACHE_LIMIT = 128


def _draw_extra_lines(layer, shape, points, fill_mode, color):
    """步兵的 X 线，以及弓骑的中间斜线。"""
    if shape == SHAPE_RECT:
        pygame.draw.line(layer, color, points[0], points[2], config.SYMBOL_LINE_WIDTH)
        pygame.draw.line(layer, color, points[1], points[3], config.SYMBOL_LINE_WIDTH)
    elif fill_mode == "slash":
        # 菱形内的一条「/」斜线：从左下边中点穿过中心到右上边中点
        p_top, p_right, p_bottom, p_left = points
        pygame.draw.line(layer, color,
                         _midpoint(p_left, p_bottom),
                         _midpoint(p_top, p_right),
                         config.SYMBOL_LINE_WIDTH)


# ============================================================
# 绘制：附加信息
# ============================================================
def draw_label(surface, center, text, shape, size_px, font_size):
    """兵种小字：框上方居中。"""
    if not text:
        return
    _, hh = extent(shape, size_px)
    font = widgets.get_font(font_size)
    widgets.draw_text(surface, text, (center[0], center[1] - hh - 2),
                      font, _TEXT_COLOR, anchor="midbottom")


def draw_troops(surface, center, text, shape, size_px, font_size):
    """兵力数字：框下方居中。"""
    if not text:
        return
    _, hh = extent(shape, size_px)
    font = widgets.get_font(font_size)
    widgets.draw_text(surface, text, (center[0], center[1] + hh + 2),
                      font, _TEXT_COLOR, anchor="midtop")


def draw_bars(surface, center, morale, stamina, shape, size_px):
    """士气（左）/ 体力（右）竖条：0–100 映射到条高。"""
    hw, hh = extent(shape, size_px)
    bar_h = max(10, int(round(hh * 2)))
    top = center[1] - bar_h / 2.0

    for x, value, color in (
        (center[0] - hw - _BAR_GAP - _BAR_WIDTH, morale, _MORALE_COLOR),
        (center[0] + hw + _BAR_GAP, stamina, _STAMINA_COLOR),
    ):
        rect = pygame.Rect(int(round(x)), int(round(top)), _BAR_WIDTH, bar_h)
        pygame.draw.rect(surface, _BAR_BG, rect)
        ratio = max(0.0, min(1.0, float(value) / 100.0))
        if ratio > 0:
            fill_h = max(1, int(round(bar_h * ratio)))
            fill = pygame.Rect(rect.x, rect.bottom - fill_h, _BAR_WIDTH, fill_h)
            pygame.draw.rect(surface, color, fill)


def draw_far_block(surface, center, side, size_px=None):
    """远 LOD：小色块（不画外形 / 小字 / 数值 / 小条）。"""
    size = config.LOD_FAR_SIZE_PX if size_px is None else int(size_px)
    color = config.LOD_FAR_COLOR.get(side, (200, 200, 200))
    rect = pygame.Rect(0, 0, size, size)
    rect.center = (int(round(center[0])), int(round(center[1])))
    pygame.draw.rect(surface, color, rect)


def draw_highlight(surface, center, shape, size_px, is_block=False):
    """选中高亮：沿符号最外层描一圈（远 LOD 时围住小色块）。"""
    color = config.SELECT_HIGHLIGHT_COLOR
    width = config.SELECT_HIGHLIGHT_WIDTH
    if is_block:
        size = config.LOD_FAR_SIZE_PX + 2 * width
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(round(center[0])), int(round(center[1])))
        pygame.draw.rect(surface, color, rect, width)
        return
    points = shape_points(shape, center, size_px * 1.12)
    pygame.draw.polygon(surface, color, points, width)
