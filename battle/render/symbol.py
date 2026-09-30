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

_TEXT_COLOR = (0, 0, 0)
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

def _ss_factor(size_px):
    """按格边长选超采样倍数。"""
    if size_px <= config.SYMBOL_SS_DOWNGRADE_PX:
        return int(config.SYMBOL_SUPERSAMPLE)
    return int(config.SYMBOL_SUPERSAMPLE_LARGE)

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



def _render_symbol(shape, fill_mode, side, size_px, line_w_screen=None):
    """把符号画成一块以中心为基准的小面。

    抗锯齿：先按 SS 倍尺寸绘制，再 `smoothscale` 缩回原尺寸（SS 见 `_ss_factor`）。
    超采样只在缓存未命中时发生 —— 缓存在调用方（`draw_symbol`）完成，
    命中后仍是单次 `blit`，每帧开销不变。

    返回 (surface, 符号中心在该面内的 x, y)。
    """
    color = config.SIDE_COLOR.get(side, (200, 200, 200))
    points = shape_points(shape, (0.0, 0.0), size_px)
    solids = fill_polygons(shape, points, fill_mode)

    line_w = (config.SYMBOL_LINE_WIDTH if line_w_screen is None
            else line_w_screen)
    pad = line_w + 2
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    left = int(math.floor(min(xs))) - pad
    top = int(math.floor(min(ys))) - pad
    width = max(1, int(math.ceil(max(xs))) + pad - left)
    height = max(1, int(math.ceil(max(ys))) + pad - top)

    ss = _ss_factor(size_px)
    if ss <= 1:
        layer = pygame.Surface((width, height), pygame.SRCALPHA)
        local_points = [(x - left, y - top) for x, y in points]
        local_solids = [[(x - left, y - top) for x, y in poly]
                        for poly in solids]
        _paint_symbol(layer, local_points, local_solids, color,
                      scale=1.0, line_w_screen=line_w,
                      shape=shape, fill_mode=fill_mode)
        return layer, -left, -top

    big = pygame.Surface((width * ss, height * ss), pygame.SRCALPHA)
    big_points = [((x - left) * ss, (y - top) * ss) for x, y in points]
    big_solids = [[((x - left) * ss, (y - top) * ss) for x, y in poly]
                  for poly in solids]
    _paint_symbol(big, big_points, big_solids, color,
                  scale=float(ss), line_w_screen=line_w,
                  shape=shape, fill_mode=fill_mode)
    small = pygame.transform.smoothscale(big, (width, height))
    return small, -left, -top

def _paint_symbol(surface, points, solids, color,
                  scale, line_w_screen, shape, fill_mode):
    """在（可能已放大 `scale` 倍的）面上画符号本体：填充 → 描边 → 内部线。

    `points` / `solids` 已是该面坐标系下的坐标；
    `line_w_screen` 是屏幕像素线宽，本函数按 `scale` 放大后落笔。
    """
    alpha_color = (color[0], color[1], color[2], config.SYMBOL_FILL_ALPHA)
    for poly in solids:
        pygame.draw.polygon(surface, alpha_color, poly)

    line_w = max(1, int(round(line_w_screen * scale)))
    pygame.draw.polygon(surface, color, points, line_w)
    _draw_extra_lines(surface, shape, points, fill_mode, color, line_w)

