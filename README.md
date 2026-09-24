# 暗耻三国志 — 项目说明文档

> 本轮更新重点：**三层人物加载**（基础数据 + 剧本覆盖 + 按年份筛选）、**190 年默认剧本**（30 势力 / 刘关张在平原 / 曹操在陈留）、**人物面板重构**（仿据点面板：分组 + 排序 + 右键 + 定位）、**`tools/build_scenario_190.py`**、**`character/` 新包**。新增 §9.10 变更日志。

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
| **剧本覆盖** | `scenarios/*.json` 的 `characters` 段 | 只覆盖 `势力 / 据点 / 身份`（其余字段留空不写，减少冗余） |
| **三层人物加载** | `_load_base_characters` + `_apply_character_overrides` + `_filter_by_year` | ★ 本轮新增 |
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

**「人物」的核心约定：**

1. **三层数据**：
   - `assets/characters.json`：全量静态数据（五维 / 生卒年 / 相性 / 关系 / 个性 / 阵型 / 战法）
   - `scenarios/*.json`：剧本覆盖（`faction / node / role`，其余不写 = 用基础数据的 null）
   - **按年份筛选**（运行时）：`_filter_by_year` 只保留该年满 16 岁 + 已出生 + 未死的人
2. **关系字段用 id 引用**，不用名字（避免重名歧义）。
3. **`faction / node / location_name / affiliation / role` 在基础数据里恒为 `null`**，由剧本填充。
4. **剧本里出现但基础数据没有的人 id → 警告并忽略**（不新建）。
5. **剧本里没覆盖到的人 → 保持 null → 在野**。

---

## 1. 项目概述

| 项 | 内容 |
|---|---|
| 项目名称 | 暗耻三国志（`APP_TITLE`） |
| 定位 | 三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》 |
| 程序入口 | `main.py` → `MainWindow().run()` |
| 核心功能 | 中国全图矢量渲染、鼠标缩放平移、**光标精确反查州/郡/县**、旬回合制时钟、顶部信息栏与菜单、右侧 Tab 面板框架、多 Tab 设置窗口、剧本系统、势力关系分组展示、**县面势力染色（唯一着色图层）**、**据点面板（多列 + 排序 + 分组 + 右键菜单 + 定位）**、**人物面板（多列 + 排序 + 分组 + 右键 + 定位到据点）**、**人物基础数据（1049 人）+ 190 剧本（30 势力 / 三国开局）** |
| 运行环境 | Python 3 + 标准库 `tkinter`。仅依赖标准库，**无第三方依赖、无 requirements.txt**（生成 `characters.json` 时临时用 `openpyxl`） |
| 数据来源 | `assets/map.geojson`：13 州 / 106 郡 / 1372 县（= 1372 据点）；`assets/roads.geojson`：约 600 条道路；`assets/water.geojson`：205 条河流/湖泊；`assets/mountains.geojson`：42 个山地区块（未接入）；`assets/characters.json`：1049 位人物基础数据 |
| 剧本来源 | `scenarios/default.json`（★ 本轮换成 **190 年 · 十八路诸侯**） |
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
- ✅ ★ **三层人物加载**：基础数据 + 剧本覆盖 + 按年份筛选
- ✅ ★ **190 年默认剧本**：30 势力（曹操陈留 / 袁绍南皮 / 刘备平原…）、~500 人物、30 据点
- ✅ ★ **人物面板重构**：仿据点面板（默认按势力分组 + 8 列 + 排序 + 右键 + 定位到据点）
- ✅ ★ **`tools/build_scenario_190.py`**：一键生成 190 年剧本
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
│   └── build_scenario_190.py         ★ 新增：生成 190 年默认剧本
├── assets/
│   ├── map.geojson                   city 带 boundary，type ∈ {城, 关隘, 渡口}
│   ├── characters.json               1049 位人物基础数据
│   ├── roads.geojson
│   ├── water.geojson
│   └── mountains.geojson             未接入
├── scenarios/
│   └── default.json                  ★ 换成 190 年剧本
├── userdata/
│   └── settings.json
└── game/
    ├── config/
    │   ├── constants.py              ★ 加 DEFAULT_CHARACTERS_PATH
    │   ├── style.py
    │   ├── settings_manager.py
    │   └── settings_schema.py
    ├── core/
    │   ├── game_state.py
    │   ├── utils.py
    │   ├── faction.py
    │   ├── character.py              44 字段
    │   ├── node.py                   Node = 县 = 据点
    │   ├── world.py                  state_names / county_names
    │   ├── scenario.py               ★ 三层人物加载
    │   └── territory.py              郡级统计保留，渲染层不再消费
    ├── map/
    │   ├── geo_data.py
    │   ├── viewport.py
    │   └── renderer.py
    └── ui/
        ├── main_window.py            创建 MapController 并注入
        ├── top_bar.py
        ├── status_bar.py
        ├── map_canvas.py
        ├── map_controller.py         地图中介
        ├── side_panel.py             ★ CharacterPanel 注入 map_controller
        ├── settings_window.py
        ├── window_utils.py
        ├── widgets/collapsible.py
        └── panels/
            ├── faction_panel.py
            ├── character_panel.py    ★ 瘦身转发
            ├── troop_panel.py
            ├── character/            ★ 新增包：人物面板
            │   ├── __init__.py
            │   ├── panel.py
            │   ├── model.py          CharacterRow
            │   ├── columns.py        列定义
            │   ├── sorting.py
            │   ├── grouping.py
            │   ├── group_bar.py
            │   └── context_menu.py
            └── node/                 据点面板包
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

