# -*- coding: utf-8 -*-
"""地图画布。整合 viewport + renderer + 鼠标交互。

对外接口：
    load_geojson(path)            加载数据
    reset_view() / zoom()         视图控制
    set_location_callback(fn)     鼠标移动时回调，参数是字符串

自动缩放机制：
    加载数据时设 _need_fit=True，等 canvas 首次获得有效尺寸
    （> 10 像素）再执行 fit。这样不依赖加载时机，无论窗口是
    最小化、最大化还是启动中就绪，地图最终都会显示在正确位置。
"""

import tkinter as tk
from tkinter import ttk

from game.config import constants as C
from game.config.style import THEME
from game.map.geo_data import GeoData
from game.map.viewport import Viewport
from game.map.renderer import MapRenderer
from game.config.constants import DEFAULT_MAP_PATH, DEFAULT_ROADS_PATH   # 补上第二个

_MIN_VALID_SIZE = 10      # 小于该尺寸认为布局还没完成


class MapCanvas(ttk.Frame):
    def __init__(self, master, font_family):
        super().__init__(master)
        self.font_family = font_family

        self.canvas = tk.Canvas(self, bg=THEME["canvas_bg"],
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.viewport = Viewport()
        self.renderer = MapRenderer(self.canvas, self.viewport, font_family)
        self.data = None

        self._drag = None
        self._label_job = None       # 平移/缩放后节流刷新标签
        self._mouse_job = None
        self._pending_mouse = None
        self._location_callback = None
        self._zoom_callback = None
        self._need_fit = False       # 加载数据后等待首次有效尺寸

        self._bind_events()

    # ==========================================================
    # 对外
    # ==========================================================
    def set_location_callback(self, fn):
        self._location_callback = fn

    def set_zoom_callback(self, fn):
        self._zoom_callback = fn

    def _notify_zoom(self):
        """缩放比例变化时通知外部（如状态栏）。"""
        if self._zoom_callback:
            self._zoom_callback(self.viewport.scale)

    def load_geojson(self, path):
        data = GeoData.from_file(path)
        # 加载水域（河流、湖泊），文件不存在则跳过
        # if C.DEFAULT_WATER_PATH.is_file():
        #     data.load_water(str(C.DEFAULT_WATER_PATH))
        # if not data.bbox:
        #     raise ValueError("文件里没有可绘制的坐标")
        
        # 路网随主地图一起加载；失败不影响主地图渲染
        roads_path = DEFAULT_ROADS_PATH
        if roads_path.exists():
            try:
                data.load_roads(roads_path)
            except Exception:
                pass
        
        self.data = data
        self.renderer.set_data(data)

        # 标记：等 canvas 拿到有效尺寸再 fit
        self._need_fit = True
        self._try_fit_now()
        return data

    def reset_view(self):
        """用户主动复位：重新 fit 到全图，不受 _need_fit 影响。"""
        if not self.data or not self.data.bbox:
            return
        self._sync_canvas_size()
        if self.viewport.width >= _MIN_VALID_SIZE and \
           self.viewport.height >= _MIN_VALID_SIZE:
            self.viewport.fit_to_bbox(self.data.bbox)
            self._need_fit = False
            self._notify_zoom()
            self.renderer.draw_full()
        else:
            self._need_fit = True

    def zoom(self, factor, anchor=None):
        if not self.data or not self.data.bbox:
            return
        self._sync_canvas_size()
        mx, my = anchor if anchor else (self.viewport.width / 2,
                                        self.viewport.height / 2)
        self.viewport.zoom(factor, (mx, my))
        self._notify_zoom()
        self.renderer.zoom(factor, mx, my)
        self._schedule_label_refresh()

    # ==========================================================
    # 内部：fit 相关
    # ==========================================================
    def _try_fit_now(self):
        """如果当前尺寸有效且有待 fit，则立即 fit。"""
        self._sync_canvas_size()
        if not self._need_fit:
            return
        if self.viewport.width < _MIN_VALID_SIZE or \
           self.viewport.height < _MIN_VALID_SIZE:
            return
        if not self.data or not self.data.bbox:
            return
        self.viewport.fit_to_bbox(self.data.bbox)
        self._need_fit = False
        self._notify_zoom()
        self.renderer.draw_full()

    # ==========================================================
    # 事件
    # ==========================================================
    def _bind_events(self):
        c = self.canvas
        c.bind("<MouseWheel>", self._on_wheel)
        c.bind("<Button-4>", lambda e: self.zoom(1.25, (e.x, e.y)))
        c.bind("<Button-5>", lambda e: self.zoom(1 / 1.25, (e.x, e.y)))
        c.bind("<ButtonPress-1>", self._on_press)
        c.bind("<B1-Motion>", self._on_drag)
        c.bind("<ButtonRelease-1>", self._on_release)
        c.bind("<Double-Button-1>", lambda e: self.reset_view())
        c.bind("<Motion>", self._on_motion)
        c.bind("<Leave>", self._on_leave)
        c.bind("<Configure>", self._on_resize)

    def _on_wheel(self, event):
        if event.delta == 0:
            return
        factor = 1.2 if event.delta > 0 else 1 / 1.2
        self.zoom(factor, (event.x, event.y))

    def _on_press(self, event):
        self._drag = (event.x, event.y)

    def _on_drag(self, event):
        if not self._drag:
            return
        x0, y0 = self._drag
        dx, dy = event.x - x0, event.y - y0
        self.viewport.pan_pixels(dx, dy)
        self._drag = (event.x, event.y)
        self.renderer.pan(dx, dy)
        self._schedule_label_refresh()

    def _on_release(self, event):
        self._drag = None

    def _on_resize(self, event):
        """窗口尺寸变化。

        首次拿到有效尺寸时自动 fit；之后只重绘，不改变比例——
        否则用户拖动 PanedWindow 分隔条会突然重置视野。
        """
        self.viewport.set_canvas_size(event.width, event.height)
        if self._need_fit:
            self._try_fit_now()
        else:
            self.renderer.draw_full()

    def _on_motion(self, event):
        self._pending_mouse = (event.x, event.y)
        if self._mouse_job is not None:
            return
        self._mouse_job = self.after(40, self._process_motion)

    def _process_motion(self):
        self._mouse_job = None
        if not self._pending_mouse or not self._location_callback:
            return
        if not self.data:
            return
        x, y = self._pending_mouse
        lon, lat = self.viewport.unproject(x, y)
        state, county, city = self.data.find_location(lon, lat)
        parts = [p for p in (state, county, city) if p]
        if parts:
            text = " · ".join(parts) + f"   （{lon:.2f}°E, {lat:.2f}°N）"
        else:
            text = f"{lon:.2f}°E, {lat:.2f}°N"
        self._location_callback(text)

    def _on_leave(self, event):
        if self._location_callback:
            self._location_callback("")

    # ==========================================================
    # 渲染
    # ==========================================================
    def _sync_canvas_size(self):
        self.viewport.set_canvas_size(
            self.canvas.winfo_width(), self.canvas.winfo_height()
        )

    def _schedule_label_refresh(self):
        """平移/缩放后节流刷新标签（每 30ms 最多一次）。

        几何已用 canvas.move/scale 即时变换，标签位置也一起变了；
        这里只补漏：重算裁剪（边缘标签增删）和字号。
        """
        if self._label_job is not None:
            return
        self._label_job = self.canvas.after(30, self._do_label_refresh)

    def _do_label_refresh(self):
        self._label_job = None
        self.renderer.refresh_dynamic()