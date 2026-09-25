# 暗耻三国志 — 项目说明文档

> 本轮更新重点：**全流程日志系统**（`game/config/logging_setup.py`，每次启动一个文件 + session id + tkinter 回调异常钩子，零第三方依赖）。新增 §9.18 变更日志。
>
> 上一轮（第十七轮）：剧本编辑器（`APP_MODE` 模式切换 + 据点/势力编辑 + 通用 undo/redo + 增量保存），见 §9.17。第十六轮：人物情报窗口 + 头像资产规范化，见 §9.16。

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
| **势力色块** | `FactionPanel` 里势力名前的 ■ | 带黑边，边长 = 行高 − 2 |
| **hover 回调契约** | `MapCanvas._location_callback(dict \| None)` | dict 含 state/county/city/node_id/lon/lat/px/py |
| **选中高亮** | `renderer._selected_node_id` / `SELECT_TAG` | 左键点选的县，描边加粗 2px 亮青 |
| **hover 高亮层** | `renderer._hover_info` / `HOVER_TAG` | 悬停县高亮，受 `MAP_INTERACTION` 5 开关控制 |
| **反向定位** | `GenericListPanel.scroll_to_row(key)` | 地图 → 列表：切 Tab + 滚动 + 选中 + 展开组 |
| **主官 / 人物数** | （预留，未实现） | 将来由剧本 / `world.characters_at` 提供 |
| **面板列配置** | `style.PANEL_COLUMNS` | 每面板 `{order:[], hidden:[]}`，见 §9.15 |
| **面板 key** | `GenericListPanel.PANEL_KEY` | 面板在 `PANEL_COLUMNS` 里的键：node/character/faction/troop |
| **列解析** | `GenericListPanel._resolve_columns()` | 读 `PANEL_COLUMNS` → 返回过滤重排后的可见列 |
| **头像路径约定** | `assets/portrait/{id}-{name}.{ext}` | ★ 不再读 `Character.portrait` 字段，见 §9.16 |
| **头像加载** | `CharacterInfoWindow._load_portrait` | ★ Pillow 打开 + `thumbnail` + `ImageTk.PhotoImage` |
| **人物情报窗口** | `CharacterInfoWindow` | ★ 右键人物 →「人物情报」弹出的 `Toplevel` |
| **应用模式** | `APP_MODE` / `MODE_EDIT` / `MODE_GAME` | ★ 编译期切换，默认 `MODE_EDIT`（§1.1） |
| **编辑会话** | `EditSession` | ★ Command 栈 + baseline + dirty 判定（§11.1） |
| **命令** | `Command` / `CompositeCommand` | ★ 改 World 的唯一入口，UI 不直接赋值（§10.1） |
| **增量保存** | `ScenarioWriter.save` | ★ `raw 原样 + diff 增量`，未改动不写（§7） |
| **字段描述** | `Field` | ★ 弹窗数据驱动核心，6 种 kind（§10.6） |
| **编辑类标识** | `MenuItem.edit` / `TopBar._edit_entries` | ★ 标记编辑入口，按 `APP_MODE` 一键全禁（§9.17 需求 8） |
| **据点编辑共用流程** | `dialogs/node_edit.py::edit_node` | ★ 面板右键与地图右键共用（含郡治互斥） |
| **日志系统** | `logging_setup.py` / `LOG_DIR` | ★ 每次启动一个文件，DEBUG，保留 30 个（§9.18） |
| **session id** | `logging_setup._SESSION_ID` | ★ 8 位十六进制，每行日志前缀，区分多次启动 |
| **异常钩子** | `install_sys_excepthook` / `install_tk_excepthook` | ★ 未捕获异常 + tkinter 回调异常统一入日志 |

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
5. **头像不再走 `portrait` 字段**：直接从 `assets/portrait/{id}-{name}.{ext}` 拼路径（§9.16）。

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
- **不吃 LOD**：只要在视口内且有主，就画。
- 只做**视口粗筛**（屏幕外跳过），性能足够。
- 无主县不染色，州面底色透出。

**「hover 回调契约」约定（第十四轮）：**

- `MapCanvas._location_callback(info)`，`info` 是 **dict 或 None**。
- dict 结构：`{"state": 州名, "county": 郡名, "city": 县名, "node_id": 县 id, "lon": float, "lat": float}`
- 鼠标离开画布 → 传 `None`。
- **`MapCanvas` 不感知 `World`**，由 `MainWindow` 拿到 dict 后再拼装势力名。

**「头像资产」约定（第十六轮）：**

- 头像统一命名 `{id}-{name}.{ext}`，如 `0651-张南.jpg`。
- 通过 `tools/check_portraits.py` 对账、`tools/rename_portraits.py` 批量改名。
- 运行时**拼路径，不读 `Character.portrait` 字段**（该字段保留兼容，不再消费）。
- 同名多人的处理：复制多份，形如 `0651-张南.jpg`、`0652-张南.jpg`。

**「剧本编辑」约定（第十七轮）：**

1. **改 World 只走 Command**：UI 构造 Command → `EditSession.execute()`，**不得**直接赋值实体字段（§10.1 硬约束）。
2. **双重 baseline**：`raw`（写回模板，保留未改动字段原值）+ `baseline_snap`（diff 基准，加载后立即 `serialize`）。
3. **`Faction.gold / food` 是派生值**：名下据点求和，`_nodes_ref` 是 `world.nodes` 引用，不落盘、不可赋值。
4. **增量保存**：`output = deepcopy(raw) + diff(current, baseline_snap)`，未改动字段不出现。
5. **弹窗数据驱动**：只认 `Field.kind`（int/str/bool/choice/color/readonly），不认业务实体。

---

## 1. 项目概述

| 项 | 内容 |
|---|---|
| 项目名称 | 暗耻三国志（`APP_TITLE`） |
| 定位 | 三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》 |
| 程序入口 | `main.py` → `MainWindow().run()` |
| 核心功能 | 中国全图矢量渲染、鼠标缩放平移、**光标精确反查州/郡/县/势力**、旬回合制时钟、顶部信息栏与菜单、右侧 Tab 面板框架、多 Tab 设置窗口、剧本系统、**势力面板（带色块 + 据点数 / 人物数）**、**县面势力染色（唯一着色图层，不吃 LOD）**、**据点面板**、**人物面板（玩家势力置顶）**、**人物情报窗口（Pillow 头像）**、**面板列配置（顺序 / 显隐可调）**、**人物基础数据（1049 人）+ 190 剧本（52 势力 / 498 人物 / 550 据点）** |
| 运行环境 | Python 3 + 标准库 `tkinter` + **Pillow**（第三方，仅人物情报窗口用） |
| 数据来源 | `assets/map.geojson`：13 州 / 106 郡 / 1372 县；`roads.geojson`；`water.geojson`；`mountains.geojson`（未接入）；`characters.json`：1049 人；**`assets/portrait/`：人物头像** |
| 剧本来源 | `scenarios/default.json`（**190 年 · 十八路诸侯**） |
| 用户数据 | `userdata/settings.json` |
| 平台 | Windows 优先 |

**当前完成度：**

- ✅ 地图查看器（州/郡/县三级边界 + 道路 + 水域 + 图层显隐 + 县名避让）
- ✅ **县界渲染** / **几何层去色** / **县面势力染色（不吃 LOD）** / **图层顺序保障可读性** / **郡名标签独立字体**
- ✅ **hover 精确反查**：`州 · 郡 · 县 · 势力`
- ✅ 多 Tab 设置系统 / 剧本系统
- ✅ **势力面板**：按玩家/盟友/敌对/中立分组 + **势力色块**（带黑边）+ **据点数 / 人物数列**
- ✅ **据点面板**：8 列 + 排序 + 嵌套分组（默认州>郡）+ 右键 + 全部展开/折叠 + 定位到地图
- ✅ **人物面板**：8 列 + 排序 + 分组（默认势力，**玩家势力置顶**）+ 右键（人物情报 / 复制编号 / 定位到据点）+ **姓名列去表字**
- ✅ **人物情报窗口**：居中弹窗 + Pillow 头像
- ✅ **`MapController`** / **`MapCanvas.center_on` / `fit_to_node`**
- ✅ **`Character` 类全展开**（44 字段，含中文注释）
- ✅ **`tools/build_characters.py`** / **`tools/build_scenario_190.py`**
- ✅ **`tools/check_portraits.py`** / **`tools/rename_portraits.py`**（第十六轮新增）
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
- ✅ **面板列配置**：4 面板列顺序 / 显隐可由设置窗口「面板列」tab 调整
- ✅ **剧本编辑模式**：`APP_MODE` 编译期切换 + 文件/编辑菜单 + 据点/势力编辑 + 通用 undo/redo + 增量保存（第十七轮）
- ✅ **`Faction.gold / food` 派生值化**：名下据点求和，不再落盘
- ✅ **地图右键「编辑据点」** + **编辑入口统一标识**（`edit=True` / `set_edit_enabled`，一键按模式禁用）
- ✅ **全流程日志系统**：每次启动一个文件 + session id + sys/tk 异常钩子，零第三方依赖（第十八轮）
- ⚠️ 回合与资源为骨架
- ❌ 内政/军事/外交/存档均为空实现
- ❌ 主官 / 人物数 / 情报三项右键均为占位

---

## 2. 文件结构清单

