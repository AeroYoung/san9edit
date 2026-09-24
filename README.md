# 暗耻三国志 — 项目说明文档

> 本轮更新重点：**统一术语「县 = 据点」**（一个县 = 一个据点 = `map.geojson` 里的一个 `city` = 一个 `Node`）、**`type` 枚举收缩为 `城 / 关隘 / 渡口`**、县面势力染色 / 图层顺序 / 郡名 KaiTi 字体等前几轮改动一并归档。新增 §9.7 变更日志。

---

## 0. 术语表（★ 全文统一，先读这里）

| 中文 | 数据 / 代码里的名字 | 说明 |
|---|---|---|
| 州 | `states` / `shapes_polygon` / `_state_index` / `labels_state` | 一级行政区，2 位 id |
| 郡 | `counties` / `shapes_line` / `_county_index` / `labels_county` | 二级行政区，4 位 id |
| **县 = 据点** | `cities` / `shapes_point` / `shapes_city_boundary` / `_city_index` / `labels_city` / `Node` 类 | **三级单元，一个县就是一个据点**，6 位 id |
| 县的 type | `city["type"]` / `Node.type` | 只有三种：`城` / `关隘` / `渡口` |

**「县 = 据点」的核心约定：**

1. **一个县 = 一个据点 = 一个 `Node` 对象。** 不存在「一个县含多个据点」或「一个据点分属多个县」的情况。
2. 在 `map.geojson` 里，一个县就是 `states[i].counties[j].cities[k]` 的一个元素。
3. 每个县**必有** `coords`（中心点）+ `boundary`（闭合多边形）+ `type`。
4. `type` 只区分县的**形态**（城郭 / 关口 / 渡口），**不区分行政级别、不影响数据结构**：
   - 三种 type 的字段完全一样
   - 三种 type 的渲染逻辑完全一样（除样式细节外）
   - 三种 type 都参与势力染色、都参与 hover 反查、都有 `Node` 对象
5. 代码里遗留的 `city*` / `*_city_*` 命名（如 `shapes_city_boundary` / `labels_city` / `find_city_at`），**语义等于「县 / 据点」**，不是「城市」。改名成本大、收益为零，保留。

---

## 1. 项目概述

| 项 | 内容 |
|---|---|
| 项目名称 | 暗耻三国志（`APP_TITLE`） |
| 定位 | 三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》 |
| 程序入口 | `main.py` → `MainWindow().run()` |
| 核心功能 | 中国全图矢量渲染（州/郡/县三级边界 + 道路路网 + 水域湖泊/河流）、鼠标缩放平移、**光标精确反查州/郡/县**、旬回合制时钟、顶部信息栏与菜单、右侧 Tab 面板框架、多 Tab 设置窗口、剧本系统、势力关系分组展示、**县面势力染色（唯一着色图层）** |
| 运行环境 | Python 3 + 标准库 `tkinter`。仅依赖标准库，**无第三方依赖、无 requirements.txt** |
| 数据来源 | `assets/map.geojson`：13 州 / 106 郡 / 1372 县（= 1372 据点，`states → counties → cities`）；`assets/roads.geojson`：约 600 条道路；`assets/water.geojson`：205 条河流/湖泊；`assets/mountains.geojson`：42 个山地区块（未接入） |
| 剧本来源 | `scenarios/default.json` |
| 用户数据 | `userdata/settings.json` |
| 平台 | Windows 优先 |

**当前完成度：**

- ✅ 地图查看器（州/郡/县三级**边界**渲染 + 道路 + 水域 + 图层显隐 + 据点四级样式 + 县名避让）
- ✅ **县界渲染**（黑色虚线，按 bbox 尺寸分级显隐）
- ✅ **几何层去色**（州 / 郡 / 县三级边界均黑色描边，州面不填充）
- ✅ **县面势力染色**（地图上**唯一**的着色图层；一县一据点，按 `node.owner` 上色；无主县透出州面底色）
- ✅ **图层顺序保障可读性**（染色层位于县界/水体/道路/郡界/点位之下）
- ✅ **郡名标签独立字体**（KaiTi，字号较其他标签小 15%）
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
│   ├── map.geojson                 city 带 boundary，type ∈ {城, 关隘, 渡口}
│   ├── roads.geojson
│   ├── water.geojson
│   └── mountains.geojson           未接入
├── scenarios/
│   └── default.json
├── userdata/
│   └── settings.json               覆盖 style.py 默认值
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
    │   ├── node.py                 Node = 县 = 据点
    │   ├── world.py
    │   ├── scenario.py
    │   └── territory.py            郡级统计保留，当前渲染层不再消费
    ├── map/
    │   ├── geo_data.py
    │   ├── viewport.py
    │   └── renderer.py
    └── ui/
        ├── main_window.py
        ├── top_bar.py
        ├── status_bar.py
        ├── map_canvas.py
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