### 3.5 游戏世界（World）

聚合容器：`factions` / `characters` / `nodes` / `state_names` / `county_names`。

```python
self.state_names = {}     # "01"   -> "并州"
self.county_names = {}    # "0101" -> "上党郡"
```

**查询**：

```python
def state_name(self, sid):  return self.state_names.get(sid, sid or "—")
def county_name(self, cid): return self.county_names.get(cid, cid or "—")
def faction(self, fid):     return self.factions.get(fid) if fid else None   # ★ 人物面板用
def node(self, nid):        return self.nodes.get(nid) if nid else None        # ★ 人物面板用
```

### 3.6 剧本加载器（ScenarioLoader）★ 本轮重写

`ScenarioLoader.load(path, geo_data)` → `World`。

**三层人物加载（顺序不可颠倒）：**

```
1. _load_base_characters(world)
     读 assets/characters.json 的 characters{}
     全部从 from_dict 构造成 Character 放进 world.characters
2. _apply_character_overrides(world, raw["characters"])
     遍历剧本 characters 段，每个 cid 找 world.characters[cid]
     找到 → ch.apply_override({faction, node, role, ...})
     找不到 → 打印警告并忽略（不新建）
3. _filter_by_year(world, world.year)
     只保留：year - birth_year >= 16 且未死
             （birth_year 缺失时用 appear_year 兜底）
```

**其他方法（未变）：**

- `_build_nodes_from_geo`：遍历 `geo_data.shapes_point` → 每个元素一个 Node
- `_build_region_names`：遍历 `geo_data.shapes_line` 填州/郡名字表
- `_apply_node_overrides`：用剧本 `nodes` 段覆盖 `owner / troops / gold / food`
- `_build_faction`：构造 `Faction`

> **关键决策**：剧本 `characters` 段**只写动态字段**（faction / node / role），静态字段（五维 / 关系 / 生卒…）一律不写 → 减少冗余、避免与基础数据打架。

### 3.7 郡级控制力统计（CountyStat）

**当前不再被渲染层消费**，`CountyStat` / `compute_county_stats` / `CAPITAL_BONUS` 全部保留，供将来复用。

### 3.8 县界（CityBoundary）

**渲染层 + 查询层 + 染色层 + 定位层共用**，由 `GeoData.shapes_city_boundary` 承载。

### 3.9 县界空间索引（CityIndex）

`GeoData._city_index`，结构 `(bbox, 名称, 外环顶点)`。

---

## 4. 数据格式参考

### 4.1 `assets/map.geojson` 实际结构

