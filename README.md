# 暗耻三国志 — 项目说明文档

## 1. 项目概述

| 项 | 内容 |
|---|---|
| 项目名称 | 暗耻三国志（`APP_TITLE`） |
| 定位 | 三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》 |
| 程序入口 | [main.py](main.py) → `MainWindow().run()` |
| 核心功能 | 中国全图矢量渲染（州/郡/县三级 GeoJSON + 道路路网，**县点按 level 分形状/尺寸并与县名同阈值显隐**）、鼠标缩放平移、光标位置反查行政区、旬回合制时钟、顶部信息栏与菜单、右侧 Tab 面板框架、**可视化设置窗口（本地持久化 + 一键恢复默认 + 图层显隐）** |
| 运行环境 | Python 3（实测 3.14）+ 标准库 `tkinter`。仅依赖标准库，**无第三方依赖、无 requirements.txt** |
| 数据来源 | [assets/map.geojson](assets/map.geojson)：13 州 / 106 郡 / 1372 县（`states → counties → cities` 三层嵌套，县 `level` 取值 **1–10**）；[assets/roads.geojson](assets/roads.geojson)：约 600 条道路线段 |
| 用户数据 | [userdata/settings.json](userdata/settings.json)：设置覆盖，仅保存与默认值不同的项；目录不存在时自动创建 |
| 平台 | Windows 优先（`maximize()` 兼容 Win/Linux/macOS） |

**当前完成度**：地图查看器（含路网与图层显隐）已完整可用；设置系统（`style.py` 全部可编辑项 + `LAYER_VISIBILITY`）已可用并持久化；回合与资源为骨架；内政/军事/外交/存档均为空实现。

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
├── userdata/                   用户数据目录（运行时自动创建）
│   └── settings.json           设置覆盖文件，只存与 style.py 默认值不同的项
└── game/
    ├── __init__.py             包声明，无逻辑
    ├── config/
    │   ├── __init__.py         空
    │   ├── constants.py        路径、窗口尺寸、初始年份/势力/资源的全局常量
    │   ├── style.py            UI 主题色、字体候选、地图绘制样式、县名分级显隐阈值、
    │   │                       图层显隐开关（`LAYER_VISIBILITY`）
    │   ├── settings_manager.py **设置数据层**：默认快照 + 覆盖合并 + 就地写回 style
    │   └── settings_schema.py  **设置 UI 元数据**：分组（GROUPS）与条目（ITEMS）
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
        ├── top_bar.py          顶部栏：左侧信息项（可点击弹窗）+ 右侧菜单与「进行」按钮
        ├── status_bar.py       底部状态栏：提示 / 缩放 / 位置三段
        ├── map_canvas.py       地图画布：整合 viewport + renderer + 鼠标交互
        ├── side_panel.py       右侧 Notebook 容器 + 统一刷新入口
        ├── settings_window.py  **设置窗口本体**
        ├── window_utils.py     窗口最大化、相对父窗居中
        ├── widgets/
        │   ├── __init__.py     空
        │   └── collapsible.py  **折叠分组控件**
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

> 设置文件的路径（`userdata/settings.json`）在 `SettingsManager.__init__` 内以 `C.PROJECT_ROOT / "userdata" / "settings.json"` 形式拼接，未抽为独立常量。

---

### 3.3 [game/config/settings_manager.py](game/config/settings_manager.py)

**职责**：加载默认值 → 合并本地覆盖 → **就地**写回 `style.py` 的字典对象 → 提供读写/恢复/保存接口。

**关键设计**：

- 因为 `renderer.py` 用 `from game.config.style import MAP_STYLE`（**模块级引用**），`apply()` 必须**就地修改 `style.py` 的字典**而非替换它。这样所有已 import 的模块自动看到新值，无需改动其读取方式。
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

- 用点号路径 + 存在性检查的方式读取，`style.py` 未来新增字段时，老配置文件不会报错（不存在的 override 直接忽略）。
- 类型合并时按默认值的类型做 `_coerce`，避免用户在 JSON 里塞了字符串而程序期望 int。

**模块级数据结构**

| 名称 | 说明 |
|---|---|
| `_DEFAULTS` | 首次 import 时对 `style.py` 中 `THEME / FONT_SIZES / FONT_CANDIDATES / MAP_STYLE / CITY_LEVEL_MIN_SCALE / LAYER_VISIBILITY` 的深拷贝快照。**它定义了"恢复默认"的权威来源**。 |

**模块级工具函数**

| 函数 | 用途 |
|---|---|
| `_find_key_in_dict(d, key_str)` | 在 dict 中找 key（先试字符串，再试 `int`），找不到返回 `None` |
| `_get_child(d, key_str)` | 类似上者，但找不到抛 `KeyError` |
| `_coerce(value, template)` | 按 template 的类型把 JSON 值转成合适的 Python 类型；dict 递归处理 |
| `_apply_inplace(target, source)` | 把 source 的叶子值写回 target，**保持 target 的对象 id 不变** |

**类 `SettingsManager`**

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `__init__(path=None)` | 可选路径 | — | 默认 `PROJECT_ROOT/userdata/settings.json`；执行 `load()` + `apply()` |
| `load()` | — | `None` | 从 `self.current`（先深拷贝默认值）开始，逐条合并本地文件中的 overrides |
| `save()` | — | `None` | 计算 diff → 写 JSON 到 `self.path`；父目录不存在时自动创建 |
| `get(path_str)` | 点号路径 | 任意值 | 读 `current` |
| `get_default(path_str)` | 点号路径 | 任意值 | 读 `defaults` |
| `set(path_str, value)` | 点号路径、值 | `None` | 写 `current`；不存在抛 `KeyError` |
| `set_many(mapping)` | `{path: value}` | `None` | 批量写，跳过不存在的 key |
| `reset_all()` | — | `None` | `current = deepcopy(defaults)` |
| `reset_paths(paths)` | 路径列表 | `None` | 把指定路径恢复为默认值（供"恢复本组默认"） |
| `apply()` | — | `None` | **就地**把 `current` 的叶子值写回 `style` 模块的各字典；`FONT_CANDIDATES` 重新替换 tuple |
| `register_listener(fn)` / `notify(changed_paths)` | 回调 | `None` | 观察者模式（当前未被使用，留给未来） |
| `changed_paths()` | — | `list[str]` | 列出与默认值不同的路径 |
| `has_overrides()` | — | `bool` | 是否有任何改动 |

**内部方法**

| 方法 | 用途 |
|---|---|
| `_get_from(root, path_str)`（static） | 按点号路径读取 |
| `_set_into(root, path_str, value)`（static） | 按点号路径写入 |
| `_compute_overrides()` | 生成给 JSON 用的 override 字典 |
| `_diff(default, current, prefix, out)` | 递归生成差异（含 dict 嵌套） |

