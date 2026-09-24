# 暗耻三国志 — 项目说明文档

> 本轮更新重点：**县界多边形反查县名**（hover 显示州 · 郡 · 县）、修复 **`polygon.fill = "#"` 导致州界渲染静默失败**、记录 **Tk 线宽整数取整** 行为。新增 §9.4 变更日志。

---

## 1. 项目概述

| 项 | 内容 |
|---|---|
| 项目名称 | 暗耻三国志（`APP_TITLE`） |
| 定位 | 三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》 |
| 程序入口 | `main.py` → `MainWindow().run()` |
| 核心功能 | 中国全图矢量渲染（州/郡/县三级边界 + 道路路网 + 水域湖泊/河流）、鼠标缩放平移、**光标精确反查州/郡/县**、旬回合制时钟、顶部信息栏与菜单、右侧 Tab 面板框架、多 Tab 设置窗口、剧本系统、势力关系分组展示、**郡面势力染色（唯一着色图层）** |
| 运行环境 | Python 3 + 标准库 `tkinter`。仅依赖标准库，**无第三方依赖、无 requirements.txt** |
| 数据来源 | `assets/map.geojson`：13 州 / 106 郡 / 1372 据点（`states → counties → cities`；**据点新增 `boundary` 字段**）；`assets/roads.geojson`：约 600 条道路；`assets/water.geojson`：205 条河流/湖泊；`assets/mountains.geojson`：42 个山地区块（未接入） |
| 剧本来源 | `scenarios/default.json` |
| 用户数据 | `userdata/settings.json` |
| 平台 | Windows 优先 |

**当前完成度**：

- ✅ 地图查看器（州/郡/县三级**边界**渲染 + 道路 + 水域 + 图层显隐 + 县点四级样式 + 县名避让）
- ✅ **县界渲染**（黑色虚线，按 bbox 尺寸分级显隐）
- ✅ **几何层去色**（州 / 郡 / 县三级边界均黑色描边，州面不填充）
- ✅ **郡面势力染色**（地图上**唯一**的着色图层）
- ✅ **hover 精确反查**：鼠标滑过显示 `州 · 郡 · 县`
- ✅ 多 Tab 设置系统（外观 tab 有内容，操作/游戏 tab 空骨架）
- ✅ 剧本系统
- ✅ 势力面板分组列表
- ⚠️ 回合与资源为骨架
- ❌ 内政/军事/外交/存档均为空实现

---

## 2. 文件结构清单

```
san9edit/
├── main.py
├── README.md
├── assets/
│   ├── map.geojson                 city 带 boundary
│   ├── roads.geojson
│   ├── water.geojson
│   └── mountains.geojson           未接入
├── scenarios/
│   └── default.json
├── userdata/
│   └── settings.json
└── game/
    ├── config/
    │   ├── constants.py
    │   ├── style.py
    │   ├── settings_manager.py
    │   └── settings_schema.py
    ├── core/
    │   ├── game_state.py
    │   ├── utils.py
    │   ├── faction.py
    │   ├── character.py
    │   ├── node.py
    │   ├── world.py
    │   ├── scenario.py
    │   └── territory.py
    ├── map/
    │   ├── geo_data.py             ★ 本轮：新增 _city_index / find_city_at
    │   ├── viewport.py
    │   └── renderer.py
    └── ui/
        ├── main_window.py
        ├── top_bar.py
        ├── status_bar.py           本轮未改（已天然支持三段显示）
        ├── map_canvas.py           本轮未改（已天然支持三段拼接）
        ├── side_panel.py
        ├── settings_window.py
        ├── window_utils.py
        ├── widgets/collapsible.py
        └── panels/
            ├── faction_panel.py
            ├── node_panel.py
            ├── character_panel.py
            └── troop_panel.py
```

**依赖方向单向**：`main → ui → core/map → config`。

---

## 3. 核心数据模型

### 3.1 三层 ID 编码

州 2 位 / 郡 4 位 / 据点 6 位。

### 3.2 势力（Faction）

`id` = 君主人物 id。字段：`id` / `name` / `color` / `prestige` / `gold` / `food` / `stance`。
`stance_label()` → `"敌对"` / `"盟友"` / `"中立"`。

### 3.3 人物（Character）

四位 id，五维。

### 3.4 据点（Node）

**静态字段**（来自 `map.geojson`）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | str | 六位 |
| `name` | str | 名称 |
| `coords` | tuple | `(lon, lat)` |
| `type` | str | `县`/`关隘`/`渡口/津`/`仓/监`/`谷`/`山地` |
| `level` | int | 1（最大）–10（最小） |
| `is_capital` | bool | 是否郡治 |
| `boundary` | list | 闭合环 `[(lon,lat), ...]`，**全部据点都有**（含关隘/仓/谷/山地，部分为极小多边形） |