（略，与上一轮相同）

### 4.2 `assets/characters.json` 结构

（略，与上一轮相同）

### 4.3 `type` 枚举

只有三种：`城` / `关隘` / `渡口`。

### 4.4 `scenarios/default.json` 结构（★ 本轮换 190 年剧本）

**三段 + 头部**：

```json
{
  "version": 1,
  "id": "default",
  "name": "十八路诸侯 · 190",
  "desc": "190年正月，关东诸侯起兵讨董；曹操据陈留，刘关张在平原",
  "start": { "year": 190, "month": 1, "xun": 1 },
  "player_faction": "0521",

  "factions": {
    "0521": { "name": "曹操", "color": "#2928EF",
              "prestige": 1000, "gold": 5000, "food": 20000,
              "stance": 0 },
    "0035": { "name": "袁绍", "color": "#C8B400", ... "stance": 30 },
    ...共 30 家...
  },

  "characters": {
    "0521": { "faction": "0521", "node": "130301", "role": "君主" },
    "0124": { "faction": "0521", "node": "130301", "role": "一般" },
    "0147": { "faction": "0952", "node": "060101", "role": "一般" },
    ...约 500 条，只写 3 个字段...
  },

  "nodes": {
    "130301": { "owner": "0521", "troops": 8000, "gold": 1000, "food": 20000 },
    "020801": { "owner": "0035", "troops": 8000, "gold": 1000, "food": 20000 },
    ...共 30 条（30 势力首都）...
  }
}
```

**关键约定：**

| 段 | 写什么 | 不写什么 |
|---|---|---|
| `factions` | `name / color / prestige / gold / food / stance` | — |
| `characters` | **只有** `faction / node / role` | 五维、关系、生卒、个性……**全部不写**（用基础数据） |
| `nodes` | 只有 30 家首都（小兵/钱粮） | 不写全图（其余据点在加载后 `owner=None`） |

### 4.5 `scenarios/default.json` 势力清单（190 年）

| # | 势力 | 主据点 | 主据点 id | stance | 类型 |
|---|---|---|---|---|---|
| 1 | 董卓 | 雒阳 | 070701 | -80 | 司州·河南尹 |
| 2 | 袁绍 | 南皮 | 020801 | +30 | 冀州·渤海 |
| 3 | 袁术 | 宛县 | 040701 | -50 | 荆州·南阳 |
| 4 | 韩馥 | 邺县 | 020101 | -10 | 冀州·魏郡 |
| 5 | 孔伷 | 阳翟 | 130101 | -10 | 豫州·颍川 |
| 6 | 刘岱 | 昌邑 | 090401 | -10 | 兖州·山阳 |
| 7 | 王匡 | 怀县 | 070601 | -10 | 司州·河内 |
| 8 | 桥瑁 | 濮阳 | 090201 | -10 | 兖州·东郡 |
| 9 | 袁遗 | 方与 | 090407 | 0 | 兖州·山阳 |
| 10 | 鲍信 | 卢县 | 090701 | 0 | 兖州·济北 |
| 11 | 张邈 | 己吾 | 130312 | 0 | 兖州·陈留 |
| 12 | **曹操** ★ | **陈留** | **130301** | **0（玩家）** | 兖州·陈留 |
| 13 | 张超 | 广陵 | 080501 | -10 | 徐州·广陵 |
| 14 | 陶谦 | 郯县 | 080401 | -50 | 徐州·东海 |
| 15 | 刘表 | 襄阳 | 040512 | 0 | 荆州·南郡 |
| 16 | 孙坚 | 临湘 | 040401 | 0 | 荆州·长沙 |
| 17 | 刘焉 | 成都 | 110501 | 0 | 益州·蜀郡 |
| 18 | 刘虞 | 蓟县 | 120401 | 0 | 幽州·广阳 |
| 19 | 公孙瓒 | 土垠 | 120601 | -50 | 幽州·右北平 |
| 20 | 公孙度 | 襄平 | 120901 | +30 | 幽州·辽东 |
| 21 | 刘繇 | 寿春 | 100604 | -50 | 扬州·九江 |
| 22 | 马腾 | 冀县 | 050201 | -50 | 凉州·汉阳 |
| 23 | 韩遂 | 金城 | 050415 | -50 | 凉州·金城 |
| 24 | 士燮 | 龙编 | 030601 | 0 | 交州·交趾 |
| 25 | 张鲁 | 南郑 | 110104 | 0 | 益州·汉中 |
| 26 | 王朗 | 山阴 | 100201 | 0 | 扬州·会稽 |
| 27 | 华歆 | 南昌 | 100101 | 0 | 扬州·豫章 |
| 28 | 严白虎 | 吴县 | 100501 | -10 | 扬州·吴郡 |
| 29 | **刘备** ★ | **平原** | **060101** | 0 | 青州·平原 |
| 30 | 孔融 | 剧县 | 060501 | +30 | 青州·北海 |