**调用者**：`MainWindow.__init__` 创建唯一实例，并立刻 `apply()`；`SettingsWindow` 通过它读写。

---

### 3.4 [game/config/settings_schema.py](game/config/settings_schema.py)

纯数据模块，无类无函数（除几个便捷查询）。

**常量 `GROUPS`**

每个元素：`{"key", "title", "desc", "restart"(可选, True 表示需重启)}`。

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

**常量 `ITEMS`**

每个元素描述一个可编辑项：

| 字段 | 含义 |
|---|---|
| `path` | 点号路径，定位到 `style.py` 中的位置（如 `MAP_STYLE.point.size_divisor`） |
| `group` | 归属分组 |
| `type` | `color` / `int` / `float` / `bool` / `choice` / `level_table` |
| `label` | 中文标签 |
| `desc`（可选） | 中文描述 |
| `min` / `max` / `step`（可选） | 数值范围 |
| `value_suffix`（可选） | 数值后缀，如 `" px/度"` |

`type="level_table"` 的额外字段：

| 字段 | 含义 |
|---|---|
| `value_type` | 每行控件类型：`int` / `float` / `choice` |
| `choices` | `value_type=choice` 时的选项列表 `[(值, 中文), ...]` |
| `min` / `max` / `step` | 数值范围 |

**便捷函数**

| 函数 | 用途 |
|---|---|
| `items_of_group(group_key)` | 返回该组的所有 ITEMS |
| `group_of(path)` | 返回某路径所属分组 key |
| `paths_of_group(group_key)` | 返回该组所有路径 |
| `group_meta(group_key)` | 返回分组元信息 |

---

### 3.5 [game/config/style.py](game/config/style.py)

纯配置模块。**运行时以 `SettingsManager.current` 为准**；本文件仅作"默认值来源"。

| 名称 | 结构 | 说明 |
|---|---|---|
| `THEME` | dict | UI 配色：信息栏、状态栏、面板、画布、工具栏背景 |
| `FONT_CANDIDATES` | tuple | 中文字体优先级列表，`MainWindow._pick_font_family` 按序挑第一个可用 |
| `FONT_SIZES` | dict | 各 UI 元素字号偏移：`info_bar/menu/status_bar/panel_title/panel_body` |
| `MAP_STYLE` | dict | 地图样式：`polygon`（州面）、`line`（郡界）、`point`（县点，含形状/半径分级）、`road`（道路）、`water_polygon`、`water_line`，以及 `label_state/label_county/label_city` 三组标签样式 |
| `CITY_LEVEL_MIN_SCALE` | dict | 县名/县点按 `level` 显隐阈值，共 10 档 |
| `LAYER_VISIBILITY` | dict | **图层显隐总开关**，见下 |

`MAP_STYLE["point"]` 子项：`fill` / `outline` / `outline_width` / `size_divisor` / `min_radius` / `max_radius` / `shape_by_level`（10 档）/ `radius_by_level`（10 档）。

`MAP_STYLE["road"]` 子项：`color` / `width_divisor` / `min_width` / `max_width` / `difficulty_floor`。

`LAYER_VISIBILITY` 结构：

| 键 | 默认 | 含义 |
|---|---|---|
| `polygon` | `True` | 州面 |
| `line` | `True` | 郡界 |
| `point` | `True` | 县点 |
| `road` | `True` | 道路 |
| `water` | `False` | 水域（water.geojson 尚未接入渲染） |
| `mountain` | `False` | 山地（mountains.geojson 无任何引用） |
| `label_state` | `True` | 州名标签 |
| `label_county` | `True` | 郡名标签 |
| `label_city` | `True` | 县名标签 |

**维护要点**：

- 运行期由 `SettingsManager.apply()` 就地修改本文件里的这些 dict，**不要在其他模块中替换它们**（否则已 import 的模块会指向旧对象）。
- `CITY_LEVEL_MIN_SCALE` 的数值必须**严格单调递增**。
- `MAP_STYLE["point"]` 的 `shape_by_level` / `radius_by_level` 是定长字典（键 1–10），与 `CITY_LEVEL_MIN_SCALE` 三者需同步维护；越界由 `.get(level, 默认)` 兜底。

#### `CITY_LEVEL_MIN_SCALE` 说明

- 语义：该级别县 **在缩放 ≥ 对应值（像素/度）时才绘制**。**县点与县名共用此阈值**，两者严格同步显隐。
- 1 级为最重要据点，阈值 0，任何缩放下都可见；级别越大阈值越高，越晚出现。
- 调参方向：整体偏大 → 更稀疏；整体偏小 → 更密集。

---

### 3.6 [game/core/utils.py](game/core/utils.py)

| 函数 | 入参 | 返回 | 用途 | 调用者 |
|---|---|---|---|---|
| `walk_coords(coords)` | 任意嵌套坐标数组 | 生成器，逐个 `(lon, lat)` | 递归展开 GeoJSON 坐标 | `GeoData._compute_bbox`、`GeoData._coords_bbox` |
| `midpoint_of_line(coords)` | 折线坐标列表 | `(lon, lat)` | 取首尾中点 | **无调用者（死代码）** |
| `point_in_polygon(x, y, ring)` | 坐标 + 顶点环 | `bool` | 射线法判断点是否在多边形内（含 `1e-12` 除零保护） | `GeoData.find_state_at`、`GeoData.find_county_at` |

---

### 3.7 [game/core/game_state.py](game/core/game_state.py)

**类 `GameState`**

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `__init__()` | — | — | 从 `constants` 初始化 `year/month/xun/player_faction/prestige/gold/food` |
| `date_text()` | — | `str` | 格式化为 `"208年 1月上旬"` |
| `advance_turn()` | — | `None` | 推进一旬；旬>3 → 月+1；月>12 → 年+1 |
| `change_gold(delta)` / `change_food(delta)` / `change_prestige(delta)` | 增减量 | `None` | 资源变更，下限钳制 0 |
| `get_display_items()` | — | `[(key, 标签, 值)]` | 信息栏数据源，5 项：date/faction/prestige/gold/food |

调用者：`MainWindow.__init__` 创建实例，分发给 `TopBar`、`SidePanel`、四个面板；`MainWindow._end_turn` 调 `advance_turn`；`TopBar._refresh` 每 200 ms 轮询 `get_display_items`。

---

### 3.8 [game/map/geo_data.py](game/map/geo_data.py)

**类 `GeoData`**

实例属性：`shapes_polygon`（州面）、`shapes_line`（郡界）、`shapes_point`（县点）、`shapes_water_line`、`shapes_water_polygon`、`roads`（道路）、`labels_state`、`labels_county`、`labels_city`、`bbox`、`feature_count`、`_state_index`、`_county_index`。

