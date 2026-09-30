# -*- coding: utf-8 -*-
"""相机：视口平移 / 缩放 / 世界⇄屏幕变换。

渲染层**只读数据**：本模块不写任何游戏状态。
"""

from battle import config
from battle.core import hexgrid


class Camera:
    """世界坐标（浮点，像素）与屏幕坐标之间的变换。

    属性：
        cx / cy   相机中心（世界坐标，浮点）
        zoom      像素 / 世界单位
    """

    def __init__(self, world_width, world_height, viewport_w, viewport_h,
                 hex_size):
        self.world_width = float(world_width)
        self.world_height = float(world_height)
        self.viewport_w = int(viewport_w)
        self.viewport_h = int(viewport_h)
        self.hex_size = float(hex_size)

        # 缩放范围
        self.zoom_max = config.ZOOM_MAX_HEX_EDGE_PX / self.hex_size
        self.zoom_min = self._compute_zoom_min()
        # 初始：每格水平进阶约 INITIAL_HEX_STEP_PX 像素
        self.zoom = config.INITIAL_HEX_STEP_PX / (1.5 * self.hex_size)

        self.cx = self.world_width / 2.0
        self.cy = self.world_height / 2.0

        self._clamp_zoom()
        self._clamp_center()

    # ------------------------------------------------------------
    # 变换
    # ------------------------------------------------------------
    def world_to_screen(self, x, y):
        """世界坐标 → 屏幕坐标。"""
        sx = (x - self.cx) * self.zoom + self.viewport_w / 2.0
        sy = (y - self.cy) * self.zoom + self.viewport_h / 2.0
        return sx, sy

    def screen_to_world(self, sx, sy):
        """屏幕坐标 → 世界坐标。"""
        x = (sx - self.viewport_w / 2.0) / self.zoom + self.cx
        y = (sy - self.viewport_h / 2.0) / self.zoom + self.cy
        return x, y

    def visible_world_rect(self):
        """当前视口覆盖的世界矩形 (x0, y0, x1, y1)，供渲染层裁剪。"""
        x0, y0 = self.screen_to_world(0, 0)
        x1, y1 = self.screen_to_world(self.viewport_w, self.viewport_h)
        return x0, y0, x1, y1

    # ------------------------------------------------------------
    # 操作
    # ------------------------------------------------------------
    def pan(self, dx, dy):
        """按屏幕像素位移平移视口。"""
        self.cx -= dx / self.zoom
        self.cy -= dy / self.zoom
        self._clamp_center()

    def zoom_at(self, factor, sx, sy):
        """以屏幕锚点 (sx, sy) 为不动点缩放，自动夹在 [zoom_min, zoom_max]。"""
        ax, ay = self.screen_to_world(sx, sy)
        self.zoom *= factor
        self._clamp_zoom()
        # 让锚点缩放后仍落在同一屏幕位置
        self.cx = ax - (sx - self.viewport_w / 2.0) / self.zoom
        self.cy = ay - (sy - self.viewport_h / 2.0) / self.zoom
        self._clamp_center()

    def center_on_world(self, x, y):
        """把相机中心设为世界坐标 (x, y)，并夹取到地图范围内。

        供小地图定位使用 —— 外部只走这个公开方法，不直接改 cx / cy。
        """
        self.cx = float(x)
        self.cy = float(y)
        self._clamp_center()

    def on_resize(self, width, height):
        """窗口尺寸变化：重算视口并重夹缩放与中心。"""
        self.viewport_w = int(width)
        self.viewport_h = int(height)
        self.zoom_min = self._compute_zoom_min()
        self._clamp_zoom()
        self._clamp_center()

    # ------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------
    def _compute_zoom_min(self):
        """整张地图完整可见，且包围盒较长边 ≈ min(屏宽, 屏高) × 0.5。"""
        shorter = max(1.0, min(self.viewport_w, self.viewport_h))
        longer_side = max(self.world_width, self.world_height)
        return (shorter * 0.5) / longer_side

    def _clamp_zoom(self):
        if self.zoom_min > self.zoom_max:
            # 视口小到与上限打架时，优先保证不越上限
            self.zoom = self.zoom_max
            return
        self.zoom = max(self.zoom_min, min(self.zoom_max, self.zoom))

    def _clamp_center(self):
        self.cx = max(0.0, min(self.world_width, self.cx))
        self.cy = max(0.0, min(self.world_height, self.cy))

    # ------------------------------------------------------------
    @classmethod
    def for_map(cls, map_data, viewport_w, viewport_h):
        """按地图数据建相机（世界尺寸由 hexgrid 统一给出）。"""
        width, height = hexgrid.world_bounds(
            map_data.cols, map_data.rows, map_data.hex_size)
        return cls(width, height, viewport_w, viewport_h, map_data.hex_size)