```
san9edit/
├── main.py                            程序入口：MainWindow().run()
├── README.md                          本文档
├── 需求文档.md                        本轮需求
├── requirements.txt                   ★ 依赖声明（Pillow）
├── tests/                            ★ 单元测试（CompositeCommand / ScenarioWriter）
├── tools/                             离线生成工具（不参与运行时）
│   ├── build_characters.py           从 xlsx/csv 生成 assets/characters.json
│   ├── build_scenario_190.py         生成 190 年默认剧本
│   ├── check_portraits.py            ★ 头像 ↔ 人物数据对账（只输出报告）
│   ├── rename_portraits.py           ★ 头像文件重命名为 {id}-{name}.{ext}
│   ├── characters/                   人物原始数据（xlsx + 生成脚本）
│   └── map/                          地图预处理脚本（预处理 / 精简 / 县边界…）
├── assets/                            静态数据
│   ├── map.geojson                   中国全图（13 州 / 106 郡 / 1372 县）
│   ├── characters.json               1049 位人物基础数据
│   ├── portrait/                     ★ 人物头像（{id}-{name}.jpg）
│   ├── roads.geojson / water.geojson / mountains.geojson   路网 / 水域 / 山地（山未接入）
├── scenarios/
│   └── default.json                  190 剧本（52 势力 / 498 人物 / ~550 据点）
├── userdata/
│   ├── settings.json                 用户设置覆盖（只存与默认不同的项）
│   └── logs/                         ★ 运行日志（app_YYYYMMDD_HHMMSS.log，保留 30 个）
└── game/                             运行时主包
    ├── config/                        配置层（无业务逻辑）
    │   ├── constants.py              路径常量 + 窗口常量
    │   ├── style.py                  主题 THEME / 字号 FONT_SIZES / 地图样式 MAP_STYLE
    │   │                              / 分级显隐 CITY_LEVEL_MIN_SCALE / 图层 LAYER_VISIBILITY
    │   │                              / hover 开关 MAP_INTERACTION
    │   │                              / 面板列 PANEL_COLUMNS
    │   ├── settings_manager.py       设置加载 / 保存 / 就地写回 style 模块
    │   ├── settings_schema.py        设置窗口元数据（Tabs / Groups / Items）
    │   │                              + get_panel_columns_meta()
    │   └── logging_setup.py          ★ 日志初始化 + sys/tk 异常钩子（§9.18）
    ├── core/                          核心数据层（与 UI 无关）
    │   ├── game_state.py             回合 / 日期 / 玩家势力 / 资源（信息栏数据源）
    │   ├── world.py                  World：势力 / 人物 / 据点的聚合容器 + 查询
    │   │                              + count_nodes_by_owner / count_characters_by_faction
    │   ├── faction.py                Faction：势力（stance 相对玩家）
    │   ├── character.py              Character：人物（44 字段，node / location 分离）
    │   ├── node.py                   Node：县 = 据点（静态 + 动态 owner/troops）
    │   ├── scenario.py               剧本加载（三层人物 + character_id_range）
    │   ├── territory.py              郡级势力统计（保留，暂不消费）
    │   ├── edit_session.py          ★ Command / CompositeCommand / EditSession
    │   ├── edit_commands.py         ★ NodeEditCommand / FactionEditCommand
    │   ├── scenario_writer.py       ★ serialize / diff / save（增量）
    │   └── utils.py                  颜色（lighten/darken）/ 几何工具
    ├── map/                           地图层（投影 + 渲染）
    │   ├── geo_data.py               GeoData：加载 / 分类 / 空间查询 find_location_detail
    │   ├── viewport.py               Viewport：经纬度 ⇄ 像素投影 / 缩放 / 平移
    │   └── renderer.py               MapRenderer：图层渲染 + 选中/hover 高亮层
    └── ui/                            UI 层
        ├── main_window.py            装配工：布局 + hover 拼状态栏 + tooltip
        │                             + 地图右键菜单 + 双向定位 + 面板列刷新转发
        ├── top_bar.py                顶部信息栏（200ms 轮询）+ 下拉菜单 +「进行」按钮
        ├── status_bar.py             底部状态栏（消息 / 缩放 / 位置）
        ├── map_canvas.py             MapCanvas：地图画布 + 鼠标（拖拽/缩放/点选/右键/hover）
        ├── map_controller.py         面板访问地图的唯一接口（fit_to_node / center_on…）
        ├── side_panel.py             右侧 Tab 集合 + 面板注册 + select_panel
        │                             + reload_panel_columns()
        ├── settings_window.py        设置窗口（多 Tab + 折叠分组 + 草稿 + 保存）
        │                             +「面板列」tab + 8 个方法
        ├── character_info_window.py  ★ 人物情报窗口（Pillow 头像）
        ├── dialogs/                  ★ 编辑弹窗（数据驱动）
        │   ├── field_spec.py        Field NamedTuple（6 种 kind）
        │   ├── edit_dialog.py       通用数据驱动弹窗（无实体分支）
        │   ├── node_fields.py       据点字段表
        │   └── faction_fields.py    势力字段表
        ├── window_utils.py           窗口工具（最大化 / 居中）
        ├── widgets/
        │   └── collapsible.py        折叠区块（设置窗口分组用）
        └── panels/                   右侧四个面板
            ├── list/                 ★ 通用列表框架（通用代码唯一集中点）
            │   ├── panel.py          GenericListPanel 基类：UI 组装 + 排序/分组/搜索
            │   │                     /右键/多选/双向定位调度 + _resolve_columns / reload_columns
            │   ├── columns.py        Column 列定义（含 image 列渲染扩展点）
            │   ├── model.py          Group 分组树节点（title/children/tags/row_tag）
            │   ├── sorting.py        按列排序（空值/"—" 永远排最后）
            │   ├── grouping.py       默认维度分组（正交 + priority_name 置顶）
            │   ├── group_bar.py      分组条（点选顺序 = 嵌套顺序）
            │   ├── search_bar.py     搜索框（实时 + 清空按钮 + parse_query 扩展点）
            │   └── context_menu.py   MenuItem / MenuContext + 菜单构建器
            ├── node_panel.py         据点面板（纯配置 + PANEL_KEY）
            ├── character_panel.py    人物面板（纯配置 + priority_name 玩家置顶
            │                         + PANEL_KEY + 姓名列去表字 + 人物情报入口）
            ├── faction_panel.py      势力面板（固定分组 build_groups + 色块 image 扩展点
            │                         + COLUMNS 绑定 / PANEL_KEY / 据点·人物列）
            └── troop_panel.py        部队面板（空壳接入框架 + PANEL_KEY）
```

**依赖方向单向**：`main → ui → core/map → config`。

**第三方依赖**：`Pillow`（仅 `game/ui/character_info_window.py` 使用）。`requirements.txt` 里声明。

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
| 列配置 | `_resolve_columns()` 读 `PANEL_COLUMNS` + 过滤重排 | `PANEL_KEY` |
| 列热重载 | `reload_columns()` 重建 Treeview + refresh | （无需） |
| **编辑会话** | `edit_session` 类属性 + `_open_dialog()` / `_notify_edit()` | `context_menu_items()` 里的 `_edit()` |
| **编辑入口置灰** | `build_menu(edit_enabled=edit_session is not None)` 统一处理 `edit=True` 项 | `MenuItem(..., edit=True)` |

---

## 3. 核心数据模型

### 3.1 三层 ID 编码

州 2 位 / 郡 4 位 / **县 6 位**。一个六位 id 对应一个县 = 一个据点 = 一个 `Node`。

### 3.2 势力（Faction）

`id` = 君主人物 id。**可落盘字段**：`id` / `name` / `color` / `prestige` / `stance`。
`stance_label()` → `"敌对"` / `"盟友"` / `"中立"`。

**★ `gold` / `food` 是派生值（第十七轮起）**：

```python
@property
def gold(self):
    """名下据点金钱求和。无主据点不计。"""
    if self._nodes_ref is None:
        return 0
    return sum(n.gold for n in self._nodes_ref.values() if n.owner == self.id)
```

- `_nodes_ref` 是 **`world.nodes` 的引用**（不是快照），由 `World.bind_factions()` 注入
- **无 setter** —— `faction.gold = x` 会报错（`GameState.change_gold` 已标记 `TODO(phase3)`）
- `from_dict` **不再读** `gold/food`；`to_dict` **不再写**（旧剧本里的遗留字段被静默忽略）
- 好处：改据点 `owner` 后，势力金/粮**自动**反映（为 phase2 的 owner 编辑铺路）

### 3.2.1 序列化对称性（第十七轮）

| 类 | `to_dict` 写什么 |
|---|---|
| `Node` | **从零写全 7 字段**：`owner / troops / gold / food / type / level / is_capital` |
| `Faction` | `name / color / prestige / stance`（**不写** `gold/food`） |
| `Character` | 全 34 字段（含 `portrait / faction / node / location / role`） |

理由见 §8.3 第 152 条：加新的可编辑静态字段时，**写 / 读 / 显示三处必须同步**。

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

**★ `portrait` 字段（第十六轮起）：**

- 字段**保留**（`from_dict` / `to_dict` 依旧读写），但**不再被消费**。
- 头像路径改为拼 `assets/portrait/{id}-{name}.{ext}`。
- 将来清理时再删字段。

#### 方法

| 方法 | 说明 |
|---|---|
| `is_ruler()` / `is_free()` / `is_appeared(year)` / `is_alive(year)` | 语义判断 |
| `display_name()` | 带表字的展示名（人物情报窗口标题仍用） |
| `from_dict(cid, d)` / `to_dict()` | JSON 双向 |
| `apply_override(data)` | 剧本覆盖（`hasattr` 防脏数据） |

### 3.4 县 = 据点（Node）

**静态**：`id` / `name` / `coords` / `type` / `level` / `is_capital` / `boundary`。
**动态**：`owner` / `troops` / `gold` / `food`。
**属性**：`state_id` → `id[:2]`，`county_id` → `id[:4]`，`is_owned()`。

**★ `to_dict()`（第十七轮新增）**：从零写全 7 字段，供 `ScenarioWriter.serialize` 用。

**★ 静态字段可被剧本覆盖（第十七轮）**：`_apply_node_overrides` 除 `owner/troops/gold/food` 外，
现在也读 `type / level / is_capital` —— 否则编辑保存后重新加载会回原样（§9.17 症状表）。

**★ 渲染必须查 World 而非 GeoData**：`renderer._effective_level(props)` 优先取 `world.node(id).level`，
退回 `GeoData.shapes_point` 的 `level`。否则改 `level` 后地图县点大小 / 形状不更新。

### 3.5 游戏世界（World）

聚合容器：`factions` / `characters` / `nodes` / `state_names` / `county_names`。

**查询**：

```python
def state_name(self, sid):  return self.state_names.get(sid, sid or "—")
def county_name(self, cid): return self.county_names.get(cid, cid or "—")
def faction(self, fid):     return self.factions.get(fid) if fid else None
def node(self, nid):        return self.nodes.get(nid) if nid else None
```

**聚合（第十六轮新增）：**

```python
def count_nodes_by_owner(self):
    """每个势力拥有的据点数。dict[fid, int]，无主据点不计。"""
    return Counter(n.owner for n in self.nodes.values() if n.owner)

def count_characters_by_faction(self):
    """每个势力的人物数。dict[fid, int]，无势力人物不计。"""
    return Counter(c.faction for c in self.characters.values() if c.faction)
```

口径与既有 `nodes_of` / `characters_of` 一致（`node.owner` / `char.faction`）。返回 `Counter`（dict 子类），调用方 `.get(fid, 0)`。

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

**★ `CityIndex`（`GeoData._city_index`）结构（第十四轮）**：

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

