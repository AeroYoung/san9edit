# 暗耻三国志 — 项目说明文档

## 1. 项目概述

| 项 | 内容 |
|---|---|
| 项目名称 | 暗耻三国志（`APP_TITLE`） |
| 定位 | 三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》 |
| 程序入口 | [main.py](main.py) → `MainWindow().run()` |
| 核心功能 | 中国全图矢量渲染（州/郡/县三级 GeoJSON + 道路路网，**县点按 level 分形状/尺寸并与县名同阈值显隐**）、鼠标缩放平移、光标位置反查行政区、旬回合制时钟、顶部信息栏与菜单、右侧 Tab 面板框架 |
| 运行环境 | Python 3（实测 3.14）+ 标准库 `tkinter`。仅依赖标准库，**无第三方依赖、无 requirements.txt** |
| 数据来源 | [assets/map.geojson](assets/map.geojson)：13 州 / 106 郡 / 1372 县（`states → counties → cities` 三层嵌套，县 `level` 取值 **1–10**）；[assets/roads.geojson](assets/roads.geojson)：约 600 条道路线段 |
| 平台 | Windows 优先（`maximize()` 兼容 Win/Linux/macOS） |

**当前完成度**：地图查看器（含路网）已完整可用；回合与资源为骨架；内政/军事/外交/存档均为空实现。

---

## 2. 文件结构清单

```
san9edit/
├── main.py                     启动入口，创建并运行 MainWindow
├── README.md                   本文档
├── assets/
│   ├── map.geojson             主地图：州面 + 郡界 + 县点 + 三级标签坐标（1.5 MB）
│   ├── roads.geojson           道路路网：LineString 线段，properties 含 difficulty /
│   │                           road_type / from_id / to_id / length_km /
│   │                           mountains_crossed / waters_crossed 等（约 600 条）
│   ├── water.geojson           河流/湖泊（205 要素），已有加载代码但调用被注释
│   └── mountains.geojson       山地/关隘（42 要素，含 passable 属性），无任何代码引用
└── game/
    ├── __init__.py             包声明，无逻辑
    ├── config/
    │   ├── __init__.py         空
    │   ├── constants.py        路径、窗口尺寸、初始年份/势力/资源的全局常量
    │   └── style.py            UI 主题色、字体候选、地图绘制样式、县名分级显隐阈值
    ├── core/
    │   ├── __init__.py         空
    │   ├── game_state.py       回合/日期/资源的数据模型，信息栏数据源
    │   └── utils.py            几何通用工具（坐标展开、点在多边形内）
    ├── map/
    │   ├── __init__.py         空
    │   ├── geo_data.py         GeoJSON 解析、图层分类、空间索引与点查询
    │   ├── viewport.py         视图状态：中心经纬度、缩放比、投影/反投影
    │   └── renderer.py         地图绘制（几何层 + 文字层），与 UI 事件解耦
    └── ui/
        ├── __init__.py         空
        ├── main_window.py      主窗口：组装部件、跨模块事件与业务
        ├── top_bar.py          顶部栏：左侧信息项（可点击弹窗）+ 右侧菜单与「进行」按钮
        ├── status_bar.py       底部状态栏：提示 / 缩放 / 位置三段
        ├── map_canvas.py       地图画布：整合 viewport + renderer + 鼠标交互
        ├── side_panel.py       右侧 Notebook 容器 + 统一刷新入口
        ├── window_utils.py     窗口最大化、相对父窗居中
        └── panels/
            ├── __init__.py     空
            ├── faction_panel.py   势力信息（占位，部分硬编码）
            ├── city_panel.py      城市列表 Treeview（空数据）
            ├── general_panel.py   武将列表 Treeview（空数据）
            └── troop_panel.py     部队列表 Treeview（空数据）
```

> `settings.local.json`、`__pycache__` 为环境产物，不属于项目源码。

**依赖方向单向**：`main → ui → map/core → config`。

---

## 3. 模块与函数清单

### 3.1 [main.py](main.py)

| 函数 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `main()` | — | `None` | 实例化 `MainWindow` 并调用 `run()` 进入事件循环 |

---

### 3.2 [game/config/constants.py](game/config/constants.py)

纯常量模块，无类与函数。

| 常量 | 值 | 说明 |
|---|---|---|
| `PROJECT_ROOT` | `Path(__file__).parents[2]` | 项目根，保证任意目录启动都能定位 assets |
| `ASSETS_DIR` | `PROJECT_ROOT/"assets"` | 资源目录 |
| `DEFAULT_MAP_PATH` | `assets/map.geojson` | 启动自动加载 |
| `DEFAULT_ROADS_PATH` | `assets/roads.geojson` | 随主地图自动加载的路网 |
| `DEFAULT_WATER_PATH` | `assets/water.geojson` | **已定义但当前无调用** |
| `APP_TITLE` | `"暗耻三国志"` | 窗口标题 |
| `WINDOW_SIZE` | `"1440x900"` | 保留常量，`MainWindow` 未使用 |
| `MIN_WINDOW_SIZE` | `(1024, 640)` | 窗口最小尺寸 |
| `INITIAL_YEAR/MONTH/XUN` | `208 / 1 / 1` | 初始日期（上旬） |
| `INITIAL_FACTION` | `"刘备"` | 初始玩家势力 |
| `INITIAL_PRESTIGE/GOLD/FOOD` | `1000 / 5000 / 20000` | 初始资源 |

---

### 3.3 [game/config/style.py](game/config/style.py)

纯配置模块，无类与函数。

| 名称 | 结构 | 说明 |
|---|---|---|
| `THEME` | dict | UI 配色：信息栏、状态栏、面板、画布、工具栏背景 |
| `FONT_CANDIDATES` | tuple | 中文字体优先级列表，`MainWindow._pick_font_family` 按序挑第一个可用 |
| `FONT_SIZES` | dict | 各 UI 元素字号偏移：`info_bar/menu/status_bar/panel_title/panel_body` |
| `MAP_STYLE` | dict | 地图样式：`polygon`（州面）、`line`（郡界）、`point`（县点，**含形状/半径分级**）、`road`（道路）、`water_polygon`、`water_line`，以及 `label_state/label_county/label_city` 三组标签样式（含 `size_divisor/min_size/max_size/min_scale/max_scale/halo`） |
| `CITY_LEVEL_MIN_SCALE` | dict | 县名按 `level` 显隐阈值（`level` 取值 **1–10**）：1→0、2→6、3→14、4→28、5→50、6→85、7→130、8→190、9→260、10→350（像素/度）。**县点与县名共用此表**，实现同显同隐 |

`MAP_STYLE["road"]` 子项：

| 键 | 示例值 | 说明 |
|---|---|---|
| `color` | `"#a8895f"` | 道路线颜色 |
| `width_divisor` | `2600` | 地图总像素宽 ÷ 此值 = 基准线宽 |
| `min_width` | `0.3` | 线宽绝对下限（像素） |
| `max_width` | `2.0` | 线宽绝对上限（像素） |
| `difficulty_floor` | `1.0` | `difficulty` 的下限，避免除零/极端放大 |

`MAP_STYLE["point"]` 子项：

| 键 | 示例值 | 说明 |
|---|---|---|
| `fill` | `"#3b2a1a"` | 县点填充色 |
| `outline` | `"#f2e6cc"` | 描边色（浅色，暗底上提亮轮廓） |
| `outline_width` | `0.6` | 描边宽（像素） |
| `size_divisor` | `1100` | 地图总像素宽 ÷ 此值 = 基准半径；越大点越小 |
| `min_radius` / `max_radius` | `0.9` / `5.5` | 半径绝对上下限（像素） |
| `shape_by_level` | `{1:"circle", …, 10:"triangle"}` | `level → 形状`，共 10 档；level 1–3 圆、4–6 菱、7–8 方、9–10 三角 |
| `radius_by_level` | `{1:1.80, …, 10:0.62}` | `level → 半径倍率`，共 10 档，单调递减 |

