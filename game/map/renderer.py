# -*- coding: utf-8 -*-
"""地图绘制。与 UI 事件完全解耦。

渲染顺序 = 叠放层级，从底到顶：
    render_polygons → render_lines → render_points
    → render_state_labels → render_county_labels → render_city_labels
"""

from game.config.style import MAP_STYLE, CITY_LEVEL_MIN_SCALE
from game.config.style import MAP_STYLE, CITY_LEVEL_MIN_SCALE, LAYER_VISIBILITY

class MapRenderer:
    LABEL_TAG = "label"     # 文字标签的 tag，用于整体删除/重绘
    WATER_TAG = "water"     # 水域的 tag，缩放时按 min_scale 重新筛选
    ROAD_TAG  = "road"
    POLYGON_TAG = "polygon"
    LINE_TAG    = "line"
    POINT_TAG   = "point"

    def __init__(self, canvas, viewport, font_family):
        self.canvas = canvas
        self.viewport = viewport
        self.font_family = font_family
        self.data = None
        self._drawn = False      # 是否已完整绘制过（move/scale 变换的前提）
        self._cum_scale = 1.0    # 自上次完整重绘以来的累计缩放倍率

    def set_data(self, geo_data):
        self.data = geo_data

    # ==========================================================
    # 调度
    # ==========================================================
    def draw_full(self):
        """完整重绘：按当前 viewport 重新投影所有几何 + 标签。

        用于加载、复位、窗口尺寸变化——这些情况缩放/中心都变了，
        无法用 move/scale 变换，只能重新投影。
        """
        self.canvas.delete("all")
        self._drawn = False
        self._cum_scale = 1.0
        if not self.data or not self.data.bbox:
            return
        self._draw_geometry()
        self._drawn = True
        self.refresh_dynamic()     # 水/路/点/标签（动态）
                

    def pan(self, dx, dy):
        """平移：整体 move 变换（O(1)），标签随后由 refresh_labels 补漏。"""
        if not self._drawn:
            return
        self.canvas.move("all", dx, dy)

    def zoom(self, factor, mx, my):
        """缩放：整体 scale 变换（O(1)），标签随后由 refresh_labels 更新字号/显隐。"""
        if not self._drawn:
            return
        self._cum_scale *= factor
        if self._cum_scale > 2.0 or self._cum_scale < 0.5:
            # canvas.scale 有微小舍入误差，连续缩放的误差会累积；
            # 累计偏离太远时重新投影一次，把误差清零。
            self.draw_full()
            return
        self.canvas.scale("all", mx, my, factor, factor)

    def refresh_dynamic(self):
        if not self._drawn:
            return
        for t in (self.LABEL_TAG, self.WATER_TAG, self.ROAD_TAG, self.POINT_TAG):
            self.canvas.delete(t)

        if LAYER_VISIBILITY.get("water", True):
            self._draw_water()
        if LAYER_VISIBILITY.get("road", True):
            self.render_roads()
        if LAYER_VISIBILITY.get("point", True):
            self.render_points()
        self._draw_labels()     # 内部各自再判断

        self.canvas.tag_lower(self.ROAD_TAG, self.LINE_TAG)
        self.canvas.tag_lower(self.WATER_TAG, self.ROAD_TAG)
        self.canvas.tag_lower(self.ROAD_TAG, self.POINT_TAG)

    def _draw_geometry(self):
        if LAYER_VISIBILITY.get("polygon", True):
            self.render_polygons()
        if LAYER_VISIBILITY.get("line", True):
            self.render_lines()

    def _draw_labels(self):
        if LAYER_VISIBILITY.get("label_state", True):
            self.render_state_labels()
        if LAYER_VISIBILITY.get("label_county", True):
            self.render_county_labels()
        if LAYER_VISIBILITY.get("label_city", True):
            self.render_city_labels()

    def _draw_water(self):
        self.render_water_polygons()
        self.render_water_lines()

    def _visible_bounds(self, margin_px=20):
        """当前视口的可见经纬度范围，margin_px 是屏幕像素的留白。"""
        vp = self.viewport
        m = margin_px / vp.scale
        half_w = vp.width / (2 * vp.scale)
        half_h = vp.height / (2 * vp.scale)
        return (vp.cx - half_w - m, vp.cy - half_h - m,
                vp.cx + half_w + m, vp.cy + half_h + m)

    # ==========================================================
    # 水域图层
    # ==========================================================
    def render_water_polygons(self):
        style = MAP_STYLE["water_polygon"]
        min_lon, min_lat, max_lon, max_lat = self._visible_bounds()
        scale = self.viewport.scale
        for feat in self.data.shapes_water_polygon:
            if scale < feat["min_scale"]:
                continue
            b = feat["bbox"]
            if b[2] < min_lon or b[0] > max_lon or b[3] < min_lat or b[1] > max_lat:
                continue
            try:
                self.render_water_polygon(feat, style)
            except Exception:
                pass

    def render_water_lines(self):
        if not LAYER_VISIBILITY.get("water", True):
                return
        style = MAP_STYLE["water_line"]
        min_lon, min_lat, max_lon, max_lat = self._visible_bounds()
        scale = self.viewport.scale
        for feat in self.data.shapes_water_line:
            if scale < feat["min_scale"]:
                continue
            b = feat["bbox"]
            if b[2] < min_lon or b[0] > max_lon or b[3] < min_lat or b[1] > max_lat:
                continue
            try:
                self.render_water_line(feat, style)
            except Exception:
                pass

    def render_water_polygon(self, feat, style):
        if not LAYER_VISIBILITY.get("water", True):
                return
        geom = feat["geometry"]
        polys = ([geom["coordinates"]] if geom["type"] == "Polygon"
                 else geom["coordinates"])
        for poly in polys:
            for ring in poly:
                if len(ring) < 3:
                    continue
                pts = []
                for lon, lat in ring:
                    x, y = self.viewport.project(lon, lat)
                    pts.extend((x, y))
                self.canvas.create_polygon(
                    *pts, fill=style["fill"], outline=style["outline"],
                    width=style["width"], tags=self.WATER_TAG
                )

    def render_water_line(self, feat, style):
        geom = feat["geometry"]
        lines = ([geom["coordinates"]] if geom["type"] == "LineString"
                 else geom["coordinates"])
        for line in lines:
            pts = []
            for lon, lat in line:
                x, y = self.viewport.project(lon, lat)
                pts.extend((x, y))
            if len(pts) >= 4:
                self.canvas.create_line(*pts, fill=style["color"],
                                        width=style["width"],
                                        tags=(self.WATER_TAG,self.LINE_TAG))

    # ==========================================================
    # 几何图层
    # ==========================================================
    def render_polygons(self):
        min_lon, min_lat, max_lon, max_lat = self._visible_bounds()
        for feat in self.data.shapes_polygon:
            b = feat["bbox"]
            if b[2] < min_lon or b[0] > max_lon or b[3] < min_lat or b[1] > max_lat:
                continue
            try:
                self.render_polygon(feat)
            except Exception:
                pass

    def render_lines(self):
        min_lon, min_lat, max_lon, max_lat = self._visible_bounds()
        for feat in self.data.shapes_line:
            b = feat["bbox"]
            if b[2] < min_lon or b[0] > max_lon or b[3] < min_lat or b[1] > max_lat:
                continue
            try:
                self.render_line(feat)
            except Exception:
                pass

    def render_points(self):
        if not LAYER_VISIBILITY.get("point", True):
                return
        style = MAP_STYLE.get("point", {})
        if not getattr(self.data, "shapes_point", None):
            return
        minx, miny, maxx, maxy = self._visible_bounds()
        scale = self.viewport.scale
        for feat in self.data.shapes_point:
            try:
                lon, lat = self._point_lonlat(feat)
                if lon is None:
                    continue
                if not (minx <= lon <= maxx and miny <= lat <= maxy):
                    continue
                props = feat.get("properties", {}) if isinstance(feat, dict) else {}
                try:
                    level = int(props.get("level", 5))
                except (TypeError, ValueError):
                    level = 5
                level = max(1, min(10, level))
                if scale < CITY_LEVEL_MIN_SCALE.get(level, 0):
                    continue
                self.render_point(lon, lat, feat, style)
            except Exception as e:
                print("[point]", type(e).__name__, e)

    def render_point(self, lon, lat, feat, style):

        props = {}
        if isinstance(feat, dict):
            props = feat.get("properties") or {}
        elif isinstance(feat, (list, tuple)) and len(feat) >= 3 and isinstance(feat[2], dict):
            props = feat[2]

        try:
            level = int(props.get("level", 5))
        except (TypeError, ValueError):
            level = 5
        level = max(1, min(10, level))

        x, y = self.viewport.project(lon, lat)
        r = self._point_radius(level, style)
        if r <= 0:
            return

        base_fill = props.get("fill", style.get("fill", "#000000"))
        shape = style.get("shape_by_level", {}).get(level, "circle")
        hollow = style.get("hollow_by_level", {}).get(level, False)

        # 空心 / 实心：用不同的描边配置
        if hollow:
            fill = ""                                        # 透明，底图透出
            outline = style.get("hollow_outline", "#000000")
            ow = max(0.8, min(1.4, r * 0.4))
        else:
            fill = base_fill
            outline = style.get("outline") or base_fill
            ow = style.get("outline_width", 0.6)

        lv_tag = f"city_lv{level}"
        tags = (self.POINT_TAG, lv_tag)

        # 外环（黑色粗线）
        if style.get("ring_by_level", {}).get(level, False):
            ring_scale = style.get("ring_scale", 1.75)
            ring_r = r * ring_scale
            ring_color = style.get("ring_color") or outline
            ring_w = style.get("ring_width", 1.4)
            self._draw_point_shape(x, y, ring_r, shape, "", ring_color, ring_w, tags)

        # 主体
        self._draw_point_shape(x, y, r, shape, fill, outline, ow, tags)    

    def _draw_point_shape(self, cx, cy, r, shape, fill, outline, width, tags):
        """按 shape 画单个点图形。主形状与外环共用，只是 fill/半径不同。"""
        if shape == "square":
            self.canvas.create_rectangle(
                cx - r, cy - r, cx + r, cy + r,
                fill=fill, outline=outline, width=width, tags=tags)
        elif shape == "diamond":
            self.canvas.create_polygon(
                [cx, cy - r, cx + r, cy, cx, cy + r, cx - r, cy],
                fill=fill, outline=outline, width=width, tags=tags)
        elif shape == "triangle":
            self.canvas.create_polygon(
                [cx, cy - r, cx + r * 0.866, cy + r * 0.5, cx - r * 0.866, cy + r * 0.5],
                fill=fill, outline=outline, width=width, tags=tags)
        else:  # circle
            self.canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=fill, outline=outline, width=width, tags=tags)

    def render_polygon(self, feat):
        geom = feat["geometry"]
        props = feat.get("properties") or {}
        base = MAP_STYLE["polygon"]
        fill = props.get("fill") or base["fill"]
        outline = props.get("stroke") or base["outline"]

        rings_iter = ([geom["coordinates"]] if geom["type"] == "Polygon"
                      else geom["coordinates"])
        for rings in rings_iter:
            if not rings or len(rings[0]) < 3:
                continue
            pts = []
            for lon, lat in rings[0]:
                x, y = self.viewport.project(lon, lat)
                pts.extend((x, y))
            self.canvas.create_polygon(
                *pts, fill=fill, outline=outline, width=base["width"]
            )

    def render_line(self, feat):
        geom = feat["geometry"]
        props = feat.get("properties") or {}
        base = MAP_STYLE["line"]
        color = props.get("stroke") or base["color"]

        lines = ([geom["coordinates"]] if geom["type"] == "LineString"
                 else geom["coordinates"])
        for line in lines:
            pts = []
            for lon, lat in line:
                x, y = self.viewport.project(lon, lat)
                pts.extend((x, y))
            if len(pts) >= 4:
                self.canvas.create_line(*pts, fill=color, width=base["width"],tags=self.LINE_TAG)

    # ==========================================================
    # 文字图层
    # ==========================================================
    def render_state_labels(self):
        self.render_label_group(self.data.labels_state, "label_state")

    def render_county_labels(self):
        self.render_label_group(self.data.labels_county, "label_county")

    def render_city_labels(self):
        labels = self.data.labels_city
        if not labels:
            return

        base = MAP_STYLE["label_city"]
        style = self.resolve_style("label_city")
        if style["size"] <= 0:
            return

        point_style = MAP_STYLE.get("point", {})       # 新增
        text_half = style["size"] * 0.5                # 新增：中文半高近似
        gap = base.get("point_gap", 3)                 # 新增

        scale = self.viewport.scale
        w = self.viewport.width
        h = self.viewport.height
        pad = style["size"] * 2
        default_min = base.get("min_scale", 30)

        for lon, lat, text, level in labels:
            # 按县的 level 决定显示名称所需的最小缩放比例
            min_scale = CITY_LEVEL_MIN_SCALE.get(level, default_min)
            if scale < min_scale:
                continue
            x, y = self.viewport.project(lon, lat)
            if x < -pad or x > w + pad or y < -pad or y > h + pad:
                continue
            r = self._point_radius(level, point_style)  # 新增：取该县点当前半径
            offset = r + text_half + gap                # 新增：总上移量
            self.draw_text(x, y - offset, text, style)  # 改：y → y - offset

    def render_label_group(self, labels, style_key):
        if not labels:
            return
        base = MAP_STYLE[style_key]
        scale = self.viewport.scale
        if scale < base.get("min_scale", 0):
            return
        if "max_scale" in base and scale >= base["max_scale"]:
            return

        style = self.resolve_style(style_key)
        if style["size"] <= 0:
            return

        w = self.viewport.width
        h = self.viewport.height
        pad = style["size"] * 2

        for lon, lat, text in labels:
            x, y = self.viewport.project(lon, lat)
            if x < -pad or x > w + pad or y < -pad or y > h + pad:
                continue
            self.draw_text(x, y, text, style)

    def draw_text(self, x, y, text, style):
        font = (self.font_family, style["size"], "bold")
        halo = style.get("halo")
        if halo:
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                self.canvas.create_text(x + dx, y + dy, text=text,
                                        fill=halo, font=font, anchor="center",
                                        tags=self.LABEL_TAG)
        self.canvas.create_text(x, y, text=text,
                                fill=style["color"], font=font, anchor="center",
                                tags=self.LABEL_TAG)

    def resolve_style(self, key):
        base = MAP_STYLE[key]
        px = (self.viewport.span_px(self.data.bbox)
              if self.data and self.data.bbox else 0)
        if px <= 0:
            size = base["min_size"]
        else:
            size = int(max(base["min_size"],
                           min(base["max_size"], px / base["size_divisor"])))
        return {**base, "size": size}


    # ==========================================================
    # 县点图层
    # ==========================================================
    
    def _point_lonlat(self, feat):
        """从 shapes_point 元素提取 (lon, lat)。当前数据格式为
        {"geometry": {"type":"Point","coordinates":[lon,lat]}, "properties": {...}}
        """
        if isinstance(feat, dict):
            geom = feat.get("geometry")
            if isinstance(geom, dict):
                c = geom.get("coordinates")
                if isinstance(c, (list, tuple)) and len(c) >= 2:
                    try:
                        return float(c[0]), float(c[1])
                    except (TypeError, ValueError):
                        return None, None
        return None, None

    def _point_radius(self, level, style):
        """按当前缩放与 level 计算县点像素半径。"""
        span = self.viewport.span_px(self.data.bbox)
        base = span / max(style.get("size_divisor", 1100), 1)
        factor = style.get("radius_by_level", {}).get(level, 1.0)
        r = base * factor
        return max(style.get("min_radius", 0.8),
                min(style.get("max_radius", 5.0), r))


    # ==========================================================
    # 道路图层
    # ==========================================================
    
    def _road_width(self, difficulty):
        """按当前缩放与 difficulty 计算道路像素宽度。"""
        style = MAP_STYLE.get("road") or {}
        if not self.data:
            return style.get("min_width", 1.0)

        span = self.viewport.span_px(self.data.bbox)
        base = span / max(style.get("width_divisor", 800), 1)

        d = max(float(difficulty or 1.0), style.get("difficulty_floor", 1.0))
        width = base / d                                   # 反相关

        return max(style.get("min_width", 0.5),
                min(style.get("max_width", 5.0), width))

    def render_roads(self):
        """绘制路网线段（不含点、不含标签）。线宽 ∝ 1/difficulty。"""
        if not LAYER_VISIBILITY.get("road", True):
                return
        style = MAP_STYLE.get("road")
        roads = getattr(self.data, "roads", None) if self.data else None
        if not style or not roads:
            return

        bounds = self._visible_bounds()
        if not bounds:
            return
        vx0, vy0, vx1, vy1 = bounds
        color = style["color"]

        # 同一缩放级别下，相同 difficulty 宽度必然相同 → 缓存避免重复计算
        width_cache = {}

        for coords, difficulty, (bx0, by0, bx1, by1) in roads:
            # 视口裁剪（bbox 粗筛）
            if bx1 < vx0 or bx0 > vx1 or by1 < vy0 or by0 > vy1:
                continue

            key = round(difficulty, 2)
            width = width_cache.get(key)
            if width is None:
                width = self._road_width(difficulty)
                width_cache[key] = width

            flat = []
            for lon, lat in coords:
                x, y = self.viewport.project(lon, lat)
                flat.append(x)
                flat.append(y)
            if len(flat) < 4:
                continue

            try:
                self.canvas.create_line(
                    *flat,
                    fill=color,
                    width=width,
                    capstyle="round",
                    joinstyle="round",
                    tags=(self.ROAD_TAG,self.LINE_TAG),
                )
            except Exception:
                pass          # 与其它 render_* 保持一致的静默策略