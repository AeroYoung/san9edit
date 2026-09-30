# -*- coding: utf-8 -*-
"""六宫格绘制：视口裁剪 + 外扩缓存 + 低缩放合并绘制。

渲染层**只读数据**：不写任何游戏状态。

绘制策略
--------
1. **视口裁剪**：只遍历视口覆盖的 (col, row) 区间，绝不遍历全图 12 万格。
2. **外扩缓存**：静态层 Surface 比视口四周各大 `CACHE_MARGIN_PX`，平移只要
   新视口仍落在缓存覆盖范围内就直接复用，不重建。
3. **低缩放合并**：视口内格数超过 `SOLID_FILL_CELL_LIMIT` 时（此时单格已小于
   约 12 像素，逐格描线只会糊成一片），降级为「整块填充 + 地图外框」，
   把 O(格数) 的绘制降成 O(1)。
"""

import logging
import math

import pygame

from battle import config
from battle.core import hexgrid

logger = logging.getLogger("battle.render.hex_renderer")

_SQRT3 = math.sqrt(3.0)


class HexRenderer:
    """平顶六宫格静态层。"""

    def __init__(self, cols, rows, hex_size):
        self.cols = int(cols)
        self.rows = int(rows)
        self.hex_size = float(hex_size)
        self.margin = int(config.CACHE_MARGIN_PX)

        self._cache = None          # 外扩后的静态层 Surface
        self._key = None            # 建缓存时的相机状态
        self._blit_pos = (0, 0)     # 缓存贴到屏幕的位置

    # ------------------------------------------------------------
    # 对外
    # ------------------------------------------------------------
    def draw(self, surface, camera):
        """把静态层画到 surface 上（能复用缓存就只 blit）。"""
        if not self._can_reuse(camera):
            self._rebuild(camera)
        surface.blit(self._cache, self._blit_pos)

    def invalidate(self):
        """作废缓存（地图 / 配色变更后调用）。"""
        self._cache = None
        self._key = None

    # ------------------------------------------------------------
    # 缓存命中判断
    # ------------------------------------------------------------
    def _can_reuse(self, camera):
        """相机是否仍落在缓存覆盖范围内（缩放与视口尺寸必须一致）。"""
        if self._cache is None:
            return False
        zoom, cx, cy, vw, vh = self._key
        if zoom != camera.zoom or vw != camera.viewport_w or vh != camera.viewport_h:
            return False

        ox, oy = self._offset(camera)
        # 缓存覆盖屏幕 x ∈ [ox, ox+vw+2M)；要求 [0, vw) 落在其中
        if not (-2 * self.margin <= ox <= 0 and -2 * self.margin <= oy <= 0):
            return False
        # 非整数位移会让 blit 糊边 → 重建
        if abs(ox - round(ox)) > 1e-6 or abs(oy - round(oy)) > 1e-6:
            return False

        self._blit_pos = (int(round(ox)), int(round(oy)))
        return True

    def _offset(self, camera):
        """缓存原点相对当前视口左上角的屏幕偏移（浮点）。"""
        zoom, cx, cy, _vw, _vh = self._key
        return (-self.margin + (cx - camera.cx) * zoom,
                -self.margin + (cy - camera.cy) * zoom)

    # ------------------------------------------------------------
    # 重建
    # ------------------------------------------------------------
    def _rebuild(self, camera):
        w = max(1, camera.viewport_w) + 2 * self.margin
        h = max(1, camera.viewport_h) + 2 * self.margin
        layer = pygame.Surface((w, h))
        layer.fill(config.COLOR_VIEWPORT_MARGIN)

        col_lo, col_hi, row_lo, row_hi = self._visible_range(camera)
        cells = (col_hi - col_lo + 1) * (row_hi - row_lo + 1)

        if cells > config.SOLID_FILL_CELL_LIMIT:
            self._draw_coalesced(layer, camera, cells)
        else:
            self._draw_cells(layer, camera, col_lo, col_hi, row_lo, row_hi)

        self._cache = layer
        self._key = (camera.zoom, camera.cx, camera.cy,
                     camera.viewport_w, camera.viewport_h)
        self._blit_pos = (-self.margin, -self.margin)

    def _draw_cells(self, layer, camera, col_lo, col_hi, row_lo, row_hi):
        """逐格画六边形（填充 + 1px 描边）。"""
        size = self.hex_size
        to_layer = self._to_layer(camera)

        for col in range(col_lo, col_hi + 1):
            for row in range(row_lo, row_hi + 1):
                q, r = hexgrid.offset_to_axial(col, row)
                wx, wy = hexgrid.axial_to_world(q, r, size)
                pts = [to_layer(px, py)
                       for px, py in hexgrid.hex_corners(wx, wy, size)]
                pygame.draw.polygon(layer, config.COLOR_HEX_FILL, pts)
                pygame.draw.polygon(layer, config.COLOR_HEX_LINE, pts, 1)

        logger.debug(
            "静态层重建（逐格）：cols %s–%s rows %s–%s，%s 格，zoom=%.4f",
            col_lo, col_hi, row_lo, row_hi,
            (col_hi - col_lo + 1) * (row_hi - row_lo + 1), camera.zoom,
        )

    def _draw_coalesced(self, layer, camera, cells):
        """低缩放合并绘制：整块填充 + 地图外框（O(1) 次绘制调用）。"""
        world_w, world_h = hexgrid.world_bounds(
            self.cols, self.rows, self.hex_size)
        x0 = -self.hex_size
        y0 = -self.hex_size * _SQRT3 / 2.0

        to_layer = self._to_layer(camera)
        sx0, sy0 = to_layer(x0, y0)
        sx1, sy1 = to_layer(x0 + world_w, y0 + world_h)
        rect = pygame.Rect(int(round(sx0)), int(round(sy0)),
                           max(1, int(round(sx1 - sx0))),
                           max(1, int(round(sy1 - sy0))))

        pygame.draw.rect(layer, config.COLOR_HEX_FILL, rect)
        pygame.draw.rect(layer, config.COLOR_HEX_LINE, rect, 1)

        logger.debug(
            "静态层重建（合并）：视口内 %s 格 > %s，降级为整块填充，zoom=%.4f",
            cells, config.SOLID_FILL_CELL_LIMIT, camera.zoom,
        )

    # ------------------------------------------------------------
    # 坐标 / 裁剪
    # ------------------------------------------------------------
    def _to_layer(self, camera):
        """世界坐标 → 缓存 Surface 像素（缓存原点 = 屏幕 (-margin, -margin)）。"""
        margin = self.margin

        def convert(x, y):
            sx, sy = camera.world_to_screen(x, y)
            return sx + margin, sy + margin

        return convert

    def _visible_range(self, camera):
        """视口（含外扩）覆盖的 (col, row) 区间，已夹到地图范围内。"""
        margin = self.margin
        x0, y0 = camera.screen_to_world(-margin, -margin)
        x1, y1 = camera.screen_to_world(
            camera.viewport_w + margin, camera.viewport_h + margin)
        size = self.hex_size

        col_lo = int(math.floor(x0 / (1.5 * size))) - 1
        col_hi = int(math.ceil(x1 / (1.5 * size))) + 1
        col_lo = max(0, min(self.cols - 1, col_lo))
        col_hi = max(0, min(self.cols - 1, col_hi))

        # 奇数列的格中心比偶数列低半格，故上下各留 1 行余量
        row_lo = int(math.floor(y0 / (_SQRT3 * size))) - 1
        row_hi = int(math.ceil(y1 / (_SQRT3 * size))) + 1
        row_lo = max(0, min(self.rows - 1, row_lo))
        row_hi = max(0, min(self.rows - 1, row_hi))

        return col_lo, col_hi, row_lo, row_hi
