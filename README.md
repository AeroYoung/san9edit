# 暗耻三国志 — 项目说明文档

## 1. 项目概述

| 项 | 内容 |
|---|---|
| 项目名称 | 暗耻三国志（`APP_TITLE`） |
| 定位 | 三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》 |
| 程序入口 | `main.py` → `MainWindow().run()` |
| 核心功能 | 中国全图矢量渲染（州/郡/县三级 + 道路路网 + 水域湖泊/河流）、鼠标缩放平移、光标反查行政区、旬回合制时钟、顶部信息栏与菜单、右侧 Tab 面板框架、多 Tab 设置窗口（外观 / 操作 / 游戏）、剧本系统（NPC/据点初始化 + 玩家势力绑定）、**势力关系分组展示（玩家 / 盟友 / 敌对 / 中立）**、**郡面势力染色（主导 / 主要势力分层着色）** |
| 运行环境 | Python 3 + 标准库 `tkinter`。仅依赖标准库，**无第三方依赖、无 requirements.txt** |
| 数据来源 | [assets/map.geojson](assets/map.geojson)：13 州 / 106 郡 / 1372 个据点（`states → counties → cities` 三层嵌套）；[assets/roads.geojson](assets/roads.geojson)：约 600 条道路线段；[assets/water.geojson](assets/water.geojson)：205 条河流/湖泊（已接入渲染）；[assets/mountains.geojson](assets/mountains.geojson)：42 个山地区块（**未接入**） |
| 剧本来源 | [scenarios/default.json](scenarios/default.json)：默认剧本，启动时自动加载。势力/人物/据点动态数据 |
| 用户数据 | [userdata/settings.json](userdata/settings.json)：设置覆盖文件，仅保存与默认值不同的项；目录不存在时自动创建 |
| 平台 | Windows 优先（`maximize()` 兼容 Win/Linux/macOS） |

**当前完成度**：

- ✅ 地图查看器（州/郡/县三级渲染 + 道路 + 水域 + 图层显隐 + 县点四级样式 + 县名避让）完整可用
- ✅ 多 Tab 设置系统（外观 tab 有内容，操作/游戏 tab 空骨架）
- ✅ 剧本系统：可加载 JSON 剧本，构造 `World`（`factions` / `characters` / `nodes`），顶部信息栏已接入玩家势力数据
- ✅ 势力面板分组列表（玩家 / 盟友 / 敌对 / 中立四组）
- ✅ **郡面势力染色**：按郡内控制力判定主导 / 主要势力，分别用原色 / 变浅色给郡面上色
- ⚠️ 回合与资源为骨架（`GameState` 只做推进 + 从 World 读数据）
- ❌ 内政/军事/外交（仅 `stance` 数据字段，无外交交互）/存档均为空实现

---

## 2. 文件结构清单

```
san9edit/
├── main.py                         启动入口，创建并运行 MainWindow
├── README.md                       本文档
├── assets/
│   ├── map.geojson                 主地图：州面 + 郡界 + 据点 + 三级标签坐标
│   ├── roads.geojson               道路路网：LineString 线段（约 600 条）
│   ├── water.geojson               河流/湖泊（205 要素），已接入渲染
│   └── mountains.geojson           山地/关隘（42 要素，无任何代码引用）
├── scenarios/                      剧本目录（与 assets/ 并列）
│   └── default.json                默认剧本，启动时自动加载
├── userdata/                       用户数据目录（运行时自动创建）
│   └── settings.json               设置覆盖文件
└── game/
    ├── __init__.py
    ├── config/
    │   ├── __init__.py
    │   ├── constants.py            路径常量（不含初始游戏状态）
    │   ├── style.py                UI 主题色 / 地图绘制样式 / 图层显隐
    │   ├── settings_manager.py     设置数据层（就地写回 style）
    │   └── settings_schema.py      设置 UI 元数据（TABS/GROUPS/ITEMS）
    ├── core/
    │   ├── __init__.py
    │   ├── game_state.py           回合/日期/玩家势力数据源（从 World 同步）
    │   ├── utils.py                几何通用工具 + 颜色工具
    │   ├── faction.py              ★ 势力（id = 君主人物 id，含 stance）
    │   ├── character.py            ★ 人物（四位 id，五维）
    │   ├── node.py                 ★ 据点（六位 id，静态 + 动态字段）
    │   ├── world.py                ★ 游戏世界容器（聚合三张表）
    │   ├── scenario.py             ★ 剧本加载器（JSON + GeoData → World）
    │   └── territory.py            ★ 势力控制范围（郡级统计）
    ├── map/
    │   ├── __init__.py
    │   ├── geo_data.py             GeoJSON 解析、图层分类、空间索引
    │   ├── viewport.py             视图状态：中心、缩放、投影/反投影
    │   └── renderer.py             地图绘制（几何层 + 文字层 + 图层显隐 + 层序重排）
    └── ui/
        ├── __init__.py
        ├── main_window.py          主窗口：组装 + 跨模块事件
        ├── top_bar.py              顶部栏：信息项 + 菜单 + 进行按钮
        ├── status_bar.py           底部状态栏：提示 / 缩放 / 位置
        ├── map_canvas.py           地图画布：viewport + renderer + 交互
        ├── side_panel.py           右侧 Notebook 容器
        ├── settings_window.py      设置窗口本体
        ├── window_utils.py         窗口最大化、相对父窗居中
        ├── widgets/
        │   ├── __init__.py
        │   └── collapsible.py      折叠分组控件
        └── panels/
            ├── __init__.py
            ├── faction_panel.py    ★ 势力分组列表 Treeview（玩家/盟友/敌对/中立）
            ├── node_panel.py       ★ 据点列表 Treeview
            ├── character_panel.py  ★ 人物列表 Treeview
            └── troop_panel.py      部队列表 Treeview（空数据）
```

> 标 ★ 的为剧本系统 + 势力染色系统新增。
> `general_panel.py` / `city_panel.py` 已被 `character_panel.py` / `node_panel.py` 取代，可删。
> `.claude/`、`__pycache__` 为工具/环境产物，不属于项目源码。
> `userdata/` 属于运行期产物：删掉即可"恢复出厂设置"。

**依赖方向单向**：`main → ui → core/map → config`。

---

## 3. 核心数据模型

### 3.1 三层 ID 编码

| 层级 | 位数 | 示例 | 说明 |
|---|---|---|---|
| 州 | 2 | `01` | 州 id |
| 郡 | 4 | `0101` | 州 2 位 + 郡 2 位 |
| 据点 | 6 | `010101` | 州 2 位 + 郡 2 位 + 县 2 位 |

**从据点 id 可直接推州 id、郡 id**（`id[:2]` / `id[:4]`），无需额外索引。`Node.state_id` / `Node.county_id` 属性已实现。