州 2 位 / 郡 4 位 / **县 6 位**。一个六位 id 对应一个县 = 一个据点 = 一个 `Node`。

```
例：010101
    ├ 01    州（并州）
    ├ 01    郡（上党郡）
    └ 01    县（长子，type=城）
```

### 3.2 势力（Faction）

`id` = 君主人物 id。字段：`id` / `name` / `color` / `prestige` / `gold` / `food` / `stance`。
`stance_label()` → `"敌对"` / `"盟友"` / `"中立"`。

### 3.3 人物（Character）

四位 id，五维。

### 3.4 县 = 据点（Node）★ 术语统一

**一个县 = 一个据点 = 一个 `Node` 对象。**

**静态字段**（来自 `map.geojson` 的 `cities[]` 元素）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | str | 六位（州 2 + 郡 2 + 县 2） |
| `name` | str | 县名（如「长子」「壶口关」） |
| `coords` | tuple | `(lon, lat)`，县的中心点 |
| `type` | str | **`城` / `关隘` / `渡口` 三选一** |
| `level` | int | 1（最大）–10（最小） |
| `is_capital` | bool | 是否郡治 |
| `boundary` | list | 闭合环 `[(lon,lat), ...]`，**所有县都有**（含关隘、渡口） |

**动态字段**（剧本覆盖）：`owner` / `troops` / `gold` / `food`。

**属性**：

- `state_id` → `id[:2]`
- `county_id` → `id[:4]`
- `is_owned()` → `owner is not None`

**关于 `type` 的约定：**

- `type` 只标记县的**形态**，不影响任何数据结构
- 三种 type 的 `Node` 字段完全一样
- 三种 type 都参与：势力染色 / hover 反查 / 剧本覆盖 / 面板展示
- **没有** `if type == "城"` 之类的逻辑分支（渲染层从设计上不区分 type）

### 3.5 游戏世界（World）

聚合容器，`factions` / `characters` / `nodes`。`nodes` 里每个元素就是一个县 = 一个据点。

### 3.6 剧本加载器（ScenarioLoader）

`ScenarioLoader.load(path, geo_data)` → `World`。

- `_build_nodes_from_geo`：遍历 `geo_data.shapes_point`，**每个 shapes_point 元素 → 一个 Node**
- `_apply_node_overrides`：用 `scenarios/default.json` 的 `nodes` 覆盖 `owner / troops / gold / food`

### 3.7 郡级控制力统计（CountyStat）

**当前不再被渲染层消费**，`CountyStat` / `compute_county_stats` / `CAPITAL_BONUS` 全部保留，供将来复用。

控制力算法：

```
单据点（县）权重 = (11 - level)
郡治县再 × 2.0
郡内总控制力 = Σ 权重(全部县，含无主)
势力值 = 控制力_F / 总控制力
ratio > 0.8   → 主导势力
0.5 < ratio ≤ 0.8 → 主要势力
其余          → 无
```

`MapRenderer.set_world` 仍会调用 `compute_county_stats` 并缓存到 `self._county_stats`，只是渲染层不读。

### 3.8 县界（CityBoundary）

**渲染层 + 查询层 + 染色层共用**，由 `GeoData.shapes_city_boundary` 承载。每个元素对应一个县 = 一个据点。

| 字段 | 类型 | 说明 |
|---|---|---|
| `geometry` | dict | `{"type": "LineString", "coordinates": [ring]}` |
| `properties.id` | str | 六位据点 id |
| `properties.县名` | str | 县名 |
| `properties.type` | str | `城` / `关隘` / `渡口` |
| `properties.level` | int | 1–10 |
| `bbox` | tuple | `(min_lon, min_lat, max_lon, max_lat)` |
| `size` | float | bbox 对角线长度 |
| `min_scale` | float | `_assign_lod` 赋的显示阈值（0/15/45/100 四档） |

`properties.id` 直接可用于 `world.node(id).owner` —— 这是县面染色的数据入口。

### 3.9 县界空间索引（CityIndex）

