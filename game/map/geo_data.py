# -*- coding: utf-8 -*-
"""地图数据：加载层级化的州/郡/县数据，分类、空间查询。

数据文件 assets/map.geojson 的结构：
    states: [
      { id, name, name_coords: [[lon,lat],[lon,lat]], boundary: MultiPolygon,
        counties: [
          { id, name, name_coords: [lon,lat], capital, capital_id,
            boundary: [闭合环], cities: [{id, name, coords, is_capital, level}] }
        ] }
    ]

分类后字段（供渲染器使用，与旧版保持一致）：
    shapes_polygon / shapes_line / shapes_point   几何
    labels_state / labels_county                 标签 (lon, lat, text)
    labels_city                                  标签 (lon, lat, text, level)
    bbox                                          外接矩形

空间查询：
    find_location(lon, lat) -> (州名, 郡名, 县名)
"""

import json
import math

from game.core.utils import walk_coords, point_in_polygon


class GeoData:
    def __init__(self):
        self.shapes_polygon = []   # 州面（MultiPolygon）
        self.shapes_line = []      # 郡界（闭合线）
        self.shapes_point = []     # 县（Point，即各郡首府）
        self.shapes_water_line = []      # 河流（LineString/MultiLineString）
        self.shapes_water_polygon = []   # 湖泊（Polygon/MultiPolygon）
        self.labels_state = []
        self.labels_county = []
        self.labels_city = []
        self.bbox = None
        self.feature_count = 0

        # 空间查询缓存：(minx, miny, maxx, maxy, 名称, 外环顶点)
        self._state_index = []
        self._county_index = []

    # ---------- 构造 ----------
    @classmethod
    def from_file(cls, path):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        states = raw.get("states") or []
        data = cls()
        data._classify(states)
        data._compute_bbox()
        data._build_index()
        return data

    def load_water(self, path):
        """加载水域（河流、湖泊）GeoJSON，按尺寸分级以便按缩放显隐。"""
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        for feat in raw.get("features") or []:
            geom = feat.get("geometry") or {}
            gtype = geom.get("type")
            coords = geom.get("coordinates")
            if not gtype or not coords:
                continue
            bbox = self._coords_bbox(coords)
            props = feat.get("properties") or {}

            if gtype in ("LineString", "MultiLineString"):
                # 河流：用 bbox 对角线近似长度，作为重要性
                size = math.hypot(bbox[2] - bbox[0], bbox[3] - bbox[1])
                self.shapes_water_line.append({
                    "geometry": geom, "properties": props,
                    "bbox": bbox, "size": size,
                })
            elif gtype in ("Polygon", "MultiPolygon"):
                # 湖泊：用 bbox 面积近似大小
                size = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                self.shapes_water_polygon.append({
                    "geometry": geom, "properties": props,
                    "bbox": bbox, "size": size,
                })

        self._assign_lod(self.shapes_water_line)
        self._assign_lod(self.shapes_water_polygon)

    def load_roads(self, path):
        """加载路网 LineString，写入 self.roads。

        self.roads 每项为 (coords, difficulty, bbox)：
            coords     : [(lon, lat), ...]
            difficulty : float（缺失时默认 1.3）
            bbox       : (minx, miny, maxx, maxy)
        """
        with open(path, "r", encoding="utf-8") as fp:
            payload = json.load(fp)

        roads = []
        for feat in payload.get("features", []):
            geom = feat.get("geometry") or {}
            if geom.get("type") != "LineString":
                continue                      # 只吃线段，其它一律跳过
            coords = geom.get("coordinates") or []
            if len(coords) < 2:
                continue

            props = feat.get("properties") or {}
            try:
                difficulty = float(props.get("difficulty", 1.3))
            except (TypeError, ValueError):
                difficulty = 1.3

            roads.append((coords, difficulty, self._coords_bbox(coords)))

        self.roads = roads


    # ---------- 分类 ----------
    def _classify(self, states):
        for state in states:
            sname = state.get("name")

            # 州名标签：name_coords 是两点线段 [[lon,lat],[lon,lat]]，取中点
            nc = state.get("name_coords")
            if nc and len(nc) >= 2 and isinstance(nc[0], (list, tuple)):
                lon = (nc[0][0] + nc[-1][0]) / 2
                lat = (nc[0][1] + nc[-1][1]) / 2
                self.labels_state.append((lon, lat, sname))

            # 州面
            boundary = state.get("boundary")
            if boundary:
                self.shapes_polygon.append({
                    "geometry": {"type": "MultiPolygon", "coordinates": boundary},
                    "properties": {"州名": sname},
                    "bbox": self._coords_bbox(boundary),
                })

            # 郡
            for county in state.get("counties") or []:
                self._classify_county(sname, county)

        self.feature_count = (
            len(self.labels_state)
            + len(self.labels_county)
            + len(self.labels_city)
        )

    def _classify_county(self, sname, county):
        cname = county.get("name")

        # 郡名标签：name_coords 是单点 [lon, lat]
        nc = county.get("name_coords")
        if nc and len(nc) == 2 and isinstance(nc[0], (int, float)):
            self.labels_county.append((nc[0], nc[1], cname))

        # 郡界（闭合线，首点 == 末点）
        boundary = county.get("boundary")
        if boundary:
            self.shapes_line.append({
                "geometry": {"type": "LineString", "coordinates": boundary},
                "properties": {"州名": sname, "郡名": cname},
                "bbox": self._coords_bbox(boundary),
            })

        # 县（首府）
        for city in county.get("cities") or []:
            coords = city.get("coords")
            name = city.get("name")
            if coords and name:
                self.shapes_point.append({
                    "geometry": {"type": "Point", "coordinates": coords},
                    "properties": {"县名": name},
                })
                level = int(city.get("level", 5))
                level = max(1, min(10, level))   # 钳制到 1–10，防止脏数据越界
                self.labels_city.append((coords[0], coords[1], name, level))

    # ---------- 外接矩形 ----------
    def _compute_bbox(self):
        lons, lats = [], []
        for feat in self.shapes_polygon + self.shapes_line + self.shapes_point:
            coords = feat["geometry"]["coordinates"]
            for lon, lat in walk_coords(coords):
                lons.append(lon)
                lats.append(lat)
        if lons:
            self.bbox = (min(lons), min(lats), max(lons), max(lats))

    # ---------- 空间索引 ----------
    def _build_index(self):
        self._state_index = []
        for feat in self.shapes_polygon:
            name = feat["properties"]["州名"]
            for polygon in feat["geometry"]["coordinates"]:  # MultiPolygon
                if not polygon or len(polygon[0]) < 3:
                    continue
                ring = polygon[0]
                self._state_index.append((self._ring_bbox(ring), name, ring))

        self._county_index = []
        for feat in self.shapes_line:
            name = feat["properties"]["郡名"]
            ring = feat["geometry"]["coordinates"]
            if len(ring) < 3:
                continue
            self._county_index.append((self._ring_bbox(ring), name, ring))

    @staticmethod
    def _ring_bbox(ring):
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return (min(xs), min(ys), max(xs), max(ys))

    @staticmethod
    def _coords_bbox(coords):
        """任意嵌套坐标的外接矩形。"""
        xs, ys = [], []
        for lon, lat in walk_coords(coords):
            xs.append(lon)
            ys.append(lat)
        return (min(xs), min(ys), max(xs), max(ys))

    @staticmethod
    def _assign_lod(features):
        """按 size 从大到小分四档赋 min_scale（越大越早显示）。"""
        if not features:
            return
        feats = sorted(features, key=lambda f: -f["size"])
        n = len(feats)
        for i, f in enumerate(feats):
            pct = i / n
            if pct < 0.15:
                f["min_scale"] = 0
            elif pct < 0.40:
                f["min_scale"] = 15
            elif pct < 0.70:
                f["min_scale"] = 45
            else:
                f["min_scale"] = 100

    # ---------- 查询 ----------
    def find_state_at(self, lon, lat):
        for (minx, miny, maxx, maxy), name, ring in self._state_index:
            if minx <= lon <= maxx and miny <= lat <= maxy \
                    and point_in_polygon(lon, lat, ring):
                return name
        return None

    def find_county_at(self, lon, lat):
        for (minx, miny, maxx, maxy), name, ring in self._county_index:
            if minx <= lon <= maxx and miny <= lat <= maxy \
                    and point_in_polygon(lon, lat, ring):
                return name
        return None

    @staticmethod
    def find_nearest_label(lon, lat, candidates, max_dist):
        """在候选标签里找距离最近的，超过 max_dist 就返回 None。"""
        best, best_d = None, max_dist
        for c in candidates:
            l_lon, l_lat, name = c[0], c[1], c[2]
            d = math.hypot(l_lon - lon, l_lat - lat)
            if d < best_d:
                best_d, best = d, name
        return best

    def find_location(self, lon, lat):
        """返回 (州名, 郡名, 县名)，没有的为 None。

        州/郡用点在多边形内判断（新数据有准确的州面、郡面），
        县用最近标签 + 距离上限（县只有首府一个点）。
        """
        state = self.find_state_at(lon, lat)
        county = self.find_county_at(lon, lat)
        city = self.find_nearest_label(lon, lat, self.labels_city, 0.4)
        return state, county, city