**`shapes_point` 元素结构**：

```python
{
    "geometry": {"type": "Point", "coordinates": [lon, lat]},
    "properties": {"县名": name, "level": level},   # level 已钳制到 1–10
}
```

**`labels_city` 元素结构**：`(lon, lat, name, level)` 四元组。

**`roads` 结构**：`[(coords, difficulty, bbox), ...]`；无数据时为 `[]`。

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `from_file(path)` (classmethod) | GeoJSON 路径 | `GeoData` | 读取 → `_classify` → `_compute_bbox` → `_build_index` |
| `load_water(path)` | 水域路径 | `None` | 按几何类型分流为河/湖，算 bbox 与 size，再 `_assign_lod` |
| `load_roads(path)` | 路网路径 | `None` | 只解析 `LineString`，提取 `coordinates` + `difficulty`（默认 1.3），逐条算 bbox |
| `_classify(states)` | states 列表 | `None` | 生成州标签（`name_coords` 两点取中点）、州面、逐郡转 `_classify_county` |
| `_classify_county(sname, county)` | 州名 + 郡字典 | `None` | 生成郡标签、郡界、县点与县标签（均带 `level`） |
| `_compute_bbox()` | — | `None` | 求全局外接矩形 |
| `_build_index()` | — | `None` | 为州面外环、郡界环建 `(bbox, name, ring)` 索引 |
| `_ring_bbox(ring)` / `_coords_bbox(coords)`（static） | 环 / 坐标 | `(minx,miny,maxx,maxy)` | 外接矩形 |
| `_assign_lod(features)`（static） | 要素列表 | `None` | 按 `size` 降序分四档赋 `min_scale`：15%→0，15–40%→15，40–70%→45，其余→100 |
| `find_state_at(lon, lat)` / `find_county_at(lon, lat)` | 经纬度 | 州名 / 郡名 / `None` | bbox 粗筛 + 射线法精判 |
| `find_nearest_label(lon, lat, candidates, max_dist)`（static） | 经纬度、候选、上限 | 名称 / `None` | 取最近候选 |
| `find_location(lon, lat)` | 经纬度 | `(州名, 郡名, 县名)` | 州/郡用多边形判定，县用最近标签（上限 0.4°） |

#### 县 `level` 字段约定

- 取值 **1–10**（1 = 最重要/最大据点，10 = 最次要/最小聚落）。
- 解析时做 `int()` + `max(1, min(10, level))` 钳制；字段缺失或非法值默认 `5`。
- **解析必须先于使用**：在 `_classify_county` 的 `for city in ...` 循环里，`level` 的两行解析**必须写在 `shapes_point.append` 之前**。顺序颠倒会抛 `UnboundLocalError`，异常沿 `GeoData.from_file` 冒泡，导致**地图完全不加载**。
- 钳制的意义：下游三张定长表不会因越界而 `KeyError`，也不会被绘制层 `except Exception` 静默吞掉。
- 同一循环内 `shapes_point` 与 `labels_city` 共用同一 `level` 值。

---

### 3.9 [game/map/viewport.py](game/map/viewport.py)

**类 `Viewport`** — 属性 `cx`、`cy`（中心经纬度）、`scale`（像素/度）、`width`、`height`。

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `set_canvas_size(w, h)` | 画布宽高 | `None` | 记录尺寸，最小 1 |
| `fit_to_bbox(bbox, margin=0.92)` | 外接矩形 | `None` | 居中对齐并计算 `min(sx, sy)` 自适应缩放 |
| `zoom(factor, anchor=None)` | 倍率、锚点像素 | `None` | 绕锚点缩放 |
| `pan_pixels(dx, dy)` | 像素位移 | `None` | 反算经纬度偏移 |
| `project(lon, lat)` | 经纬度 | `(x, y)` | 地理 → 屏幕（Y 轴取反） |
| `unproject(x, y)` | 屏幕坐标 | `(lon, lat)` | 屏幕 → 地理 |
| `span_px(bbox)` | 外接矩形 | `float` | 当前缩放下地图总宽（像素），用于字号、线宽、县点半径计算 |

---

### 3.10 [game/map/renderer.py](game/map/renderer.py)

**类 `MapRenderer`** — 常量 `LABEL_TAG="label"`、`WATER_TAG="water"`、`ROAD_TAG="road"`、`POINT_TAG="point"`、`POLYGON_TAG="polygon"`、`LINE_TAG="line"`；属性 `data`、`_drawn`、`_cum_scale`。

> **`_drawn` 语义**：表示"几何层已绘制完成、动态层可以叠加"。
> `draw_full` 中必须在 `_draw_geometry()` 之后、`refresh_dynamic()` **之前**置 `True`。

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `__init__(canvas, viewport, font_family)` | 画布/视图/字体 | — | 绑定三者 |
| `set_data(geo_data)` | `GeoData` | `None` | 注入数据 |
| `draw_full()` | — | `None` | 全量重绘：`delete("all")` → `_drawn=False` → 重置 `_cum_scale` → `_draw_geometry()` → **`_drawn=True`** → `refresh_dynamic()` |
| `pan(dx, dy)` | 像素位移 | `None` | `canvas.move("all", ...)`，O(1)；不补画新进入视口的静态几何 |
| `zoom(factor, mx, my)` | 倍率、锚点 | `None` | `canvas.scale("all", ...)`；累计倍率超出 `[0.5, 2.0]` 时改为 `draw_full()` |
| `refresh_dynamic()` | — | `None` | 守卫 → 删除动态 tag → 按 水 → 路 → 点 → 标签 顺序重绘 → `tag_lower` 归位 |
| `_draw_geometry()` | — | `None` | 只绘静态层：州面 → 郡界；**开头按 `LAYER_VISIBILITY["polygon"|"line"]` 判断** |
| `_draw_labels()` | — | `None` | **按 `LAYER_VISIBILITY["label_state"|"label_county"|"label_city"]` 分别判断**后绘制 |
| `_draw_water()` | — | `None` | 湖泊 + 河流 |
| `_visible_bounds(margin_px=20)` | 留白像素 | `(minx,miny,maxx,maxy)` | 由 viewport 反推可见经纬度范围 |
| `render_water_polygons()` / `render_water_lines()` | — | `None` | **开头按 `LAYER_VISIBILITY["water"]` 判断**；按 `min_scale` + bbox 双重筛选 |
| `render_water_polygon(feat, style)` / `render_water_line(feat, style)` | 要素 + 样式 | `None` | 投影后创建图形，打 `WATER_TAG` |
| `render_polygons()` / `render_lines()` | — | `None` | 视口裁剪后逐要素绘制 |
| `render_polygon(feat)` / `render_line(feat)` | 要素 | `None` | 单要素绘制，支持 `properties` 里的 `fill`/`stroke` 覆盖 |
| `_point_lonlat(feat)` | 县点要素 dict | `(lon, lat)` / `(None, None)` | 提取经纬度 |
| `_point_radius(level, style)` | level、样式 | `float` | `clamp(span_px / size_divisor × radius_by_level[level], min_radius, max_radius)` |
| `render_points()` | — | `None` | **开头按 `LAYER_VISIBILITY["point"]` 判断**；视口裁剪 + `CITY_LEVEL_MIN_SCALE[level]` LOD 过滤；打 `POINT_TAG` 与 `city_lv{level}` |
| `render_point(lon, lat, feat, style)` | 经纬度、要素、样式 | `None` | 按 `shape_by_level` 走 `create_oval`/`create_polygon`/`create_rectangle` |
| `_road_width(difficulty)` | `difficulty` | `float` | `clamp(span_px / width_divisor / max(d, floor), min_width, max_width)` |
| `render_roads()` | — | `None` | **开头按 `LAYER_VISIBILITY["road"]` 判断**；视口 bbox 粗筛后逐条 `create_line`；按 `round(difficulty, 2)` 缓存宽度 |
| `render_state_labels()` / `render_county_labels()` | — | `None` | 转调 `render_label_group` |
| `render_city_labels()` | — | `None` | 县名，额外按 `CITY_LEVEL_MIN_SCALE` 判断 |
| `render_label_group(labels, style_key)` | 标签列表 + 样式键 | `None` | 通用标签绘制，检查 `min_scale`/`max_scale` |
| `draw_text(x, y, text, style)` | 屏幕坐标、文本、样式 | `None` | 四方向白色描边 + 正文，打 `LABEL_TAG` |
| `resolve_style(key)` | 样式键 | `{...base, "size": int}` | 由地图总像素宽 ÷ `size_divisor` 动态算字号 |

