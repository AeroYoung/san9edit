# 暗耻三国志 — 项目说明文档

> 本轮更新重点：**`Character` 类全展开**（44 列字段全覆盖，带中文注释）、**新增 `tools/build_characters.py` 基础数据生成脚本**、**新增 `assets/characters.json` 基础人物数据（1049 人）**、**关系字段由名字转 id**、**势力 / 所在 / 所属 / 身份 留空由剧本填充**。新增 §9.9 变更日志。

---

## 0. 术语表（★ 全文统一，先读这里）

| 中文 | 数据 / 代码里的名字 | 说明 |
|---|---|---|
| 州 | `states` / `shapes_polygon` / `_state_index` / `labels_state` | 一级行政区，2 位 id |
| 郡 | `counties` / `shapes_line` / `_county_index` / `labels_county` | 二级行政区，4 位 id |
| **县 = 据点** | `cities` / `shapes_point` / `shapes_city_boundary` / `_city_index` / `labels_city` / `Node` 类 | **三级单元，一个县就是一个据点**，6 位 id |
| 县的 type | `city["type"]` / `Node.type` | 只有三种：`城` / `关隘` / `渡口` |
| **人物** | `characters` / `Character` 类 | 四位 id，全局唯一 |
| **基础数据** | `assets/characters.json` | 1049 人的静态数据（五维 / 关系 / 个性 / 阵型 / 战法…） |
| **剧本覆盖** | `scenarios/*.json` 的 `characters` 段 | 只覆盖 `势力 / 据点 / 所在 / 所属 / 身份`（暂未实现） |
| **主官** | （预留，未实现） | 将来由剧本指定 |
| **人物数** | （预留，未实现） | 将来按 `Character.node == 据点 id` 统计 |

**「县 = 据点」的核心约定：**

1. **一个县 = 一个据点 = 一个 `Node` 对象。** 不存在「一个县含多个据点」或「一个据点分属多个县」的情况。
2. 在 `map.geojson` 里，一个县就是 `states[i].counties[j].cities[k]` 的一个元素。
3. 每个县**必有** `coords`（中心点）+ `boundary`（闭合多边形）+ `type`。
4. `type` 只区分县的**形态**（城郭 / 关口 / 渡口），**不区分行政级别、不影响数据结构**：
   - 三种 type 的字段完全一样
   - 三种 type 的渲染逻辑完全一样（除样式细节外）
   - 三种 type 都参与势力染色、都参与 hover 反查、都有 `Node` 对象
5. 代码里遗留的 `city*` / `*_city_*` 命名（如 `shapes_city_boundary` / `labels_city` / `find_city_at`），**语义等于「县 / 据点」**，不是「城市」。改名成本大、收益为零，保留。

**「人物」的核心约定（本轮新增）：**

1. **静态数据 + 剧本覆盖** 双层结构：
   - `assets/characters.json`：五维 / 生卒年 / 相性 / 关系 / 个性 / 阵型 / 战法 等**静态字段**
   - `scenarios/*.json`：`势力 / 据点 / 所在 / 所属 / 身份` 等**动态字段**
2. **关系字段用 id 引用**，不用名字（避免重名歧义）。
3. **`faction / node / location_name / affiliation / role` 在基础数据里恒为 `null`**，由剧本填充。

---

## 1. 项目概述

| 项 | 内容 |
|---|---|
| 项目名称 | 暗耻三国志（`APP_TITLE`） |
| 定位 | 三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》 |
| 程序入口 | `main.py` → `MainWindow().run()` |
| 核心功能 | 中国全图矢量渲染（州/郡/县三级边界 + 道路路网 + 水域湖泊/河流）、鼠标缩放平移、**光标精确反查州/郡/县**、旬回合制时钟、顶部信息栏与菜单、右侧 Tab 面板框架、多 Tab 设置窗口、剧本系统、势力关系分组展示、**县面势力染色（唯一着色图层）**、**据点面板（多列 + 排序 + 分组 + 右键菜单 + 定位）**、**人物基础数据（1049 人）** |
| 运行环境 | Python 3 + 标准库 `tkinter`。仅依赖标准库，**无第三方依赖、无 requirements.txt**（生成 `characters.json` 时临时用 `openpyxl`） |
| 数据来源 | `assets/map.geojson`：13 州 / 106 郡 / 1372 县（= 1372 据点）；`assets/roads.geojson`：约 600 条道路；`assets/water.geojson`：205 条河流/湖泊；`assets/mountains.geojson`：42 个山地区块（未接入）；**`assets/characters.json`：1049 位人物基础数据（本轮新增）** |
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
- ✅ **据点面板**：8 列 + 点列头排序 + 正交嵌套分组（默认州>郡）+ 右键菜单 + 全部展开/折叠 + 定位到地图
- ✅ **`MapController`** 作为面板访问地图的唯一中介
- ✅ **`MapCanvas.center_on` / `fit_to_node`**
- ✅ **`Character` 类全展开**（44 列字段，含中文注释）
- ✅ **`assets/characters.json`**：1049 位人物基础数据
- ✅ **`tools/build_characters.py`**：从 xlsx/csv 一键生成 JSON
- ⚠️ 回合与资源为骨架
- ❌ 内政/军事/外交/存档均为空实现
- ❌ **剧本覆盖基础数据（加载逻辑）未实现**
- ❌ 主官 / 人物数 / 情报三项右键均为占位

