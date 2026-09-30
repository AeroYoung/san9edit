# -*- coding: utf-8 -*-
"""UI 通用小部件：字体 / 文字 / 圆角底板 / 按钮（三态）/ 半透明矩形 / 虚线框。

纯绘制，**不**读也不写任何战斗数据。
"""

import logging
from pathlib import Path

import pygame

from battle import config

logger = logging.getLogger("battle.render.widgets")

# 按钮配色（UI 细节，不进 config.py 的结构配置表）
BUTTON_BG = (52, 58, 70)
BUTTON_BG_HOVER = (76, 84, 100)
BUTTON_BG_DISABLED = (36, 40, 48)
BUTTON_BORDER = (90, 100, 120)
BUTTON_TEXT = (228, 232, 238)
BUTTON_TEXT_DISABLED = (118, 124, 134)
TEXT_COLOR = (228, 232, 238)
TEXT_DIM = (150, 156, 166)
TEXT_OUTLINE = (0, 0, 0)

_FONT_CACHE = {}
_font_fallback_logged = False
_CJK_SYS_FONTS = "microsoftyahei,simhei,simsun,notosanscjksc"


# ============================================================
# 字体
# ============================================================
def get_font(size):
    """按字号取字体（带缓存）。

    优先 `config.UI_FONT_PATH`；字体文件不存在时退回系统 CJK 字体
    （pygame 自带能力，不引入第三方依赖）；再失败用 pygame 默认字体。
    """
    size = int(size)
    font = _FONT_CACHE.get(size)
    if font is None:
        font = _load_font(size)
        _FONT_CACHE[size] = font
    return font


def _load_font(size):
    global _font_fallback_logged
    path = Path(str(config.UI_FONT_PATH))
    try:
        if path.exists():
            return pygame.font.Font(str(path), size)
    except Exception:
        logger.warning("字体文件加载失败：%s", path, exc_info=True)

    if not _font_fallback_logged:
        _font_fallback_logged = True
        logger.warning("字体文件不存在：%s，退回系统 CJK 字体", path)
    try:
        return pygame.font.SysFont(_CJK_SYS_FONTS, size)
    except Exception:
        logger.warning("系统字体不可用，退回 pygame 默认字体", exc_info=True)
        return pygame.font.Font(None, size)


# ============================================================
# 文字
# ============================================================
def draw_text(surface, text, pos, font, color=TEXT_COLOR,
              anchor="topleft", outline_color=TEXT_OUTLINE, outline=True,
              antialias=True):
    """画一行文字，可带 1px 描边（保证在任意地图底色上都可读）。

    返回文字矩形（屏幕坐标）。
    """
    img = font.render(text, antialias, color)
    rect = img.get_rect(**{anchor: pos})
    if outline and outline_color is not None:
        shadow = font.render(text, antialias, outline_color)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            surface.blit(shadow, rect.move(dx, dy))
    surface.blit(img, rect)
    return rect


# ============================================================
# 底板 / 填充
# ============================================================
def make_round_panel(size, bg_color=None, border_color=None, radius=None):
    """生成一块圆角半透明底板。调用方缓存它，避免每帧重建。"""
    bg_color = config.PANEL_BG_COLOR if bg_color is None else bg_color
    border_color = config.PANEL_BORDER_COLOR if border_color is None else border_color
    radius = config.PANEL_CORNER_RADIUS if radius is None else radius

    surf = pygame.Surface(size, pygame.SRCALPHA)
    rect = surf.get_rect()
    if bg_color is not None:
        pygame.draw.rect(surf, bg_color, rect, border_radius=radius)
    if border_color is not None and radius is not None:
        pygame.draw.rect(surf, border_color, rect, width=1, border_radius=radius)
    return surf


def draw_alpha_rect(surface, rect, rgba):
    """画一块半透明矩形（临时 surface，仅在需要时调用）。"""
    w, h = max(1, rect.width), max(1, rect.height)
    layer = pygame.Surface((w, h), pygame.SRCALPHA)
    layer.fill(rgba)
    surface.blit(layer, rect.topleft)


def draw_dashed_rect(surface, color, rect, dash=(6, 4), width=1):
    """画虚线矩形（四边各自分段；步长 = dash）。"""
    on, off = dash
    step = on + off

    for x in range(rect.left, rect.right, step):
        end = min(x + on, rect.right)
        pygame.draw.line(surface, color, (x, rect.top), (end, rect.top), width)
        pygame.draw.line(surface, color, (x, rect.bottom), (end, rect.bottom), width)
    for y in range(rect.top, rect.bottom, step):
        end = min(y + on, rect.bottom)
        pygame.draw.line(surface, color, (rect.left, y), (rect.left, end), width)
        pygame.draw.line(surface, color, (rect.right, y), (rect.right, end), width)


# ============================================================
# 按钮
# ============================================================
def draw_play_icon(surface, center, color):
    """「▶」三角：几何绘制，不依赖字体是否收录该码位。"""
    cx, cy = center
    points = [(cx - 5, cy - 6), (cx + 6, cy), (cx - 5, cy + 6)]
    pygame.draw.polygon(surface, color, points)


def draw_pause_icon(surface, center, color):
    """「⏸」双竖条：同样几何绘制。"""
    cx, cy = center
    pygame.draw.rect(surface, color, pygame.Rect(cx - 5, cy - 6, 4, 12))
    pygame.draw.rect(surface, color, pygame.Rect(cx + 2, cy - 6, 4, 12))


class Button:
    """三态按钮（normal / hover / disabled）。

    `enabled=False` 时**不**消费点击事件（点击交给上层写日志）。
    `icon` 取 `"play"` / `"pause"` / None —— 图标几何绘制在文字左侧。
    """

    def __init__(self, rect, label, enabled=True, font_size=None, icon=None,
                 bg_color=None, hover_bg_color=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.enabled = enabled
        # 字号一律从 config 取，不写字面量
        self.font_size = config.FONT_SIZE_CONSOLE if font_size is None else font_size
        self.icon = icon
        self.bg_color = BUTTON_BG if bg_color is None else bg_color
        self.hover_bg_color = (BUTTON_BG_HOVER if hover_bg_color is None
                               else hover_bg_color)
        self.hovered = False

    # ---------------- 事件 ----------------
    def hit_test(self, pos):
        return self.rect.collidepoint(pos)

    def handle_event(self, event):
        """返回 True = 本次事件已消费。"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.hit_test(event.pos)
        return False

    # ---------------- 绘制 ----------------
    def draw(self, surface, mouse_pos):
        self.hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        if not self.enabled:
            bg = BUTTON_BG_DISABLED
        elif self.hovered:
            bg = self.hover_bg_color
        else:
            bg = self.bg_color

        pygame.draw.rect(surface, bg, self.rect,
                         border_radius=config.PANEL_CORNER_RADIUS - 2)
        pygame.draw.rect(surface, BUTTON_BORDER, self.rect, width=1,
                         border_radius=config.PANEL_CORNER_RADIUS - 2)

        color = BUTTON_TEXT if self.enabled else BUTTON_TEXT_DISABLED
        font = get_font(self.font_size)
        img = font.render(self.label, True, color)

        icon_w = 12 if self.icon else 0
        gap = 6 if self.icon else 0
        total = icon_w + gap + img.get_width()
        x = self.rect.centerx - total // 2
        if self.icon == "play":
            draw_play_icon(surface, (x + 6, self.rect.centery), color)
        elif self.icon == "pause":
            draw_pause_icon(surface, (x + 6, self.rect.centery), color)
        surface.blit(img, (x + icon_w + gap,
                           self.rect.centery - img.get_height() // 2))
