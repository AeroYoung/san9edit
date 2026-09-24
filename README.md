# 暗耻三国志 — 项目说明文档

> 本轮更新重点：**势力面板色块**（带黑边，行高自适应）、**hover 显示势力名**（方案 B：MapCanvas 传 dict，MainWindow 拼装）、**`_city_index` 加 id 字段**（3 元组 → 4 元组）。新增 §9.13 变更日志。

---

## 0. 术语表（★ 全文统一，先读这里）

| 中文 | 数据 / 代码里的名字 | 说明 |
|---|---|---|
| 州 | `states` / `shapes_polygon` / `_state_index` / `labels_state` | 一级行政区，2 位 id |
| 郡 | `counties` / `shapes_line` / `_county_index` / `labels_county` | 二级行政区，4 位 id |
| **县 = 据点** | `cities` / `shapes_point` / `shapes_city_boundary` / `_city_index` / `labels_city` / `Node` 类 | **三级单元，一个县就是一个据点**，6 位 id |
| 县的 type | `city["type"]` / `Node.type` | 只有三种：`城` / `关隘` / `渡口` |
| **人物** | `characters` / `Character` 类 | 四位 id，全局唯一 |
| **基础数据** | `assets/characters.json` | 1049 人的静态数据（含 49 位穿越人物） |
| **剧本覆盖** | `scenarios/*.json` 的 `characters` 段 | 只覆盖 `势力 / 所属 / 所在 / 身份` |
| **穿越人物** | id ≥ 1001（英布 / 韩信 / 岳飞…） | 默认剧本不加载，由 `character_id_range` 控制 |
| **所属** | `Character.node` | 编制上属于哪个据点，**运行时不变** |
| **所在** | `Character.location` | 人**现在**在哪儿，**运行时可变** |
| **染色层** | `render_territory` 画的县面 | **地图上唯一的着色图层**，不吃 LOD |
| **势力色块** | `FactionPanel` 里势力名前的 ■ | ★ 带黑边，边长 = 行高 − 2 |
| **hover 回调契约** | `MapCanvas._location_callback(dict \| None)` | ★ 本轮从 `str` 改成 `dict` |
| **主官 / 人物数** | （预留，未实现） | 将来由剧本 / `world.characters_at` 提供 |

**「县 = 据点」的核心约定：**

1. **一个县 = 一个据点 = 一个 `Node` 对象。**
2. `map.geojson` 里，一个县就是 `states[i].counties[j].cities[k]` 的一个元素。
3. 每个县**必有** `coords` + `boundary` + `type`。
4. `type` 只区分县的**形态**（城郭 / 关口 / 渡口），**不影响数据结构、不区分行政级别**。
5. 代码里遗留的 `city*` / `*_city_*` 命名，**语义等于「县 / 据点」**，保留。

**「人物」的核心约定：**

1. **三层数据**：`characters.json`（静态）+ `scenarios/*.json`（动态覆盖）+ `_filter_by_year`（运行时按年龄筛选）。
2. **关系字段用 id 引用**。
3. **`faction / node / location / role` 在基础数据里恒为 `null`**，由剧本填充。
4. **剧本里出现但基础数据没有的人 id → 警告并忽略**（不新建）。

**「所属 vs 所在」的核心约定：**

| 概念 | 字段 | 类型 | 含义 | 剧本初始 | 运行时 |
|---|---|---|---|---|---|
| **所属** | `Character.node` | str \| None | 编制上隶属哪个据点 | = 所在 | 不变（除非归属变更） |
| **所在** | `Character.location` | str \| None | 人当前在哪个据点 | = 所属 | 随出征 / 调动 / 流亡变化 |

**「穿越人物」约定：**

- 编号 1001–1049 共 49 人。
- 数据保留在 `characters.json`。
- **默认剧本通过 `character_id_range: [1, 1000]` 排除**。
- 将来做穿越剧本时改成 `[1, 1049]` 或省略此字段（默认全加载）。

**「染色层」约定：**

- 地图上**唯一的着色图层**（一县一据点，按 `node.owner` 上色）。
- **不吃 LOD**：只要在视口内且有主，就画。原因——染色是**主信息**，不是细节。
- 只做**视口粗筛**（屏幕外跳过），性能足够。
- 无主县不染色，州面底色透出。

**「hover 回调契约」约定（★ 本轮）：**

- `MapCanvas._location_callback(info)`，`info` 是 **dict 或 None**。
- dict 结构：`{"state": 州名, "county": 郡名, "city": 县名, "node_id": 县 id, "lon": float, "lat": float}`
- 鼠标离开画布 → 传 `None`。
- **`MapCanvas` 不感知 `World`**，由 `MainWindow` 拿到 dict 后再拼装势力名。