#### `CITY_LEVEL_MIN_SCALE` 说明

- 语义：该级别县 **在缩放 ≥ 对应值（像素/度）时才绘制**。**县点与县名共用此阈值**，因此两者的显隐严格同步。
- 1 级为最重要据点，阈值 0，任何缩放下都可见；级别越大阈值越高，越晚出现。
- 数值必须**严格单调递增**，否则会出现"高级别先于低级别显示"的错乱。
- 调参方向：整体偏大 → 县名/县点更稀疏、地图更干净；整体偏小 → 更密集，低缩放级别下易堆叠。
- 若 9/10 两档在当前地图最大缩放下永远达不到，可下调至 `200 / 260`。

#### `MAP_STYLE["point"]` 说明

- 形状映射：level 1–3 → `circle`（州治/郡治级大据点）；4–6 → `diamond`（普通县城）；7–8 → `square`（小县）；9–10 → `triangle`（村落/关隘级小聚落）。视觉权重随 level 递减。
- 半径公式：`clamp(地图总像素宽 / size_divisor × radius_by_level[level], min_radius, max_radius)`，与道路线宽同一套思路，随缩放动态变化。
- `shape_by_level` 与 `radius_by_level` 是**定长字典**（键 1–10），与 `CITY_LEVEL_MIN_SCALE` 三者必须同步维护；越界 `level` 由 `.get(level, 默认)` 兜底，不抛异常。

---

### 3.4 [game/core/utils.py](game/core/utils.py)

| 函数 | 入参 | 返回 | 用途 | 调用者 |
|---|---|---|---|---|
| `walk_coords(coords)` | 任意嵌套坐标数组 | 生成器，逐个 `(lon, lat)` | 递归展开 GeoJSON 坐标 | `GeoData._compute_bbox`、`GeoData._coords_bbox` |
| `midpoint_of_line(coords)` | 折线坐标列表 | `(lon, lat)` | 取首尾中点 | **无调用者（死代码）** |
| `point_in_polygon(x, y, ring)` | 坐标 + 顶点环 | `bool` | 射线法判断点是否在多边形内（含 `1e-12` 除零保护） | `GeoData.find_state_at`、`GeoData.find_county_at` |

---

### 3.5 [game/core/game_state.py](game/core/game_state.py)

**类 `GameState`**

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `__init__()` | — | — | 从 `constants` 初始化 `year/month/xun/player_faction/prestige/gold/food` |
| `date_text()` | — | `str` | 格式化为 `"208年 1月上旬"` |
| `advance_turn()` | — | `None` | 推进一旬；旬>3 → 月+1；月>12 → 年+1 |
| `change_gold(delta)` | 增减量 | `None` | 金钱变更，下限钳制为 0 |
| `change_food(delta)` | 增减量 | `None` | 军粮变更，下限 0 |
| `change_prestige(delta)` | 增减量 | `None` | 威望变更，下限 0 |
| `get_display_items()` | — | `[(key, 标签, 值)]` | 信息栏数据源，目前 5 项：date/faction/prestige/gold/food |

调用者：`MainWindow.__init__` 创建实例，分发给 `TopBar`、`SidePanel`、四个面板；`MainWindow._end_turn` 调 `advance_turn`；`TopBar._refresh` 每 200 ms 轮询 `get_display_items`。

---

### 3.6 [game/map/geo_data.py](game/map/geo_data.py)

**类 `GeoData`**

实例属性：`shapes_polygon`（州面）、`shapes_line`（郡界）、`shapes_point`（县点）、`shapes_water_line`、`shapes_water_polygon`、`roads`（道路）、`labels_state`、`labels_county`、`labels_city`、`bbox`、`feature_count`、`_state_index`、`_county_index`。

**`shapes_point` 元素结构**（与 `renderer._point_lonlat` 约定一致）：

```python
{
    "geometry": {"type": "Point", "coordinates": [lon, lat]},
    "properties": {"县名": name, "level": level},   # level 为已钳制到 1–10 的 int
}
```

**`labels_city` 元素结构**：`(lon, lat, name, level)` 四元组。

**`roads` 结构**：`[(coords, difficulty, bbox), ...]`，其中 `coords` 为 `[(lon, lat), ...]`，`difficulty` 为 `float`（默认 1.3），`bbox` 为 `(minx, miny, maxx, maxy)`；无数据时为 `[]`。

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `from_file(path)` (classmethod) | GeoJSON 路径 | `GeoData` | 读取 → `_classify` → `_compute_bbox` → `_build_index` |
| `load_water(path)` | 水域 GeoJSON 路径 | `None` | 按几何类型分流为河/湖，计算 `bbox` 与 `size`，再 `_assign_lod` |
| `load_roads(path)` | 路网 GeoJSON 路径 | `None` | 只解析 `LineString`，提取 `coordinates` + `difficulty`（默认 1.3），逐条算 bbox 存入 `self.roads`。不做空间索引，由 renderer 侧做 bbox 粗筛 |
| `_classify(states)` | states 列表 | `None` | 生成州标签（`name_coords` 两点取中点）、州面、逐郡转 `_classify_county`，最后统计 `feature_count` |
| `_classify_county(sname, county)` | 州名 + 郡字典 | `None` | 生成郡标签（单点）、郡界（闭合 LineString）、县点与县标签（均带 `level`）。**县点与县标签共用同一个 `level` 值，且该值的解析必须先于 `shapes_point.append`**（见下方警告） |
| `_compute_bbox()` | — | `None` | 遍历州面/郡界/县点坐标求全局外接矩形 |
| `_build_index()` | — | `None` | 为州面外环、郡界环建 `(bbox, name, ring)` 索引 |
| `_ring_bbox(ring)` (static) | 顶点环 | `(minx,miny,maxx,maxy)` | 环的外接矩形 |
| `_coords_bbox(coords)` (static) | 任意嵌套坐标 | `(minx,miny,maxx,maxy)` | 通用外接矩形 |
| `_assign_lod(features)` (static) | 要素列表 | `None` | 按 `size` 降序分四档赋 `min_scale`：前 15%→0，15–40%→15，40–70%→45，其余→100 |
| `find_state_at(lon, lat)` | 经纬度 | 州名 / `None` | bbox 粗筛 + 射线法精判 |
| `find_county_at(lon, lat)` | 经纬度 | 郡名 / `None` | 同上 |
| `find_nearest_label(lon, lat, candidates, max_dist)` (static) | 经纬度、候选、距离上限 | 名称 / `None` | 取最近候选，超出上限返回 `None` |
| `find_location(lon, lat)` | 经纬度 | `(州名, 郡名, 县名)` | 州/郡用多边形判定，县用最近标签（上限 0.4°） |

调用链：`MapCanvas.load_geojson` → `from_file` → `load_roads`；`MapCanvas._process_motion` → `find_location` → `find_state_at`/`find_county_at`/`find_nearest_label`。

#### 县 `level` 字段约定

- 取值范围 **1–10**（1 = 最重要/最大据点，10 = 最次要/最小聚落）。
- 解析时做 `int()` 转换 + `max(1, min(10, level))` 钳制；字段缺失或非法值时默认 `5`。
- **解析必须先于使用**：在 `_classify_county` 的 `for city in ...` 循环里，`level` 的两行解析（`int()` + 钳制）**必须写在 `shapes_point.append` 之前**。若顺序颠倒（先 append 用 `level`，后解析），Python 会抛 `UnboundLocalError: cannot access local variable 'level'`，且异常会中断整个 `GeoData.from_file`，导致**地图完全不加载**（症状：状态栏提示"自动加载失败"，画布空白）。
- 钳制的意义：下游 `CITY_LEVEL_MIN_SCALE`、`shape_by_level`、`radius_by_level` 都是定长字典，越界值若不钳制会直接 `KeyError`，而绘制层的 `except Exception` 会静默吞掉，导致整层县点/县名凭空消失、极难排查。
- `level` 值需在 `shapes_point` 与 `labels_city` 两处保持一致（同一循环内共用），否则会出现"点出、标签不出"或反过来的诡异现象。

