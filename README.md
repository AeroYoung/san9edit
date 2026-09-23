# 暗耻三国志 — 项目说明文档

## 1. 项目概述

| 项 | 内容 |
|---|---|
| 项目名称 | 暗耻三国志（`APP_TITLE`） |
| 定位 | 三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》 |
| 程序入口 | `main.py` → `MainWindow().run()` |
| 核心功能 | 中国全图矢量渲染（州/郡/县三级 + 道路路网 + 水域湖泊/河流）、鼠标缩放平移、光标反查行政区、旬回合制时钟、顶部信息栏与菜单、右侧 Tab 面板框架、多 Tab 设置窗口（外观 / 操作 / 游戏）、**剧本系统（NPC/据点初始化 + 玩家势力绑定）** |
| 运行环境 | Python 3 + 标准库 `tkinter`。仅依赖标准库，**无第三方依赖、无 requirements.txt** |
| 数据来源 | [assets/map.geojson](assets/map.geojson)：13 州 / 106 郡 / 1372 个据点（`states → counties → cities` 三层嵌套）；[assets/roads.geojson](assets/roads.geojson)：约 600 条道路线段；[assets/water.geojson](assets/water.geojson)：205 条河流/湖泊（已接入渲染）；[assets/mountains.geojson](assets/mountains.geojson)：42 个山地区块（**未接入**） |
| 剧本来源 | [scenarios/default.json](scenarios/default.json)：默认剧本，启动时自动加载。势力/人物/据点动态数据 |
| 用户数据 | [userdata/settings.json](userdata/settings.json)：设置覆盖文件，仅保存与默认值不同的项；目录不存在时自动创建 |
| 平台 | Windows 优先（`maximize()` 兼容 Win/Linux/macOS） |

**当前完成度**：

- ✅ 地图查看器（州/郡/县三级渲染 + 道路 + 水域 + 图层显隐 + 县点四级样式 + 县名避让）完整可用
- ✅ 多 Tab 设置系统（外观 tab 有内容，操作/游戏 tab 空骨架）
- ✅ **剧本系统**：可加载 JSON 剧本，构造 `World`（`factions` / `characters` / `nodes`），顶部信息栏已接入玩家势力数据
- ⚠️ 回合与资源为骨架（`GameState` 只做推进 + 从 World 读数据）
- ❌ 内政/军事/外交/存档均为空实现

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
    │   ├── utils.py                几何通用工具
    │   ├── faction.py              ★ 势力（id = 君主人物 id）
    │   ├── character.py            ★ 人物（四位 id，五维）
    │   ├── node.py                 ★ 据点（六位 id，静态 + 动态字段）
    │   ├── world.py                ★ 游戏世界容器（聚合三张表）
    │   └── scenario.py             ★ 剧本加载器（JSON + GeoData → World）
    ├── map/
    │   ├── __init__.py
    │   ├── geo_data.py             GeoJSON 解析、图层分类、空间索引
    │   ├── viewport.py             视图状态：中心、缩放、投影/反投影
    │   └── renderer.py             地图绘制（几何层 + 文字层 + 图层显隐）
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
            ├── faction_panel.py    势力信息（占位）
            ├── node_panel.py       ★ 据点列表 Treeview
            ├── character_panel.py  ★ 人物列表 Treeview
            └── troop_panel.py      部队列表 Treeview（空数据）
```

> 标 ★ 的为本轮新增。
> `general_panel.py` / `city_panel.py` 已被 `character_panel.py` / `node_panel.py` 取代，可删。
> `.claude/`、`__pycache__` 为工具/环境产物，不属于项目源码。
> `userdata/` 属于运行期产物：删掉即可"恢复出厂设置"。

**依赖方向单向**：`main → ui → core/map → config`。

---

## 3. 核心数据模型（本轮新增）

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

**属性**：`ruler_id` 返回 `self.id`。

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
2. 构造 Faction / Character（剧本提供的动态数据）
3. 遍历 geo_data.shapes_point，为每个据点建 Node（静态数据）
4. 用剧本 nodes 段的覆盖字段写到对应 Node（动态数据）
5. 返回 World
```

