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

import logging
import tkinter as tk
from tkinter import ttk

from game.config import constants as C
from game.config.style import THEME
from game.map.geo_data import GeoData
from game.map.viewport import Viewport
from game.map.renderer import MapRenderer
from game.config.constants import DEFAULT_MAP_PATH, DEFAULT_ROADS_PATH   # 补上第二个

logger = logging.getLogger(__name__)

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
        self._right_click_callback = None
        self._need_fit = False       # 加载数据后等待首次有效尺寸
        self._settle_job = None      # 滚轮静默后补绘的定时器句柄
        self._selected_node_id = None   # ★ 左键选中的县
        self._press_xy = None           # ★ 按下位置（区分拖拽 / 点击）
        self._bind_events()

    # ==========================================================
    # 对外
    # ==========================================================
    def set_location_callback(self, fn):
        self._location_callback = fn

    def set_zoom_callback(self, fn):
        self._zoom_callback = fn

    def set_right_click_callback(self, fn):
        """右键回调：fn(node_id, event)。node_id 为 None 表示空白处。"""
        self._right_click_callback = fn

    def _notify_zoom(self):
        """缩放比例变化时通知外部（如状态栏）。"""
        if self._zoom_callback:
            self._zoom_callback(self.viewport.scale)

    def load_geojson(self, path):
        logger.debug("MapCanvas 加载地图：%s", path)
        data = GeoData.from_file(path)
        # 加载水域（河流、湖泊），文件不存在则跳过
        if C.DEFAULT_WATER_PATH.is_file():
            try:
                data.load_water(str(C.DEFAULT_WATER_PATH))
            except Exception:
                # 与路网一致：加载失败不影响主地图
                logger.warning("水域加载失败，跳过", exc_info=True)

        # 路网随主地图一起加载；失败不影响主地图渲染
        roads_path = DEFAULT_ROADS_PATH
        if roads_path.exists():
            try:
                data.load_roads(roads_path)
            except Exception:
                logger.warning("路网加载失败，跳过", exc_info=True)
        
        self.data = data
        self.renderer.set_data(data)

        # 标记：等 canvas 拿到有效尺寸再 fit
        self._need_fit = True
        self._try_fit_now()
        return data

    def center_on(self, lon, lat, min_scale=None):
        """把视图中心移到 (lon, lat)；必要时把 scale 抬到 min_scale。"""
        if not self.data:
            return
        self._sync_canvas_size()
        self.viewport.cx = lon
        self.viewport.cy = lat
        if min_scale is not None and self.viewport.scale < min_scale:
            self.viewport.scale = min_scale
        self._notify_zoom()
        self.renderer.draw_full()

    def fit_to_node(self, node_id, fallback_lonlat=None,
                    margin=0.7, max_scale=200):
        """把某个县移到视图中心，并缩放到恰好显示其边界。

        找不到县界时退回 fallback_lonlat（节点中心点），只移不缩。
        max_scale 防止关隘/渡口这类小 boundary 被放大到离谱。
        """
        if not self.data:
            return
        logger.debug("定位到据点：%s", node_id)
        bbox = self._node_bbox(node_id)
        self._sync_canvas_size()

        if bbox is not None:
            self.viewport.fit_to_bbox(bbox, margin=margin)
            if max_scale is not None:
                self.viewport.scale = min(self.viewport.scale, max_scale)
        elif fallback_lonlat is not None:
            logger.debug("据点无 boundary，退回中心点：%s", node_id)
            self.viewport.cx, self.viewport.cy = fallback_lonlat
            if max_scale is not None:
                self.viewport.scale = min(self.viewport.scale, max_scale)
        else:
            return

        self._notify_zoom()
        self.renderer.draw_full()

    def _node_bbox(self, node_id):
        for feat in getattr(self.data, "shapes_city_boundary", []):
            props = feat.get("properties") or {}
            if props.get("id") == node_id:
                return feat.get("bbox")
        return None

    def reset_view(self):
        """用户主动复位：重新 fit 到全图，不受 _need_fit 影响。"""
        if not self.data or not self.data.bbox:
            return
        logger.debug("复位视图")
        self._sync_canvas_size()
        if self.viewport.width >= _MIN_VALID_SIZE and \
           self.viewport.height >= _MIN_VALID_SIZE:
            self.viewport.fit_to_bbox(self.data.bbox)
            self._need_fit = False
            self._notify_zoom()
            self.renderer.draw_full()
        else:
            self._need_fit = True

    def redraw(self):
        """设置变更后强制全量重绘（不改视图）。"""
        if not self.data or not self.data.bbox:
            return
        self._sync_canvas_size()
        self.renderer.draw_full()

    def zoom(self, factor, anchor=None):
        if not self.data or not self.data.bbox:
            return
        self._sync_canvas_size()
        mx, my = anchor if anchor else (self.viewport.width / 2,
                                        self.viewport.height / 2)
        self.viewport.zoom(factor, (mx, my))
        logger.debug("缩放 factor=%s  新 scale=%.2f", factor,
                     self.viewport.scale)
        self._notify_zoom()
        self.renderer.zoom(factor, mx, my)
        self._schedule_label_refresh()
        self._schedule_settle_redraw()

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
        logger.debug("画布尺寸生效：%dx%d",
                     self.viewport.width, self.viewport.height)
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
        c.bind("<Button-3>", self._on_right_click)
        c.bind("<Button-2>", self._on_right_click)
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
        self._press_xy = (event.x, event.y)

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
        # 位移 <= 4px 视为点击（否则是拖拽平移）
        was_click = False
        if self._press_xy is not None:
            if (abs(event.x - self._press_xy[0]) <= 4
                    and abs(event.y - self._press_xy[1]) <= 4):
                was_click = True
        self._drag = None
        self._press_xy = None
        if was_click:
            self._handle_click(event)

    def _handle_click(self, event):
        """左键点选县：只更新选中高亮，不触发任何业务逻辑。"""
        if not self.data:
            return
        lon, lat = self.viewport.unproject(event.x, event.y)
        info = self.data.find_location_detail(lon, lat)
        node_id = info.get("node_id")
        if node_id == self._selected_node_id:
            self._selected_node_id = None       # 再点同一县 → 取消
        else:
            self._selected_node_id = node_id    # 点空白 / 海 / 山 → None
        self.renderer.set_selected(self._selected_node_id)
        logger.debug("左键点选 node_id=%s", node_id)

    def _on_right_click(self, event):
        if not self.data:
            return
        lon, lat = self.viewport.unproject(event.x, event.y)
        info = self.data.find_location_detail(lon, lat)
        # 优先用被点选的县，否则用右键位置的县
        node_id = self._selected_node_id or info.get("node_id")
        logger.debug("右键 node_id=%s", node_id)
        if self._right_click_callback:
            self._right_click_callback(node_id, event)

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
        info = self.data.find_location_detail(lon, lat)   # ★ 新方法
        info["lon"] = lon
        info["lat"] = lat
        info["px"] = x          # ★ tooltip 定位用（画布内像素）
        info["py"] = y
        self.renderer.set_hover(info)                      # ★ hover 高亮
        self._location_callback(info)                      # ★ 传 dict

    def _on_leave(self, event):
        self.renderer.set_hover(None)                      # ★ 清除 hover 高亮
        if self._location_callback:
            self._location_callback(None)                  # ★ "" → None
    
    # ==========================================================
    # 渲染
    # ==========================================================
    def _sync_canvas_size(self):
        self.viewport.set_canvas_size(
            self.canvas.winfo_width(), self.canvas.winfo_height()
        )

    def _settle_redraw(self):
        self._settle_job = None
        if self._need_fit or not self.data:
            return
        self.renderer.draw_full()

    def _schedule_settle_redraw(self):
        """滚轮停手 180ms 后补一次全量重绘，补齐快速缩放时漏掉的州郡面。"""
        if self._settle_job is not None:
            try:
                self.after_cancel(self._settle_job)
            except Exception:
                pass
        self._settle_job = self.after(180, self._settle_redraw)

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