### 3.2 势力（Faction）

**约定**：**势力 id = 君主的人物 id**。势力不再有独立编号。`"0001"` 既是曹操的人物 id，也是曹操势力的 id。

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | str | 四位字符串，= 君主人物 id |
| `name` | str | 势力名（一般 = 君主姓名） |
| `color` | str | 势力色（十六进制） |
| `prestige` | int | 威望 |
| `gold` | int | 金钱 |
| `food` | int | 军粮 |
| `stance` | int | **相对玩家的关系值**，范围 -100 ～ 100。默认 0 |

**属性**：`ruler_id` 返回 `self.id`。

**方法**：`stance_label()` → `"敌对"` / `"盟友"` / `"中立"`。

**stance 语义**（UI 分组用，非势力间关系矩阵）：

```
stance <  0   → 敌对
stance >  80  → 盟友
其余（0~80）  → 中立
```

玩家自身没有 stance 语义（面板里永远归入"玩家势力"组第一组）。

> **为什么不做势力间关系矩阵**：原型阶段只从玩家视角分组，独立矩阵（A 与 B、A 与 C……）复杂度高、无人消费。后续若要做外交系统再叠加。

### 3.3 人物（Character）

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | str | **全局四位**字符串 `"0001"`–`"9999"` |
| `name` | str | 姓名 |
| `faction` | str \| None | 所属势力 id；`None` = 在野 |
| `node` | str \| None | 所在据点 id；`None` = 无归属 |
| `leadership` | int | 统率（上限 100） |
| `might` | int | 武力（上限 100） |
| `intelligence` | int | 智力（上限 100） |
| `politics` | int | 政治（上限 100） |
| `charisma` | int | 魅力（上限 100） |

**方法**：`is_ruler()`（是否本势力君主）、`is_free()`（是否在野）。

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

**动态字段**（来自剧本覆盖）：

| 字段 | 类型 | 说明 |
|---|---|---|
| `owner` | str \| None | 势力 id |
| `troops` | int | 兵力 |
| `gold` | int | 金钱 |
| `food` | int | 军粮 |

**属性**：`state_id` / `county_id`（从 id 推）、`is_owned()`。

### 3.5 游戏世界（World）

剧本加载后的聚合容器，**不做加载本身**（`ScenarioLoader` 负责）。

| 属性 | 说明 |
|---|---|
| `version` / `id` / `name` / `desc` | 剧本元信息 |
| `year` / `month` / `xun` | 起始日期 |
| `player_faction_id` | 玩家势力 id（可为 `None`） |
| `factions` | `dict[str, Faction]` |
| `characters` | `dict[str, Character]` |
| `nodes` | `dict[str, Node]`，**含全部 1372 个据点** |

**查询方法**：`player_faction()` / `player_ruler()` / `nodes_of(fid)` / `characters_of(fid)` / `node(id)` / `character(id)` / `faction(id)` / `summary()`。

### 3.6 剧本加载器（ScenarioLoader）

`ScenarioLoader.load(path, geo_data)` → `World`。

**加载流程**：

```
1. 读 JSON
2. 构造 Faction / Character（剧本提供的动态数据，含 stance）
3. 遍历 geo_data.shapes_point，为每个据点建 Node（静态数据）
4. 用剧本 nodes 段的覆盖字段写到对应 Node（动态数据）
5. 返回 World
```

**关键设计**：

- `nodes` 先由 `map.geojson` **全量构造**（1372 个），再用剧本覆盖其中一部分
- 剧本只需写"要覆盖的据点"，未提及的据点用默认值（`owner=None`，`troops=0`…）
- 剧本引用不存在的据点 id **静默忽略**，不报错
- `stance` 缺省为 0（中立）；老剧本不加字段也能加载

### 3.7 郡级控制力统计（CountyStat）

**渲染层专用**，不是游戏状态的一部分，由 `compute_county_stats(world)` 按需算出。

| 字段 | 类型 | 说明 |
|---|---|---|
| `county_id` | str | 郡 id（四位） |
| `owner_id` | str \| None | 控制力最高的有主势力；无主郡为 `None` |
| `ratio` | float | `owner_id` 的势力值（含无主据点作分母） |

**派生属性**：

- `is_dominant` — `owner_id` 非空 **且** `ratio > 0.8`（主导势力）
- `is_major` — `owner_id` 非空 **且** `ratio > 0.5`（主要势力）

**控制力算法**（见 §5.20 `territory.py`）：

```
单个据点权重 = (11 - level)          # level 1→10 分，level 10→1 分
郡治据点再 × 2.0                     # CAPITAL_BONUS
势力 F 在郡内控制力 = Σ 权重(归 F 的据点)
郡内总控制力         = Σ 权重(全部据点，含无主)
势力 F 的势力值      = 控制力_F / 总控制力
```

**分档语义**：

```
ratio > 0.8         → 主导势力（dominant）
0.5 < ratio ≤ 0.8   → 主要势力（major）
其余                 → 无（郡面不上色）
```

> `is_dominant` 是 `is_major` 的子集。无主据点计入分母——否则一个 2/2 据点被占、其余 8 个无主的郡会被算成"主导势力"，误导人。

---

## 4. 数据格式参考

### 4.1 `assets/map.geojson` 实际结构

**重要**：这**不是标准 GeoJSON**（没有 `Feature` / `Geometry` 外壳），是自定义 JSON。

```json
{
  "states": [
    {
      "id": "01",
      "name": "并州",
      "name_coords": [[lon, lat], [lon, lat]],
      "boundary": [[[ [lon,lat], ... ]]],     // 州面，嵌套深
      "counties": [
        {
          "id": "0101",
          "name": "上党郡",
          "name_coords": [lon, lat],
          "capital": "长子",
          "capital_id": "010101",
          "boundary": [ [lon,lat], ... ],     // 郡界，单层
          "cities": [
            {
              "id": "010101",
              "name": "长子",
              "coords": [lon, lat],
              "is_capital": true,
              "level": 3,
              "type": "县"
            }
          ]
        }
      ]
    }
  ]
}
```

**county 层还携带 `capital`（郡治县名）+ `capital_id`（郡治县 id）**，目前未读取，但对"郡治"逻辑有用。

### 4.2 `type` 完整枚举（当前数据）

| type | 例子 | 说明 |
|---|---|---|
| `县` | 长子、江陵 | 绝大多数 |
| `关隘` | 壶口关、散关、函谷关 | 关隘 |
| `渡口/津` | 阳渠、白马津、采桑津 | 渡口 |
| `仓/监` | 敖仓、盐监、黄金采、牧苑 | 仓储 / 官方机构 |
| `谷` | 白陉谷、斜谷、蓝田谷 | 山谷 |
| `山地` | 白登、陇坻、砥柱 | 山地区块 |