---

## 2. 文件结构清单

```
san9edit/
├── main.py
├── README.md
├── tools/                         ★ 新增
│   └── build_characters.py        从 xlsx/csv 生成 characters.json
├── assets/
│   ├── map.geojson                 city 带 boundary，type ∈ {城, 关隘, 渡口}
│   ├── characters.json            ★ 新增：1049 位人物基础数据
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
    │   ├── character.py           ★ 全展开重写（44 字段）
    │   ├── node.py                 Node = 县 = 据点
    │   ├── world.py                加 state_names / county_names
    │   ├── scenario.py             加 _build_region_names
    │   └── territory.py            郡级统计保留，当前渲染层不再消费
    ├── map/
    │   ├── geo_data.py
    │   ├── viewport.py
    │   └── renderer.py
    └── ui/
        ├── main_window.py          创建 MapController 并注入
        ├── top_bar.py
        ├── status_bar.py
        ├── map_canvas.py           加 center_on / fit_to_node
        ├── map_controller.py       新增：地图中介
        ├── side_panel.py           接收 map_controller
        ├── settings_window.py
        ├── window_utils.py
        ├── widgets/collapsible.py
        └── panels/
            ├── faction_panel.py
            ├── character_panel.py
            ├── troop_panel.py
            └── node/               新增包，取代 node_panel.py
                ├── __init__.py
                ├── panel.py        主面板
                ├── model.py        NodeRow
                ├── columns.py      列定义（单一真相源）
                ├── sorting.py      排序
                ├── grouping.py     分组 + 嵌套树构建
                ├── group_bar.py    分组维度选择条
                └── context_menu.py 右键菜单
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

### 3.3 人物（Character）★ 本轮全展开

四位 id（"0001"–"1049"），全局唯一。**静态字段来自 `assets/characters.json`，动态字段由剧本覆盖。**

#### 字段一览（共 33 项 + 剧本 5 项）

| 分组 | 字段 | 汉语 | 类型 | 说明 |
|---|---|---|---|---|
| **标识** | `id` | 编号 | str | 四位字符串 |
| | `name` | 姓名 | str | |
| | `family_name` | 字 | str | 表字，如「云长」 |
| | `sex` | 性别 | str | 「男」/「女」 |
| | `portrait` | 头像编号 | int | 立绘资源索引 |
| **五维** | `leadership` | 统率 | int | 带兵能力 |
| | `might` | 武力 | int | 武艺 / 单挑 |
| | `intelligence` | 智力 | int | 谋略 / 计策 |
| | `politics` | 政治 | int | 内政 / 外交 |
| | `charisma` | 魅力 | int | 人格魅力 |
| **时间** | `appear_year` | 登场年 | int | |
| | `birth_year` | 出生年 | int | |
| | `death_year` | 死亡年 | int | |
| **相性** | `affinity` | 相性 | int | 0–149，决定天然亲疏 |
| **关系（id 引用）** | `blood` | 血缘 | str | 家族 / 氏族标签，**不转 id** |
| | `father` | 父亲 | str \| None | id 引用 |
| | `mother` | 母亲 | str \| None | id 引用 |
| | `generation` | 世代 | int | 家族辈分 |
| | `spouse` | 配偶 | str \| None | id 引用 |
| | `sworn_brothers` | 义兄弟 | list[str] | id 列表 |
| | `liked` | 亲爱武将 | list[str] | id 列表 |
| | `disliked` | 厌恶武将 | list[str] | id 列表 |
| **系统** | `start_official` | 开始仕官年 | int | 0 = 未出仕，251 = 251 年 |
| | `traits` | 个性 | list[str] | 如 ["神眼","疾走"] |
| | `formations` | 阵型 | list[str] | 如 ["鱼鳞","锋矢"] |
| | `tactics` | 战法 | list[str] | 如 ["突击","牵制"] |
| **剧本动态** | `faction` | 势力 | str \| None | 势力 id，基础数据里 null |
| | `node` | 据点 | str \| None | 六位据点 id |
| | `location_name` | 所在 | str \| None | 城池名 |
| | `affiliation` | 所属 | str \| None | 城池名 |
| | `role` | 身份 | str \| None | 「君主」/「一般」等 |

#### 方法

| 方法 | 说明 |
|---|---|
| `is_ruler()` | 是否为其所属势力的君主（势力 id = 君主 id 约定） |
| `is_free()` | 是否在野 |
| `is_appeared(year)` | 该年份是否已登场 |
| `is_alive(year)` | 该年份是否健在（生卒缺失时不作为约束） |
| `display_name()` | 带表字的展示名，如「关羽（云长）」 |
| `from_dict(cid, d)` | 从 JSON 一条 dict 构造 |
| `to_dict()` | 转回 dict（存档 / 调试） |
| `apply_override(data)` | 用剧本 dict 覆盖已有字段（防脏数据：只覆盖已有属性） |

#### 数据质量字段（JSON 里）

`characters.json` 顶层还带三个排查字段（游戏加载时忽略）：

| 字段 | 说明 |
|---|---|
| `_name_index` | `名字 → id` 索引（重名取编号最小者） |
| `_ambiguous_names` | 重名表：`名字 → [id, id, ...]` |
| `_missing_refs` | 关系字段里引用了但表里不存在的人名 |

### 3.4 县 = 据点（Node）

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

**属性**：`state_id` → `id[:2]`，`county_id` → `id[:4]`，`is_owned()`。

**关于 `type` 的约定：**

- `type` 只标记县的**形态**，不影响任何数据结构
- 三种 type 的 `Node` 字段完全一样
- 三种 type 都参与：势力染色 / hover 反查 / 剧本覆盖 / 面板展示
- **没有** `if type == "城"` 之类的逻辑分支（渲染层从设计上不区分 type）

### 3.5 游戏世界（World）

聚合容器：`factions` / `characters` / `nodes` / `state_names` / `county_names`。

**新增字段：**

```python
self.state_names = {}     # "01"   -> "并州"
self.county_names = {}    # "0101" -> "上党郡"
```

**新增查询：**

```python
def state_name(self, sid):  return self.state_names.get(sid, sid or "—")
def county_name(self, cid): return self.county_names.get(cid, cid or "—")
```

名字表由 `ScenarioLoader._build_region_names` 从 `geo_data.shapes_line` 的 `properties` 填充。

### 3.6 剧本加载器（ScenarioLoader）

`ScenarioLoader.load(path, geo_data)` → `World`。

- `_build_nodes_from_geo`：遍历 `geo_data.shapes_point`，**每个 shapes_point 元素 → 一个 Node**
- `_build_region_names`：遍历 `geo_data.shapes_line`，填 `world.state_names` / `world.county_names`
- `_apply_node_overrides`：用 `scenarios/default.json` 的 `nodes` 覆盖 `owner / troops / gold / food`
- **`_build_character`**：从剧本 `characters` 段构造 `Character`（参数与新版 `Character` 完全兼容）

> **未实现（下一步）**：从 `assets/characters.json` 加载全量人物，再用剧本 `characters` 段做**增量覆盖**。

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

**渲染层 + 查询层 + 染色层 + 定位层共用**，由 `GeoData.shapes_city_boundary` 承载。

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

### 3.9 县界空间索引（CityIndex）

`GeoData._city_index`，结构 `(bbox, 名称, 外环顶点)`，与 `_state_index` / `_county_index` 同构。

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
        "type": "城",
        "boundary": [[lon,lat], ...]
      }]
    }]
  }]
}
```