---

## 1. 项目概述

| 项 | 内容 |
|---|---|
| 项目名称 | 暗耻三国志（`APP_TITLE`） |
| 定位 | 三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》 |
| 程序入口 | `main.py` → `MainWindow().run()` |
| 核心功能 | 中国全图矢量渲染、鼠标缩放平移、**光标精确反查州/郡/县/势力**、旬回合制时钟、顶部信息栏与菜单、右侧 Tab 面板框架、多 Tab 设置窗口、剧本系统、**势力面板（带色块）**、**县面势力染色（唯一着色图层，不吃 LOD）**、**据点面板**、**人物面板（玩家势力置顶）**、**人物基础数据（1049 人）+ 190 剧本（52 势力 / 498 人物 / 550 据点）** |
| 运行环境 | Python 3 + 标准库 `tkinter`。**无第三方依赖** |
| 数据来源 | `assets/map.geojson`：13 州 / 106 郡 / 1372 县；`roads.geojson`；`water.geojson`；`mountains.geojson`（未接入）；`characters.json`：1049 人 |
| 剧本来源 | `scenarios/default.json`（**190 年 · 十八路诸侯**） |
| 用户数据 | `userdata/settings.json` |
| 平台 | Windows 优先 |

**当前完成度：**

- ✅ 地图查看器（州/郡/县三级边界 + 道路 + 水域 + 图层显隐 + 县名避让）
- ✅ **县界渲染** / **几何层去色** / **县面势力染色（不吃 LOD）** / **图层顺序保障可读性** / **郡名标签独立字体**
- ✅ **hover 精确反查**：`州 · 郡 · 县 · 势力`
- ✅ 多 Tab 设置系统 / 剧本系统
- ✅ **势力面板**：按玩家/盟友/敌对/中立分组 + **势力色块**（带黑边）
- ✅ **据点面板**：8 列 + 排序 + 嵌套分组（默认州>郡）+ 右键 + 全部展开/折叠 + 定位到地图
- ✅ **人物面板**：8 列 + 排序 + 分组（默认势力，**玩家势力置顶**）+ 右键（人物情报 / 复制编号 / 定位到据点）
- ✅ **`MapController`** / **`MapCanvas.center_on` / `fit_to_node`**
- ✅ **`Character` 类全展开**（44 字段，含中文注释）
- ✅ **`tools/build_characters.py`** / **`tools/build_scenario_190.py`**
- ✅ **三层人物加载**：基础数据 + 剧本覆盖 + 按年份筛选
- ✅ **`character_id_range`**：剧本级人物 id 过滤（穿越人物排除机制）
- ✅ **190 剧本定稿**：**52 势力 / 498 人物 / ~550 据点**
- ✅ **所属 vs 所在**概念：`node` / `location` 分离
- ⚠️ 回合与资源为骨架
- ❌ 内政/军事/外交/存档均为空实现
- ❌ 主官 / 人物数 / 情报三项右键均为占位

---

## 2. 文件结构清单

```
san9edit/
├── main.py
├── README.md
├── tools/
│   ├── build_characters.py           从 xlsx/csv 生成 characters.json
│   └── build_scenario_190.py         生成 190 年默认剧本
├── assets/
│   ├── map.geojson
│   ├── characters.json               1049 位人物基础数据
│   ├── roads.geojson
│   ├── water.geojson
│   └── mountains.geojson             未接入
├── scenarios/
│   └── default.json                  190 剧本（52 势力 / 498 人物 / 550 据点）
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
    │   ├── character.py              44 字段（node / location 分离）
    │   ├── node.py
    │   ├── world.py
    │   ├── scenario.py               三层人物加载 + character_id_range
    │   └── territory.py
    ├── map/
    │   ├── geo_data.py               ★ _city_index 加 id；新增 find_location_detail
    │   ├── viewport.py
    │   └── renderer.py               render_territory 去掉 LOD 粗筛
    └── ui/
        ├── main_window.py            ★ _on_location_change 接收 dict + 查势力
        ├── top_bar.py
        ├── status_bar.py
        ├── map_canvas.py             ★ hover 回调传 dict / None
        ├── map_controller.py
        ├── side_panel.py
        ├── settings_window.py
        ├── window_utils.py
        ├── widgets/collapsible.py
        └── panels/
            ├── faction_panel.py      ★ 势力色块（带黑边，行高自适应）
            ├── character_panel.py
            ├── troop_panel.py
            ├── character/
            │   ├── __init__.py
            │   ├── panel.py          refresh 加玩家势力置顶
            │   ├── model.py
            │   ├── columns.py
            │   ├── sorting.py
            │   ├── grouping.py       build_tree 加 priority_name
            │   ├── group_bar.py
            │   └── context_menu.py
            └── node/
                ├── __init__.py
                ├── panel.py
                ├── model.py
                ├── columns.py
                ├── sorting.py
                ├── grouping.py
                ├── group_bar.py
                └── context_menu.py
```

