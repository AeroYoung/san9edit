下面是更新后的完整项目文档。本轮改动集中在 **3.5 / 3.10 / 5.3 / 6.3 / 变更日志**，另外项目概述的"核心功能"和"当前完成度"两处也顺带补了县名避让的描述。

---

# 暗耻三国志 — 项目说明文档

## 1. 项目概述

| 项 | 内容 |
|---|---|
| 项目名称 | 暗耻三国志（`APP_TITLE`） |
| 定位 | 三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》 |
| 程序入口 | [main.py](main.py) → `MainWindow().run()` |
| 核心功能 | 中国全图矢量渲染（州/郡/县三级 GeoJSON + 道路路网 + **水域湖泊/河流**，**县点按 level 分形状/尺寸并与县名同阈值显隐，县名按点半径上移避让**）、鼠标缩放平移、光标位置反查行政区、旬回合制时钟、顶部信息栏与菜单、右侧 Tab 面板框架、**可视化设置窗口（本地持久化 + 一键恢复默认 + 图层显隐）** |
| 运行环境 | Python 3（实测 3.14）+ 标准库 `tkinter`。仅依赖标准库，**无第三方依赖、无 requirements.txt** |
| 数据来源 | [assets/map.geojson](assets/map.geojson)：13 州 / 106 郡 / 1372 县（`states → counties → cities` 三层嵌套，县 `level` 取值 **1–10**）；[assets/roads.geojson](assets/roads.geojson)：约 600 条道路线段；[assets/water.geojson](assets/water.geojson)：205 条河流/湖泊（**已接入渲染**）；[assets/mountains.geojson](assets/mountains.geojson)：42 个山地区块（**未接入**） |
| 用户数据 | [userdata/settings.json](userdata/settings.json)：设置覆盖，仅保存与默认值不同的项；目录不存在时自动创建 |
| 平台 | Windows 优先（`maximize()` 兼容 Win/Linux/macOS） |

**当前完成度**：地图查看器（含路网与水域、图层显隐、县点尺寸分级、县名避让）已完整可用；设置系统已可用并持久化；回合与资源为骨架；内政/军事/外交/存档均为空实现。

---

## 2. 文件结构清单

```
san9edit/
├── main.py                     启动入口，创建并运行 MainWindow
├── README.md                   本文档
├── assets/
│   ├── map.geojson             主地图：州面 + 郡界 + 县点 + 三级标签坐标（1.5 MB）
│   ├── roads.geojson           道路路网：LineString 线段（约 600 条）
│   ├── water.geojson           河流/湖泊（205 要素），已接入渲染
│   └── mountains.geojson       山地/关隘（42 要素，含 passable），无任何代码引用
├── userdata/                   用户数据目录（运行时自动创建）
│   └── settings.json           设置覆盖文件，只存与 style.py 默认值不同的项
└── game/
    ├── __init__.py             包声明，无逻辑
    ├── config/
    │   ├── __init__.py         空
    │   ├── constants.py        路径、窗口尺寸、初始年份/势力/资源的全局常量
    │   ├── style.py            UI 主题色、字体候选、地图绘制样式、县名分级显隐阈值、
    │   │                       图层显隐开关（LAYER_VISIBILITY）
    │   ├── settings_manager.py 设置数据层：默认快照 + 覆盖合并 + 就地写回 style
    │   └── settings_schema.py  设置 UI 元数据：分组（GROUPS）与条目（ITEMS）
    ├── core/
    │   ├── __init__.py         空
    │   ├── game_state.py       回合/日期/资源的数据模型，信息栏数据源
    │   └── utils.py            几何通用工具（坐标展开、点在多边形内）
    ├── map/
    │   ├── __init__.py         空
    │   ├── geo_data.py         GeoJSON 解析、图层分类、空间索引与点查询
    │   ├── viewport.py         视图状态：中心经纬度、缩放比、投影/反投影
    │   └── renderer.py         地图绘制（几何层 + 文字层 + 图层显隐守卫），与 UI 事件解耦
    └── ui/
        ├── __init__.py         空
        ├── main_window.py      主窗口：组装部件、跨模块事件与业务
        ├── top_bar.py          顶部栏：左侧信息项 + 右侧菜单与「进行」按钮
        ├── status_bar.py       底部状态栏：提示 / 缩放 / 位置三段
        ├── map_canvas.py       地图画布：整合 viewport + renderer + 鼠标交互
        ├── side_panel.py       右侧 Notebook 容器 + 统一刷新入口
        ├── settings_window.py  设置窗口本体
        ├── window_utils.py     窗口最大化、相对父窗居中
        ├── widgets/
        │   ├── __init__.py     空
        │   └── collapsible.py  折叠分组控件
        └── panels/
            ├── __init__.py     空
            ├── faction_panel.py   势力信息（占位，部分硬编码）
            ├── city_panel.py      城市列表 Treeview（空数据）
            ├── general_panel.py   武将列表 Treeview（空数据）
            └── troop_panel.py     部队列表 Treeview（空数据）
```

> `.claude/`、`__pycache__` 为工具/环境产物，不属于项目源码。
> `userdata/` 属于**运行期产物**：删掉即可"恢复出厂设置"。

**依赖方向单向**：`main → ui → map/core → config`。

---

## 3. 模块与函数清单

### 3.1 [main.py](main.py)

| 函数 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `main()` | — | `None` | 实例化 `MainWindow` 并调用 `run()` 进入事件循环 |

---

### 3.2 [game/config/constants.py](game/config/constants.py)

纯常量模块。

| 常量 | 值 | 说明 |
|---|---|---|
| `PROJECT_ROOT` | `Path(__file__).parents[2]` | 项目根 |
| `ASSETS_DIR` | `PROJECT_ROOT/"assets"` | 资源目录 |
| `DEFAULT_MAP_PATH` | `assets/map.geojson` | 启动自动加载 |
| `DEFAULT_ROADS_PATH` | `assets/roads.geojson` | 随主地图自动加载 |
| `DEFAULT_WATER_PATH` | `assets/water.geojson` | 随主地图自动加载（**已启用**） |
| `APP_TITLE` | `"暗耻三国志"` | 窗口标题 |
| `WINDOW_SIZE` | `"1440x900"` | 保留常量，未使用 |
| `MIN_WINDOW_SIZE` | `(1024, 640)` | 窗口最小尺寸 |
| `INITIAL_YEAR/MONTH/XUN` | `208 / 1 / 1` | 初始日期（上旬） |
| `INITIAL_FACTION` | `"刘备"` | 初始玩家势力 |
| `INITIAL_PRESTIGE/GOLD/FOOD` | `1000 / 5000 / 20000` | 初始资源 |