### 4.2 `assets/characters.json` 结构（本轮新增）

```json
{
  "version": 1,
  "source": "314英雄集结武将数据.xlsx",
  "count": 1049,
  "characters": {
    "0001": {
      "name": "阿会喃",
      "family_name": "",
      "sex": "男",
      "portrait": 127,
      "leadership": 65,
      "might": 74,
      "intelligence": 26,
      "politics": 33,
      "charisma": 44,
      "appear_year": 217,
      "birth_year": 190,
      "death_year": 225,
      "affinity": 62,
      "blood": "阿会喃",
      "father": null,
      "mother": null,
      "generation": 1,
      "spouse": null,
      "sworn_brothers": [],
      "liked": ["0023", "0739"],
      "disliked": [],
      "start_official": 251,
      "traits": ["南中", "短虑"],
      "formations": ["锋矢", "长蛇"],
      "tactics": ["突击"],
      "faction": null,
      "location_name": null,
      "affiliation": null,
      "role": null
    }
  },
  "_name_index": { "阿会喃": "0001" },
  "_ambiguous_names": { "李丰": ["0917", "0918", "0919"] },
  "_missing_refs": {}
}
```

**关键约定：**

| 字段 | 类型 | 说明 |
|---|---|---|
| `sworn_brothers / liked / disliked` | `list[str]` | id 数组，**空就是 `[]`**，不是 `null` |
| `father / mother / spouse` | `str \| null` | 单值 id |
| `blood` | `str` | 血缘家族名，**不转 id** |
| `traits / formations / tactics` | `list[str]` | 按空格切分 |
| `faction / location_name / affiliation / role` | `null` | 基础数据里**恒为 null**，剧本填 |