**依赖方向单向**：`main → ui → core/map → config`。

---

## 3. 核心数据模型

### 3.1 三层 ID 编码

州 2 位 / 郡 4 位 / **县 6 位**。一个六位 id 对应一个县 = 一个据点 = 一个 `Node`。

### 3.2 势力（Faction）

`id` = 君主人物 id。字段：`id` / `name` / `color` / `prestige` / `gold` / `food` / `stance`。
`stance_label()` → `"敌对"` / `"盟友"` / `"中立"`。

### 3.3 人物（Character）

四位 id（"0001"–"1049"）。**静态来自 `characters.json`，动态由剧本覆盖。**

#### 字段一览（共 34 项，其中剧本动态 4 项）

| 分组 | 字段 | 汉语 | 类型 |
|---|---|---|---|
| **标识** | `id` / `name` / `family_name` / `sex` / `portrait` | 编号 / 姓名 / 字 / 性别 / 头像编号 | str / str / str / str / int |
| **五维** | `leadership` / `might` / `intelligence` / `politics` / `charisma` | 统率 / 武力 / 智力 / 政治 / 魅力 | int |
| **时间** | `appear_year` / `birth_year` / `death_year` | 登场年 / 出生年 / 死亡年 | int |
| **相性** | `affinity` | 相性（0–149 圆形值） | int |
| **关系** | `blood` / `father` / `mother` / `generation` / `spouse` / `sworn_brothers` / `liked` / `disliked` | 血缘 / 父亲 / 母亲 / 世代 / 配偶 / 义兄弟 / 亲爱 / 厌恶 | str / str\|None / str\|None / int / str\|None / list[str] / list[str] / list[str] |
| **系统** | `start_official` / `traits` / `formations` / `tactics` | 开始仕官年 / 个性 / 阵型 / 战法 | int / list[str] / list[str] / list[str] |
| **剧本动态** | `faction` | 势力 id | str \| None |
| | **`node`** | **所属**（编制所属据点 id） | str \| None |
| | **`location`** | **所在**（当前所在据点 id） | str \| None |
| | `role` | 身份 | str \| None |

**已删除**：~~`location_name`~~ / ~~`affiliation`~~。

#### 方法

| 方法 | 说明 |
|---|---|
| `is_ruler()` / `is_free()` / `is_appeared(year)` / `is_alive(year)` | 语义判断 |
| `display_name()` | 带表字的展示名 |
| `from_dict(cid, d)` / `to_dict()` | JSON 双向 |
| `apply_override(data)` | 剧本覆盖（`hasattr` 防脏数据） |

### 3.4 县 = 据点（Node）

**静态**：`id` / `name` / `coords` / `type` / `level` / `is_capital` / `boundary`。
**动态**：`owner` / `troops` / `gold` / `food`。
**属性**：`state_id` → `id[:2]`，`county_id` → `id[:4]`，`is_owned()`。

### 3.5 游戏世界（World）

聚合容器：`factions` / `characters` / `nodes` / `state_names` / `county_names`。

**查询**：

```python
def state_name(self, sid):  return self.state_names.get(sid, sid or "—")
def county_name(self, cid): return self.county_names.get(cid, cid or "—")
def faction(self, fid):     return self.factions.get(fid) if fid else None
def node(self, nid):        return self.nodes.get(nid) if nid else None
```

### 3.6 剧本加载器（ScenarioLoader）

**三层人物加载（顺序不可颠倒）：**

```
1. _load_base_characters(world, id_range)
     读 characters.json，只保留 id 落在 id_range 内的人
2. _apply_character_overrides(world, raw["characters"])
     剧本覆盖 faction / node / location / role
3. _filter_by_year(world, world.year)
     只保留 year - birth_year >= 16 且未死
```

**`character_id_range`**：剧本顶层可选字段，`[lo, hi]`。不写 = 全加载。

### 3.7 – 3.9

`CountyStat` / `CityBoundary` 同上轮。

**★ `CityIndex`（`GeoData._city_index`）结构变更（本轮）**：

| 旧 | 新 |
|---|---|
| `(bbox, 县名, ring)` | **`(bbox, 县名, ring, 县 id)`** |

