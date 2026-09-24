# 暗耻三国志 — 项目说明文档

> 本轮更新重点：**Panel 通用框架**（4 个面板收敛到 `panels/list/` 框架，具体面板只写配置）、**搜索**（实时 / 多词 AND / 保留分组结构）、**地图点选 + 选中高亮**、**hover 高亮（5 开关）**、**地图右键菜单**、**双向定位**。新增 §9.14 变更日志。

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
| **hover 回调契约** | `MapCanvas._location_callback(dict \| None)` | dict 含 state/county/city/node_id/lon/lat/px/py |
| **选中高亮** | `renderer._selected_node_id` / `SELECT_TAG` | 左键点选的县，描边加粗 2px 亮青 |
| **hover 高亮层** | `renderer._hover_info` / `HOVER_TAG` | 悬停县高亮，受 `MAP_INTERACTION` 5 开关控制 |
| **反向定位** | `GenericListPanel.scroll_to_row(key)` | 地图 → 列表：切 Tab + 滚动 + 选中 + 展开组 |
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
- ✅ **Panel 通用框架**：4 面板共享 `panels/list/`，具体面板只写配置
- ✅ **搜索**：实时 / 多词 AND / 保留分组结构 / 清空按钮
- ✅ **地图点选 + 选中高亮**：只点县、单选、描边加粗、再点/点空白取消
- ✅ **hover 高亮**：5 开关（描边 / 填充 / 整个势力 / tooltip / 区域）
- ✅ **地图右键菜单**：县上（情报 + 定位到列表）/ 空白（复位 / 放大 / 缩小）
- ✅ **双向定位**：地图 → 列表（切 Tab + 滚动 + 选中）/ 列表 → 地图
- ⚠️ 回合与资源为骨架
- ❌ 内政/军事/外交/存档均为空实现
- ❌ 主官 / 人物数 / 情报三项右键均为占位

---

## 2. 文件结构清单