**生成方式**：`python tools/build_characters.py`（脚本与 xlsx 同目录，自动找文件）。

**数据来源**：《314英雄集结武将数据.xlsx》，1049 行，列含义见 §5.7。

### 4.3 `type` 枚举

**只有三种：**

| type | 含义 | 典型 |
|---|---|---|
| `城` | 有城郭的县，通常是郡治或重要城市 | 长子、晋阳、临戎 |
| `关隘` | 关口、隘口 | 壶口关、天井关、鸡鹿塞 |
| `渡口` | 渡口、津 | （本数据集暂未出现，为将来预留） |

**已废弃的旧枚举**：~~`县`~~ / ~~`渡口/津`~~ / ~~`仓/监`~~ / ~~`谷`~~ / ~~`山地`~~。

**据点面板的显示逻辑**：`is_capital == True` 时，类型列显示「郡治」；否则显示原始 `type`。这是**展示层**的覆盖，不改数据。

### 4.4 `scenarios/default.json` 结构

version 1。字段与前一版一致：

- `nodes` 段：以六位 id 为 key，覆盖 `owner / troops / gold / food`
- `characters` 段：以四位 id 为 key，覆盖 `faction / node / location_name / affiliation / role`（**新语义**）

---

## 5. 模块与函数清单

### 5.1 `main.py`

`main()` → `MainWindow().run()`。

### 5.2 `game/config/constants.py`

路径常量：`ASSETS_DIR` / `DEFAULT_MAP_PATH` / `DEFAULT_WATER_PATH` / `DEFAULT_ROADS_PATH` / `SCENARIOS_DIR` / `DEFAULT_SCENARIO_PATH` / `APP_TITLE` / `MIN_WINDOW_SIZE`。

> **待新增**：`DEFAULT_CHARACTERS_PATH = ASSETS_DIR / "characters.json"`（实现剧本覆盖加载时补）。

### 5.3 – 5.6

`faction.py` / `game_state.py` / `utils.py` **未改动**。

`utils.lighten_color` / `darken_color`：**保留**，当前渲染层不调用。

### 5.7 `game/core/character.py` ★ 本轮全展开重写

**类结构**：见 §3.3 字段表 + §5.7 下方方法表。

**构造参数**（全部带中文注释）：

```python
Character(
    cid, name,
    # 基础信息
    family_name="", sex="男", portrait=0,
    # 五维
    leadership=50, might=50, intelligence=50, politics=50, charisma=50,
    # 时间
    appear_year=0, birth_year=0, death_year=0,
    # 相性
    affinity=0,
    # 关系（id 引用）
    blood="", father=None, mother=None, generation=1,
    spouse=None, sworn_brothers=None, liked=None, disliked=None,
    # 系统
    start_official=0, traits=None, formations=None, tactics=None,
    # 剧本动态
    faction=None, node=None,
    location_name=None, affiliation=None, role=None,
)
```

**关键方法：**