**顶部 import（关键）**：

```python
from game.config.style import MAP_STYLE, CITY_LEVEL_MIN_SCALE, LAYER_VISIBILITY
```

因为 `SettingsManager.apply()` 是**就地**修改这几个字典对象，所以本模块 import 进来的引用自动看到新值。

#### 叠放层级（从底到顶）

> 州面 → 郡界 → 湖泊 → 河流 → 道路 → 县点 → 州名 → 郡名 → 县名

- 州面、郡界为**静态层**；湖泊、河流、道路、县点、三类标签为**动态层**。
- **层级主要由 `refresh_dynamic` 内的绘制顺序决定**：
  `_draw_water() → render_roads() → render_points() → _draw_labels()`
- 辅以 `canvas.tag_lower` 把动态几何压回静态层之下；标签**不降**。

> ⚠️ **维护提示 1**：`_draw_labels()` 必须保持在 `refresh_dynamic` 末尾调用。
> ⚠️ **维护提示 2**：`_point_lonlat` 是 `render_points` 的必需依赖，**不可省略**。
> ⚠️ **维护提示 3**：`_drawn` 必须在 `_draw_geometry()` 后、`refresh_dynamic()` 前 `True`。

---

### 3.11 [game/ui/main_window.py](game/ui/main_window.py)

**类 `MainWindow`** — 属性 `root`、`font_family`、`settings`、`game_state`、`top_bar`、`map_canvas`、`side_panel`、`status_bar`、`_settings_win`。

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `__init__()` | — | — | 建 `Tk` → 标题/最小尺寸 → `maximize` → **`SettingsManager()` + `apply()`** → 选字体 → 建 `GameState` → `_setup_theme` → `_build_layout` → `_bind_shortcuts` → `after(120, _auto_load_default)` |
| `_pick_font_family()` | — | `str` | 从 `FONT_CANDIDATES` 选第一个可用 |
| `_setup_theme()` | — | `None` | ttk 切 `clam` 主题，配置 Frame/PanedWindow/Notebook 配色 |
| `_build_layout()` | — | `None` | 装配三段式布局 |
| `_bind_shortcuts()` | — | `None` | 全局快捷键：`+`/`=`/`-`/`0`/`Ctrl+O` |
| `_auto_load_default()` | — | `None` | 默认地图存在则静默加载 |
| `open_geojson()` | — | `None` | 文件对话框选文件 |
| `load_geojson(path, silent=False)` | 路径、静默标志 | `bool` | 转调 `MapCanvas.load_geojson` |
| `_on_location_change(text)` / `_on_zoom_change(scale)` | 文本/缩放 | `None` | 转 `status_bar` |
| `_on_menu_action(action, **kw)` | 动作名 | `None` | 菜单动作总线（见下） |
| `_end_turn()` | — | `None` | `advance_turn()` → `side_panel.refresh_all()` → 状态栏提示 |
| `_confirm_and_new_game()` | — | `None` | 二次确认后仅提示"尚未实现" |
| **`_open_settings()`** | — | `None` | **单例打开 `SettingsWindow`；已存在则 `lift`** |
| **`_on_settings_applied(changed_paths)`** | 变更路径列表 | `None` | **设置保存后回调**：若涉及 `MAP_STYLE`/`CITY_LEVEL_MIN_SCALE`/`LAYER_VISIBILITY` → `map_canvas.redraw()`；状态栏提示"设置已保存" |
| `run()` | — | `None` | `root.mainloop()` |

`_on_menu_action` 分支：`quit` / `new_game` / `load_game` / `save_game` / **`settings`→`_open_settings()`** / `view_zoom_in/out`、`view_reset` / `view_cities/generals/troops` / `end_turn` / `help_about`；其余落 else。

**`__init__` 关键顺序**：`SettingsManager` 创建并 `apply()` **必须早于** `_pick_font_family`、`GameState`、`_build_layout` —— 保证所有读取 `style.py` 的部件拿到的是覆盖后的值。

---

### 3.12 [game/ui/top_bar.py](game/ui/top_bar.py)

**类 `TopBar(tk.Frame)`** — 属性 `game_state`、`font_family`、`on_action`、`items`、`_popups`、`_menus`、`end_turn_btn`。常量 `_REFRESH_INTERVAL_MS = 200`。