新增字段用于 hover 反查势力（`node_id`）。

---

## 4. 数据格式参考

### 4.1 `assets/map.geojson`

（同上轮）

### 4.2 `assets/characters.json`

（同上轮）

### 4.3 `type` 枚举

只有三种：`城` / `关隘` / `渡口`。

### 4.4 `scenarios/default.json` 结构

```json
{
  "version": 2,
  "id": "default",
  "name": "十八路诸侯 · 190",
  "start": { "year": 190, "month": 1, "xun": 1 },
  "player_faction": "0521",
  "character_id_range": [1, 1000],
  "factions": { ...52 家... },
  "characters": { ...498 条，只写 4 字段... },
  "nodes": { ...~550 条... }
}
```

**关键约定**：

| 段 | 写什么 |
|---|---|
| `character_id_range` | `[1, 1000]` 或省略 |
| `factions` | `name / color / prestige / gold / food / stance` |
| `characters` | **只有** `faction / node / location / role` |
| `nodes` | 首都 + 地盘（无主县不写） |

### 4.5 190 剧本势力清单（52 家）

（同上轮，见 §9.11 / §4.5 表格）

**颜色锁定**：刘备 `#3B8B3B` 暗绿 / 袁绍 `#E8C500` 亮黄 / 曹操 `#2928EF` 蓝 / 孙坚 `#C83030` 红。

### 4.6 势力地盘表达（`build_scenario_190.py`）

```python
FACTIONS = {
    "0521": {
        "name": "曹操", "color": "#2928EF", "stance": 0,
        "capital": "130301",
        "territories": [...],  # 4 位=整郡；6 位=单县
        "max_cities": 14,
    },
}
```

**人物分配**：CORE 手写种子 + 网络投票扩展 + **affinity 兜底**。

---

## 5. 模块与函数清单

### 5.1 – 5.14

（同上轮）

### 5.15 `game/map/renderer.py`

`render_territory` 去掉 LOD 粗筛（上一轮改动，未变）。保留视口粗筛。

### 5.16 – 5.18

（同上轮）

### 5.19 ★ `game/map/geo_data.py`（本轮改动）

**① `_build_city_index` 索引加 id**：

```python
def _build_city_index(self):
    """县界多边形索引。每项 = (bbox, 县名, ring, 县 id)"""
    self._city_index = []
    feats = getattr(self, "shapes_city_boundary", None) or []
    for feat in feats:
        ring = feat["geometry"]["coordinates"]
        if len(ring) < 3:
            continue
        props = feat["properties"]
        name = props.get("县名")
        nid = props.get("id")               # ★
        if not name or not nid:
            continue
        bbox = feat["bbox"]
        self._city_index.append((bbox, name, ring, nid))
```

**② `find_city_at` 解包改成 4 元组**：

```python
for (minx, miny, maxx, maxy), name, ring, nid in self._city_index:   # ★ 4 元组
    ...
```

**③ 新增 `_find_city_with_id`**：

```python
def _find_city_with_id(self, lon, lat):
    """和 find_city_at 同逻辑，但同时返回县 id。
       返回 (县名, 县 id)；未命中 → (None, None)。"""
    best_name = None
    best_id = None
    best_area = None
    for (minx, miny, maxx, maxy), name, ring, nid in self._city_index:
        if not (minx <= lon <= maxx and miny <= lat <= maxy):
            continue
        if not point_in_polygon(lon, lat, ring):
            continue
        area = (maxx - minx) * (maxy - miny)
        if best_area is None or area < best_area:
            best_area, best_name, best_id = area, name, nid
    return best_name, best_id
```

**④ 新增 `find_location_detail`**：

```python
def find_location_detail(self, lon, lat):
    """给 MapCanvas hover 用。返回带 node_id 的 dict。"""
    state = self.find_state_at(lon, lat)
    county = self.find_county_at(lon, lat)

    city_name, node_id = self._find_city_with_id(lon, lat)
    if city_name is None:
        # 兜底：用标签近邻找县名，但拿不到 id
        city_name = self.find_nearest_label(lon, lat, self.labels_city, 0.4)

    return {
        "state":   state,
        "county":  county,
        "city":    city_name,
        "node_id": node_id,
    }
```

### 5.20 ★ `game/ui/map_canvas.py`（本轮改动）

**① `_process_motion` 传 dict**：

```python
def _process_motion(self):
    self._mouse_job = None
    if not self._pending_mouse or not self._location_callback:
        return
    if not self.data:
        return
    x, y = self._pending_mouse
    lon, lat = self.viewport.unproject(x, y)
    info = self.data.find_location_detail(lon, lat)   # ★
    info["lon"] = lon
    info["lat"] = lat
    self._location_callback(info)                      # ★ dict
```

