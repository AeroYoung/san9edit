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

    def __init__(self, state, on_toggle_play=None, on_step=None,
                 on_speed=None, on_move=None):
        self.state = state
        self.on_toggle_play = on_toggle_play
        self.on_step = on_step          # 单步
        self.on_speed = on_speed        # 速度档：on_speed(档位)
        self.on_move = on_move          # 「移动」按钮 → 进入目标格选择态

        self._rect = pygame.Rect(0, 0, 0, 0)
        self._bg = None
        self._layout_key = None
        self._play_btn = None
        self._step_btn = None
        self._speed_btns = []
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

        # ---------------- 视口极窄时的兜底：按内宽等比收缩按钮，不溢出底板 ----------------
        step_w, step_h = config.CONSOLE_STEP_BTN_SIZE
        speed_w, speed_h = config.CONSOLE_SPEED_BTN_SIZE
        speed_gap = config.CONSOLE_SPEED_BTN_GAP
        speed_count = len(config.CONSOLE_SPEED_LABELS)

        def _blocks(cw, spw, cgap, spgap):
            cmd_block = per_row * cw + (per_row - 1) * cgap
            speed_block = speed_count * spw + (speed_count - 1) * spgap
            return cmd_block, speed_block

        cmd_block_w, speed_block_w = _blocks(cmd_w, speed_w, gap, speed_gap)
        natural_w = (play_w + step_w + speed_block_w + cmd_block_w
                     + 3 * _GAP)
        if natural_w > inner.width > 0:
            k = inner.width / float(natural_w)
            play_w = max(56, int(play_w * k))
            step_w = max(38, int(step_w * k))
            speed_w = max(20, int(speed_w * k))
            cmd_w = max(32, int(cmd_w * k))
            group_gap = max(4, int(_GAP * k))
            gap = max(4, int(gap * k))
            speed_gap = max(3, int(speed_gap * k))
            cmd_block_w, speed_block_w = _blocks(cmd_w, speed_w, gap, speed_gap)
            block_h = rows * cmd_h + (rows - 1) * gap
        else:
            group_gap = _GAP

        # ---------------- 进行 / 暂停 ----------------
        self._play_btn = widgets.Button(
            (inner.left, inner.centery - play_h // 2, play_w, play_h),
            "进行", icon="play",
            bg_color=config.CONSOLE_PLAY_BG,
            hover_bg_color=config.CONSOLE_PLAY_HOVER_BG,
        )

        # ---------------- 单步 + 速度档 ----------------
        self._step_btn = widgets.Button(
            (self._play_btn.rect.right + group_gap,
             inner.centery - step_h // 2, step_w, step_h),
            "单步", font_size=config.FONT_SIZE_CONSOLE)

        speed_left = self._step_btn.rect.right + group_gap
        self._speed_btns = []
        for index, (speed, label) in enumerate(config.CONSOLE_SPEED_LABELS):
            rect = (speed_left + index * (speed_w + speed_gap),
                    inner.centery - speed_h // 2, speed_w, speed_h)
            self._speed_btns.append(
                (speed, widgets.Button(rect, label,
                                       font_size=config.FONT_SIZE_CONSOLE)))

        # ---------------- 命令按钮组 ----------------
        top = inner.centery - block_h // 2
        cmd_left = speed_left + speed_block_w + group_gap

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
                if btn.label == "移动" and self.on_move is not None:
                    self.on_move()
                else:
                    logger.debug("命令按钮「%s」本步未接命令系统（disabled）", btn.label)
                return True

        if self._play_btn.hit_test(pos):
            if self.on_toggle_play is not None:
                self.on_toggle_play()
            return True
        if self._step_btn.hit_test(pos):
            if self.on_step is not None:
                self.on_step()
            return True
        for speed, btn in self._speed_btns:
            if btn.hit_test(pos):
                if self.on_speed is not None:
                    self.on_speed(speed)
                return True

        return True   # 控制台内其它点击一律吞掉

    # ============================================================
    # 绘制
    # ============================================================
    def draw(self, surface, viewport_size, is_playing, panel_width, minimap_width,
             speed=None):
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

        # 视口极窄时按钮可能仍超出（收缩有下限）：裁到控制台矩形内，保证不涂到地图上
        previous_clip = surface.get_clip()
        surface.set_clip(self._rect)
        mouse = pygame.mouse.get_pos()
        self._play_btn.draw(surface, mouse)
        self._step_btn.draw(surface, mouse)
        for btn_speed, btn in self._speed_btns:
            btn.bg_color = (config.CONSOLE_SPEED_ACTIVE_BG if btn_speed == speed
                            else widgets.BUTTON_BG)
            btn.draw(surface, mouse)
        for btn in self._cmd_btns:
            btn.draw(surface, mouse)
        surface.set_clip(previous_clip)