---

### 3.3 [game/config/settings_manager.py](game/config/settings_manager.py)

**职责**：加载默认值 → 合并本地覆盖 → **就地**写回 `style.py` 的字典对象 → 提供读写/恢复/保存接口。

**关键设计**：

- `apply()` **就地修改** `style.py` 的字典而非替换，保证所有 `from game.config.style import X` 的模块自动看到新值。
- 本地文件只保存"与默认值不同的项"，用点号路径做 key：

  ```json
  {
    "version": 1,
    "overrides": {
      "THEME.info_bg": "#1A2530",
      "MAP_STYLE.point.size_divisor": 900,
      "CITY_LEVEL_MIN_SCALE.7": 320,
      "LAYER_VISIBILITY.water": true
    }
  }
  ```

**模块级数据结构**

| 名称 | 说明 |
|---|---|
| `_DEFAULTS` | 首次 import 时对 `style.py` 中 `THEME / FONT_SIZES / FONT_CANDIDATES / MAP_STYLE / CITY_LEVEL_MIN_SCALE / LAYER_VISIBILITY` 的深拷贝快照 |

**模块级工具函数**

| 函数 | 用途 |
|---|---|
| `_find_key_in_dict(d, key_str)` | 在 dict 中找 key（先试字符串，再试 `int`） |
| `_get_child(d, key_str)` | 找不到抛 `KeyError` |
| `_coerce(value, template)` | 按 template 类型转 JSON 值；dict 递归 |
| `_apply_inplace(target, source)` | 把 source 的叶子值写回 target，**保持对象 id 不变** |

**类 `SettingsManager`**

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `__init__(path=None)` | 可选路径 | — | 默认 `PROJECT_ROOT/userdata/settings.json`；执行 `load()` + `apply()` |
| `load()` / `save()` | — | `None` | 覆盖合并 / 写盘（父目录自动创建） |
| `get(path_str)` / `get_default(path_str)` | 点号路径 | 值 | 读 current / defaults |
| `set(path_str, value)` / `set_many(mapping)` | 路径、值 | `None` | 写 current |
| `reset_all()` / `reset_paths(paths)` | — / 路径列表 | `None` | 恢复默认 |
| `apply()` | — | `None` | **就地**写回 style 的各字典；`FONT_CANDIDATES` 重新替换 tuple |
| `register_listener(fn)` / `notify(changed_paths)` | 回调 | `None` | 观察者（当前未使用） |
| `changed_paths()` / `has_overrides()` | — | `list[str]` / `bool` | 差异查询 |

**内部方法**：`_get_from` / `_set_into`（static，点号路径读写）、`_compute_overrides` / `_diff`（递归差异）。

---

### 3.4 [game/config/settings_schema.py](game/config/settings_schema.py)

纯数据模块。

**常量 `GROUPS`**

| key | 标题 | 是否需重启 |
|---|---|---|
| `theme` | 界面主题 | **是** |
| `font` | 字体与字号 | **是** |
| `polygon` | 州面样式 | 否 |
| `line` | 郡界样式 | 否 |
| `point` | 县点样式 | 否 |
| `road` | 道路样式 | 否 |
| `water` | 水域样式 | 否 |
| `label_state` | 州名标签 | 否 |
| `label_county` | 郡名标签 | 否 |
| `label_city` | 县名标签 | 否 |
| `lod` | 分级显隐 | 否 |
| `visibility` | 图层显隐 | 否 |

**常量 `ITEMS`** — 每个元素：

| 字段 | 含义 |
|---|---|
| `path` | 点号路径 |
| `group` | 归属分组 |
| `type` | `color` / `int` / `float` / `bool` / `choice` / `level_table` |
| `label` / `desc` | 中文标签 / 描述 |
| `min` / `max` / `step`（可选） | 数值范围 |
| `value_suffix`（可选） | 数值后缀，如 `" px/度"` |
| **`hidden`（可选）** | **`True` 表示不在 UI 中显示**，用于临时屏蔽尚未接入的图层项 |

`type="level_table"` 额外字段：`value_type`（`int` / `float` / `choice`）、`choices`、`min` / `max` / `step`。

**当前 `hidden=True` 的项**：`LAYER_VISIBILITY.mountain`（山地未接入渲染，UI 隐藏但 `style.py` 里字段保留，默认 `False`；将来接入时删除 `hidden` 即可）。

**便捷函数**：`items_of_group` / `group_of` / `paths_of_group` / `group_meta`。

---

### 3.5 [game/config/style.py](game/config/style.py)

纯配置模块。**运行时以 `SettingsManager.current` 为准**；本文件仅作"默认值来源"。

| 名称 | 结构 | 说明 |
|---|---|---|
| `THEME` | dict | UI 配色 |
| `FONT_CANDIDATES` | tuple | 中文字体优先级 |
| `FONT_SIZES` | dict | 五处 UI 字号 |
| `MAP_STYLE` | dict | 地图样式：`polygon` / `line` / `point` / `road` / `water_polygon` / `water_line` / `label_state` / `label_county` / `label_city` |
| `CITY_LEVEL_MIN_SCALE` | dict | 县名/县点按 `level` 显隐阈值，共 10 档 |
| `LAYER_VISIBILITY` | dict | 图层显隐总开关 |

**当前关键样式值（最新）**：

```python
"polygon": {
    "fill":    "#E5D9BC",   # 暖米黄：州面底色，偏亮偏暖
    "outline": "#6B4226",   # 深咖啡：州界用墨线感，最重
    "width":   1,
},
"line": {
    "color": "#B0A085",     # 浅灰褐：郡界用细线，最轻
    "width": 1,
},
"road": {
    "color": "#B5442C",     # 暗砖红：道路明显偏暖偏红，一眼区分
    "width_divisor": 2600,
    "min_width": 0.2,
    "max_width": 2.0,
    "difficulty_floor": 1.0,
},
"point": {
    "fill": "#3b2a1a",      # 填充色
    "outline": "#f2e6cc",   # 描边色（浅色，暗底上提亮轮廓）
    "outline_width": 0.6,   # 描边宽（像素）
    "size_divisor": 820,    # 地图总像素宽 ÷ 此值 = 基准半径
    "min_radius": 1.3,      # 半径下限（像素）
    "max_radius": 7.0,      # 半径上限（像素）
    # shape_by_level / radius_by_level 见 style.py（10 档定长）
},
"label_city": {
    "color": "#7A3B00", "halo": "#FFFFFF",
    "size_divisor": 140, "min_size": 8, "max_size": 16,
    "min_scale": 30,
    "point_gap": 3,         # 县名与县点边缘之间的额外视觉间隙（像素）
},
```