---

### 3.7 [game/map/viewport.py](game/map/viewport.py)

**类 `Viewport`** — 属性 `cx`、`cy`（中心经纬度）、`scale`（像素/度）、`width`、`height`。

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `set_canvas_size(w, h)` | 画布宽高 | `None` | 记录尺寸，最小 1 |
| `fit_to_bbox(bbox, margin=0.92)` | 外接矩形 | `None` | 居中对齐并计算 `min(sx, sy)` 自适应缩放 |
| `zoom(factor, anchor=None)` | 倍率、锚点像素 | `None` | 绕锚点缩放，保持锚点地理坐标不动；锚点默认画布中心 |
| `pan_pixels(dx, dy)` | 像素位移 | `None` | 反算经纬度偏移 |
| `project(lon, lat)` | 经纬度 | `(x, y)` | 地理 → 屏幕（Y 轴取反，北在上） |
| `unproject(x, y)` | 屏幕坐标 | `(lon, lat)` | 屏幕 → 地理 |
| `span_px(bbox)` | 外接矩形 | `float` | 当前缩放下地图总宽（像素），用于标签字号、道路线宽与**县点半径**计算 |

调用者：`MapRenderer` 全部绘制方法调 `project`/`span_px`；`MapCanvas` 调 `unproject`/`zoom`/`pan_pixels`/`fit_to_bbox`/`set_canvas_size`。

---

### 3.8 [game/map/renderer.py](game/map/renderer.py)

**类 `MapRenderer`** — 常量 `LABEL_TAG="label"`、`WATER_TAG="water"`、`ROAD_TAG="road"`、`POINT_TAG="point"`、`POLYGON_TAG="polygon"`、`LINE_TAG="line"`；属性 `data`、`_drawn`、`_cum_scale`（自上次全量重绘的累计缩放）。

> **`_drawn` 的语义**：表示"**几何层已绘制完成、动态层可以叠加**"，而非"全部绘制完成"。`draw_full` 中必须在 `_draw_geometry()` 之后、`refresh_dynamic()` **之前**置 `True`；`refresh_dynamic` 以它作为守卫（`if not self._drawn: return`）。若置位时机错误（如置于末尾），`draw_full` 首帧的动态层会被守卫跳过，出现"开图只有州郡边界、鼠标一动才补全"的现象。

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `__init__(canvas, viewport, font_family)` | 画布/视图/字体 | — | 绑定三者 |
| `set_data(geo_data)` | `GeoData` | `None` | 注入数据 |
| `draw_full()` | — | `None` | 全量重绘：`delete("all")` → `_drawn=False` → 重置 `_cum_scale` → `_draw_geometry()` → **`_drawn=True`** → `refresh_dynamic()`。**置位顺序是关键**（见上） |
| `pan(dx, dy)` | 像素位移 | `None` | 调 `canvas.move("all", ...)`，O(1) 平移；**不补画新进入视口的静态几何**（详见 6.3 节） |
| `zoom(factor, mx, my)` | 倍率、锚点 | `None` | 调 `canvas.scale("all", ...)`；累计倍率超出 `[0.5, 2.0]` 时改为 `draw_full()` 消除舍入误差 |
| `refresh_dynamic()` | — | `None` | `_drawn` 守卫 → 删除 `LABEL_TAG` / `WATER_TAG` / `ROAD_TAG` / `POINT_TAG` → **按 水 → 路 → 点 → 标签 顺序重绘** → `tag_lower` 归位。**绘制顺序决定叠放**（标签最后画故天然在最顶） |
| `_draw_geometry()` | — | `None` | 只绘**静态层**：州面 → 郡界（湖泊/河流/道路/县点/标签均在 `refresh_dynamic`） |
| `_draw_labels()` | — | `None` | 依次绘州名 → 郡名 → 县名 |
| `_draw_water()` | — | `None` | 湖泊 + 河流 |
| `_visible_bounds(margin_px=20)` | 留白像素 | `(minx,miny,maxx,maxy)` | 由 viewport 反推可见经纬度范围，做视口裁剪 |
| `render_water_polygons()` / `render_water_lines()` | — | `None` | 按 `min_scale` + bbox 双重筛选后逐个绘制，单要素异常静默跳过 |
| `render_water_polygon(feat, style)` / `render_water_line(feat, style)` | 要素 + 样式 | `None` | 投影后 `create_polygon` / `create_line`，打 `WATER_TAG` |
| `render_polygons()` / `render_lines()` | — | `None` | 视口裁剪后逐要素绘制，异常静默跳过 |
| `render_polygon(feat)` / `render_line(feat)` | 要素 | `None` | 单要素绘制，支持 `properties` 里的 `fill`/`stroke` 覆盖默认样式；分别打 `POLYGON_TAG` / `LINE_TAG` |
| `_point_lonlat(feat)` | 县点要素 dict | `(lon, lat)` / `(None, None)` | **从 `shapes_point` 元素中提取经纬度**。约定结构为 `{"geometry":{"type":"Point","coordinates":[lon,lat]}, "properties":{...}}`；非法结构返回 `(None, None)` 由调用方跳过 |
| `_point_radius(level, style)` | level、样式 | `float` | 按当前缩放与 `level` 计算县点像素半径：`clamp(span_px(bbox) / size_divisor × radius_by_level[level], min_radius, max_radius)` |
| `render_points()` | — | `None` | 视口 bbox 裁剪 + **按 `CITY_LEVEL_MIN_SCALE[level]` 做 LOD 过滤**后逐点绘制，打 `POINT_TAG` 与 `city_lv{level}` 双 tag；单要素异常静默跳过 |
| `render_point(lon, lat, feat, style)` | 经纬度、要素、样式 | `None` | 取 `level`（缺省 5，钳制 1–10）→ 查 `shape_by_level` / `radius_by_level` → 按形状 `create_oval`（圆）/ `create_polygon`（菱、三角）/ `create_rectangle`（方），支持 `properties.fill` 覆盖；打 `POINT_TAG` + `city_lv{level}` |
| `_road_width(difficulty)` | `difficulty` | `float` | 按当前缩放与 `difficulty` 计算道路像素宽度：`clamp(span_px(bbox) / width_divisor / max(difficulty, floor), min_width, max_width)` |
| `render_roads()` | — | `None` | 视口 bbox 粗筛后逐条 `create_line`；按 `round(difficulty, 2)` 缓存宽度；打 `ROAD_TAG`；单要素异常静默跳过 |
| `render_state_labels()` / `render_county_labels()` | — | `None` | 转调 `render_label_group` |
| `render_city_labels()` | — | `None` | 县名，额外按 `CITY_LEVEL_MIN_SCALE` 判断是否显示；`level` 来自 `GeoData`（已钳制到 1–10），取值用 `.get(level, 0)` 兜底，越界退化为"始终显示"而非抛异常。无标签出现，故**不做 bbox 预筛** |
| `render_label_group(labels, style_key)` | 标签列表 + 样式键 | `None` | 通用标签绘制，检查 `min_scale`/`max_scale`，逐标签投影 + 屏幕边界裁剪 |
| `draw_text(x, y, text, style)` | 屏幕坐标、文本、样式 | `None` | 绘制四方向白色描边 + 正文，打 `LABEL_TAG` |
| `resolve_style(key)` | 样式键 | `{...base, "size": int}` | 由地图总像素宽 ÷ `size_divisor` 动态算字号，钳制在 `[min_size, max_size]` |

调用者：全部由 `MapCanvas` 驱动（`draw_full` / `pan` / `zoom` / `refresh_dynamic`），`MapRenderer` 自身不引用任何 UI 事件。