| 方法 | 说明 |
|---|---|
| `is_ruler()` | 是否为其所属势力的君主（势力 id = 君主 id） |
| `is_free()` | 是否在野 |
| `is_appeared(year)` | 该年份是否已登场 |
| `is_alive(year)` | 该年份是否健在（生卒缺失时不作为约束） |
| `display_name()` | 带表字的展示名，如「关羽（云长）」 |
| `from_dict(cid, d)` | classmethod，从 JSON 一条 dict 构造 |
| `to_dict()` | 转回 dict（存档 / 调试） |
| `apply_override(data)` | 用剧本 dict 覆盖已有字段 |

**兼容性**：`scenario.py::_build_character` 的 keyword 调用不受影响。

### 5.8 `tools/build_characters.py` ★ 本轮新增

**用途**：从《314英雄集结武将数据.xlsx》（或 CSV）生成 `characters.json`。

**用法**（脚本与 xlsx 同目录，直接运行）：

```bash
pip install openpyxl
python build_characters.py
```

**行为**：
1. 在脚本同目录找第一个 `.xlsx` / `.xlsm` / `.csv`
2. 读表，跳过表头
3. 第一遍建 `名字 → [id, ...]` 索引，记录重名
4. 第二遍构造人物，关系字段由名字转 id（**重名取编号最小者**）
5. 输出 `characters.json` 到脚本同目录
6. 控制台打印重名列表与找不到的引用

**列映射**（0-based）：

| 索引 | 列名 | 用途 |
|---|---|---|
| 0 | 编号 | → `id`（补零四位） |
| 1 | 姓名 | → `name` |
| 2 | 字 | → `family_name` |
| 3 | 军团 | **不读**（改名「势力」，留空） |
| 4–6 | 所在 / 所属 / 身份 | **不读**（留空） |
| 7–11 | 统率 / 武力 / 智力 / 政治 / 魅力 | → 五维 |
| 12 | 头像 | → `portrait` |
| 13–15 | 个性 / 阵型 / 战法 | → 空格切分字符串列表 |
| 16 | 开始仕官 | → `start_official` |
| 17 | 性别 | → `sex` |
| 18–20 | 登场年 / 出生年 / 死亡年 | → 时间 |
| 21 | 相性 | → `affinity` |
| 22 | 血缘 | → `blood`（**不转 id**） |
| 23 | 父亲 | → `father`（转 id） |
| 24 | 母亲 | → `mother`（转 id） |
| 25 | 世代 | → `generation` |
| 26 | 配偶 | → `spouse`（转 id） |
| 27 | 义兄弟 | → `sworn_brothers`（转 id） |
| 28–35 | 亲爱武将 1–8 | → `liked`（转 id） |
| 36–43 | 厌恶武将 1–8 | → `disliked`（转 id） |

### 5.9 – 5.11

`game/core/node.py` / `world.py` / `scenario.py` 同上轮（World 加名字表、ScenarioLoader 加 `_build_region_names`）。

### 5.12 `game/core/territory.py`

`CountyStat` 数据类 + `compute_county_stats(world)` + `CAPITAL_BONUS = 2.0`。**保留不动**。

### 5.13 `game/map/geo_data.py`

**未改动**（本轮）。容器、`from_file`、`_classify`、`_classify_county`、查询方法、索引均同上轮。

### 5.14 `game/map/viewport.py`

未改动。`project` / `unproject` / `fit_to_bbox` / `zoom` / `pan_pixels` / `span_px`。

### 5.15 `game/map/renderer.py`

未改动。`_LAYER_ORDER`、`render_territory`、`set_world`、`draw_text` 等均同上轮。

### 5.16 `game/ui/map_canvas.py`

**本轮未改动**。`center_on` / `fit_to_node` / `_node_bbox` 同上轮。

### 5.17 `game/ui/map_controller.py`

**本轮未改动**。`center_on` / `fit_to_node` / `reset_view` / `zoom` 同上轮。

### 5.18 `game/ui/panels/node/`（据点面板包）

**本轮未改动**。目录结构、`panel.py` / `model.py` / `columns.py` / `sorting.py` / `grouping.py` / `group_bar.py` / `context_menu.py` 均同上轮。

### 5.19 `game/ui/side_panel.py` / `main_window.py`

**本轮未改动**。`SidePanel` 接收 `map_controller`，`MainWindow` 创建 `MapController` 并注入，均同上轮。

### 5.20 `game/config/style.py`

**本轮未改动**。`MAP_STYLE` / `LAYER_VISIBILITY` 同上轮。

### 5.21 `game/config/settings_schema.py`