`GeoData._city_index`，结构 `(bbox, 名称, 外环顶点)`，与 `_state_index` / `_county_index` 同构。

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
      "cities": [{                              // ★ 每个元素 = 一个县 = 一个据点
        "id": "010101", "name": "长子",
        "coords": [lon, lat],
        "is_capital": true, "level": 3,
        "type": "城",                           // 城 / 关隘 / 渡口
        "boundary": [[lon,lat], ...]            // 县界多边形（三种 type 都有）
      }]
    }]
  }]
}
```

**关于 `boundary` 的约定：**

- **所有** type（城 / 关隘 / 渡口）的 city 都带 `boundary`
- `城` 的 boundary 通常是完整县域多边形，面积较大
- `关隘` / `渡口` 的 boundary 也覆盖一定区域，但形状更狭长或更小
- boundary 用于三件事：**绘制县界虚线**、**绘制县面染色**、**hover 反查县名**

### 4.2 `type` 枚举（★ 本轮收缩）

**只有三种：**

| type | 含义 | 典型 |
|---|---|---|
| `城` | 有城郭的县，通常是郡治或重要城市 | 长子、晋阳、临戎 |
| `关隘` | 关口、隘口 | 壶口关、天井关、鸡鹿塞 |
| `渡口` | 渡口、津 | （本数据集暂未出现，为将来预留） |

**已废弃的旧枚举**（旧数据里存在，新数据已无）：

- ~~`县`~~ → 用 `城` 代替
- ~~`渡口/津`~~ → 用 `渡口`
- ~~`仓/监`~~ → 已并入 `城` 或其他
- ~~`谷`~~ → 已并入 `城` 或其他
- ~~`山地`~~ → 已并入 `城` 或其他

**代码里对旧枚举的 fallback 已同步改为 `"城"`**（见 §5.11 / §5.16 / §5.17）。

### 4.3 `scenarios/default.json` 结构

version 1。字段与前一版一致，`nodes` 段以六位 id 为 key，覆盖 `owner / troops / gold / food`。

---

## 5. 模块与函数清单

### 5.1 `main.py`

`main()` → `MainWindow().run()`。

### 5.2 `game/config/constants.py`

路径常量：`ASSETS_DIR` / `DEFAULT_MAP_PATH` / `DEFAULT_WATER_PATH` / `DEFAULT_ROADS_PATH` / `SCENARIOS_DIR` / `DEFAULT_SCENARIO_PATH` / `APP_TITLE` / `MIN_WINDOW_SIZE`。

### 5.3 – 5.9

`faction.py` / `character.py` / `world.py` / `scenario.py` / `game_state.py` / `utils.py` **未改动**。

`utils.lighten_color(hex_color, factor=0.4)` / `darken_color(hex_color, factor=0.5)`：向白 / 黑线性插值。**保留**，当前渲染层不调用，供将来复用。

### 5.10 `game/core/territory.py`

`CountyStat` 数据类 + `compute_county_stats(world)` + `CAPITAL_BONUS = 2.0`。**保留不动**。`set_world` 仍会调用 `compute_county_stats`，结果缓存在 `self._county_stats`，但渲染层不读。

### 5.11 `game/map/geo_data.py`

#### 容器

```python
self.shapes_polygon = []          # 州面
self.shapes_line = []             # 郡界
self.shapes_point = []            # ★ 县（据点）点，每个元素 = 一个 Node
self.shapes_city_boundary = []    # ★ 县界（闭合 ring），每个元素 = 一个县
self.shapes_water_line = []
self.shapes_water_polygon = []
self.labels_state = []
self.labels_county = []
self.labels_city = []             # ★ 县名标签，每个元素对应一个县
self.bbox = None
self.roads = []
self._state_index = []
self._county_index = []
self._city_index = []
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
    data._assign_lod(data.shapes_city_boundary)
    data._compute_bbox()
    data._build_index()
    return data