#### 县点形状与半径分级

- **形状映射**（`shape_by_level`）：level 1–3 → 圆形（州治/郡治级大据点）；4–6 → 菱形（普通县城）；7–8 → 方形（小县）；9–10 → 三角形（村落/关隘级小聚落）。视觉权重随 level 递减。
- **半径公式**：`_point_radius` 用 `span_px(bbox) / size_divisor × radius_by_level[level]`，钳制在 `[min_radius, max_radius]`。随缩放动态变化，与道路线宽同一机制。
- **LOD 过滤**：`render_points` 用 `CITY_LEVEL_MIN_SCALE.get(level, 0)` 判断当前 `viewport.scale` 是否达到该等级的显示阈值——**与 `render_city_labels` 完全同一张表、同一个判断**，故县点与县名严格同显同隐。
- 越界 `level` 统一 `.get(level, 默认)` 兜底，不抛异常。

#### 叠放层级（从底到顶）

> 州面 → 郡界 → 湖泊 → 河流 → 道路 → 县点 → 州名 → 郡名 → 县名

- 州面、郡界为**静态层**，`draw_full` 后不再重建。
- 湖泊、河流、道路、**县点**、三类标签为**动态层**，由 `refresh_dynamic` 统一 delete → 重绘。
- **层级主要由 `refresh_dynamic` 内的绘制顺序决定**：Tk canvas 后画的盖先画的，故顺序固定为
  ```
  _draw_water() → render_roads() → render_points() → _draw_labels()
  ```
  这样标签天然位于最顶、县点在几何之上、水在最底。
- 再辅以 `canvas.tag_lower` 把动态几何压回静态层之下：
  - `tag_lower(ROAD_TAG, LINE_TAG)`：道路降到郡界之下
  - `tag_lower(WATER_TAG, ROAD_TAG)`：水域降到道路之下
  - `tag_lower(ROAD_TAG, POINT_TAG)`：道路降到县点之下（双保险）
  - 标签**不降**，保持最顶。
- `pan()` / `zoom()` 使用的 `canvas.move` / `canvas.scale` 不改变对象层级，无需额外处理。

> ⚠️ **维护提示 1**：`_draw_labels()` 必须保持在 `refresh_dynamic` 末尾调用。若图省事把它挪到开头，标签会沉到几何之下被县点/道路遮挡。

> ⚠️ **维护提示 2**：`_point_lonlat` 是 `render_points` 的必需依赖，**不可省略**。若缺失，`render_points` 会在第一行就抛 `AttributeError`，被 `except Exception: pass` 静默吞掉，症状为"县名标签正常显示，但一个县点都没有"。

---

### 3.9 [game/ui/main_window.py](game/ui/main_window.py)

**类 `MainWindow`** — 属性 `root`、`font_family`、`game_state`、`top_bar`、`map_canvas`、`side_panel`、`status_bar`。

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `__init__()` | — | — | 建 `Tk` → 标题/最小尺寸 → `maximize` → 选字体 → 建 `GameState` → `_setup_theme` → `_build_layout` → `_bind_shortcuts` → `after(120, _auto_load_default)` |
| `_pick_font_family()` | — | `str` | 从 `FONT_CANDIDATES` 选第一个系统可用字体，兜底 `"TkDefaultFont"` |
| `_setup_theme()` | — | `None` | ttk 切 `clam` 主题，配置 Frame/PanedWindow/Notebook 配色与 Tab 内边距 |
| `_build_layout()` | — | `None` | 装配三段式布局（见第 4 节），并挂接 `set_location_callback` / `set_zoom_callback` |
| `_bind_shortcuts()` | — | `None` | 全局快捷键：`+`/`=` 放大、`-` 缩小、`0` 复位、`Ctrl+O` 打开文件 |
| `_auto_load_default()` | — | `None` | 默认地图存在则静默加载，否则提示按 Ctrl+O |
| `open_geojson()` | — | `None` | 文件对话框选文件后调 `load_geojson` |
| `load_geojson(path, silent=False)` | 路径、静默标志 | `bool` | 转调 `map_canvas.load_geojson` → 复位视图 → 状态栏显示要素统计；异常时静默写状态栏或弹 `showerror` |
| `_on_location_change(text)` | 位置文本 | `None` | 转 `status_bar.set_location` |
| `_on_zoom_change(scale)` | 缩放比 | `None` | 转 `status_bar.set_zoom`，格式 `"缩放 27.3"` |
| `_on_menu_action(action, **kw)` | 动作名 | `None` | 菜单动作总线，见下表 |
| `_end_turn()` | — | `None` | `game_state.advance_turn()` → `side_panel.refresh_all()` → 状态栏提示新日期 |
| `_confirm_and_new_game()` | — | `None` | 二次确认后仅提示"尚未实现" |
| `run()` | — | `None` | `root.mainloop()` |

`_on_menu_action` 分支：`quit`→`root.quit()`；`new_game`→确认框；`load_game`→`open_geojson`；`save_game`→状态栏提示未实现；`view_zoom_in/out`、`view_reset`→转 `MapCanvas`；`view_cities/generals/troops`→`notebook.select(1/2/3)`；`end_turn`→`_end_turn`；`help_about`→`showinfo`；**其余全部落入 else**，仅状态栏显示 `[菜单] 动作名`。

---

### 3.10 [game/ui/top_bar.py](game/ui/top_bar.py)

**类 `TopBar(tk.Frame)`** — 属性 `game_state`、`font_family`、`on_action`、`items`（`key→(Label, StringVar)`）、`_popups`（`key→Toplevel`）、`_menus`（持有引用防 GC）、`end_turn_btn`。常量 `_REFRESH_INTERVAL_MS = 200`。

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `__init__(master, game_state, font_family, on_action=None)` | 父容器、状态、字体、回调 | — | `_build_left_info` → `_build_right_menus` → `_start_refresh` |
| `_build_left_info()` | — | `None` | 按 `get_display_items()` 顺序生成信息格（标签 + 加粗值 + 竖分隔线），绑定悬停与点击 |
| `_hover(cell, entering)` | 单元格、进入标志 | `None` | 切换底色 |
| `_open_info_window(key, title)` | 键、标题 | `None` | 打开 620×460 详情窗（已有则 `lift`），内容为占位文字 |
| `_close_info_window(key)` | 键 | `None` | 销毁弹窗并移出 `_popups` |
| `_build_right_menus()` | — | `None` | 生成 游戏/势力/命令/查看/帮助 五个 `Menubutton` + 绿色「进行 ▶」按钮 |
| `_make_menu_button(parent, text, build_fn)` | 父容器、文本、构建函数 | `Menubutton` | 通用菜单按钮工厂 |
| `_emit(action)` | 动作名 | `None` | 转发给 `on_action` |
| `_build_game_menu(m)` | `Menu` | `None` | 新游戏/读取存档/保存存档/游戏设置/退出 |
| `_build_faction_menu(m)` | `Menu` | `None` | 内政（开发·商业·农业）、军事（征兵·训练·出征）、外交（同盟·停战·劝降）、结束本回合 |
| `_build_order_menu(m)` | `Menu` | `None` | 移动/攻击/计略/待机 |
| `_build_view_menu(m)` | `Menu` | `None` | 缩放放大/缩小、地图复位、城市/武将/部队列表 |
| `_build_help_menu(m)` | `Menu` | `None` | 操作说明、关于 |
| `_start_refresh()` | — | `None` | 立即 `_refresh()` 并 `after(200ms, _start_refresh)` 自递归 |
| `_refresh()` | — | `None` | 轮询 `get_display_items()`，把新值 `set` 进对应 `StringVar` |

---

### 3.11 [game/ui/status_bar.py](game/ui/status_bar.py)