四层的视觉层次：

| 层 | 颜色 | 效果 |
|---|---|---|
| 州面 | `#E5D9BC` 暖米黄 | 大面积底色，像古纸 |
| 州界 | `#6B4226` 深咖啡 | 深墨线，一眼看出省级划分 |
| 郡界 | `#B0A085` 浅灰褐 | 淡细线，不抢州界视觉重心 |
| 道路 | `#B5442C` 暗砖红 | 色相与褐色/米色拉开，暖底上醒目 |

**`LAYER_VISIBILITY` 结构**：

| 键 | 默认 | 含义 |
|---|---|---|
| `polygon` | `True` | 州面 |
| `line` | `True` | 郡界 |
| `point` | `True` | 县点 |
| `road` | `True` | 道路 |
| **`water`** | **`False`** | **水域（已接入，默认关，用户可在设置里开启）** |
| `mountain` | `False` | 山地（未接入，设置窗口已隐藏此项） |
| `label_state` | `True` | 州名标签 |
| `label_county` | `True` | 郡名标签 |
| `label_city` | `True` | 县名标签 |

**维护要点**：

- 运行期由 `SettingsManager.apply()` 就地修改本文件的 dict，**不要在其他模块中替换它们**。
- `CITY_LEVEL_MIN_SCALE` 数值必须**严格单调递增**。
- 三张定长字典（`CITY_LEVEL_MIN_SCALE` / `shape_by_level` / `radius_by_level`）需同步维护，越界由 `.get(level, 默认)` 兜底。
- `MAP_STYLE["point"]` 的三个字段（`size_divisor` / `min_radius` / `max_radius`）共同决定县点观感：只改其一会导致"分级感丢失"或"小点被钳死"。调整时建议三个一起动，`radius_by_level` 保持不动。

---

### 3.6 [game/core/utils.py](game/core/utils.py)

| 函数 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `walk_coords(coords)` | 嵌套坐标 | 生成器，逐个 `(lon, lat)` | 递归展开 GeoJSON 坐标 |
| `midpoint_of_line(coords)` | 折线坐标 | `(lon, lat)` | **死代码** |
| `point_in_polygon(x, y, ring)` | 坐标 + 环 | `bool` | 射线法（含 `1e-12` 除零保护） |

---

### 3.7 [game/core/game_state.py](game/core/game_state.py)

**类 `GameState`**

| 方法 | 用途 |
|---|---|
| `__init__()` | 从 `constants` 初始化日期与四项资源 |
| `date_text()` | 格式化为 `"208年 1月上旬"` |
| `advance_turn()` | 推进一旬；旬>3 → 月+1；月>12 → 年+1 |
| `change_gold/food/prestige(delta)` | 资源变更，下限钳制 0 |
| `get_display_items()` | 信息栏数据源，5 项：date/faction/prestige/gold/food |

---

### 3.8 [game/map/geo_data.py](game/map/geo_data.py)

**类 `GeoData`**

实例属性：`shapes_polygon`、`shapes_line`、`shapes_point`、`shapes_water_line`、`shapes_water_polygon`、`roads`、`labels_state`、`labels_county`、`labels_city`、`bbox`、`feature_count`、`_state_index`、`_county_index`。

**`shapes_point` 元素结构**：

```python
{
    "geometry": {"type": "Point", "coordinates": [lon, lat]},
    "properties": {"县名": name, "level": level},   # level 已钳制到 1–10
}
```

**`labels_city` 元素结构**：`(lon, lat, name, level)` 四元组。**经纬度即县点坐标**（与 `shapes_point` 同源），渲染层若需要标签偏移，必须在绘制时自行计算，数据层不做分离。

**`roads` 结构**：`[(coords, difficulty, bbox), ...]`。

| 方法 | 用途 |
|---|---|
| `from_file(path)`（classmethod） | 读取 → `_classify` → `_compute_bbox` → `_build_index` |
| `load_water(path)` | 按几何类型分流为河/湖，算 bbox 与 size，再 `_assign_lod` |
| `load_roads(path)` | 只解析 `LineString`，提取 `coordinates` + `difficulty`（默认 1.3），逐条算 bbox |
| `_classify(states)` / `_classify_county(sname, county)` | 生成州/郡/县各图元与标签 |
| `_compute_bbox()` / `_build_index()` | 全局外接矩形 / 州郡环索引 |
| `_ring_bbox` / `_coords_bbox`（static） | 外接矩形 |
| `_assign_lod(features)`（static） | 按 size 降序分四档 `min_scale`：15%→0，15–40%→15，40–70%→45，其余→100 |
| `find_state_at` / `find_county_at` | 州/郡查询 |
| `find_nearest_label(lon, lat, cands, max_dist)`（static） | 取最近候选 |
| `find_location(lon, lat)` | 返回 `(州名, 郡名, 县名)` |

**县 `level` 字段约定**：

- 取值 **1–10**；解析时做 `int()` + `max(1, min(10, level))` 钳制；缺失/非法默认 `5`。
- **解析必须先于使用**：`_classify_county` 里 `level` 的两行解析**必须写在 `shapes_point.append` 之前**，否则会抛 `UnboundLocalError`，导致地图完全不加载。
- 同一循环内 `shapes_point` 与 `labels_city` 共用同一 `level` 值。

---

### 3.9 [game/map/viewport.py](game/map/viewport.py)

**类 `Viewport`** — 属性 `cx`、`cy`、`scale`、`width`、`height`。

| 方法 | 用途 |
|---|---|
| `set_canvas_size(w, h)` | 记录尺寸，最小 1 |
| `fit_to_bbox(bbox, margin=0.92)` | 居中对齐 + 自适应缩放 |
| `zoom(factor, anchor=None)` | 绕锚点缩放 |
| `pan_pixels(dx, dy)` | 像素位移 |
| `project(lon, lat)` / `unproject(x, y)` | 地理 ↔ 屏幕（Y 轴取反） |
| `span_px(bbox)` | 当前缩放下地图总宽（像素） |

---

### 3.10 [game/map/renderer.py](game/map/renderer.py)

**类 `MapRenderer`** — 常量 `LABEL_TAG` / `WATER_TAG` / `ROAD_TAG` / `POINT_TAG` / `POLYGON_TAG` / `LINE_TAG`；属性 `data` / `_drawn` / `_cum_scale`。

> **`_drawn` 语义**：表示"几何层已绘制完成、动态层可以叠加"。`draw_full` 中必须在 `_draw_geometry()` 之后、`refresh_dynamic()` **之前**置 `True`。