**约定**：type 决定"能力"，level 决定"数值"。目前全部 type **都建成 Node 对象**，逻辑层可根据 type 区分能力（尚未实现）。

### 4.3 `scenarios/default.json` 结构（version 1）

```json
{
  "version": 1,
  "id": "default",
  "name": "默认剧本",
  "desc": "十八路诸侯 · 曹操据陈留，袁绍据魏郡",
  "start": { "year": 190, "month": 1, "xun": 1 },
  "player_faction": "0001",

  "factions": {
    "0001": {
      "name": "曹操",
      "color": "#1E40AF",
      "prestige": 1000,
      "gold": 5000,
      "food": 20000,
      "stance": 0
    },
    "0006": {
      "name": "袁绍",
      "color": "#7C3AED",
      "prestige": 1000,
      "gold": 5000,
      "food": 20000,
      "stance": -50
    }
  },

  "characters": {
    "0001": {
      "name": "曹操", "faction": "0001", "node": "130301",
      "leadership": 96, "might": 72, "intelligence": 91,
      "politics": 94, "charisma": 96
    },
    "0006": {
      "name": "袁绍", "faction": "0006", "node": "020101",
      "leadership": 88, "might": 66, "intelligence": 74,
      "politics": 72, "charisma": 92
    },
    "0007": {
      "name": "颜良", "faction": "0006", "node": "020101",
      "leadership": 82, "might": 94, "intelligence": 34,
      "politics": 38, "charisma": 70
    }
  },

  "nodes": {
    "130301": { "owner": "0001", "troops": 8000, "gold": 1000, "food": 20000 },
    "020101": { "owner": "0006", "troops": 8000, "gold": 1000, "food": 20000 }
  }
}
```

**字段说明**：

| 段 | 形态 | 说明 |
|---|---|---|
| `version` | int | 固定 `1` |
| `id` / `name` / `desc` | str | 剧本标识 |
| `start` | obj | `{year, month, xun}` |
| `player_faction` | str \| null | 玩家势力 id；`null` = 无玩家 |
| `factions` | dict | key = 四位君主 id；值含 `stance`（可选，默认 0） |
| `characters` | dict | key = 四位人物 id |
| `nodes` | dict | key = 六位据点 id，value = 要覆盖的字段 |

**覆盖语义**：`nodes` 段只写**要改的字段**，未写的字段保留默认值。例如只写 `{"owner": "0001"}`，则 `troops` / `gold` / `food` 全为默认 0。

**引用一致性约定**：

```
Faction.id  == 其君主的 Character.id
Node.owner  → Faction.id
Character.faction → Faction.id
Character.node    → Node.id
```

**默认剧本（v1）内容**：

| 势力 | id | 起始据点 | 据点数量 | 人物数 |
|---|---|---|---|---|
| 曹操（玩家） | `0001` | `130301` 陈留 | 17（兖州陈留郡） | 5（`0001`–`0005`） |
| 袁绍（NPC） | `0006` | `020101` 邺县 | 18（冀州魏郡） | 6（`0006`–`0011`） |

> 袁绍势力中，`0006` 本人为君主，`0007`–`0011` 为颜良 / 文丑 / 张郃 / 田丰 / 沮授。**id 是临时占用，后续可重排**。

---

## 5. 模块与函数清单

### 5.1 `main.py`

| 函数 | 用途 |
|---|---|
| `main()` | 实例化 `MainWindow` 并调用 `run()` |

### 5.2 `game/config/constants.py`

纯常量模块。**不再含初始游戏状态**（由剧本提供）。

| 常量 | 值 | 说明 |
|---|---|---|
| `PROJECT_ROOT` | `Path(__file__).parents[2]` | 项目根 |
| `ASSETS_DIR` | `PROJECT_ROOT/"assets"` | 资源目录 |
| `DEFAULT_MAP_PATH` | `assets/map.geojson` | 启动自动加载 |
| `DEFAULT_WATER_PATH` | `assets/water.geojson` | 随主地图加载（已启用） |
| `DEFAULT_ROADS_PATH` | `assets/roads.geojson` | 随主地图加载 |
| `SCENARIOS_DIR` | `PROJECT_ROOT/"scenarios"` | 剧本目录 |
| `DEFAULT_SCENARIO_PATH` | `scenarios/default.json` | 启动自动加载 |
| `APP_TITLE` | `"暗耻三国志"` | 窗口标题 |
| `WINDOW_SIZE` | `"1440x900"` | 保留常量，未使用 |
| `MIN_WINDOW_SIZE` | `(1024, 640)` | 窗口最小尺寸 |

> **注意**：`INITIAL_YEAR` / `INITIAL_FACTION` / `INITIAL_GOLD` 等常量**已删除**。

### 5.3 `game/core/faction.py`

**类 `Faction`**

| 方法 / 属性 | 说明 |
|---|---|
| `__init__(fid, name, color="#888888", prestige=0, gold=0, food=0, stance=0)` | 构造 |
| `ruler_id` | 属性，返回 `self.id`（约定：势力 id = 君主 id） |
| `stance_label()` | 返回 `"敌对"` / `"盟友"` / `"中立"` |

**stance 语义**：相对玩家。`<0` 敌对，`>80` 盟友，其余中立。默认 0（中立）。

### 5.4 `game/core/character.py`

**类 `Character`**

| 方法 | 说明 |
|---|---|
| `__init__(cid, name, faction=None, node=None, leadership=50, might=50, intelligence=50, politics=50, charisma=50)` | 构造 |
| `is_ruler()` | 是否本势力君主（`faction == id`） |
| `is_free()` | 是否在野（`faction is None`） |

默认五维 50。

### 5.5 `game/core/node.py`

**类 `Node`**

| 方法 / 属性 | 说明 |
|---|---|
| `__init__(nid, name, coords, type_="县", level=5, is_capital=False, owner=None, troops=0, gold=0, food=0)` | 构造 |
| `state_id` | 属性，`id[:2]` |
| `county_id` | 属性，`id[:4]` |
| `is_owned()` | 是否有所属势力 |

### 5.6 `game/core/world.py`

**类 `World`** — 见 §3.5。

### 5.7 `game/core/scenario.py`

**类 `ScenarioLoader`**（全部类方法，不实例化）

| 方法 | 用途 |
|---|---|
| `load(path, geo_data)` | 从文件加载，返回 `World` |
| `from_dict(raw, geo_data)` | 从已解析 dict 构造，返回 `World` |
| `_build_faction(fid, fdata)`（static） | 单条势力构造，**读取 `stance`（默认 0）** |
| `_build_character(cid, cdata)`（static） | 单条人物构造 |
| `_build_nodes_from_geo(world, geo_data)`（static） | 遍历 `geo_data.shapes_point` 建全部 Node |
| `_apply_node_overrides(world, overrides)`（static） | 把剧本覆盖字段写到已有 Node |