**本轮未改动**。`GROUPS` / `ITEMS` 同上轮。

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
│     └─ _build_index → _build_city_index()
│  └─ MapCanvas → renderer.set_data → draw_full
│
└─ _load_default_scenario()
   ├─ ScenarioLoader.load → World
   │  ├─ _build_nodes_from_geo：shapes_point → Node
   │  ├─ _build_region_names：shapes_line.properties → state_names / county_names
   │  └─ _apply_node_overrides
   │  └─ 【未实现】_load_base_characters + 剧本覆盖
   ├─ game_state.sync_from_world(world)
   ├─ renderer.set_world(world)
   └─ map_canvas.redraw()
```

### 6.3 人物数据生成流程（离线，一次性）

```
python tools/build_characters.py
├─ 找脚本同目录 *.xlsx / *.xlsm / *.csv
├─ read_xlsx (openpyxl) 或 read_csv
├─ 第一遍：建 name → [id, ...] 索引，记录重名
├─ 第二遍：构造 characters{}，关系字段名字转 id
│  └─ 重名取编号最小者
└─ 输出 characters.json（同目录）
   └─ 手动移到 assets/characters.json
```

### 6.4 主循环交互

| 触发 | 调用链 |
|---|---|
| 鼠标移动 | `_on_motion` → 40ms 节流 → `viewport.unproject` → `data.find_location` → `status_bar.set_location` |
| 滚轮 / 拖拽 | `viewport.zoom / pan_pixels` → `renderer.zoom / pan` |
| 顶部信息栏 | 200ms 轮询 `game_state.get_display_items()` |
| 设置保存 | `_on_settings_applied` → 地图相关则 `map_canvas.redraw()` |
| 据点右键 → 定位 | `context_menu._locate` → `MapController.fit_to_node` → `MapCanvas.fit_to_node` → `_node_bbox` → `viewport.fit_to_bbox` → `draw_full` |
| 据点右键 → 展开/折叠 | `context_menu._set_all_open` → `tree.item(open=...)` 递归 |
| 据点列头点击 | `_on_heading_click` → `self._sort_key/_sort_desc` → `refresh` |
| 据点分组切换 | `GroupBar._toggle` → `on_change` → `NodePanel.refresh` |

### 6.5 模块协作关系

```
main.py
└─ ui.main_window ──┬─ config.settings_manager ─ config.style
                    │                            └ config.settings_schema
                    ├─ core.game_state
                    ├─ core.scenario ─────── core.world ─── core.faction
                    │                                    ├─ core.character ★
                    │                                    └─ core.node
                    ├─ ui.top_bar
                    ├─ ui.status_bar
                    ├─ ui.map_canvas ─── map.viewport
                    │                   map.renderer ─── map.geo_data ── core.utils
                    │                                  └ core.territory（保留备用）
                    ├─ ui.map_controller ─── ui.map_canvas
                    ├─ ui.settings_window
                    └─ ui.side_panel ──── panels.faction_panel
                                       ├─ panels.node ── map_controller
                                       ├─ panels.character_panel
                                       └─ panels.troop_panel
                       config.constants
tools.build_characters ──── assets/characters.json （离线，独立）
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
| **`DEFAULT_CHARACTERS_PATH`** | **`assets/characters.json`（待新增）** |

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
| `MapRenderer._LAYER_ORDER` | 见 §5.15 | 图层底→顶 |
| `GeoData._assign_lod` 四档 | `0 / 15 / 45 / 100` | 所有 LOD 图层共用 |
| `MAP_STYLE.city_line.dash` | `(3, 3)` | 虚线节奏 |
| `MapCanvas.fit_to_node` 的 `margin` | `0.7` | 定位时留 30% 边距 |
| `MapCanvas.fit_to_node` 的 `max_scale` | `200` | 小 boundary 放大上限 |
| hover 节流 | `40 ms` | `_process_motion` |
| 标签刷新节流 | `30 ms` | `_schedule_label_refresh` |
| settle redraw | `180 ms` | 滚轮静默后补绘 |
| 据点面板默认分组 | `["state", "county"]` | `GroupBar.initial_selected` |
| **`Character._DEFAULT_STAT`** | **`50`** | **五维缺省值（本轮）** |

---

## 8. 已知逻辑限制与待完善清单

### 8.1 未实现功能