| 方法 | 用途 |
|---|---|
| `__init__(canvas, viewport, font_family)` | 绑定三者 |
| `set_data(geo_data)` | 注入数据 |
| `draw_full()` | 全量重绘：`delete("all")` → `_drawn=False` → 重置 `_cum_scale` → `_draw_geometry()` → **`_drawn=True`** → `refresh_dynamic()` |
| `pan(dx, dy)` | `canvas.move("all")`，O(1)；不补画新进入视口的静态几何 |
| `zoom(factor, mx, my)` | `canvas.scale("all")`；累计倍率超出 `[0.5, 2.0]` 时改为 `draw_full()` |
| `refresh_dynamic()` | 守卫 → 删除动态 tag → **按 水 → 路 → 点 → 标签 顺序重绘** → `tag_lower` 归位；水/路/点/标签各自由 `LAYER_VISIBILITY` 判断 |
| `_draw_geometry()` | 州面 → 郡界，各自按 `LAYER_VISIBILITY["polygon"|"line"]` 判断 |
| `_draw_labels()` | 州/郡/县三类标签，各自按 `LAYER_VISIBILITY["label_state"|"label_county"|"label_city"]` 判断 |
| `_draw_water()` | 湖泊 + 河流 |
| `_visible_bounds(margin_px=20)` | 由 viewport 反推可见经纬度范围 |
| `render_water_polygons()` / `render_water_lines()` | **开头按 `LAYER_VISIBILITY["water"]` 判断**；按 `min_scale` + bbox 双重筛选 |
| `render_water_polygon` / `render_water_line` | 投影后创建图形，打 `WATER_TAG` |
| `render_polygons()` / `render_lines()` | 视口裁剪后逐要素绘制 |
| `render_polygon` / `render_line` | 单要素绘制，支持 `properties` 里的 `fill`/`stroke` 覆盖 |
| `_point_lonlat(feat)` | 从 `shapes_point` 元素提取经纬度 |
| `_point_radius(level, style)` | `clamp(span_px / size_divisor × radius_by_level[level], min_radius, max_radius)` |
| `render_points()` | **开头按 `LAYER_VISIBILITY["point"]` 判断**；视口裁剪 + `CITY_LEVEL_MIN_SCALE[level]` LOD 过滤；打 `POINT_TAG` + `city_lv{level}` |
| `render_point(lon, lat, feat, style)` | 按 `shape_by_level` 走 `create_oval` / `create_polygon` / `create_rectangle` |
| `_road_width(difficulty)` | `clamp(span_px / width_divisor / max(d, floor), min_width, max_width)` |
| `render_roads()` | **开头按 `LAYER_VISIBILITY["road"]` 判断**；bbox 粗筛后逐条 `create_line`；按 `round(difficulty, 2)` 缓存宽度 |
| `render_state_labels` / `render_county_labels` / `render_city_labels` | 三类标签绘制。州/郡走 `render_label_group`；县名额外按 `CITY_LEVEL_MIN_SCALE` 判断，并按 `_point_radius(level) + size×0.5 + point_gap` 上移避让县点 |
| `render_label_group(labels, style_key)` | 通用标签绘制（州/郡，`anchor="center"`，**不做偏移**） |
| `draw_text(x, y, text, style)` | 四方向白色描边 + 正文，打 `LABEL_TAG` |
| `resolve_style(key)` | 由地图总像素宽 ÷ `size_divisor` 动态算字号 |

**顶部 import（关键）**：

```python
from game.config.style import MAP_STYLE, CITY_LEVEL_MIN_SCALE, LAYER_VISIBILITY
```

#### 县名避让（`render_city_labels`）

县名与县点共用同一经纬度（`labels_city` 的第 1、2 位就是县点坐标），而 `draw_text` 用 `anchor="center"`，若不加偏移必然盖住点。因此 `render_city_labels` 对每个县额外计算：

```
offset = _point_radius(level, MAP_STYLE["point"])   # 该县点当前像素半径
       + style["size"] * 0.5                        # 中文半高近似
       + MAP_STYLE["label_city"].get("point_gap", 3) # 视觉间隙
```

再以 `draw_text(x, y - offset, ...)` 落笔。

- **必须与 `_point_radius` 同源**：这样点半径随缩放/样式变化时，标签偏移自动跟随，不会在大缩放下重新贴上。
- **只作用于县名**：州名、郡名走 `render_label_group`，不受影响。
- **视口裁剪 `pad` 不变**：`pad = size * 2`，偏移量最大值约 `max_radius + size*0.5 + gap ≈ 7 + 8 + 3 = 18px`，仍小于或接近 `pad`，边缘标签裁掉一两个无感。

#### 叠放层级（从底到顶）

> 州面 → 郡界 → 湖泊 → 河流 → 道路 → 县点 → 州名 → 郡名 → 县名

- **层级主要由 `refresh_dynamic` 内的绘制顺序决定**：
  `_draw_water() → render_roads() → render_points() → _draw_labels()`
- 辅以 `canvas.tag_lower` 把动态几何压回静态层之下；标签**不降**。

> ⚠️ **维护提示 1**：`_draw_labels()` 必须保持在 `refresh_dynamic` 末尾调用。
> ⚠️ **维护提示 2**：`_point_lonlat` 是 `render_points` 的必需依赖。
> ⚠️ **维护提示 3**：`_drawn` 必须在 `_draw_geometry()` 后、`refresh_dynamic()` 前 `True`。
> ⚠️ **维护提示 4**：县名偏移必须走 `_point_radius`，不要硬编码像素值。

---

### 3.11 [game/ui/main_window.py](game/ui/main_window.py)

**类 `MainWindow`** — 属性 `root`、`font_family`、`settings`、`game_state`、`top_bar`、`map_canvas`、`side_panel`、`status_bar`、`_settings_win`。

| 方法 | 用途 |
|---|---|
| `__init__()` | 建 `Tk` → 标题/最小尺寸 → `maximize` → **`SettingsManager()` + `apply()`** → 选字体 → 建 `GameState` → `_setup_theme` → `_build_layout` → `_bind_shortcuts` → `after(120, _auto_load_default)` |
| `_pick_font_family()` | 从 `FONT_CANDIDATES` 选第一个可用 |
| `_setup_theme()` | ttk 切 `clam` 主题 |
| `_build_layout()` / `_bind_shortcuts()` | 布局 / 快捷键（`+`/`=`/`-`/`0`/`Ctrl+O`） |
| `_auto_load_default()` / `open_geojson()` / `load_geojson(path, silent=False)` | 地图加载 |
| `_on_location_change(text)` / `_on_zoom_change(scale)` | 转 `status_bar` |
| `_on_menu_action(action, **kw)` | 菜单总线；`settings` → `_open_settings` |
| `_end_turn()` | `advance_turn` → `refresh_all` → 状态栏 |
| `_confirm_and_new_game()` | 二次确认后仅提示"尚未实现" |
| `_open_settings()` | 单例打开 `SettingsWindow`；已存在则 `lift` |
| `_on_settings_applied(changed_paths)` | 若涉及地图样式/阈值/显隐 → `map_canvas.redraw()`；状态栏"设置已保存" |
| `run()` | `root.mainloop()` |