```
san9edit/
├── main.py                            程序入口：MainWindow().run()
├── README.md                          本文档
├── 需求文档.md                        本轮需求（Panel 框架 + 地图交互）
├── tools/                             离线生成工具（不参与运行时）
│   ├── build_characters.py           从 xlsx/csv 生成 assets/characters.json
│   ├── build_scenario_190.py         生成 190 年默认剧本
│   ├── characters/                   人物原始数据（xlsx + 生成脚本）
│   └── map/                          地图预处理脚本（预处理 / 精简 / 县边界…）
├── assets/                            静态数据
│   ├── map.geojson                   中国全图（13 州 / 106 郡 / 1372 县）
│   ├── characters.json               1049 位人物基础数据
│   ├── roads.geojson / water.geojson / mountains.geojson   路网 / 水域 / 山地（山未接入）
├── scenarios/
│   └── default.json                  190 剧本（52 势力 / 498 人物 / ~550 据点）
├── userdata/
│   └── settings.json                 用户设置覆盖（只存与默认不同的项）
└── game/                             运行时主包
    ├── config/                        配置层（无业务逻辑）
    │   ├── constants.py              路径常量 + 窗口常量
    │   ├── style.py                  主题 THEME / 字号 FONT_SIZES / 地图样式 MAP_STYLE
    │   │                              / 分级显隐 CITY_LEVEL_MIN_SCALE / 图层 LAYER_VISIBILITY
    │   │                              / ★ hover 开关 MAP_INTERACTION
    │   ├── settings_manager.py       设置加载 / 保存 / 就地写回 style 模块
    │   └── settings_schema.py        设置窗口元数据（Tabs / Groups / Items）
    ├── core/                          核心数据层（与 UI 无关）
    │   ├── game_state.py             回合 / 日期 / 玩家势力 / 资源（信息栏数据源）
    │   ├── world.py                  World：势力 / 人物 / 据点的聚合容器 + 查询
    │   ├── faction.py                Faction：势力（stance 相对玩家）
    │   ├── character.py              Character：人物（44 字段，node / location 分离）
    │   ├── node.py                   Node：县 = 据点（静态 + 动态 owner/troops）
    │   ├── scenario.py               剧本加载（三层人物 + character_id_range）
    │   ├── territory.py              郡级势力统计（保留，暂不消费）
    │   └── utils.py                  颜色（lighten/darken）/ 几何工具
    ├── map/                           地图层（投影 + 渲染）
    │   ├── geo_data.py               GeoData：加载 / 分类 / 空间查询 find_location_detail
    │   ├── viewport.py               Viewport：经纬度 ⇄ 像素投影 / 缩放 / 平移
    │   └── renderer.py               MapRenderer：图层渲染 + ★ 选中/hover 高亮层
    └── ui/                            UI 层
        ├── main_window.py            装配工：布局 + hover 拼状态栏 + tooltip
        │                             + 地图右键菜单 + 双向定位
        ├── top_bar.py                顶部信息栏（200ms 轮询）+ 下拉菜单 +「进行」按钮
        ├── status_bar.py             底部状态栏（消息 / 缩放 / 位置）
        ├── map_canvas.py             MapCanvas：地图画布 + 鼠标（拖拽/缩放/点选/右键/hover）
        ├── map_controller.py         面板访问地图的唯一接口（fit_to_node / center_on…）
        ├── side_panel.py             右侧 Tab 集合 + 面板注册 + select_panel（反向定位切 Tab）
        ├── settings_window.py        设置窗口（多 Tab + 折叠分组 + 草稿 + 保存）
        ├── window_utils.py           窗口工具（最大化 / 居中）
        ├── widgets/
        │   └── collapsible.py        折叠区块（设置窗口分组用）
        └── panels/                   右侧四个面板
            ├── list/                 ★ 通用列表框架（通用代码唯一集中点）
            │   ├── panel.py          GenericListPanel 基类：UI 组装 + 排序/分组/搜索
            │   │                     /右键/多选/双向定位调度
            │   ├── columns.py        Column 列定义（含 image 列渲染扩展点）
            │   ├── model.py          Group 分组树节点（title/children/tags/row_tag）
            │   ├── sorting.py        按列排序（空值/"—" 永远排最后）
            │   ├── grouping.py       默认维度分组（正交 + priority_name 置顶）
            │   ├── group_bar.py      分组条（点选顺序 = 嵌套顺序）
            │   ├── search_bar.py     搜索框（实时 + 清空按钮 + parse_query 扩展点）
            │   └── context_menu.py   MenuItem / MenuContext + 菜单构建器
            ├── node_panel.py         据点面板（纯配置：NodeRow + COLUMNS + 分组 + 右键）
            ├── character_panel.py    人物面板（纯配置 + priority_name 玩家置顶）
            ├── faction_panel.py      势力面板（固定分组 build_groups + 色块 image 扩展点）
            └── troop_panel.py        部队面板（空壳接入框架，数据留白）
```

**依赖方向单向**：`main → ui → core/map → config`。

### 2.1 `panels/list/` 框架与具体面板的分工

| 关注点 | 框架（`list/`）负责 | 具体面板只写 |
|---|---|---|
| 列表 | Treeview 构建、列宽/对齐、滚动条、`group` tag | `COLUMNS` / `NAME_COLUMN` |
| 排序 | 列头点击切换升降序、空值排最后 | （无需） |
| 分组 | 默认维度分组（`GROUP_DIMS` + GroupBar） | `GROUP_DIMS` / `DEFAULT_GROUP` / `PRIORITY_NAME` |
| 固定分组 | `CUSTOM_GROUPING` 时走 `build_groups()` 回调 | `build_groups()`（势力用） |
| 搜索 | 过滤调度、多词 AND、保留分组结构 | （无需） |
| 右键菜单 | 菜单弹出、多选上下文、`MenuItem` 构建 | `context_menu_items()` |
| 列渲染 | `Column.image` 扩展点（文本前加图片） | `image` 取值函数（势力色块） |
| 定位到地图 | `locate_on_map()` 默认按 `node_id/coords` | （可选覆盖） |
| 反向定位 | `scroll_to_row()` 展开祖先 + 滚动 + 选中 | `row_key()` |

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

### 5.23 ★ `game/ui/panels/list/`（本轮新增框架）