### 5.8 `game/core/game_state.py`

**类 `GameState`** — 属性 `year` / `month` / `xun` / `player_faction` / `prestige` / `gold` / `food` / `world`。

| 方法 | 用途 |
|---|---|
| `__init__()` | 字段全部置 0 / `None`（"未初始化"状态） |
| `sync_from_world(world)` | 剧本加载后注入 World，同步起始日期 |
| `date_text()` | 未初始化时返回 `"—"` |
| `advance_turn()` | 推进一旬；未初始化时直接返回 |
| `change_gold/food/prestige(delta)` | 有 World 时写回玩家势力，否则写自身 |
| `get_display_items()` | 5 项；`faction/prestige/gold/food` 从 `world.player_faction()` 读，未就绪时显示 `"—"` |

**状态机**：
```
未加载剧本 → year=0，信息栏除日期外全部 "—"
   │
   ▼ sync_from_world(world)
已加载剧本 → 信息栏显示玩家势力实时数据
```

### 5.9 `game/core/utils.py`

| 函数 | 用途 |
|---|---|
| `walk_coords(coords)` | 递归展开 GeoJSON 坐标 |
| `midpoint_of_line(coords)` | **死代码** |
| `point_in_polygon(x, y, ring)` | 射线法 |
| `lighten_color(hex_color, factor=0.4)` | **新**。`#RRGGBB` 向白色线性插值；`factor` 0→原色，1→纯白。非法输入原样返回 |

### 5.10 `game/core/territory.py`（新文件）

**数据类 `CountyStat`**：`county_id` / `owner_id` / `ratio`；派生属性 `is_dominant` / `is_major`。见 §3.7。

**模块函数 `compute_county_stats(world)`**：遍历 `world.nodes`，按郡聚合控制力，返回 `{county_id: CountyStat}`。`world` 为 `None` 时返回 `{}`。

**模块常量 `CAPITAL_BONUS = 2.0`**：郡治据点的控制力倍率。

**设计定位**：**渲染层专用**，是唯一独立于 `World` 之外的计算。将来若 `World` 也想要郡级控制度（比如弹窗显示），可以下沉成 `World` 的属性缓存。

### 5.11 `game/map/geo_data.py`

`_classify_county` 的改动（**本轮新增**）：

**① 郡界 `shapes_line` properties 加 `郡id`**：

```python
{
    "州名": sname,
    "郡名": cname,
    "郡id": county.get("id"),    # ★ 新（势力染色用）
}
```

**② `shapes_point.properties` 五个字段**（沿用上轮）：

```python
{
    "id": city.get("id"),
    "县名": name,
    "level": level,
    "type": city.get("type", "县"),
    "is_capital": bool(city.get("is_capital", False)),
}
```

**③ `labels_county` 三元组 → 四元组**：

```python
self.labels_county.append((nc[0], nc[1], cname, county.get("id")))    # ★
```

**④ `labels_city` 四元组 → 五元组**：

```python
self.labels_city.append((coords[0], coords[1], name, level, city.get("id")))    # ★
```

**兼容性**：

- `find_nearest_label` 用索引 `c[0]/c[1]/c[2]` 访问，`labels_city` 五元组不破
- `labels_county` 从三元组变四元组会破 `render_label_group` 里的 `for lon, lat, text in labels`，所以 **`render_county_labels` 已改为独立实现**（见 §5.13）
- `labels_state` **仍是三元组**，继续走通用 `render_label_group`

> 维护要点：`level` 的两行解析仍必须**写在 `shapes_point.append` 之前**（否则抛 `UnboundLocalError`，地图完全不加载）。

### 5.12 `game/map/viewport.py`

**未改动**（参照前版文档 §3.9）。

### 5.13 `game/map/renderer.py`

**本轮改动集中在"势力染色 + 分层上色"**。

#### 类常量

```python
LABEL_TAG     = "label"
WATER_TAG     = "water"
ROAD_TAG      = "road"
POLYGON_TAG   = "polygon"
LINE_TAG      = "line"
POINT_TAG     = "point"
TERRITORY_TAG = "territory"    # ★ 新：郡面势力染色

# 从底到顶的图层顺序；越靠后越在上面
_LAYER_ORDER = (
    "polygon",      # 州/郡面
    "territory",    # ★ 郡面势力染色（新，在州面之上、水域之下）
    "water",        # 水域
    "road",         # 道路
    "line",         # 郡界
    "point",        # 县点
    "label",        # 文字
)
```

#### 实例属性

`__init__` 新增：

- `self._world = None` — World 引用
- `self._county_stats = {}` — `{county_id: CountyStat}` 缓存

#### 方法

| 方法 | 说明 |
|---|---|
| `set_world(world)` | **新**。注入 World，触发 `_county_stats` 重算。**不负责重绘** |
| `_restack()` | **上轮新增**。按 `_LAYER_ORDER` 从底到顶 `tag_raise` 一遍。用 `tag_raise` 而非 `tag_lower`，免疫空图层 |
| `_draw_geometry()` | 中间插入 `if LAYER_VISIBILITY.get("territory", True): self.render_territory()` |
| `render_territory()` | **新**。遍历 `shapes_line`，从 `properties["郡id"]` 找 `CountyStat`，`is_major` 才上色。`is_dominant` 用原色，否则 `lighten_color(faction.color, MAP_STYLE.territory.major_fade)`。同色描边防亚像素缝 |
| `render_county_labels()` | **重写**。不再调 `render_label_group`；遍历 `(lon, lat, text, cid)` 四元组，调 `_county_label_color(cid, default)` 决定字色 |
| `_county_label_color(cid, default)` | **新**。`is_major` 用势力色，否则默认。**不变浅** |
| `render_city_labels()` | 循环变量加 `cid`（改读五元组）；`draw_text` 前调 `_city_label_color(cid, style["color"])` 替换字色 |
| `_city_label_color(cid, default)` | **新**。有主 → 势力色；无主 / 无 World → 默认 |

**`refresh_dynamic()` 末尾**：上轮起由三条 `tag_lower` 改为一行 `self._restack()`。

**`_LAYER_ORDER` 是自文档的**：一眼看清叠放结构，加新图层只需往表里插一行。

### 5.14 `game/ui/main_window.py`

**关键改动**：

| 位置 | 改动 |
|---|---|
| `load_geojson(path)` | 在 `self.map_canvas.reset_view()` 之前保存 `self._geo_data = data` |
| `_auto_load_default()` | 加载地图成功后接着调 `_load_default_scenario()` |
| `_load_default_scenario()` | **本轮新增两步**：`self.map_canvas.renderer.set_world(world)` + `self.map_canvas.redraw()`（触发一次全量重绘，让染色生效）。原先已有 `side_panel.refresh_all()` |
| `_on_menu_action()` | 动作 `view_cities` → `view_nodes`，`view_generals` → `view_characters` |