**类 `StatusBar(tk.Frame)`** — 三个 `StringVar`：`message_var`（左）、`zoom_var`（右）、`location_var`（右二）。

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `__init__(master, font_family)` | 父容器、字体 | — | 高 26px，三个 Label + 顶部 1px 分隔线 |
| `set_message(text)` | 文本 | `None` | 更新左侧系统提示 |
| `set_zoom(text)` | 文本 | `None` | 更新缩放显示 |
| `set_location(text)` | 文本 | `None` | 更新光标位置/地区名 |

---

### 3.12 [game/ui/map_canvas.py](game/ui/map_canvas.py)

**类 `MapCanvas(ttk.Frame)`** — 属性 `canvas`、`viewport`、`renderer`、`data`、`_drag`、`_label_job`、`_mouse_job`、`_pending_mouse`、`_settle_job`、`_location_callback`、`_zoom_callback`、`_need_fit`。常量 `_MIN_VALID_SIZE = 10`。

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `__init__(master, font_family)` | 父容器、字体 | — | 建内嵌 `tk.Canvas`，建 `Viewport` 与 `MapRenderer`；初始化 `_settle_job = None` 等实例变量；`_bind_events` |
| `set_location_callback(fn)` / `set_zoom_callback(fn)` | 回调 | `None` | 注册外部回调 |
| `_notify_zoom()` | — | `None` | 调 `_zoom_callback(viewport.scale)` |
| `load_geojson(path)` | 路径 | `GeoData` | `GeoData.from_file` → **若 `DEFAULT_ROADS_PATH` 存在则 `data.load_roads(...)`（失败静默忽略）** → `renderer.set_data` → `_need_fit=True` → `_try_fit_now()` |
| `reset_view()` | — | `None` | 主动复位：尺寸有效则 `fit_to_bbox` + `draw_full`，否则挂起 `_need_fit` |
| `zoom(factor, anchor=None)` | 倍率、锚点 | `None` | `viewport.zoom` → `_notify_zoom` → `renderer.zoom` → `_schedule_label_refresh` → **`_schedule_settle_redraw`** |
| `_try_fit_now()` | — | `None` | 尺寸有效且 `_need_fit` 时执行 `fit_to_bbox` + `draw_full` |
| `_bind_events()` | — | `None` | 绑定滚轮、Button-4/5、左键按下/拖动/释放、双击、Motion、Leave、Configure |
| `_on_wheel(event)` | 事件 | `None` | `delta>0` 放大 1.2，否则缩小 |
| `_on_press/_on_drag/_on_release(event)` | 事件 | `None` | 拖拽平移：`viewport.pan_pixels` + `renderer.pan` + 节流刷新动态层 |
| `_on_resize(event)` | 事件 | `None` | 更新画布尺寸；`_need_fit` 时 fit，否则 `draw_full`（**不改缩放比例**，避免拖分隔条重置视野） |
| `_on_motion(event)` | 事件 | `None` | 缓存坐标，40 ms 节流后处理 |
| `_process_motion()` | — | `None` | `unproject` → `find_location` → 拼 `"州 · 郡 · 县 （经度, 纬度）"` → 回调 |
| `_on_leave(event)` | 事件 | `None` | 清空位置显示 |
| `_sync_canvas_size()` | — | `None` | 从 `winfo_width/height` 同步到 viewport |
| `_schedule_label_refresh()` | — | `None` | 30 ms 节流调度 `_do_label_refresh` |
| `_do_label_refresh()` | — | `None` | 调 `renderer.refresh_dynamic()`（含水域、道路、**县点**、标签） |
| `_schedule_settle_redraw()` | — | `None` | **滚轮静默 180 ms 后补一次全量重绘**：取消旧 `_settle_job`、挂新的 `after(180, _settle_redraw)`。连续滚动期间计时器被反复重置，不触发重绘 |
| `_settle_redraw()` | — | `None` | `_settle_job=None`；若 `_need_fit` 或 `data` 为空则直接返回，否则调 `renderer.draw_full()`。用于补齐快速缩放过程中"触发 `draw_full` 的瞬间视图 ≠ 最终稳定视图"造成的边缘州郡缺失 |

> **为什么需要 settle redraw**：`draw_full` 由 `_cum_scale` 累积超阈值触发，触发点按**当时**视口裁剪静态几何。快速放大后又快速缩小，`draw_full` 可能在"视图还比较小"的中间时刻触发，停手后最终视图边缘的州郡面缺失。详见 6.3 节第 22、23 条。

---

### 3.13 [game/ui/side_panel.py](game/ui/side_panel.py)

**类 `SidePanel(ttk.Frame)`** — 属性 `game_state`、`notebook`。

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `__init__(master, game_state)` | 父容器、状态 | — | 建 `Notebook` + `_add_tabs` |
| `_add_tabs()` | — | `None` | 按顺序加入 势力(0) / 城市(1) / 武将(2) / 部队(3) |
| `refresh_all()` | — | `None` | 遍历所有 Tab，有 `refresh()` 方法的就调用 |

> **Tab 索引 1/2/3 被 `MainWindow._on_menu_action` 硬编码引用**。

---

### 3.14 [game/ui/window_utils.py](game/ui/window_utils.py)

| 函数 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `maximize(window)` | `Tk`/`Toplevel` | `None` | 三级降级：`state("zoomed")` → `attributes("-zoomed")` → 手动铺满屏幕 |
| `center_on_parent(child, parent, width, height)` | 子窗、父窗、宽高 | `None` | 相对父窗居中并夹在屏幕范围内 |

---

### 3.15 panels 四件套

| 文件 | 类 | 方法 | 说明 |
|---|---|---|---|
| [faction_panel.py](game/ui/panels/faction_panel.py) | `FactionPanel(ttk.Frame)` | `__init__(master, game_state)`、`_build_info_grid(parent)` | 9 行信息表；势力名称/威望/金钱/军粮取自 `game_state`，**君主「刘备」、都城「江陵」硬编码**，城市/武将/部队为 `"—"`。**无 `refresh()` 方法**，`refresh_all()` 会跳过它 |
| [city_panel.py](game/ui/panels/city_panel.py) | `CityPanel(ttk.Frame)` | `__init__`、`_build_toolbar`、`_build_tree`、`refresh()`、`_on_double_click(event)` | 5 列 Treeview；`refresh()` 仅清空，**无数据源**；双击 `print` 到控制台 |
| [general_panel.py](game/ui/panels/general_panel.py) | `GeneralPanel(ttk.Frame)` | `__init__`、`_build_toolbar`、`_build_tree`、`refresh()` | 7 列 Treeview（姓名/势力/统率/武力/智力/政治/所在），`refresh()` 仅清空 |
| [troop_panel.py](game/ui/panels/troop_panel.py) | `TroopPanel(ttk.Frame)` | `__init__`、`_build_toolbar`、`_build_tree`、`refresh()` | 5 列 Treeview（部队/主将/兵力/士气/状态），`refresh()` 仅清空 |

---

## 4. 程序完整运行流程

### 4.1 启动阶段

