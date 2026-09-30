# -*- coding: utf-8 -*-
"""右侧面板组（浮于地图之上，不占地图布局空间）。

4 个 Tab：Tab1「部队」实装列表，Tab2–4 内容区显示「（本步未实现）」。
只读数据：不写 `BattleState` / `Unit` 的任何字段。
"""

import logging

import pygame

from battle import config
from battle.render import unit_layer
from battle.render import widgets

logger = logging.getLogger("battle.render.panel")

_ROW_HEIGHT = 24
_PAD = 12
_TAB_ACTIVE_BG = (56, 64, 80)
_TAB_BG = (38, 44, 56)
_ROW_ALT_BG = (36, 41, 51)
_ROW_HOVER_BG = (52, 60, 74)
_SCROLLBAR_WIDTH = 6
_SCROLLBAR_BG = (38, 44, 54)
_SCROLLBAR_FG = (108, 118, 138)


class Panel:
    """右侧面板组。"""

    def __init__(self, state, on_select_unit=None, player_side=None):
        self.state = state
        self.on_select_unit = on_select_unit
        self.player_side = player_side or config.PLAYER_SIDE

        self.active_tab = 0
        self.scroll = 0

        self._rect = pygame.Rect(0, 0, 0, 0)
        self._tab_rects = []
        self._content = pygame.Rect(0, 0, 0, 0)
        self._bg = None
        self._viewport_key = None

    # ============================================================
    # 布局
    # ============================================================
    def layout(self, viewport_size):
        """按视口重算面板矩形；屏幕过小时按比例收窄（不遮挡整屏）。"""
        vw, vh = viewport_size
        width = self._panel_width(vw)
        margin = config.PANEL_MARGIN
        height = max(120, vh - 2 * margin)
        self._rect = pygame.Rect(vw - margin - width, margin, width, height)

        tab_h = config.PANEL_TAB_HEIGHT
        tab_w = width // max(1, len(config.PANEL_TAB_TITLES))
        self._tab_rects = [
            pygame.Rect(self._rect.left + i * tab_w,
                        self._rect.top, tab_w, tab_h)
            for i in range(len(config.PANEL_TAB_TITLES))
        ]
        self._content = pygame.Rect(self._rect.left + _PAD,
                                    self._rect.top + tab_h + 4,
                                    width - 2 * _PAD,
                                    height - tab_h - 4 - _PAD)

        self._viewport_key = (vw, vh)
        self._bg = widgets.make_round_panel(self._rect.size)
        self._clamp_scroll()

    def _panel_width(self, viewport_w):
        """面板宽度：不超过屏宽的 40%，且不低于最小可读宽度。"""
        return max(160, min(config.PANEL_WIDTH, int(viewport_w * 0.4)))

    def rect(self):
        return self._rect

    def point_inside(self, pos):
        return self._rect.collidepoint(pos)

    # ============================================================
    # 事件
    # ============================================================
    def handle_event(self, event):
        """返回 True = 事件已被面板消费（不再交给地图）。"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.point_inside(event.pos):
                return False
            return self._on_click(event.pos)

        if event.type == pygame.MOUSEWHEEL:
            if not self.point_inside(pygame.mouse.get_pos()):
                return False
            if self.active_tab == 0:
                self.scroll -= event.y * _ROW_HEIGHT * 3
                self._clamp_scroll()
            return True   # 面板内滚轮一律吞掉，不影响地图 zoom

        return False

    def _on_click(self, pos):
        for index, rect in enumerate(self._tab_rects):
            if rect.collidepoint(pos):
                self.active_tab = index
                self.scroll = 0
                return True

        if self.active_tab == 0:
            row = self._row_index_at(pos)
            if row is not None and self.on_select_unit is not None:
                self.on_select_unit(self._rows()[row].id)
        return True

    def _rows(self):
        return self.state.all_units()

    def _row_index_at(self, pos):
        if not self._content.collidepoint(pos):
            return None
        offset = pos[1] - self._content.top + self.scroll
        index = int(offset // _ROW_HEIGHT)
        if 0 <= index < len(self._rows()):
            return index
        return None

    def _clamp_scroll(self):
        total = len(self._rows()) * _ROW_HEIGHT
        self.scroll = max(0, min(self.scroll, max(0, total - self._content.height)))

    # ============================================================
    # 绘制
    # ============================================================
    def draw(self, surface, viewport_size, selected):
        if tuple(viewport_size) != self._viewport_key:
            self.layout(viewport_size)
        surface.blit(self._bg, self._rect.topleft)
        self._draw_tabs(surface)
        if self.active_tab == 0:
            self._draw_unit_list(surface, selected)
        else:
            self._draw_empty(surface)

    def _draw_tabs(self, surface):
        font = widgets.get_font(13)
        for index, rect in enumerate(self._tab_rects):
            active = index == self.active_tab
            pygame.draw.rect(surface, _TAB_ACTIVE_BG if active else _TAB_BG, rect)
            if active:
                pygame.draw.line(surface, config.SELECT_HIGHLIGHT_COLOR,
                                 rect.bottomleft, rect.bottomright, 2)
            widgets.draw_text(surface, config.PANEL_TAB_TITLES[index],
                              rect.center, font,
                              widgets.TEXT_COLOR if active else widgets.TEXT_DIM,
                              anchor="center", outline=False)

    def _draw_empty(self, surface):
        font = widgets.get_font(13)
        widgets.draw_text(surface, "（本步未实现）", self._content.center,
                          font, widgets.TEXT_DIM, anchor="center", outline=False)

    def _draw_unit_list(self, surface, selected):
        rows = self._rows()
        font = widgets.get_font(11)
        mouse = pygame.mouse.get_pos()
        surface.set_clip(self._content)

        offset = -self.scroll
        for index, unit in enumerate(rows):
            top = self._content.top + offset + index * _ROW_HEIGHT
            rect = pygame.Rect(self._content.left, top,
                               self._content.width, _ROW_HEIGHT)
            if rect.bottom < self._content.top:
                continue
            if rect.top > self._content.bottom:
                break
            self._draw_row(surface, rect, unit, font, unit.id in selected,
                           rect.collidepoint(mouse) and self._content.collidepoint(mouse))

        surface.set_clip(None)
        self._draw_scrollbar(surface)

    def _draw_scrollbar(self, surface):
        """列表超出可视区时画滚动条（不超出则不画）。"""
        total = len(self._rows()) * _ROW_HEIGHT
        view = self._content.height
        if total <= view or view <= 0:
            return

        track = pygame.Rect(self._content.right - _SCROLLBAR_WIDTH,
                            self._content.top, _SCROLLBAR_WIDTH, view)
        pygame.draw.rect(surface, _SCROLLBAR_BG, track)

        thumb_h = max(24, int(view * view / total))
        max_scroll = total - view
        offset = 0 if max_scroll <= 0 else int((view - thumb_h) * (self.scroll / max_scroll))
        thumb = pygame.Rect(track.x, track.y + offset, track.width, thumb_h)
        pygame.draw.rect(surface, _SCROLLBAR_FG, thumb)

    def _draw_row(self, surface, rect, unit, font, is_selected, hovered):
        if hovered:
            pygame.draw.rect(surface, _ROW_HOVER_BG, rect)
        elif is_selected:
            pygame.draw.rect(surface, _ROW_ALT_BG, rect)

        left = rect.left
        # 选中标记
        widgets.draw_text(surface, "●" if is_selected else "○",
                          (left + 6, rect.centery), font,
                          config.SELECT_HIGHLIGHT_COLOR if is_selected
                          else widgets.TEXT_DIM,
                          anchor="midleft", outline=False)
        # 阵营：色点 + 文字
        dot = pygame.Rect(left + 24, rect.centery - 4, 8, 8)
        pygame.draw.rect(surface, config.SIDE_COLOR.get(unit.side, (200, 200, 200)), dot)
        side_text = "红" if unit.side == "red" else "蓝"
        widgets.draw_text(surface, side_text, (left + 36, rect.centery), font,
                          widgets.TEXT_COLOR, anchor="midleft", outline=False)
        # 兵种
        widgets.draw_text(surface, unit.name, (left + 62, rect.centery), font,
                          widgets.TEXT_COLOR, anchor="midleft", outline=False)
        # 兵力（右对齐到 200）
        widgets.draw_text(surface, unit_layer.format_troops(unit.troops),
                          (left + 200, rect.centery), font, widgets.TEXT_COLOR,
                          anchor="midright", outline=False)
        # 坐标
        col, row = unit.offset()
        widgets.draw_text(surface, "(%s, %s)" % (col, row),
                          (left + 206, rect.centery), font, widgets.TEXT_DIM,
                          anchor="midleft", outline=False)