**启动加载链**：
```
root.after(120, _auto_load_default)
├── load_geojson(DEFAULT_MAP_PATH)
│   └── self._geo_data = data       ← 关键
└── if 加载成功:
    _load_default_scenario()
    ├── ScenarioLoader.load(DEFAULT_SCENARIO_PATH, self._geo_data)
    ├── self._world = world
    ├── self.game_state.sync_from_world(world)
    ├── self.map_canvas.renderer.set_world(world)   ← ★ 本轮：注入 World 并重算郡级统计
    ├── self.status_bar.set_message(world.summary() + " | 玩家势力：曹操")
    ├── self.side_panel.refresh_all()
    └── self.map_canvas.redraw()                    ← ★ 本轮：触发染色生效
```

### 5.15 `game/ui/top_bar.py`

菜单项改名：`城市列表` → `据点列表`（`view_nodes`），`武将列表` → `人物列表`（`view_characters`）。`TopBar` 其余逻辑不变（200ms 轮询 `game_state.get_display_items()`）。

### 5.16 `game/ui/side_panel.py`

Tab 顺序：势力(0) / 据点(1) / 人物(2) / 部队(3)。

`refresh_all()`：遍历每个 Tab，有 `refresh` 方法就调一次。被 `MainWindow._load_default_scenario()` 主动调用。

### 5.17 `game/ui/panels/faction_panel.py`

**类 `FactionPanel`** — 分组式 `Treeview`。

**分组常量**：

```python
_GROUPS = [
    ("player",  "玩家势力"),
    ("ally",    "盟友"),
    ("hostile", "敌对"),
    ("neutral", "中立"),
]
```

**列**：`势力` / `君主` / `威望` / `金` / `粮` / `关系`。

**分组规则**（`_bucket_factions`）：

```
f.id == world.player_faction_id → player  组（永远第一）
f.stance >  80                  → ally   组
f.stance <  0                   → hostile 组
其余                            → neutral 组
```

**展示**：

- 组头是顶级节点，文本形如 `盟友 (2)`，**空组也显示**
- 组头配置不同背景色 tag（`group_player` 蓝 / `group_ally` 绿 / `group_hostile` 红 / `group_neutral` 灰）
- 子节点以势力名为主列，其余列展示数值
- 组内按 **威望降序** 排（次键姓名）

**`refresh()`**：清空后从 `game_state.world.factions` 重建；`world` 为 `None` 时安全返回（`__init__` 即调一次，此时是空列表）。

### 5.18 `game/ui/panels/node_panel.py` / `character_panel.py`

沿用：8 列 / 9 列 Treeview，从 `game_state.world` 读数据。

### 5.19 其他 UI 模块

`status_bar.py` / `map_canvas.py` / `settings_window.py` / `window_utils.py` / `widgets/collapsible.py` / `panels/troop_panel.py` **未改动**。

### 5.20 `game/config/style.py`

**本轮新增**：

```python
MAP_STYLE = {
    ...
    "territory": {              # ★ 势力染色
        "major_fade": 0.4,      # 主要势力郡面的变浅比例。0=原色，1=纯白
    },
    ...
}

LAYER_VISIBILITY = {
    ...
    "territory": True,          # ★ 郡面势力染色
}
```

> **为什么 `major_fade` 放进 `MAP_STYLE` 而不是做模块级标量**：`SettingsManager` 只支持"名字.子键"或"顶层字典"两种 path 形式，不支持裸标量。放进 `MAP_STYLE` 可直接复用现成的嵌套字典读写机制；语义上也更贴切（染色样式就是地图样式的一部分）。

### 5.21 `game/config/settings_schema.py`

**本轮新增**：

**`GROUPS` 加一组**（在 `lod` 和 `visibility` 之间）：

```python
{"key": "territory", "tab": "appearance", "title": "势力染色",
 "desc": "按郡内主导势力给郡面上色。控制力 = 据点(11-level)之和，"
         "郡治 ×2；势力值 >80% 用原色，50%~80% 用变浅色。"},
```

**`ITEMS` 加两条**（在 `# --- 图层显隐 ---` 段之前）：

```python
{"path": "LAYER_VISIBILITY.territory", "group": "territory", "type": "bool",
 "label": "启用势力染色"},
{"path": "MAP_STYLE.territory.major_fade", "group": "territory", "type": "float",
 "label": "主要势力郡面变浅比例", "min": 0.0, "max": 1.0, "step": 0.05,
 "desc": "势力值 50%~80% 的郡，底色 = 势力色向白色插值。0 = 不变浅，1 = 纯白。"},
```

---

## 6. 程序完整运行流程

### 6.1 启动阶段

```
python main.py
└─ main.py: main()
   └─ MainWindow()
      ├─ tk.Tk() → title → minsize
      ├─ maximize(root)
      ├─ SettingsManager() → apply()        ← 就地写回 style
      ├─ _pick_font_family()
      ├─ GameState()                        ← 未初始化状态（year=0）
      ├─ _setup_theme()
      ├─ _build_layout()
      │  ├─ TopBar(root, game_state, ...)
      │  ├─ MapCanvas / SidePanel
      │  │  └─ SidePanel 组装 FactionPanel / NodePanel / CharacterPanel / TroopPanel
      │  ├─ StatusBar
      │  └─ 回调挂接
      ├─ _bind_shortcuts()
      └─ root.after(120, _auto_load_default)
   └─ run() → root.mainloop()
```

### 6.2 地图 + 剧本加载流程

```
_auto_load_default()
├─ load_geojson(assets/map.geojson, silent=True)
│  └─ MapCanvas.load_geojson(path)
│     ├─ GeoData.from_file(path) → 13 州 / 106 郡 / 1372 据点
│     │  └─ _classify_county：shapes_line 带 郡id / labels_county 四元组
│     ├─ load_water(...) / load_roads(...)
│     ├─ renderer.set_data(data)
│     └─ _try_fit_now() → viewport.fit_to_bbox → renderer.draw_full()
│  ★ self._geo_data = data                 ← 保存供剧本使用
│  ★ map_canvas.reset_view()
│
└─ if 地图加载成功: _load_default_scenario()
   └─ ScenarioLoader.load(scenarios/default.json, self._geo_data)
      ├─ 构造 Faction（2 个：曹操 / 袁绍；各带 stance）
      ├─ 构造 Character（11 个：曹操方 5 + 袁绍方 6）
      ├─ _build_nodes_from_geo → 遍历 shapes_point 建 1372 个 Node
      ├─ _apply_node_overrides → 覆盖曹操 17 + 袁绍 18 = 35 个据点
      └─ 返回 World
   ├─ self._world = world
   ├─ game_state.sync_from_world(world)
   ├─ renderer.set_world(world)                    ★ 本轮：注入 World + 重算 CountyStat
   ├─ status_bar.set_message(...)
   ├─ side_panel.refresh_all()                     （上轮加入）
   └─ map_canvas.redraw()                          ★ 本轮：触发染色生效
```