```
python main.py
└─ main.py: main()
   └─ MainWindow()                        ← game/ui/main_window.py:27
      ├─ tk.Tk() → title(APP_TITLE) → minsize(1024,640)
      ├─ maximize(root)                   ← window_utils.py，Windows 走 state("zoomed")
      ├─ _pick_font_family()              ← 遍历 FONT_CANDIDATES 命中即返回
      ├─ GameState()                      ← 读 constants 初始化 208年1月上旬 / 刘备 / 1000 / 5000 / 20000
      ├─ _setup_theme()                   ← ttk clam + 配色
      ├─ _build_layout()
      │  ├─ TopBar(root, game_state, font, on_action=self._on_menu_action) → grid(row=0)
      │  │  ├─ _build_left_info()         ← 轮询 get_display_items() 建 5 个信息格
      │  │  ├─ _build_right_menus()       ← 5 个下拉菜单 + 「进行 ▶」按钮
      │  │  └─ _start_refresh()           ← 启动 200ms 信息栏刷新定时器
      │  ├─ PanedWindow(horizontal) → grid(row=1, weight=1)
      │  │  ├─ MapCanvas(pane) → add(weight=4)
      │  │  │  ├─ tk.Canvas(pack fill both)
      │  │  │  ├─ Viewport()
      │  │  │  ├─ MapRenderer(canvas, viewport, font)
      │  │  │  ├─ __init__ 初始化 _settle_job=None 等
      │  │  │  └─ _bind_events()
      │  │  └─ SidePanel(pane) → add(weight=1)
      │  │     └─ Notebook + FactionPanel / CityPanel / GeneralPanel / TroopPanel
      │  ├─ map_canvas.set_location_callback(_on_location_change)
      │  ├─ StatusBar(root) → grid(row=2)，初始 "就绪"
      │  └─ map_canvas.set_zoom_callback(_on_zoom_change)
      ├─ _bind_shortcuts()                ← +/-/0/Ctrl+O
      └─ root.after(120, _auto_load_default) ← 延迟，等 canvas 拿到真实尺寸
   └─ run() → root.mainloop()
```

### 4.2 地图加载流程（120 ms 后）

```
_auto_load_default()
└─ load_geojson(assets/map.geojson, silent=True)
   ├─ MapCanvas.load_geojson(path)
   │  ├─ GeoData.from_file(path)
   │  │  ├─ _classify(states) → 13 州标签 + 13 州面 + 106 郡标签/郡界 + 1372 县点/县标签
   │  │  │  └─ _classify_county 内：先解析 level（int + 钳制 1–10）→ 再 shapes_point.append
   │  │  │     与 labels_city.append，两处共用同一 level 值
   │  │  ├─ _compute_bbox() → 全局外接矩形
   │  │  └─ _build_index() → 州面/郡界空间索引
   │  ├─ data.load_roads(assets/roads.geojson) ← 若文件存在；失败静默忽略
   │  ├─ renderer.set_data(data)
   │  ├─ _need_fit = True
   │  └─ _try_fit_now()                    ← 若此时 canvas 尺寸已有效，立即 fit；否则等 <Configure>
   │     ├─ viewport.fit_to_bbox(data.bbox)
   │     └─ renderer.draw_full()
   │        ├─ canvas.delete("all")
   │        ├─ _drawn = False
   │        ├─ _draw_geometry(): render_polygons → render_lines（静态层）
   │        ├─ _drawn = True               ← 必须在 refresh_dynamic 之前置位
   │        └─ refresh_dynamic():
   │           ├─ 守卫：if not _drawn: return
   │           ├─ delete(LABEL/WATER/ROAD/POINT)
   │           ├─ _draw_water() → render_roads() → render_points() → _draw_labels()
   │           │  ├─ 县点层：_point_lonlat 取坐标 → bbox 裁剪
   │           │  │  → CITY_LEVEL_MIN_SCALE[level] 过滤 → 半径按 span_px 重算
   │           │  └─ 县名层：同阈值过滤（与县点同显同隐）
   │           └─ tag_lower 归位（道路/水域降到静态层之下）
   └─ map_canvas.reset_view()              ← 再 fit 一次（幂等）
   └─ status_bar.set_message("已加载 map.geojson | 1491 个要素 | 州 13 / 郡 106 / 县 1372")
```

### 4.3 主循环中的交互

| 触发 | 调用链 |
|---|---|
| 滚轮 | `_on_wheel` → `MapCanvas.zoom` → `viewport.zoom`（改中心与比例）→ `_notify_zoom` → `StatusBar.set_zoom` → `renderer.zoom`（`canvas.scale("all")`，或 `_cum_scale` 超阈值时改为 `draw_full`）→ 30 ms 后 `_do_label_refresh` → `renderer.refresh_dynamic`（重绘**水域 + 道路 + 县点 + 标签**并 `tag_lower`）；县点与县名随缩放跨过 `CITY_LEVEL_MIN_SCALE` 阈值**同步浮现/消失**，县点半径同步重算；**同时** `_schedule_settle_redraw` 挂起 180 ms 静默计时器，停手后 `draw_full` 一次补齐边缘静态几何 |
| 左键拖拽 | `_on_press` 记起点 → `_on_drag` → `viewport.pan_pixels` → `renderer.pan` → `canvas.move("all")` → 30 ms 后水域/道路/县点/标签补漏（县点随 `refresh_dynamic` 重建，半径不变，仅位置刷新）。**注**：`pan` 不创建新对象，若拖出原 `draw_full` 的裁剪范围，静态州郡面可能暂时缺失，需滚轮触发下一次 `draw_full`（或等 settle 补绘）后才完整 |
| 双击 | `_on_press`/`_on_release` + `reset_view()` |
| 鼠标移动 | `_on_motion` 缓存坐标 → 40 ms 后 `_process_motion` → `viewport.unproject` → `data.find_location` → `_on_location_change` → `StatusBar.set_location` |
| 鼠标离开 | `_on_leave` → 清空位置栏 |
| 窗口/分隔条尺寸变化 | `<Configure>` → `viewport.set_canvas_size` → `_need_fit ? _try_fit_now() : renderer.draw_full()` |
| 「进行 ▶」/菜单"结束本回合" | `TopBar._emit("end_turn")` → `MainWindow._on_menu_action` → `_end_turn` → `GameState.advance_turn` → `SidePanel.refresh_all` → `StatusBar.set_message` |
| 菜单"城市/武将/部队列表" | `_on_menu_action` → `side_panel.notebook.select(1/2/3)` |
| 200 ms 定时器 | `TopBar._refresh` → `GameState.get_display_items()` → 更新各 `StringVar` |

### 4.4 模块协作关系

```
main.py
└─ ui.main_window ──┬─ ui.top_bar ──────┐
                    ├─ ui.status_bar    │ 均只读 core.game_state
                    ├─ ui.map_canvas ───┼─ map.viewport ─┐
                    │                   │ map.renderer ─┴─ map.geo_data ─ core.utils
                    └─ ui.side_panel ───┴─ ui.panels.*
                       config.constants / config.style（被所有层引用）
```

---

## 5. 全局变量与配置项

### 5.1 可通过 `constants.py` 调整

| 常量 | 影响 |
|---|---|
| `INITIAL_YEAR/MONTH/XUN` | 开局日期 |
| `INITIAL_FACTION` | 开局势力名（信息栏与势力面板显示） |
| `INITIAL_PRESTIGE/GOLD/FOOD` | 开局资源 |
| `MIN_WINDOW_SIZE` | 窗口最小尺寸 |
| `APP_TITLE` | 标题栏 |
| `DEFAULT_MAP_PATH` / `DEFAULT_WATER_PATH` / `DEFAULT_ROADS_PATH` | 自动加载路径 |

### 5.2 `style.py` 配置

| 项 | 影响 |
|---|---|
| `THEME` | 全部 UI 配色（信息栏/状态栏/面板/画布/工具栏背景及各前景色） |
| `FONT_CANDIDATES` | 中文字体优先级；缺失时回退 `TkDefaultFont` |
| `FONT_SIZES` | `info_bar/menu/status_bar/panel_title/panel_body` 五处字号 |
| `MAP_STYLE["polygon"/"line"]` | 州面填充描边、郡界线颜色 |
| `MAP_STYLE["point"]` | 县点颜色、描边、`size_divisor`、`min_radius`/`max_radius`、`shape_by_level`（level→形状）、`radius_by_level`（level→半径倍率） |
| `MAP_STYLE["road"]` | 道路颜色、`width_divisor`、`min_width`、`max_width`、`difficulty_floor` |
| `MAP_STYLE["water_polygon"/"water_line"]` | 湖泊/河流样式（**当前不生效，加载被注释**） |
| `MAP_STYLE["label_*"]` | 标签颜色、描边、`size_divisor`（越小字越大）、`min_size`/`max_size`、`min_scale`/`max_scale` 显隐区间 |
| `CITY_LEVEL_MIN_SCALE` | 县点与县名共用的分级显示阈值，**共 10 档（level 1–10）** |