| 方法 | 用途 |
|---|---|
| `__init__(master, game_state, font_family, on_action=None)` | `_build_left_info` → `_build_right_menus` → `_start_refresh` |
| `_build_left_info()` | 按 `get_display_items()` 顺序生成信息格（标签 + 加粗值 + 竖分隔线），绑定悬停与点击 |
| `_hover(cell, entering)` | 切换底色 |
| `_open_info_window(key, title)` / `_close_info_window(key)` | 信息项详情弹窗（占位内容） |
| `_build_right_menus()` | 五个菜单 + 绿色「进行 ▶」按钮 |
| `_make_menu_button(parent, text, build_fn)` | 通用菜单按钮工厂 |
| `_emit(action)` | 转发给 `on_action` |
| `_build_game_menu(m)` | 新游戏 / 读取存档 / 保存存档 / **游戏设置** / 退出 |
| `_build_faction_menu(m)` | 内政 / 军事 / 外交 / 结束本回合 |
| `_build_order_menu(m)` / `_build_view_menu(m)` / `_build_help_menu(m)` | 各菜单项 |
| `_start_refresh()` / `_refresh()` | 每 200 ms 轮询 `get_display_items()` 更新 `StringVar` |

「游戏设置」通过 `_emit("settings")` 上报，`MainWindow._on_menu_action` 捕获后打开设置窗口。

---

### 3.13 [game/ui/status_bar.py](game/ui/status_bar.py)

**类 `StatusBar(tk.Frame)`** — 三个 `StringVar`：`message_var` / `zoom_var` / `location_var`。方法：`set_message` / `set_zoom` / `set_location`。

---

### 3.14 [game/ui/map_canvas.py](game/ui/map_canvas.py)

**类 `MapCanvas(ttk.Frame)`** — 属性 `canvas`、`viewport`、`renderer`、`data`、`_drag`、`_label_job`、`_mouse_job`、`_pending_mouse`、`_settle_job`、`_location_callback`、`_zoom_callback`、`_need_fit`。常量 `_MIN_VALID_SIZE = 10`。

| 方法 | 用途 |
|---|---|
| `__init__(master, font_family)` | 建内嵌 `tk.Canvas`，建 `Viewport` 与 `MapRenderer`；`_bind_events` |
| `set_location_callback(fn)` / `set_zoom_callback(fn)` | 注册外部回调 |
| `_notify_zoom()` | 调 `_zoom_callback(viewport.scale)` |
| `load_geojson(path)` | `GeoData.from_file` → 若路网存在则 `load_roads` → `renderer.set_data` → `_need_fit=True` → `_try_fit_now()` |
| `reset_view()` | 主动复位：`fit_to_bbox` + `draw_full` |
| **`redraw()`** | **设置变更后强制全量重绘（不改视图）**：`_sync_canvas_size` → `renderer.draw_full()` |
| `zoom(factor, anchor=None)` | `viewport.zoom` → `_notify_zoom` → `renderer.zoom` → `_schedule_label_refresh` → `_schedule_settle_redraw` |
| `_try_fit_now()` | 尺寸有效且 `_need_fit` 时 fit |
| `_bind_events()` | 滚轮、Button-4/5、左键按下/拖动/释放、双击、Motion、Leave、Configure |
| `_on_wheel(event)` | `delta>0` 放大 1.2，否则缩小 |
| `_on_press/_on_drag/_on_release(event)` | 拖拽平移 |
| `_on_resize(event)` | 更新画布尺寸；`_need_fit` 时 fit，否则 `draw_full` |
| `_on_motion(event)` / `_process_motion()` | 缓存坐标，40 ms 节流后 `find_location` → 回调 |
| `_on_leave(event)` | 清空位置显示 |
| `_sync_canvas_size()` | 从 `winfo_width/height` 同步到 viewport |
| `_schedule_label_refresh()` / `_do_label_refresh()` | 30 ms 节流刷新动态层 |
| `_schedule_settle_redraw()` / `_settle_redraw()` | 滚轮静默 180 ms 后补一次全量重绘 |

---

### 3.15 [game/ui/side_panel.py](game/ui/side_panel.py)

**类 `SidePanel(ttk.Frame)`** — 属性 `game_state`、`notebook`。方法 `__init__` / `_add_tabs` / `refresh_all`。Tab 顺序：势力(0) / 城市(1) / 武将(2) / 部队(3)。

---

### 3.16 [game/ui/window_utils.py](game/ui/window_utils.py)

| 函数 | 用途 |
|---|---|
| `maximize(window)` | 三级降级：`state("zoomed")` → `attributes("-zoomed")` → 手动铺满屏幕 |
| `center_on_parent(child, parent, width, height)` | 相对父窗居中并夹在屏幕范围内 |

---

### 3.17 [game/ui/widgets/collapsible.py](game/ui/widgets/collapsible.py)

**类 `CollapsibleSection(tk.Frame)`** — 折叠分组控件。

| 属性 | 说明 |
|---|---|
| `body` | 内容区 `tk.Frame`，把控件放这里 |
| `font_family` | 字体 |
| `_expanded` | 是否展开 |

| 方法 | 入参 | 返回 | 用途 |
|---|---|---|---|
| `__init__(master, title, desc="", on_reset=None, expanded=False, font_family="TkDefaultFont")` | 各配置 | — | 建标题条（▶/▼ + 标题 + 「↺ 恢复本组默认」）+ 描述行 + body |
| `toggle()` | — | `None` | 切换展开/收起 |
| `set_expanded(flag)` | `bool` | `None` | 展开时 `body.pack`，收起时 `body.pack_forget`，同步箭头方向 |

点击标题条的任意部分（箭头、标题、空白）都会 `toggle`；`on_reset(self)` 在用户点击「恢复本组默认」时被调用。

---

### 3.18 [game/ui/settings_window.py](game/ui/settings_window.py)

**类 `SettingsWindow(tk.Toplevel)`** — 设置窗口本体。

**属性**：

| 属性 | 说明 |
|---|---|
| `settings` | 传入的 `SettingsManager` |
| `font_family` | 字体 |
| `on_applied` | 保存后回调，参数是 `changed_paths` |
| `draft` | `{path: value}`，**所有改动先写这里，不直接写 manager** |
| `_rows` | `{path: {"setter": fn}}`，每个控件一个 setter，用于"恢复默认"时回填 |
| `_sections` | `{group_key: CollapsibleSection}` |
| `filter_var` / `only_modified_var` | 搜索框与"仅显示已修改"勾选状态 |

**构建**：

| 方法 | 用途 |
|---|---|
| `_build_toolbar()` | 顶部：搜索框 + 仅显示已修改 + 本地文件路径显示 |
| `_build_body()` | 中部：`Canvas + Scrollbar` 承载所有分组；内容区自适应宽度；绑定滚轮 |
| `_build_footer()` | 底部：「恢复全部默认」「取消」「保存」，及「已修改 N 项」计数 |
| `_populate()` | 遍历 `schema.GROUPS` 生成 `CollapsibleSection`，遍历 `items_of_group` 生成行 |
| `_add_item_row(parent, item)` | 一行：左侧中文标签 + 描述；右侧按 `type` 派发控件 |

**控件构造**：