| 入口 | 现状 |
|---|---|
| 存档 / 新游戏 / 读档 | 提示"尚未实现" |
| 内政 / 军事 / 外交 | 空实现 |
| 外交交互 | 只有 `stance` 字段 |
| 部队面板 | 只清空 |
| `type` 差异化的能力 / 玩法 | 未做（城 / 关隘 / 渡口目前只是标记） |
| 设置窗口「操作」「游戏」tab | 骨架 |
| 县界 / 县面 hover | 不做 |
| `dash` 可调 | 不支持（tuple path） |
| 郡面分级调色 | 相关字段全保留但不消费 |
| 字体可在 UI 里改 | 不支持（无 `font` 类型控件） |
| 据点面板「主官」列 | 占位，恒显示 `—` |
| 据点面板「人物」列 | 占位，恒显示 `0` |
| 据点面板右键三项 | 占位，只 `print` |
| 据点面板字体 / 字号可调 | 不支持（走 ttk 全局默认 + 组头硬编码 9 号粗体） |
| 据点面板列宽 / 分组 / 排序持久化 | 不支持，重启后恢复默认 |
| **剧本覆盖 `characters.json`** | **未实现（本轮明确记录）** |
| **`characters.json` 加载入口** | **未实现** |
| **人物面板展示新字段** | **未实现（`character_panel.py` 未动）** |
| **`Character` 的 `affinity` 参与计算** | **未实现**（字段已存） |
| **人物头像加载** | **未实现**（`portrait` 字段已存） |

### 8.2 数据层缺失

- `GameState` 只有日期 + 玩家势力 + 3 项资源
- `mountains.geojson` 未接入
- 路网无拓扑关联
- 势力间无关系矩阵
- `渡口` 类型在本数据集暂未出现
- **`characters.json` 生成后需要人工核查 `_ambiguous_names` / `_missing_refs`**
- **`Character.affinity` 与 `Faction.stance` 的关系未建立**
- **人物与据点的归属（`faction / node`）完全依赖剧本，剧本未更新**

### 8.3 逻辑与性能限制

（承接前几轮，本轮新增 104–110）

1–94. （同上轮，略）
95–103. （同上轮，略）
104. ★ **`Character` 全展开但未接入加载**：`characters.json` 存在，但 `ScenarioLoader` 不读它
105. ★ **剧本覆盖未实现**：剧本 `characters` 段仍**新建**人物而非覆盖基础数据
106. ★ **`apply_override` 用 `hasattr` 防脏数据**：剧本写错字段名会被静默忽略
107. ★ **关系字段转 id 取"编号最小者"**：重名歧义需人工核对 `_ambiguous_names`
108. ★ **`blood` 不转 id**：它是家族 / 氏族标签，不是人名
109. ★ **`start_official = 0` 表示未出仕**：不是错误数据
110. ★ **`tools/build_characters.py` 依赖 `openpyxl`**：仅生成阶段需要，游戏运行时零依赖

### 8.4 建议的下一步

1. **实现剧本覆盖加载**（§6.2 里标注的 `_load_base_characters` + 剧本增量覆盖）
2. **`constants.py` 加 `DEFAULT_CHARACTERS_PATH`**
3. **`character_panel.py` 展示新字段**（五维 / 表字 / 个性 / 关系）
4. **给 `render_*` 的 `except` 加"首次异常打印"**
5. **给 `type` 赋予玩法差异**
6. **据点点击详情面板**（`node_panel` 的右键三项接入真实窗口）
7. **外交入口（改 `stance`）**
8. **接入 `mountains.geojson`**
9. **存档系统 / 新游戏流程 / 回合流程**
10. **县界样式细化**
11. **`settings_schema` 增加 `font` 类型**
12. **主官 / 人物数两列的真实数据**（`world.characters_at(node_id)` 聚合）
13. **据点面板字体 / 字号可调**
14. **据点面板状态持久化**
15. **★ 人工核查 `characters.json` 的 `_ambiguous_names` / `_missing_refs`**
16. **★ `Character.affinity` 参与势力关系计算**

---

## 9. 变更日志

### 9.1 – 9.8（摘要）

- 9.1：剧本系统 + 外交分组 + 层序修复
- 9.2：郡面势力染色
- 9.3：县界渲染 + 几何层去色
- 9.4：hover 反查县名 + 州界渲染修复
- 9.5：县面势力染色 + 图层顺序调整
- 9.6：郡名标签独立字体（KaiTi）+ 缩小 15%
- 9.7：术语「县 = 据点」统一 + `type` 枚举收缩为 `城 / 关隘 / 渡口`
- 9.8：据点面板重构 + `MapController` + `fit_to_node` + 右键展开/折叠 + 郡治显示 + 默认州>郡分组