**动态字段**（剧本覆盖）：`owner` / `troops` / `gold` / `food`。

**属性**：`state_id` / `county_id` / `is_owned()`。

### 3.5 游戏世界（World）

聚合容器，`factions` / `characters` / `nodes`。

### 3.6 剧本加载器（ScenarioLoader）

`ScenarioLoader.load(path, geo_data)` → `World`。

### 3.7 郡级控制力统计（CountyStat）

**渲染层专用**。控制力算法：

```
单据点权重 = (11 - level)
郡治据点再 × 2.0
郡内总控制力 = Σ 权重(全部据点，含无主)
势力值 = 控制力_F / 总控制力
ratio > 0.8   → 主导势力（郡面用原色）
0.5 < ratio ≤ 0.8 → 主要势力（郡面用变浅色）
其余          → 郡面不上色
```

### 3.8 县界（CityBoundary）

**渲染层 + 查询层共用**，由 `GeoData.shapes_city_boundary` 承载。每个元素：

| 字段 | 类型 | 说明 |
|---|---|---|
| `geometry` | dict | `{"type": "LineString", "coordinates": [ring]}` |
| `properties` | dict | `{id, 县名, type, level}` |
| `bbox` | tuple | `(min_lon, min_lat, max_lon, max_lat)` |
| `size` | float | bbox 对角线长度 |
| `min_scale` | float | `_assign_lod` 赋的显示阈值（0/15/45/100 四档） |

### 3.9 县界空间索引（CityIndex）

**本轮新增**。`GeoData._city_index`，结构 `(bbox, 名称, 外环顶点)`，与 `_state_index` / `_county_index` 同构。

- 构建：`_build_index` 末尾调 `_build_city_index`
- 用途：`find_city_at(lon, lat)` 用 `point_in_polygon` 精确反查县名
- 只收 `shapes_city_boundary` 中 `boundary` 顶点 ≥ 3 的项

---

## 4. 数据格式参考

### 4.1 `assets/map.geojson` 实际结构

```json
{
  "states": [{
    "id": "01", "name": "并州",
    "name_coords": [[lon,lat],[lon,lat]],
    "boundary": [[[ [lon,lat], ... ]]],        // 州面
    "counties": [{
      "id": "0101", "name": "上党郡",
      "name_coords": [lon, lat],
      "capital": "长子", "capital_id": "010101",
      "boundary": [[lon,lat], ...],             // 郡界
      "cities": [{
        "id": "010101", "name": "长子",
        "coords": [lon, lat],
        "is_capital": true, "level": 3, "type": "县",
        "boundary": [[lon,lat], ...]            // 县/据点边界
      }]
    }]
  }]
}
```

**注意**：

- `boundary` 在**所有** type 的 city 上都存在
- 非 `县` 类型的 `boundary` 常常是极小的圆环（关隘 / 仓 / 谷 / 山地），视觉上接近一个点
- `fill` 在 `style.py` 里是**空串 `""`**（Tk 合法的"不填充"），**不是 `"#"`**

### 4.2 `type` 枚举

`县` / `关隘` / `渡口/津` / `仓/监` / `谷` / `山地`。

### 4.3 `scenarios/default.json` 结构

version 1。字段与前一版一致。

---

## 5. 模块与函数清单

### 5.1 `main.py`

`main()` → `MainWindow().run()`。

### 5.2 `game/config/constants.py`

路径常量：`ASSETS_DIR` / `DEFAULT_MAP_PATH` / `DEFAULT_WATER_PATH` / `DEFAULT_ROADS_PATH` / `SCENARIOS_DIR` / `DEFAULT_SCENARIO_PATH` / `APP_TITLE` / `MIN_WINDOW_SIZE`。

### 5.3 – 5.9

`faction.py` / `character.py` / `node.py` / `world.py` / `scenario.py` / `game_state.py` / `utils.py` **未改动**。

`utils.lighten_color(hex_color, factor=0.4)` / `darken_color(hex_color, factor=0.5)`：向白 / 黑线性插值。

### 5.10 `game/core/territory.py`

`CountyStat` 数据类 + `compute_county_stats(world)` + `CAPITAL_BONUS = 2.0`。渲染层专用，不进 `World`。

### 5.11 `game/map/geo_data.py`（★ 本轮改动）

#### 容器

```python
self.shapes_polygon = []          # 州面
self.shapes_line = []             # 郡界
self.shapes_point = []            # 据点（Point）
self.shapes_city_boundary = []    # ★ 县界（闭合 ring）
self.shapes_water_line = []
self.shapes_water_polygon = []
self.labels_state = []            # [(lon, lat, 州名)]
self.labels_county = []           # [(lon, lat, 郡名, 郡id)]
self.labels_city = []             # [(lon, lat, 县名, level, 据点id)]
self.bbox = None
self.roads = []
self._state_index = []            # [(bbox, 州名, ring)]
self._county_index = []           # [(bbox, 郡名, ring)]
self._city_index = []             # ★ 本轮新增：[(bbox, 县名, ring)]
```