**`__init__` 关键顺序**：`SettingsManager` 创建并 `apply()` **必须早于**任何读取 `style.py` 的部件创建。

---

### 3.12 [game/ui/top_bar.py](game/ui/top_bar.py)

**类 `TopBar(tk.Frame)`** — 常量 `_REFRESH_INTERVAL_MS = 200`。

左侧信息格：按 `get_display_items()` 顺序生成，悬停高亮、点击弹详情窗（占位）。
右侧：五个 `Menubutton`（游戏 / 势力 / 命令 / 查看 / 帮助）+ 绿色「进行 ▶」按钮。

「游戏设置」通过 `_emit("settings")` 上报。

---

### 3.13 [game/ui/status_bar.py](game/ui/status_bar.py)

**类 `StatusBar(tk.Frame)`** — 三个 `StringVar`：`message_var` / `zoom_var` / `location_var`，方法 `set_message` / `set_zoom` / `set_location`。

---

### 3.14 [game/ui/map_canvas.py](game/ui/map_canvas.py)

**类 `MapCanvas(ttk.Frame)`** — 常量 `_MIN_VALID_SIZE = 10`。

| 方法 | 用途 |
|---|---|
| `__init__(master, font_family)` | 建 `tk.Canvas` + `Viewport` + `MapRenderer`；`_bind_events` |
| `set_location_callback` / `set_zoom_callback` | 注册回调 |
| `load_geojson(path)` | `GeoData.from_file` → **若 `DEFAULT_WATER_PATH` 存在则 `data.load_water(...)`（try/except 静默忽略）** → **若 `DEFAULT_ROADS_PATH` 存在则 `data.load_roads(...)`（try/except 静默忽略）** → `renderer.set_data` → `_need_fit=True` → `_try_fit_now()` |
| `reset_view()` | 主动复位 |
| `redraw()` | 设置变更后强制全量重绘（不改视图） |
| `zoom(factor, anchor=None)` | `viewport.zoom` → `_notify_zoom` → `renderer.zoom` → `_schedule_label_refresh` → `_schedule_settle_redraw` |
| `_try_fit_now()` | 尺寸有效且 `_need_fit` 时 fit |
| `_bind_events()` / `_on_wheel` / `_on_press` / `_on_drag` / `_on_release` / `_on_resize` / `_on_motion` / `_on_leave` | 鼠标/键盘事件 |
| `_process_motion()` | 40 ms 节流后 `unproject` → `find_location` → 回调 |
| `_schedule_label_refresh()` / `_do_label_refresh()` | 30 ms 节流刷新动态层 |
| `_schedule_settle_redraw()` / `_settle_redraw()` | 滚轮静默 180 ms 后补一次全量重绘 |

**水/路加载的守卫策略**：两者都用 `try/except Exception: pass` 包裹——加载失败不影响主地图渲染。如果水体不出现，最可能是 `load_water` 内部或 `render_water_*` 抛异常被静默吞掉。临时排查方法：把 `render_water_*` 里的 `except Exception: pass` 改为 `except Exception as e: print("[water]", e)`。

---

### 3.15 [game/ui/side_panel.py](game/ui/side_panel.py)

**类 `SidePanel(ttk.Frame)`** — Tab 顺序：势力(0) / 城市(1) / 武将(2) / 部队(3)。`refresh_all()` 遍历所有 Tab，有 `refresh()` 方法就调。

---

### 3.16 [game/ui/window_utils.py](game/ui/window_utils.py)

| 函数 | 用途 |
|---|---|
| `maximize(window)` | 三级降级：`state("zoomed")` → `attributes("-zoomed")` → 手动铺满 |
| `center_on_parent(child, parent, width, height)` | 相对父窗居中并夹在屏幕范围内 |

---

### 3.17 [game/ui/widgets/collapsible.py](game/ui/widgets/collapsible.py)

**类 `CollapsibleSection(tk.Frame)`** — 折叠分组控件。

| 属性 / 方法 | 说明 |
|---|---|
| `body` | 内容区 `tk.Frame`，把控件放这里 |
| `__init__(master, title, desc="", on_reset=None, expanded=False, font_family="TkDefaultFont")` | 建标题条（▶/▼ + 标题 + 「↺ 恢复本组默认」）+ 描述行 + body |
| `toggle()` / `set_expanded(flag)` | 展开/收起；收起时 `body.pack_forget` |

点击标题条任意部分都会 `toggle`。

---

### 3.18 [game/ui/settings_window.py](game/ui/settings_window.py)

**类 `SettingsWindow(tk.Toplevel)`** — 设置窗口本体。

**属性**：

| 属性 | 说明 |
|---|---|
| `settings` | `SettingsManager` |
| `font_family` | 字体 |
| `on_applied` | 保存后回调 |
| `draft` | `{path: value}`，所有改动先写这里 |
| `_rows` | `{path: {"setter": fn}}`，用于回填 |
| `_sections` | `{group_key: CollapsibleSection}` |
| `filter_var` / `only_modified_var` | 筛选状态 |
| **`_closing`** | **防重入标志；`_do_destroy` 与 `_on_save` 都会检查它** |

**构建**：

| 方法 | 用途 |
|---|---|
| `_build_toolbar()` | 搜索框 + 仅显示已修改 + 本地文件路径显示 |
| `_build_body()` | `Canvas + Scrollbar` 承载所有分组；内容区自适应宽度；绑定滚轮 |
| `_build_footer()` | 「恢复全部默认」「取消」「保存」+「已修改 N 项」 |
| `_populate()` | **遍历 GROUPS / ITEMS 生成行；`if it.get("hidden"): continue` 跳过隐藏项** |
| `_add_item_row(parent, item)` | 一行：左侧中文标签 + 描述；右侧按 `type` 派发控件 |

**控件构造**：