### 9.9 人物基础数据 + `Character` 全展开（第十轮）

#### 需求

1. 基于《314英雄集结武将数据.xlsx》（1049 行 × 49 列）**构建人物类**
2. 形成 **JSON 文件保存信息作为基础数据**
3. **独立基础数据**（`assets/characters.json`）
4. **游戏运行时剧本覆盖基础数据**
5. **`Character` 全展开**（每字段显式属性 + 中文注释）
6. **关系字段转 id**（名字 → id 引用）
7. **`军团` 改为 `势力`**
8. **基础数据里 `势力 / 所在 / 所属 / 身份` 留空**（剧本决定）

#### 改动

**新增文件：**

- `tools/build_characters.py` —— xlsx/csv → characters.json 转换脚本
- `assets/characters.json` —— 1049 位人物基础数据（脚本生成，手动移入 assets/）

**重写文件：**

- `game/core/character.py` —— 全展开，44 列字段全覆盖，每字段带中文注释

**未改动文件（兼容）：**

- `game/core/scenario.py` 的 `_build_character` —— keyword 调用方式与新版 `Character` 兼容
- `game/core/world.py` / `node.py` / `territory.py` 等

#### 设计决策

- **静态 + 动态双层数据**：
  - `assets/characters.json` = 静态（五维 / 关系 / 生卒 / 个性 / 阵型 / 战法…）
  - `scenarios/*.json` = 动态（`faction / node / location_name / affiliation / role`）
- **关系字段一律用 id 引用**：避免重名歧义
- **重名取编号最小者**：`李丰` → `0917`（不写特殊规则，让用户接受默认；剧本可显式指定 id）
- **`blood` 不转 id**：它是家族标签，不是人名
- **`_ambiguous_names` / `_missing_refs`**：JSON 顶层带排查字段，游戏加载时忽略
- **`apply_override`**：只覆盖已有属性（`hasattr` 防脏数据）
- **`sex / traits / formations / tactics`** 全部是字符串列表
- **`start_official = 0`**：表示未出仕（合法值）
- **`from_dict` / `to_dict`**：JSON 双向映射，方便存档

#### 数据映射（xlsx → JSON）

| xlsx 列 | JSON 字段 | 说明 |
|---|---|---|
| 编号 | `id` | 补零四位 |
| 姓名 / 字 | `name` / `family_name` | |
| 性别 / 头像 | `sex` / `portrait` | |
| 五维 | `leadership` … `charisma` | |
| 登场 / 出生 / 死亡 | `appear_year` … `death_year` | |
| 相性 | `affinity` | |
| 血缘 | `blood` | **不转 id** |
| 父亲 / 母亲 / 配偶 | `father` / `mother` / `spouse` | 转 id |
| 义兄弟 | `sworn_brothers` | 转 id |
| 亲爱 / 厌恶 1–8 | `liked` / `disliked` | 转 id |
| 世代 | `generation` | |
| 开始仕官 | `start_official` | |
| 个性 / 阵型 / 战法 | `traits` / `formations` / `tactics` | 空格切分 |
| **军团** | **不读** | 改名「势力」，由剧本填 |
| **所在 / 所属 / 身份** | **不读** | 由剧本填 |

#### 记录（非代码改动）

- **穿越人物（编号 1001–1049）保留**：所在 / 所属 / 身份均为「无」，`世代 = 0`
- **脏值原样存**（如「所在: 61」）：不做清洗，保证源头可信
- **数据源文件**《314英雄集结武将数据.xlsx》与脚本**同目录**运行即可

#### 待办（本轮明确记录）

- **剧本覆盖加载**：`ScenarioLoader` 加 `_load_base_characters` + `_apply_character_overrides`
- **`constants.py` 加 `DEFAULT_CHARACTERS_PATH`**
- **人工核查 `_ambiguous_names` / `_missing_refs`**（生成后看控制台输出）
- **`character_panel.py` 展示新字段**
- **`Character.affinity` 参与势力关系计算**
- **人物头像加载**（`portrait` 字段已存）

---

**本轮核心变动集中在 §0（人物约定）**、**§2（新增 tools / characters.json）**、**§3.3（Character 全展开）**、**§4.2（characters.json 结构）**、**§5.7 / 5.8（character.py + build_characters.py）**、**§6.3（数据生成流程）**、**§8.3 第 104–110 条**、**§9.9**。