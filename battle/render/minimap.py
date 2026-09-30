# -*- coding: utf-8 -*-
"""小地图：地图全貌 + 当前视口框 + 双方部队点 + 单击 / 拖动定位。

渲染层**只读数据**：不写 `BattleState` / `Unit` 的任何字段。
相机中心只通过 `Camera.center_on_world()` 写入，不碰 `cx` / `cy`。
"""

import logging

import pygame

from battle import config
from battle.core import hexgrid
from battle.render import widgets

logger = logging.getLogger("battle.render.minimap")


class Minimap:
    """左下角小地图，与大地图共用**同一个** `Camera`。"""

    def __init__(self, state, map_data):
        self.state = state
        self.cols = int(map_data.cols)
        self.rows = int(map_data.rows)
        self.hex_size = float(map_data.hex_size)
        self.world_width, self.world_height = hexgrid.world_bounds(
            self.cols, self.rows, self.hex_size)

        self._rect = pygame.Rect(0, 0, 0, 0)
        self._map_rect = pygame.Rect(0, 0, 0, 0)
        self._bg = None
        self._layout_key = None
        self._dragging = False

    # ============================================================
    # 布局
    # ============================================================
    def layout(self, viewport_size, panel_width=None):
        """按视口重算小地图矩形。

        `panel_width` 只为与 app 的装配顺序保持同一调用签名；小地图贴左，
        不受面板宽度影响。
        """
        vw, vh = viewport_size
        height = min(config.MINIMAP_HEIGHT,
                     max(60, vh - 2 * config.CONSOLE_MARGIN))
        width = max(40, int(round(height * self.cols / float(self.rows))))
        self._rect = pygame.Rect(config.CONSOLE_MARGIN,
                                 vh - config.CONSOLE_MARGIN - height,
                                 width, height)

        # 地图范围等比缩放居中（宽被夹到 40px 时留白）
        pad = config.MINIMAP_PAD
        inner = self._rect.inflate(-2 * pad, -2 * pad)
        scale = min(inner.width / self.world_width,
                    inner.height / self.world_height)
        map_w = max(1, int(round(self.world_width * scale)))
        map_h = max(1, int(round(self.world_height * scale)))
        self._map_rect = pygame.Rect(0, 0, map_w, map_h)
        self._map_rect.center = inner.center

        self._layout_key = (vw, vh)
        self._bg = widgets.make_round_panel(
            self._rect.size,
            bg_color=config.MINIMAP_BG_COLOR,
            border_color=config.MINIMAP_BORDER_COLOR)

    def rect(self):
        return self._rect

    def point_inside(self, pos):
        return self._rect.collidepoint(pos)

    # ============================================================
    # 坐标映射
    # ============================================================
    def world_to_minimap(self, x, y):
        """世界坐标 → 小地图屏幕坐标。"""
        mr = self._map_rect
        return (mr.left + x / self.world_width * mr.width,
                mr.top + y / self.world_height * mr.height)

    def minimap_to_world(self, pos):
        """小地图屏幕坐标（已夹到地图范围内）→ 世界坐标。"""
        mr = self._map_rect
        x = min(max(pos[0], mr.left), mr.right)
        y = min(max(pos[1], mr.top), mr.bottom)
        return ((x - mr.left) / mr.width * self.world_width,
                (y - mr.top) / mr.height * self.world_height)

    # ============================================================
    # 事件
    # ============================================================
    def handle_event(self, event, camera):
        """返回 True = 事件已被小地图消费。"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.point_inside(event.pos):
                return False
            self._dragging = True
            self._center_to(event.pos, camera)
            return True

        if event.type == pygame.MOUSEMOTION and self._dragging:
            # 按住后连续跟随（拖出小地图也不中断，直到松手）
            self._center_to(event.pos, camera)
            return True

        if (event.type == pygame.MOUSEBUTTONUP and event.button == 1
                and self._dragging):
            self._dragging = False
            return True

        if (event.type == pygame.MOUSEWHEEL
                and self.point_inside(pygame.mouse.get_pos())):
            return True   # 小地图内滚轮吞掉，不缩放大地图

        return False

    def _center_to(self, pos, camera):
        """把小地图上的一点换算成世界坐标并移动相机中心。"""
        wx, wy = self.minimap_to_world(pos)
        camera.center_on_world(wx, wy)

    # ============================================================
    # 绘制
    # ============================================================
    def draw(self, surface, camera):
        viewport_size = (camera.viewport_w, camera.viewport_h)
        if viewport_size != self._layout_key:
            self.layout(viewport_size)

        surface.blit(self._bg, self._rect.topleft)
        pygame.draw.rect(surface, config.MINIMAP_MAP_FILL, self._map_rect)
        self._draw_units(surface)
        self._draw_viewport(surface, camera)
        pygame.draw.rect(surface, config.MINIMAP_MAP_LINE, self._map_rect, 1)

    def _draw_units(self, surface):
        radius = max(1, int(config.MINIMAP_UNIT_RADIUS))
        for unit in self.state.all_units():
            wx, wy = hexgrid.axial_to_world(unit.q, unit.r, self.hex_size)
            mx, my = self.world_to_minimap(wx, wy)
            pygame.draw.circle(surface, config.SIDE_COLOR.get(unit.side, (200, 200, 200)),
                               (int(round(mx)), int(round(my))), radius)

    def _draw_viewport(self, surface, camera):
        x0, y0, x1, y1 = camera.visible_world_rect()
        mx0, my0 = self.world_to_minimap(x0, y0)
        mx1, my1 = self.world_to_minimap(x1, y1)
        rect = pygame.Rect(int(round(mx0)), int(round(my0)),
                           max(2, int(round(mx1 - mx0))),
                           max(2, int(round(my1 - my0))))
        rect = rect.clip(self._map_rect)
        if rect.width > 0 and rect.height > 0:
            pygame.draw.rect(surface, config.MINIMAP_VIEWPORT_LINE, rect, 1)
