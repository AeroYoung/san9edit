# -*- coding: utf-8 -*-
"""底部控制台（浮于地图之上，不占地图布局空间）。

从左到右：小地图区（由 `Minimap` 自己占位）→ 进行 / 暂停按钮 → 命令按钮组。
只读数据：不写 `BattleState` / `Unit` 的任何字段。
"""

import logging
import math

import pygame

from battle import config
from battle.render import widgets

logger = logging.getLogger("battle.render.console")

_PAD = 12
_GAP = 16


class Console:
    """底部控制台。"""

    def __init__(self, state, on_toggle_play=None):
        self.state = state
        self.on_toggle_play = on_toggle_play

        self._rect = pygame.Rect(0, 0, 0, 0)
        self._bg = None
        self._layout_key = None
        self._play_btn = None
        self._cmd_btns = []

    # ============================================================
    # 布局
    # ============================================================
    def layout(self, viewport_size, panel_width, minimap_width):
        """按视口、面板实际宽度、小地图实际宽度重算控制台与内部按钮。

        控制台高度取下限 `CONSOLE_HEIGHT` 与视口比例夹取的较大者，且不低于
        按钮组所需高度 —— 否则窗口一矮，按钮就会溢出底板。
        """
        vw, vh = viewport_size
        margin = config.CONSOLE_MARGIN

        # ---------------- 命令按钮组尺寸（先算，用来定控制台最小高度）----------------
        labels = config.CONSOLE_CMD_LABELS
        rows = max(1, int(config.CONSOLE_CMD_ROWS))
        per_row = int(math.ceil(len(labels) / float(rows))) if labels else 1
        cmd_w, cmd_h = config.CONSOLE_CMD_BTN_SIZE
        gap = config.CONSOLE_CMD_BTN_GAP
        play_w, play_h = config.CONSOLE_PLAY_BTN_SIZE

        block_h = rows * cmd_h + (rows - 1) * gap
        needed_h = max(play_h, block_h) + 2 * _PAD

        height = max(needed_h, min(config.CONSOLE_HEIGHT, int(vh * 0.15)))
        height = min(height, max(60, vh - 2 * margin))

        left = margin + int(minimap_width) + config.MINIMAP_MARGIN
        width = max(240, vw - left - margin - int(panel_width)
                    - config.PANEL_MARGIN)
        self._rect = pygame.Rect(left, vh - margin - height, width, height)

        inner = self._rect.inflate(-2 * _PAD, -2 * _PAD)

        # 视口极矮时的兜底：按内高等比收缩按钮，保证不溢出底板
        need = max(play_h, block_h)
        if need > inner.height > 0:
            shrink = inner.height / float(need)
            play_h = max(24, int(play_h * shrink))
            cmd_h = max(16, int(cmd_h * shrink))
            block_h = rows * cmd_h + (rows - 1) * gap

        # ---------------- 进行 / 暂停 ----------------
        self._play_btn = widgets.Button(
            (inner.left, inner.centery - play_h // 2, play_w, play_h),
            "进行", icon="play",
            bg_color=config.CONSOLE_PLAY_BG,
            hover_bg_color=config.CONSOLE_PLAY_HOVER_BG,
        )

        # ---------------- 命令按钮组 ----------------
        top = inner.centery - block_h // 2
        cmd_left = self._play_btn.rect.right + _GAP

        self._cmd_btns = []
        for index, label in enumerate(labels):
            row, col = divmod(index, per_row)
            rect = (cmd_left + col * (cmd_w + gap),
                    top + row * (cmd_h + gap), cmd_w, cmd_h)
            self._cmd_btns.append(
                widgets.Button(rect, label, enabled=False))

        self._layout_key = (tuple(viewport_size), int(panel_width),
                            int(minimap_width))
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

        if (event.type == pygame.MOUSEWHEEL
                and self.point_inside(pygame.mouse.get_pos())):
            return True   # 控制台内滚轮吞掉，不影响地图 zoom

        return False

    def _on_click(self, pos):
        for btn in self._cmd_btns:
            if btn.hit_test(pos):
                logger.debug("命令按钮「%s」本步未接命令系统（disabled）", btn.label)
                return True

        if self._play_btn.hit_test(pos):
            if self.on_toggle_play is not None:
                self.on_toggle_play()
            return True

        return True   # 控制台内其它点击一律吞掉

    # ============================================================
    # 绘制
    # ============================================================
    def draw(self, surface, viewport_size, is_playing, panel_width, minimap_width):
        key = (tuple(viewport_size), int(panel_width), int(minimap_width))
        if key != self._layout_key:
            self.layout(viewport_size, panel_width, minimap_width)

        surface.blit(self._bg, self._rect.topleft)

        self._play_btn.label = "暂停" if is_playing else "进行"
        self._play_btn.icon = "pause" if is_playing else "play"
        self._play_btn.bg_color = (config.CONSOLE_PAUSE_BG if is_playing
                                   else config.CONSOLE_PLAY_BG)
        self._play_btn.hover_bg_color = (config.CONSOLE_PAUSE_HOVER_BG if is_playing
                                         else config.CONSOLE_PLAY_HOVER_BG)

        mouse = pygame.mouse.get_pos()
        self._play_btn.draw(surface, mouse)
        for btn in self._cmd_btns:
            btn.draw(surface, mouse)