### 6.3 主循环交互

| 触发 | 调用链 |
|---|---|
| 滚轮（地图） | `MapCanvas.zoom` → `viewport.zoom` → `renderer.zoom` → 30 ms 刷新动态层 |
| 左键拖拽 | `viewport.pan_pixels` → `renderer.pan` |
| 鼠标移动 | 40 ms 节流 → `unproject` → `find_location` → 状态栏 |
| 顶部信息栏 | 每 200 ms `game_state.get_display_items()` → 更新 Label |
| 「进行 ▶」 | `_end_turn` → `game_state.advance_turn()` |
| 菜单"据点列表" | `view_nodes` → `notebook.select(1)` |
| 菜单"人物列表" | `view_characters` → `notebook.select(2)` |
| 菜单"部队列表" | `view_troops` → `notebook.select(3)` |
| 菜单"游戏设置" | `_open_settings` |
| 设置保存 | `_on_settings_applied` → 地图相关则 `map_canvas.redraw()` |
| 图层显隐切换 | 立即 `refresh_dynamic` → `_restack()`（空图层免疫） |
| 染色参数修改 | `MAP_STYLE.territory.major_fade` 改后 → `redraw` → `render_territory` 用新值 |

### 6.4 模块协作关系

```
main.py
└─ ui.main_window ──┬─ config.settings_manager ─ config.style
                    │                            └ config.settings_schema
                    ├─ core.game_state ──────┐
                    ├─ core.scenario ────────┼─ core.world
                    │                        │  ├─ core.faction（含 stance）
                    │                        │  ├─ core.character
                    │                        │  └─ core.node
                    ├─ ui.top_bar（读 game_state）
                    ├─ ui.status_bar
                    ├─ ui.map_canvas ─── map.viewport ─┐
                    │                   map.renderer ─┴─ map.geo_data ─ core.utils
                    │                   │                └ core.territory（郡级统计）
                    │                   └─ core.world（set_world 注入）
                    ├─ ui.settings_window ─ ui.widgets.collapsible
                    │                    └─ ui.window_utils
                    └─ ui.side_panel ────┬─ panels.faction_panel（分组列表）
                                         ├─ panels.node_panel
                                         ├─ panels.character_panel
                                         └─ panels.troop_panel
                       config.constants（被所有层引用）
```

---

## 7. 全局变量与配置项

### 7.1 `constants.py` 现有项

| 常量 | 影响 |
|---|---|
| `MIN_WINDOW_SIZE` / `APP_TITLE` | 窗口 |
| `DEFAULT_MAP_PATH` / `DEFAULT_ROADS_PATH` / `DEFAULT_WATER_PATH` | 自动加载路径 |
| `SCENARIOS_DIR` / `DEFAULT_SCENARIO_PATH` | 剧本自动加载路径 |

**已删除**：`INITIAL_YEAR` / `INITIAL_MONTH` / `INITIAL_XUN` / `INITIAL_FACTION` / `INITIAL_PRESTIGE` / `INITIAL_GOLD` / `INITIAL_FOOD`。

### 7.2 设置窗口可改（`style.py` 默认值）

| 项 | 是否需重启 |
|---|---|
| `THEME` / `FONT_SIZES` / `FONT_CANDIDATES` | **是** |
| `MAP_STYLE` 全部子项 | 否 |
| `CITY_LEVEL_MIN_SCALE` | 否 |
| `LAYER_VISIBILITY`（`mountain` 已 UI 隐藏） | 否 |
| **`MAP_STYLE.territory.major_fade`** | 否 |

### 7.3 代码内常量

| 位置 | 值 | 含义 |
|---|---|---|
| `MapCanvas._MIN_VALID_SIZE` | `10` | 布局未完成阈值 |
| `TopBar._REFRESH_INTERVAL_MS` | `200` | 信息栏轮询周期 |
| `MapRenderer._LAYER_ORDER` | 见 §5.13 | 图层底→顶顺序 |
| `MapRenderer` 各 TAG | `"label"/"water"/"road"/"point"/"polygon"/"line"/"territory"` | 图层锚点 |
| 据点 `level` 范围 | `1–10` | 越界兜底 |
| 人物 id 范围 | `0001–9999` | 四位字符串 |
| 五维上限 | `100` | 约定（代码不强制） |
| 势力 `stance` 范围 | `-100 ～ 100` | 约定（代码不强制） |
| 势力 `stance` 分档 | `<0` / `>80` / 其余 | 敌对 / 盟友 / 中立 |
| **郡控制力 `CAPITAL_BONUS`** | `2.0` | 郡治据点权重倍率（`territory.py`） |
| **郡主导阈值** | `> 0.8` | 主导势力（郡面用原色） |
| **郡主要阈值** | `> 0.5` | 主要势力（郡面用变浅色、郡名用原色） |
| `MAP_STYLE.territory.major_fade` | `0.4` | 主要势力郡面变浅比例 |
| `MAP_STYLE.label_city.point_gap` | `6` | 县名与县点间隙 |
| `MAP_STYLE.point.ring_scale` | `1.30` | 外环半径倍率 |
| `GeoData.find_nearest_label` 上限 | `0.4°` | 县名匹配 |
| `Viewport.fit_to_bbox` 边距 | `0.92` | 缩放留白 |
| 节流 | `30 ms` / `40 ms` / `180 ms` | 标签刷新 / 鼠标查询 / settle |
| `SettingsWindow` 尺寸 | `940 × min(900, 屏高-100)` | 初始大小 |

---

## 8. 已知逻辑限制与待完善清单

### 8.1 未实现功能

| 入口 | 现状 |
|---|---|
| 保存存档 / 新游戏 | 提示"尚未实现" |
| 读取存档 | 复用 `open_geojson`，未处理 `scenarios/` |
| 内政/军事/外交/命令/操作说明 | 落入 else，状态栏回显 |
| 信息项详情弹窗 | 占位文字 |
| **外交交互** | 只有 `stance` 数据字段和 UI 分组，**无改变 stance 的任何入口** |
| 部队面板 | `refresh()` 只清空 |
| **type 决定能力** | 全部 type 建成 Node 对象，但代码层未区分能力 |
| 设置窗口「操作」「游戏」tab | 骨架就位，内容为空 |
| **郡面染色 hover / 点击** | 染色层不做交互；据点 hover 也尚未实现 |

### 8.2 数据层缺失