**② `_on_leave` 传 None**：

```python
def _on_leave(self, event):
    if self._location_callback:
        self._location_callback(None)                  # ★ None
```

**MapCanvas 不感知 World**，只输出地理信息字典。

### 5.21 ★ `game/ui/main_window.py`（本轮改动）

```python
def _on_location_change(self, info):
    """info 为 None 或 dict。"""
    if not info:
        self.status_bar.set_location("")
        return

    parts = [p for p in (info.get("state"),
                         info.get("county"),
                         info.get("city")) if p]
    faction = self._faction_at(info.get("node_id"))
    if faction:
        parts.append(faction)

    lon = info.get("lon", 0.0)
    lat = info.get("lat", 0.0)
    text = " · ".join(parts) + f"   （{lon:.2f}°E, {lat:.2f}°N）"
    self.status_bar.set_location(text)

def _faction_at(self, node_id):
    """按据点 id 查势力名；无主 → None。"""
    if not node_id:
        return None
    world = getattr(self.game_state, "world", None)
    if world is None:
        return None
    node = world.node(node_id)
    if node is None or node.owner is None:
        return None
    f = world.faction(node.owner)
    return f.name if f else None
```

**MainWindow 是唯一知道 World 的 hover 拼装点。**

### 5.22 ★ `game/ui/panels/faction_panel.py`（本轮改动）

**① 加 `import tkinter as tk`**

**② `__init__` 加缓存 + 动态色块尺寸**：

```python
self._swatches = {}                                 # PhotoImage 缓存（防 GC）
self._SWATCH_SIZE = self._compute_swatch_size()     # 行高 - 2
```

**③ 新增 `_compute_swatch_size`**：

```python
@staticmethod
def _compute_swatch_size():
    """读 ttk 主题行高，返回比行高略小的色块边长。"""
    import tkinter.font as tkfont

    row_h = None
    try:
        style = ttk.Style()
        v = style.lookup("Treeview", "rowheight")
        if v:
            row_h = int(v)
    except Exception:
        pass

    if not row_h:
        try:
            f = tkfont.nametofont("TkDefaultFont")
            row_h = f.metrics("linespace") + 6
        except Exception:
            row_h = 20

    return max(8, row_h - 2)
```

**④ 新增 `_make_swatch`（带黑边）**：

```python
def _make_swatch(self, color):
    """生成带黑色边框的纯色小方块 PhotoImage。

    做法：先整块填黑，再在内部 (1,1)-(size-1,size-1) 填势力色，
    自然形成 1 像素黑色边框。
    """
    size = self._SWATCH_SIZE
    img = tk.PhotoImage(width=size, height=size)

    # 1) 整块填黑（当边框用）
    img.put("#000000", to=(0, 0, size, size))

    # 2) 内部填势力色（留 1 像素边框）
    try:
        img.put(color, to=(1, 1, size - 1, size - 1))
    except tk.TclError:
        img.put("#888888", to=(1, 1, size - 1, size - 1))
    return img
```

**⑤ `refresh` 里生成色块 + 缓存**：

```python
def refresh(self):
    for item in self.tree.get_children():
        self.tree.delete(item)
    self._swatches.clear()                              # ★ 释放旧引用

    world = getattr(self.game_state, "world", None)
    if world is None or not getattr(world, "factions", None):
        return

    buckets = self._bucket_factions(world)
    for key, title in self._GROUPS:
        factions = buckets[key]
        header = self.tree.insert(
            "", "end",
            text=f"{title} ({len(factions)})",
            open=True,
            tags=(f"group_{key}",),
        )
        for f in factions:
            swatch = self._make_swatch(f.color)         # ★
            self._swatches[f.id] = swatch               # ★ 保引用

            self.tree.insert(
                header, "end",
                text=f.name,
                image=swatch,                           # ★ 势力色块
                values=(...),
                tags=(f"row_{key}",),
            )
```

### 5.23 `game/ui/panels/character/`

`grouping.py::build_tree` 加 `priority_name` 参数；`panel.py::refresh` 传 `priority_name`。上一轮改动，未变。

### 5.24 其它

`faction.py` / `game_state.py` / `utils.py` / `node.py` / `world.py` / `territory.py` / `viewport.py` / `map_controller.py` / `settings_*` / `style.py` 未改动。

---

## 6. 程序完整运行流程

### 6.1 启动阶段

（同上轮）

### 6.2 地图 + 剧本加载流程

（同上轮）

### 6.3 剧本生成流程（离线）