**关系 stance 图例**：

| stance | 含义 | 势力 |
|---|---|---|
| -80 | 死敌 | 董卓 |
| -50 | 敌对 | 袁术、公孙瓒、陶谦、刘繇、马腾、韩遂 |
| -10 | 微敌 | 韩馥、孔伷、刘岱、王匡、桥瑁、张超、严白虎 |
| 0 | 中立 | 袁遗、鲍信、张邈、刘表、孙坚、刘焉、刘虞、公孙度、士燮、张鲁、王朗、华歆、刘备 |
| +30 | 友好 | 袁绍、孔融、公孙度 |

### 4.6 核心人物清单（`CORE`，写在 `build_scenario_190.py` 里）

每个势力手写 1~14 名种子人物。**自动扩展逻辑**会补：

1. **义兄弟**：核心人物的 `sworn_brothers` 里满 16 岁的一并拉入
2. **家族**：核心人物的 `blood` 标签相同的所有满 16 岁人物一并拉入

**重点锁定**：

- **刘关张**：`0952`（刘备）核心 → `0147`（关羽）和 `0656`（张飞）都在刘备的 `sworn_brothers` 里 → 自动归入刘备，同据点在 **平原**
- **曹操班底**：夏侯惇 `0124` → 夏侯渊 `0114`（同 blood）→ 夏侯尚/夏侯霸（同 blood）自动补齐
- **曹仁 `0518`、曹洪 `0511`、曹纯 `0514`** 都在 `0521` 的 CORE 里

---

## 5. 模块与函数清单

### 5.1 `main.py`
`main()` → `MainWindow().run()`。

### 5.2 `game/config/constants.py` ★ 加一项

```python
DEFAULT_CHARACTERS_PATH = ASSETS_DIR / "characters.json"
```

其他常量不变。

### 5.3 – 5.6
`faction.py` / `game_state.py` / `utils.py` 未改动。

### 5.7 `game/core/character.py`
44 字段全展开，未改动。

### 5.8 `tools/build_characters.py`
从 xlsx/csv 生成 `characters.json`，未改动。

### 5.9 ★ `tools/build_scenario_190.py`（本轮新增）

**用途**：从 `assets/characters.json` + 史实核心清单，生成 190 年 `scenarios/default.json`。

**用法**：
```bash
python tools/build_scenario_190.py
```

**逻辑**：

1. 读 `characters.json`
2. `FACTIONS` 硬编码 30 家（君主 id / 名称 / 颜色 / stance / 首都 id）
3. `CORE` 硬编码 30 家的种子人物清单
4. `expand()`：
   - `sworn_brothers` 拉入
   - 同 `blood` 家族拉入
   - 全员过滤 `eligible()`（190 年满 16 岁 + 已出生 + 未死）
5. 冲突检测：一人不能属于两个势力（后来者出局）
6. 输出 `scenarios/default.json`（只写 `faction / node / role`）

**核心人物清单**（节选）：