| 方法 | 类型 | 说明 |
|---|---|---|
| `_build_bool` | 勾选框 | 变更即写 draft |
| `_build_color` | 色块按钮 + hex 输入框 | 点色块 → `colorchooser.askcolor()`；hex 输入框失焦/回车时校验 `#RRGGBB` |
| `_build_number` | 输入框 + 单位标签 + 错误提示 | 回车/失焦时校验类型与范围 |
| `_build_choice` | `ttk.Combobox` | 显示中文，写 draft 时映射回原值 |
| `_build_level_table` | 5 列网格 | 每行 `Lv{n}` + 控件；`child_path = f"{path}.{level}"` |

**值读写与差异**：

| 方法 | 用途 |
|---|---|
| `_get(path)` | 优先 draft，否则 `settings.get(path)` |
| `_refresh_dirty_label()` | 更新底部「已修改 N 项」 |
| `_apply_filter()` | 按搜索 + 「仅显示已修改」筛选；**跳过 hidden 项**；`level_table` 用前缀匹配 |
| `_on_reset_group(section)` / `_on_reset_all()` | 恢复本组/全部默认 |

**保存 / 关闭（含防重入）**：

| 方法 | 流程 |
|---|---|
| `_on_save()` | ① `_closing` 守卫；② 找 `restart=True` 分组；③ `set_many` → `save` → `apply`；④ 清 draft + 更新计数；⑤ `on_applied(changed)`；⑥ **提前记住主窗 `main = self.master`**；⑦ **先 `_do_destroy()` 销毁自身**（避免后续焦点事件回填 draft）；⑧ 若有需重启分组 → **以 `parent=main` 弹 `showinfo`** |
| `_on_close()` | `_closing` 守卫 → 若 draft 非空 → `askyesnocancel`；"取消"中止；"是"走 `_on_save`；"否"丢弃 → `_do_destroy()` |
| `_do_destroy()` | **统一销毁入口**：`_closing` 加锁 → 解绑滚轮 → 释放 grab → `destroy()`；**不做 draft 检查** |
| `_on_wheel(event)` / `_unbind_wheel()` | 仅当鼠标位于本窗口时滚动；关闭时解绑 |

**窗口属性**：`transient(master)` + `grab_set()`（模态）、`940×660`、相对主窗居中。

> **`_closing` + `_do_destroy` 是修复"保存后无限循环"bug 的关键**：清空 draft 与销毁窗口之间若夹了模态弹窗，`showinfo` 的焦点变化会触发控件的 `<FocusOut>` 把值重新写回 draft，导致 `_on_close` 反复看到"未保存"。现在的顺序是 **清 draft → 销毁窗口 → 以主窗为 parent 弹提示**。

---

### 3.19 panels 四件套

| 文件 | 类 | 说明 |
|---|---|---|
| [faction_panel.py](game/ui/panels/faction_panel.py) | `FactionPanel` | 9 行信息表；君主/都城硬编码；**无 `refresh()`** |
| [city_panel.py](game/ui/panels/city_panel.py) | `CityPanel` | 5 列 Treeview；`refresh()` 仅清空 |
| [general_panel.py](game/ui/panels/general_panel.py) | `GeneralPanel` | 7 列 Treeview；`refresh()` 仅清空 |
| [troop_panel.py](game/ui/panels/troop_panel.py) | `TroopPanel` | 5 列 Treeview；`refresh()` 仅清空 |

---

## 4. 程序完整运行流程

### 4.1 启动阶段

```
python main.py
└─ main.py: main()
   └─ MainWindow()
      ├─ tk.Tk() → title(APP_TITLE) → minsize(1024,640)
      ├─ maximize(root)
      ├─ SettingsManager()                ← 从 userdata/settings.json 读覆盖
      │  ├─ load()                        ← 合并到 self.current
      │  └─ apply()                       ← 就地写回 style.py 的各 dict
      ├─ _pick_font_family()              ← 遍历（可能被覆盖的）FONT_CANDIDATES
      ├─ GameState()
      ├─ _setup_theme()                   ← ttk clam + THEME
      ├─ _build_layout()
      │  ├─ TopBar(...)
      │  ├─ PanedWindow(horizontal)
      │  │  ├─ MapCanvas(pane) → add(weight=4)
      │  │  └─ SidePanel(pane) → add(weight=1)
      │  ├─ StatusBar(root)
      │  └─ 挂接 location / zoom 回调
      ├─ _bind_shortcuts()
      └─ root.after(120, _auto_load_default)
   └─ run() → root.mainloop()
```

### 4.2 地图加载流程

```
_auto_load_default()
└─ load_geojson(assets/map.geojson, silent=True)
   └─ MapCanvas.load_geojson(path)
      ├─ GeoData.from_file(path)
      │  └─ _classify → 13 州 / 106 郡 / 1372 县
      │     └─ _classify_county 内：先解析 level → 再 shapes_point.append + labels_city.append
      ├─ if DEFAULT_WATER_PATH.is_file():
      │     try: data.load_water(...)   ← 河流/湖泊
      │     except: pass
      ├─ if DEFAULT_ROADS_PATH.exists():
      │     try: data.load_roads(...)   ← 道路
      │     except: pass
      ├─ renderer.set_data(data)
      ├─ _need_fit = True
      └─ _try_fit_now() → viewport.fit_to_bbox → renderer.draw_full()
         ├─ canvas.delete("all")
         ├─ _draw_geometry(): 州面 → 郡界（按 LAYER_VISIBILITY 判断）
         ├─ _drawn = True
         └─ refresh_dynamic():
            ├─ delete(LABEL/WATER/ROAD/POINT)
            ├─ _draw_water()      ← 若 water=True
            ├─ render_roads()     ← 若 road=True
            ├─ render_points()    ← 若 point=True
            ├─ _draw_labels()     ← 三类标签各自判断
            │  └─ render_city_labels 内：按 _point_radius 上移县名
            └─ tag_lower 归位
```

### 4.3 设置窗口流程

```
点击 「游戏 → 游戏设置」
└─ _open_settings() → 单例 SettingsWindow

用户修改控件
└─ 控件回调写 self.draft[path] → _refresh_dirty_label

用户点「保存」
└─ _on_save()
   ├─ _closing 守卫
   ├─ 找 restart 分组（theme / font）
   ├─ settings.set_many(draft) → save() → apply()
   ├─ 清 draft + 更新计数
   ├─ on_applied(changed_paths)  ← MainWindow._on_settings_applied
   │  ├─ 地图相关变更 → map_canvas.redraw()
   │  └─ 状态栏 "设置已保存"
   ├─ main = self.master
   ├─ _do_destroy()              ← 先销毁自身
   └─ 若需重启 → showinfo(parent=main)
```

### 4.4 主循环交互