### 5.3 代码内常量

| 位置 | 值 | 含义 |
|---|---|---|
| `MapCanvas._MIN_VALID_SIZE` | `10` | 小于此像素视为布局未完成，暂不 fit |
| `TopBar._REFRESH_INTERVAL_MS` | `200` | 信息栏轮询周期 |
| `MapRenderer.LABEL_TAG` / `WATER_TAG` / `ROAD_TAG` / `POINT_TAG` | `"label"` / `"water"` / `"road"` / `"point"` | 动态重绘的删除锚点（含县点） |
| `MapRenderer.POLYGON_TAG` / `LINE_TAG` | `"polygon"` / `"line"` | 静态图层锚点，用于 `tag_lower` 定位层级 |
| `MapRenderer._drawn` 语义 | `bool` | "几何层已画、动态层可叠加"。**必须在 `_draw_geometry()` 后、`refresh_dynamic()` 前置位** |
| `MapRenderer.refresh_dynamic` 绘制顺序 | 水 → 路 → 点 → 标签 | Tk 后画盖先画；标签最后画保证其位于最顶 |
| `MapRenderer._cum_scale` 阈值 | `(0.5, 2.0)` | 超出则全量重绘以消除 canvas 缩放误差 |
| `MapRenderer._point_radius` 公式 | `span_px / size_divisor × radius_by_level[level]` | 县点半径计算，钳制在 `[min_radius, max_radius]` |
| 县点 / 县名共用阈值 | `CITY_LEVEL_MIN_SCALE[level]` | 两者以此为准同显同隐，`level` 越界统一 `.get(level, 0)` 兜底 |
| `MapCanvas._schedule_settle_redraw` 静默时长 | `180 ms` | 滚轮停手后补绘的等待窗口 |
| `MAP_STYLE["road"]["width_divisor"]` | `2600` | 道路基准线宽分母；越大越细 |
| `MAP_STYLE["road"]["min_width"] / ["max_width"]` | `0.3` / `2.0` | 道路线宽绝对上下限（像素） |
| `MAP_STYLE["point"]["size_divisor"]` | `1100` | 县点基准半径分母；越大越小 |
| `MAP_STYLE["point"]["min_radius"] / ["max_radius"]` | `0.9` / `5.5` | 县点半径绝对上下限（像素） |
| 县 `level` 取值范围 | `1–10` | `GeoData._classify_county` 内 `max(1, min(10, level))` 钳制，缺省 `5` |
| `CITY_LEVEL_MIN_SCALE` 键集 | `1–10` | 与地图数据等级一一对应，越界由 `.get(level, 0)` 兜底 |
| `shape_by_level` / `radius_by_level` 键集 | `1–10` | 与 `level` 一一对应，越界由 `.get(level, 默认)` 兜底 |
| `GeoData.find_nearest_label` 上限 | `0.4`（度） | 县名匹配的最大距离 |
| `Viewport.fit_to_bbox` 边距 | `0.92` | 自适应缩放留白 |
| `_schedule_label_refresh` / `_on_motion` 节流 | `30 ms` / `40 ms` | 动态层刷新与鼠标查询节流 |
| `_assign_lod` 分档 | `0 / 15 / 45 / 100` | 水域按大小分四档 `min_scale` |

---

## 6. 已知逻辑限制与待完善清单

### 6.1 未实现功能（菜单已挂但无逻辑）

| 入口 | 现状 |
|---|---|
| 保存存档 `save_game` | 仅状态栏提示"尚未实现" |
| 读取存档 `load_game` | 复用了 `open_geojson`（打开地图文件，非存档） |
| 新游戏 `new_game` | 确认后仅提示"尚未实现" |
| 游戏设置 `settings` | 落入 else 分支，仅状态栏回显 |
| 内政（开发/商业/农业）、军事（征兵/训练/出征）、外交（同盟/停战/劝降）、命令（移动/攻击/计略/待机）、操作说明 | 全部落入 else 分支，仅状态栏显示 `[菜单] 动作名` |
| 信息项详情弹窗 | 开窗后为占位文字「这里将显示…的详细内容」 |
| 城市/武将/部队面板 | `refresh()` 只清空，无数据源、无数据模型 |

### 6.2 数据层缺失