```

#### `_classify_county`（★ type fallback 改为 `"城"`）

对每个 `county["cities"][k]`（一个县）：

1. 解析 `level`（含钳制到 1–10）
2. 向 `shapes_point` 追加：
   ```python
   "type": city.get("type", "城"),      # ★ 原 "县" → "城"
   ```
3. 向 `labels_city` 追加五元组 `(lon, lat, 县名, level, id)`
4. 向 `shapes_city_boundary` 追加：
   ```python
   "properties": {
       "id": city.get("id"),
       "县名": name,
       "type": city.get("type", "城"),   # ★ 原 "县" → "城"
       "level": level,
   },
   ```

#### 查询

- `find_state_at` / `find_county_at` / `find_city_at`：多边形精确反查
- `find_location(lon, lat)` → `(州名, 郡名, 县名)`；县查询为"`find_city_at` 精确优先 + `find_nearest_label` 0.4° 兜底"

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
    "territory",    # 县面势力染色（在 city 之下）
    "city",         # 县界（黑虚线）
    "water",        # 水体（湖泊 / 河流）
    "road",         # 道路
    "line",         # 郡界（黑实线）
    "point",        # 县点（= 据点）
    "label",        # 文字
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
| `_draw_geometry()` | `render_polygons → render_territory → render_city_boundaries → render_lines` |
| `render_polygons()` / `render_polygon(feat)` | 州面（透明 + 黑描边） |
| **`render_territory()`** | **县面染色**（遍历 `shapes_city_boundary`，按 `world.node(id).owner` 上色；**不区分 type**） |
| `render_city_boundaries()` | 县界：黑色虚线轮廓（**不区分 type**） |
| `render_lines()` / `render_line(feat)` | 郡界 |
| `render_points()` / `render_point(...)` | 县点（**不区分 type**，所有县都画） |
| `render_state_labels()` | 州名 |
| `render_county_labels()` | 郡名（**不随势力着色**；KaiTi 字体） |
| `render_city_labels()` | 县名（**不随势力着色**；**不区分 type**） |
| `render_label_group(labels, style_key)` | 通用标签绘制（州名用） |
| **`draw_text(x, y, text, style)`** | 单条文字 + halo；**支持 `style["font_family"]` 覆盖** |
| `resolve_style(key)` | 按当前 `span_px` 决定字号；返回 `{**base, "size": size}` |
| `_visible_bounds(margin_px=20)` | 视口经纬度范围 |
| `_point_lonlat(feat)` / `_point_radius(level, style)` | 县点辅助 |
| `_road_width(difficulty)` / `render_roads()` | 道路 |
| `render_water_polygons()` / `render_water_lines()` | 水域 |

#### `render_territory`（县面染色）

```python
def render_territory(self):
    """县面按所属势力上色。

    - 无 World：跳过
    - 遍历所有县（城 / 关隘 / 渡口），按其 owner 用势力原色填充
    - 无主县不染色，州面底色透出
    - 不区分 type；不画 stipple、不画斜线
    - LOD 与县界层一致：scale < feat["min_scale"] 时跳过
    """
    if not self._world or not self.data:
        return

    feats = getattr(self.data, "shapes_city_boundary", None)
    if not feats:
        return

    vx0, vy0, vx1, vy1 = self._visible_bounds()
    scale = self.viewport.scale

    for feat in feats:
        if scale < feat.get("min_scale", 0):
            continue
        b = feat["bbox"]
        if b[2] < vx0 or b[0] > vx1 or b[3] < vy0 or b[1] > vy1:
            continue
        props = feat.get("properties") or {}
        nid = props.get("id")
        if not nid:
            continue
        node = self._world.node(nid)
        if node is None or node.owner is None:
            continue
        faction = self._world.faction(node.owner)
        if faction is None:
            continue
        color = faction.color

        ring = feat["geometry"]["coordinates"]
        if len(ring) < 3:
            continue
        try:
            pts = []
            for lon, lat in ring:
                x, y = self.viewport.project(lon, lat)
                pts.extend((x, y))
            self.canvas.create_polygon(
                *pts, fill=color, outline=color, width=1,
                tags=self.TERRITORY_TAG,
            )
        except Exception:
            pass
```

**关键设计：**

- **数据源**：`shapes_city_boundary`（县界），每个元素对应一个县
- **数据入口**：`feat["properties"]["id"]` → `world.node(id).owner`
- **不区分 type**：城 / 关隘 / 渡口一视同仁
- **无主不上色**：`owner is None` 跳过
- **不用 `_county_stats`**：郡级统计不参与渲染

#### `set_world`

```python
def set_world(self, world):
    """注入 World。

    - 更新 self._world，供 render_territory 按据点 owner 查势力色
    - 仍会重算 _county_stats（郡级控制力），当前渲染层不用，
      保留给将来可能恢复的郡面染色 / 分级调色
    - 不负责重绘；调用方（MainWindow）按需 redraw
    """
    self._world = world
    self._county_stats = compute_county_stats(world)
```

#### `draw_text`（字体覆盖）

```python
def draw_text(self, x, y, text, style):
    family = style.get("font_family") or self.font_family   # ★ 字体覆盖
    font = (family, style["size"], "bold")
    halo = style.get("halo")
    if halo:
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            self.canvas.create_text(x + dx, y + dy, text=text,
                                    fill=halo, font=font, anchor="center",
                                    tags=self.LABEL_TAG)
    self.canvas.create_text(x, y, text=text,
                            fill=style["color"], font=font, anchor="center",
                            tags=self.LABEL_TAG)