#### `from_file`

```python
@classmethod
def from_file(cls, path):
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    states = raw.get("states") or []
    data = cls()
    data._classify(states)
    data._assign_lod(data.shapes_city_boundary)   # ★
    data._compute_bbox()
    data._build_index()
    return data
```

#### `_classify_county`

在 `labels_city.append(...)` 之后：

```python
boundary = city.get("boundary")
if boundary and len(boundary) >= 3:
    b = self._coords_bbox(boundary)
    size = math.hypot(b[2] - b[0], b[3] - b[1])
    self.shapes_city_boundary.append({
        "geometry": {"type": "LineString", "coordinates": boundary},
        "properties": {
            "id": city.get("id"),
            "县名": name,
            "type": city.get("type", "县"),
            "level": level,
        },
        "bbox": b,
        "size": size,
    })
```

#### `_build_index`（★ 本轮新增一步）

```python
def _build_index(self):
    # ... 现有 state / county 索引 ...
    self._build_city_index()      # ★ 新增

def _build_city_index(self):
    """县界多边形索引。只收有 boundary 的项。"""
    self._city_index = []
    feats = getattr(self, "shapes_city_boundary", None) or []
    for feat in feats:
        ring = feat["geometry"]["coordinates"]
        if len(ring) < 3:
            continue
        name = feat["properties"].get("县名")
        if not name:
            continue
        self._city_index.append((feat["bbox"], name, ring))
```

#### 查询（★ 本轮新增 + 修改）

```python
def find_city_at(self, lon, lat):
    """按县界多边形反查县名。多个命中取 bbox 面积最小的。"""
    best_name = None
    best_area = None
    for (minx, miny, maxx, maxy), name, ring in self._city_index:
        if not (minx <= lon <= maxx and miny <= lat <= maxy):
            continue
        if not point_in_polygon(lon, lat, ring):
            continue
        area = (maxx - minx) * (maxy - miny)
        if best_area is None or area < best_area:
            best_area, best_name = area, name
    return best_name

def find_location(self, lon, lat):
    """返回 (州名, 郡名, 县名)，没有的为 None。

    三级全部多边形反查；县界查不到时退回最近标签兜底。
    """
    state  = self.find_state_at(lon, lat)
    county = self.find_county_at(lon, lat)
    city   = self.find_city_at(lon, lat)                              # ★ 精确
    if city is None:
        city = self.find_nearest_label(lon, lat, self.labels_city, 0.4)  # 兜底
    return state, county, city
```

**兜底的必要性**：非"县"类型的 boundary 是极小圆环，鼠标几乎不可能落进去；`find_nearest_label` 接住这种情况。

### 5.12 `game/map/viewport.py`

未改动。`project` / `unproject` / `fit_to_bbox` / `zoom` / `pan_pixels` / `span_px`。

### 5.13 `game/map/renderer.py`

#### 类常量

```python
LABEL_TAG     = "label"
WATER_TAG     = "water"
ROAD_TAG      = "road"
POLYGON_TAG   = "polygon"
LINE_TAG      = "line"
POINT_TAG     = "point"
TERRITORY_TAG = "territory"
CITY_TAG      = "city"          # 县界

_LAYER_ORDER = (
    "polygon",      # 州面（透明填充 + 黑描边）
    "city",         # 县界（黑虚线）
    "territory",    # 郡面势力染色（唯一的着色层）
    "water",
    "road",
    "line",         # 郡界（黑实线）
    "point",
    "label",
)
```

#### 方法

| 方法 | 说明 |
|---|---|
| `set_data(geo_data)` | 注入数据 |
| `set_world(world)` | 注入 World，触发 `_county_stats` 重算；**不负责重绘** |
| `draw_full()` | 全量重绘 |
| `pan(dx, dy)` / `zoom(f, mx, my)` | canvas 变换；`_cum_scale` 越界时 `draw_full` |
| `refresh_dynamic()` | 重建动态层（水/路/点/标签），末尾 `_restack` |
| `_restack()` | 用 `tag_raise` 从底到顶一遍，空图层免疫 |
| `_draw_geometry()` | `render_polygons → render_city_boundaries → render_territory → render_lines` |
| `render_polygons()` / `render_polygon(feat)` | 州面（透明 + 黑描边，`width = base["width"]`） |
| **`render_city_boundaries()`** | 县界：只画黑色虚线轮廓，`create_line` + `dash` |
| `render_territory()` | 郡面染色，`outline=color` 避免亚像素缝 |
| `render_lines()` / `render_line(feat)` | 郡界 |
| `render_points()` / `render_point(...)` | 县点 |
| `render_state_labels()` | 州名 |
| `render_county_labels()` | 郡名（**不再随势力着色**） |
| `render_city_labels()` | 县名（**不再随势力着色**） |
| `render_label_group(labels, style_key)` | 通用标签绘制（州名用） |
| `draw_text(x, y, text, style)` | 单条文字 + halo |
| `resolve_style(key)` | 按当前 `span_px` 决定字号 |
| `_visible_bounds(margin_px=20)` | 视口经纬度范围 |
| `_point_lonlat(feat)` / `_point_radius(level, style)` | 县点辅助 |
| `_road_width(difficulty)` / `render_roads()` | 道路 |
| `render_water_polygons()` / `render_water_lines()` | 水域 |

