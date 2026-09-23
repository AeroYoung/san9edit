# -*- coding: utf-8 -*-
"""视图状态：中心经纬度、缩放比例、画布尺寸。

外部只需三步：
    1. set_canvas_size(w, h)   窗口尺寸变化时调一次
    2. fit_to_bbox(bbox)       加载文件后调一次
    3. project(lon, lat)       渲染时把经纬度转成画布像素
    4. 缩放用 zoom()，平移用 pan_pixels()。
"""
 
class Viewport:
    def __init__(self):
        self.cx = 0.0
        self.cy = 0.0
        self.scale = 1.0        # 像素 / 度
        self.width = 1
        self.height = 1

    def set_canvas_size(self, w, h):
        self.width = max(int(w), 1)
        self.height = max(int(h), 1)

    def fit_to_bbox(self, bbox, margin=0.92):
        min_lon, min_lat, max_lon, max_lat = bbox
        self.cx = (min_lon + max_lon) / 2
        self.cy = (min_lat + max_lat) / 2
        sx = (self.width * margin) / max(max_lon - min_lon, 1e-9)
        sy = (self.height * margin) / max(max_lat - min_lat, 1e-9)
        self.scale = min(sx, sy)

    def zoom(self, factor, anchor=None):
        mx, my = anchor if anchor else (self.width / 2, self.height / 2)
        lon0 = self.cx + (mx - self.width / 2) / self.scale
        lat0 = self.cy - (my - self.height / 2) / self.scale
        self.scale *= factor
        self.cx = lon0 - (mx - self.width / 2) / self.scale
        self.cy = lat0 + (my - self.height / 2) / self.scale

    def pan_pixels(self, dx, dy):
        self.cx -= dx / self.scale
        self.cy += dy / self.scale

    def project(self, lon, lat):
        x = (lon - self.cx) * self.scale + self.width / 2
        y = -(lat - self.cy) * self.scale + self.height / 2
        return x, y

    def unproject(self, x, y):
        """屏幕像素 → 经纬度。"""
        lon = self.cx + (x - self.width / 2) / self.scale
        lat = self.cy - (y - self.height / 2) / self.scale
        return lon, lat

    def span_px(self, bbox):
        return (bbox[2] - bbox[0]) * self.scale