```

### 5.14 `game/ui/main_window.py`

未改动。`_auto_load_default` → `load_geojson` + `_load_default_scenario`；`_load_default_scenario` 里调 `renderer.set_world(world)` + `map_canvas.redraw()`。

### 5.15 `game/ui/map_canvas.py`

`load_geojson` 里状态栏文案：

```python
f"据点 {len(data.labels_city)}"    # ★ 原 "县 N" → "据点 N"
```

`labels_city` 变量名保留（语义已统一为"县 / 据点"，不改）。

### 5.16 `game/core/node.py`（★ 默认 type 改为 `"城"`）

```python
def __init__(self, nid, name, coords, type_="城",   # ★ 原 "县" → "城"
             level=5, is_capital=False,
             owner=None, troops=0, gold=0, food=0):
```

`state_id` / `county_id` / `is_owned()` 不变。

### 5.17 `game/core/scenario.py`（★ 默认 type 改为 `"城"`）

`_build_nodes_from_geo`：

```python
world.nodes[nid] = Node(
    nid=nid,
    name=props.get("县名", ""),
    coords=(coords[0], coords[1]),
    type_=props.get("type", "城"),   # ★ 原 "县" → "城"
    level=props.get("level", 5),
    is_capital=props.get("is_capital", False),
)
```

### 5.18 `game/config/style.py`（当前生效值）

```python
MAP_STYLE = {
    "polygon": {
        "fill":    "",
        "outline": "#000000",
        "width":   4,
    },
    "line": {
        "color": "#000000",
        "width": 1,
    },
    "city_line": {
        "color": "#000000",
        "width": 1,
        "dash": (3, 3),
    },
    "road": { ... },
    "point": { ... },
    "water_polygon": { ... },
    "water_line": { ... },
    "territory": {
        "major_fade": 0.4,       # 保留字段，当前渲染层不消费
    },
    "label_state": {
        "color": "#1A1A1A", "halo": "#FFFFFF",
        "size_divisor": 55, "min_size": 11, "max_size": 44,
        "min_scale": 0, "max_scale": 40,
    },
    "label_county": {
        "color": "#000000", "halo": "#FFFFFF",
        "font_family": "KaiTi",
        "size_divisor": 124, "min_size": 8, "max_size": 19,
        "min_scale": 12, "max_scale": 150,
    },
    "label_city": {
        "color": "#000000", "halo": "#FFFFFF",
        "size_divisor": 140, "min_size": 8, "max_size": 16,
        "min_scale": 30, "point_gap": 6,
    },
}

LAYER_VISIBILITY = {
    "polygon":      True,
    "territory":    True,
    "city":         True,
    "line":         True,
    "point":        True,
    "road":         True,
    "water":        False,
    "mountain":     False,
    "label_state":  True,
    "label_county": True,
    "label_city":   True,
}
```

**视觉分层总结：**

| 层 | 线型 | 颜色 | 宽度 | 备注 |
|---|---|---|---|---|
| 州面 | 描边 | 黑 | 4 | 不填充 |
| 县面染色 | 实心面 | 势力色 | — | **唯一着色层**；只染州内部；不区分 type |
| 县界 | 虚线 | 黑 | 1 | 在染色之上；不区分 type |
| 水体 | 线/面 | 蓝系 | — | 在染色之上 |
| 道路 | 实线 | — | 按 difficulty | 在染色之上 |
| 郡界 | 实线 | 黑 | 1 | 在染色之上 |
| 县点 | — | 黑 | — | 不随势力变化；不区分 type |
| 州名 / 县名标签 | — | 黑 / 深灰 | — | 全局字体 |
| 郡名标签 | — | 黑 | — | **KaiTi 字体**，字号较其他标签小 15% |

### 5.19 `game/config/settings_schema.py`

**`GROUPS`：**

- `theme` / `font`（restart = True）
- `polygon` / `line` / `city` / `point` / `road` / `water`
- `label_state` / `label_county` / `label_city`
- `lod`
- `territory`
- `visibility`

**`territory` 分组**：

```python
{"key": "territory", "tab": "appearance", "title": "势力染色",
 "desc": "按各县所属势力给县面上色。有主县用势力原色，"
         "无主县不染色（州面底色透出）。"},