通用列表面板框架，核心 `GenericListPanel`（`panel.py`），分工见 §2.1：

- **构建 UI**：搜索框 + 分组条 + Treeview + 滚动条（`_build_ui`）
- **调度**：排序（`_on_heading_click`）、分组（`_build_groups`）、搜索（`_apply_search`）
- **右键**：`_on_right_click` 拼 `MenuContext` → `context_menu_items` 配置 → `build_menu` 弹出
- **多选**：`extended` + `_on_select_all`（Ctrl+A）
- **双向定位**：`scroll_to_row`（展开祖先 + 滚动 + 选中）、`locate_on_map`（默认 `node_id/coords`）

### 5.24 其它

`faction.py` / `game_state.py` / `utils.py` / `node.py` / `world.py` / `territory.py` / `viewport.py` / `top_bar.py` / `status_bar.py` / `settings_window.py` / `window_utils.py` / `collapsible.py` / `constants.py` 未改动。

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
| 据点右键 → 定位 | `MenuItem「定位到地图」` → `GenericListPanel.locate_on_map` → `MapController.fit_to_node` → `MapCanvas.fit_to_node` → `_node_bbox` → `viewport.fit_to_bbox` → `draw_full` |
| 据点右键 → 展开/折叠 | `MenuItem「全部展开/折叠」` → `GenericListPanel._toggle_all` → `tree.item(open=...)` 递归 |
| 据点列头点击 | `_on_heading_click` → `_sort_key/_sort_desc` → `refresh` |
| 据点分组切换 | `GroupBar._toggle` → `on_change` → `NodePanel.refresh` |
| 人物列头点击 | `_on_heading_click` → `refresh` |
| 人物右键 → 定位到据点 | `MenuItem「定位到据点」` → `GenericListPanel.locate_on_map` → `MapController.fit_to_node` |
| 人物分组切换 | `GroupBar._toggle` → `on_change` → `CharacterPanel.refresh` → **`priority_name` 玩家置顶** |
| ★ 搜索输入 | `SearchBar._on_write` → `_on_search_change` → `refresh`（过滤在分组前） |
| ★ 左键点选 | `_on_release`（位移≤4px）→ `_handle_click` → `renderer.set_selected` → `_redraw_selected` |
| ★ hover 高亮 | `_process_motion` → `renderer.set_hover` → `_redraw_hover`（吃 5 开关） |
| ★ hover tooltip | `_process_motion` → `_location_callback` → `MainWindow._on_location_change` → `_update_tooltip` |
| ★ 地图右键（县上） | `MapCanvas._on_right_click` → `MainWindow._on_map_right_click` → `_build_node_context_menu` |
| ★ 地图右键（空白） | `_on_map_right_click(node_id=None)` → `_build_empty_context_menu`（复位/放大/缩小） |
| ★ 反向定位 | 右键「定位到列表→据点」→ `_locate_to_list` → `side_panel.select_panel` → `NodePanel.scroll_to_row` |

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
                    │        ↳ 查 World 拼势力名 → status_bar / tooltip
                    │   ★ 右键回调 → MainWindow._on_map_right_click → 双向定位
                    ├─ ui.map_controller
                    ├─ ui.settings_window
                    └─ ui.side_panel ──── panels.faction_panel ──┐
                                       ├─ panels.node_panel ─────┤
                                       ├─ panels.character_panel ┤── panels.list（通用框架）
                                       └─ panels.troop_panel ────┘
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
| **势力色块尺寸** | **`行高 − 6`** | ★ 动态计算（`_compute_swatch_size`，最小 8） |
| **势力色块黑边** | **`1 px`** | ★ `img.put("#000000", to=(0,0,size,size))` |
| `character_id_range` 默认 | `[1, 1000]` | 排除穿越人物 |
| `character_id_range` 不写 | `[1, 9999]` | 全部加载 |
| 190 剧本势力 / 人物 / 据点 | `52 / 498 / ~550` | 定稿 |
| `Character._DEFAULT_STAT` | `50` | 五维缺省值 |
| **选中描边** | **`#00C8FF` / `2px`** | `renderer.SELECT_TAG` |
| **hover 描边** | **`#00BFFF` / `2px`** | `renderer.HOVER_TAG` |
| **hover 填充** | **`lighten_color(color, 0.45)`** | 蒙白 45%（无主县 `#F5F5F5`） |
| **点击判定阈值** | **`4 px`** | 位移 ≤ 4px 算点击，否则拖拽 |
| **面板 selectmode** | **`extended`** | 多选（Ctrl / Shift / Ctrl+A） |
| **`MAP_INTERACTION` 默认** | tooltip 开；border / fill / faction_all / region 关 | 5 开关 |

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
| **搜索正则 / 跨字段 / 拼音** | **只留 `parse_query` 接口，未实现** |
| **反向定位（人物 / 势力 / 部队）** | **占位，`state="disabled"`** |
| **region 高亮州面** | **只做郡面（基础版），州面 MultiPolygon 未做** |
| **地图情报三项右键** | **占位，只 `print`** |

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