| 势力 | 种子人物 |
|---|---|
| 曹操 0521 | 曹操、夏侯惇、夏侯渊、曹仁、曹洪、曹纯、乐进、李典、典韦、荀彧、荀攸、程昱、戏志才、于禁 |
| 袁绍 0035 | 袁绍、颜良、文丑、张郃、高览、田丰、沮授、审配、逢纪、郭图、许攸、淳于琼、韩猛 |
| **刘备 0952** | **刘备、关羽、张飞、简雍** |
| 孙坚 0551 | 孙坚、孙策、韩当、黄盖、程普、祖茂、孙静、孙贲 |
| 董卓 0736 | 董卓、李儒、吕布、华雄、李傕、郭汜、樊稠、董旻、董璜、牛辅 |
| 刘表 0953 | 刘表、蔡瑁、蒯越、蒯良、傅巽、韩嵩、刘磐 |
| 刘焉 0925 | 刘焉、刘璋、刘瑁、庞羲、刘璝、董和、张任、董扶 |
| 公孙瓒 0266 | 公孙瓒、公孙范、公孙越、公孙续、严纲、邹丹、田楷、单经 |
| 张鲁 0666 | 张鲁、张卫、杨昂、杨任、阎圃、杨松 |
| 士燮 0341 | 士燮、士壹、士廞、士徽、士匡、士祗、士武 |
| 陶谦 0724 | 陶谦、杜琼、曹豹 |
| 马腾 0771 | 马腾、马玩、杨秋、马延 |
| 韩遂 0166 | 韩遂、成公英、成宜、王方、梁兴 |

完整清单见脚本 §CORE。

### 5.10 `game/core/scenario.py` ★ 本轮重写

**三层人物加载**（见 §3.6）；其余方法不变。

### 5.11 `game/core/node.py` / `world.py`
未改动（`World` 加 `faction(id)` / `node(id)` 便捷查询，供人物面板用）。

### 5.12 `game/core/territory.py`
保留不动。

### 5.13 – 5.15 `geo_data.py` / `viewport.py` / `renderer.py`
未改动。

### 5.16 – 5.17 `map_canvas.py` / `map_controller.py`
未改动。

### 5.18 据点面板包 `game/ui/panels/node/`
未改动。

### 5.19 ★ 人物面板包 `game/ui/panels/character/`（本轮新增）

| 文件 | 作用 |
|---|---|
| `panel.py` | 主面板：分组条 + Treeview + 右键 + `refresh()` |
| `model.py` | `CharacterRow` dataclass（14 个字段，含 `display_name` 属性） |
| `columns.py` | 列定义：`势力 / 所在 / 身份 / 统 / 武 / 智 / 政 / 魅`（8 列） |
| `sorting.py` | 与 node 包同款 |
| `grouping.py` | 4 个分组维度：`faction / node / role / sex` |
| `group_bar.py` | 与 node 包同款 |
| `context_menu.py` | 4 项菜单：人物情报 / 复制编号 / 定位到据点 / 全部展开折叠 |

**对外接口**：`CharacterPanel(master, game_state, map_controller=None)` + `refresh()`。

**面板行为**：

- `#0` 列显示 `姓名（字）`（`display_name`）
- 默认按「势力」分组
- 点击列头排序（`_on_heading_click`）
- 右键 → `定位到据点` → `MapController.fit_to_node(node_id, fallback_lonlat)`
- 组头背景 `#F3F4F6`、9 号粗体

### 5.20 `game/ui/panels/character_panel.py` ★ 瘦身

```python
from .character.panel import CharacterPanel
__all__ = ["CharacterPanel"]
```

### 5.21 `game/ui/side_panel.py` ★ 改一行

```python
self.notebook.add(
    CharacterPanel(self.notebook, self.game_state, self.map_controller),
    text=" 人物 ",
)
```

### 5.22 `game/config/style.py` / `settings_schema.py`
未改动。

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