### 4.7 ★ 头像资产（第十六轮）

**目录**：`assets/portrait/`
**命名**：`{id}-{name}.{ext}`，如 `0651-张南.jpg`
**扩展名**：`.jpg` / `.jpeg` / `.png` / `.gif` / `.bmp` / `.webp`
**同名多人**：复制多份，如 `0651-张南.jpg` + `0652-张南.jpg`

**规范流程**：

```bash
python tools/check_portraits.py           # 对账（只读）
python tools/rename_portraits.py          # 预览改名计划
# 顶部 APPLY 改 True 后
python tools/rename_portraits.py          # 执行
```

---

## 5. 模块与函数清单

### 5.1 – 5.14

（同上轮）

### 5.15 `game/map/renderer.py`

`render_territory` 去掉 LOD 粗筛（第十三轮改动，未变）。保留视口粗筛。

### 5.16 – 5.18

（同上轮）

### 5.19 `game/map/geo_data.py`（第十四轮改动）

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
        nid = props.get("id")
        if not name or not nid:
            continue
        bbox = feat["bbox"]
        self._city_index.append((bbox, name, ring, nid))
```

**② `find_city_at` 解包改成 4 元组**：

```python
for (minx, miny, maxx, maxy), name, ring, nid in self._city_index:
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
        city_name = self.find_nearest_label(lon, lat, self.labels_city, 0.4)

    return {
        "state":   state,
        "county":  county,
        "city":    city_name,
        "node_id": node_id,
    }
```

### 5.20 `game/ui/map_canvas.py`（第十四轮改动）

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
    info = self.data.find_location_detail(lon, lat)
    info["lon"] = lon
    info["lat"] = lat
    self._location_callback(info)
```

**② `_on_leave` 传 None**：

```python
def _on_leave(self, event):
    if self._location_callback:
        self._location_callback(None)
```

### 5.21 `game/ui/main_window.py`（第十四轮改动）

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

`_on_settings_applied(changed_paths)` 增 `panel_dirty` 分支：

```python
        panel_dirty = False
        for p in changed_paths:
            if p.startswith("MAP_STYLE.") \
            or p.startswith("CITY_LEVEL_MIN_SCALE") \
            or p.startswith("LAYER_VISIBILITY."):
                map_dirty = True
            elif p.startswith("PANEL_COLUMNS"):
                panel_dirty = True

        # ... 原有 map redraw ...

        if panel_dirty:
            side = getattr(self, "side_panel", None)
            if side is not None and hasattr(side, "reload_panel_columns"):
                try:
                    side.reload_panel_columns()
                except Exception:
                    pass
```

### 5.22 `game/ui/panels/faction_panel.py`（第十四 / 十六轮改动）

**色块部分（第十四轮）：**

- `__init__` 加 `self._swatches = {}` + `self._swatch_size = self._compute_swatch_size()`
- `_compute_swatch_size()`：读 ttk 主题行高，返回 `max(8, 行高 − 6)`
- `_make_swatch(color)`：先整块填 `#000000`，再在 `(1, 1, size-1, size-1)` 填势力色
- `_swatch_for(row)`：PhotoImage 缓存，`refresh` 前 `clear()`
- `NAME_COLUMN` 用 `Column(..., image=self._swatch_for)`

**势力面板列（第十六轮）：**

```python
@dataclass(frozen=True)
class FactionRow:
    id: str
    name: str
    color: str
    prestige: int
    gold: int
    food: int
    stance: int
    ruler_name: str
    node_count: int = 0
    char_count: int = 0

    @classmethod
    def from_faction(cls, f, world, node_count=0, char_count=0):
        ruler = world.characters.get(f.ruler_id)
        return cls(
            id=f.id, name=f.name, color=f.color,
            prestige=f.prestige, gold=f.gold, food=f.food, stance=f.stance,
            ruler_name=ruler.name if ruler is not None else "—",
            node_count=node_count, char_count=char_count,
        )
```

**类体内必须显式绑定 `COLUMNS = COLUMNS`（见 §8.3 第 141 条）。**

```python
class FactionPanel(GenericListPanel):
    COLUMNS = COLUMNS           # ★ 必须：否则 self.COLUMNS 取基类默认 ()
    PANEL_KEY = "faction"
    CUSTOM_GROUPING = True
    ...
```

**`fetch_rows` 循环外算一次聚合：**

```python
def fetch_rows(self):
    world = getattr(self.game_state, "world", None)
    if world is None or not getattr(world, "factions", None):
        return []
    node_counts = world.count_nodes_by_owner()
    char_counts = world.count_characters_by_faction()
    return [
        FactionRow.from_faction(
            f, world,
            node_count=node_counts.get(f.id, 0),
            char_count=char_counts.get(f.id, 0),
        )
        for f in world.factions.values()
    ]
```

**`COLUMNS`（模块级，7 列）：**

```python
COLUMNS = (
    Column("ruler",    "君主", 70, "center", lambda r: r.ruler_name),
    Column("prestige", "威望", 60, "e", lambda r: f"{r.prestige:,}", sort_numeric=True),
    Column("gold",     "金",   60, "e", lambda r: f"{r.gold:,}",     sort_numeric=True),
    Column("food",     "粮",   70, "e", lambda r: f"{r.food:,}",     sort_numeric=True),
    Column("nodes",    "据点", 55, "e", lambda r: str(r.node_count), sort_numeric=True),
    Column("chars",    "人物", 55, "e", lambda r: str(r.char_count), sort_numeric=True),
    Column("stance",   "关系", 50, "center", lambda r: r.stance_text),
)
```

### 5.23 `game/ui/panels/list/`（第十五轮框架）

通用列表面板框架，核心 `GenericListPanel`（`panel.py`），分工见 §2.1：

- **构建 UI**：搜索框 + 分组条 + Treeview + 滚动条（`_build_ui`）
- **调度**：排序（`_on_heading_click`）、分组（`_build_groups`）、搜索（`_apply_search`）
- **右键**：`_on_right_click` 拼 `MenuContext` → `context_menu_items` 配置 → `build_menu` 弹出
- **多选**：`extended` + `_on_select_all`（Ctrl+A）
- **双向定位**：`scroll_to_row`（展开祖先 + 滚动 + 选中）、`locate_on_map`（默认 `node_id/coords`）
- **列配置（第十六轮）**：`_resolve_columns()` / `reload_columns()` / `_build_tree_in()`

### 5.24 其它

`faction.py` / `game_state.py` / `utils.py` / `node.py` / `territory.py` / `viewport.py` / `top_bar.py` / `status_bar.py` / `window_utils.py` / `collapsible.py` / `constants.py` 未改动。

### 5.25 新增/改动函数（第十六轮）

**`game/core/world.py`**

见 §3.5。

**`game/ui/panels/list/panel.py`**

| 函数 | 作用 |
|---|---|
| `_resolve_columns()` | 读 `PANEL_COLUMNS[PANEL_KEY]` → `(可见列 tuple, NAME_COLUMN)`。order 未列的 key 追加末尾；hidden 过滤；NAME_COLUMN 锁定必显；无 `PANEL_KEY` 退化为原 `COLUMNS` |
| `reload_columns()` | 设置保存后由 `MainWindow` 调用：重解析 + 重建 Treeview + `refresh`。若排序键已被隐藏则清除排序状态 |
| `_build_tree_in(body)` | 从原 `_build_ui` 抽出，Treeview 及滚动条构建。可被 `reload_columns` 复用。末尾走 `_configure_tags` hook |

三处 `self.COLUMNS` → `self._visible_columns`：`_match_one` / `_column_index` / `_insert_row`。

**`game/ui/panels/{node,character,faction,troop}_panel.py`**

- 各加 `PANEL_KEY = "node" / "character" / "faction" / "troop"`
- `faction_panel` 补回 `COLUMNS = COLUMNS`（见 §8.3 第 141 条）
- `character_panel` 的 `NAME_COLUMN` 改为 `lambda r: r.name`（去表字）

**`game/ui/side_panel.py`**

```python
def reload_panel_columns(self):
    """遍历 panels 字典，逐个调 reload_columns()。"""
    panels = getattr(self, "panels", None) or {}
    for p in panels.values():
        hook = getattr(p, "reload_columns", None)
        if callable(hook):
            try:
                hook()
            except Exception:
                pass
```

**`game/config/settings_schema.py`**

- `TABS` 加 `{"key": "panels", "title": "面板列"}`（位于 operation 与 game 之间）
- `PANEL_KEYS = ("node", "character", "faction", "troop")`
- `PANEL_TITLES = {"node": "据点", "character": "人物", "faction": "势力", "troop": "部队"}`
- `get_panel_columns_meta()`：延迟导入 4 个 panel 类，返回 `{panel_key: [(col_key, title), ...]}`；NAME_COLUMN 不返回

**`game/ui/settings_window.py`**

新增 8 个方法：

| 函数 | 作用 |
|---|---|
| `_populate_panel_columns()` | 构建「面板列」tab：4 个 `CollapsibleSection`，每个含 Listbox + 按钮组 |
| `_init_panel_state(k, cols)` | 读 `settings.current` 的 order/hidden，套到声明列上，得 `[(key, title, visible), ...]` |
| `_build_panel_columns_ui(parent, k)` | Listbox + 上移/下移/显示隐藏/全部显示 四按钮 |
| `_render_panel_listbox(k)` | 重绘 Listbox + 同步 draft |
| `_panel_move(k, delta)` | 上移 / 下移 |
| `_panel_toggle(k)` | 切换显示 / 隐藏 |
| `_panel_show_all(k)` | 一键全显 |
| `_reset_panel_columns(k)` | 恢复声明顺序 + 全显示 |

`_populate` 加两处：跳过 panels tab 的空占位；末尾调 `_populate_panel_columns()`。`_on_reset_all` 同步重置面板列 state。

### 5.26 ★ `game/ui/character_info_window.py`（第十六轮新增）

```python
class CharacterInfoWindow(tk.Toplevel):
    """人物情报窗口。当前只显示头像。"""
    MAX_W = 200
    MAX_H = 200

    def __init__(self, master, character, font_family="TkDefaultFont"):
        # title = f"{character.display_name()} — 人物情报"
        # 名字 Label + 200×200 头像框
        # 加载头像 → update_idletasks → center_on_parent → grab_set
        # Escape 关闭

    def _find_portrait_path(self):
        """拼 assets/portrait/{id}-{name}.{ext}，遍历扩展名。无 → None。"""

    def _load_portrait(self):
        """Pillow 打开 → convert("RGB") → thumbnail((200,200), LANCZOS)
           → ImageTk.PhotoImage → self._photo 保引用。
           缺图 / 无 Pillow / 加载失败 → Label 显示文字提示。"""
```