| 方法 | 类型 | 说明 |
|---|---|---|
| `_build_bool` | 勾选框 | 变更即写 draft |
| `_build_color` | 色块按钮 + hex 输入框 | 点色块 → `colorchooser.askcolor()`；hex 输入框失焦/回车时校验 `#RRGGBB` |
| `_build_number` | 输入框 + 单位标签 + 错误提示 | 回车/失焦时按 `int`/`float` 校验 + 范围校验；失败时红字提示且不写 draft |
| `_build_choice` | `ttk.Combobox` | 显示中文标签，写 draft 时映射回原始值 |
| `_build_level_table` | 5 列网格 | 每行 `Lv{n}` + 控件；`child_path = f"{path}.{level}"`；支持 `int`/`float`/`choice` |

**值读写与差异**：

| 方法 | 用途 |
|---|---|
| `_get(path)` | 优先从 `draft`，否则从 `settings.get(path)` |
| `_refresh_dirty_label()` | 更新底部「已修改 N 项」 |
| `_apply_filter()` | 按搜索关键字 + 「仅显示已修改」筛选；`level_table` 用前缀匹配 |
| `_on_reset_group(section)` | 该组全部项恢复默认：清 draft + 调 setter 回填 |
| `_on_reset_all()` | 二次确认后 `settings.reset_all()` + 全部 setter 回填 |

**保存 / 关闭**：

| 方法 | 流程 |
|---|---|
| `_on_save()` | ① 遍历 draft，找出 `restart=True` 的分组；② `settings.set_many(draft)` → `settings.save()` → `settings.apply()`；③ 清 draft；④ `on_applied(changed)`；⑤ 若有需重启分组 → `showinfo`；⑥ `_on_close()` |
| `_on_close()` | 若 draft 非空 → `askyesnocancel("有未保存的修改，是否保存？")`；"取消"则中止关闭；"是"→ 走保存；"否"→ 丢弃 |

**其它**：

| 方法 | 用途 |
|---|---|
| `_on_wheel(event)` | 仅当鼠标位于本窗口时滚动内容区 |
| `_unbind_wheel()` | 关闭时解绑全局滚轮事件 |

**窗口属性**：`transient(master)` + `grab_set()`（模态）、`940×660`、相对主窗居中。

---

### 3.19 panels 四件套

| 文件 | 类 | 方法 | 说明 |
|---|---|---|---|
| [faction_panel.py](game/ui/panels/faction_panel.py) | `FactionPanel(ttk.Frame)` | `__init__`、`_build_info_grid` | 9 行信息表；**君主「刘备」、都城「江陵」硬编码**；**无 `refresh()`** |
| [city_panel.py](game/ui/panels/city_panel.py) | `CityPanel(ttk.Frame)` | `__init__`、`_build_toolbar`、`_build_tree`、`refresh()`、`_on_double_click` | 5 列 Treeview；`refresh()` 仅清空；双击 `print` |
| [general_panel.py](game/ui/panels/general_panel.py) | `GeneralPanel(ttk.Frame)` | `__init__`、`_build_toolbar`、`_build_tree`、`refresh()` | 7 列 Treeview；`refresh()` 仅清空 |
| [troop_panel.py](game/ui/panels/troop_panel.py) | `TroopPanel(ttk.Frame)` | `__init__`、`_build_toolbar`、`_build_tree`、`refresh()` | 5 列 Treeview；`refresh()` 仅清空 |

---

## 4. 程序完整运行流程

### 4.1 启动阶段

```
python main.py
└─ main.py: main()
   └─ MainWindow()                        ← game/ui/main_window.py
      ├─ tk.Tk() → title(APP_TITLE) → minsize(1024,640)
      ├─ maximize(root)
      ├─ SettingsManager()                ← 从 userdata/settings.json 读覆盖
      │  ├─ load()                        ← 合并到 self.current
      │  └─ apply()                       ← 就地写回 style.py 的各 dict（关键）
      ├─ _pick_font_family()              ← 遍历 FONT_CANDIDATES（已可能被覆盖）
      ├─ GameState()                      ← 208年1月上旬 / 刘备 / 1000 / 5000 / 20000
      ├─ _setup_theme()                   ← ttk clam + THEME 配色（已可能被覆盖）
      ├─ _build_layout()
      │  ├─ TopBar(...)                   ← 5 个信息格 + 5 个菜单 + 「进行 ▶」
      │  ├─ PanedWindow(horizontal)
      │  │  ├─ MapCanvas(pane) → add(weight=4)
      │  │  └─ SidePanel(pane) → add(weight=1)
      │  ├─ StatusBar(root)
      │  └─ 挂接 location / zoom 回调
      ├─ _bind_shortcuts()
      └─ root.after(120, _auto_load_default)
   └─ run() → root.mainloop()
```

### 4.2 地图加载流程（120 ms 后）

与原先相同；`load_geojson` 之后 `_try_fit_now` → `renderer.draw_full`。
`_draw_geometry` 与 `refresh_dynamic` 内部按 `LAYER_VISIBILITY` 判断各层是否绘制。

### 4.3 设置窗口流程

```
用户点击 「游戏 → 游戏设置」
└─ TopBar._emit("settings")
   └─ MainWindow._on_menu_action("settings")
      └─ MainWindow._open_settings()
         ├─ 已存在 → lift + focus
         └─ 否则 SettingsWindow(root, self.settings, font_family,
                                on_applied=self._on_settings_applied)
            ├─ _build_toolbar / _build_body / _build_footer
            ├─ _populate()          ← 遍历 schema.GROUPS / ITEMS 生成控件
            │  └─ 各控件初值来自 settings.get(path)（已是覆盖后的当前值）
            ├─ center_on_parent + grab_set（模态）
            └─ WM_DELETE_WINDOW → _on_close

用户在窗口里修改任意控件
└─ 控件回调把新值写入 self.draft[path]
   └─ _refresh_dirty_label 更新底部"已修改 N 项"

用户点「保存」
└─ _on_save()
   ├─ 找出 draft 中涉及 restart=True 分组（theme / font）的项
   ├─ settings.set_many(draft)   ← 写入 current
   ├─ settings.save()            ← 计算 diff → 写 userdata/settings.json
   ├─ settings.apply()           ← 就地写回 style.py 的各 dict
   ├─ 清 draft + 更新计数
   ├─ on_applied(changed_paths)  ← MainWindow._on_settings_applied
   │  ├─ 若涉及 MAP_STYLE / CITY_LEVEL_MIN_SCALE / LAYER_VISIBILITY
   │  │  → map_canvas.redraw() → renderer.draw_full()  （立即生效）
   │  └─ 状态栏 "设置已保存"
   ├─ 若有需重启分组 → showinfo("部分设置需重启生效")
   └─ _on_close()

用户点「取消」或点 X
└─ _on_close()
   ├─ draft 非空 → askyesnocancel("有未保存的修改，是否保存？")
   │  ├─ "取消" → 中止关闭
   │  ├─ "是"   → 走 _on_save
   │  └─ "否"   → 丢弃 draft 并关闭
   └─ 释放 grab + destroy
```

