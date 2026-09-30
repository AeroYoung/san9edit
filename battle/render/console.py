# -*- coding: utf-8 -*-
"""底部控制台（浮于地图之上，不占地图布局空间）。

左起：进行/暂停按钮 · 选取展示区 · 部队按钮区（本步全 disabled）· 全选 / 清空选择。
只读数据：不写 `BattleState` / `Unit` 的任何字段。
"""

import logging

import pygame

from battle import config
from battle.render import unit_layer
from battle.render import widgets

logger = logging.getLogger("battle.render.console")

_PAD = 12
_GAP = 10
_BTN_H = 34
_PLAY_W = 90
_OTHER_W = 120
_UNIT_BTN_LABELS = ("移动", "攻击", "待命", "停止")
_MAX_SELECTED_TEXT = 6


class Console:
    """底部控制台。"""

    def __init__(self, state, on_toggle_play=None,
                 on_select_all=None, on_clear_selection=None):
        self.state = state
        self.on_toggle_play = on_toggle_play
        self.on_select_all = on_select_all
        self.on_clear_selection = on_clear_selection

        self._rect = pygame.Rect(0, 0, 0, 0)
        self._bg = None
        self._layout_key = None
        self._play_btn = None
        self._unit_btns = []
        self._select_all_btn = None
        self._clear_btn = None
        self._selection_rect = pygame.Rect(0, 0, 0, 0)

    # ============================================================
    # 布局
    # ============================================================
    def layout(self, viewport_size, panel_width):
        """按视口与面板实际宽度重算控制台矩形与内部按钮。"""
        vw, vh = viewport_size
        margin = config.CONSOLE_MARGIN
        height = max(80, min(config.CONSOLE_HEIGHT, int(vh * 0.15)))
        width = max(240, vw - 2 * margin - panel_width - config.PANEL_MARGIN)
        self._rect = pygame.Rect(margin, vh - margin - height, width, height)

        inner = self._rect.inflate(-2 * _PAD, -2 * _PAD)
        btn_y = inner.centery - _BTN_H // 2

        self._play_btn = widgets.Button(
            (inner.left, btn_y, _PLAY_W, _BTN_H), "进行",
            font_size=13, icon="play")

        right_x = inner.right - _OTHER_W
        other_w = (_OTHER_W - _GAP) // 2
        self._select_all_btn = widgets.Button(
            (right_x, btn_y, other_w, _BTN_H), "全选", font_size=12)
        self._clear_btn = widgets.Button(
            (right_x + other_w + _GAP, btn_y, other_w, _BTN_H), "清空选择",
            font_size=12)

        middle_left = self._play_btn.rect.right + _GAP
        middle_right = right_x - _GAP
        middle_w = max(80, middle_right - middle_left)
        sel_w = max(80, middle_w // 2 - _GAP)
        self._selection_rect = pygame.Rect(
            middle_left, inner.top, sel_w, inner.height)

        unit_left = self._selection_rect.right + _GAP
        unit_w = max(80, middle_right - unit_left)
        btn_w = min(72, max(40, (unit_w - 3 * 6) // 4))
        self._unit_btns = []
        for index, label in enumerate(_UNIT_BTN_LABELS):
            rect = (unit_left + index * (btn_w + 6), btn_y, btn_w, _BTN_H)
            self._unit_btns.append(
                widgets.Button(rect, label, enabled=False, font_size=12))

        self._layout_key = ((vw, vh), int(panel_width))
        self._bg = widgets.make_round_panel(self._rect.size)

    def rect(self):
        return self._rect

    def point_inside(self, pos):
        return self._rect.collidepoint(pos)

    # ============================================================
    # 事件
    # ============================================================
    def handle_event(self, event):
        """返回 True = 事件已被控制台消费。"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.point_inside(event.pos):
                return False
            return self._on_click(event.pos)

        if event.type == pygame.MOUSEWHEEL and self.point_inside(pygame.mouse.get_pos()):
            return True   # 控制台内滚轮吞掉，不影响地图 zoom

        return False

    def _on_click(self, pos):
        for btn in self._unit_btns:
            if btn.hit_test(pos):
                logger.debug("部队按钮「%s」本步未实现（disabled）", btn.label)
                return True

        if self._play_btn.hit_test(pos):
            if self.on_toggle_play is not None:
                self.on_toggle_play()
            return True
        if self._select_all_btn.hit_test(pos):
            if self.on_select_all is not None:
                self.on_select_all()
            return True
        if self._clear_btn.hit_test(pos):
            if self.on_clear_selection is not None:
                self.on_clear_selection()
            return True
        return True   # 控制台内其它点击一律吞掉

    # ============================================================
    # 绘制
    # ============================================================
    def draw(self, surface, viewport_size, selected_units, is_playing, panel_width):
        if (tuple(viewport_size), int(panel_width)) != self._layout_key:
            self.layout(viewport_size, panel_width)

        surface.blit(self._bg, self._rect.topleft)
        mouse = pygame.mouse.get_pos()

        self._play_btn.label = "暂停" if is_playing else "进行"
        self._play_btn.icon = "pause" if is_playing else "play"
        self._play_btn.draw(surface, mouse)
        for btn in self._unit_btns:
            btn.draw(surface, mouse)
        self._select_all_btn.draw(surface, mouse)
        self._clear_btn.draw(surface, mouse)

        self._draw_selection(surface, selected_units)

    def _draw_selection(self, surface, selected_units):
        font = widgets.get_font(11)
        title = widgets.get_font(12)

        widgets.draw_text(surface, "选取：%s 支" % len(selected_units),
                          (self._selection_rect.left, self._selection_rect.top),
                          title, widgets.TEXT_DIM, anchor="topleft", outline=False)

        if not selected_units:
            widgets.draw_text(surface, "（未选中任何部队）",
                              (self._selection_rect.left, self._selection_rect.top + 20),
                              font, widgets.TEXT_DIM, anchor="topleft", outline=False)
            return

        units = sorted(selected_units, key=lambda u: u.id)
        shown = units[:_MAX_SELECTED_TEXT]
        lines = ["%s %s %s" % (u.id, u.name,
                               unit_layer.format_troops(u.troops)) for u in shown]
        if len(units) > len(shown):
            lines.append("… 另有 %s 支" % (len(units) - len(shown)))

        y = self._selection_rect.top + 20
        for line in lines:
            if y + 14 > self._selection_rect.bottom:
                break
            widgets.draw_text(surface, line,
                              (self._selection_rect.left, y), font,
                              widgets.TEXT_COLOR, anchor="topleft", outline=False)
            y += 16