**已删除的方法**：`_county_label_color` / `_city_label_color`（不再随势力着色）。

### 5.14 `game/ui/main_window.py`

未改动。`_auto_load_default` → `load_geojson` + `_load_default_scenario`；`_load_default_scenario` 里调 `renderer.set_world(world)` + `map_canvas.redraw()`。

### 5.15 – 5.19

`top_bar.py` / `side_panel.py` / `panels/*` **未改动**。

### 5.20 `game/config/style.py`（当前生效值）

```python
MAP_STYLE = {
    "polygon": {
        "fill":    "",           # 空串 = 不填充（★ 关键：不能写成 "#"）
        "outline": "#000000",
        "width":   4,            # 州界最粗
    },
    "line": {
        "color": "#000000",      # 郡界黑实线
        "width": 1,              # ★ 建议整数（Tk 取整到像素）
    },
    "city_line": {
        "color": "#000000",
        "width": 1,
        "dash": (3, 3),          # 虚线
    },
    "road": { ... },
    "point": { ... },
    "water_polygon": { ... },
    "water_line": { ... },
    "territory": {
        "major_fade": 0.4,
    },
    "label_state": {
        "color": "#1A1A1A", "halo": "#FFFFFF",
        "size_divisor": 55, "min_size": 11, "max_size": 44,
        "min_scale": 0, "max_scale": 40,
    },
    "label_county": {
        "color": "#000000", "halo": "#FFFFFF",   # ★ 不随势力
        "size_divisor": 105, "min_size": 9, "max_size": 22,
        "min_scale": 12, "max_scale": 150,
    },
    "label_city": {
        "color": "#000000", "halo": "#FFFFFF",   # ★ 不随势力
        "size_divisor": 140, "min_size": 8, "max_size": 16,
        "min_scale": 30,
        "point_gap": 6,
    },
}

LAYER_VISIBILITY = {
    "polygon":      True,
    "city":         True,     # 县界
    "line":         True,     # 郡界
    "point":        True,
    "road":         True,
    "water":        False,
    "mountain":     False,
    "label_state":  True,
    "label_county": True,
    "label_city":   True,
    "territory":    True,
}
```

**视觉分层总结**：

| 层 | 线型 | 颜色 | 宽度 | 备注 |
|---|---|---|---|---|
| 州界 | 实线 | 黑 | 4 | 最粗 |
| 郡界 | 实线 | 黑 | 1 | |
| 县界 | 虚线 | 黑 | 1 | |
| 郡面染色 | 实心面 | 势力色 | — | 唯一着色层 |
| 县点 / 标签 | — | 黑 / 深灰 | — | 不随势力变化 |

### 5.21 `game/config/settings_schema.py`

**`GROUPS`**：

- `theme` / `font` （restart = True）
- `polygon` / `line` / `city` / `point` / `road` / `water`
- `label_state` / `label_county` / `label_city`
- `lod`
- `territory`
- `visibility`

**`ITEMS`（与 `style.py` 对应的关键项）**：

| path | group | type | label | 范围 |
|---|---|---|---|---|
| `MAP_STYLE.polygon.outline` | polygon | color | 州面描边色 | — |
| `MAP_STYLE.polygon.width` | polygon | int | 描边宽度 | 0–20 |
| `MAP_STYLE.line.color` | line | color | 郡界颜色 | — |
| `MAP_STYLE.line.width` | line | int | 线宽 | 0–8 |
| `MAP_STYLE.city_line.color` | city | color | 县界轮廓色 | — |
| `MAP_STYLE.city_line.width` | city | int | 轮廓线宽 | 0–8 |
| `LAYER_VISIBILITY.city` | visibility | bool | 县界（虚线轮廓） | — |
| ... | | | | |

**已删除的 ITEM**（无消费方且会触发 `#` 报错）：