### 4.4 主循环中的交互

| 触发 | 调用链 |
|---|---|
| 滚轮 | `_on_wheel` → `MapCanvas.zoom` → `viewport.zoom` → `_notify_zoom` → `renderer.zoom`（或 `draw_full`）→ 30 ms 后 `_do_label_refresh` → `renderer.refresh_dynamic`；同时 `_schedule_settle_redraw` 挂起 180 ms 计时器 |
| 左键拖拽 | `_on_press` → `_on_drag` → `viewport.pan_pixels` → `renderer.pan` → 30 ms 后 `refresh_dynamic` |
| 双击 | `reset_view()` |
| 鼠标移动 | `_on_motion` → 40 ms 节流 `_process_motion` → `find_location` → `_on_location_change` |
| 窗口/分隔条尺寸变化 | `<Configure>` → `viewport.set_canvas_size` → `_need_fit ? _try_fit_now : draw_full` |
| 「进行 ▶」 | `TopBar._emit("end_turn")` → `_end_turn` → `advance_turn` → `refresh_all` |
| 菜单城市/武将/部队 | `side_panel.notebook.select(1/2/3)` |
| **菜单游戏设置** | **`_open_settings` → 设置窗口** |
| **设置保存** | **`_on_settings_applied` → `map_canvas.redraw()`（若涉及地图样式/显隐）** |
| 200 ms 定时器 | `TopBar._refresh` → 更新各 `StringVar` |

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

### 5.1 可通过 `constants.py` 调整

| 常量 | 影响 |
|---|---|
| `INITIAL_YEAR/MONTH/XUN` | 开局日期 |
| `INITIAL_FACTION` | 开局势力名 |
| `INITIAL_PRESTIGE/GOLD/FOOD` | 开局资源 |
| `MIN_WINDOW_SIZE` | 窗口最小尺寸 |
| `APP_TITLE` | 标题栏 |
| `DEFAULT_MAP_PATH` / `DEFAULT_WATER_PATH` / `DEFAULT_ROADS_PATH` | 自动加载路径 |

### 5.2 可通过设置窗口修改（即 `style.py` 默认值）

| 项 | 影响 | 是否需重启 |
|---|---|---|
| `THEME` | 全部 UI 配色 | 是 |
| `FONT_SIZES` | 五处 UI 字号 | 是 |
| `FONT_CANDIDATES` | 中文字体优先级 | 是 |
| `MAP_STYLE["polygon"/"line"]` | 州面填充描边、郡界线 | 否 |
| `MAP_STYLE["point"]` | 县点颜色、描边、`size_divisor`、`min/max_radius`、`shape_by_level`、`radius_by_level` | 否 |
| `MAP_STYLE["road"]` | 道路颜色、`width_divisor`、`min/max_width`、`difficulty_floor` | 否 |
| `MAP_STYLE["water_*"]` | 湖泊/河流样式（**当前不生效，加载被注释**） | 否 |
| `MAP_STYLE["label_*"]` | 标签颜色、描边、`size_divisor`、`min/max_size`、`min/max_scale` | 否 |
| `CITY_LEVEL_MIN_SCALE` | 县点与县名共用的分级显示阈值（1–10） | 否 |
| `LAYER_VISIBILITY` | 图层显隐总开关 | 否 |

修改后写入 `userdata/settings.json`，只保存与默认不同的项。

### 5.3 代码内常量

| 位置 | 值 | 含义 |
|---|---|---|
| `MapCanvas._MIN_VALID_SIZE` | `10` | 小于此像素视为布局未完成 |
| `TopBar._REFRESH_INTERVAL_MS` | `200` | 信息栏轮询周期 |
| `MapRenderer.LABEL_TAG` / `WATER_TAG` / `ROAD_TAG` / `POINT_TAG` | `"label"` / `"water"` / `"road"` / `"point"` | 动态重绘锚点 |
| `MapRenderer.POLYGON_TAG` / `LINE_TAG` | `"polygon"` / `"line"` | 静态层锚点 |
| `MapRenderer._drawn` 语义 | `bool` | "几何层已画、动态层可叠加" |
| `MapRenderer.refresh_dynamic` 绘制顺序 | 水 → 路 → 点 → 标签 | Tk 后画盖先画 |
| `MapRenderer._cum_scale` 阈值 | `(0.5, 2.0)` | 超出则全量重绘 |
| `MAP_STYLE["point"]["size_divisor"]` 默认 | `1100` | 县点半径分母 |
| `MAP_STYLE["road"]["width_divisor"]` 默认 | `2600` | 道路线宽分母 |
| 县 `level` 取值范围 | `1–10` | 由 `GeoData._classify_county` 钳制，缺省 `5` |
| `GeoData.find_nearest_label` 上限 | `0.4`（度） | 县名匹配最大距离 |
| `Viewport.fit_to_bbox` 边距 | `0.92` | 自适应缩放留白 |
| `_schedule_label_refresh` / `_on_motion` 节流 | `30 ms` / `40 ms` | 动态层刷新与鼠标查询节流 |
| `_schedule_settle_redraw` 静默时长 | `180 ms` | 滚轮停手后补绘窗口 |
| `SettingsManager` 本地路径 | `PROJECT_ROOT/userdata/settings.json` | 覆盖文件位置 |
| `SettingsWindow` 尺寸 | `940 × 660` | 设置窗口初始大小 |
| `SettingsWindow._on_save` 中需重启分组 | `theme` / `font` | 由 `schema.GROUPS[...]["restart"]` 决定 |

---

## 6. 已知逻辑限制与待完善清单

### 6.1 未实现功能

| 入口 | 现状 |
|---|---|
| 保存存档 `save_game` | 仅状态栏提示"尚未实现" |
| 读取存档 `load_game` | 复用了 `open_geojson`（打开地图文件，非存档） |
| 新游戏 `new_game` | 确认后仅提示"尚未实现" |
| 内政/军事/外交/命令/操作说明 | 全部落入 else 分支，仅状态栏回显 |
| 信息项详情弹窗 | 占位文字 |
| 城市/武将/部队面板 | `refresh()` 只清空，无数据源 |

### 6.2 数据层缺失