### 6.2 地图 + 剧本加载流程 ★ 本轮更新

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
   │  ├─ _build_faction × 30
   │  ├─ _load_base_characters           ★ 读 characters.json，1049 人全进
   │  ├─ _apply_character_overrides      ★ 剧本覆盖 ~500 人
   │  ├─ _filter_by_year(world, 190)     ★ 只留 190 年满 16 岁的
   │  ├─ _build_nodes_from_geo           shapes_point → Node
   │  ├─ _build_region_names             shapes_line → state/county names
   │  └─ _apply_node_overrides           30 家首都覆盖 owner
   ├─ game_state.sync_from_world(world)
   ├─ renderer.set_world(world)          → 地图染色（30 家首都）
   └─ map_canvas.redraw()
   └─ side_panel.refresh_all()           → 人物面板刷新
```

### 6.3 剧本生成流程（离线，一次性）

```
python tools/build_characters.py         # 已存在
   → assets/characters.json

python tools/build_scenario_190.py      # ★ 本轮新增
   ├─ 读 characters.json
   ├─ 30 势力 CORE 种子
   ├─ expand()：sworn_brothers + blood 家族
   ├─ eligible()：190 年满 16 岁
   ├─ 冲突检测（一人一势力）
   └─ 输出 scenarios/default.json