- `MAP_STYLE.polygon.fill`
- `MAP_STYLE.city_polygon.fill`

---

## 6. 程序完整运行流程

### 6.1 启动阶段

```
python main.py
└─ MainWindow()
   ├─ SettingsManager().apply()
   ├─ GameState()
   ├─ TopBar / MapCanvas / SidePanel / StatusBar
   └─ root.after(120, _auto_load_default)
```

### 6.2 地图 + 剧本加载流程

```
_auto_load_default()
├─ load_geojson(assets/map.geojson)
│  └─ GeoData.from_file
│     ├─ _classify → shapes_polygon / shapes_line / shapes_point
│     │              + shapes_city_boundary + labels_*
│     ├─ _assign_lod(shapes_city_boundary)
│     ├─ _compute_bbox
│     └─ _build_index → _build_city_index()   ★
│  └─ MapCanvas → renderer.set_data → draw_full
│
└─ _load_default_scenario()
   ├─ ScenarioLoader.load → World
   ├─ game_state.sync_from_world(world)
   ├─ renderer.set_world(world)
   └─ map_canvas.redraw()
```

### 6.3 主循环交互

| 触发 | 调用链 |
|---|---|
| 鼠标移动 | `_on_motion` → 40ms 节流 `_process_motion` → `viewport.unproject` → `data.find_location(lon, lat)` → `status_bar.set_location(text)` |
| 滚轮 / 拖拽 | `viewport.zoom / pan_pixels` → `renderer.zoom / pan` |
| 顶部信息栏 | 200ms 轮询 `game_state.get_display_items()` |
| 设置保存 | `_on_settings_applied` → 地图相关则 `map_canvas.redraw()` |

**hover 反查链（本轮）**：

```
_process_motion
  ├─ lon, lat = viewport.unproject(x, y)
  ├─ state, county, city = data.find_location(lon, lat)
  │    ├─ find_state_at  → _state_index  + point_in_polygon
  │    ├─ find_county_at → _county_index + point_in_polygon
  │    ├─ find_city_at   → _city_index   + point_in_polygon   ★ 新增
  │    └─ city 为 None 时 → find_nearest_label(labels_city, 0.4) 兜底
  └─ parts = [p for p in (state, county, city) if p]
     text = " · ".join(parts) + "   （lon°E, lat°N）"
```

### 6.4 模块协作关系

```
main.py
└─ ui.main_window ──┬─ config.settings_manager ─ config.style
                    │                            └ config.settings_schema
                    ├─ core.game_state
                    ├─ core.scenario ─────── core.world ─── core.faction / character / node
                    ├─ ui.top_bar
                    ├─ ui.status_bar
                    ├─ ui.map_canvas ─── map.viewport
                    │                   map.renderer ─── map.geo_data ── core.utils
                    │                                  └ core.territory
                    ├─ ui.settings_window
                    └─ ui.side_panel ──── panels.faction_panel / node_panel / character_panel / troop_panel
                       config.constants
```

---

## 7. 全局变量与配置项

### 7.1 `constants.py`

| 常量 | 值 |
|---|---|
| `MIN_WINDOW_SIZE` | `(1024, 640)` |
| `APP_TITLE` | `"暗耻三国志"` |
| `DEFAULT_MAP_PATH` | `assets/map.geojson` |
| `DEFAULT_WATER_PATH` | `assets/water.geojson` |
| `DEFAULT_ROADS_PATH` | `assets/roads.geojson` |
| `SCENARIOS_DIR` | `scenarios/` |
| `DEFAULT_SCENARIO_PATH` | `scenarios/default.json` |

### 7.2 设置窗口可改

| 项 | 需重启 |
|---|---|
| `THEME` / `FONT_SIZES` / `FONT_CANDIDATES` | 是 |
| `MAP_STYLE.*` 其余 | 否 |
| `LAYER_VISIBILITY.*` | 否 |

**已从设置窗口移除**：`MAP_STYLE.polygon.fill`、`MAP_STYLE.city_polygon.fill`。

### 7.3 代码内常量

| 位置 | 值 | 含义 |
|---|---|---|
| `MapCanvas._MIN_VALID_SIZE` | `10` | 布局未完成阈值 |
| `TopBar._REFRESH_INTERVAL_MS` | `200` | 信息栏轮询 |
| `MapRenderer._LAYER_ORDER` | 见 §5.13 | 图层底→顶 |
| `GeoData._assign_lod` 四档 | `0 / 15 / 45 / 100` | 所有 LOD 图层共用 |
| `MAP_STYLE.city_line.dash` | `(3, 3)` | 虚线节奏（tuple，不入设置项） |
| `MAP_STYLE.polygon.width` 上限 | `20` | 设置窗口允许的最大值 |
| `find_city_at` 复杂度 | O(n) + point_in_polygon | n = 1372，节流 40ms 下可接受 |
| hover 节流 | `40 ms` | `_process_motion` |
| 标签刷新节流 | `30 ms` | `_schedule_label_refresh` |
| settle redraw | `180 ms` | 滚轮静默后补绘 |