| 触发 | 调用链 |
|---|---|
| 滚轮 | `MapCanvas.zoom` → `viewport.zoom` → `renderer.zoom`（或 `draw_full`）→ 30 ms `refresh_dynamic`；180 ms settle |
| 左键拖拽 | `viewport.pan_pixels` → `renderer.pan` |
| 双击 | `reset_view()` |
| 鼠标移动 | 40 ms `_process_motion` → `find_location` |
| `<Configure>` | `viewport.set_canvas_size` → fit 或 `draw_full` |
| 「进行 ▶」 | `_end_turn` |
| 菜单城市/武将/部队 | `notebook.select(1/2/3)` |
| 菜单游戏设置 | `_open_settings` |
| 设置保存 | `_on_settings_applied` |
| 200 ms 定时器 | `TopBar._refresh` |

### 4.5 模块协作关系

```
main.py
└─ ui.main_window ──┬─ config.settings_manager ─ config.style（就地 apply）
                    │                            └ config.settings_schema
                    ├─ ui.top_bar ──────┐
                    ├─ ui.status_bar    │ 均只读 core.game_state
                    ├─ ui.map_canvas ───┼─ map.viewport ─┐
                    │                   │ map.renderer ─┴─ map.geo_data ─ core.utils
                    ├─ ui.settings_window ─ ui.widgets.collapsible
                    └─ ui.side_panel ───┴─ ui.panels.*
                       config.constants / config.style（被所有层引用）
```

---

## 5. 全局变量与配置项

### 5.1 `constants.py`

| 常量 | 影响 |
|---|---|
| `INITIAL_YEAR/MONTH/XUN` / `INITIAL_FACTION` / `INITIAL_PRESTIGE/GOLD/FOOD` | 开局数据 |
| `MIN_WINDOW_SIZE` / `APP_TITLE` | 窗口 |
| `DEFAULT_MAP_PATH` / `DEFAULT_ROADS_PATH` / `DEFAULT_WATER_PATH` | 自动加载路径 |

### 5.2 设置窗口可改（`style.py` 默认值）

| 项 | 是否需重启 |
|---|---|
| `THEME` / `FONT_SIZES` / `FONT_CANDIDATES` | **是** |
| `MAP_STYLE` 全部子项 | 否 |
| `CITY_LEVEL_MIN_SCALE` | 否 |
| `LAYER_VISIBILITY`（`mountain` 已在 UI 隐藏） | 否 |

### 5.3 代码内常量

| 位置 | 值 | 含义 |
|---|---|---|
| `MapCanvas._MIN_VALID_SIZE` | `10` | 布局未完成阈值 |
| `TopBar._REFRESH_INTERVAL_MS` | `200` | 信息栏轮询周期 |
| `MapRenderer` 各 TAG | `"label"/"water"/"road"/"point"/"polygon"/"line"` | 图层锚点 |
| `MapRenderer._cum_scale` 阈值 | `(0.5, 2.0)` | 超出则全量重绘 |
| 县 `level` 取值范围 | `1–10` | 越界兜底 |
| `MAP_STYLE.label_city.point_gap` | `3` | 县名与县点边缘的视觉间隙（像素） |
| `GeoData.find_nearest_label` 上限 | `0.4°` | 县名匹配 |
| `Viewport.fit_to_bbox` 边距 | `0.92` | 缩放留白 |
| 节流 | `30 ms` / `40 ms` / `180 ms` | 标签刷新 / 鼠标查询 / settle |
| `SettingsManager` 本地路径 | `PROJECT_ROOT/userdata/settings.json` | 覆盖文件 |
| `SettingsWindow` 尺寸 | `940 × 660` | 初始大小 |

---

## 6. 已知逻辑限制与待完善清单

### 6.1 未实现功能

| 入口 | 现状 |
|---|---|
| 保存存档 / 新游戏 | 提示"尚未实现" |
| 读取存档 | 复用 `open_geojson` |
| 内政/军事/外交/命令/操作说明 | 落入 else，仅状态栏回显 |
| 信息项详情弹窗 | 占位文字 |
| 城市/武将/部队面板 | `refresh()` 只清空 |

### 6.2 数据层缺失

- `GameState` 只有日期与四项资源，无武将池/城市/部队/外交。
- **`assets/mountains.geojson` 无任何代码引用**；设置窗口里 `LAYER_VISIBILITY.mountain` 已 `hidden=True`（UI 隐藏），`style.py` 里字段保留默认 `False`。将来接入山地渲染时，删除 `settings_schema.ITEMS` 里该项的 `"hidden": True` 即可。
- `assets/roads.geojson` 只做视觉呈现：`difficulty` 仅影响线宽；`from_id` / `to_id` / `length_km` / `mountains_crossed` / `waters_crossed` 等字段完全未读取。
- 路网与县点/郡界之间无拓扑关联。
- 县 `level` 驱动渲染但未挂任何游戏逻辑。
- `labels_city` 的经纬度与县点坐标相同，标签避让完全靠渲染层计算，数据层不存"标签专用坐标"。

### 6.3 逻辑与性能限制