**关键设计**：

- `nodes` 先由 `map.geojson` **全量构造**（1372 个），再用剧本覆盖其中一部分
- 剧本只需写"要覆盖的据点"，未提及的据点用默认值（`owner=None`，`troops=0`…）
- 剧本引用不存在的据点 id **静默忽略**，不报错

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
  "desc": "十八路诸侯 · 曹操据陈留",
  "start": { "year": 190, "month": 1, "xun": 1 },
  "player_faction": "0001",

  "factions": {
    "0001": {
      "name": "曹操",
      "color": "#1E40AF",
      "prestige": 1000,
      "gold": 5000,
      "food": 20000
    }
  },

  "characters": {
    "0001": {
      "name": "曹操", "faction": "0001", "node": "130301",
      "leadership": 96, "might": 72, "intelligence": 91,
      "politics": 94, "charisma": 96
    }
  },

  "nodes": {
    "130301": { "owner": "0001", "troops": 8000, "gold": 1000, "food": 20000 }
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
| `factions` | dict | key = 四位君主 id |
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

> **注意**：`INITIAL_YEAR` / `INITIAL_FACTION` / `INITIAL_GOLD` 等常量**已删除**。初始状态一律来自剧本或存档。

### 5.3 `game/core/faction.py`

**类 `Faction`**

| 方法 / 属性 | 说明 |
|---|---|
| `__init__(fid, name, color="#888888", prestige=0, gold=0, food=0)` | 构造 |
| `ruler_id` | 属性，返回 `self.id`（约定：势力 id = 君主 id） |

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
| `_build_faction(fid, fdata)`（static） | 单条势力构造 |
| `_build_character(cid, cdata)`（static） | 单条人物构造 |
| `_build_nodes_from_geo(world, geo_data)`（static） | 遍历 `geo_data.shapes_point` 建全部 Node |
| `_apply_node_overrides(world, overrides)`（static） | 把剧本覆盖字段写到已有 Node |

### 5.8 `game/core/game_state.py`（重写）

**类 `GameState`** — 属性 `year` / `month` / `xun` / `player_faction` / `prestige` / `gold` / `food` / `world`。

| 方法 | 用途 |
|---|---|
| `__init__()` | **不再读 constants**，字段全部置 0 / `None`（"未初始化"状态） |
| `sync_from_world(world)` | **新增**。剧本加载后注入 World，同步起始日期 |
| `date_text()` | 未初始化时返回 `"—"` |
| `advance_turn()` | 推进一旬；未初始化时直接返回 |
| `change_gold/food/prestige(delta)` | **改**：有 World 时写回玩家势力，否则写自身 |
| `get_display_items()` | **改**：5 项；`faction/prestige/gold/food` 从 `world.player_faction()` 读，未就绪时显示 `"—"` |

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

### 5.10 `game/map/geo_data.py`（1 处修改）

`_classify_county` 中 `shapes_point.append(...)` 的 `properties` 由旧的两个字段扩充为五个：

```python
"properties": {
    "id": city.get("id"),            # ★ 新增
    "县名": name,
    "level": level,
    "type": city.get("type", "县"),  # ★ 新增
    "is_capital": bool(city.get("is_capital", False)),  # ★ 新增
}
```

**为什么必须补**：旧结构只存 `{县名, level}`，Node 构造**依赖 `id`**（作为字典 key），且需要 `type` / `is_capital` 才能区分据点类别与郡治。

`labels_city` 保持四元组 `(lon, lat, name, level)`，渲染层不受影响。

> 维护要点：`level` 的两行解析仍必须**写在 `shapes_point.append` 之前**（否则抛 `UnboundLocalError`，地图完全不加载）。

### 5.11 `game/map/viewport.py` / `renderer.py`

**未改动**（参照前版文档 §3.9–3.10）。

### 5.12 `game/ui/main_window.py`

**关键改动**：

| 位置 | 改动 |
|---|---|
| 顶部 import | 加 `from game.core.scenario import ScenarioLoader` |
| `__init__` 属性 | 新增 `self._world = None`、`self._geo_data = None` |
| `load_geojson(path)` | **在 `self.map_canvas.reset_view()` 之前**保存 `self._geo_data = data` |
| `_auto_load_default()` | 加载地图成功后**接着调 `_load_default_scenario()`** |
| `_load_default_scenario()` | **新增**。读 `DEFAULT_SCENARIO_PATH` → `ScenarioLoader.load(path, self._geo_data)` → `game_state.sync_from_world(world)` → 状态栏显示 `world.summary()` |
| `_on_menu_action()` | 动作改名：`view_cities` → `view_nodes`，`view_generals` → `view_characters` |

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
    └── status_bar.set_message(world.summary())
```

### 5.13 `game/ui/top_bar.py`

**改动**：`_build_view_menu` 中三个菜单项改名：

| 旧 | 新 | 上报动作 |
|---|---|---|
| 城市列表 | **据点列表** | `view_cities` → `view_nodes` |
| 武将列表 | **人物列表** | `view_generals` → `view_characters` |
| 部队列表 | 部队列表 | 不变 |

`TopBar` 其余逻辑不变（200ms 轮询 `game_state.get_display_items()`）。

### 5.14 `game/ui/side_panel.py`

**改动**：

| 项 | 旧 | 新 |
|---|---|---|
| Tab 2 | `CityPanel` | `NodePanel` |
| Tab 3 | `GeneralPanel` | `CharacterPanel` |
| Tab 2 标题 | `" 城市 "` | `" 据点 "` |
| Tab 3 标题 | `" 武将 "` | `" 人物 "` |

Tab 顺序：势力(0) / 据点(1) / 人物(2) / 部队(3)。

### 5.15 `game/ui/panels/node_panel.py`（新建）

**类 `NodePanel`** — 8 列 Treeview：`id / name / type / level / owner / troops / gold / food`。

`refresh()` 遍历 `game_state.world.nodes.values()`；`world` 为 `None` 时只清空。

### 5.16 `game/ui/panels/character_panel.py`（新建）

**类 `CharacterPanel`** — 9 列 Treeview：`id / name / faction / node / lead / might / int / pol / cha`。

`refresh()` 遍历 `game_state.world.characters.values()`；势力/据点列显示名称而非 id。

### 5.17 其他 UI 模块

`status_bar.py` / `map_canvas.py` / `settings_window.py` / `window_utils.py` / `widgets/collapsible.py` / `panels/faction_panel.py` / `panels/troop_panel.py` **未改动**。

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
│     ├─ GeoData.from_file(path)
│     │  └─ _classify → 13 州 / 106 郡 / 1372 据点
│     │     └─ _classify_county：
│     │        先解析 level → shapes_point.append（含 id/type/is_capital）
│     │        + labels_city.append
│     ├─ if DEFAULT_WATER_PATH: data.load_water(...)
│     ├─ if DEFAULT_ROADS_PATH: data.load_roads(...)
│     ├─ renderer.set_data(data)
│     └─ _try_fit_now() → viewport.fit_to_bbox → renderer.draw_full()
│  ★ self._geo_data = data                 ← 保存供剧本使用
│  ★ map_canvas.reset_view()
│
└─ if 地图加载成功: _load_default_scenario()
   └─ ScenarioLoader.load(scenarios/default.json, self._geo_data)
      ├─ 构造 Faction（1 个）
      ├─ 构造 Character（5 个）
      ├─ _build_nodes_from_geo → 遍历 shapes_point 建 1372 个 Node
      ├─ _apply_node_overrides → 覆盖 17 个曹操据点
      └─ 返回 World
   ├─ self._world = world
   ├─ game_state.sync_from_world(world)
   │  └─ year/month/xun 从剧本同步
   └─ status_bar.set_message(world.summary() + " | 玩家势力：曹操")
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

### 6.4 模块协作关系

```
main.py
└─ ui.main_window ──┬─ config.settings_manager ─ config.style
                    │                            └ config.settings_schema
                    ├─ core.game_state ──────┐
                    ├─ core.scenario ────────┼─ core.world
                    │                        │  ├─ core.faction
                    │                        │  ├─ core.character
                    │                        │  └─ core.node
                    │                        │
                    ├─ ui.top_bar（读 game_state）
                    ├─ ui.status_bar
                    ├─ ui.map_canvas ─── map.viewport ─┐
                    │                   map.renderer ─┴─ map.geo_data ─ core.utils
                    ├─ ui.settings_window ─ ui.widgets.collapsible
                    │                    └─ ui.window_utils
                    └─ ui.side_panel ────┬─ panels.faction_panel
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
| `SCENARIOS_DIR` / `DEFAULT_SCENARIO_PATH` | ★ 剧本自动加载路径 |

**已删除**：`INITIAL_YEAR` / `INITIAL_MONTH` / `INITIAL_XUN` / `INITIAL_FACTION` / `INITIAL_PRESTIGE` / `INITIAL_GOLD` / `INITIAL_FOOD`（初始状态一律来自剧本/存档）。

### 7.2 设置窗口可改（`style.py` 默认值）

| 项 | 是否需重启 |
|---|---|
| `THEME` / `FONT_SIZES` / `FONT_CANDIDATES` | **是** |
| `MAP_STYLE` 全部子项 | 否 |
| `CITY_LEVEL_MIN_SCALE` | 否 |
| `LAYER_VISIBILITY`（`mountain` 已 UI 隐藏） | 否 |

### 7.3 代码内常量

| 位置 | 值 | 含义 |
|---|---|---|
| `MapCanvas._MIN_VALID_SIZE` | `10` | 布局未完成阈值 |
| `TopBar._REFRESH_INTERVAL_MS` | `200` | 信息栏轮询周期 |
| `MapRenderer` 各 TAG | `"label"/"water"/"road"/"point"/"polygon"/"line"` | 图层锚点 |
| 据点 `level` 范围 | `1–10` | 越界兜底 |
| 人物 id 范围 | `0001–9999` | 四位字符串 |
| 五维上限 | `100` | **约定**（代码不强制） |
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
| **据点/人物面板** | 有 `refresh()` 但只在 `side_panel.refresh_all()` 时被调（回合推进），启动后不主动刷 |
| 部队面板 | `refresh()` 只清空 |
| **type 决定能力** | 全部 type 建成 Node 对象，但**代码层未区分能力**（能否驻兵/征粮/被占领） |
| 设置窗口「操作」「游戏」tab | 骨架就位，内容为空 |

### 8.2 数据层缺失

- `GameState` 只有日期 + 玩家势力 + 3 项资源，无武将池/城市/部队/外交（已下沉到 `World`，但未与地图渲染/交互联动）
- **`assets/mountains.geojson` 无任何代码引用**；设置窗口 `LAYER_VISIBILITY.mountain` 已 `hidden=True`
- `assets/roads.geojson` 只做视觉呈现：`difficulty` 仅影响线宽
- 路网与据点/郡界无拓扑关联
- **据点 `level` / `type` 驱动渲染但未挂游戏逻辑**
- `labels_city` 经纬度与据点坐标相同，标签避让靠渲染层计算

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
10. `FactionPanel` 缺少 `refresh()`
11. `WINDOW_SIZE` 定义了但从未使用
12. `_cum_scale` 复位时机导致周期性全量重绘停顿
13. 无测试、无打包、无 lint 配置
14. 道路无 LOD、无空间索引
15. 动态图层重建 + `tag_lower` 额外开销
16. `CITY_LEVEL_MIN_SCALE` 硬编码定长
17. 四张 `*_by_level` 表同样问题
18. 县点与县名"同显同隐"依赖同表同判，分处两处
19. `_drawn` 置位时机是易错点
20. `refresh_dynamic` 绘制顺序决定层级
21. `shapes_point` 的 `level` 解析必须先于 `append`
22. 静态层依赖 `draw_full`；快速缩放可能边缘州郡缺失，靠 180 ms settle 缓解
23. `_cum_scale` 触发点是"当前视图"，不是"最终视图"
24. 拖拽路径不做静态层补画
25. **`SettingsManager.apply()` 必须就地修改 `style.py` 的字典**
26. **`SettingsManager` 必须在 `MainWindow.__init__` 早期创建并 `apply()`**
27. **`theme` / `font` 分组的 `restart=True` 是硬编码约定**
28. **`settings_schema.ITEMS` 与 `style.py` 结构必须一致**
29. **`level_table` 的 draft key 是 `path.LEVEL`**
30. **`SettingsWindow` 的保存/关闭路径必须走 `_do_destroy()`**
31. **`items` 中 `hidden=True` 的项要在 `_populate` 和 `_apply_filter` 两处都跳过**
32. **`water.geojson` 加载**：`try/except Exception: pass` 静默吞异常
33. **`LAYER_VISIBILITY.water` 默认 `False`**
34. **县名避让偏移必须与 `_point_radius` 同源**
35. **县点放大的三个字段联动**（`size_divisor` / `min_radius` / `max_radius`）
36. **外环绘制顺序**：先外环再主体
37. **空心 / 外环用不同的描边配置**
38. **`update_idletasks()` 不要在 `<Configure>` 回调链里调**
39. **设置窗口的滚轮用 `bind` 递归绑到每个子控件，不要用 `bind_all`**
40. **`scrollregion` 用 `winfo_reqheight()` 而不是 `bbox("all")`**
41. **多 Tab 结构下，`_apply_filter` / 滚轮 / `scrollregion` 都按"当前 tab"作用**
42. **`center_on_parent` 必须分多轮延迟设位置**
43. **方法缩进事故高发**：`render_point` / `_build_level_table` / `_bind_wheel_recursive` 等新加方法曾多次因复制粘贴导致缩进跑出类外
44. **`tag_lower(tag)` 要求 tag 下至少有一个 item**
45. ★ **`load_geojson` 必须在 `reset_view()` 之前保存 `self._geo_data`**：`_load_default_scenario` 依赖它。若顺序颠倒或漏存，剧本加载会因 `GeoData` 未就绪而失败。
46. ★ **剧本加载依赖 `shapes_point` 的 `id` 字段**：`GeoData._classify_county` 若漏掉 `"id": city.get("id")`，`_build_nodes_from_geo` 会因 `nid` 为空而跳过所有据点，`World.nodes` 为空字典，不报错但 UI 空。
47. ★ **势力 id = 君主 id 是硬约定**：代码里 `Faction.ruler_id` 直接返回 `self.id`；剧本里 `player_faction` / `Character.faction` / `Node.owner` 全部用四位人物 id 引用。改这个约定要同步改剧本 + 类定义。
48. ★ **`GameState.__init__` 处于"未初始化"状态（year=0）**：`date_text()` 返回 `"—"`，`get_display_items()` 除日期外全部 `"—"`。启动到剧本加载完成之间约 120 ms 内，顶栏显示"未初始化"是正常的。
49. ★ **`change_gold/food/prestige` 有双路径**：有 World 时写回玩家势力，否则写自身。目前只有 `_end_turn` 不涉及资源，所以两者等价。后续实现内政时注意别调错。

### 8.4 建议的下一步

1. **回合流程**：`_end_turn` 里推进 World 的日期 + 刷新面板；`side_panel.refresh_all()` 已就位
2. **据点交互**：点击地图上的据点 → 弹出据点详情（兵力/金钱/军粮/所属势力/驻守人物）
3. **人物面板联动**：点击人物 → 弹出人物详情（五维 + 所属 + 所在据点）
4. **接入 `mountains.geojson`**：新增 `GeoData.load_mountains` + `MapRenderer.render_mountains`，把 `LAYER_VISIBILITY["mountain"]` 挂上，然后删掉 schema 里 `hidden=True`
5. **type 能力矩阵**：定义每种 type 的"能否驻兵 / 能否征粮 / 能否被占领 / 是否交通节点"
6. **存档系统**：序列化 World（`factions` / `characters` / `nodes`）+ GameState，写 `userdata/saves/`
7. **新游戏流程**：菜单"新游戏"→ 弹窗选剧本 → 加载
8. **把势力/据点/人物面板的 `refresh()` 挂上启动后自动调用**（现在只在回合推进时调）
9. 给绘制方法的 `except Exception` 加"首次异常打印一次日志"
10. 设置系统扩展（同前版文档）

---

## 9. 变更日志（本轮 · 剧本系统）

### 新增

- **`scenarios/` 目录**：与 `assets/` 并列，存放剧本 JSON
- **`scenarios/default.json`**：默认剧本，"十八路诸侯 · 曹操据陈留"，17 个据点归曹操
- **`game/core/faction.py`**：`Faction` 类（id = 君主 id）
- **`game/core/character.py`**：`Character` 类（四位 id，五维）
- **`game/core/node.py`**：`Node` 类（六位 id，静态 + 动态字段）
- **`game/core/world.py`**：`World` 类（聚合三张表 + 元信息）
- **`game/core/scenario.py`**：`ScenarioLoader`（JSON + GeoData → World）
- **`game/ui/panels/node_panel.py`**：据点列表 Treeview（8 列）
- **`game/ui/panels/character_panel.py`**：人物列表 Treeview（9 列）

### 修改

- **`game/config/constants.py`**：
  - 删除全部 `INITIAL_*` 常量（初始状态一律来自剧本/存档）
  - 新增 `SCENARIOS_DIR` / `DEFAULT_SCENARIO_PATH`
- **`game/core/game_state.py`**：
  - 字段改为"未初始化"状态（`year=0`，资源 0）
  - 新增 `sync_from_world(world)` 方法
  - `get_display_items()` 改为从 `world.player_faction()` 读
  - `change_*` 双路径（有 World 写回势力，否则写自身）
- **`game/map/geo_data.py`**：
  - `_classify_county` 里 `shapes_point` 的 `properties` 补 `id` / `type` / `is_capital`（Node 构造依赖）
- **`game/ui/main_window.py`**：
  - `load_geojson` 中保存 `self._geo_data = data`（在 `reset_view` 之前）
  - `_auto_load_default` 改为"加载地图 → 成功后加载剧本"
  - 新增 `_load_default_scenario()`
  - `_on_menu_action` 动作改名：`view_cities` → `view_nodes`、`view_generals` → `view_characters`
- **`game/ui/top_bar.py`**：菜单项改名（城市→据点，武将→人物）
- **`game/ui/side_panel.py`**：
  - `CityPanel` → `NodePanel`，Tab 标题" 城市 "→" 据点 "
  - `GeneralPanel` → `CharacterPanel`，Tab 标题" 武将 "→" 人物 "

### 术语变更（全局）

| 旧 | 新 |
|---|---|
| 武将 / `General` | **人物 / `Character`** |
| 城市 / `City` | **据点 / `Node`** |
| 势力编号独立 | **势力 id = 君主人物 id** |

### 删除（可删文件）

- `game/ui/panels/general_panel.py`
- `game/ui/panels/city_panel.py`

### 数据约定（本轮定稿）

- 人物 id：全局四位字符串（`"0001"`–`"9999"`）
- 势力 id：= 君主的人物 id
- 据点 id：六位（州 2 + 郡 2 + 县 2）
- 五维上限：100（约定，代码不强制）
- `type` 决定能力，`level` 决定数值
- 全部 type 都建成 Node 对象（包括 `山地` / `谷`）

---

**变更核心集中在 §3（核心数据模型）**、**§4（数据格式参考）**、**§5.3–5.8 / 5.12–5.16**、**§6.2（加载流程）**、**§8.3 第 45–49 条**。