**关键点**：

- **`self._photo` 保引用**：Tk 不持 `PhotoImage` 引用，不存 → GC 后显示空白（§8.3 第 139 条同类坑）
- **Pillow 缺失降级**：`try: from PIL import Image, ImageTk` 失败 → `_PIL_OK = False` → Label 提示"未安装 Pillow"
- **`thumbnail` 而非 `resize`**：保比例，只缩不放（小图不放大）
- **RGB 转换**：`Image.open(path).convert("RGB")` —— PNG 带 alpha / 灰度图不会炸
- **`update_idletasks` 后再居中**：让 `winfo_reqwidth/height` 拿到实际尺寸

### 5.27 ★ `tools/check_portraits.py`（第十六轮新增）

只读对账工具。**精确匹配**（图片 stem == `Character.name`），不做简繁 / 表字 / 模糊。输出三张表：

1. **有数据但没头像**：`姓名 + id`
2. **有头像但数据里没有**：`文件名 + 实际文件`
3. **附：数据里重名**：同名多人，一张图无法区分

`load_characters` 兼容 `{id: {...}}` / `{"characters": {...}}` / `[...]` 三种结构。

### 5.28 ★ `tools/rename_portraits.py`（第十六轮新增）

批量重命名 `{id}-{name}.{ext}`。**顶部常量控制开关**：

```python
APPLY = False            # False = dry-run；True = 执行
REMOVE_ORIGINAL = False  # 重名复制后是否删原图
FORCE = False            # 目标已存在时是否覆盖
```

行为表：

| 场景 | 处理 |
|---|---|
| `蔡瑁.jpg`，数据唯一 | **重命名** → `0088-蔡瑁.jpg` |
| `张南.jpg`，数据两人 | **复制** 2 份 → `0651-张南.jpg`、`0652-张南.jpg`；原文件保留（`REMOVE_ORIGINAL=False`） |
| 数据里无此人 | **不动**，归入"未匹配" |
| 已是 `{id}-{name}` 格式 | **跳过**（stem 匹配不上人名，归入"未匹配-不动"） |

---

### 5.29 ★ `game/config/logging_setup.py`（第十八轮新增）

```python
setup_logging() -> Path          # 初始化，返回本次会话的 log 文件路径
install_sys_excepthook()         # 未捕获异常 → CRITICAL + traceback
install_tk_excepthook(root)      # tkinter 回调异常 → ERROR + traceback
get_session_id() -> str          # 8 位十六进制
get_log_file_path() -> Path|None
_cleanup_old_logs(log_dir)       # 只保留最近 _MAX_LOG_FILES 个
class _SessionFilter             # 给每条 record 注入 record.session
```

**关键点**：

- **只挂 `FileHandler`**：不挂 `StreamHandler`，控制台完全静默
- **`_SessionFilter` 挂 handler**：`handler.addFilter(...)`，不是 `logger.addFilter(...)`
- **`install_tk_excepthook` 覆盖 `Tk.report_callback_exception`**：`sys.excepthook` 接不到 tk 回调异常
- **安装顺序**：`setup_logging()` → `install_sys_excepthook()` → `MainWindow()`；tk hook 在 `Tk()` 之后立即
- **`KeyboardInterrupt` 交回原生**：`sys.__excepthook__`，不吞 Ctrl+C

### 5.30 第十七 / 十八轮改动一览（§5.1–5.24 的增量）

| 模块 | 增量 |
|---|---|
| `core/faction.py` | `gold/food` → property（`_nodes_ref`）+ `from_dict` / `to_dict` |
| `core/node.py` | `to_dict()`（写全 7 字段） |
| `core/world.py` | `bind_factions` / `add_faction`(phase2) / `character_id_range` |
| `core/scenario.py` | `_build_faction` 简化；`from_dict` 末尾 `bind_factions`；`_apply_node_overrides` 补静态字段 |
| `core/edit_session.py` | ★ 新增：Command / CompositeCommand / EditSession |
| `core/edit_commands.py` | ★ 新增：NodeEditCommand / FactionEditCommand |
| `core/scenario_writer.py` | ★ 新增：serialize / diff / save |
| `ui/dialogs/` | ★ 新增：field_spec / edit_dialog / node_fields / faction_fields / node_edit |
| `ui/panels/list/context_menu.py` | `MenuItem.edit` 标识 + `build_menu(edit_enabled=)` |
| `ui/panels/list/panel.py` | `edit_session` 类属性 + `_open_dialog` / `_notify_edit` |
| `ui/top_bar.py` | 文件/编辑菜单 + `_add_edit_command` / `set_edit_enabled` / `set_game_mode` |
| `ui/main_window.py` | 菜单动作 / 快捷键 / 编辑会话 / 未保存拦截 / 保存 / 另存为 / 地图右键编辑 |
| `ui/side_panel.py` | `set_edit_session` / `on_panel_edit` / `open_edit_dialog` |
| `map/renderer.py` | `_effective_level`（县点 level 优先取 World） |
| `config/logging_setup.py` | ★ 新增（§5.29） |

---

## 6. 程序完整运行流程

### 6.1 启动阶段（第十八轮更新）

```
main.main()
 ├─ setup_logging()                 userdata/logs/app_YYYYMMDD_HHMMSS.log（清旧 + 建新）
 ├─ install_sys_excepthook()        未捕获异常 → CRITICAL
 ├─ logger.info("应用启动…")
 └─ MainWindow()
     ├─ install_tk_excepthook(root) ★ 紧跟 Tk() 之后
     ├─ SettingsManager → apply()   就地写回 style
     ├─ _build_layout()             TopBar + MapCanvas + SidePanel + StatusBar
     │   └─ set_game_mode / set_edit_enabled  按 APP_MODE 切按钮
     ├─ _bind_shortcuts()
     └─ after(120, _auto_load_default)
         ├─ load_geojson(DEFAULT_MAP_PATH, silent=True)
         └─ _load_default_scenario() → _load_scenario(path)
```

**顺序约束**：`setup_logging()` 必须在 `MainWindow()` 之前，否则构造期间的日志丢失（§8.3 第 154 条）。

### 6.2 地图 + 剧本加载流程

（同上轮；`_load_scenario` 末尾新增：编辑模式建 `EditSession` + baseline 快照 + `side_panel.set_edit_session`）

### 6.3 剧本生成流程（离线）

（同上轮）

### 6.4 主循环交互

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
| 设置保存 | `_on_settings_applied` → 地图相关则 `map_canvas.redraw()`；`PANEL_COLUMNS*` 则 `side_panel.reload_panel_columns()` |
| 面板列重载 | `side_panel.reload_panel_columns()` → 各 panel `reload_columns()` → `_resolve_columns()` 读 `style.PANEL_COLUMNS` → `_build_tree_in()` + `refresh()` |
| 据点右键 → 定位 | `MenuItem「定位到地图」` → `GenericListPanel.locate_on_map` → `MapController.fit_to_node` |
| 据点右键 → 展开/折叠 | `MenuItem「全部展开/折叠」` → `GenericListPanel._toggle_all` |
| 据点列头点击 | `_on_heading_click` → `_sort_key/_sort_desc` → `refresh` |
| 据点分组切换 | `GroupBar._toggle` → `on_change` → `NodePanel.refresh` |
| 人物列头点击 | `_on_heading_click` → `refresh` |
| 人物右键 → 定位到据点 | `MenuItem「定位到据点」` → `GenericListPanel.locate_on_map` |
| **人物右键 → 人物情报** | **`CharacterPanel._open_info_window(row)` → `world.character(row.id)` → `CharacterInfoWindow(self, ch, ...)`** |
| **人物情报窗口加载头像** | **`_find_portrait_path()` 拼 `{id}-{name}.{ext}` → `Image.open → convert("RGB") → thumbnail → ImageTk.PhotoImage → self._photo 保引用`** |
| 人物分组切换 | `GroupBar._toggle` → `on_change` → `CharacterPanel.refresh` → `priority_name` 玩家置顶 |
| 搜索输入 | `SearchBar._on_write` → `_on_search_change` → `refresh` |
| 左键点选 | `_on_release`（位移≤4px）→ `_handle_click` → `renderer.set_selected` |
| hover 高亮 | `_process_motion` → `renderer.set_hover` → `_redraw_hover`（吃 5 开关） |
| hover tooltip | `_process_motion` → `_location_callback` → `MainWindow._on_location_change` → `_update_tooltip` |
| 地图右键（县上） | `MapCanvas._on_right_click` → `MainWindow._on_map_right_click` → `_build_node_context_menu` |
| 地图右键（空白） | `_on_map_right_click(node_id=None)` → `_build_empty_context_menu` |
| 反向定位 | 右键「定位到列表→据点」→ `_locate_to_list` → `side_panel.select_panel` → `NodePanel.scroll_to_row` |
| 设置 → 面板列 | 设置窗口 panels tab → Listbox 上移/下移/显示隐藏 → 「保存」→ `settings.save/apply` → `on_applied` → `_on_settings_applied` → `side_panel.reload_panel_columns` → 各 panel `reload_columns` |
| **据点右键 → 编辑** | `NodePanel._edit` → `dialogs.node_edit.edit_node` → `EditDialog` → `dlg.get_changed()` → 郡治互斥（可选）→ `edit_session.execute(cmd)` → `_notify_edit` |
| **地图右键 → 编辑据点** | `_edit_node_from_map(node_id)` → **同一个 `edit_node`** → `session.execute` → `side_panel.refresh_all()` + `on_edit_executed()` |
| ↳ 编辑后刷新 | `SidePanel.on_panel_edit()` → `refresh_all()`（4 面板）→ `_edit_callback` → `MainWindow.on_edit_executed()` → `_sync_undo_redo_state()` + `_redraw_map()` |
| **Ctrl+Z / Ctrl+Shift+Z** | `_on_undo/_on_redo`（`_modal_open` 时直接 return）→ `edit_session.undo/redo` → `refresh_all` + `_sync_undo_redo_state` + `_redraw_map` |
| **Ctrl+S / Ctrl+Shift+S** | `_on_save_scenario`（无改动 → 状态栏提示，不写文件）→ `_save_to_path` → `ScenarioWriter.save(world, path, raw, baseline)` → `rebase` + `clear` |
| **关窗 / 选择剧本拦截** | `_confirm_discard()` → `edit_session.is_dirty()` → `askyesnocancel` → 非 `True` 则中止 |
| **编辑入口置灰** | `TopBar.set_edit_enabled(editable)` 批量控菜单项；右键 `MenuItem(edit=True)` → `build_menu(edit_enabled=edit_session is not None)` |

