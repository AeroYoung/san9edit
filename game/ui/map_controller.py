# -*- coding: utf-8 -*-
"""面板访问地图的唯一接口。

面板只依赖本类的方法名，不触碰 MapCanvas / Viewport / Renderer。
将来需要新增跨模块命令（高亮、选中等）都往这里加。
"""


class MapController:
    def __init__(self, map_canvas):
        self._canvas = map_canvas

    def center_on(self, lon, lat, min_scale=None):
        """把视图中心移到 (lon, lat)；min_scale 给定时保证缩放不小于它。"""
        if self._canvas is None:
            return
        self._canvas.center_on(lon, lat, min_scale=min_scale)

    def reset_view(self):
        if self._canvas is not None:
            self._canvas.reset_view()

    def zoom(self, factor):
        if self._canvas is not None:
            self._canvas.zoom(factor)

    def fit_to_node(self, node_id, fallback_lonlat=None):
        if self._canvas is not None:
            self._canvas.fit_to_node(node_id, fallback_lonlat=fallback_lonlat)