def render_thumbnail(type_def, side, size_px):
    """面板「符号」列用的缩略符号面（内容居中）。

    与地图符号**共用**同一套几何 / 填充 / 缓存实现（`_render_symbol`），
    缓存 key 加 `"panel"` 前缀与地图上的尺寸区分。地图符号绘制规则不受影响。

    ★ 保证返回的面是 (size_px, size_px) 的正方形，原符号按比例缩放至
    最长边不超过 size_px 后居中。不同形状（菱形 / 正方形 / 矩形）在面板中
    占据的尺寸完全一致，避免菱形因高度系数 1.4 而撑破行高。
    """
    shape = type_def.get("symbol_shape", SHAPE_SQUARE)
    fill_mode = type_def.get("symbol_fill", "hollow")
    size = int(round(size_px))
    key = ("panel_box", shape, fill_mode, side, size)

    cached = _SYMBOL_CACHE.get(key)
    if cached is not None:
        return cached

    # 1. 原尺寸下绘制符号（返回 Surface, ox, oy）
    src_layer, _ox, _oy = _render_symbol(
        shape, fill_mode, side, size,
        line_w_screen=config.PANEL_SYMBOL_LINE_WIDTH,
    )
    src_w, src_h = src_layer.get_size()

    # 2. 创建固定尺寸的正方形面
    box = pygame.Surface((size, size), pygame.SRCALPHA)

    # 3. 等比缩放：最长边不超过 size
    scale = min(1.0, float(size) / max(1, src_w), float(size) / max(1, src_h))
    if scale < 1.0:
        new_w = max(1, int(round(src_w * scale)))
        new_h = max(1, int(round(src_h * scale)))
        scaled = pygame.transform.smoothscale(src_layer, (new_w, new_h))
    else:
        scaled = src_layer

    # 4. 居中放置
    dst_w, dst_h = scaled.get_size()
    box.blit(scaled, ((size - dst_w) // 2, (size - dst_h) // 2))

    if len(_SYMBOL_CACHE) >= _SYMBOL_CACHE_LIMIT:
        _SYMBOL_CACHE.pop(next(iter(_SYMBOL_CACHE)))   # dict 保序 → FIFO
    _SYMBOL_CACHE[key] = box
    return box

# 符号小面缓存：key = (外形, 填充, 阵营, 取整格边长)，缩略图 key 前置 "panel"
_SYMBOL_CACHE = {}
_SYMBOL_CACHE_LIMIT = 128


def _draw_extra_lines(surface, shape, points, fill_mode, color, line_w):
    """步兵的 X 线，以及弓骑的中间斜线。线宽由调用方按超采样倍数放大后传入。"""
    if shape == SHAPE_RECT:
        pygame.draw.line(surface, color, points[0], points[2], line_w)
        pygame.draw.line(surface, color, points[1], points[3], line_w)
    elif fill_mode == "slash":
        p_top, p_right, p_bottom, p_left = points
        pygame.draw.line(surface, color,
                         _midpoint(p_left, p_bottom),
                         _midpoint(p_top, p_right),
                         line_w)


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
                      font, _TEXT_COLOR, anchor="midbottom",
                      outline=False, antialias=False)


def draw_troops(surface, center, text, shape, size_px, font_size):
    """兵力数字：框下方居中。"""
    if not text:
        return
    _, hh = extent(shape, size_px)
    font = widgets.get_font(font_size)
    widgets.draw_text(surface, text, (center[0], center[1] + hh + 2),
                      font, _TEXT_COLOR, anchor="midtop",
                      outline=False, antialias=False)


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


# 选中高亮环缓存：key = (外形, 取整格边长 × 1.12, 颜色, 线宽)
_HIGHLIGHT_CACHE = {}
_HIGHLIGHT_CACHE_LIMIT = 64


def draw_highlight(surface, center, shape, size_px, is_block=False):
    """选中高亮：沿符号最外层描一圈（远 LOD 时围住小色块）。

    高亮环单独走超采样 + 缓存；缓存在 `_highlight_layer` 里按
    （外形 / 尺寸 / 颜色 / 线宽）复用，命中后仍是单次 `blit`。
    """
    color = config.SELECT_HIGHLIGHT_COLOR
    width = config.SELECT_HIGHLIGHT_WIDTH
    if is_block:
        size = config.LOD_FAR_SIZE_PX + 2 * width
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(round(center[0])), int(round(center[1])))
        pygame.draw.rect(surface, color, rect, width)
        return

    layer, ox, oy = _highlight_layer(shape, size_px, color, width)
    surface.blit(layer, (int(round(center[0])) - ox,
                         int(round(center[1])) - oy))


def _highlight_layer(shape, size_px, color, width):
    """以 (0, 0) 为中心的高亮环小面（超采样 + FIFO 缓存）。"""
    scaled_size = size_px * 1.12
    key = (shape, int(round(scaled_size)), color, width)
    cached = _HIGHLIGHT_CACHE.get(key)
    if cached is not None:
        return cached

    pts = shape_points(shape, (0.0, 0.0), scaled_size)
    pad = width + 2
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    left = int(math.floor(min(xs))) - pad
    top = int(math.floor(min(ys))) - pad
    w = max(1, int(math.ceil(max(xs))) + pad - left)
    h = max(1, int(math.ceil(max(ys))) + pad - top)

    ss = _ss_factor(scaled_size)
    if ss <= 1:
        layer = pygame.Surface((w, h), pygame.SRCALPHA)
        local = [(x - left, y - top) for x, y in pts]
        pygame.draw.polygon(layer, color, local, width)
    else:
        big = pygame.Surface((w * ss, h * ss), pygame.SRCALPHA)
        big_pts = [((x - left) * ss, (y - top) * ss) for x, y in pts]
        pygame.draw.polygon(big, color, big_pts,
                            max(1, int(round(width * ss))))
        layer = pygame.transform.smoothscale(big, (w, h))

    result = (layer, -left, -top)
    if len(_HIGHLIGHT_CACHE) >= _HIGHLIGHT_CACHE_LIMIT:
        _HIGHLIGHT_CACHE.pop(next(iter(_HIGHLIGHT_CACHE)))
    _HIGHLIGHT_CACHE[key] = result
    return result