- `GameState` 只有日期与四项资源，**没有武将池、城市数据库、部队、外交关系**；势力面板的「君主」「都城」为硬编码，其余统计项为 `"—"`。`city_panel._on_double_click` 只能 `print`。
- [assets/water.geojson](assets/water.geojson)（205 条河湖）加载调用在 [map_canvas.py:68-69](game/ui/map_canvas.py#L68-L69) **被注释掉**，导致：`DEFAULT_WATER_PATH` 无引用、`GeoData.load_water` / `_assign_lod` / `MapRenderer.render_water_*` / `WATER_TAG` / `MAP_STYLE["water_*"]` 全部为休眠代码。同时 [map_canvas.py:70-71](game/ui/map_canvas.py#L70-L71) 的空数据校验 `raise ValueError("文件里没有可绘制的坐标")` 也被注释。
- [assets/mountains.geojson](assets/mountains.geojson)（42 个山地区块，带 `passable`/`fill`/`stroke` 属性）**没有任何代码引用**，属于未接入资源。
- [assets/roads.geojson](assets/roads.geojson) 已接入渲染，但**仅用于视觉呈现**：`difficulty` 只影响线宽，未参与任何寻路/行军/补给计算；`from_id` / `to_id` / `length_km` / `effective_length_km` / `mountains_crossed` / `waters_crossed` / `mountain_pass` / `ferry` / `bridge` 等字段目前完全未被读取，是后续"行军路径规划""道路通行惩罚""关隘/渡口判定"的现成数据源。
- 路网与县点/郡界之间**没有建立拓扑关联**：`from_id` 是县 ID 字符串，但 `GeoData` 里县点没有以 ID 为键的索引，所以"点击某县高亮其相邻道路"这类需求需要先补一层 `id → 县点` 的映射。
- 县 `level` 字段已从 5 档扩展到 10 档，且已驱动**县点形状/半径**与**县名显隐**；但没有任何游戏逻辑（城市规模、人口、兵力上限、资源产出）挂在上面；后续建立 `City` 数据模型时应把它作为核心分级字段复用。

### 6.3 逻辑与性能限制

1. **无 LOD 分级（部分改善）**：`render_points` 已按 `CITY_LEVEL_MIN_SCALE[level]` 做 LOD 过滤，`render_lines`（106 条郡界）仍全量重绘、仅 bbox 视口裁剪。**县点因此从静态层移入动态层**：每次 zoom/pan 后 30 ms 都会重建全部可见点（bbox 裁剪后通常数十至数百个），配合县名同步刷新——这是"同显同隐"的必要代价，当前量级可接受；若后续出现卡顿，可让 `pan` 路径跳过县点/标签重建（平移不改变 scale，半径无需重算），只让 `zoom` 触发。
2. **`<Configure>` 全量重绘**：尺寸变化且非首次 fit 时无条件 `draw_full()`，拖动 PanedWindow 分隔条会触发连续全量重绘，可能卡顿；且**不调整缩放比例**（这是刻意设计，避免视野被重置）。
3. **异常静默吞掉**：`render_polygon` / `render_line` / `render_point` / `render_roads` / 水域绘制外层 `except Exception: pass`，几何出错时不报错也不提示，排查困难。县 `level` 越界、`_point_lonlat` 未实现这类问题都属于典型受害场景——因此必须在数据入口钳制、在查表处用 `.get`、在新方法上补"首次异常打一次日志"的策略。
4. **标签不做视口预筛**：`render_label_group` 与 `render_city_labels` 对每个标签都调 `project()` 再判断屏幕范围，未先按 bbox 裁剪；且每次 `refresh_dynamic` 都会重建全部标签对象（含每字 4 次描边绘制）。县点层已做 bbox 粗筛（`_visible_bounds`），但 `render_city_labels` 仍逐标签 `project()`，未预筛。
5. **空间索引为线性扫描**：`find_state_at` / `find_county_at` 遍历全部环做 bbox 粗筛 + 射线法，未建 R 树/网格；鼠标 40 ms 节流下勉强可用但非最优。
6. **只取外环**：`_build_index` 只用 `polygon[0]`，忽略多边形内环（孔洞），带洞的州面判定可能误判。
7. **县名匹配用固定 0.4° 距离**：`find_location` 的县名靠最近标签，边界或标签稀疏处可能匹配到邻县或返回 `None`。
8. **`midpoint_of_line` 为死代码**，无任何调用者（州名中点逻辑已内联在 `GeoData._classify`）。
9. **Tab 索引硬编码**：`MainWindow._on_menu_action` 用 `notebook.select(1/2/3)`，调整 `SidePanel._add_tabs` 顺序会静默错位。
10. **`FactionPanel` 缺少 `refresh()`**：`SidePanel.refresh_all()` 靠 `hasattr` 跳过，回合推进后势力面板数据不更新。
11. **`WINDOW_SIZE` 常量定义了但从未使用**（窗口走 `maximize`）。
12. **`GameState` 与地图数据无关联**：县点/州面只是图形，没有绑定归属势力、兵力、资源等游戏属性；`GameState` 也没有存档序列化接口。
13. **`_cum_scale` 复位时机**：全量重绘会清零累计缩放，因此长时间单向缩放时会出现周期性的全量重绘停顿。
14. **无测试、无打包、无 lint 配置**，`.claude/settings.local.json` 中的编译白名单还引用了已删除的 `menu_bar.py` / `info_bar.py`。
15. **道路无 LOD、无空间索引**：`render_roads` 每次全量遍历约 600 条线段做 bbox 粗筛，配合 `refresh_dynamic` 在每次缩放/平移后重建全部道路 canvas 对象。当前量级可接受，但道路若扩展到数千条，应优先给 `GeoData.roads` 建网格索引，并在低缩放级别下按 `road_type`（郡内道 → 郡间道 → 历史干道）分级显示。
16. **动态图层重建 + `tag_lower` 的额外开销**：`refresh_dynamic` 每次需 `delete` → 重绘 → `tag_lower` 三段操作；Tk 的 `tag_lower` 需要遍历该 tag 下所有对象并调整其在显示列表中的位置，对象数量越多成本越高。若日后卡顿，替代方案是给静态层打 tag 后将其整体上提 / 下压，而不是逐 tag 调整；或改为分层 `Canvas` 布局（每层一个独立 Canvas 叠放）。
17. **`CITY_LEVEL_MIN_SCALE` 是硬编码定长字典**：等级数量一旦再次变动（如改成 1–20），仍需手工同步；后续可改为「按 `min_level`/`max_level` + 指数曲线程序化生成」的方式，彻底免除手工维护。
18. **`shape_by_level` / `radius_by_level` 是定长字典**：与 `CITY_LEVEL_MIN_SCALE` 同样的手工同步问题——等级数量若再变，三张表都要改。后续可统一为「按 `min_level`/`max_level` + 曲线公式程序化生成」，一次免除维护。
19. **县点与县名"同显同隐"依赖同表同判**：两者都读 `CITY_LEVEL_MIN_SCALE`，但分处 `render_points` 与 `render_city_labels` 两处。若日后有人只改一处阈值，就会破坏一致性；建议后续抽出一个 `_visible_by_level(level, scale)` 公共方法统一判定。
20. **`_drawn` 置位时机是易错点（已修复，但需警惕回归）**：`_drawn` 同时被 `draw_full` 用作"几何层完成"标志、被 `refresh_dynamic` 用作执行守卫。`draw_full` 内**必须**在 `_draw_geometry()` 之后、`refresh_dynamic()` 之前置 `True`；一旦误置于方法末尾，首帧动态层会被守卫 `if not self._drawn: return` 跳过，表现为"开图只有州郡边界，鼠标一动/一缩放才补全"。文档已固化该顺序（见 3.8 节），修改 `draw_full` 时请勿调整这两行的相对位置。
21. **`refresh_dynamic` 的绘制顺序决定层级（易错点）**：Tk 后画盖先画，标签必须**最后**绘制才能位于最顶。当前正确顺序为 `_draw_water() → render_roads() → render_points() → _draw_labels()`，其中 `_draw_labels()` 保持在末尾。若调整顺序（例如把标签提到最前），标签会被县点/道路/水域遮挡；`tag_lower` 只调整几何层，不会挽救标签被埋的问题。
22. **`shapes_point` 的 `level` 解析必须先于 `append`（易错点）**：`_classify_county` 里 `level` 的两行解析（`int()` + 钳制）**必须在 `shapes_point.append` 之前**。顺序颠倒会抛 `UnboundLocalError: cannot access local variable 'level'`，异常沿 `GeoData.from_file` 冒泡，导致**地图完全不加载**（状态栏提示"自动加载失败"，画布空白）。Python 逐行执行，`level` 在 `append` 那行时还不存在。
23. **静态层依赖 `draw_full`，而 `draw_full` 由累计缩放触发（时机问题）**：州面、郡界仅在 `draw_full` 时按当时视口裁剪创建。快速放大后又快速缩小，`draw_full` 可能在"视图还比较小"的中间时刻触发，导致缩回后**最终视图边缘的州郡面缺失**，需再滚一下滚轮（累计缩放再次触发）才补齐。现通过"滚轮停手 180 ms 后补一次 `draw_full`"（`MapCanvas._schedule_settle_redraw`）缓解；根治方案是给静态层做增量补画或改用更大的裁剪留白。
24. **`_cum_scale` 触发点是"当前视图"，不是"最终视图"**：`draw_full` 按触发瞬间的 `_visible_bounds` 决定创建范围，与用户最终停手时的视口可能不一致。这是"边缘缺失"这类间歇性视觉 bug 的根源。任何"按当前视口裁剪 + 只在特定时机重建"的图层都可能复现同类问题。
25. **拖拽路径不做静态层补画**：`renderer.pan` 只调 `canvas.move("all", ...)`，不创建新对象。若拖出原 `draw_full` 时的裁剪范围，新进入视口的州面/郡界缺失。当前依赖"滚轮触发 `draw_full`"或"settle redraw"间接触发补画；若需要**拖拽后立即补全**，可在 `_on_release` 里检测位移超阈值后调 `renderer.draw_full()`（代价是松手一瞬间的刷新感）。

### 6.4 建议的下一步优先级

1. 接入 `water.geojson`（取消 `map_canvas.py` 注释）与 `mountains.geojson`（新增加载分支）。
2. 为州面/郡界加 `min_scale` LOD；`pan` 路径增加"新视口超出已绘制范围则补画"的判断，或让 `_on_release` 位移超阈值时补一次 `draw_full`，降低拖拽后静态层缺失的概率。
3. 建立 `General` / `City` / `Troop` 数据模型，填充三个列表面板并补 `FactionPanel.refresh()`。
4. 实现存档序列化（JSON）+ 保存/读取菜单。
5. 把县点与 `GameState` 的城市数据绑定，使地图点击可选中城市；把县 `level` 作为城市规模/人口/兵力的分级依据。
6. 给 `GeoData.roads` 建 `id → 县点` / `id → 道路列表` 索引，启用"点击城市高亮其相邻道路"，为行军路径规划做准备。
7. 给 `render_points` / `render_point` 的 `except Exception` 加上"首次异常打印一次日志"的逻辑（`self._point_err_logged` 标志），避免新 bug 被完全静默吞掉。