```

**`label_county` 分组**：

```python
{"key": "label_county", "tab": "appearance", "title": "郡名标签",
 "desc": "郡名文字的显隐区间与字号。郡名使用独立字体（style.py 里 "
         "MAP_STYLE.label_county.font_family，默认楷体 KaiTi）。"},
```

**`point` 分组**（★ 文案更新）：

```python
{"key": "point", "tab": "appearance", "title": "据点样式",
 "desc": "各据点（城 / 关隘 / 渡口）小点的颜色、大小、描边与形状分级。"},
```

**`ITEMS` 关键项**（部分）：

| path | group | type | label |
|---|---|---|---|
| `MAP_STYLE.polygon.outline` | polygon | color | 州面描边色 |
| `MAP_STYLE.polygon.width` | polygon | int | 描边宽度 |
| `MAP_STYLE.line.color` | line | color | 郡界颜色 |
| `MAP_STYLE.line.width` | line | int | 线宽 |
| `MAP_STYLE.city_line.color` | city | color | 县界轮廓色 |
| `MAP_STYLE.city_line.width` | city | int | 轮廓线宽 |
| `MAP_STYLE.label_county.size_divisor` | label_county | int | 字号分母 |
| `MAP_STYLE.label_county.min_size` | label_county | int | 字号下限 |
| `MAP_STYLE.label_county.max_size` | label_county | int | 字号上限 |
| `LAYER_VISIBILITY.city` | visibility | bool | 县界 |
| `LAYER_VISIBILITY.territory` | territory | bool | 启用势力染色 |

**已删除的 ITEM**：

- `MAP_STYLE.territory.major_fade`（县面染色不再使用）
- `MAP_STYLE.polygon.fill` / `MAP_STYLE.city_polygon.fill`（历史）

**未纳入设置窗口**：`MAP_STYLE.*.font_family`（无 `font` 类型控件）。

---

## 6. 程序完整运行流程

### 6.1 启动阶段

```
python main.py
└─ MainWindow()
   ├─ SettingsManager().apply()      # 会用 userdata 覆盖 style.py
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
│     └─ _build_index → _build_city_index()
│  └─ MapCanvas → renderer.set_data → draw_full
│
└─ _load_default_scenario()
   ├─ ScenarioLoader.load → World
   │  └─ _build_nodes_from_geo：shapes_point → Node（一县一 Node）
   ├─ game_state.sync_from_world(world)
   ├─ renderer.set_world(world)
   └─ map_canvas.redraw()          # 触发 render_territory 按县面上色