### 6.5 模块协作关系

```
main.py ── config.logging_setup（setup_logging / sys hook）
   │
   └─ ui.main_window ──┬─ config.settings_manager ─ config.style
                       │                            └ config.settings_schema
                       │                                 └ get_panel_columns_meta()
                       ├─ core.game_state
                       ├─ core.scenario ─── core.world ─── core.faction
                       │                    ├─ core.character
                       │                    └─ core.node
                       │                    └─ count_nodes_by_owner / count_characters_by_faction
                       ├─ core.edit_session ─── core.edit_commands
                       ├─ core.scenario_writer（serialize / diff / save）
                       ├─ ui.top_bar
                       ├─ ui.status_bar
                       ├─ ui.map_canvas ─── map.viewport
                       │                   map.renderer ─── map.geo_data
                       │                                  └ core.territory（保留）
                       │   hover 回调 → MainWindow._on_location_change
                       │   右键回调 → MainWindow._on_map_right_click
                       │                └─ _edit_node_from_map → dialogs.node_edit
                       ├─ ui.map_controller
                       ├─ ui.settings_window ──── config.settings_schema
                       │                       └─ ui.widgets.collapsible
                       ├─ ui.character_info_window ──── Pillow（Image / ImageTk）
                       │                            └─ ui.window_utils.center_on_parent
                       └─ ui.side_panel ──── panels.faction_panel ──┐
                                          ├─ panels.node_panel ─────┤
                                          │   └─ dialogs.node_edit ─┤─ dialogs.edit_dialog
                                          │                         │  └─ dialogs.field_spec
                                          │                         │     + node_fields / faction_fields
                                          ├─ panels.character_panel ┤── panels.list（通用框架）
                                          │   └─ ui.character_info_window
                                          └─ panels.troop_panel ────┘
                                          └─ reload_panel_columns()
                       config.constants
                       config.logging_setup ──── userdata/logs/*.log
tools.build_characters    ──── assets/characters.json
tools.build_scenario_190  ──── scenarios/default.json
tools.check_portraits     ──── 报告（只读）
tools.rename_portraits    ──── assets/portrait/*.{jpg,png,...}
```

**编辑链路（第十七轮）**：面板/地图右键 → `dialogs.node_edit.edit_node` → `EditDialog`（数据驱动）→ `Command` → **`EditSession.execute`** → 面板刷新 + 地图重绘。
**UI 层不得直接改 World**，一切经 Command（§10.1 硬约束）。

**日志（第十八轮）**：所有模块 `logger = logging.getLogger(__name__)`，根 logger 只挂一个 `FileHandler`（`userdata/logs/`）。

---

## 7. 全局变量与配置项

### 7.1 `constants.py`

（路径常量同上轮）**第十七 / 十八轮追加**：

```python
# 应用模式（第十七轮）
MODE_EDIT = "edit"     # 剧本编辑模式
MODE_GAME = "game"     # 游戏模式（本轮不实现）
APP_MODE  = MODE_EDIT  # 全局开关：编译期切换

# 日志（第十八轮）
LOG_DIR = PROJECT_ROOT / "userdata" / "logs"
```

**`APP_MODE` 只被 `MainWindow.__init__` 读一次**（`self.editable`），其余模块读 `edit_session is not None`（§8.3 第 151 条 / D9）。

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
| **势力色块尺寸** | **`行高 − 6`** | 动态计算（`_compute_swatch_size`，最小 8） |
| **势力色块黑边** | **`1 px`** | `img.put("#000000", to=(0,0,size,size))` |
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
| **`PANEL_COLUMNS` 默认** | `{order:[], hidden:[]}` × 4 panel | 空 = 用 COLUMNS 声明顺序 + 全显示 |
| **面板列配置 tab** | `TABS` 里 key=`panels` | 位于「操作」与「游戏」之间 |
| **面板列 UI** | Listbox + 上移/下移/显示隐藏 | 双击 = 切换显隐 |
| **头像目录** | `assets/portrait/` | 第十六轮 |
| **头像命名** | `{id}-{name}.{ext}` | 第十六轮 |
| **头像扩展名** | `.jpg/.jpeg/.png/.gif/.bmp/.webp` | `PORTRAIT_EXTS` |
| **头像缩放上限** | `200 × 200` | `CharacterInfoWindow.MAX_W/MAX_H` |
| **头像重采样** | `Image.LANCZOS` | 高质量缩略 |
| **`rename_portraits.py` 默认** | `APPLY=False / REMOVE_ORIGINAL=False / FORCE=False` | 三开关全保守 |
| **`APP_MODE` 默认** | `MODE_EDIT`（= `"edit"`） | 第十七轮：编译期切换（§1.1） |
| **`EditSession.max_depth`** | `5` | undo 栈深度，超出裁剪最旧命令 |
| **`character_id_range`** | 第十七轮起 `world.character_id_range` | 由 `ScenarioLoader` 从 raw 读入（供 serialize 回写） |
| **`ScenarioWriter` 元字段** | version/id/name/desc/start/player_faction/character_id_range | 不参与 diff |
| **日志目录** | `userdata/logs/` | 第十八轮：`constants.LOG_DIR` |
| **日志文件名** | `app_YYYYMMDD_HHMMSS.log` | 秒级唯一，每次启动一个 |
| **`_MAX_LOG_FILES`** | `30` | 超出删最旧（`_cleanup_old_logs`） |
| **日志级别** | 文件 `DEBUG`；**无控制台 handler** | 只挂 `FileHandler`，终端静默 |
| **日志格式** | `时间.毫秒 [级别] [session] 模块: 消息` | `%(asctime)s.%(msecs)03d ...` |
| **session id** | 8 位十六进制 | `uuid.uuid4().hex[:8]` |
| **日志保留时间格式** | `%Y-%m-%d %H:%M:%S` | `Formatter(datefmt=...)` |
| **`install_tk_excepthook` 时机** | `Tk()` 之后立即 | 越早越好，构造期回调异常才抓得到 |

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
| 人物面板右键「人物情报」 | **已接入（第十六轮）** |
| **人物情报窗口内容** | **只显示头像 + 名字，五维 / 关系 / 生平未做** |
| 人物头像加载 | **已实现（第十六轮，Pillow）** |
| 人物面板状态持久化 | 不支持 |
| `Character.location` 运行时变更 | 未实现（字段已存，无逻辑） |
| `Character.node` 归属变更 | 未实现 |
| 人物面板势力分组顺序可调 | 未实现（目前仅玩家置顶 + 其余字典序） |
| hover 近邻兜底显示势力 | 未实现（见 §8.3 第 135 条） |
| 势力色块间距可调 | 未实现（受 ttk 主题控制，不可直接调） |
| 搜索正则 / 跨字段 / 拼音 | 只留 `parse_query` 接口，未实现 |
| **搜索匹配表字** | **姓名列去表字后，搜表字不再命中（第十六轮起）** |
| 反向定位（人物 / 势力 / 部队） | 占位，`state="disabled"` |
| region 高亮州面 | 只做郡面（基础版），州面 MultiPolygon 未做 |
| 地图情报三项右键 | 占位，只 `print` |
| 面板列拖拽排序 | 只做 Listbox + 上移/下移 |
| 面板列宽 / 排序状态持久化 | 不支持（列宽由 `Column.width` 决定） |
| NAME_COLUMN 可配置 | 锁定必显，不参与配置 |
| **`Character.portrait` 字段清理** | **保留但不再消费（§9.16）** |
| **头像缺图提示** | **只显示"（无头像）"，无占位图** |
| **人物情报窗口多实例控制** | **无——重复右键会弹多个窗口** |
| 据点 `owner` 编辑 + 级联 | 推迟到 phase2（§0.2 方案 C 范围） |
| 势力新建 / 删除 / 消亡 | 推迟到 phase2（`World.add_faction` 等为 `NotImplementedError`） |
| 人物编辑 | 未做（弹窗骨架已就绪，未接 `CHARACTER_FIELDS`） |
| `GameState.change_gold/food` | 未适配派生值（编辑模式不跑回合，标记 `TODO(phase3)`） |
| **设置窗口「日志」入口** | **本轮只做后端，无 UI（§9.18）** |
| 日志级别 / 保留数量配置化 | 不支持（`_MAX_LOG_FILES = 30` 硬编码） |

### 8.2 数据层缺失

（同上轮）

### 8.3 逻辑与性能限制

（承接前几轮）

**119–133.**（同上轮）

**134. `_city_index` 从 3 元组改 4 元组，任何解包处必须同步**：
- 现在 `(bbox, 县名, ring, 县 id)`
- 已改：`_build_city_index` / `find_city_at` / `_find_city_with_id`
- 若将来新增遍历处，务必 4 元组解包

**135. hover 兜底不返回 `node_id`**：
- `find_location_detail` 里，如果 `_find_city_with_id` 未命中多边形，回落到 `find_nearest_label` → 只有县名，无 id
- 结果：近邻兜底时**不显示势力名**

**136. `MapCanvas` 与 `World` 解耦**：
- `MapCanvas` 只输出地理信息 dict（state / county / city / node_id / lon / lat）
- 势力名由 `MainWindow._on_location_change` 拼装
- **不要**给 `MapCanvas` 塞 `World` 引用

**137. 势力色块大小必须动态计算**：
- 不能硬编码（不同系统 ttk 行高不同）
- `_compute_swatch_size` 优先读 `Style.lookup("Treeview", "rowheight")`，退化到 `TkDefaultFont.metrics("linespace") + 6`
- 色块 = 行高 − 2

**138. `PhotoImage` 必须显式填整块**：
- `img.put(color)` 单色字符串在部分 Tk 版本只填左上角一个像素
- **必须** `img.put(color, to=(0, 0, size, size))`

**139. `PhotoImage` 必须保引用**：
- `FactionPanel._swatches` 缓存
- `CharacterInfoWindow._photo` 属性
- **Tk 不持 `PhotoImage` 引用**，不存 → GC 后显示空白
- 每次 `refresh` / 每次开窗，先 `clear()` 再重建

**140. 势力色块带黑边**：
- 先整块填 `#000000`
- 再在 `(1, 1, size-1, size-1)` 填势力色
- 想调边框粗细改 `to` 起点；想调颜色改 `#000000`