- `GameState` 只有日期与四项资源，没有武将池、城市数据库、部队、外交关系。
- `assets/water.geojson` 加载调用在 `map_canvas.py` 被注释；`GeoData.load_water` / `_assign_lod` / `MapRenderer.render_water_*` / `WATER_TAG` / `MAP_STYLE["water_*"]` 全部为休眠代码。
- `assets/mountains.geojson` 无任何代码引用。
- `assets/roads.geojson` 只做视觉呈现：`difficulty` 仅影响线宽，`from_id` / `to_id` / `length_km` / `mountains_crossed` / `waters_crossed` 等字段完全未读取。
- 路网与县点/郡界之间没有建立拓扑关联（`from_id` 无法反查县点）。
- 县 `level` 已从 5 档扩展到 10 档并驱动渲染，但没有任何游戏逻辑挂在上面。

### 6.3 逻辑与性能限制

1. `render_lines`（106 条郡界）仍全量重绘、仅 bbox 视口裁剪。
2. `<Configure>` 全量重绘：拖动分隔条会触发连续重绘；且**不调整缩放比例**（刻意设计）。
3. 绘制方法外层 `except Exception: pass`，几何出错时静默，排查困难。
4. 标签不做视口预筛，每次 `refresh_dynamic` 重建全部标签对象。
5. 空间索引为线性扫描。
6. `_build_index` 只取外环，忽略孔洞。
7. 县名匹配用固定 0.4° 距离。
8. `midpoint_of_line` 为死代码。
9. Tab 索引硬编码在 `MainWindow._on_menu_action`。
10. `FactionPanel` 缺少 `refresh()`。
11. `WINDOW_SIZE` 定义了但从未使用。
12. `GameState` 与地图数据无关联，无存档序列化接口。
13. `_cum_scale` 复位时机导致周期性全量重绘停顿。
14. 无测试、无打包、无 lint 配置。
15. 道路无 LOD、无空间索引。
16. 动态图层重建 + `tag_lower` 的额外开销。
17. `CITY_LEVEL_MIN_SCALE` 是硬编码定长字典，等级数量变动需手工同步。
18. `shape_by_level` / `radius_by_level` 同样问题。
19. 县点与县名"同显同隐"依赖同表同判，分处两处，建议抽公共 `_visible_by_level(level, scale)`。
20. **`_drawn` 置位时机是易错点**：必须在 `_draw_geometry()` 后、`refresh_dynamic()` 前。
21. **`refresh_dynamic` 的绘制顺序决定层级**：`_draw_labels()` 必须保持在末尾。
22. **`shapes_point` 的 `level` 解析必须先于 `append`**。
23. **静态层依赖 `draw_full`**：快速缩放可能导致最终视图边缘州郡面缺失，靠 180 ms settle redraw 缓解。
24. **`_cum_scale` 触发点是"当前视图"**，不是"最终视图"。
25. **拖拽路径不做静态层补画**。
26. **`SettingsManager.apply()` 必须就地修改 `style.py` 的字典**：若有人改成 `_style.MAP_STYLE = new_dict`，则已 import 到旧对象的模块（如 `renderer`）将看不到新值，设置看似保存但地图不更新。这是设置系统最容易踩的坑，请勿改动这一约定。
27. **`SettingsManager` 必须在 `MainWindow.__init__` 早期创建并 `apply()`**：晚于任何读取 `style.py` 的模块（`_pick_font_family`、`_setup_theme`、`TopBar`、`MapCanvas`、`MapRenderer` 等）创建，就会导致这些模块使用旧默认值。
28. **`theme` / `font` 分组的 `restart=True` 是硬编码约定**：`_on_save` 靠 `schema.GROUPS[...]["restart"]` 决定是否提示"需重启"。新增需重启分组时，记得在 `GROUPS` 里标记；不要在 `_on_save` 里写死分组 key。
29. **`settings_schema.ITEMS` 与 `style.py` 结构必须保持一致**：`ITEMS` 里引用的 path 若不存在于 `style.py`，`_get` 会返回 `None`，控件会显示空白但不报错；`SettingsManager.load` 里对废弃 override 是忽略的。新增/重命名 `style.py` 字段时，务必同步更新 `ITEMS`。
30. **`SettingsWindow` 里 `level_table` 的 draft key 是 `path.LEVEL`**：例如 `CITY_LEVEL_MIN_SCALE.7`、`MAP_STYLE.point.shape_by_level.4`。`_apply_filter` 里的"仅显示已修改"判定对 `level_table` 用前缀匹配。`reset_paths` / `_on_reset_group` 都要处理带后缀的 key。

### 6.4 建议的下一步优先级

1. 接入 `water.geojson`（取消 `map_canvas.py` 注释）与 `mountains.geojson`（新增加载分支）。此时 `LAYER_VISIBILITY` 里 `water` / `mountain` 已就绪，用户可直接在设置里开关。
2. 为州面/郡界加 `min_scale` LOD；`pan` 路径增加"新视口超出已绘制范围则补画"的判断。
3. 建立 `General` / `City` / `Troop` 数据模型，填充三个列表面板并补 `FactionPanel.refresh()`。
4. 实现存档序列化（JSON）+ 保存/读取菜单。
5. 把县点与 `GameState` 的城市数据绑定；把县 `level` 作为城市规模/人口/兵力的分级依据。
6. 给 `GeoData.roads` 建 `id → 县点` / `id → 道路列表` 索引。
7. 给绘制方法的 `except Exception` 加"首次异常打印一次日志"。
8. **设置系统后续扩展**：
   - 增加"导出/导入设置"（选择 JSON 文件读写）；
   - 增加"主题预设"（如「暖色」「高对比」「夜色」几套 `THEME` 一键切换）；
   - 把 `THEME` 也做到即时生效（需要遍历已创建 widget 递归重配 bg/fg，工作量较大）；
   - 把 `ITEMS` 从手工维护改为"扫描 `style.py` 结构 + 中文标签映射表"的半自动生成；
   - 增加"未保存前预览"（临时 apply 到 style 后 `map_canvas.redraw()`，关闭时回滚）。

---

**变更日志（本次设置系统上线）**

- 新增：`game/config/settings_manager.py`、`game/config/settings_schema.py`、`game/ui/widgets/__init__.py`、`game/ui/widgets/collapsible.py`、`game/ui/settings_window.py`。
- 新增目录：`userdata/`（运行时自动创建）。
- `game/config/style.py`：末尾追加 `LAYER_VISIBILITY`。
- `game/ui/main_window.py`：新增 `SettingsManager` 初始化、`settings` 菜单分支、`_open_settings`、`_on_settings_applied`。
- `game/ui/map_canvas.py`：新增 `redraw()`。
- `game/map/renderer.py`：顶部 import 增加 `LAYER_VISIBILITY`；`_draw_geometry` / `refresh_dynamic` / `_draw_labels` / `render_water_*` / `render_roads` / `render_points` 增加显隐守卫。