（同上轮）

### 6.4 ★ 主循环交互（hover 链路更新）

| 触发 | 调用链 |
|---|---|
| 鼠标移动 | `_on_motion` → 40ms 节流 → `_process_motion` |
| ↳ 反查 | `viewport.unproject` → `data.find_location_detail(lon, lat)` → **dict** |
| ↳ 拼装 | `MapCanvas._location_callback(info)` → **`MainWindow._on_location_change(info)`** |
| ↳ 势力 | `MainWindow._faction_at(node_id)` → `world.node(id)` → `node.owner` → `world.faction(id)` → `f.name` |
| ↳ 显示 | `status_bar.set_location(text)` → `州 · 郡 · 县 · 势力   （经度°E, 纬度°N）` |
| 鼠标离开 | `_on_leave` → `_location_callback(None)` → 状态栏清空 |
| 滚轮 / 拖拽 | `viewport.zoom / pan_pixels` → `renderer.zoom / pan` |
| 顶部信息栏 | 200ms 轮询 `game_state.get_display_items()` |
| 设置保存 | `_on_settings_applied` → 地图相关则 `map_canvas.redraw()` |
| 据点右键 → 定位 | `context_menu._locate` → `MapController.fit_to_node` → `MapCanvas.fit_to_node` → `_node_bbox` → `viewport.fit_to_bbox` → `draw_full` |
| 据点右键 → 展开/折叠 | `context_menu._set_all_open` → `tree.item(open=...)` 递归 |
| 据点列头点击 | `_on_heading_click` → `self._sort_key/_sort_desc` → `refresh` |
| 据点分组切换 | `GroupBar._toggle` → `on_change` → `NodePanel.refresh` |
| 人物列头点击 | `CharacterPanel._on_heading_click` → `refresh` |
| 人物右键 → 定位到据点 | `context_menu._locate` → `MapController.fit_to_node` |
| 人物分组切换 | `GroupBar._toggle` → `on_change` → `CharacterPanel.refresh` → **`priority_name` 玩家置顶** |

### 6.5 模块协作关系

```
main.py
└─ ui.main_window ──┬─ config.settings_manager ─ config.style
                    │                            └ config.settings_schema
                    ├─ core.game_state
                    ├─ core.scenario ─── core.world ─── core.faction
                    │                    ├─ core.character
                    │                    └─ core.node
                    ├─ ui.top_bar
                    ├─ ui.status_bar
                    ├─ ui.map_canvas ─── map.viewport
                    │                   map.renderer ─── map.geo_data
                    │                                  └ core.territory（保留）
                    │   ★ hover 回调 → MainWindow._on_location_change
                    │                    ↳ 查 World 拼势力名 → status_bar
                    ├─ ui.map_controller
                    ├─ ui.settings_window
                    └─ ui.side_panel ──── panels.faction_panel ★ 色块
                                       ├─ panels.node ── map_controller
                                       ├─ panels.character ── map_controller ★ 置顶
                                       └─ panels.troop_panel
                       config.constants
tools.build_characters ──── assets/characters.json
tools.build_scenario_190 ── scenarios/default.json
```

---

## 7. 全局变量与配置项

### 7.1 `constants.py`

（同上轮）

### 7.2 设置窗口可改

（不变）

### 7.3 代码内常量

| 位置 | 值 | 含义 |
|---|---|---|
| `MapCanvas._MIN_VALID_SIZE` | `10` | 布局未完成阈值 |
| `TopBar._REFRESH_INTERVAL_MS` | `200` | 信息栏轮询 |
| `GeoData._assign_lod` 四档 | `0 / 15 / 45 / 100` | **县界 / 郡界 / 州界 / 水体 / 道路 / 标签**共用；**染色层不吃** |
| `MAP_STYLE.city_line.dash` | `(3, 3)` | 虚线节奏 |
| `MapCanvas.fit_to_node` 的 `margin` | `0.7` | 定位留边距 |
| `MapCanvas.fit_to_node` 的 `max_scale` | `200` | 小 boundary 放大上限 |
| hover 节流 | `40 ms` | `_process_motion` |
| 标签刷新节流 | `30 ms` | `_schedule_label_refresh` |
| settle redraw | `180 ms` | 滚轮静默后补绘 |
| `renderer.zoom` 重投影阈值 | `_cum_scale > 2.0 / < 0.5` | 超过触发 `draw_full` |
| 据点面板默认分组 | `["state", "county"]` | `GroupBar.initial_selected` |
| 人物面板默认分组 | `["faction"]` | `GroupBar.initial_selected` |
| 人物面板玩家势力置顶 | `priority_name=faction.name` | 只对最外层生效 |
| **势力色块尺寸** | **`行高 − 2`** | ★ 动态计算（`_compute_swatch_size`） |
| **势力色块黑边** | **`1 px`** | ★ `img.put("#000000", to=(0,0,size,size))` |
| `character_id_range` 默认 | `[1, 1000]` | 排除穿越人物 |
| `character_id_range` 不写 | `[1, 9999]` | 全部加载 |
| 190 剧本势力 / 人物 / 据点 | `52 / 498 / ~550` | 定稿 |
| `Character._DEFAULT_STAT` | `50` | 五维缺省值 |