**141. ★ 面板的 `COLUMNS` / `NAME_COLUMN` 等类属性必须显式绑定**：
- **框架读的是 `self.COLUMNS`（类属性），不是模块级变量。**
- 只要模块里有 `COLUMNS = (...)`，**类体内必须写 `COLUMNS = COLUMNS`**，否则 `self.COLUMNS` 取到基类默认 `()`，Treeview 只剩 `#0` 列
- 症状：面板只显示名称列 / 势力名一列，其它列全消失
- **`NAME_COLUMN` 之所以没暴露此坑**：`FactionPanel` 在 `__init__` 里设了**实例属性** `self.NAME_COLUMN = Column(...)`，绕过了类属性查找
- **永久约束**：将来重写 / 新增任何 panel，类体内必须显式绑定模块级配置到类属性。已在 `node_panel` / `character_panel` 遵守；`faction_panel` 曾漏写（第十六轮补回）
- **不要**为了"省事"把模块级变量直接改名成类属性——分组复用（如 `GROUP_DIMS` 同时喂 GroupBar 和 build_tree）会失效

**142. ★ 面板列配置必须兼容"用户旧配置 + 框架新列"**：
- 用户在设置窗口调整过列顺序后，`PANEL_COLUMNS[k].order` 被写进 `userdata/settings.json`
- 将来在 `COLUMNS` 里加新列，用户旧配置里没这个 key
- **`_resolve_columns` 的规则**：order 中的 key 优先排前，**未出现的按声明顺序追加到末尾 + 默认显示**
- **不要**把 order 当白名单（否则加列后用户看不到新列）
- **不要**在加载配置时把未知 key 报错（将来列被删除时同理）

**143. ★ Pillow 是唯一的第三方依赖**：
- 只用在 `game/ui/character_info_window.py`
- 加载时 `try: from PIL import Image, ImageTk` → 失败时 `_PIL_OK = False`，窗口降级显示"未安装 Pillow"，不崩
- `requirements.txt` 声明 `Pillow`
- **不要**在 `core/` / `map/` 层引入 Pillow —— 保持数据层无依赖

**144. ★ 头像路径拼 `{id}-{name}`，不读 `portrait` 字段**：
- `Character.portrait` 字段**保留但不再消费**
- 拼路径只用 `ch.id` + `ch.name`，**不含表字**
- 表字（`family_name`）不参与文件名
- 名字含空格 / 特殊字符时需与重命名工具保持一致（工具也按原样拼）

**145. ★ `Image.open` 后必须 `convert("RGB")`**：
- 部分 PNG 带 alpha 通道 → `ImageTk.PhotoImage` 可能不认
- 灰度图 / 调色板图同理
- 统一 `convert("RGB")` 最稳

**146. ★ 缩略用 `thumbnail` 而非 `resize`**：
- `thumbnail` 保比例、只缩不放
- 想固定尺寸、允许放大，才用 `resize`
- 默认"不超过 200×200"，小图原样

**147. ★ 改 World 只走 Command**：
- UI 层（弹窗/面板/菜单）**不得**直接赋值实体字段
- 只能构造 Command → `EditSession.execute()`
- 任何"直接赋值 World 字段"绕过 session 的代码 = bug

**148. ★ baseline_snap 必须在 `bind_factions()` 之后序列化**：
- 否则 `Faction.gold/food` property 尚未注入 nodes 引用，值为 0
- 顺序：`bind_factions` → `serialize` → `EditSession(world, baseline_snap)`

**149. ★ raw 必须保留用于增量写回**：
- `ScenarioWriter.save(world, path, raw, baseline_snap)` 三个参数都要
- `raw` 是加载时的原始 dict，写回时作为模板（保留未改动字段原值）

**150. ★ Ctrl+Shift+S / Ctrl+Shift+Z 的 keysym 必须大写**：
- 正确：`<Control-Shift-S>` / `<Control-Shift-Z>`
- 错误：`<Control-Shift-s>`（小写不触发）

**151. ★ 新增编辑入口必须登记，不得各自写模式判断**：
- **右键菜单**：`MenuItem(..., edit=True)` → 由 `build_menu(edit_enabled=)` 统一置灰，判定 = `edit_session is not None`
- **顶部菜单**：用 `TopBar._add_edit_command()` 加项 → 自动登记进 `_edit_entries`，`set_edit_enabled()` 一键全禁
- **地图右键**（tk.Menu 直建，不走 build_menu）：`state = "normal" if self.editable else "disabled"`
- **不要**在每个新入口里复制 `if APP_MODE == MODE_EDIT`（D9：模式判断只在 `MainWindow`）

**152. ★ 列表/渲染显示「可编辑实体」时必须查 World，不能只读 GeoData**：
- `Node.type/level/is_capital` 来自 `map.geojson`（`GeoData.shapes_point`），但**编辑只改 World 的 Node**
- 渲染端（`renderer._effective_level`）与加载端（`scenario._apply_node_overrides`）**都要以 World 为准**
- 加新的可编辑静态字段时，**三处必须同步**：`Node.to_dict`（写）/ `_apply_node_overrides`（读）/ 渲染或面板（显示）

**153. ★ 日志一律用 `%s` 惰性格式化，禁止 f-string**：
- 正例：`logger.info("加载剧本：%s", path)`
- 反例：`logger.info(f"加载剧本：{path}")`（日志未输出时也白拼字符串）
- 高频路径**不打日志**：`_process_motion` / `find_location_detail` / `_on_location_change` / `draw_full`

**154. ★ 两个异常钩子的安装时机**：
- `setup_logging()` + `install_sys_excepthook()` 必须在 `MainWindow()` **之前**（`main.py` 里）
- `install_tk_excepthook(root)` 必须**紧跟 `Tk()` 之后**（越早越好，构造期的回调异常才抓得到）
- `sys.excepthook` **接不到 tkinter 回调异常**，必须单独覆盖 `Tk.report_callback_exception`

**155. ★ `_SessionFilter` 挂 handler，不挂 logger**：
- `handler.addFilter(_SessionFilter())` —— filter 在 handler 上才会给每条 record 注入 `session`
- 格式化串用 `%(session)s`；挂错地方会导致 `KeyError: 'session'`

### 8.4 建议的下一步

1. **实现"出征 / 调动"**：改 `Character.location`，不动 `node`
2. **`world.characters_at(node_id)` 聚合**（据点面板「人物」列真实数据）
3. **人物情报窗口扩展**：五维条形图 + 关系网络 + 生平
4. **`Character.affinity` 参与势力关系计算**
5. **非首都据点兵/钱/粮细化**
6. **存档系统 / 新游戏流程 / 回合流程**
7. **`type` 赋予玩法差异**
8. **外交入口（改 `stance`）**
9. **接入 `mountains.geojson`**
10. **人工核查 `_ambiguous_names`**（5 组重名）
11. **hover 近邻兜底也返回 node_id**（`find_nearest_label` 加 id 输出）
12. **势力面板组内排序可调**（当前威望降序）
13. **面板列宽持久化**（`PANEL_COLUMNS` 里加 `widths` 字段）
14. **面板列配置支持拖拽**（tkinter 需手写，暂用按钮替代）
15. **人物情报窗口单例化**（同一人物只开一个窗口）
16. **`Character.portrait` 字段清理**（确认无用后从 `from_dict` / `to_dict` 移除）
17. **搜索匹配扩展到表字**（`_match_one` 加 `family_name` 字段）
18. **据点 `owner` 编辑 + 级联弹窗**（phase2：改 owner → 人物 faction/node/location 联动）
19. **势力新建 / 删除 / 消亡**（phase2：`World.add_faction` / `remove_faction` / `remove_faction_if_empty`）
20. **人物编辑**（复用 §10.6 弹窗骨架，新增 `CharacterEditCommand` + `CHARACTER_FIELDS`）
21. **`GameState.change_gold/food` 适配派生值**（phase3：`Faction.gold` 已无 setter）
22. **编辑弹窗多实例控制 / 滚动**（同一实体只开一个窗口；字段 > 10 时加滚动）
23. **设置窗口「日志」tab**（查看当前日志路径 / 打开目录 / 切换级别）
24. **日志配置化**（`_MAX_LOG_FILES` / 级别 / 是否输出控制台，从 `userdata/settings.json` 读）
25. **`edit_dialog` 字段值实时校验反馈**（当前只有提交时校验，红字提示在按钮栏）

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

- `game/map/geo_data.py` —— `_city_index` 3→4 元组；`find_city_at` 解包改 4 元组；新增 `_find_city_with_id` / `find_location_detail`
- `game/ui/map_canvas.py` —— `_process_motion` 传 dict；`_on_leave` 传 `None`
- `game/ui/main_window.py` —— `_on_location_change` 接收 dict 并查 World 拼势力名；新增 `_faction_at`
- `game/ui/panels/faction_panel.py` —— 加色块（`_make_swatch` / `_compute_swatch_size` / `_swatches` 缓存）

#### 设计决策

- **hover 走方案 B（结构化回调）而非 A（给 MapCanvas 塞 World）**：`MapCanvas` 保持纯地图控件
- **`_city_index` 加 id 而非另建新索引**：改动集中
- **色块尺寸动态计算**：不硬编码
- **色块带黑边**：先整块填黑，再在 `(1,1,size-1,size-1)` 填势力色

#### 症状与根因

| 症状 | 根因 |
|---|---|
| 色块只显示 1 个像素 | `img.put(color)` 单色字符串在部分 Tk 版本只填左上角 |
| 色块大小不对 | 硬编码 12 在 Windows 上偏小，Linux 上偏大 |

---

### 9.14 Panel 通用框架 + 地图交互（第十五轮）

#### 需求

1. **Panel 通用框架**：4 个面板共享基础设施
2. **搜索**：实时 / 多词 AND / 保留分组结构
3. **地图交互**：左键点选 + hover 高亮（5 开关）+ 右键菜单
4. **双向定位**：地图 ↔ 列表

#### 改动

**新增**：`panels/list/` 9 文件 + `node_panel.py`
**重写**：`character_panel.py` / `faction_panel.py` / `troop_panel.py`
**删除**：`panels/node/`、`panels/character/` 共 16 文件
**地图层**：`renderer.py` / `map_canvas.py` / `main_window.py` / `side_panel.py`
**配置层**：`style.py`（`MAP_INTERACTION`）/ `settings_manager.py` / `settings_schema.py`

#### 设计决策