- `GameState` 只有日期 + 玩家势力 + 3 项资源，无武将池/城市/部队/外交
- **`assets/mountains.geojson` 无任何代码引用**；`LAYER_VISIBILITY.mountain` 已 `hidden=True`
- `assets/roads.geojson` 只做视觉呈现：`difficulty` 仅影响线宽
- 路网与据点/郡界无拓扑关联
- **据点 `level` / `type` 驱动渲染但未挂游戏逻辑**
- **势力间无关系矩阵**：`stance` 单向，只表达"该势力相对玩家"
- **郡面染色是渲染层近似**：一个郡的 `CountyStat` 只有"主导势力+势力值"，不保留第二、第三势力的信息。多势力混战看据点色点

### 8.3 逻辑与性能限制

1. `render_lines`（106 条郡界）全量重绘、仅 bbox 视口裁剪
2. `<Configure>` 全量重绘；不调整缩放比例（刻意设计）
3. 绘制方法外层 `except Exception: pass`，几何出错静默
4. 标签不做视口预筛
5. 空间索引线性扫描
6. `_build_index` 只取外环，忽略孔洞
7. 县名匹配用固定 0.4° 距离
8. `midpoint_of_line` 死代码
9. Tab 索引硬编码在 `MainWindow._on_menu_action`
10. `FactionPanel` 分组列表无选中交互
11. `WINDOW_SIZE` 定义了但从未使用
12. `_cum_scale` 复位时机导致周期性全量重绘停顿
13. 无测试、无打包、无 lint 配置
14. 道路无 LOD、无空间索引
15. 动态图层重建 + `tag_lower` 额外开销
16. `CITY_LEVEL_MIN_SCALE` 硬编码定长
17. 四张 `*_by_level` 表同样问题
18. 县点与县名"同显同隐"依赖同表同判，分处两处
19. `_drawn` 置位时机是易错点
20. `refresh_dynamic` 绘制顺序决定层级（由 `_LAYER_ORDER` 显式表达）
21. `shapes_point` 的 `level` 解析必须先于 `append`
22. 静态层依赖 `draw_full`；快速缩放可能边缘州郡缺失，靠 180 ms settle 缓解
23. `_cum_scale` 触发点是"当前视图"，不是"最终视图"
24. 拖拽路径不做静态层补画
25. `SettingsManager.apply()` 必须就地修改 `style.py` 的字典
26. `SettingsManager` 必须在 `MainWindow.__init__` 早期创建并 `apply()`
27. `theme` / `font` 分组的 `restart=True` 是硬编码约定
28. `settings_schema.ITEMS` 与 `style.py` 结构必须一致
29. `level_table` 的 draft key 是 `path.LEVEL`
30. `SettingsWindow` 的保存/关闭路径必须走 `_do_destroy()`
31. `items` 中 `hidden=True` 的项要在 `_populate` 和 `_apply_filter` 两处都跳过
32. `water.geojson` 加载：`try/except Exception: pass` 静默吞异常
33. `LAYER_VISIBILITY.water` 默认 `False`
34. 县名避让偏移必须与 `_point_radius` 同源
35. 县点放大的三个字段联动（`size_divisor` / `min_radius` / `max_radius`）
36. 外环绘制顺序：先外环再主体
37. 空心 / 外环用不同的描边配置
38. `update_idletasks()` 不要在 `<Configure>` 回调链里调
39. 设置窗口的滚轮用 `bind` 递归绑到每个子控件，不要用 `bind_all`
40. `scrollregion` 用 `winfo_reqheight()` 而不是 `bbox("all")`
41. 多 Tab 结构下，`_apply_filter` / 滚轮 / `scrollregion` 都按"当前 tab"作用
42. `center_on_parent` 必须分多轮延迟设位置
43. 方法缩进事故高发
44. `tag_lower(tag)` 要求 tag 下至少有一个 item（**该坑已被 `_restack` 根治**）
45. `load_geojson` 必须在 `reset_view()` 之前保存 `self._geo_data`
46. 剧本加载依赖 `shapes_point` 的 `id` 字段
47. 势力 id = 君主 id 是硬约定
48. `GameState.__init__` 处于"未初始化"状态（year=0）
49. `change_gold/food/prestige` 有双路径
50. **`tag_lower(A, B)` 的 `belowThis` 参数 B 必须非空**：Tk 文档明示，B 空则抛 `TclError: tagOrId "xxx" doesn't match any items`。**A 空只是 no-op**
51. **`_restack()` 用 `tag_raise` 而不是 `tag_lower`**：`tag_raise(A)` 空 tag 是 no-op，从底到顶一遍最终层序一定正确，且不需要"参照物"概念。**空图层免疫**
52. **图层"内容"与图层"层序"解耦**：`LAYER_VISIBILITY` 控制要不要画，`_LAYER_ORDER` 控制画在哪。新增图层（如 `mountains`）只需三步：往 `_LAYER_ORDER` 加一行 + 加 `if LAYER_VISIBILITY` 判断 + 加对应 `render_*`
53. **`FactionPanel.__init__` 会先调一次 `refresh()`**：此时 `game_state.world` 还是 `None`。真正的数据填充发生在 `MainWindow._load_default_scenario()` 末尾的 `side_panel.refresh_all()`
54. **`FactionPanel._bucket_factions` 是纯函数**：不读 `self`，只吃 `world`。将来若把分组逻辑下沉到 `World`，直接搬过去
55. **`stance` 默认 0**：老剧本不写也能加载，一律按"中立"。玩家自身 `stance` 值无 UI 意义
56. ★ **`settings_schema.ITEMS` 每项必须含 `group`**：`items_of_group` 和 `_apply_filter` 都读 `it["group"]`，漏一个就 KeyError 到天荒地老。加新项时务必写全 `path` / `group` / `type` / `label` 四个字段
57. ★ **`SettingsManager` 只支持"名字.子键"或"顶层字典"两种 path 形式**：不支持裸标量。想加可编辑的标量（如"变浅比例"），必须塞进已有的嵌套字典（如 `MAP_STYLE.territory.major_fade`），不要建 `TERRITORY_MAJOR_FADE = 0.4` 这种模块级标量
58. ★ **`labels_county` 是四元组、`labels_city` 是五元组**：末位都是 id。`render_county_labels` 和 `render_city_labels` 是独立实现，**不再走通用的 `render_label_group`**。`labels_state` 仍是三元组，继续走通用逻辑
59. ★ **`render_territory` 的 `outline=color` 是刻意的**：Tk 相邻多边形之间常留一像素缝，用同色描边盖掉；郡界描边由 `line` 层单独负责，视觉上仍有深色界线
60. ★ **`set_world` 不负责重绘**：只注入 World 并重算 `_county_stats`，触发重绘是调用方（`MainWindow`）的事。这样的分工避免渲染层反向依赖 UI 生命周期
61. ★ **`CountyStat` 是渲染层缓存，不进 `World`**：游戏逻辑若将来也要用（弹窗显示"某郡控制度"），可以下沉成 `World` 的懒加载属性；现在独立在 `territory.py` 里，职责清晰
62. ★ **无主据点计入控制力分母**：若不算分母，一个郡 2/2 据点被占、其余 8 个无主，会被算成 100% 主导势力——上色误导。算入分母后，这种郡会正确显示为"<50% 不上色"
63. ★ **`style.py` 里 `LAYER_VISIBILITY` 段的注释和缩进不齐**：不影响运行，但风格上待整理