```

### 6.4 主循环交互

（与上轮相同，加两条）

| 触发 | 调用链 |
|---|---|
| 人物列头点击 | `CharacterPanel._on_heading_click` → `refresh` |
| 人物右键 → 定位到据点 | `context_menu._locate` → `MapController.fit_to_node` → `MapCanvas.fit_to_node` → `_node_bbox` → `viewport.fit_to_bbox` → `draw_full` |

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
                    ├─ ui.map_controller
                    ├─ ui.settings_window
                    └─ ui.side_panel ──── panels.faction_panel
                                       ├─ panels.node ── map_controller
                                       ├─ panels.character ── map_controller ★
                                       └─ panels.troop_panel
                       config.constants
tools.build_characters ──── assets/characters.json （离线）
tools.build_scenario_190 ── assets/characters.json + scenarios/default.json （离线）★
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
| **`DEFAULT_CHARACTERS_PATH`** | **`assets/characters.json`（本轮新增）** |

### 7.2 设置窗口可改

（不变）

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
| **人物面板默认分组** | **`["faction"]`** | ★ 本轮 |
| **人物面板列数** | **`8`** | ★ 本轮（势力/所在/身份/五维） |
| **人物面板分组维度** | **`faction / node / role / sex`** | ★ 本轮 |
| **190 剧本势力数** | **`30`** | ★ 本轮 |
| **剧本人物段只写 3 字段** | **`faction / node / role`** | ★ 本轮 |
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
| 据点面板「主官」列 | 占位，恒显示 `—` |
| 据点面板「人物」列 | 占位，恒显示 `0` |
| 据点面板右键三项 | 占位，只 `print` |
| 据点面板字体 / 字号可调 | 不支持 |
| 据点面板列宽 / 分组 / 排序持久化 | 不支持 |
| **人物面板右键「人物情报」** | **占位，只 `print`（★ 本轮）** |
| **人物头像加载** | **未实现（`portrait` 字段已存）** |
| **人物面板状态持久化** | **不支持（★ 本轮）** |

### 8.2 数据层缺失

- `GameState` 只有日期 + 玩家势力 + 3 项资源
- `mountains.geojson` 未接入
- 路网无拓扑关联
- 势力间无关系矩阵
- **`characters.json` 的 `_ambiguous_names` / `_missing_refs` 未人工核查（5 组重名）**
- **`Character.affinity` 与 `Faction.stance` 的关系未建立**
- **190 剧本非首都据点 `owner=None`**（势力只染 30 个首都）

### 8.3 逻辑与性能限制

（承接前几轮）

1–110. （同上轮，略）

**111. ★ `_filter_by_year` 只按 `birth_year` 判断，`birth_year` 缺失时退到 `appear_year <= year`**：极少数人物可能因此在 190 年"提前出场"。

**112. ★ 剧本 `characters` 段不新建人物**：id 不在 `characters.json` 里 → 警告忽略。

**113. ★ `expand()` 只递归 2 层**：义兄弟 1 层 + 家族 1 层。再深的间接关系（义兄弟的义兄弟）不拉。

**114. ★ 冲突检测是"后来者出局"**：如果曹操和袁绍都想要同一个人，后遍历到的势力丢人。势力顺序由 `CORE` 字典的遍历顺序决定（Python 3.7+ 保序）。

**115. ★ 190 剧本只有 30 个首都覆写了 `owner`**：其余 1342 个据点 owner 全为 None（灰色）。

**116. ★ 人物面板按「势力」分组**：某势力 20 人全挂在首都，导致同一据点实际"人数"和显示不一致。将来 `world.characters_at(node_id)` 聚合后再处理。

**117. ★ 人物面板列头「统/武/智/政/魅」用单字**：因为面板宽度有限（340px），全称会挤。

**118. ★ `side_panel.py` 已改为 3 参数调用 `CharacterPanel`**：如果不改，人物右键的"定位到据点"会报错（`map_controller=None`）。

### 8.4 建议的下一步

1. **给 190 剧本的非首都据点分兵**（每家 2~5 个二线城市）
2. **人工核查 `_ambiguous_names`**（李丰 0917/0918/0919 等 5 组）
3. **`Character.affinity` 参与势力关系计算**
4. **人物头像加载**（`portrait` 字段已存）
5. **人物面板右键「人物情报」接入真实窗口**
6. **`world.characters_at(node_id)` 聚合**（据点面板「人物」列真实数据）
7. **存档系统 / 新游戏流程 / 回合流程**
8. **`type` 赋予玩法差异**
9. **外交入口（改 `stance`）**
10. **接入 `mountains.geojson`**

---

## 9. 变更日志

### 9.1 – 9.9（摘要）

- 9.1：剧本系统 + 外交分组 + 层序修复
- 9.2：郡面势力染色
- 9.3：县界渲染 + 几何层去色
- 9.4：hover 反查县名 + 州界渲染修复
- 9.5：县面势力染色 + 图层顺序调整
- 9.6：郡名标签独立字体（KaiTi）+ 缩小 15%
- 9.7：术语「县 = 据点」统一 + `type` 枚举收缩为 `城 / 关隘 / 渡口`
- 9.8：据点面板重构 + `MapController` + `fit_to_node` + 右键展开/折叠 + 郡治显示 + 默认州>郡分组
- 9.9：人物基础数据 + `Character` 全展开（第十轮）

### 9.10 三层人物加载 + 190 剧本 + 人物面板（第十一轮）

#### 需求

1. **剧本年份 190 年**
2. **玩家势力：曹操**
3. **至少 30 个势力**（据点、人物贴近史实），电脑与玩家的关系也贴近史实
4. **人物基础数据在 `assets/characters.json`**；年满 16 岁的安排出场，按史实分配势力或在野（尽量不要在野）
5. **游戏运行时先读剧本，不足的从基础数据读**（三层加载）
6. **左侧面板展示人物数据**，像据点面板那样
7. **剧本尽量用基础数据，减少冗余**（只写动态字段）
8. **刘关张必须在一起**（锁死在刘备势力）

#### 改动

**新增文件：**

- `tools/build_scenario_190.py` —— 30 势力 + 核心清单 → `default.json`
- `game/ui/panels/character/__init__.py`
- `game/ui/panels/character/panel.py`
- `game/ui/panels/character/model.py`
- `game/ui/panels/character/columns.py`
- `game/ui/panels/character/sorting.py`
- `game/ui/panels/character/grouping.py`
- `game/ui/panels/character/group_bar.py`
- `game/ui/panels/character/context_menu.py`

**重写文件：**

- `game/core/scenario.py` —— 三层人物加载
- `game/ui/panels/character_panel.py` —— 瘦身为转发
- `scenarios/default.json` —— 换成 190 剧本
- `game/config/constants.py` —— 加 `DEFAULT_CHARACTERS_PATH`

**改一行文件：**

- `game/ui/side_panel.py` —— `CharacterPanel(..., self.map_controller)`

**未改动文件（兼容）：**

- `game/core/character.py`（44 字段全展开，不变）
- `game/core/world.py`（加 `faction(id)` / `node(id)` 便捷方法）
- `game/core/node.py` / `territory.py`
- 据点面板包 `game/ui/panels/node/` 全部文件
- `game/ui/panels/character_panel.py` 的旧逻辑全部下线

#### 设计决策

- **三层人物加载**：基础数据（静态）+ 剧本覆盖（动态）+ 按年份筛选（运行时）
- **剧本只写动态字段**：`characters` 段只写 `faction / node / role`，不写五维 → 减冗余
- **剧本 id 校验**：剧本写的人物 id 必须在 `characters.json` 里，否则警告忽略（不新建）
- **`_filter_by_year` 只按 `birth_year` 判断**：`birth_year` 缺失时退到 `appear_year`
- **刘关张锁死**：刘备 `CORE` 里手写关羽 + 张飞 + 简雍；同时关羽和张飞的 `sworn_brothers` 会互相拉入
- **人物面板完全仿据点面板**：同样的分组条 + Treeview + 排序 + 右键 + 定位；默认分组用 `faction`
- **`map_controller` 注入**：人物面板也接收 `map_controller`，右键可以"定位到据点"

#### 30 势力划分（史实依据）

| 势力 | 史实依据 |
|---|---|
| 董卓 | 189 年入洛阳，挟天子 |
| 袁绍 | 渤海太守，反董盟主 |
| 袁术 | 后将军，据南阳 |
| 韩馥 | 冀州牧，让冀州给袁绍 |
| 孔伷 | 豫州刺史 |
| 刘岱 | 兖州刺史，治昌邑 |
| 王匡 | 河内太守 |
| 桥瑁 | 东郡太守，首倡义兵 |
| 袁遗 | 山阳太守 |
| 鲍信 | 济北相 |
| 张邈 | 陈留太守，曹操发小 |
| 曹操 | 己吾起兵，据陈留 |
| 张超 | 广陵太守，张邈之弟 |
| 陶谦 | 徐州牧 |
| 刘表 | 荆州牧，治襄阳 |
| 孙坚 | 长沙太守，反董先锋 |
| 刘焉 | 益州牧，治成都 |
| 刘虞 | 幽州牧，治蓟县 |
| 公孙瓒 | 右北平，白马义从 |
| 公孙度 | 辽东太守，割据 |
| 刘繇 | 扬州刺史，治寿春 |
| 马腾 | 西凉军阀 |
| 韩遂 | 西凉军阀 |
| 士燮 | 交趾太守 |
| 张鲁 | 汉中，五斗米道 |
| 王朗 | 会稽太守 |
| 华歆 | 豫章太守 |
| 严白虎 | 吴郡，山越豪强 |
| 刘备 | 平原令，刘关张起家 |
| 孔融 | 北海相 |

#### 关系设定（`stance`）

- 董卓 -80（死敌）
- 袁术 / 公孙瓒 / 陶谦 / 刘繇 / 马腾 / 韩遂 -50
- 韩馥 / 孔伷 / 刘岱 / 王匡 / 桥瑁 / 张超 / 严白虎 -10
- 袁绍 / 孔融 / 公孙度 +30
- 其余 0

#### 待办（本轮明确记录）

- **非首都据点分兵**：目前 30 家只有首都染成势力色
- **`_ambiguous_names` 人工核查**（5 组重名：李丰、张承、张南、马忠、韩忠）
- **人物头像加载**（`portrait` 字段已存）
- **人物面板右键「人物情报」窗口**
- **`world.characters_at(node_id)` 聚合**（据点面板「人物」列）
- **`Character.affinity` 参与势力关系计算**
- **人物面板状态持久化**

---

**本轮核心变动集中在 §0（人物约定）**、**§2（新增 character/ 包 + build_scenario_190.py）**、**§3.6（ScenarioLoader 三层加载）**、**§4.4 / 4.5 / 4.6（190 剧本结构 + 势力表 + 核心清单）**、**§5.9 / 5.10 / 5.19 / 5.20 / 5.21**、**§6.2 / 6.3（加载 + 生成流程）**、**§7.1 / 7.3（常量）**、**§8.3 第 111–118 条**、**§9.10**。**