- **三个框架扩展点**：`CUSTOM_GROUPING` / `Column.image` / `priority_name()`
- **分组树抽象 `Group`**：`title / children / tags / row_tag`
- **hover 高亮用独立图层 tag**：删旧画新
- **点选不触发业务逻辑**
- **反向定位 `_syncing` 防递归**
- **搜索过滤在分组前**

---

### 9.15 势力面板加列 + 面板列配置（第十六轮前半）

#### 需求

1. **势力面板加列**：据点数、人物数（威望 / 金 / 粮已有）
2. **4 个面板的列顺序 / 显隐可调**：设置窗口新增「面板列」tab
3. **低耦合**：统计进 `World`，配置进 `style`，框架读 `style`，UI 层不碰业务

#### 改动

**数据层**：`core/world.py` —— `count_nodes_by_owner()` / `count_characters_by_faction()`
**配置层**：`style.py`（`PANEL_COLUMNS`）/ `settings_manager.py` / `settings_schema.py`（panels tab + `get_panel_columns_meta`）
**框架层**：`list/panel.py` —— `_resolve_columns()` / `reload_columns()` / `_build_tree_in()`
**面板层**：4 panel 加 `PANEL_KEY`；`faction_panel` 补 `COLUMNS = COLUMNS`；`FactionRow` 加 `node_count` / `char_count`
**UI 层**：`side_panel.py` / `main_window.py` / `settings_window.py`（8 个新方法）

#### 数据流

```
style.PANEL_COLUMNS (默认)
        ↓ settings_manager 加载/保存/apply
userdata/settings.json  ←→  设置窗口「面板列」tab
        ↓ 保存后 on_applied 回调
main_window → side_panel.reload_panel_columns() → 各 panel.reload_columns()
        ↓
GenericListPanel._resolve_columns() 读 style.PANEL_COLUMNS → 重建 Treeview
```

#### 症状与根因

| 症状 | 根因 |
|---|---|
| 势力面板只有势力名一列 | `faction_panel` 类体内**漏写 `COLUMNS = COLUMNS`**，`self.COLUMNS` 取到基类默认 `()`（§8.3 第 141 条） |
| 据点/人物数为 0 | id 类型不一致（str vs int） |
| 设置窗口 panels tab 空白 | `schema.TABS` 未加 `panels`，或 `get_panel_columns_meta` 导入失败 |
| 改动列配置保存后面板无变化 | `_on_settings_applied` 未接 `PANEL_COLUMNS*` 分支 |

#### 待办

- 面板列不支持拖拽排序
- 列宽 / 分组 / 排序状态未持久化
- `NAME_COLUMN` 不可配置

---

### 9.16 人物情报窗口 + 头像资产规范化（第十六轮后半）

#### 需求

1. **对账头像与人物数据**：找出"缺头像的人"和"孤儿图片"
2. **头像文件重命名**：`{id}-{name}.{ext}`，重名武将复制多份
3. **人物面板右键「人物情报」**：打开居中的头像窗口
4. **人物面板姓名列去表字**：只显示姓名

#### 改动

**新增**：
- `tools/check_portraits.py` —— 对账（只读，输出三张表）
- `tools/rename_portraits.py` —— 批量改名（dry-run + 顶部常量开关）
- `game/ui/character_info_window.py` —— 人物情报窗口（Pillow 头像）
- `requirements.txt` —— 声明 `Pillow`

**修改**：
- `game/ui/panels/character_panel.py` —— 右键「人物情报」接入窗口；`NAME_COLUMN` 改 `lambda r: r.name`（去表字）

**未改动**：
- `Character` 类（`portrait` 字段保留但不再消费）
- 其它面板 / 地图层 / 数据层

#### 设计决策

- **引入 Pillow**：tkinter 原生不支持 JPG；Pillow 后续还要用于立绘 / 缩放 / 裁剪，早引入划算
- **只用在 UI 层**：`core/` / `map/` 保持零第三方依赖
- **降级不崩**：`try: import PIL` 失败 → `_PIL_OK = False` → 窗口显示"未安装 Pillow"
- **头像路径拼 `{id}-{name}`，不读 `portrait` 字段**：字段保留兼容，逻辑已切换
- **名字只用 `ch.name`，不含表字**：文件名 = `0651-张南.jpg`，不是 `0651-张南（XX）.jpg`
- **`Image.open().convert("RGB")`**：兼容 PNG alpha / 灰度
- **`thumbnail` 而非 `resize`**：保比例、只缩不放
- **`self._photo` 保引用**：Tk 不持 `PhotoImage` 引用，不存 → GC 后空白（§8.3 第 139 条同类坑）
- **`update_idletasks` 后再 `center_on_parent`**：让 `winfo_reqwidth/height` 拿到实际尺寸
- **`rename_portraits.py` 用顶部常量控制**：`APPLY / REMOVE_ORIGINAL / FORCE`，比 `--apply` 命令行参数更直观
- **对账脚本不做模糊匹配**：简繁 / 表字 / 异体全交给人工（用户明确要求）

#### 症状与根因

| 症状 | 根因 |
|---|---|
| 头像窗口显示空白 | `PhotoImage` 未保引用，GC 回收（§8.3 第 139 条） |
| 头像窗口报 `unknown file type` | tkinter 原生不支持 JPG，必须走 Pillow 中转 |
| 部分 PNG 头像加载失败 | PNG 带 alpha / 调色板，需 `convert("RGB")` |
| 重命名脚本"未匹配"一大堆 | 名字写法不一致（简繁 / 异体 / 表字），脚本不做模糊，需人工 |
| 重名武将只改出一个文件 | 数据里同名多人，需复制 N 份（`build_plan` 的 `len(ids) > 1` 分支） |

#### 待办（本轮明确记录）

- 人物情报窗口只显示头像 + 名字，五维 / 关系 / 生平未做
- 窗口非单例，重复右键弹多个
- 缺头像只显示"（无头像）"，无占位图
- `Character.portrait` 字段保留但不再消费，将来确认无用后清理
- 姓名列去表字后，搜表字不再命中（`_match_one` 未扩展）
- 右键菜单标题仍带表字（`row.display_name`），未统一

---

### 9.17 剧本编辑器（第一阶段 · 瘦身版）（第十七轮）

#### 需求

1. **模式切换**：`APP_MODE` 编译期切换，编辑模式禁用「进行」/ 回合推进
2. **菜单栏**：新增「文件」「编辑」两个 Menubutton（沿用现有风格，不改原生 menubar）
3. **据点编辑**：静态字段（`type / level / is_capital / troops / gold / food`）+ 郡治互斥
4. **势力编辑**：静态字段（`name / color / prestige / stance`），`gold / food` 只读
5. **通用 undo / redo 框架**：Command / CompositeCommand / EditSession（`max_depth=5`）
6. **增量保存**：`raw 原样 + diff 增量`，未改动字段不出现
7. **`Faction.gold / food` 派生值化**：名下据点求和，不落盘
8. **编辑类按钮统一标识**（追加）：代码中标记编辑入口，切 `APP_MODE` 时一键全禁
9. **地图右键「编辑据点」**（追加）：与面板右键共用同一套编辑流程（含郡治互斥）

#### 改动

**新增（13 个）**：
- `game/core/edit_session.py` —— Command / CompositeCommand / EditSession
- `game/core/edit_commands.py` —— NodeEditCommand / FactionEditCommand
- `game/core/scenario_writer.py` —— serialize / diff / save（增量）
- `game/ui/dialogs/` —— field_spec（Field NamedTuple）/ edit_dialog / node_fields / faction_fields
- `game/ui/dialogs/node_edit.py` —— ★ 据点编辑共用流程（面板右键 / 地图右键）
- `tests/` —— test_composite_command / test_scenario_writer

**修改（15 个）**：
- `constants.py`（MODE_EDIT / MODE_GAME / APP_MODE）
- `faction.py`（gold/food → property + `_nodes_ref` + from_dict/to_dict）
- `node.py`（to_dict）/ `world.py`（bind_factions + character_id_range + 3 个 phase2 占位）
- `scenario.py`（_build_faction 简化 + from_dict 末尾 bind + `_apply_node_overrides` 补静态字段）
- `game_state.py`（TODO(phase3) 注释）
- `renderer.py`（`_effective_level`：县点 level 优先取 World 的 Node）
- `top_bar.py`（文件/编辑菜单 + `_add_edit_command` 登记 + `set_edit_enabled` / `set_edit_state` / `set_game_mode`）
- `main_window.py`（菜单动作 / 快捷键 / 编辑会话 / 未保存拦截 / 保存 / 另存为 / 地图右键编辑 / `_redraw_map`）
- `side_panel.py`（set_edit_session / on_panel_edit / open_edit_dialog）
- `list/panel.py`（edit_session 类属性 + _open_dialog / _notify_edit + build_menu 传 edit_enabled）
- `list/context_menu.py`（★ `MenuItem.edit` 标识 + `build_menu(edit_enabled=)`）
- `node_panel.py` / `faction_panel.py`（右键「编辑」+ `edit=True` + _edit 复用 node_edit）
- `build_scenario_190.py` + `scenarios/default.json`（去 factions 的 gold/food）

#### 设计决策

- **Command 模式**：UI 只构造 Command 交给 EditSession.execute，不直接改 World（§10.1 硬约束）
- **双重 baseline（D2）**：`raw`（写回模板）+ `baseline_snap`（diff 基准），与 undo 栈解耦
- **`Faction._nodes_ref` = world.nodes 引用（D1）**：gold/food property 实时求和，owner 变化自动反映
- **数据驱动弹窗（D10）**：Field NamedTuple + kind 分派，无「if 据点 elif 势力」分支
- **增量保存（D4）**：`output = deepcopy(raw) + diff(current, baseline_snap)`，未改动字段不出现
- **`EditSession.max_depth = 5`**：undo 栈深度限制，超出裁剪最旧命令
- **模式判断只在 MainWindow（D9）**：`self.editable`；其余模块读 `edit_session is not None`
- **★ 编辑入口统一标识（需求 8）**：两处，共用「`APP_MODE` 单点决定」原则
  - **右键菜单**：`MenuItem.edit = True`，`build_menu(..., edit_enabled=)` 统一置灰（面板侧判定 = `edit_session is not None`）
  - **顶部菜单**：`TopBar._add_edit_command()` 登记到 `_edit_entries`，`set_edit_enabled()` 一键全禁
  - **地图右键**：构建时 `state = "normal" if self.editable else "disabled"`
  - 新增任何编辑入口 → **只需登记**，不必各自写模式判断
- **★ 据点编辑流程抽到 `dialogs/node_edit.py`（需求 9）**：面板右键与地图右键共用，郡治互斥只写一份