---

## 8. 已知逻辑限制与待完善清单

### 8.1 未实现功能

| 入口 | 现状 |
|---|---|
| 存档 / 新游戏 / 读档 | 提示"尚未实现" |
| 内政 / 军事 / 外交 | 空实现 |
| 外交交互 | 只有 `stance` 字段 |
| 部队面板 | 只清空 |
| `type` 决定能力 | 未区分 |
| 设置窗口「操作」「游戏」tab | 骨架 |
| 县界 / 郡面 hover | 不做（县界不做 hover 高亮） |
| `dash` 可调 | 不支持（tuple path） |

### 8.2 数据层缺失

- `GameState` 只有日期 + 玩家势力 + 3 项资源
- `mountains.geojson` 未接入
- 路网无拓扑关联
- 势力间无关系矩阵

### 8.3 逻辑与性能限制

（承接前一版 1–73 条，本轮新增 74–80）

1. `render_lines` / `render_city_boundaries` 全量遍历 + bbox 粗筛
2. `<Configure>` 全量重绘
3. 绘制方法外层 `except Exception: pass` ← **本轮暴露重大风险，见第 74 条**
4. 标签不做视口预筛
5. 空间索引线性扫描
6. `_build_index` 只取外环
7. 县名匹配 0.4° 兜底距离
8. `midpoint_of_line` 死代码
9. Tab 索引硬编码
10. `FactionPanel` 无选中交互
11. `WINDOW_SIZE` 定义未用
12. `_cum_scale` 周期性全量重绘
13. 无测试 / 打包 / lint
14. 道路无 LOD
15. 动态图层重建 + tag_lower 开销
16. `CITY_LEVEL_MIN_SCALE` 硬编码
17. `*_by_level` 表同问题
18. 县点与县名"同显同隐"两处判断
19. `_drawn` 置位时机是易错点
20. `refresh_dynamic` 绘制顺序 → `_LAYER_ORDER` 表达
21. `shapes_point` 的 `level` 解析必须先于 `append`
22. 静态层依赖 `draw_full`
23. `_cum_scale` 触发点是"当前视图"
24. 拖拽路径不做静态层补画
25. `SettingsManager.apply()` 必须就地修改
26. `SettingsManager` 必须在 `MainWindow.__init__` 早期创建
27. `theme` / `font` 的 `restart=True` 硬编码
28. `ITEMS` 与 `style.py` 结构必须一致
29. `level_table` 的 draft key 是 `path.LEVEL`
30. 设置保存 / 关闭路径必须走 `_do_destroy()`
31. `hidden=True` 要在 `_populate` / `_apply_filter` 两处都跳过
32. `water.geojson` 加载 `except: pass`
33. `LAYER_VISIBILITY.water` 默认 `False`
34. 县名避让偏移与 `_point_radius` 同源
35. 县点放大三字段联动
36. 外环绘制顺序：先外环再主体
37. 空心 / 外环用不同描边
38. `update_idletasks()` 不在 `<Configure>` 里调
39. 设置窗口滚轮用 `bind` 递归
40. `scrollregion` 用 `winfo_reqheight()`
41. 多 Tab 结构下 `_apply_filter` 按"当前 tab"作用
42. `center_on_parent` 分多轮延迟
43. 方法缩进事故高发
44. `tag_lower(A, B)` 的 `B` 必须非空
45. `load_geojson` 必须在 `reset_view()` 之前保存 `self._geo_data`
46. 剧本加载依赖 `shapes_point` 的 `id` 字段
47. 势力 id = 君主 id 是硬约定
48. `GameState.__init__` 处于"未初始化"状态
49. `change_gold/food/prestige` 双路径
50. `tag_lower(A, B)` 的 `belowThis` 参数 B 必须非空
51. `_restack()` 用 `tag_raise`
52. 图层"内容"与层序解耦
53. `FactionPanel.__init__` 先调一次 `refresh()`
54. `FactionPanel._bucket_factions` 是纯函数
55. `stance` 默认 0
56. ★ `settings_schema.ITEMS` 每项必须含 `group`
57. ★ `SettingsManager` 只支持"名字.子键"或"顶层字典"，不支持裸标量和 tuple
58. ★ `labels_county` 是四元组、`labels_city` 是五元组
59. ★ `render_territory` 的 `outline=color` 是刻意的
60. ★ `set_world` 不负责重绘
61. ★ `CountyStat` 是渲染层缓存
62. ★ 无主据点计入控制力分母
63. ★ `style.py` 里 `LAYER_VISIBILITY` 段注释和缩进不齐
64. ★ **`MAP_STYLE.polygon.fill = ""` 是合法的"不填充"值，但不是合法颜色值**。任何 `color` 类型设置项读到空串会构出 `"#"`，Tk 拒收（`TclError: invalid color name "#"`）。**修法：这类无意义的 color 设置项从 `settings_schema.ITEMS` 删掉**
65. ★ **`city_polygon` 段已彻底移除**，`style.py` 里不能再有
66. ★ **县界是 `CITY_TAG` 下的独立图层**，位于 `polygon` 与 `territory` 之间。有主郡的县界虚线会被染色覆盖；若要共存，把 `"city"` 移到 `"territory"` 之后
67. ★ **`shapes_city_boundary` 收集所有 type**：非县类型的极小 boundary 视觉上接近一个点
68. ★ **县界 LOD 与水域共用 `_assign_lod`**：四档 `0 / 15 / 45 / 100`
69. ★ **`render_city_boundaries` 用 `create_line` 而非 `create_polygon`**：Tk polygon 不支持 `dash`
70. ★ **`render_city_labels` 解包变量 `cid` 无人消费但不能删**（五元组）
71. ★ **`render_county_labels` / `render_city_labels` 都不再查势力色**
72. ★ **州 / 郡 / 县三级边界区分靠粗细与虚实**：州 4px 实线、郡 1px 实线、县 1px 虚线，全黑
73. ★ **州界宽度在设置窗口内受 `max` 限制**，要改上限只能改 `settings_schema.ITEMS` 里的 `max`
74. ★ **`render_polygons` / `render_lines` 的 `except Exception: pass` 是重大排查障碍**。症状："改 `polygon.width` 毫无效果"。真因：`MAP_STYLE.polygon.fill = "#"` → `create_polygon` 抛 `TclError` → 被静默吞 → **整个 polygon 层一个都没画出来**。用户看到的"州界"其实是 `line` 层的郡界。**修法**：① `fill` 写成 `""`（空串）；② 给每个 `render_*` 的 except 加"每种异常只打印一次"的调试日志（见 §8.4 第 1 条）
75. ★ **Tk 线宽取整到整数像素**：`1.00 ~ 1.49 → 1px`，`1.50 ~ 2.49 → 2px`。所以 `width = 1.42` 和 `1.5` 视觉差别巨大。**写浮点无意义，`MAP_STYLE.line.width` / `polygon.width` 直接用整数**
76. ★ **`_city_index` 与 `_state_index` / `_county_index` 同构**：`(bbox, 名称, ring)` 三元组列表，构建在 `_build_index` 里
77. ★ **`find_city_at` 多命中取 bbox 面积最小者**：极小 boundary（关隘/仓/谷/山地）套在县内时，命中县界和极小环两者，取面积小的那个更精确
78. ★ **`find_location` 的县查询是"精确优先 + 最近兜底"**：`find_city_at` 命中则用精确值；否则 `find_nearest_label(labels_city, 0.4)` 兜底接住极小 boundary 的据点
79. ★ **hover 反查是 O(n) 线性 + 40ms 节流**：1372 项 bbox 比较，纯 Python 完全够用，无需额外空间结构
80. ★ **UI 层（`map_canvas` / `status_bar`）对县名显示"零改动"**：`_process_motion` 早已是 `" · ".join(parts)` + `None` 段跳过，`find_location` 一返回县名，状态栏自动补上