---

### 9.14 Panel 通用框架 + 地图交互（第十五轮）

#### 需求

1. **Panel 通用框架**：4 个面板（据点 / 人物 / 势力 / 部队）共享一套基础设施，具体面板只写配置
2. **搜索**：实时 / 包含匹配 / 多词 AND / 保留分组结构 / 清空按钮
3. **地图交互**：左键点选 + 选中高亮；hover 高亮（5 开关）；地图右键菜单（县上 / 空白两种）
4. **双向定位**：地图 → 列表（右键触发）、列表 → 地图（`fit_to_node`）

#### 改动

**新增**：
- `game/ui/panels/list/` —— 通用框架 9 文件（panel / columns / model / sorting / grouping / group_bar / search_bar / context_menu）
- `game/ui/panels/node_panel.py` —— 据点面板（纯配置）

**重写**（瘦身为配置）：
- `character_panel.py` / `faction_panel.py` / `troop_panel.py`

**删除**（旧包，代码并入框架）：
- `game/ui/panels/node/`、`game/ui/panels/character/` 共 16 文件

**地图层**：
- `renderer.py` —— 新增选中 / hover 高亮层（`SELECT_TAG` / `HOVER_TAG`）
- `map_canvas.py` —— 点选（拖拽/点击判定）、右键回调、hover 高亮触发、`px/py` 传递
- `main_window.py` —— 地图右键菜单、tooltip 浮窗、`_locate_to_list` 双向定位
- `side_panel.py` —— 面板注册 `panels` 字典 + `select_panel`（反向定位切 Tab）

**配置层**：
- `style.py` —— 新增 `MAP_INTERACTION`（5 开关）
- `settings_manager.py` —— `_DEFAULTS` + `apply` 接入 `MAP_INTERACTION`
- `settings_schema.py` —— 新增「操作」Tab 下的「地图悬停互动」分组 + 5 个 bool 项

#### 设计决策

- **三个框架扩展点**（需求 2.4 的三处差异）：
  - 势力「固定分组」→ `CUSTOM_GROUPING` + `build_groups()` 回调
  - 势力「色块」→ `Column.image` 列渲染扩展点
  - 人物「玩家置顶」→ `priority_name()` 动态方法
- **分组树抽象 `Group`**：`title / children / tags / open / row_tag`，同时承载组头配色与行配色
- **hover 高亮用独立图层 tag**：删旧画新，不污染底层数据；pan/zoom 走 `move/scale` 自动跟随
- **点选不触发业务逻辑**：只更新 `renderer._selected_node_id` + 高亮，不滚动列表 / 不弹窗 / 不查 World
- **反向定位 `_syncing` 防递归**：`scroll_to_row` 期间置位，阻止列表 → 地图回触发
- **搜索过滤在分组前**：过滤只作用于叶子行，组内有匹配行才显示该组（空组隐藏）

#### 待办（本轮明确记录）

- `highlight_hover_region` 为基础版：只高亮郡面，州面（MultiPolygon）未做
- 反向定位其余 3 项（人物 / 势力 / 部队）占位，`state="disabled"`
- 搜索正则 / 跨字段 / 拼音只留 `parse_query` 接口，未实现
- 地图情报三项右键仍为 `print` 占位