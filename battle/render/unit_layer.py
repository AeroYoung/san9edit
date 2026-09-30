# -*- coding: utf-8 -*-
"""部队绘制层：视口裁剪 + 三级 LOD + 命中测试 + 框选。

渲染层**只读数据**：不写 `BattleState` / `Unit` 的任何字段。
"""

import logging
import math

import pygame

from battle import config
from battle.core import hexgrid
from battle.render import symbol as sym
from battle.render import widgets

logger = logging.getLogger("battle.render.unit_layer")

_SQRT3 = math.sqrt(3.0)

LOD_FAR = "far"
LOD_MID = "mid"
LOD_NEAR = "near"

# 符号可能超出格子的余量（小字 / 小条 / 高亮圈），裁剪时放宽这么多像素
_CULL_MARGIN_PX = 64


class UnitLayer:
    """把 `BattleState` 里的单位画到屏幕上。"""

    def __init__(self, state, map_data):
        self.state = state
        self.cols = int(map_data.cols)
        self.rows = int(map_data.rows)
        self.hex_size = float(map_data.hex_size)

    # ============================================================
    # LOD
    # ============================================================
    def edge_px(self, camera):
        """屏幕上的格边长（像素）。"""
        return camera.zoom * self.hex_size

    def lod_of(self, camera):
        edge = self.edge_px(camera)
        if edge < config.LOD_FAR_MAX_PX:
            return LOD_FAR
        if edge >= config.LOD_NEAR_MIN_PX:
            return LOD_NEAR
        return LOD_MID

    def font_sizes(self, camera):
        """(兵种小字字号, 兵力数字字号)：按格边长在区间内插值。"""
        span = max(1e-6, config.LOD_NEAR_MIN_PX - config.LOD_FAR_MAX_PX)
        t = (self.edge_px(camera) - config.LOD_FAR_MAX_PX) / span
        t = max(0.0, min(1.0, t))
        label = config.SYMBOL_FONT_SIZE_MIN + t * (
            config.SYMBOL_FONT_SIZE_MAX - config.SYMBOL_FONT_SIZE_MIN)
        troops = config.SYMBOL_TROOP_FONT_MIN + t * (
            config.SYMBOL_TROOP_FONT_MAX - config.SYMBOL_TROOP_FONT_MIN)
        return int(round(label)), int(round(troops))

    # ============================================================
    # 绘制
    # ============================================================
    def draw(self, surface, camera, selected, box_rect=None,
             motion=None, progress=0.0):
        """画路径 → 全部可见单位 → 选中高亮 →（拖拽中的）框选虚线框。

        `motion` = `{unit_id: (旧 q, 旧 r)}`，`progress` = 本 tick 内进度 0.0–1.0；
        两者由 `app.py` 持有（渲染层只读），用于帧间位置插值，不写任何 `Unit` 字段。
        """
        lod = self.lod_of(camera)
        label_size, troop_size = self.font_sizes(camera)
        size_px = self.edge_px(camera)

        self._draw_paths(surface, camera, selected)

        for unit, cell_center in self._visible_units(camera):
            center = self._interpolated_center(unit, cell_center, camera,
                                               motion, progress)
            type_def = unit.type_def or {}
            shape = type_def.get("symbol_shape", sym.SHAPE_SQUARE)
            is_selected = unit.id in selected

            if lod == LOD_FAR:
                sym.draw_far_block(surface, center, unit.side)
                if is_selected:
                    sym.draw_highlight(surface, center, shape, size_px,
                                       is_block=True)
                continue

            sym.draw_symbol(surface, center, type_def, unit.side, size_px)
            sym.draw_bars(surface, center, unit.morale, unit.stamina,
                          shape, size_px)
            sym.draw_label(surface, center, unit.name,
                           shape, size_px, label_size)
            if lod == LOD_NEAR:
                sym.draw_troops(surface, center, format_troops(unit.troops),
                                shape, size_px, troop_size)
            if is_selected:
                sym.draw_highlight(surface, center, shape, size_px)

        if box_rect is not None and box_rect.width > 0 and box_rect.height > 0:
            self._draw_box(surface, box_rect)

    def _draw_box(self, surface, box_rect):
        """框选：半透明填充 + 虚线边框。"""
        widgets.draw_alpha_rect(surface, box_rect, config.SELECT_BOX_COLOR)
        widgets.draw_dashed_rect(surface, config.SELECT_HIGHLIGHT_COLOR,
                                 box_rect, dash=(6, 4), width=1)

    def _interpolated_center(self, unit, cell_center, camera, motion, progress):
        """本 tick 内从旧格向当前格插值后的屏幕中心（无位移记录 → 格中心）。"""
        if not motion or progress >= 1.0:
            return cell_center
        previous = motion.get(unit.id)
        if previous is None or previous == (unit.q, unit.r):
            return cell_center
        fx, fy = hexgrid.axial_to_world(previous[0], previous[1], self.hex_size)
        tx, ty = hexgrid.axial_to_world(unit.q, unit.r, self.hex_size)
        return camera.world_to_screen(fx + (tx - fx) * progress,
                                      fy + (ty - fy) * progress)

    # ------------------------------------------------------------
    # 路径预览（只画选中部队）
    # ------------------------------------------------------------
    def _draw_paths(self, surface, camera, selected):
        for unit, cell_center in self._visible_units(camera):
            if unit.id not in selected:
                continue
            command = unit.command
            path = getattr(command, "path", None) if command is not None else None
            if not path:
                continue
            points = [cell_center]
            for q, r in path:
                wx, wy = hexgrid.axial_to_world(q, r, self.hex_size)
                points.append(camera.world_to_screen(wx, wy))
            self._draw_dashed_polyline(surface, points)

    def _draw_dashed_polyline(self, surface, points):
        """沿折线画虚线（跨段连续，步长 = `config.PATH_DASH`）。"""
        on, off = config.PATH_DASH
        period = float(on + off)
        traveled = 0.0
        for (x0, y0), (x1, y1) in zip(points, points[1:]):
            length = math.hypot(x1 - x0, y1 - y0)
            if length <= 0:
                continue
            t = 0.0
            while t < length:
                phase = (traveled + t) % period
                if phase < on:
                    end = min(t + (on - phase), length)
                    start_pt = (x0 + (x1 - x0) * t / length,
                                y0 + (y1 - y0) * t / length)
                    end_pt = (x0 + (x1 - x0) * end / length,
                              y0 + (y1 - y0) * end / length)
                    pygame.draw.line(surface, config.PATH_COLOR,
                                     start_pt, end_pt, config.PATH_WIDTH)
                    t = end
                else:
                    t += (period - phase)
            traveled += length

    # ============================================================
    # 查询
    # ============================================================
    def hit_test(self, pos, camera):
        """屏幕点 → 该格单位；空格 / 无单位 → None。"""
        wx, wy = camera.screen_to_world(pos[0], pos[1])
        q, r = hexgrid.world_to_axial(wx, wy, self.hex_size)
        return self.state.unit_at(q, r)

    def box_select(self, box_rect, camera, side_filter=None):
        """返回矩形内的单位（只返回 `side_filter` 匹配的）。"""
        out = []
        for unit, center in self._visible_units(camera, margin=0):
            if side_filter is not None and unit.side != side_filter:
                continue
            if box_rect.collidepoint(center):
                out.append(unit)
        return out

    # ============================================================
    # 视口裁剪
    # ============================================================
    def _visible_units(self, camera, margin=_CULL_MARGIN_PX):
        """视口内的单位：(unit, 屏幕中心) 迭代器。

        先按视口反算轴向矩形做粗筛，再按屏幕坐标精筛 —— 不遍历全表。
        """
        q_lo, q_hi, r_lo, r_hi = self._axial_rect(camera)
        viewport_w = camera.viewport_w
        viewport_h = camera.viewport_h
        size = self.hex_size

        for unit in self.state.units_in_axial_rect(q_lo, q_hi, r_lo, r_hi):
            wx, wy = hexgrid.axial_to_world(unit.q, unit.r, size)
            sx, sy = camera.world_to_screen(wx, wy)
            if (-margin <= sx <= viewport_w + margin
                    and -margin <= sy <= viewport_h + margin):
                yield unit, (sx, sy)

    def _axial_rect(self, camera):
        """视口覆盖的轴向坐标矩形（保守取大，保证不漏）。"""
        x0, y0, x1, y1 = camera.visible_world_rect()
        size = self.hex_size

        q_lo = int(math.floor(x0 / (1.5 * size))) - 1
        q_hi = int(math.ceil(x1 / (1.5 * size))) + 1
        q_lo = max(0, min(self.cols - 1, q_lo))
        q_hi = max(0, min(self.cols - 1, q_hi))

        # y = √3·size·(r + q/2) ⇒ r = y/(√3·size) − q/2，按 q 的两端放宽
        r_lo = int(math.floor(y0 / (_SQRT3 * size) - q_hi / 2.0)) - 1
        r_hi = int(math.ceil(y1 / (_SQRT3 * size) - q_lo / 2.0)) + 1
        r_lo = max(0, min(self.rows - 1, r_lo))
        r_hi = max(0, min(self.rows - 1, r_hi))
        return q_lo, q_hi, r_lo, r_hi


def format_troops(troops):
    """兵力千分位文本。"""
    return format(int(troops), ",")