### 8.4 建议的下一步

1. **给 `render_*` 的 `except` 加"首次异常打印"**（防止第 74 条重演）：

```python
_warned = set()   # 类属性

def render_polygons(self):
    min_lon, min_lat, max_lon, max_lat = self._visible_bounds()
    for feat in self.data.shapes_polygon:
        b = feat["bbox"]
        if b[2] < min_lon or b[0] > max_lon or b[3] < min_lat or b[1] > max_lat:
            continue
        try:
            self.render_polygon(feat)
        except Exception as e:
            key = type(e).__name__
            if key not in MapRenderer._warned:
                MapRenderer._warned.add(key)
                print(f"[renderer] {key}: {e}")
```

`render_lines` / `render_city_boundaries` / `render_points` 同理。

2. **决定县界与染色层的相对位置**（见第 66 条）
3. 回合流程
4. 据点点击详情
5. 人物面板联动
6. 势力面板交互
7. 外交入口（改 `stance`）
8. 接入 `mountains.geojson`
9. `type` 能力矩阵
10. 存档系统
11. 新游戏流程
12. 县界样式细化：`dash` 可调、区分据点 type、hover 高亮

---

## 9. 变更日志

### 9.1 前两轮（摘要）

剧本系统 + 外交分组 + 层序修复。术语：武将→人物 / 城市→据点 / 势力 id = 君主人物 id。