```

### 6.3 主循环交互

| 触发 | 调用链 |
|---|---|
| 鼠标移动 | `_on_motion` → 40ms 节流 `_process_motion` → `viewport.unproject` → `data.find_location(lon, lat)` → `status_bar.set_location(text)` |
| 滚轮 / 拖拽 | `viewport.zoom / pan_pixels` → `renderer.zoom / pan` |
| 顶部信息栏 | 200ms 轮询 `game_state.get_display_items()` |
| 设置保存 | `_on_settings_applied` → 地图相关则 `map_canvas.redraw()` |

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
                    │                                  └ core.territory（保留备用）
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

### 7.3 代码内常量

| 位置 | 值 | 含义 |
|---|---|---|
| `MapCanvas._MIN_VALID_SIZE` | `10` | 布局未完成阈值 |
| `TopBar._REFRESH_INTERVAL_MS` | `200` | 信息栏轮询 |
| `MapRenderer._LAYER_ORDER` | 见 §5.13 | 图层底→顶 |
| `GeoData._assign_lod` 四档 | `0 / 15 / 45 / 100` | 所有 LOD 图层共用 |
| `MAP_STYLE.city_line.dash` | `(3, 3)` | 虚线节奏 |
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
| **`type` 差异化的能力 / 玩法** | **未做**（城 / 关隘 / 渡口目前只是标记） |
| 设置窗口「操作」「游戏」tab | 骨架 |
| 县界 / 县面 hover | 不做 |
| `dash` 可调 | 不支持（tuple path） |
| 郡面分级调色 | `lighten_color` / `major_fade` / `_county_stats` 全保留但不消费 |
| 字体可在 UI 里改 | 不支持（无 `font` 类型控件） |

### 8.2 数据层缺失

- `GameState` 只有日期 + 玩家势力 + 3 项资源
- `mountains.geojson` 未接入
- 路网无拓扑关联
- 势力间无关系矩阵
- `渡口` 类型在本数据集暂未出现

### 8.3 逻辑与性能限制

（承接前几版 1–89 条，本轮新增 90–94）

1. `render_lines` / `render_city_boundaries` 全量遍历 + bbox 粗筛
2. `<Configure>` 全量重绘
3. 绘制方法外层 `except Exception: pass`
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
57. ★ `SettingsManager` 只支持"名字.子键"或"顶层字典"
58. ★ `labels_county` 是四元组、`labels_city` 是五元组
59. ★ `render_territory` 的 `outline=color` 是刻意的
60. ★ `set_world` 不负责重绘
61. ★ `CountyStat` 现在是渲染层"未消费缓存"
62. ★ 无主据点计入控制力分母
63. ★ `style.py` 里 `LAYER_VISIBILITY` 段注释和缩进不齐
64. ★ `MAP_STYLE.polygon.fill = ""` 是合法的"不填充"值
65. ★ `city_polygon` 段已彻底移除
66. ★ 县界是 `CITY_TAG` 下的独立图层，位于 `territory` 之上
67. ★ **`shapes_city_boundary` 收集所有 type（城 / 关隘 / 渡口）**
68. ★ 县界 LOD 与水域共用 `_assign_lod`
69. ★ `render_city_boundaries` 用 `create_line` 而非 `create_polygon`
70. ★ `render_city_labels` 解包变量 `cid` 无人消费但不能删
71. ★ `render_county_labels` / `render_city_labels` 都不再查势力色
72. ★ 州 / 郡 / 县三级边界区分靠粗细与虚实
73. ★ 州界宽度在设置窗口内受 `max` 限制
74. ★ **`render_*` 的 `except Exception: pass` 是重大排查障碍**
75. ★ Tk 线宽取整到整数像素
76. ★ `_city_index` 与 `_state_index` / `_county_index` 同构
77. ★ `find_city_at` 多命中取 bbox 面积最小者
78. ★ `find_location` 的县查询是"精确优先 + 最近兜底"
79. ★ hover 反查是 O(n) 线性 + 40ms 节流
80. ★ UI 层对县名显示"零改动"
81. ★ `_LAYER_ORDER` 中 `territory` 位于 `city` 之下
82. ★ `render_territory` 数据源是 `shapes_city_boundary`
83. ★ `render_territory` 不再消费 `_county_stats`
84. ★ 县面染色的 LOD 与县界层严格一致
85. ★ 一个县一个据点，`owner` 就是染色依据
86. ★ **所有 type 都参与染色、县界、点位、标签渲染**（城 / 关隘 / 渡口一视同仁）
87. ★ `LAYER_VISIBILITY.territory` 语义为"县面染色"
88. ★ `MAP_STYLE.territory.major_fade` 保留在 `style.py`，设置窗口已移除
89. ★ `settings_schema` 里 `territory` 分组描述已更新
90. ★ **郡名标签有独立字体覆盖**（`MAP_STYLE.label_county.font_family`，默认 `"KaiTi"`）
91. ★ **郡名字号三字段联动缩 15%**（`size_divisor 105→124`、`min_size 9→8`、`max_size 22→19`）
92. ★ **术语「县 = 据点」已统一**
    - 一个县 = 一个据点 = 一个 `Node` 对象 = `map.geojson` 里的一个 `city`
    - 代码里 `city*` / `*_city_*` 命名的变量，语义等于"县 / 据点"
    - 文档、注释、UI 文案里不再出现"一个县含多个据点"或"据点分属多个县"的表述
93. ★ **`type` 枚举已收缩为 `城 / 关隘 / 渡口`**
    - 代码里对 type 的 fallback 默认值全部改为 `"城"`
    - 旧枚举 `县 / 渡口\/津 / 仓\/监 / 谷 / 山地` 已废弃
    - **渲染层、查询层、剧本层、染色层对 type 无任何分支**
94. ★ **`userdata/settings.json` 会覆盖 `style.py` 默认值**
    - `MainWindow.__init__` 里 `SettingsManager().apply()` 在 `style.py` 被 import 之后运行
    - 排查"改了没效果"时优先看 `userdata/settings.json`

### 8.4 建议的下一步

1. **给 `render_*` 的 `except` 加"首次异常打印"**：

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

2. **给 `type` 赋予玩法差异**（城 / 关隘 / 渡口的不同能力）
3. **据点点击详情面板**（`node_panel` 接入）
4. **人物面板 / 势力面板交互**
5. **外交入口（改 `stance`）**
6. **接入 `mountains.geojson`**
7. **存档系统 / 新游戏流程**
8. **回合流程**
9. **县界样式细化**：`dash` 可调、按 type 区分样式、hover 高亮
10. **恢复郡级统计图层**（若将来需要"郡面 + 县面"双层染色）
11. **给 `settings_schema` 增加 `font` 类型**，把 `MAP_STYLE.*.font_family` 暴露到设置窗口

---

## 9. 变更日志

### 9.1 – 9.5（摘要）

- 9.1：剧本系统 + 外交分组 + 层序修复
- 9.2：郡面势力染色（`territory.py` + `render_territory`）
- 9.3：县界渲染 + 几何层去色
- 9.4：hover 反查县名 + 州界渲染修复
- 9.5：县面势力染色 + 图层顺序调整（`territory` 降到 `city` 之下）

### 9.6 郡名标签独立字体 + 缩小 15%（第七轮）

**需求**：

1. 郡名标签换字体（KaiTi）
2. 郡名字号稍微小一点（缩 15%）

**改动**：

- **`game/map/renderer.py`**：`draw_text` 增加字体覆盖（`style.get("font_family") or self.font_family`）
- **`game/config/style.py`**：`MAP_STYLE.label_county` 新增 `"font_family": "KaiTi"`，`size_divisor 105→124`，`min_size 9→8`，`max_size 22→19`
- **`game/config/settings_schema.py`**：`label_county` 分组 `desc` 补字体说明

### 9.7 县 = 据点 · `type` 枚举收缩（第八轮）

#### 需求

1. **统一术语「县 = 据点」**：一个县 = 一个据点 = `map.geojson` 里的一个 `city` = 一个 `Node` 对象。
2. **`type` 枚举收缩**：从 `县 / 关隘 / 渡口\/津 / 仓\/监 / 谷 / 山地` 变为 `城 / 关隘 / 渡口`。
3. 在文档中把这两件事说清楚。

#### 改动

**`game/map/geo_data.py`**：

- `_classify_county` 里两处 `type` fallback 默认值 `"县"` → `"城"`
  - `shapes_point` 元素
  - `shapes_city_boundary` 的 `properties`
- 顶部 docstring / 容器注释统一为"县（据点）"

**`game/core/node.py`**：

- `Node.__init__` 默认 `type_="县"` → `"城"`

**`game/core/scenario.py`**：

- `_build_nodes_from_geo` 里 `type_=props.get("type", "城")`（原 `"县"`）

**`game/ui/map_canvas.py`**：

- `load_geojson` 状态栏文案 `f"县 {len(data.labels_city)}"` → `f"据点 {len(data.labels_city)}"`

**`game/config/settings_schema.py`**：

- `point` 分组 `title` `"县点样式"` → `"据点样式"`
- `point` 分组 `desc` 改为"各据点（城 / 关隘 / 渡口）小点的颜色、大小、描边与形状分级。"

**代码逻辑层**：

- **零改动**。渲染层 / 查询层 / 剧本层 / 染色层从来不对 `type` 做分支判断，所有 type 一视同仁。

#### 记录（非代码改动）

- **`userdata/settings.json` 会覆盖 `style.py` 默认值**：排查"改了没效果"时优先查看
- **KaiTi 字体名可能不匹配**：Windows 上可能是 `"KaiTi"` / `"楷体"` / `"KaiTi_GB2312"`；缺失时 Tk 静默回退 `TkDefaultFont`
- **只改 `style.py` 不改 `draw_text`，字号变但字体不变**

#### 设计决策（本轮定稿）

- **术语统一**：全文以"县"为主称，"据点"为同义补充，不再混用其他叫法
- **`type` 只标记形态**：城 / 关隘 / 渡口三者字段、渲染、逻辑完全平等
- **代码里保留 `city*` 命名**：语义已等同"县 / 据点"，改名成本大于收益
- **fallback 默认值统一为 `"城"`**：数据里都有 `type`，fallback 只为防御脏数据
- **文档显眼处（§0）单列术语表**：先读术语再读代码，避免"城市 vs 据点"的旧歧义重演

#### 数据约定（本轮明确）

- 一个 `cities[]` 元素 = 一个县 = 一个据点 = 一个 `Node`
- `type ∈ {"城", "关隘", "渡口"}`
- 三种 type 的字段完全一样
- 三种 type 都参与：势力染色 / 县界虚线 / 县点点位 / 县名标签 / hover 反查 / 剧本覆盖

---

**本轮核心变动集中在 §0（新增术语表）**、**§3.4（县 = 据点 定义）**、**§4.2（type 枚举收缩）**、**§5.11 / 5.16 / 5.17 / 5.18 / 5.19（fallback + 文案）**、**§8.3 第 92–94 条**、**§9.7**。