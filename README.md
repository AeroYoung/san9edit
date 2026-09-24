# 暗耻三国志 — 项目说明文档

> 本轮更新重点：**县界渲染（黑色虚线）**、**几何层去色（州/郡/县只画黑边）**、**标签去势力色（全部黑色）**、**设置窗口 `#` 颜色报错修复**。新增 §9.3 变更日志。

---

## 1. 项目概述

| 项 | 内容 |
|---|---|
| 项目名称 | 暗耻三国志（`APP_TITLE`） |
| 定位 | 三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》 |
| 程序入口 | `main.py` → `MainWindow().run()` |
| 核心功能 | 中国全图矢量渲染（州/郡/**县**三级边界 + 道路路网 + 水域湖泊/河流）、鼠标缩放平移、光标反查行政区、旬回合制时钟、顶部信息栏与菜单、右侧 Tab 面板框架、多 Tab 设置窗口（外观 / 操作 / 游戏）、剧本系统（NPC/据点初始化 + 玩家势力绑定）、势力关系分组展示、**郡面势力染色（唯一的着色图层）** |
| 运行环境 | Python 3 + 标准库 `tkinter`。仅依赖标准库，**无第三方依赖、无 requirements.txt** |
| 数据来源 | `assets/map.geojson`：13 州 / 106 郡 / 1372 据点（`states → counties → cities` 三层嵌套；**据点新增 `boundary` 字段**）；`assets/roads.geojson`：约 600 条道路线段；`assets/water.geojson`：205 条河流/湖泊（已接入渲染）；`assets/mountains.geojson`：42 个山地区块（**未接入**） |
| 剧本来源 | `scenarios/default.json`：默认剧本，启动时自动加载 |
| 用户数据 | `userdata/settings.json`：设置覆盖文件，仅保存与默认值不同的项 |
| 平台 | Windows 优先（`maximize()` 兼容 Win/Linux/macOS） |

**当前完成度**：

- ✅ 地图查看器（州/郡/县三级**边界**渲染 + 道路 + 水域 + 图层显隐 + 县点四级样式 + 县名避让）
- ✅ 多 Tab 设置系统（外观 tab 有内容，操作/游戏 tab 空骨架）
- ✅ 剧本系统：可加载 JSON 剧本，构造 `World`
- ✅ 势力面板分组列表（玩家 / 盟友 / 敌对 / 中立四组）
- ✅ **郡面势力染色**：地图上**唯一**的着色图层
- ✅ **县界渲染**：黑色虚线，按 bbox 尺寸分级显隐
- ✅ **几何层去色**：州 / 郡 / 县三级边界均黑色描边，州面不再填充
- ✅ **标签去势力色**：州名 / 郡名 / 县名 / 县点均为固定颜色（黑或深灰）
- ⚠️ 回合与资源为骨架
- ❌ 内政/军事/外交/存档均为空实现

---

## 2. 文件结构清单

```
san9edit/
├── main.py
├── README.md
├── assets/
│   ├── map.geojson                 ★ city 新增 boundary 字段
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
    │   ├── style.py                ★ 本轮：州面透明、三级边界黑、县界虚线、标签黑
    │   ├── settings_manager.py     待排查：州界宽度保存后是否生效
    │   └── settings_schema.py      ★ 本轮：删 2 条颜色 ITEM、加县界分组、polygon.width max 调大
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
    │   ├── geo_data.py             ★ 本轮：新增 shapes_city_boundary，from_file 调 _assign_lod
    │   ├── viewport.py
    │   └── renderer.py             ★ 本轮：CITY_TAG、_LAYER_ORDER 插 "city"、render_city_boundaries、删两个换色方法
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

不变：州 2 位 / 郡 4 位 / 据点 6 位。

### 3.2 势力（Faction）

不变。

### 3.3 人物（Character）

不变。

### 3.4 据点（Node）

**静态字段**（来自 `map.geojson`）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | str | 六位字符串 |
| `name` | str | 名称 |
| `coords` | tuple | `(lon, lat)` |
| `type` | str | `县`/`关隘`/`渡口/津`/`仓/监`/`谷`/`山地` |
| `level` | int | 规模，1（最大）–10（最小） |
| `is_capital` | bool | 是否郡治 |
| **`boundary`** | list | ★ 本轮新增：`[(lon,lat), ...]` 闭合环，**全部据点都有**（含关隘/仓/谷/山地等，部分为非县的极小多边形） |

**动态字段**（来自剧本覆盖）：`owner` / `troops` / `gold` / `food`。

**属性**：`state_id` / `county_id` / `is_owned()`。

### 3.5 游戏世界（World）

不变。

### 3.6 剧本加载器（ScenarioLoader）

不变。

### 3.7 郡级控制力统计（CountyStat）

不变。

### 3.8 县界（CityBoundary）

**渲染层专用**，由 `GeoData.shapes_city_boundary` 承载。每个元素：

| 字段 | 类型 | 说明 |
|---|---|---|
| `geometry` | dict | `{"type": "LineString", "coordinates": [ring]}`，ring 是闭合环 |
| `properties` | dict | `{id, 县名, type, level}` |
| `bbox` | tuple | `(min_lon, min_lat, max_lon, max_lat)` |
| `size` | float | bbox 对角线长度，供 `_assign_lod` 分级 |
| `min_scale` | float | `_assign_lod` 赋的显示阈值（0/15/45/100 四档） |

**收集规则**：所有 `city` 的 `boundary`，不做 type 过滤。

**LOD 规则**：与水域共用 `_assign_lod`——按 size 从大到小分四档，前 15% 阈值 0，15%–40% 阈值 15，40%–70% 阈值 45，其余阈值 100。

---

## 4. 数据格式参考

### 4.1 `assets/map.geojson` 实际结构（本轮更新）

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
        "boundary": [[lon,lat], ...]            // ★ 本轮新增：县/据点边界（闭合环）
      }]
    }]
  }]
}
```

**注意**：
- `boundary` 字段在**所有** type 的 city 上都存在。
- 非 `县` 类型的 `boundary` 常常是极小的圆环（关隘/仓/谷/山地），视觉上接近一个点，不影响正常渲染。
- 部分县 boundary 是正常多边形。

### 4.2 `type` 枚举

不变。

### 4.3 `scenarios/default.json` 结构

不变。

---

## 5. 模块与函数清单

### 5.1 `main.py`

不变。

### 5.2 `game/config/constants.py`

不变。

### 5.3 – 5.9

`faction.py` / `character.py` / `node.py` / `world.py` / `scenario.py` / `game_state.py` / `utils.py` **均未改动**。

### 5.10 `game/core/territory.py`

不变。

### 5.11 `game/map/geo_data.py`（★ 本轮改动）

**① `__init__` 新增容器**：

```python
self.shapes_city_boundary = []   # ★ 县界（闭合 ring，虚线轮廓用）
```

**② `_classify_county` 内，在 `labels_city.append(...)` 之后**：

```python
# ★ 新增：县界（所有 type 都收，不做过滤）
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

**③ `from_file` 里赋 LOD**：

```python
data._classify(states)
data._assign_lod(data.shapes_city_boundary)   # ★ 新增
data._compute_bbox()
data._build_index()
```

**`_compute_bbox` / `_build_index` 不改**：县界不扩展 bbox，也不参与空间反查。

**`labels_city` 保持五元组**：`(lon, lat, name, level, id)`，id 目前无人消费，保留以备将来。

### 5.12 `game/map/viewport.py`

不变。

### 5.13 `game/map/renderer.py`（★ 本轮改动）

#### 类常量

```python
LABEL_TAG     = "label"
WATER_TAG     = "water"
ROAD_TAG      = "road"
POLYGON_TAG   = "polygon"
LINE_TAG      = "line"
POINT_TAG     = "point"
TERRITORY_TAG = "territory"
CITY_TAG      = "city"         # ★ 本轮新增：县界

# 从底到顶
_LAYER_ORDER = (
    "polygon",      # 州面（透明填充 + 黑描边）
    "city",         # ★ 县界（黑虚线）
    "territory",    # 郡面势力染色（唯一的着色层）
    "water",
    "road",
    "line",         # 郡界（黑实线）
    "point",
    "label",
)
```

#### `_draw_geometry`

```python
def _draw_geometry(self):
    if LAYER_VISIBILITY.get("polygon", True):
        self.render_polygons()
    if LAYER_VISIBILITY.get("city", True):      # ★ 新增
        self.render_city_boundaries()
    if LAYER_VISIBILITY.get("territory", True):
        self.render_territory()
    if LAYER_VISIBILITY.get("line", True):
        self.render_lines()
```

#### 新增方法 `render_city_boundaries`

```python
def render_city_boundaries(self):
    """县界：只画黑色虚线轮廓，不填充。

    - 按 LOD（feat["min_scale"]）与视口裁剪粗筛
    - 所有 type 的据点都画（数据层已收集）
    - 首尾闭合：create_line 不自动闭合
    """
    feats = getattr(self.data, "shapes_city_boundary", None)
    if not feats:
        return

    line_style = MAP_STYLE.get("city_line") or {}
    color = line_style.get("color")
    if not color:
        return
    width = line_style.get("width", 1)
    dash  = line_style.get("dash", (3, 3))

    vx0, vy0, vx1, vy1 = self._visible_bounds()
    scale = self.viewport.scale

    for feat in feats:
        if scale < feat.get("min_scale", 0):
            continue
        b = feat["bbox"]
        if b[2] < vx0 or b[0] > vx1 or b[3] < vy0 or b[1] > vy1:
            continue
        ring = feat["geometry"]["coordinates"]
        if len(ring) < 3:
            continue
        try:
            pts = []
            for lon, lat in ring:
                x, y = self.viewport.project(lon, lat)
                pts.extend((x, y))
            if pts[0] != pts[-2] or pts[1] != pts[-1]:
                pts.extend((pts[0], pts[1]))
            self.canvas.create_line(
                *pts, fill=color, width=width, dash=dash,
                tags=self.CITY_TAG,
            )
        except Exception:
            pass
```

#### `render_county_labels` 重写

不再调 `_county_label_color`，直接用 `style`：

```python
for lon, lat, text, cid in labels:
    x, y = self.viewport.project(lon, lat)
    if x < -pad or x > w + pad or y < -pad or y > h + pad:
        continue
    self.draw_text(x, y, text, style)
```

#### `render_city_labels` 简化

```python
for lon, lat, text, level, cid in labels:
    min_scale = CITY_LEVEL_MIN_SCALE.get(level, default_min)
    if scale < min_scale:
        continue
    x, y = self.viewport.project(lon, lat)
    if x < -pad or x > w + pad or y < -pad or y > h + pad:
        continue
    r = self._point_radius(level, point_style)
    offset = r + text_half + gap
    self.draw_text(x, y - offset, text, style)   # ★ 不换色
```

#### 删除的方法

- `_city_label_color(cid, default)` —— 死代码，删除
- `_county_label_color(cid, default)` —— 死代码，删除

#### 未变

`draw_full` / `pan` / `zoom` / `refresh_dynamic` / `_restack` / `_visible_bounds` / `render_polygons` / `render_polygon` / `render_territory` / `render_lines` / `render_line` / `render_points` / `render_point` / `_draw_point_shape` / `render_state_labels` / `render_label_group` / `draw_text` / `resolve_style` / `_point_lonlat` / `_point_radius` / `_road_width` / `render_roads` / 水域相关方法。

### 5.14 `game/ui/main_window.py`

不变。

### 5.15 – 5.19

不变。

### 5.20 `game/config/style.py`（★ 本轮改动）

**州面**：

```python
"polygon": {
    "fill":    "",           # ★ 透明：不填充
    "outline": "#000000",    # ★ 黑：州界
    "width":   4,            # ★ 最粗
},
```

**郡界**：

```python
"line": {
    "color": "#000000",      # ★ 黑
    "width": 1,
},
```

**县界**（新增，代替已废弃的 `city_polygon`）：

```python
"city_line": {
    "color": "#000000",      # ★ 黑
    "width": 1,
    "dash": (3, 3),          # ★ 虚线
},
```

**已删除**：`city_polygon` 整段。

**标签**：

```python
"label_county": {
    "color": "#000000",      # ★ 黑（原 #333333）
    ...
},
"label_city": {
    "color": "#000000",      # ★ 黑（原 #7A3B00）
    ...
},
```

**图层显隐**：

```python
LAYER_VISIBILITY = {
    "polygon":      True,
    "city":         True,     # ★ 新增
    "line":         True,
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

**视觉效果总结**：

| 层 | 线型 | 颜色 | 宽度 |
|---|---|---|---|
| 州界 | 实线 | 黑 | 4（可调，上限已放到 20） |
| 郡界 | 实线 | 黑 | 1 |
| 县界 | 虚线 | 黑 | 1 |
| 郡面染色 | 实心面 | 势力色 | — |
| 县点 / 标签 | — | 黑 / 深灰 | — |

### 5.21 `game/config/settings_schema.py`（★ 本轮改动）

**`GROUPS` 新增一组**（在 `"line"` 之后、`"point"` 之前）：

```python
{"key": "city", "tab": "appearance", "title": "县界样式",
 "desc": "各县据点的边界，黑色虚线。州/郡/县三级边界均不再着色，"
         "着色由势力染色层负责。"},
```

**`ITEMS` 变更**：

- **删除**：`MAP_STYLE.polygon.fill`（颜色，州面填充色）
- **删除**：`MAP_STYLE.city_polygon.fill`（颜色，县面填充色）
- **新增**（`city` 分组）：

```python
{"path": "MAP_STYLE.city_line.color", "group": "city", "type": "color",
 "label": "县界轮廓色"},
{"path": "MAP_STYLE.city_line.width", "group": "city", "type": "int",
 "label": "轮廓线宽（像素）", "min": 0, "max": 8},
```

- **修改**：`MAP_STYLE.polygon.width` 的 `max` 从 `8` 调到 `20`：

```python
{"path": "MAP_STYLE.polygon.width", "group": "polygon", "type": "int",
 "label": "描边宽度（像素）", "min": 0, "max": 20},
```

- **新增**（`visibility` 分组）：

```python
{"path": "LAYER_VISIBILITY.city", "group": "visibility", "type": "bool",
 "label": "县界（虚线轮廓）"},
```

**注意**：`dash` 是 tuple，`SettingsManager` 不支持 tuple path，故不出现在设置项里。

---

## 6. 程序完整运行流程

### 6.1 启动阶段

不变。

### 6.2 地图 + 剧本加载流程

```
_auto_load_default()
├─ load_geojson(assets/map.geojson)
│  └─ GeoData.from_file
│     ├─ _classify → shapes_polygon / shapes_line / shapes_point / labels_*
│     │                ★ shapes_city_boundary 一并收集
│     ├─ _assign_lod(shapes_city_boundary)   ★ 新增
│     ├─ _compute_bbox
│     └─ _build_index
│  └─ MapCanvas.load_geojson → renderer.set_data → draw_full
│     └─ _draw_geometry 顺序：
│        render_polygons → render_city_boundaries ★ → render_territory → render_lines
│
└─ _load_default_scenario()  （不变）
```

### 6.3 主循环交互

| 触发 | 调用链 |
|---|---|
| 图层显隐切换 | `refresh_dynamic` → `_restack()` |
| 设置保存 | `_on_settings_applied` → 地图相关则 `map_canvas.redraw()` |
| 县界开关 | `LAYER_VISIBILITY.city` 改后 → `redraw` → `_draw_geometry` 是否调 `render_city_boundaries` |

### 6.4 模块协作关系

不变。

---

## 7. 全局变量与配置项

### 7.1 `constants.py`

不变。

### 7.2 设置窗口可改

| 项 | 是否需重启 |
|---|---|
| `THEME` / `FONT_SIZES` / `FONT_CANDIDATES` | **是** |
| `MAP_STYLE.polygon.outline` / `MAP_STYLE.polygon.width` | 否 |
| `MAP_STYLE.line.*` | 否 |
| `MAP_STYLE.city_line.*` | 否 |
| `MAP_STYLE.*` 其余 | 否 |
| `LAYER_VISIBILITY.*` | 否 |

**已从设置窗口移除**：`MAP_STYLE.polygon.fill`、`MAP_STYLE.city_polygon.fill`。

### 7.3 代码内常量

| 位置 | 值 | 含义 |
|---|---|---|
| `MapRenderer._LAYER_ORDER` | 见 §5.13 | 图层底→顶（本轮加 `"city"`） |
| 各 TAG | `"label"/"water"/"road"/"point"/"polygon"/"line"/"territory"/"city"` | 图层锚点 |
| `MAP_STYLE.polygon.width` 上限 | `20` | 设置窗口允许的最大值 |
| `MAP_STYLE.city_line.dash` | `(3, 3)` | 虚线节奏（tuple，不入设置项） |
| `GeoData._assign_lod` 四档 | `0 / 15 / 45 / 100` | 所有 LOD 图层的通用阈值 |
| 县界 `dash` 无法从设置改 | — | 需直接改 `style.py` |

---

## 8. 已知逻辑限制与待完善清单

### 8.1 未实现功能

| 入口 | 现状 |
|---|---|
| 保存/新游戏/读档 | 提示"尚未实现" |
| 内政/军事/外交 | 空实现 |
| **外交交互** | 只有 `stance` 字段，无改变入口 |
| 部队面板 | 只清空 |
| **type 决定能力** | 未区分 |
| 设置窗口「操作」「游戏」tab | 骨架 |
| **县界 / 郡面 hover / 点击** | 不做交互 |
| **`dash` 可调** | 不支持（tuple path） |

### 8.2 数据层缺失

- `GameState` 只有日期 + 玩家势力 + 3 项资源
- `mountains.geojson` 未接入
- 路网与据点/郡界无拓扑关联
- **势力间无关系矩阵**

### 8.3 逻辑与性能限制

1. `render_lines` / `render_city_boundaries` 均全量遍历 + bbox 粗筛
2. `<Configure>` 全量重绘
3. 绘制方法外层 `except Exception: pass`
4. 标签不做视口预筛
5. 空间索引线性扫描
6. `_build_index` 只取外环
7. 县名匹配固定 0.4°
8. `midpoint_of_line` 死代码
9. Tab 索引硬编码
10. `FactionPanel` 无选中交互
11. `WINDOW_SIZE` 定义未用
12. `_cum_scale` 周期性全量重绘
13. 无测试/打包/lint
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
30. 设置保存/关闭路径必须走 `_do_destroy()`
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
44. `tag_lower(A, B)` 的 `B` 必须非空（已被 `_restack` 根治）
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

**本轮新增：**

64. ★ **`MAP_STYLE.polygon.fill = ""` 是合法的"不填充"值，但不是合法的颜色值**。任何 `color` 类型的设置项若读到空串，会构造出 `"#"` 并被 Tk 拒收（`TclError: invalid color name "#"`）。**修法：把这类无实际意义的 color 设置项从 `settings_schema.ITEMS` 删掉**，保留 `style.py` 里的 `""`。
65. ★ **`city_polygon` 段被彻底移除后，`style.py` 里不能再有它**。若残留 + `fill` 为空串，同样触发第 64 条的报错。
66. ★ **县界是 `CITY_TAG` 下的独立图层**，位于 `_LAYER_ORDER` 的 `polygon` 与 `territory` 之间。这意味着**有主郡的县界虚线会被势力染色覆盖**（territory 是不透明实色 polygon，画在 city 之上）。若要让虚线与染色共存，把 `"city"` 移到 `"territory"` 之后。
67. ★ **`shapes_city_boundary` 收集所有 type**：关隘/仓/谷/山地的 boundary 常常是极小的圆环，视觉上接近一个点。当前不做过滤，视觉噪声很小。
68. ★ **县界 LOD 与水域共用 `_assign_lod`**：四档 `0 / 15 / 45 / 100`，按 bbox 对角线长度。调整出现密度只需改这一个函数。
69. ★ **`render_city_boundaries` 用 `create_line` 而非 `create_polygon`**：因为 Tk 的 polygon 不支持 `dash`。代价是要手动补首尾闭合。
70. ★ **`render_city_labels` 的解包变量 `cid` 无人消费但不能删**：`labels_city` 是五元组，删了会解包错误。
71. ★ **`render_county_labels` 和 `render_city_labels` 都不再查势力色**：郡名 / 县名颜色完全由 `MAP_STYLE.label_*.color` 决定。`_county_label_color` / `_city_label_color` 已删除。
72. ★ **州 / 郡 / 县三级边界的区分完全靠粗细与虚实**：州 4px 实线、郡 1px 实线、县 1px 虚线，全黑。着色完全交给 `territory` 层。
73. ★ **州界宽度在设置窗口内受 `max` 限制**：当前 `MAP_STYLE.polygon.width` 的 `max=20`。若在 `style.py` 里直接改到超过 20，设置窗口打开时会读成 20 并可能回写覆盖，看起来像"改了没反应"。**要改上限只能改 `settings_schema.ITEMS` 里的 `max`**。
74. ⚠️ **待排查：州界宽度改后地图无变化**。可能原因：① `SettingsManager.apply()` 未真正写回 `MAP_STYLE`；② `_on_settings_applied` 未触发 `map_canvas.redraw()`；③ 改的值被 `max` 钳制。需要看 `settings_manager.py` / `settings_window.py` / `main_window._on_settings_applied` 定位。

### 8.4 建议的下一步

1. **排查州界宽度不生效**（见 8.3 第 74 条）
2. **决定县界与染色层的相对位置**（见 8.3 第 66 条）
3. 回合流程
4. 据点交互
5. 人物面板联动
6. 势力面板交互
7. 外交入口（改 `stance`）
8. 接入 `mountains.geojson`
9. `type` 能力矩阵
10. 存档系统
11. 新游戏流程
12. 县界样式细化：`dash` 可调、或区分据点 type

---

## 9. 变更日志

### 9.1 前两轮（摘要）

同前版。

### 9.2 势力染色（上一轮）

同前版。

### 9.3 本轮 · 县界渲染 + 几何层去色

#### 新增

- **`game/map/geo_data.py`**：
  - `shapes_city_boundary` 容器
  - `_classify_county` 内收集 city 的 `boundary`
  - `from_file` 里 `_assign_lod(shapes_city_boundary)`
- **`game/map/renderer.py`**：
  - `CITY_TAG` 类常量
  - `_LAYER_ORDER` 插入 `"city"`（`polygon` 与 `territory` 之间）
  - `_draw_geometry` 调 `render_city_boundaries`
  - `render_city_boundaries()` 方法
- **`game/config/style.py`**：
  - `MAP_STYLE.city_line`（`color` / `width` / `dash`）
  - `LAYER_VISIBILITY.city`
- **`game/config/settings_schema.py`**：
  - `GROUPS` 加 `city` 分组
  - `ITEMS` 加 `city_line.color` / `city_line.width` 两条
  - `ITEMS` 加 `LAYER_VISIBILITY.city` 一条

#### 修改

- **`game/config/style.py`**：
  - `MAP_STYLE.polygon.fill` 改为 `""`（透明）
  - `MAP_STYLE.polygon.outline` 改为 `#000000`
  - `MAP_STYLE.polygon.width` 改为 `4`
  - `MAP_STYLE.line.color` 改为 `#000000`
  - `MAP_STYLE.label_county.color` 改为 `#000000`
  - `MAP_STYLE.label_city.color` 改为 `#000000`
- **`game/map/renderer.py`**：
  - `render_county_labels` 去掉 `_county_label_color` 调用
  - `render_city_labels` 去掉 `_city_label_color` 调用
- **`game/config/settings_schema.py`**：
  - `MAP_STYLE.polygon.width` 的 `max` 从 `8` 调到 `20`
  - `LAYER_VISIBILITY.city` 的 label 改为"县界（虚线轮廓）"

#### 删除

- **`game/map/renderer.py`**：
  - `_county_label_color(cid, default)` 方法
  - `_city_label_color(cid, default)` 方法
- **`game/config/style.py`**：
  - `MAP_STYLE.city_polygon` 整段
- **`game/config/settings_schema.py`**：
  - `MAP_STYLE.polygon.fill` 这条 ITEM
  - `MAP_STYLE.city_polygon.fill` 这条 ITEM

#### 修复

- **`TclError: invalid color name "#"`**：
  - 症状：打开游戏设置窗口立刻报错
  - 原因：`MAP_STYLE.polygon.fill = ""`（及残留的 `city_polygon.fill`），`_build_color` 读到空串后构出 `"#"`，Tk 拒收
  - 修复：从 `settings_schema.ITEMS` 删掉这两条无意义的 color 设置项

#### 设计决策（本轮定稿）

- **几何层只留黑边，着色全部交给 `territory`**：地图上唯一的色块 = 郡势力染色
- **三级边界用粗细与虚实区分**：州 4px 实线、郡 1px 实线、县 1px 虚线，全黑
- **县界不做面填充**：`city_polygon` 废弃，仅保留 `city_line` 虚线轮廓
- **县界范围 = 所有 type**：不做过滤，非县类型的极小 boundary 视觉上接近一个点
- **县界 LOD 复用 `_assign_lod`**：调密度只需改一个函数
- **标签去势力色**：`_county_label_color` / `_city_label_color` 删除，颜色完全由 `MAP_STYLE.label_*.color` 决定
- **`dash` 不进设置项**：tuple path 不被 `SettingsManager` 支持

#### 数据约定（本轮新增）

- city（所有 type）新增 `boundary` 字段，闭合环
- 县界 LOD 四档：`0 / 15 / 45 / 100`，与水域共用
- 三级边界视觉：

  | 层 | 线型 | 颜色 | 宽度 |
  |---|---|---|---|
  | 州界 | 实线 | 黑 | 4（上限 20） |
  | 郡界 | 实线 | 黑 | 1 |
  | 县界 | 虚线 | 黑 | 1 |
  | 郡面染色 | 实心面 | 势力色 | — |

- 标签颜色：州名 `#1A1A1A`、郡名 `#000000`、县名 `#000000`，均不随势力变化

#### 待排查

- 州界宽度改后地图无变化（可能：`apply` 未写回 / 未触发 `redraw` / `max` 钳制）—— 见 §8.3 第 74 条

---

**本轮核心变动集中在 §3.8（CityBoundary）**、**§4.1（map.geojson 新增 boundary）**、**§5.11（geo_data 新容器）/ 5.13（renderer 新图层）/ 5.20（style 去色）/ 5.21（settings_schema 增删）**、**§6.2（绘制顺序）**、**§8.3 第 64–74 条**、**§9.3**。