### 9.2 势力染色（第三轮）

`game/core/territory.py` + `CountyStat` + `compute_county_stats`；`MAP_STYLE.territory.major_fade`；`LAYER_VISIBILITY.territory`；`render_territory()`；`set_world(world)`。

### 9.3 县界渲染 + 几何层去色（第四轮）

**新增**：

- `GeoData.shapes_city_boundary`
- `MapRenderer.CITY_TAG` + `render_city_boundaries()`
- `_LAYER_ORDER` 插入 `"city"`（`polygon` 与 `territory` 之间）
- `style.py` 里 `MAP_STYLE.city_line` + `LAYER_VISIBILITY.city`
- `settings_schema` 里 `city` 分组 + 3 条 ITEM

**修改**：

- `MAP_STYLE.polygon.fill = ""` / `outline = "#000000"` / `width = 4`
- `MAP_STYLE.line.color = "#000000"`
- `MAP_STYLE.label_county.color = "#000000"`
- `MAP_STYLE.label_city.color = "#000000"`
- `MAP_STYLE.polygon.width` 的 `max` 从 `8` → `20`
- `LAYER_VISIBILITY.city` 的 label → `"县界（虚线轮廓）"`

**删除**：

- `render_county_labels` / `render_city_labels` 里的换色调用
- `_county_label_color` / `_city_label_color` 方法
- `MAP_STYLE.city_polygon` 整段
- `MAP_STYLE.polygon.fill` / `MAP_STYLE.city_polygon.fill` 两条 ITEM

**修复**：

- `TclError: invalid color name "#"`（`settings_schema` 删掉两条无意义的 color 项）

**设计决策**：

- 几何层只留黑边，着色全交 `territory`
- 三级边界用粗细与虚实区分：州 4px 实线、郡 1px 实线、县 1px 虚线
- 县界不做面填充
- 县界范围 = 所有 type
- 县界 LOD 复用 `_assign_lod`
- 标签去势力色

### 9.4 本轮 · hover 反查县名 + 州界渲染修复

#### 新增

- **`game/map/geo_data.py`**：
  - `self._city_index` 容器
  - `_build_city_index()` 方法
  - `find_city_at(lon, lat)` 方法
- **`_build_index`**：末尾调 `_build_city_index()`

#### 修改

- **`game/map/geo_data.py`**：
  - `find_location` 改为"先精确后兜底"：
    ```python
    city = self.find_city_at(lon, lat)
    if city is None:
        city = self.find_nearest_label(lon, lat, self.labels_city, 0.4)
    ```

#### 修复

- **`MAP_STYLE.polygon.fill = "#"` 导致州界渲染静默失败**：
  - 症状：改 `polygon.width` 毫无效果；关掉 `LAYER_VISIBILITY.polygon` 后"州界"仍在
  - 原因：`fill = "#"` → `create_polygon` 抛 `TclError` → 被 `except: pass` 吞 → polygon 层一个都没画。用户看到的"州界"其实是 `line` 层的郡界
  - 修复：`fill = ""`（空串）；清 `userdata/settings.json` 里可能残留的 `"MAP_STYLE.polygon.fill": "#"`

#### 记录（非代码改动）

- **Tk 线宽整数取整**：`1.42` 落到 1px 档，`1.5` 落到 2px 档，视觉差别翻倍。`style.py` 里 `width` 直接用整数
- **UI 层"零改动"**：`map_canvas._process_motion` 早已是 `" · ".join(parts)` + `None` 段跳过，只需 `find_location` 返回县名

#### 设计决策（本轮定稿）

- **县查询走"精确优先 + 最近兜底"**：`find_city_at` 命中则用多边形内判断；否则 `find_nearest_label` 接住极小 boundary 的据点
- **多命中取 bbox 面积最小者**：极小环套在县内时，取更精确的那个
- **hover 反查复杂度可接受**：O(n) 线性 + 40ms 节流，无需额外空间结构
- **`_city_index` 与 `_state_index` / `_county_index` 同构**：保持代码一致
- **状态栏显示格式**：`州 · 郡 · 县`，`None` 段跳过（C 方案）

#### 数据约定（本轮新增）

- 县界多边形用于两件事：**渲染**（虚线）+ **反查**（`find_city_at`）
- hover 反查结果三元组：`(州名, 郡名, 县名)`，任一可为 `None`
- 兜底距离 0.4° 与旧行为一致

---

**本轮核心变动集中在 §3.9（CityIndex）**、**§5.11（geo_data 新增索引与查询）/ 5.20（style.py 现状）/ 5.21（settings_schema 现状）**、**§6.3（hover 反查链）**、**§8.3 第 74–80 条**、**§9.4**。