1. `render_lines`（106 条郡界）全量重绘、仅 bbox 视口裁剪。
2. `<Configure>` 全量重绘；**不调整缩放比例**（刻意设计）。
3. 绘制方法外层 `except Exception: pass`，几何出错静默。
4. 标签不做视口预筛。
5. 空间索引线性扫描。
6. `_build_index` 只取外环，忽略孔洞。
7. 县名匹配用固定 0.4° 距离。
8. `midpoint_of_line` 死代码。
9. Tab 索引硬编码在 `MainWindow._on_menu_action`。
10. `FactionPanel` 缺少 `refresh()`。
11. `WINDOW_SIZE` 定义了但从未使用。
12. `GameState` 与地图数据无关联，无存档接口。
13. `_cum_scale` 复位时机导致周期性全量重绘停顿。
14. 无测试、无打包、无 lint 配置。
15. 道路无 LOD、无空间索引。
16. 动态图层重建 + `tag_lower` 额外开销。
17. `CITY_LEVEL_MIN_SCALE` 硬编码定长。
18. `shape_by_level` / `radius_by_level` 同样问题。
19. 县点与县名"同显同隐"依赖同表同判，分处两处。
20. `_drawn` 置位时机是易错点。
21. `refresh_dynamic` 绘制顺序决定层级。
22. `shapes_point` 的 `level` 解析必须先于 `append`。
23. 静态层依赖 `draw_full`；快速缩放可能边缘州郡缺失，靠 180 ms settle 缓解。
24. `_cum_scale` 触发点是"当前视图"，不是"最终视图"。
25. 拖拽路径不做静态层补画。
26. **`SettingsManager.apply()` 必须就地修改 `style.py` 的字典**：若改成 `_style.MAP_STYLE = new_dict`，已 import 旧对象的模块将看不到新值。
27. **`SettingsManager` 必须在 `MainWindow.__init__` 早期创建并 `apply()`**，否则部分部件用旧默认值。
28. **`theme` / `font` 分组的 `restart=True` 是硬编码约定**，靠 `schema.GROUPS[...]["restart"]` 决定提示。
29. **`settings_schema.ITEMS` 与 `style.py` 结构必须一致**：path 不存在时控件静默空白，不报错。
30. **`level_table` 的 draft key 是 `path.LEVEL`**（如 `CITY_LEVEL_MIN_SCALE.7`），`_apply_filter` / `reset_paths` 都要处理带后缀的 key。
31. **`SettingsWindow` 的保存/关闭路径必须走 `_do_destroy()`**：直接 `self.destroy()` 会绕过 `_closing` 加锁，若再夹模态弹窗可能复现"保存后无限循环"。所有新增的关闭路径都要调用 `_do_destroy`。
32. **`items` 中 `hidden=True` 的项要在 `_populate` 和 `_apply_filter` 两处都跳过**：只加一处会导致搜索/筛选时漏出。
33. **`water.geojson` 加载**：`MapCanvas.load_geojson` 里用 `try/except Exception: pass` 包裹，任何解析异常被静默吞掉。水体不出现时先怀疑 `load_water` 或 `render_water_*` 内部抛异常，临时把 `except` 改为 `print` 排查。
34. **`LAYER_VISIBILITY.water` 默认 `False`**：即使已接入渲染，也需要用户在设置里开启或本地覆盖为 `true` 才显示。
35. **县名避让偏移必须与 `_point_radius` 同源**：`render_city_labels` 里的上移量 = `_point_radius(level, MAP_STYLE["point"]) + style["size"] * 0.5 + MAP_STYLE["label_city"].get("point_gap", 3)`。若日后点半径公式改动（新增 level 系数、调整 `size_divisor` 等），县名偏移会自动跟随；**不要**把偏移量硬编码成常数，否则点放大后标签会重新贴上。改 `MAP_STYLE["label_city"]` 时保留 `point_gap` 字段（缺省回退 3）。
36. **县点放大的三个字段联动**：`MAP_STYLE["point"]` 的 `size_divisor` / `min_radius` / `max_radius` 需一起调。只降 `size_divisor` 会让小点仍被 `min_radius` 钳死、大点更快撞 `max_radius`，呈现"只有大城变大"的失真。`radius_by_level` 不建议动，它是分级形状感的关键。

### 6.4 建议的下一步

1. 接入 `mountains.geojson`：新增 `GeoData.load_mountains` + `MapRenderer.render_mountains`，把 `LAYER_VISIBILITY["mountain"]` 的判断挂上去，然后删除 `settings_schema.ITEMS` 里对应项的 `"hidden": True`。
2. 为州面/郡界加 `min_scale` LOD；`pan` 路径补画新进入视口的静态几何。
3. 建立 `General` / `City` / `Troop` 数据模型，填充三个列表面板并补 `FactionPanel.refresh()`。
4. 实现存档序列化（JSON）+ 保存/读取菜单。
5. 把县点与 `GameState` 的城市数据绑定；把县 `level` 作为城市规模/人口/兵力的分级依据。
6. 给 `GeoData.roads` 建 `id → 县点` / `id → 道路列表` 索引。
7. 给绘制方法的 `except Exception` 加"首次异常打印一次日志"。
8. 设置系统扩展：
   - 导出/导入设置；
   - 主题预设；
   - `THEME` 做到即时生效（需遍历 widget 递归重配 bg/fg）；
   - `ITEMS` 半自动生成；
   - 未保存前的实时预览。

---

**变更日志（本轮）**

- **县点放大**：`game/config/style.py` 的 `MAP_STYLE["point"]`：`size_divisor` 1100→**820**、`min_radius` 0.9→**1.3**、`max_radius` 5.5→**7.0**。三个字段联动，全局放大 ≈1.34 倍，同时保留 `radius_by_level` 的 10 档分级感，避免小县城被下限钳死、大城被上限压平。`radius_by_level` / `shape_by_level` 未动。
- **县名避让**：`game/config/style.py` 的 `MAP_STYLE["label_city"]` 新增 `"point_gap": 3`；`game/map/renderer.py` 的 `render_city_labels` 改为对每个县按 `offset = _point_radius(level, MAP_STYLE["point"]) + style["size"] * 0.5 + point_gap` 上移后再 `draw_text`。偏移与点半径同源，随缩放/样式自动跟随；**只作用于县名**，州名/郡名走 `render_label_group` 不受影响。
- **文档同步**：3.5 节补充 `point` / `label_city` 当前值；3.10 节补"县名避让"小节；5.3 节加 `point_gap`；6.3 节新增第 35、36 条维护提示。

---

**上一轮变更日志（保留）**

- **水域接入**：`game/ui/map_canvas.py` 的 `load_geojson` 取消水域加载注释，用 `try/except Exception: pass` 包裹（与路网一致）。
- **山地 UI 隐藏**：`game/config/settings_schema.py` 中 `LAYER_VISIBILITY.mountain` 项加 `"hidden": True`；`game/ui/settings_window.py` 的 `_populate` 与 `_apply_filter` 跳过 hidden 项。`style.py` 字段保留默认 `False`。
- **设置窗口保存/关闭防重入**：`game/ui/settings_window.py` 新增 `_closing` 标志 + `_do_destroy()` 统一销毁入口；`_on_save` 改为"清 draft → 销毁自身 → 以主窗为 parent 弹重启提示"，修复"保存后无限循环"bug。
- **配色调整**：`style.py` 中 `polygon.fill` → `#E5D9BC`、`polygon.outline` → `#6B4226`、`line.color` → `#B0A085`、`road.color` → `#B5442C`，四层视觉拉开。

---

以上是完整文档。检查一下三处关键改动是否都在里面：

- **3.5 节**：`point` 的 `size_divisor=820 / min_radius=1.3 / max_radius=7.0`，`label_city` 的 `point_gap=3` ✅
- **3.10 节**：`render_city_labels` 的偏移公式 + "县名避让"小节 ✅
- **6.3 节**：第 35、36 条维护提示 ✅

你确认没问题就可以按文档里那三行改动实际动手了。改完如果有观感偏差（比如放大过头、标签离太远），回来说一声，我帮你微调 `size_divisor` / `min_radius` / `point_gap` 这三个旋钮。