### 8.4 建议的下一步

1. **回合流程**：`_end_turn` 里推进 World 的日期 + 刷新面板；`side_panel.refresh_all()` 已就位
2. **据点交互**：点击地图上的据点 → 弹出据点详情（兵力/金钱/军粮/所属势力/驻守人物）
3. **人物面板联动**：点击人物 → 弹出人物详情（五维 + 所属 + 所在据点）
4. **势力面板交互**：点击势力 → 弹势力详情 / 或地图上高亮其领地
5. **外交入口**：让 `stance` 可被用户修改（菜单项、或势力面板右键菜单），并做边界（-100～100）
6. **接入 `mountains.geojson`**：`GeoData.load_mountains` + `MapRenderer.render_mountains` + 往 `_LAYER_ORDER` 插一行，把 `LAYER_VISIBILITY["mountain"]` 挂上，删掉 schema 里 `hidden=True`
7. **type 能力矩阵**：定义每种 type 的"能否驻兵 / 能否征粮 / 能否被占领 / 是否交通节点"
8. **存档系统**：序列化 World + GameState，写 `userdata/saves/`
9. **新游戏流程**：菜单"新游戏"→ 弹窗选剧本 → 加载
10. **势力染色细化**：hover 郡面显示"控制度"浮窗；或加势力图例
11. 给绘制方法的 `except Exception` 加"首次异常打印一次日志"
12. 设置系统扩展（同前版文档）

---

## 9. 变更日志

### 9.1 前两轮（摘要）

**剧本系统**：新增 `scenarios/` / `Faction` / `Character` / `Node` / `World` / `ScenarioLoader` / `NodePanel` / `CharacterPanel`。删除 `INITIAL_*` 常量，加 `SCENARIOS_DIR` / `DEFAULT_SCENARIO_PATH`。术语：武将→人物 / 城市→据点 / 势力 id = 君主人物 id。

**外交分组 + 层序修复**：`Faction.stance` 字段 + `stance_label()`；`MapRenderer._LAYER_ORDER` + `_restack()`；`FactionPanel` 整文件重写为分组 Treeview；`default.json` 加袁绍势力（冀州魏郡 18 据点）+ 6 人物。

### 9.2 本轮 · 势力染色

#### 新增

- **`game/core/territory.py`**：`CountyStat` 数据类 + `compute_county_stats(world)` 函数 + `CAPITAL_BONUS = 2.0`
- **`game/core/utils.lighten_color(hex_color, factor=0.4)`**：向白色线性插值
- **`game/map/geo_data.py`**：
  - `shapes_line` 的 properties 加 `郡id`
  - `labels_county` 三元组 → **四元组**（末尾补郡 id）
  - `labels_city` 四元组 → **五元组**（末尾补据点 id）
- **`game/map/renderer.py`**：
  - `TERRITORY_TAG` 类常量
  - `_LAYER_ORDER` 加 `territory`（在 `polygon` 之上、`water` 之下）
  - `set_world(world)` 方法
  - `render_territory()` 方法
  - `_county_label_color(cid, default)` / `_city_label_color(cid, default)` 方法
- **`game/config/style.py`**：
  - `MAP_STYLE.territory.major_fade = 0.4`
  - `LAYER_VISIBILITY.territory = True`
- **`game/config/settings_schema.py`**：
  - `GROUPS` 加 `territory` 分组
  - `ITEMS` 加两条（开关 + 变浅比例）

#### 修改

- **`game/map/renderer.py`**：
  - `__init__` 加 `self._world = None` / `self._county_stats = {}`
  - `_draw_geometry()` 中间插入 `render_territory()` 调用
  - `render_county_labels()` **重写**：不再走通用 `render_label_group`，按郡 id 查控制度上色
  - `render_city_labels()`：循环变量加 `cid`（改读五元组），`draw_text` 前替换字色
  - import 去掉 `TERRITORY_MAJOR_FADE`，改从 `MAP_STYLE.territory.major_fade` 读
- **`game/ui/main_window.py`**：
  - `_load_default_scenario()` 里 `sync_from_world` 之后加 `renderer.set_world(world)`
  - 末尾加 `map_canvas.redraw()`

#### 修复

- **`settings_schema.ITEMS` 缺少 `group` 字段导致 KeyError**（详见 §8.3 第 56 条）
  - 症状：打开游戏设置窗口立刻抛 `KeyError: 'group'`
  - 原因：加 `territory` 项时只写了 `path` / `label`，漏了 `group` 和 `type`
  - 修复：写全四字段，`path` 大小写也改正（`territory` 小写）

#### 设计决策（本轮定稿）

- **"变浅"用向白插值，不用 stipple、不用斜线**：Tk 的 polygon 只能有一个 stipple，透明填色画不了纹样，斜纹要手绘成本高、和点阵叠加视觉会脏
- **`major_fade` 放进 `MAP_STYLE` 而不做模块级标量**：`SettingsManager` 只支持嵌套 path，加模块级标量要在 `settings_manager` 里加 setattr 分支，逻辑更杂
- **郡面染色是"背景层"近似，不是"事实层"**：只有"主导势力 + 势力值"，不表达"第二势力是谁"。多势力混战看据点色点
- **控制力权重 = `(11 - level)`，郡治 ×2，无主据点计入分母**：见 §3.7

#### 数据约定（本轮新增）

- 郡级控制力分档：
  - `ratio > 0.8` → 主导势力（郡面用原色）
  - `0.5 < ratio ≤ 0.8` → 主要势力（郡面用变浅色，郡名用原色）
  - `≤ 0.5` → 无（郡面不上色，郡名用默认色）
- 郡名用色只区分"是否主要势力"（>50% 用势力色，不变浅）
- 据点文本用色：有主 → 势力色；无主 → 默认
- 据点**点位**颜色：始终黑色（用户明确要求）
- 势力染色独立图层开关：`LAYER_VISIBILITY.territory`

---

**本轮核心变动集中在 §3.7（CountyStat）**、**§5.10（territory.py）/ 5.11（geo_data.py 元组结构）/ 5.13（renderer.py）/ 5.20（style.py）/ 5.21（settings_schema.py）**、**§6.2（set_world + redraw）**、**§8.3 第 56–63 条**、**§9.2**。