---

## 8. 已知逻辑限制与待完善清单

### 8.1 未实现功能

| 入口 | 现状 |
|---|---|
| 存档 / 新游戏 / 读档 | 提示"尚未实现" |
| 内政 / 军事 / 外交 | 空实现 |
| 外交交互 | 只有 `stance` 字段 |
| 部队面板 | 只清空 |
| `type` 差异化的能力 / 玩法 | 未做 |
| 设置窗口「操作」「游戏」tab | 骨架 |
| 县界 / 县面 hover | 不做 |
| `dash` 可调 | 不支持 |
| 郡面分级调色 | 字段全保留但不消费 |
| 字体可在 UI 里改 | 不支持 |
| 据点面板「主官」列 / 「人物」列 | 占位 |
| 据点面板右键三项 | 占位，只 `print` |
| 据点面板字体 / 字号可调 | 不支持 |
| 据点面板列宽 / 分组 / 排序持久化 | 不支持 |
| 人物面板右键「人物情报」 | 占位，只 `print` |
| 人物头像加载 | 未实现（`portrait` 已存） |
| 人物面板状态持久化 | 不支持 |
| **`Character.location` 运行时变更** | **未实现（字段已存，无逻辑）** |
| **`Character.node` 归属变更** | **未实现** |
| **人物面板势力分组顺序可调** | **未实现（目前仅玩家置顶 + 其余字典序）** |
| **hover 近邻兜底显示势力** | **未实现（见 §8.3 第 135 条）** |
| **势力色块间距可调** | **未实现（受 ttk 主题控制，不可直接调）** |

### 8.2 数据层缺失

（同上轮）

### 8.3 逻辑与性能限制

（承接前几轮）

**119–133.**（同上轮）

**134. ★ `_city_index` 从 3 元组改 4 元组，任何解包处必须同步**：
- 现在 `(bbox, 县名, ring, 县 id)`
- 已改：`_build_city_index` / `find_city_at` / `_find_city_with_id`
- 若将来新增遍历处，务必 4 元组解包

**135. ★ hover 兜底不返回 `node_id`**：
- `find_location_detail` 里，如果 `_find_city_with_id` 未命中多边形，回落到 `find_nearest_label` → 只有县名，无 id
- 结果：近邻兜底时**不显示势力名**
- 出现场景：县界缝隙、多边形外但靠近中心点
- 影响：轻微，不影响主功能

**136. ★ `MapCanvas` 与 `World` 解耦**：
- `MapCanvas` 只输出地理信息 dict（state / county / city / node_id / lon / lat）
- 势力名由 `MainWindow._on_location_change` 拼装
- **不要**给 `MapCanvas` 塞 `World` 引用（方案 A 的债）

**137. ★ 势力色块大小必须动态计算**：
- 不能硬编码（不同系统 ttk 行高不同：Windows ~20，Linux ~22，Mac ~24）
- `_compute_swatch_size` 优先读 `Style.lookup("Treeview", "rowheight")`，退化到 `TkDefaultFont.metrics("linespace") + 6`
- 色块 = 行高 − 2

**138. ★ `PhotoImage` 必须显式填整块**：
- `img.put(color)` 单色字符串在部分 Tk 版本只填左上角一个像素
- **必须** `img.put(color, to=(0, 0, size, size))`

**139. ★ `PhotoImage` 必须保引用**：
- `FactionPanel._swatches` 缓存
- 每次 `refresh` 先 `clear()` 再重建

**140. ★ 势力色块带黑边**：
- 先整块填 `#000000`
- 再在 `(1, 1, size-1, size-1)` 填势力色
- 想调边框粗细改 `to` 起点；想调颜色改 `#000000`

### 8.4 建议的下一步