#### 症状与根因

| 症状 | 根因 |
|---|---|
| 势力面板 gold/food 显示 0 | Faction.gold 变 property，必须 `bind_factions()` 注入 nodes 引用后再序列化 baseline |
| `pf.gold = ...` 报错 | property 无 setter（GameState.change_gold/food，标记 TODO(phase3)） |
| Ctrl+Shift+S / Ctrl+Shift+Z 不触发 | Tk keysym 必须大写 `S` / `Z`（`<Control-Shift-S>`） |
| 面板找不到 MainWindow | MainWindow 不是 widget，经 SidePanel 回调转发（`_open_dialog_callback` / `_edit_callback`） |
| 编辑弹窗无「确定」按钮 / 不居中 / 郡治不弹二选一 | ★ 三者同源：`_build_buttons` 把 `pady=(0, 12)` 元组误传给 `tk.Frame()` **构造函数**，Tcl 抛 `bad screen distance` → 按钮未建成、后续居中代码未执行 |
| 改 `type/level/is_capital` 保存后重新加载回原样 | `_apply_node_overrides` 只读 `owner/troops/gold/food`，**漏读三个静态字段**（写入端正常，读取端缺失） |
| 改 `level` 地图县点无变化 | `render_points` / `render_point` 只读 `GeoData.shapes_point` 的 `level`，**从不查 World 的 Node**；且编辑后未触发地图重绘 |

#### 待办（本轮明确记录）

- 据点 `owner` 编辑 + 级联弹窗（phase2）
- 势力新建 / 删除 / 消亡（phase2）
- 人物编辑（复用弹窗骨架，新增 CharacterEditCommand + CHARACTER_FIELDS）
- `GameState.change_gold/food` 适配派生值（phase3）
- 编辑弹窗缺滚动（字段 ≤ 10，暂不需要）
- 面板列宽 / 排序 / 分组状态持久化（沿用 §9.15 待办）

---

#### 手工验证清单

自动化只覆盖核心逻辑，以下交互需实际点一遍（`python main.py` 启动）：

| 操作 | 预期 |
|---|---|
| 据点面板右键 →「编辑」 | 弹窗**居中相对主窗口**，含「确定 / 取消」按钮 |
| ↳ 改 `type / level / 郡治 / 兵力 / 金 / 粮` → 确定 | 面板数据立即变化 |
| ↳ 勾「郡治」且同郡已有郡治 | 弹「二选一」；选「是」→ 旧郡治改非 + 本县郡治（**1 个 undo 单元**）；选「否」→ 整体放弃 |
| ↳ 改 `level` 后 | **地图县点的大小 / 形状随之变化** |
| ↳ `Ctrl+Z` | 完全回滚（含郡治联动） |
| **地图右键（县上）→「编辑据点」** | 弹出同一个编辑弹窗，改动同样生效、同样入 undo 栈 |
| 势力面板右键 →「编辑」 | 弹窗 7 字段；`金 / 粮` 只读显示**派生值**（名下据点求和） |
| ↳ 改势力名 → 确定 | 全局面板刷新，势力名同步 |
| 改任一据点 `金` | 势力面板对应势力的 `金` 实时变化（求和） |
| `Ctrl+S` 无改动 | 状态栏提示「无改动，未保存」，不写文件 |
| `Ctrl+S` 有改动 | 覆盖当前剧本文件；撤销/重做菜单项置灰 |
| `Ctrl+Shift+S` | 弹文件对话框；保存后上下文切到新文件，再 `Ctrl+S` 写新文件 |
| 有改动时关窗口 / 选择剧本 | 弹「放弃改动 / 取消」，取消则中止 |
| 保存后重新打开 | `type / level / is_capital` 等改动**保留** |
| 切换 `APP_MODE = MODE_GAME` | 菜单栏「选择剧本 / 保存 / 另存为 / 撤销 / 重做」、面板与地图右键的「编辑」**全部置灰**；「进行」按钮恢复可用 |

---

**本轮核心变动集中在 §0（新增 7 术语：编辑会话 / Command / 增量保存 / Field / APP_MODE / 编辑类标识 / 据点编辑共用流程）**、**§2（dialogs + edit_session / edit_commands / scenario_writer / node_edit + tests）**、**§3.2（Faction 派生值）/ §3.4（Node.to_dict）/ §3.6（bind_factions）**、**§5（新增 edit_session / edit_commands / scenario_writer / dialogs 四组模块）**、**§7.3（编辑相关常量）**、**§8.3 第 147–152 条（编辑框架永久约束）**、**§8.4 第 18–22 条**、**§9.17**。

---

### 9.18 全流程日志系统（第十八轮）

#### 需求

1. **每次启动一个独立 log 文件**：`userdata/logs/app_YYYYMMDD_HHMMSS.log`
2. **文件级别 DEBUG，控制台不输出**（只挂 `FileHandler`，不挂 `StreamHandler`）
3. **保留最近 30 个** log 文件，超出自动删最旧
4. 每行带 **session id 前缀**（8 位十六进制），区分多次启动
5. **零第三方依赖**：只用标准库 `logging` + `logging.handlers`
6. `core/` / `map/` 允许 `logging.getLogger(__name__)`，保持无第三方依赖
7. 现有占位 `print` 迁移到 `logger.debug`
8. 编辑 / 保存 / undo / redo 用 `INFO`；字段明细用 `DEBUG`
9. **本轮不加设置窗口入口**，只做后端
10. `tools/` 下脚本**保持 `print`**（离线工具，不接入 logging）

#### 改动

**新增（1 个）**：
- `game/config/logging_setup.py` —— `setup_logging` / `install_sys_excepthook` / `install_tk_excepthook` / `_cleanup_old_logs`

**修改（12 个）**：
- `constants.py`（`LOG_DIR`）
- `main.py`（★ 清掉误粘贴的 docstring 段落 + 初始化日志 + sys hook）
- `main_window.py`（★ 紧跟 `Tk()` 装 tk hook + ~30 处日志）
- `map_canvas.py`（~10 处）/ `top_bar.py`（~4 处）/ `side_panel.py`（~6 处，补异常日志）
- `settings_manager.py`（~10 处，`notify` / `apply` 的 `except: pass` 补 `logger.warning`）
- `scenario.py`（~10 处，`print` → `logger.warning`）/ `world.py`（1 处）
- `edit_session.py`（~8 处）/ `scenario_writer.py`（~4 处，`save` 异常补 ERROR）
- `geo_data.py`（~4 处）

#### 设计决策

- **只挂 `FileHandler`**：控制台完全静默，`python main.py` 终端无日志行
- **`_SessionFilter` 注入 session id**：`record.session = _SESSION_ID`，格式化串用 `%(session)s`
- **`%s` 惰性格式化，不用 f-string**：日志未输出时不拼字符串
- **两个异常钩子**：
  - `install_sys_excepthook()` —— `sys.excepthook`，捕获所有未捕获异常（`KeyboardInterrupt` 除外，交回原生）
  - `install_tk_excepthook(root)` —— 覆盖 `Tk.report_callback_exception`，**tkinter 项目最容易漏日志的地方**（回调异常默认只打 stderr，窗口继续跑但行为异常）
- **tk hook 紧跟 `Tk()` 之后安装**：越早越好，避免构造期间的回调异常丢失
- **`setup_logging()` 必须在 `MainWindow()` 之前**：否则构造期间的日志会丢
- **高频路径不打日志**：`_process_motion`（40ms 节流）/ `find_location_detail` / `_on_location_change` / `draw_full` 一律不加
- **`main.py` 的 docstring 误粘贴段落清掉**（历史遗留的对话残片）

#### 日志格式

```
2026-09-25 09:42:24.933 [INFO ] [573b6529] game.ui.main_window: 初始化 MainWindow，APP_MODE=edit
   ↑ 时间戳(毫秒)         ↑级别   ↑session    ↑模块(__name__)        ↑消息
```

#### 症状与根因

| 症状 | 根因 |
|---|---|
| 日志文件不生成 | `setup_logging()` 在 `MainWindow()` 之后调用，构造期日志丢失；或未挂 `FileHandler` |
| 每行缺 session id | `_SessionFilter` 未 `addFilter` 到 handler 上（filter 挂 handler，不是 logger） |
| tkinter 回调异常没进日志 | 必须覆盖 `Tk.report_callback_exception`，`sys.excepthook` 接不到 |
| 日志文件堆积 | `_cleanup_old_logs` 在 `mkdir` 之后、创建新文件之前调用（顺序不能反） |

#### 待办（本轮明确记录）

- 设置窗口「日志」入口未做（本轮只做后端）
- `tools/` 下脚本保持 `print`，不接入 logging
- 日志级别 / 保留数量未做配置化（`_MAX_LOG_FILES = 30` 硬编码）

#### 补充覆盖（§16 清单收尾）

第一轮后补齐了 §16 列出的其余模块：

| 文件 | 日志点 |
|---|---|
| `dialogs/edit_dialog.py` | 构建弹窗 / 确定 / 取消 / 校验失败 / **字段变更明细（旧值→新值）** |
| `dialogs/node_edit.py` | 编辑据点 / **郡治互斥** / 用户放弃互斥 |
| `panels/list/panel.py` | 刷新行数 / 排序 / 反向定位（含失败）/ 重载列 |
| `panels/node_panel.py` | 据点情报（`print` → `logger.debug`）/ 编辑入口 |
| `panels/faction_panel.py` | 编辑势力 / 势力不存在告警 |
| `panels/character_panel.py` | 人物情报 / 复制编号（含失败告警） |
| `ui/settings_window.py` | 保存 N 项 / 恢复默认（含失败告警） |
| `ui/character_info_window.py` | 打开窗口 / 头像路径 / **头像加载失败** / Pillow 缺失 |
| `core/game_state.py` | 同步 World / 推进回合 |
| `map/renderer.py` | 绑定 World（势力数 / 据点数） |

**刻意不加**（高频或纯数据，加日志只会刷屏）：
`viewport.py`（投影/缩放）/ `core/node.py` / `faction.py` / `character.py`（构造 1000+ 次）/ `game/core/utils.py` / `list/context_menu.py` / `settings_schema.py`（纯数据）/ `panels/troop_panel.py`（空壳）/ `renderer.draw_full` 与 `set_hover`（文档 §15.3 明确禁止）。

---

**本轮核心变动集中在 §0（新增 1 术语：日志系统）**、**§2（logging_setup.py + userdata/logs）**、**§8.3 第 153–155 条（日志永久约束）**、**§9.18**。