1. **实现"出征 / 调动"**：改 `Character.location`，不动 `node`
2. **`world.characters_at(node_id)` 聚合**（据点面板「人物」列真实数据）
3. **人物面板右键「人物情报」接入真实窗口**
4. **`Character.affinity` 参与势力关系计算**
5. **非首都据点兵/钱/粮细化**
6. **存档系统 / 新游戏流程 / 回合流程**
7. **`type` 赋予玩法差异**
8. **外交入口（改 `stance`）**
9. **接入 `mountains.geojson`**
10. **人工核查 `_ambiguous_names`**（5 组重名）
11. **hover 近邻兜底也返回 node_id**（`find_nearest_label` 加 id 输出）
12. **势力面板组内排序可调**（当前威望降序）

---

## 9. 变更日志

### 9.1 – 9.12（摘要）

- 9.1：剧本系统 + 外交分组 + 层序修复
- 9.2：郡面势力染色
- 9.3：县界渲染 + 几何层去色
- 9.4：hover 反查县名 + 州界渲染修复
- 9.5：县面势力染色 + 图层顺序调整
- 9.6：郡名标签独立字体（KaiTi）+ 缩小 15%
- 9.7：术语「县 = 据点」统一 + `type` 枚举收缩
- 9.8：据点面板重构 + `MapController` + `fit_to_node` + 右键
- 9.9：人物基础数据 + `Character` 全展开
- 9.10：三层人物加载 + 190 剧本初版 + 人物面板重构
- 9.11：190 剧本定稿（52 势力 / 498 人物 / ~550 据点）+ 所属/所在拆分 + 穿越人物排除
- 9.12：染色层去 LOD + 人物面板玩家势力置顶

### 9.13 势力色块 + hover 显示势力（第十四轮）

#### 需求

1. **势力面板**：势力名前面加一个小方块，颜色 = 该势力颜色
2. **色块带黑边**，边长比行高**稍小一点点**
3. **鼠标划过地图**：除了州/郡/县，还要显示占据该县的势力名

#### 改动

**修改文件：**

- `game/map/geo_data.py` —— `_build_city_index` 加 id（3→4 元组）；`find_city_at` 解包改 4 元组；新增 `_find_city_with_id` / `find_location_detail`
- `game/ui/map_canvas.py` —— `_process_motion` 传 dict；`_on_leave` 传 `None`
- `game/ui/main_window.py` —— `_on_location_change` 接收 dict 并查 World 拼势力名；新增 `_faction_at`
- `game/ui/panels/faction_panel.py` —— 加色块（`_make_swatch` / `_compute_swatch_size` / `_swatches` 缓存）

**未改动**：

- `Character` / `Node` / `Faction` / `ScenarioLoader`
- 其它面板（据点 / 人物 / 部队）
- 染色层 / LOD

#### 设计决策

- **hover 走方案 B（结构化回调）而非 A（给 MapCanvas 塞 World）**：
  - 理由：`MapCanvas` 保持纯地图控件，将来可复用于别的场景
  - `MainWindow` 本来就是装配工，持有 World，拼装天然
  - 代价：回调契约从 `str` 变 `dict`，`_on_leave` 从 `""` 变 `None`
- **`_city_index` 加 id 而非另建新索引**：
  - 加一个字段，元组长度 3→4，改动集中
  - 唯一风险：忘了同步解包处 → grep 验证
- **色块尺寸动态计算**：
  - 不能硬编码（系统 ttk 行高不同）
  - `Style.lookup("Treeview", "rowheight")` 优先；退化到 `TkDefaultFont.metrics("linespace") + 6`
  - 色块 = 行高 − 2
- **色块带黑边**：先整块填黑，再在 `(1,1,size-1,size-1)` 填势力色
- **`img.put(color, to=...)` 显式填整块**：单色字符串 `put` 在部分 Tk 版本只填 1 像素
- **`PhotoImage` 保引用**：`_swatches` 缓存，`refresh` 先 `clear` 再重建

#### 症状与根因

| 症状 | 根因 |
|---|---|
| 色块只显示 1 个像素 | `img.put(color)` 单色字符串在部分 Tk 版本只填左上角 |
| 色块大小不对 | 硬编码 12 在 Windows 上偏小，Linux 上偏大 |

#### 待办（本轮明确记录）

- hover 近邻兜底不返回 `node_id` → 该情况下不显示势力名
- 势力色块间距受 ttk 主题控制，不可直接调
- 势力面板组内排序（当前威望降序）将来若需可调，另做

---

**本轮核心变动集中在 §0（hover 回调契约）**、**§3.9（CityIndex 4 元组）**、**§5.19 / 5.20 / 5.21 / 5.22（geo_data / map_canvas / main_window / faction_panel）**、**§6.4（hover 链路）**、**§7.3（色块尺寸常量）**、**§8.3 第 134–140 条**、**§9.13**。