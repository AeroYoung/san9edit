# 暗耻三国志 — 项目说明文档

三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》。本文档描述**当前代码的实际状态**：数据模型、文件结构、模块职责、运行流程、配置项、已知限制与后续计划。

**阅读建议**：先读 §0 术语表（全文用词统一以它为准）；只想跑起来看 `main.py` 与 §6.1；要改代码看 §2 / §3 / §5；要查配置看 §7；要动编辑功能看 §9 / §10。

---

## 0. 术语表（★ 全文统一，先读这里）

| 中文 | 数据 / 代码里的名字 | 说明 |
|---|---|---|
| 州 | states / shapes_polygon / _state_index / labels_state | 一级行政区，2 位 id |
| 郡 | counties / shapes_line / _county_index / labels_county | 二级行政区，4 位 id |
| 县 = 据点 | cities / shapes_point / shapes_city_boundary / _city_index / labels_city / Node 类 | 三级单元，一个县就是一个据点，6 位 id |
| 县的 type | city["type"] / Node.type | 只有三种：城 / 关隘 / 渡口 |
| 人物 | characters / Character 类 | 四位 id，全局唯一 |
| 基础数据 | assets/characters.json | 1049 人的静态数据（含 49 位穿越人物） |
| 剧本覆盖 | scenarios/*.json 的 characters 段 | 只覆盖 登场 / 势力 / 所属 / 所在 / 身份 |
| 登场 | Character.appeared | ★ 剧本动态字段（bool），「设为登场 / 未登场」开关的对象 |
| 穿越人物 | id ≥ 1001（英布 / 韩信 / 岳飞…） | 全量进 World，appeared = false，可手动设为登场 |
| 所属 | Character.node | 编制上属于哪个据点，运行时不变 |
| 所在 | Character.location | 人现在在哪儿，运行时可变 |
| 染色层 | render_territory 画的县面 | 地图上唯一的着色图层，不吃 LOD |
| 势力色块 | FactionPanel 里势力名前的 ■ | 带黑边，边长 = 行高 − 2 |
| hover 回调契约 | MapCanvas._location_callback(dict \| None) | dict 含 state/county/city/node_id/lon/lat/px/py |
| 选中高亮 | renderer._selected_node_id / SELECT_TAG | 左键点选的县，描边加粗 2px 亮青 |
| hover 高亮层 | renderer._hover_info / HOVER_TAG | 悬停县高亮，受 MAP_INTERACTION 5 开关控制 |
| 反向定位 | GenericListPanel.scroll_to_row(key) | 地图 → 列表：切 Tab + 滚动 + 选中 + 展开组 |
| 据点人物数 | World.count_characters_by_node | ★ 按所属 node 聚合，未登场不计（§3.5） |
| 势力兵力 | Faction.troops | ★ 派生值：名下据点 troops 求和 + 所属部队求和（部队项恒 0，§3.2） |
| 势力兵力口径 | —— | ★ Σ node.troops (owner=本势力) + Σ troop.troops（Troop 未建模，见 §8.4） |
| 面板列配置 | style.PANEL_COLUMNS | 每面板 {order:[], hidden:[]}，见 §5.22 |
| 面板 key | GenericListPanel.PANEL_KEY | 面板在 PANEL_COLUMNS 里的键：node/character/faction/troop |
| 列解析 | GenericListPanel._resolve_columns() | 读 PANEL_COLUMNS → 返回过滤重排后的可见列 |
| 头像路径约定 | assets/portrait/{id}-{name}.{ext} | ★ 不再读 Character.portrait 字段 |
| 头像加载 | CharacterInfoWindow._load_portrait | ★ Pillow 打开 + thumbnail + ImageTk.PhotoImage |
| 人物情报窗口 | CharacterInfoWindow | ★ 右键人物 →「人物情报」弹出的 Toplevel |
| 五维雷达图 | CharacterInfoWindow._build_radar | ★ tkinter Canvas 画，5 轴 5 层同心五边形 |
| 关系链接 | CharacterInfoWindow._link_label | ★ 蓝字可点 → 新开该人物情报窗口 |
| 生平占位 | CharacterInfoWindow._build_bio | ★ 灰色斜体「（生平未收录）」，数据源待定 |
| 主窗口引用 | CharacterInfoWindow._top | ★ master.winfo_toplevel()；居中基准 + 跳转窗口 master |
| 应用模式 | APP_MODE / MODE_EDIT / MODE_GAME | ★ 编译期切换，默认 MODE_EDIT（§7.1） |
| 编辑会话 | EditSession | ★ Command 栈 + baseline + dirty 判定（§10.1） |
| 命令 | Command / CompositeCommand | ★ 改 World 的唯一入口，UI 不直接赋值（§9.1） |
| 增量保存 | ScenarioWriter.save | ★ raw 原样 + diff 增量，未改动不写（§9.3） |
| 字段描述 | Field | ★ 弹窗数据驱动核心，6 种 kind（§9.4） |
| 编辑类标识 | MenuItem.edit / TopBar._edit_entries | ★ 标记编辑入口，按 APP_MODE 一键全禁 |
| 据点编辑共用流程 | dialogs/node_edit.py::edit_node | ★ 面板右键与地图右键共用（含郡治互斥） |
| 势力编辑共用流程 | dialogs/faction_edit.py::edit_faction | ★ 势力面板右键与地图右键共用 |
| 日志系统 | logging_setup.py / LOG_DIR | ★ 每次启动一个文件，DEBUG，保留 30 个（§5.6） |
| 日志总开关 | LOG_ENABLED（constants.py） | ★ 编译期一键关闭全部日志（§5.6）；风格同 APP_MODE |
| session id | logging_setup._SESSION_ID | ★ 8 位十六进制，每行日志前缀，区分多次启动 |
| 异常钩子 | install_sys_excepthook / install_tk_excepthook | ★ 未捕获异常 + tkinter 回调异常统一入日志 |
| 未保存提示 | MainWindow._refresh_title | ★ 编辑后窗口标题追加 " *"，回到 baseline 自动消除 |
| 应用登场状态 | ScenarioLoader._apply_appeared | ★ 第三层：只读 appeared，不删人（§3.6） |
| 登场开关 | CharacterPanel._toggle_appeared | ★ 右键「设为登场 / 未登场」，走 CharacterEditCommand |

**「县 = 据点」的核心约定：**

- 一个县 = 一个据点 = 一个 Node 对象。
- map.geojson 里，一个县就是 states[i].counties[j].cities[k] 的一个元素。
- 每个县必有 coords + boundary + type。
- type 只区分县的形态（城郭 / 关口 / 渡口），不影响数据结构、不区分行政级别。
- 代码里遗留的 city* / *_city_* 命名，语义等于「县 / 据点」，保留。

**「人物」的核心约定：**

- 三层数据：characters.json（静态）+ scenarios/*.json（动态覆盖）+ _apply_appeared（应用登场状态）。
- 关系字段用 id 引用。
- appeared / faction / node / location / role 在基础数据里恒为默认值（appeared=True，其余 null），由剧本填充。
- World.characters 收**全量**人物：未登场的人也在里面，编辑器才能改他们。
- 登场与否只看 appeared；**不消费 death_year**（历史人物可长寿化 / 穿越）。
- 剧本里出现但基础数据没有的人 id → 警告并忽略（不新建）。
- 头像不再走 portrait 字段：直接从 assets/portrait/{id}-{name}.{ext} 拼路径。

**「所属 vs 所在」的核心约定：**

| 概念 | 字段 | 类型 | 含义 | 剧本初始 | 运行时 |
|---|---|---|---|---|---|
| 所属 | Character.node | str \| None | 编制上隶属哪个据点 | = 所在 | 不变（除非归属变更） |
| 所在 | Character.location | str \| None | 人当前在哪个据点 | = 所属 | 随出征 / 调动 / 流亡变化 |

**「穿越人物」约定：**

- 编号 1001–1049 共 49 人。
- 数据保留在 characters.json。
- 默认剧本**全量写进** World.characters，appeared = false、归属字段为 null。
- 不参与势力分配（build_scenario_190 只给 id ≤ 1000 的人分势力）。
- 想让他们登场：人物面板右键「设为登场」。
- `character_id_range` 字段仍保留兼容（老剧本还能按 id 白名单过滤），190 剧本不再写它。

**「染色层」约定：**

- 地图上唯一的着色图层（一县一据点，按 node.owner 上色）。
- 不吃 LOD：只要在视口内且有主，就画。
- 只做视口粗筛（屏幕外跳过），性能足够。
- 无主县不染色，州面底色透出。

**「hover 回调契约」约定：**

- MapCanvas._location_callback(info)，info 是 dict 或 None。
- dict 结构：{"state": 州名, "county": 郡名, "city": 县名, "node_id": 县 id, "lon": float, "lat": float, "px": int, "py": int}
- 鼠标离开画布 → 传 None。
- MapCanvas 不感知 World，由 MainWindow 拿到 dict 后再拼装势力名。

**「头像资产」约定：**

- 头像统一命名 {id}-{name}.{ext}，如 0651-张南.jpg。
- 通过 tools/头像.py 批量重命名 / 对账。
- 运行时拼路径，不读 Character.portrait 字段（该字段保留兼容，不再消费）。
- 同名多人的处理：复制多份，形如 0651-张南.jpg、0652-张南.jpg。

**「人物情报窗口」约定：**

- 居中基准 = **游戏主窗口**（`self._top = master.winfo_toplevel()`），不是右侧面板。
- 窗口宽固定 600，高自适应（`resizable(False, True)`）；最小高 640。
- 内容四区：标题（名字）/ 上区（头像 + 五维雷达图）/ 关系 / 生平（占位）。
- 五维雷达图用 **tkinter Canvas** 画（不用 Pillow，避免跨平台字体文件路径问题）。
- 关系区 8 字段全画；姓名带表字（display_name），不带势力。
- 可点姓名 → 蓝字 + hand2 → 打开新窗口（master = 主窗口）。
- 查不到的人（world 缺失 / 不在 World.characters 里）→ 灰色 "—" 不可点。
- 未登场人物：**标题**追加「（未登场）」（`X — 人物情报（未登场）`）；雷达图 / 关系区不受 appeared 影响。
- 生平区只占位（灰色斜体「（生平未收录）」），数据源待定。
- **不做单例**：重复右键会开多个窗口（已知限制，见 §8.4）。
- world 参数可选（None → 关系区全 "—"，雷达图用主题灰）。

**「剧本编辑」约定：**

- 改 World 只走 Command：UI 构造 Command → EditSession.execute()，不得直接赋值实体字段（§8.3 永久约束）。
- 双重 baseline：raw（写回模板，保留未改动字段原值）+ baseline_snap（diff 基准，加载后立即 serialize）。
- Faction.gold / food / troops 是派生值：名下据点求和，_nodes_ref 是 world.nodes 引用，不落盘、不可赋值。
- 增量保存：output = deepcopy(raw) + diff(current, baseline_snap)，未改动字段不出现。
- 弹窗数据驱动：只认 Field.kind（int/str/bool/choice/color/readonly），不认业务实体。

**「日志开关」约定：**

- LOG_ENABLED 是编译期开关，风格同 APP_MODE，只在 constants.py 里改。
- True：正常建目录 + 写文件 + 挂 2 个异常钩子 + 保留 30 个。
- False：不建目录、不清理旧日志、不挂 FileHandler、不挂任何异常钩子，`logging.disable(CRITICAL)`。
- 关闭时未捕获异常交回 Python / Tk 默认 stderr（不静默吞掉）。

**「未保存提示」约定：**

- 唯一刷新入口：MainWindow._sync_undo_redo_state → _refresh_title。
- 标题格式：`APP_TITLE [- 剧本文件名] [ *]`。
- 编辑 → `*` 出现；undo 回 baseline / 保存 / 加载新剧本 → `*` 消失。
- 不做状态栏提示，不加托盘图标，不闪烁。

**「势力兵力」约定：**

- 口径：名下据点 troops 求和 + 所属部队兵力求和。
- 部队项恒为 0（Troop 模型未建，见 §8.4）。
- Faction.troops 是派生 property：无 setter、不落盘、不可直接赋值。
- _troops_ref 不建（没有 Troop 容器可注入）。
- 展示落点：势力面板「兵力」列 + 势力编辑弹窗只读行。

---

## 1. 项目概述

| 项 | 内容 |
|---|---|
| 项目名称 | 暗耻三国志（APP_TITLE） |
| 定位 | 三国类回合制策略游戏原型，玩法参照光荣《三国志 IX》 |
| 程序入口 | main.py → MainWindow().run() |
| 核心功能 | 中国全图矢量渲染 + 缩放平移 + 光标精确反查州 / 郡 / 县 / 势力；旬回合时钟 + 顶部信息栏 / 菜单；右侧 4 Tab 面板（势力 / 据点 / 人物 / 部队）+ 通用列表框架（排序 / 嵌套分组 / 搜索 / 右键 / 双向定位）+ 面板列可配置；人物情报窗口（Pillow 头像 + 五维雷达图 + 关系）；设置窗口；剧本系统 + 剧本编辑（据点 / 势力 / 人物登场 + undo/redo + 增量保存）；全流程日志 |
| 运行环境 | Python 3 + 标准库 tkinter + Pillow（第三方，仅人物情报窗口的头像用；雷达图/关系区纯 Canvas/Widget） |
| 数据来源 | assets/map.geojson：13 州 / 106 郡 / **1152 县**；roads.geojson；water.geojson；mountains.geojson（未接入）；characters.json：1049 人；assets/portrait/：739 张头像 |
| 剧本来源 | scenarios/default.json（190 年 · 十八路诸侯；52 势力 / 1049 人物全覆盖（登场 469）/ 555 据点） |
| 用户数据 | userdata/settings.json；userdata/logs/ |

**当前完成度（粗粒度）：**

- ✅ 地图 / 渲染：州郡县三级边界 + 道路 + 水域 + 图层显隐 + 县名避让；县面势力染色（唯一着色图层，不吃 LOD）；县点选 + hover 高亮（5 开关）；地图 ⇄ 列表双向定位；精确反查州 · 郡 · 县 · 势力
- ✅ 面板：4 面板共享 panels/list/ 框架（列 / 排序 / 嵌套分组 / 搜索 / 多选 / 右键菜单）+ 列顺序与显隐可配置；势力色块；兵力 / 据点数 / 人物数三列现算（兵力是派生值不落盘，人物数未登场不计）；据点面板「主官」列与据点情报三项右键仍是占位
- ✅ 人物情报窗口：Pillow 头像 + Canvas 五维雷达图 + 关系区（8 字段，可点击跳转）+ 生平占位
- ✅ 剧本系统：characters.json 1049 人（31 字段，含 node / location 分离）+ 190 剧本（52 势力 / 1049 人物 / 555 据点）+ 三层加载 + character_id_range 仅老剧本兼容
- ✅ 剧本编辑：APP_MODE 编译期切换 + 据点 / 势力编辑（共用流程 + 郡治互斥）+ 人物登场开关 + undo/redo + 增量保存 + 未保存提示；编辑入口统一标识（edit=True / set_edit_enabled）
- ✅ 设置窗口：主题 / 地图样式 / 图层 / 面板列 多 Tab
- ✅ 日志：会话文件 + session id + sys/tk 异常钩子 + LOG_ENABLED 编译期总开关
- ⚠️ 骨架：回合与资源；设置窗口「游戏」tab
- ❌ 空实现：内政 / 军事 / 外交 / 存档 / 读档 / 新游戏 / 部队面板与 Troop 模型

---

## 2. 文件结构清单

```text
san9edit/
├── main.py                            程序入口：setup_logging → install_sys_excepthook → MainWindow().run()
├── README.md                          本文档
├── 需求文档.md                        当前需求（正式，按轮次替换）
├── 备忘文档.md                        Prompt 备忘草稿
├── assets/                            静态数据
│   ├── map.geojson                    ★ 中国全图（自定义嵌套结构，非标准 GeoJSON）：13 州 / 106 郡 / 1152 县
│   ├── characters.json                1049 位人物基础数据（29 字段）
│   ├── color.txt                      调色板参考（仅供人工取色，运行时不读）
│   ├── portrait/                      人物头像（{id}-{name}.{ext}，当前 739 张）
│   ├── roads.geojson                  路网
│   ├── water.geojson                  河流 / 湖泊
│   └── mountains.geojson              山地（已下载，未接入渲染）
├── scenarios/
│   └── default.json                   190 剧本（52 势力 / 1049 人物 / 555 据点）
├── tests/                             单元测试
│   ├── test_composite_command.py      CompositeCommand 顺序 / 逆序语义
│   ├── test_scenario_writer.py        serialize / diff / save 增量写回
│   └── test_character_appeared.py     appeared 加载兼容 / 登场开关 / dirty
├── tools/                             离线脚本（不参与运行时，保持 print 输出）
│   ├── build_scenario_190.py          生成 190 年默认剧本（FACTIONS 常量 + 人物分配）
│   ├── 头像.py                        头像批量重命名 / 复制 / 对账（顶部 APPLY 开关）
│   ├── characters/                    人物原始数据
│   │   ├── 314英雄集结武将数据.xlsx    源数据表
│   │   ├── 314.py                     生成脚本
│   │   └── characters.json            中间产物
│   └── map/                           地图预处理脚本（预处理 / 精简 / 县边界 / 道路生成 / 诊断…）
├── userdata/
│   ├── settings.json                  用户设置覆盖（只存与默认不同的项）
│   └── logs/                          运行日志（app_YYYYMMDD_HHMMSS.log，保留 30 个）
└── game/                              运行时主包
    ├── config/                        配置层（无业务逻辑）
    │   ├── constants.py               路径常量 + 窗口常量 + APP_MODE + LOG_ENABLED
    │   ├── style.py                   主题 THEME / 字号 FONT_SIZES / 地图样式 MAP_STYLE
    │   │                              / 分级显隐 CITY_LEVEL_MIN_SCALE / 图层 LAYER_VISIBILITY
    │   │                              / hover 开关 MAP_INTERACTION / 面板列 PANEL_COLUMNS
    │   ├── settings_manager.py        设置加载 / 保存 / 就地写回 style 模块
    │   ├── settings_schema.py         设置窗口元数据（Tabs / Groups / Items）
    │   │                              + get_panel_columns_meta()
    │   └── logging_setup.py           ★ 日志初始化 + sys/tk 异常钩子 + LOG_ENABLED 总开关
    ├── core/                          核心数据层（与 UI 无关）
    │   ├── game_state.py              回合 / 日期 / 玩家势力 / 资源（信息栏数据源）
    │   ├── world.py                   World：势力 / 人物 / 据点的聚合容器 + 查询 + 统计
    │   ├── faction.py                 Faction：势力（stance 相对玩家）+ gold/food/troops 派生
    │   ├── character.py               Character：人物（31 字段，node / location 分离）
    │   ├── node.py                    Node：县 = 据点（静态 + 动态 owner/troops/gold/food）
    │   ├── scenario.py                剧本加载（三层人物 + character_id_range + 应用登场状态）
    │   ├── territory.py               郡级势力统计（保留，暂不消费）
    │   ├── edit_session.py            ★ Command / CompositeCommand / EditSession
    │   ├── edit_commands.py           ★ NodeEditCommand / FactionEditCommand / CharacterEditCommand
    │   ├── scenario_writer.py         ★ serialize / diff / save（增量）
    │   └── utils.py                   颜色（lighten/darken）/ 几何工具
    ├── map/                           地图层（投影 + 渲染）
    │   ├── geo_data.py                GeoData：加载 / 分类 / 空间查询 find_location_detail
    │   ├── viewport.py                Viewport：经纬度 ⇄ 像素投影 / 缩放 / 平移
    │   └── renderer.py                MapRenderer：图层渲染 + 选中/hover 高亮层
    └── ui/                            UI 层
        ├── main_window.py             装配工：布局 + hover 拼状态栏 + tooltip
        │                              + 地图右键菜单 + 双向定位 + 面板列刷新转发
        │                              + 未保存提示（_refresh_title）
        ├── top_bar.py                 顶部信息栏（200ms 轮询）+ 下拉菜单 +「进行」按钮
        ├── status_bar.py              底部状态栏（消息 / 缩放 / 位置）
        ├── map_canvas.py              MapCanvas：地图画布 + 鼠标（拖拽/缩放/点选/右键/hover）
        ├── map_controller.py          面板访问地图的唯一接口（fit_to_node / center_on…）
        ├── side_panel.py              右侧 Tab 集合 + 面板注册 + select_panel
        │                              + reload_panel_columns()
        ├── settings_window.py         设置窗口（多 Tab + 折叠分组 + 草稿 + 保存）
        │                              +「面板列」tab + 8 个方法
        ├── character_info_window.py   ★ 人物情报窗口（头像 + 五维雷达图 + 关系 + 生平占位）
        ├── window_utils.py            窗口工具（最大化 / 居中）
        ├── dialogs/                   ★ 编辑弹窗（数据驱动）
        │   ├── field_spec.py          Field NamedTuple（6 种 kind）
        │   ├── edit_dialog.py         通用数据驱动弹窗（无实体分支）
        │   ├── node_fields.py         据点字段表（10 项）
        │   ├── faction_fields.py      势力字段表（8 项，含 troops readonly）
        │   ├── node_edit.py           ★ 据点编辑共用流程（含郡治互斥）
        │   └── faction_edit.py        ★ 势力编辑共用流程
        ├── widgets/
        │   └── collapsible.py         折叠区块（设置窗口分组用）
        └── panels/                    右侧四个面板
            ├── list/                  ★ 通用列表框架（通用代码唯一集中点）
            │   ├── panel.py           GenericListPanel 基类：UI 组装 + 排序/分组/搜索
            │   │                      /右键/多选/双向定位调度 + _resolve_columns / reload_columns
            │   ├── columns.py         Column 列定义（含 image 列渲染扩展点）
            │   ├── model.py           Group 分组树节点（title/children/tags/row_tag）
            │   ├── sorting.py         按列排序（空值/"—" 永远排最后）
            │   ├── grouping.py        默认维度分组（正交 + priority_name 置顶）
            │   ├── group_bar.py       分组条（点选顺序 = 嵌套顺序）
            │   ├── search_bar.py      搜索框（实时 + 清空按钮 + parse_query 扩展点）
            │   └── context_menu.py    MenuItem / MenuContext + 菜单构建器
            ├── node_panel.py          据点面板（纯配置 + PANEL_KEY）
            ├── character_panel.py     人物面板（纯配置 + priority_name 玩家置顶
            │                          + PANEL_KEY + 姓名列去表字 + 人物情报入口）
            ├── faction_panel.py       势力面板（固定分组 build_groups + 色块 image 扩展点
            │                          + COLUMNS 绑定 / PANEL_KEY / 兵力·据点·人物列
            │                          + 编辑复用 faction_edit）
            └── troop_panel.py         部队面板（空壳接入框架 + PANEL_KEY）
```

依赖方向单向：main → ui → core/map → config。

第三方依赖：**Pillow**（仅 game/ui/character_info_window.py 的头像加载用）。仓库内没有 requirements.txt，需自行安装：`pip install Pillow`。未安装时该窗口降级显示「未安装 Pillow」，其余功能不受影响（§8.3 第 34 条）。

---

## 2.1 panels/list/ 框架与具体面板的分工

| 关注点 | 框架（list/）负责 | 具体面板只写 |
|---|---|---|
| 列表 | Treeview 构建、列宽/对齐、滚动条、group tag | COLUMNS / NAME_COLUMN |
| 排序 | 列头点击切换升降序、空值排最后 | （无需） |
| 分组 | 默认维度分组（GROUP_DIMS + GroupBar） | GROUP_DIMS / DEFAULT_GROUP / PRIORITY_NAME |
| 固定分组 | CUSTOM_GROUPING 时走 build_groups() 回调 | build_groups()（势力用） |
| 搜索 | 过滤调度、多词 AND、保留分组结构 | （无需） |
| 右键菜单 | 菜单弹出、多选上下文、MenuItem 构建 | context_menu_items() |
| 列渲染 | Column.image 扩展点（文本前加图片） | image 取值函数（势力色块） |
| 定位到地图 | locate_on_map() 默认按 node_id/coords | （可选覆盖） |
| 反向定位 | scroll_to_row() 展开祖先 + 滚动 + 选中 | row_key() |
| 列配置 | _resolve_columns() 读 PANEL_COLUMNS + 过滤重排 | PANEL_KEY |
| 列热重载 | reload_columns() 重建 Treeview + refresh | （无需） |
| 编辑会话 | edit_session 类属性 + _open_dialog() / _notify_edit() | context_menu_items() 里的 _edit() |
| 编辑入口置灰 | build_menu(edit_enabled=edit_session is not None) 统一处理 edit=True 项 | MenuItem(..., edit=True) |

---

## 3. 核心数据模型

### 3.1 三层 ID 编码

州 2 位 / 郡 4 位 / 县 6 位。一个六位 id 对应一个县 = 一个据点 = 一个 Node。

势力 id = 君主的人物 id（四位）。人物 id 四位，全局唯一。

### 3.2 势力（Faction）

id = 君主人物 id。可落盘字段：id / name / color / prestige / stance。stance_label() → "敌对" / "盟友" / "中立"（stance < 0 敌对；> 80 盟友；其余中立）。

★ gold / food / troops 是派生值：

```python
@property
def gold(self):
    """名下据点金钱求和。无主据点不计。"""
    if self._nodes_ref is None:
        return 0
    return sum(n.gold for n in self._nodes_ref.values() if n.owner == self.id)

@property
def food(self):
    """名下据点军粮求和。"""
    if self._nodes_ref is None:
        return 0
    return sum(n.food for n in self._nodes_ref.values() if n.owner == self.id)

@property
def troops(self):
    """名下据点兵力求和 + 所属部队兵力求和。

    部队项恒为 0（Troop 模型未建，见 §8.4 / TODO(phase2)）。
    """
    total = 0
    if self._nodes_ref is not None:
        total += sum(n.troops for n in self._nodes_ref.values()
                     if n.owner == self.id)
    # TODO(phase2): Troop 模型落地后，在此追加 self._troops_ref 求和：
    #     if self._troops_ref is not None:
    #         total += sum(t.troops for t in self._troops_ref.values()
    #                      if t.faction_id == self.id)
    return total
```

- _nodes_ref 是 world.nodes 的引用（不是快照），由 World.bind_factions() 注入
- _troops_ref **不建**（没有 Troop 容器可注入，避免留空属性误导后人）
- 三者均无 setter —— faction.gold = x / faction.food = x / faction.troops = x 都会报错
- from_dict 不读 gold / food / troops；to_dict 不写（旧剧本里的遗留字段被静默忽略）
- 好处：改据点 owner / troops 后，势力金/粮/兵力自动反映（为 phase2 的 owner 编辑铺路）

### 3.2.1 序列化对称性

| 类 | to_dict 写什么 |
|---|---|
| Node | 从零写全 7 字段：owner / troops / gold / food / type / level / is_capital |
| Faction | name / color / prestige / stance（不写 gold / food / troops） |
| Character | 全 31 字段（含 portrait / appeared / faction / node / location / role） |

理由见 §8.3 第 43 条：加新的可编辑静态字段时，写 / 读 / 显示三处必须同步。

### 3.3 人物（Character）

四位 id（"0001"–"1049"）。静态来自 characters.json，动态由剧本覆盖。

**字段一览（共 31 项，其中剧本动态 5 项）**

| 分组 | 字段 | 汉语 | 类型 |
|---|---|---|---|
| 标识 | id / name / family_name / sex / portrait | 编号 / 姓名 / 字 / 性别 / 头像编号 | str / str / str / str / int |
| 五维 | leadership / might / intelligence / politics / charisma | 统率 / 武力 / 智力 / 政治 / 魅力 | int |
| 时间 | appear_year / birth_year / death_year | 登场年 / 出生年 / 死亡年 | int |
| 相性 | affinity | 相性（0–149 圆形值） | int |
| 关系 | blood / father / mother / generation / spouse / sworn_brothers / liked / disliked | 血缘 / 父亲 / 母亲 / 世代 / 配偶 / 义兄弟 / 亲爱 / 厌恶 | str / str\|None / str\|None / int / str\|None / list[str] / list[str] / list[str] |
| 系统 | start_official / traits / formations / tactics | 开始仕官年 / 个性 / 阵型 / 战法 | int / list[str] / list[str] / list[str] |
| 剧本动态 | appeared | 登场（本剧本中是否已登场） | bool |
| | faction | 势力 id | str \| None |
| | node | 所属（编制所属据点 id） | str \| None |
| | location | 所在（当前所在据点 id） | str \| None |
| | role | 身份 | str \| None |

★ 基础数据里的废弃字段（location_name / affiliation）：

- characters.json 里仍是 29 字段，除上表外还多出 location_name / affiliation 两个**历史遗留字段**（json 里没有 node / location，改由剧本覆盖）。
- Character 类不读也不写这两个字段；from_dict 只认它自己有的 key，apply_override 用 hasattr 过滤 → 二者被静默忽略。
- 清理时只需改 tools/characters/314.py 与重生成 characters.json。

★ portrait 字段：

- 字段保留（from_dict / to_dict 依旧读写），但不再被消费。
- 头像路径改为拼 assets/portrait/{id}-{name}.{ext}。
- 将来清理时再删字段。

**方法**

| 方法 | 说明 |
|---|---|
| is_ruler() / is_free() / is_appeared(year) / is_alive(year) | 语义判断 |
| display_name() | 带表字的展示名（人物情报窗口标题 / 关系区姓名仍用） |
| from_dict(cid, d) / to_dict() | JSON 双向（31 key） |
| apply_override(data) | 剧本覆盖（hasattr 防脏数据，只覆盖显式出现的 key） |

★ appeared 字段（bool）：

- 属于**剧本动态字段**：基础数据里恒为 True，由剧本覆盖成 true / false。
- `from_dict` 用 `d.get("appeared", True)` —— **老剧本无此字段 → 全部默认登场**（行为同改造前）。
- 判登场**只看 appeared**，不看 birth_year / death_year；`is_appeared(year)` 保留为纯推算方法，不读 appeared。

### 3.4 县 = 据点（Node）

静态：id / name / coords / type / level / is_capital / boundary。 动态：owner / troops / gold / food。 属性：state_id → id[:2]，county_id → id[:4]，is_owned()。

★ to_dict()：从零写全 7 字段（owner / troops / gold / food / type / level / is_capital），供 ScenarioWriter.serialize 用。**不含 id / name / coords**（静态字段不参与编辑回写）。

★ level 构造时不 clamp；GeoData 在建县点时统一 clamp 到 1–10。

★ 静态字段可被剧本覆盖：_apply_node_overrides 除 owner/troops/gold/food 外， 也读 type / level / is_capital —— 否则编辑保存后重新加载会回原样（§8.3 第 43 条）。

★ 渲染必须查 World 而非 GeoData：renderer._effective_level(props) 优先取 world.node(id).level， 退回 GeoData.shapes_point 的 level。否则改 level 后地图县点大小 / 形状不更新。

### 3.5 游戏世界（World）

聚合容器：factions / characters / nodes / state_names / county_names。元信息：version / id / name / desc / year / month / xun / player_faction_id / character_id_range。

★ characters 收**全量**人物（1049 人）——但「算不算某个势力 / 据点的人」要过 appeared 这一关：
未登场人物虽然留在 World.characters（可编辑），却**不计入**势力 / 据点的人物数（§查询与聚合）。

**查询：**

```python
def player_faction(self):   return self.factions.get(self.player_faction_id)
def player_ruler(self):     # 玩家势力的君主 Character
def state_name(self, sid):  return self.state_names.get(sid, sid or "—")
def county_name(self, cid): return self.county_names.get(cid, cid or "—")
def faction(self, fid):     return self.factions.get(fid) if fid else None
def node(self, nid):        return self.nodes.get(nid) if nid else None
def character(self, cid):   return self.characters.get(cid) if cid else None
def nodes_of(self, faction_id):      # 该势力拥有的据点列表
def characters_of(self, faction_id): # 该势力的人物列表（★ 未登场不计）
def characters_at(self, node_id):    # 该据点的人物列表（★ 按所属 node，未登场不计）
```

★ **人物查询一律过 appeared**：`characters_of` / `characters_at` / `count_characters_by_faction` /
`count_characters_by_node` 全部要求 `c.appeared`。理由：未登场人物虽然留在 World.characters
（编辑器要能看到并改），但「算不算这个势力 / 据点的人」——不算。口径统一，避免面板与查询打架。

★ **据点人物口径 = Character.node（所属）**，不是 location（所在）。两者剧本初始相同，
只有将来实现出征 / 调动时才会分叉；选中所属是因为它与 faction 同属「编制归属」语义。

**聚合：**

```python
def count_nodes_by_owner(self):
    """每个势力拥有的据点数。dict[fid, int]，无主据点不计。"""
    return Counter(n.owner for n in self.nodes.values() if n.owner)

def count_characters_by_faction(self):
    """每个势力的人物数。dict[fid, int]，无势力 / 未登场人物不计。"""
    return Counter(c.faction for c in self.characters.values()
                   if c.faction and c.appeared)

def count_characters_by_node(self):
    """每个据点的人物数。dict[node_id, int]，无所属 / 未登场人物不计。"""
    return Counter(c.node for c in self.characters.values()
                   if c.node and c.appeared)
```

口径与 nodes_of / characters_of 一致（node.owner / char.faction / char.node，再过 appeared）。
返回 Counter（dict 子类），调用方 .get(id, 0)。

**刷新时机：** 人物登场开关（CharacterEditCommand）→ CharacterPanel._notify_edit →
SidePanel.on_panel_edit → refresh_all()：四个面板一起重算，势力面板「人物」列与据点面板
「人物」列随之更新（不缓存聚合值，每次 refresh 现算）。undo / redo 同路径（MainWindow._on_undo/_on_redo）。

**注入与占位：**

- bind_factions()：给每个 Faction 注入 `_nodes_ref = self.nodes`，由 ScenarioLoader.from_dict 末尾调用（必须在 node overrides 之后）。
- add_faction() / remove_faction() / remove_faction_if_empty()：phase2 占位，抛 NotImplementedError。

### 3.6 剧本加载器（ScenarioLoader）

三层人物加载（顺序不可颠倒）：

```text
1. _load_base_characters(world, id_range)
     读 characters.json，只保留 id 落在 id_range 内的人
2. _apply_character_overrides(world, raw["characters"])
     剧本覆盖 appeared / faction / node / location / role
3. _apply_appeared(world)
     只读 appeared（脏数据归一化成 bool），★ 不删人
```

**第三层只读不筛**：World.characters 收全量人物（1049 人，含未登场与穿越人物）——
未登场人物也必须在 World 里，编辑器才能看到并改他们（「设为登场」才有着落）。

character_id_range：剧本顶层可选字段，[lo, hi]。不写 = 全加载（[1, 9999]）。
仍保留兼容（老剧本还能按 id 白名单过滤）；190 剧本已不再写它。

据点构造与覆盖顺序（_build_nodes_from_geo → _build_region_names → _apply_node_overrides → bind_factions）见 §5.10。

★ death_year 不再被消费：加载不筛、登场判定不看。字段本身保留（历史人物长寿化 / 穿越设定）。

### 3.7 郡级统计与县界（CountyStat / CityBoundary）

**CountyStat（core/territory.py）** — 郡级势力控制力统计，**保留但不消费**：

- 常量 CAPITAL_BONUS = 2.0；控制力权重 = 11 − level，郡治该值再乘 2。
- CountyStat 字段：county_id / owner_id / ratio；is_dominant（ratio > 0.8）/ is_major（ratio > 0.5）。
- compute_county_stats(world) → {county_id: CountyStat}。
- 消费状态：只有 MapRenderer.set_world() 调它并存进 `_county_stats`，之后无任何读取点；染色层走的是「按 node.owner 查势力色」的另一条路径。`MAP_STYLE["territory"]["major_fade"]` 同样无人消费。

**CityBoundary（县界）** — 不是 map.geojson 的原生结构，由 GeoData 从 `counties[].cities[].boundary` 生成：

- 每一项形如 `{"geometry": {"coordinates": ring}, "properties": {...}, "bbox": (...), "size": 面积}`。
- properties 含 id / 县名 / type / level。
- 所有 type 的据点都收县界，不做过滤。
- 带 bbox 与 size 是为了 LOD 分级（§5.14 _assign_lod）。

**GeoData._city_index（县界多边形索引）**：

| 项 | 结构 |
|---|---|
| 每项 | (bbox, 县名, ring, 县 id) |

4 元组里的县 id 用于 hover 反查势力（node_id）。任何解包处必须 4 元组，见 §8.3 第 16 条。

---

## 4. 数据格式参考

### 4.1 assets/map.geojson

★ **不是标准 GeoJSON**：顶层只有一个键 `states`，没有 `type` / `features`，也没有 `properties` 概念，是自定义嵌套结构（约 3.7 MB）。GeoData 把它「翻译」成 shapes_* 系列供渲染层消费。

```text
{ "states": [ state, ... ] }

state  = { id, name, name_coords: [[x, y], ...], boundary: [ring, ...], counties: [county, ...] }
county = { id, name, name_coords, capital, capital_id, boundary: [ring, ...], cities: [city, ...] }
city   = { id, name, coords: [x, y], is_capital: bool, level: int(1–10), type: str, boundary: [ring, ...] }
```

- id 分层前缀编码：州 2 位 `01`，郡 4 位 `0101`，县 6 位 `010101`。
- 州 boundary 为 MultiPolygon 风格（list → ring → 点）；郡 / 县 boundary 是 ring 列表。
- 州 / 郡的 name_coords 是标签锚点线段（取中点画名字）。

**具名样例**：州 `id="01"` `name="并州"` → 郡 `id="0101"` `name="上党郡"` `capital="长子"` `capital_id="010101"` → 县 `id="010101"` `name="长子"` `level=3` `type="城"` `is_capital=true`。

**规模统计：**

| 项 | 数量 |
|---|---|
| 州 | 13（id 01–13） |
| 郡 | 106 |
| 县 | **1152** |
| is_capital = true 的县 | 106（与郡数一致，即每郡一治所） |
| type 分布 | 城 1107 / 关隘 30 / 渡口 15 |
| level 分布 | 1→2, 2→36, 3→31, 4→63, 5→96, 6→126, 7→160, 8→188, 9→221, 10→229 |

### 4.2 assets/characters.json

顶层是 dict，不是裸数组：

| 键 | 类型 | 值 |
|---|---|---|
| version | int | 1 |
| source | str | 数据来源标记 |
| count | int | 1049 |
| characters | dict | 1049 条，键为 4 位零填充字符串 "0001"–"1049" |
| _name_index | dict | 姓名 → id 索引（1043 项） |
| _ambiguous_names | dict | 重名表（5 组） |
| _missing_refs | dict | 悬空引用（0 项） |

- 每条记录的字段集**完全一致**（29 字段），无差异。
- id 连续无缺号：1 … 1049。
- 关系字段（father / mother / spouse / sworn_brothers / liked / disliked）的元素是人物 id 引用。
- faction / location_name / affiliation / role 在基础数据里恒为 null，由剧本填充；node / location 不在基础数据里。
- count（1049）与 _name_index（1043）的差值来自 5 组重名（同名多人）。

### 4.3 type 枚举

只有三种：城 / 关隘 / 渡口。

### 4.4 scenarios/default.json 结构

```json
{
  "version": 2,
  "id": "default",
  "name": "十八路诸侯 · 190",
  "desc": "190年，十八路诸侯讨董……",
  "start": { "year": 190, "month": 1, "xun": 1 },
  "player_faction": "0521",
  "factions": { "…52 家…" },
  "characters": { "…1049 条，写 5 字段（appeared/faction/node/location/role），按 id 排序…" },
  "nodes": { "…555 条…" }
}
```

**关键约定：**

| 段 | 写什么 |
|---|---|
| character_id_range | 老剧本可写 [1, 1000] 或省略；190 剧本**不写** |
| factions | name / color / prestige / stance（不写 gold / food / troops） |
| characters | appeared / faction / node / location / role（全量 1049 人） |
| nodes | owner / troops / gold / food；个别条目额外带 is_capital / level |

- 三段均为 **dict（键 = id）而非数组**：factions 键 4 位势力 id、characters 键 4 位人物 id、nodes 键 6 位据点 id。
- nodes 只有 555 条 < map.geojson 的 1152 县 —— 剧本只覆盖有主的据点，其余县由 GeoData 建出来后保持无主。
- nodes 的 is_capital / level 是**可选字段**，解析端必须容错（`_apply_node_overrides` 用 `in` 判断）。
- characters 的 appeared 也是**可选字段**：不写 → 默认 true（老剧本兼容）。

**登场判定（生成期一次算死，写进剧本，见 tools/build_scenario_190.py::compute_appeared）**

| 情况 | appeared |
|---|---|
| 穿越人物（id ≥ 1001） | false |
| 已被分配到势力 | true |
| birth_year 缺失 | false |
| year − birth_year ≥ 16 | true |
| 其余 | false |

- 判定顺序即优先级（穿越 > 已分配 > 生年规则）。
- ★ `death_year` **不参与判定**。
- 未登场人物的 faction / node / location / role 一律 null；「设为登场」后仍是「在野」，归属由完整人物编辑补。

### 4.5 190 剧本势力（52 家）

- 键 = 4 位势力 id = 君主的人物 id；字段 name / color / prestige / stance（初始 prestige 1000、stance 相对玩家的关系值）。
- 完整清单（含 capital / territories / max_cities）见 tools/build_scenario_190.py 的 `FACTIONS` 常量，生成结果落在 scenarios/default.json。
- 四位主角色锁定：刘备 #3B8B3B 暗绿 / 袁绍 #E8C500 亮黄 / 曹操 #2928EF 蓝 / 孙坚 #C83030 红。

### 4.6 势力地盘表达（build_scenario_190.py）

```python
FACTIONS = {
    "0521": {
        "name": "曹操", "color": "#2928EF", "stance": 0,
        "capital": "130301",
        "territories": [...],  # 4 位 = 整郡；6 位 = 单县
        "max_cities": 14,      # 限制该势力总县数（按 level 优先大城市）
    },
}
```

人物分配：CORE 手写种子 + 网络投票扩展 + affinity 兜底（只给 id ≤ 1000 的历史人物分势力；穿越人物不参与）。

登场预计算：分配完势力后逐人算 appeared（规则见 §4.4）——有势力的一律 true，其余按生年规则；穿越人物一律 false。
未登场人物仍写进 characters 段（faction / node / location / role 一律 null），编辑器里可查可改。

### 4.7 头像资产

目录：assets/portrait/（当前 739 张） 命名：{id}-{name}.{ext}，如 0651-张南.jpg 扩展名：.jpg / .jpeg / .png / .gif / .bmp / .webp 同名多人：复制多份，如 0651-张南.jpg + 0652-张南.jpg

**规范流程：**

```bash
python tools/头像.py          # APPLY = False 时只预览，不改文件
# 确认清单无误后，把文件顶部 APPLY 改成 True
python tools/头像.py          # 执行
```

匹配规则：图片 stem == Character.name，**精确匹配**，不做简繁 / 表字 / 模糊。

---

## 5. 模块与函数清单

### 5.1 main.py

```python
def main():
    log_path = setup_logging()            # LOG_ENABLED=False → 返回 None
    install_sys_excepthook()              # LOG_ENABLED=False → no-op
    logging.getLogger(__name__).info("应用启动，日志文件：%s", log_path)
    MainWindow().run()
```

顺序约束：setup_logging() 必须在 MainWindow() 之前，否则构造期间的日志丢失（§8.3 第 48 条）。

### 5.2 game/config/constants.py

全部常量共 15 个：

| 常量 | 值 | 说明 |
|---|---|---|
| PROJECT_ROOT | Path(__file__).resolve().parent.parent.parent | 由文件位置反推，任意 cwd 启动都能定位 assets/ |
| ASSETS_DIR | PROJECT_ROOT / "assets" | |
| DEFAULT_MAP_PATH | ASSETS_DIR / "map.geojson" | |
| DEFAULT_WATER_PATH | ASSETS_DIR / "water.geojson" | |
| DEFAULT_ROADS_PATH | ASSETS_DIR / "roads.geojson" | |
| DEFAULT_CHARACTERS_PATH | ASSETS_DIR / "characters.json" | |
| SCENARIOS_DIR | PROJECT_ROOT / "scenarios" | 与 assets/ 并列 |
| DEFAULT_SCENARIO_PATH | SCENARIOS_DIR / "default.json" | |
| APP_TITLE | "暗耻三国志" | |
| WINDOW_SIZE | "1440x900" | 字符串；当前窗口走 maximize，此常量未被使用（§8.3 第 21 条） |
| MIN_WINDOW_SIZE | (1024, 640) | 元组 |
| MODE_EDIT / MODE_GAME | "edit" / "game" | 应用模式 |
| APP_MODE | MODE_EDIT | 全局开关：编译期切换 |
| LOG_DIR | PROJECT_ROOT / "userdata" / "logs" | |
| LOG_ENABLED | True | False = 不建目录 / 不写文件 / 不装异常钩子 |

### 5.3 game/config/style.py

分组原则：UI 改 THEME，地图改 MAP_STYLE，互不干扰。

**THEME（11 键）**：info_bg #2C3E50 / info_fg #ECF0F1 / info_hover_bg #3D566E / info_sep #4A6076 / status_bg #E4E7EA / status_fg #333333 / status_sep #B0B8C0 / panel_bg #FAFBFC / panel_header_bg #E8EDF2 / canvas_bg #EEF2F7 / toolbar_bg #F5F7FA

**FONT_CANDIDATES**：按序回退的中文字体名元组（Microsoft YaHei → SimHei → PingFang SC → …）。MainWindow._pick_font_family 取第一个可用者，全程序共用。

**FONT_SIZES**：相对基准字号的偏移量 —— info_bar 10 / menu 10 / status_bar 9 / panel_title 10 / panel_body 9。

**MAP_STYLE（14 个子项）**

| 子项 | 关键键 → 值 |
|---|---|
| polygon | fill ""（空 = 不填充）/ outline #000000 / width 2 —— 州面 |
| line | color #000000 / width 1 —— 郡界 |
| city_line | color #000000 / width 1 / dash (3,5) —— 县界虚线 |
| road | color #B5442C / width_divisor 2600 / min_width 0.2 / max_width 2.0 / difficulty_floor 1.0 |
| point | fill #3b2a1a / outline #f2e6cc / size_divisor 820 / min_radius 1.3 / max_radius 7.0 / ring_scale 1.3 / ring_width 0.9 / ring_color #000000 |
| point.shape_by_level | 1–3 circle / 4–6 square / 7–8 diamond / 9–10 triangle |
| point.radius_by_level | 1→2.00, 2→1.80, 3→1.60, 4→1.42, 5→1.26, 6→1.12, 7→0.90, 8→0.80, 9→0.70, 10→0.62（level 越小点越大） |
| point.hollow_by_level | 1–10 全 False（空心逻辑保留但未启用） |
| point.ring_by_level | 仅 1、2 为 True（大城外环） |
| water_polygon / water_line | #A9D2F0 / #5B9BD5；#1E90FF —— 湖 / 河 |
| territory | major_fade 0.4（当前无人消费） |
| label_state | color #1A1A1A / halo #FFFFFF / size_divisor 55 / min_size 11 / max_size 44 / min_scale 0 / max_scale 40 |
| label_county | color #333333 / font_family "楷体" / size_divisor 124 / min_size 8 / max_size 19 / min_scale 12 / max_scale 150 |
| label_city | color #000000 / size_divisor 140 / min_size 8 / max_size 16 / min_scale 30 / point_gap 6 |

min_scale / max_scale 单位是像素/度；低于 min 或达到 max 均隐藏（放大到 max_scale 时州/郡名让位给县名）。

**CITY_LEVEL_MIN_SCALE（level → 显示县名所需最小 scale）**：1→0, 2→10, 3→25, 4→50, 5→150, 6→250, 7→350, 8→500, 9→600, 10→700。★ 只控制**名称**显隐，县点本身始终绘制。

**LAYER_VISIBILITY（11 键）**：polygon / line / point / road / label_state / label_county / label_city / territory / city 默认 True；water / mountain 默认 False（数据未接入渲染）。

**MAP_INTERACTION（5 开关）**：highlight_hover_border / _fill / _faction_all / _region 默认 False，_tooltip 默认 True。

**PANEL_COLUMNS（4 面板）**：node / character / faction / troop，结构统一 `{"order": [], "hidden": []}`。order 为空 = 沿用 COLUMNS 声明顺序；NAME_COLUMN(#0) 锁定必显；未出现在 order 中的新列自动追加到末尾并默认显示（§8.3 第 28 条）。

### 5.4 game/config/settings_manager.py

- 模块级 `_DEFAULTS`：首次 import 时对 style 的 THEME / FONT_SIZES / FONT_CANDIDATES / MAP_STYLE / CITY_LEVEL_MIN_SCALE / LAYER_VISIBILITY / MAP_INTERACTION / PANEL_COLUMNS 做 deepcopy 快照。
- `load()`：current = deepcopy(defaults) → 遍历文件里的点号路径覆盖项 → 按 defaults 的模板类型 `_coerce` 转型 → `_set_into`。文件不存在 / 解析失败 / 路径已废弃一律静默忽略，不抛。
- `save()`：只落盘与默认值不同的项，格式 `{"version": 1, "overrides": {"MAP_STYLE.point.min_radius": …, …}}`。
- `get / get_default / set / set_many / reset_all / reset_paths`。
- `apply()`：★ **就地**改写 style 模块里的 dict 对象（保持对象 id 不变），因此 `from game.config.style import MAP_STYLE` 的模块自动看到新值。特例：FONT_CANDIDATES 以 tuple 整体替换。
- `register_listener / notify`，以及 `changed_paths()` / `has_overrides()`。

### 5.5 game/config/settings_schema.py

纯数据模块，描述设置窗口的 Tab / 分组 / 条目。

- TABS：appearance（外观）/ operation（操作）/ panels（面板列）/ game（游戏）。
- GROUPS：key / tab / title / desc / restart —— `restart: True` 的分组（theme、font）保存后提示需重启。
- ITEMS：path / group / type / label，可选 desc / min / max / choices / value_type / value_suffix / hidden。type ∈ color / int / float / bool / choice / level_table。level_table 用于 MAP_STYLE.point.shape_by_level、radius_by_level、hollow_by_level 与 CITY_LEVEL_MIN_SCALE 这类「等级 → 值」表。
- 查询辅助：groups_of_tab / items_of_group / group_of / paths_of_group / group_meta。
- `get_panel_columns_meta() -> {panel_key: [(col_key, col_title), ...]}`：惰性 import 四个 Panel 类读其 COLUMNS；每个面板独立 try/except 降级。NAME_COLUMN（#0）不返回（锁定必显）。

### 5.6 game/config/logging_setup.py

```python
setup_logging() -> Path | None    # 初始化，返回本次会话的 log 文件路径
install_sys_excepthook()          # 未捕获异常 → CRITICAL + traceback
install_tk_excepthook(root)       # tkinter 回调异常 → ERROR + traceback
get_session_id() -> str           # 8 位十六进制
get_log_file_path() -> Path|None
_cleanup_old_logs(log_dir)        # 只保留最近 _MAX_LOG_FILES（= 30）个
class _SessionFilter              # 给每条 record 注入 record.session
```

关键点：

- 只挂 FileHandler：不挂 StreamHandler，控制台完全静默。
- _SessionFilter 挂 handler：`handler.addFilter(...)`，不是 `logger.addFilter(...)`（§8.3 第 49 条）。
- install_tk_excepthook 覆盖 `Tk.report_callback_exception`：sys.excepthook 接不到 tk 回调异常。
- 安装顺序：setup_logging() → install_sys_excepthook() → MainWindow()；tk hook 在 Tk() 之后立即。
- KeyboardInterrupt 交回原生 `sys.__excepthook__`，不吞 Ctrl+C。
- 重复初始化保护：先清空 root 已有 handler。

★ LOG_ENABLED 编译期总开关（三处入口判断，其余模块不感知）：

```python
def setup_logging():
    if not LOG_ENABLED:
        logging.disable(logging.CRITICAL)
        _LOG_FILE_PATH = None
        return None
    # ... 原逻辑

def install_sys_excepthook():
    if not LOG_ENABLED:
        return   # 交回 Python 默认 stderr
    # ...

def install_tk_excepthook(root):
    if not LOG_ENABLED:
        return   # 交回 Tk 默认 stderr
    # ...
```

行为表：

| 场景 | 处理 |
|---|---|
| True | 建目录 + 清旧 + 建新 + 挂 FileHandler + 装 2 个异常钩子 |
| False（启动） | logging.disable(CRITICAL) + _LOG_FILE_PATH = None + 不建目录、不清旧、不写文件 |
| False（未捕获异常） | 交回 sys.__excepthook__ / Tk 默认 stderr，不静默 |
| False（KeyboardInterrupt） | 交回 Python 原生 |
| False（旧日志） | 保留不动（不清理） |
| tools/ 下脚本 | 不受影响（保持 print，本就不接 logging） |

**日志格式：**

```text
2026-09-25 09:42:24.933 [INFO ] [573b6529] game.ui.main_window: 初始化 MainWindow，APP_MODE=edit
   ↑ 时间戳(毫秒)         ↑级别   ↑session    ↑模块(__name__)        ↑消息
```

### 5.7 game/core/utils.py

纯函数模块，无类。

| 函数 | 说明 |
|---|---|
| darken_color(hex_color, factor=0.5) | #RRGGBB 向黑插值；支持 3 位缩写；非法输入原样返回 |
| lighten_color(hex_color, factor=0.4) | 同上，向白插值 |
| walk_coords(coords) | 生成器，递归展开 GeoJSON 任意嵌套坐标，产出 (lon, lat) |
| midpoint_of_line(coords) | 取折线首尾中点（★ 当前无调用方，死代码） |
| point_in_polygon(x, y, ring) | 射线法点在多边形内判定；顶点 < 3 直接 False |

### 5.8 game/core/game_state.py

GameState：回合 / 日期 / 玩家势力 / 资源的信息栏数据源。

- 字段 8 个：year / month / xun（旬 1–3）/ player_faction / prestige / gold / food / world。
- `sync_from_world(world)`：绑定 world 并单向复制 year/month/xun。
- `date_text()`：未初始化返回 "—"，否则 `YYYY年 M月X旬`。
- `advance_turn()`：旬 → 月 → 年进位。
- `change_gold / change_food / change_prestige(delta)`：clamp ≥ 0；有玩家势力时改的是 Faction 对象，无势力时落在 GameState 自身作为回退存储。
- `_player_faction()`：委托 `world.player_faction()`。
- `get_display_items()`：5 元组列表（date / faction / prestige / gold / food），供 TopBar 渲染。
- ★ 已知缺陷（TODO(phase3)）：Faction.gold / food 已改为只读 property，`change_gold / change_food` 里的 `pf.gold = …` 一旦玩家势力存在就会抛 AttributeError；change_prestige 不受影响。

### 5.9 game/core/world.py

见 §3.5。

### 5.10 game/core/scenario.py — ScenarioLoader

`load(path, geo_data)` 只读 JSON 后转调 `from_dict(raw, geo_data)`。from_dict 完整顺序：

```text
1. World()；写元字段 version / id / name / desc / start / player_faction_id / character_id_range
2. factions 段 → Faction.from_dict
3. characters 段三层加载（§3.6）—— 第三层 _apply_appeared 只读 appeared，不删人
4. _build_nodes_from_geo(world, geo_data)
     从 geo_data.shapes_point 的 properties（id / 县名 / type / level / is_capital）
     + geometry.coordinates 建 Node
5. _build_region_names(world, geo_data)
     从 shapes_line 的 郡id / 郡名 / 州名 填 county_names / state_names
     （key 同时写 cid 与 cid[:2]）
6. _apply_node_overrides(world, raw["nodes"])
     动态 owner / troops / gold / food；静态可覆盖 type / level / is_capital
     （int / bool 强转；不读 name / coords；节点不在 geo 中则静默跳过）
7. world.bind_factions()      ★ 必须在 node overrides 之后（§8.3 第 39 条）
8. logger.info("剧本加载完成：%s", world.summary())
```

### 5.11 game/core/faction.py / node.py / character.py

见 §3.2 / §3.4 / §3.3。三者都不依赖 UI 与第三方库。

### 5.12 game/core/territory.py

见 §3.7。保留代码，当前无消费方。

### 5.13 game/core/edit_session.py / edit_commands.py / scenario_writer.py

见 §10（编辑会话设计）与 §9.3（增量保存）。摘要：

| 模块 | 导出 |
|---|---|
| edit_session.py | Command（抽象基类）/ CompositeCommand / EditSession |
| edit_commands.py | NodeEditCommand / FactionEditCommand / CharacterEditCommand |
| scenario_writer.py | ScenarioWriter.serialize / .diff / .save（全静态方法） |

### 5.14 game/map/geo_data.py / viewport.py / renderer.py

**GeoData（geo_data.py）**

- 入口：`GeoData.from_file(path)` → `_classify` → `_assign_lod(shapes_city_boundary)` → `_compute_bbox` → `_build_index`。
- 容器：shapes_polygon（州面）/ shapes_line（郡界）/ shapes_point（县点）/ shapes_city_boundary（县界 ring）/ shapes_water_line / shapes_water_polygon / roads；标签 labels_state（3 元组）/ labels_county（4 元组：(lon, lat, 郡名, 郡id)）/ labels_city（5 元组：(lon, lat, 县名, level, 据点id)）。
- 索引：_state_index / _county_index / _city_index（每项 (bbox, 县名, ring, 县 id)）。
- 空间查询：
  - find_state_at / find_county_at / find_city_at（多命中取 bbox 面积最小者）
  - _find_city_with_id（同 find_city_at 但返回 (县名, 县id)）
  - find_nearest_label(lon, lat, candidates, max_dist)（静态，标签近邻兜底）
  - find_location_detail(lon, lat) → {"state", "county", "city", "node_id"}；city 未命中时用 find_nearest_label(…, 0.4) 兜底（此时 node_id 为 None）
  - find_location(lon, lat) → (州名, 郡名, 县名)
- LOD：`_assign_lod(features)` 静态方法，对 shapes_city_boundary / shapes_water_line / shapes_water_polygon 按 size 降序后按累计百分位赋 min_scale —— pct < 0.15 → 0；< 0.40 → 15；< 0.70 → 45；其余 → 100。

**Viewport（viewport.py）**

- 字段：cx / cy（中心经纬度）/ scale（像素/度，X/Y 同比例）/ width / height。等距圆柱投影（纬度不做 cos 校正）。
- 方法：set_canvas_size / fit_to_bbox(bbox, margin=0.92)（contain 语义）/ zoom(factor, anchor)（以屏幕锚点为不动点）/ pan_pixels(dx, dy)（Y 轴符号与屏幕相反）/ project / unproject / span_px(bbox)（供字号、线宽、半径随缩放取值）。

**MapRenderer（renderer.py）**

- tag 常量：LABEL_TAG / WATER_TAG / ROAD_TAG / POLYGON_TAG / LINE_TAG / POINT_TAG / CITY_TAG / TERRITORY_TAG / SELECT_TAG / HOVER_TAG。
- 叠放层级（_LAYER_ORDER，从底到顶，由 _restack 逐个 tag_raise 实现）：polygon → territory → city → water → road → line → point → select_highlight → hover_highlight → label。
- 调度：set_data / set_world（绑定 World，重算 _county_stats，不重绘）/ draw_full / pan（canvas.move，O(1)）/ zoom（canvas.scale；_cum_scale 累计偏离 [0.5, 2.0] 即回落 draw_full 消除舍入误差）/ refresh_dynamic（删 water/road/point/label 四类 tag 后按 LAYER_VISIBILITY 重画并 _restack）/ _visible_bounds(margin_px=20)。
- 几何图层：render_polygons / render_lines（郡界）/ render_city_boundaries（县界虚线，不吃 LOD，只做视口粗筛）/ render_territory（★ 染色层：按 node.owner → Faction.color 填色，**不吃 LOD**，无主县跳过）/ render_water_polygons / render_water_lines。
- 县点：render_points（bbox 粗筛 + CITY_LEVEL_MIN_SCALE 门限）/ render_point / _draw_point_shape（square / diamond / triangle / circle）/ _point_radius / _effective_level（★ 优先读 World 的 Node.level，回退 GeoJSON props，clamp 1–10）。
- 道路：render_roads（线宽 ∝ 1/difficulty，同 difficulty 走 width_cache）。
- 标签：render_state_labels / render_county_labels / render_city_labels（按 CITY_LEVEL_MIN_SCALE 显隐，文字上移「半径 + 字高半 + point_gap」）/ render_label_group / draw_text（四向 halo 描边）/ resolve_style（按 span_px / size_divisor 在 min_size–max_size 间插值字号）。
- 高亮：set_selected / _redraw_selected / set_hover / _redraw_hover（受 MAP_INTERACTION 开关控制）/ _highlight_node / _highlight_region / _node_ring / _county_ring / _project_ring / _node_owner_color。

### 5.15 game/ui/main_window.py

唯一顶层装配者与跨模块事件枢纽。持有 root / settings / game_state / map_canvas / map_controller / side_panel / top_bar / status_bar / edit_session / _world / _geo_data / _scenario_path / _baseline_raw。

布局：row0 TopBar —— row1 PanedWindow（MapCanvas weight=4 + SidePanel weight=1）—— row2 StatusBar。

| 分组 | 方法 |
|---|---|
| 初始化 | __init__（Tk → install_tk_excepthook → title/minsize → maximize → _pick_font_family → SettingsManager + apply → GameState → _setup_theme → _build_layout → _bind_shortcuts → WM_DELETE_WINDOW → after(120, _auto_load_default)）/ _setup_theme（clam 主题）/ _build_layout / _bind_shortcuts |
| 加载 | _auto_load_default / _load_default_scenario / _load_scenario / open_geojson / load_geojson |
| 地图联动 | _on_location_change（拼 州·郡·县·势力 + 经纬度写状态栏，并驱动 tooltip）/ _faction_at / _on_zoom_change / _locate_to_list |
| 气泡 | _update_tooltip / _show_tooltip（复用一个 overrideredirect Toplevel）/ _hide_tooltip |
| 地图右键 | _on_map_right_click / _build_node_context_menu / _build_empty_context_menu / _edit_node_from_map / _edit_faction_from_map / _map_intel |
| 菜单分发 | _on_menu_action（覆盖 quit / select_scenario / save_scenario / save_scenario_as / undo / redo / new_game / load_game / settings / view_zoom_* / view_cities / view_characters / view_troops / end_turn / help_about…） |
| 游戏流程 | _end_turn（编辑模式直接 return）/ _open_settings（单例复用 _settings_win）/ _on_settings_applied / _confirm_and_new_game |
| 编辑会话 | open_edit_dialog（置 _modal_open + wait_window）/ on_edit_executed / _redraw_map / _refresh_title / _sync_undo_redo_state / _load_raw_scenario |
| 保存关闭 | _on_close / _confirm_discard / _on_save_scenario / _on_save_as / _save_to_path / _on_undo / _on_redo / _on_select_scenario / run |

快捷键：`+` / `-` / `=` 缩放、`0` 复位、Ctrl+O 打开地图、Ctrl+S 保存、Ctrl+Shift+S 另存、Ctrl+Z 撤销、Ctrl+Shift+Z 重做。

★ _refresh_title（未保存提示，唯一刷新入口）：

```python
def _refresh_title(self):
    """窗口标题：APP_TITLE [- 剧本文件名] [*]"""
    title = C.APP_TITLE
    world = getattr(self, "_world", None)
    if world is not None and self._scenario_path:
        title = f"{title} - {os.path.basename(self._scenario_path)}"
    if self.edit_session is not None and self.edit_session.is_dirty():
        title += " *"
    self.root.title(title)
```

并在 _sync_undo_redo_state 末尾调用（唯一刷新入口）：

```python
def _sync_undo_redo_state(self):
    if self.edit_session is None:
        self.top_bar.set_edit_state(False, False)
    else:
        self.top_bar.set_edit_state(
            self.edit_session.can_undo(),
            self.edit_session.can_redo(),
        )
    self._refresh_title()
```

★ _on_settings_applied(changed_paths) 的分支：

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

★ _build_node_context_menu（含「编辑势力」）：

```python
def _build_node_context_menu(self, menu, node_id):
    world = getattr(self, "_world", None)
    node = world.nodes.get(node_id) if world is not None else None

    faction = None
    if node is not None and node.owner and world is not None:
        faction = world.factions.get(node.owner)
        if faction is None:
            logger.warning("据点 %s 的 owner=%s 无对应势力",
                           node_id, node.owner)

    edit_state = "normal" if self.editable else "disabled"

    menu.add_command(label="编辑据点",
                     command=lambda: self._edit_node_from_map(node_id),
                     state=edit_state)

    if faction is not None:
        menu.add_command(
            label=f"编辑势力：{faction.name}",
            command=lambda fid=faction.id: self._edit_faction_from_map(fid),
            state=edit_state,
        )

    # ... 情报 / 定位到列表 略
```

★ _edit_faction_from_map：

```python
def _edit_faction_from_map(self, faction_id):
    """地图右键 →「编辑势力」：与面板右键共用 edit_faction。"""
    logger.info("地图右键编辑势力：%s", faction_id)
    world = getattr(self, "_world", None)
    if world is None or self.edit_session is None:
        return
    f = world.factions.get(faction_id)
    if f is None:
        logger.warning("势力不存在：%s", faction_id)
        return
    from game.ui.dialogs.faction_edit import edit_faction
    if edit_faction(self.root, world, f,
                    self.edit_session, self.open_edit_dialog):
        self.side_panel.refresh_all()
        self.on_edit_executed()
```

### 5.16 game/ui/top_bar.py / status_bar.py

**TopBar（302 行）**

- 左侧信息区：条目来自 `game_state.get_display_items()`，存 `self.items: key -> (value_lbl, value_var)`；`_hover` 换底色；`_open_info_window` / `_close_info_window` 弹 620×460 占位窗。
- 刷新机制：`_REFRESH_INTERVAL_MS = 200`，自递归 `after` 全量 `value_var.set(...)`。
- 菜单（全部 tearoff=0）：
  - 文件：选择剧本 / 保存(Ctrl+S) / 另存为(Ctrl+Shift+S) / 退出
  - 编辑：撤销(Ctrl+Z) / 重做(Ctrl+Shift+Z)
  - 游戏：新游戏 / 读取存档 / 保存存档 / 游戏设置 / 退出
  - 势力：内政▸ 军事▸ 外交▸ / 结束本回合
  - 命令：移动 / 攻击 / 计略 / 待机
  - 查看：地图缩放（放大/缩小/复位）/ 城市列表 / 人物列表 / 部队列表
  - 帮助：操作说明 / 关于
  - 右侧绿色「进行 ▶」按钮 → `on_action("end_turn")`
- `_add_edit_command`：登记 (menu, index) 到 `_edit_entries`；覆盖文件菜单 3 项 + 编辑菜单 2 项，共 5 项。
- `set_edit_enabled(enabled)`：按 APP_MODE 一次性全启 / 全禁 `_edit_entries`。
- `set_edit_state(can_undo, can_redo)`：仅对编辑菜单 index 0/1 置灰，且与 `_edit_enabled` 相与。
- `set_game_mode(enabled)`：控制「进行」按钮 state。
- 动作统一走 `_emit(action)` → `on_action(action)`。

**StatusBar（51 行）**

三个 StringVar + Label，顶部 1px 分隔线：

- 左：`set_message(text)` —— 系统提示。
- 右：`set_location(text)`（鼠标位置 / 地区名）、`set_zoom(text)`。

### 5.17 game/ui/map_canvas.py / map_controller.py

**MapCanvas（353 行）**

- `_MIN_VALID_SIZE = 10`（小于视为布局未完成）。
- 节流：滚轮静默补绘 after(180)；标签补刷 after(30)；鼠标移动 after(40)。
- 缩放系数：滚轮 1.2，Button-4/5 与快捷键 1.25。
- 事件绑定：`<MouseWheel>` `<Button-4>` `<Button-5>` `<ButtonPress-1>` `<B1-Motion>` `<ButtonRelease-1>` `<Double-Button-1>`(复位) `<Button-3>`/`<Button-2>`(右键) `<Motion>` `<Leave>` `<Configure>`。
- 处理链：_on_wheel / _on_press（记 _drag / _press_xy）/ _on_drag（pan_pixels + renderer.pan + 标签节流）/ _on_release（位移 ≤ 4px 判为点击）/ _handle_click（unproject + find_location_detail，再点同县取消选中）/ _on_right_click（优先 _selected_node_id，否则点位置 node_id）/ _on_resize / _on_motion → _process_motion（回填 lon/lat/px/py，set_hover + _location_callback）/ _on_leave（清 hover + 回调 None）。
- 对外：load_geojson（GeoData.from_file + 水域 + 路网，后两者失败仅告警）/ reset_view / redraw / zoom / center_on / fit_to_node(node_id, fallback_lonlat, margin=0.7, max_scale=200) / _node_bbox / set_location_callback / set_zoom_callback / set_right_click_callback。
- fit 机制：_need_fit 标志 + _try_fit_now，_sync_canvas_size 从 canvas 实测尺寸同步 viewport。

**MapController**

面板访问地图的唯一接口，持有 `_canvas`，4 个纯转发方法：`center_on(lon, lat, min_scale=None)` / `reset_view()` / `zoom(factor)` / `fit_to_node(node_id, fallback_lonlat=None)`。`_canvas is None` 时空操作直接返回。选中与 hover 不经此入口。

### 5.18 game/ui/side_panel.py

- `TAB_KEYS = ("faction", "node", "character", "troop")`；`panels: dict[key -> panel]`；标签「势力 / 据点 / 人物 / 部队」。
- `panel(key)` / `select_panel(key)`（不在 TAB_KEYS 返回 None）/ `refresh_all()`（遍历 notebook tabs 调 refresh）/ `reload_panel_columns()`（遍历 panels 调 reload_columns，异常仅告警）。
- `set_edit_session(session, on_edit=None, open_dialog=None)`：存回调并把 session 注入每个面板的 `p.edit_session`。
- `on_panel_edit()`：refresh_all() + 转发 _edit_callback。
- `open_edit_dialog(dlg_factory)`：转发 _open_dialog_callback，无回调则直接 `dlg_factory()`。

### 5.19 game/ui/settings_window.py

tk.Toplevel，940×660、minsize 760×480、center_on_parent、grab_set 模态。

- 结构：_build_toolbar（搜索框 + 「仅显示已修改项」+ 显示 settings 路径）/ _build_body（Notebook，每个 tab = Frame + Canvas + Scrollbar + content window）/ _build_footer（脏值标签 + 保存 / 取消 / 恢复全部默认）。
- 草稿机制：所有控件改动只写 `self.draft`（path → value）；`_get(path)` 读取顺序 = draft → settings.get → None；`_refresh_dirty_label` 显示「已修改 N 项 / 尚无修改」。
- 控件构建：_add_item_row 按 kind 分派 —— _build_bool / _build_color / _build_number（min/max 校验 + 错误标签）/ _build_choice / _build_level_table。
- 保存流程 `_on_save`：收集需重启分组 → `settings.set_many(draft)` → `settings.save()` → `settings.apply()` → 记 changed → 清空 draft → `on_applied(changed)` → 销毁；draft 为空则直接销毁。
- 关闭 `_on_close`：有 draft 时 askyesnocancel（取消 = 不关 / 是 = 先保存 / 否 = 丢弃）。
- 筛选：_apply_filter（按当前 tab 范围过滤 label/path 关键字与 only_modified）。

**「面板列」tab 的 8 个方法：**

| 方法 | 作用 |
|---|---|
| _populate_panel_columns() | 用 schema.get_panel_columns_meta() 为每个面板建 CollapsibleSection |
| _init_panel_state(k, cols) | 读 settings 的 order/hidden，套到声明列上，得 [(key, title, visible), ...] |
| _build_panel_columns_ui(parent, k) | Listbox + 上移 / 下移 / 显示隐藏 / 全部显示 四按钮（双击 = 切换显隐） |
| _render_panel_listbox(k) | 重绘 Listbox（"●/○ 标题"）+ 同步 draft |
| _panel_move(k, delta) | 上移 / 下移 |
| _panel_toggle(k) | 切换显示 / 隐藏 |
| _panel_show_all(k) | 一键全显 |
| _reset_panel_columns(k) | 恢复声明顺序 + 全显示 |

另有 `_on_reset_group(section)`（按分组恢复默认）与 `_on_reset_all`（需确认，同步重置面板列 state）。

### 5.20 game/ui/character_info_window.py

```python
class CharacterInfoWindow(tk.Toplevel):
    """人物情报窗口：头像 + 五维雷达图 + 关系 + 生平（占位）。"""
    MAX_W = 200
    MAX_H = 200

    def __init__(self, master, character, world=None, font_family="TkDefaultFont"):
        # master 仍传 panel（保留 transient 关系）
        # self._top = master.winfo_toplevel()    ← 居中基准 / 跳转窗口 master
        # title = f"{character.display_name()} — 人物情报"
        #       未登场（appeared=False）→ 追加「（未登场）」后缀
        # 宽固定 600，高自适应（resizable(False, True)）；最小高 640
        # 四区：标题 / 上区（头像 + 雷达图）/ 关系 / 生平占位
        # update_idletasks → center_on_parent(self, self._top, 600, max(req_h, 640))
        # Escape 关闭

    def _build_ui(self):                    # 四区布局
    def _build_portrait(self, parent):      # 头像框
    def _build_radar(self, parent):         # ★ 雷达图（Canvas）
    def _axis_angles(self):                 # 5 轴角度：-90° + i * 72°
    def _axis_points(self):                 # 5 个最外层顶点坐标
    def _fill_and_edge(self):               # 势力色 / 无势力主题灰
    def _draw_data_polygon(self, canvas):   # 数据多边形 + 顶点小圆
    def _build_relations(self, parent):     # ★ 关系区（8 字段）
    def _relation_cell(self, parent, col, label, cid)   # 单值（父/母/配偶）
    def _relation_list_row(self, parent, label, ids)    # 列表（义兄弟/亲爱/厌恶）
    def _muted_label(self, parent, text)    # 灰色 "—"
    def _link_label(self, parent, cid, name)  # 蓝字可点姓名
    def _resolve_name(self, cid):           # id → display_name；未命中 → None
    def _build_bio(self, parent):           # 生平占位
    def _open_character(self, cid):         # ★ 跳转（新窗口 master = self._top）
    def _find_portrait_path(self):          # 头像路径
    def _load_portrait(self):               # 头像加载
```

**头像加载要点：**

- self._photo 保引用：Tk 不持 PhotoImage 引用，不存 → GC 后显示空白（§8.3 第 25 条）。
- Pillow 缺失降级：`try: from PIL import Image, ImageTk` 失败 → `_PIL_OK = False` → Label 提示「未安装 Pillow」。
- thumbnail 而非 resize：保比例，只缩不放。
- RGB 转换：`Image.open(path).convert("RGB")`。
- update_idletasks 后再居中：让 winfo_reqwidth/height 拿到实际尺寸。

**五维雷达图（纯 Canvas，不用 Pillow）：**

- Canvas 尺寸固定 340×340，坐标全硬编码，**不问 winfo_width**（布局未完成时拿到的是 1）。
- 5 轴：-90° 起，顺时针 72° 步进（统 → 武 → 智 → 政 → 魅）。
- 5 层同心五边形网格（对应 20 / 40 / 60 / 80 / 100）；中心到顶点的轴线。
- 数据多边形：`stipple="gray50"` 模拟半透明填充 + 势力色描边；无势力 → `#7F8C8D`。
- 轴上限 100：> 100 截到 100 画；数值列表仍显示真实值。
- 轴标签单字（统/武/智/政/魅）+ 标签下小字数值；数据顶点小圆 r=3。

**关系区（8 字段全画）：**

- 顺序：父 / 母 / 配偶（同三列等宽）→ 义兄弟 / 亲爱 / 厌恶（各一行）→ 血缘 + 世代（同一行）。
- 三列等宽用 `grid + columnconfigure(uniform="rel")`，不用 pack expand（§8.3 第 29 条）。
- 姓名带表字（display_name），**不带势力**。
- 可点：蓝字 `#1F6FBF` + `cursor="hand2"` → 新开窗口。
- 查不到的人 → 灰色 `#999999` "—" 不可点（§8.3 第 33 条）。
- 血缘是字符串标签不可点；世代是数字。

**窗口：**

- 宽固定 600，高自适应（`resizable(False, True)`）；最小高 640。
- 居中基准 = 游戏主窗口（§8.3 第 32 条）。
- **不做单例**：重复右键会开多个窗口。

**world 参数：** 可选（默认 None）；None 时关系区全部显示 "—"，雷达图用主题灰。由 CharacterPanel._open_info_window 传入。

### 5.21 game/ui/dialogs/

| 文件 | 内容 |
|---|---|
| field_spec.py | Field NamedTuple（key / label / kind / default / options / min / max / editable / hint / display_fn） |
| edit_dialog.py | EditDialog：通用数据驱动弹窗，`get_changed() -> (new_values, old_values)` |
| node_fields.py | NODE_FIELDS，10 项 |
| faction_fields.py | FACTION_FIELDS，8 项 |
| node_edit.py | `edit_node(parent, world, node, session, open_dialog) -> bool`（含郡治互斥） |
| faction_edit.py | `edit_faction(parent, world, faction, session, open_dialog) -> bool` |

详见 §9.4 / §9.5 / §9.6。

### 5.22 game/ui/panels/list/

通用列表面板框架，核心是 GenericListPanel（panel.py），分工见 §2.1。

- 构建 UI：搜索框 + 分组条 + Treeview + 滚动条（_build_ui，Treeview 部分抽在 _build_tree_in）。
- 调度：排序（_on_heading_click）、分组（_build_groups）、搜索（_apply_search，多词 AND，过滤在分组前）。
- 右键：_on_right_click 拼 MenuContext → context_menu_items 配置 → build_menu(edit_enabled=) 弹出。
- 多选：`selectmode="extended"` + Ctrl+A 全选。
- 双向定位：scroll_to_row（展开祖先 + 滚动 + 选中，_syncing 防递归）、locate_on_map（默认 node_id / coords）。
- 列配置：_resolve_columns()（读 style.PANEL_COLUMNS[PANEL_KEY] → (可见列 tuple, NAME_COLUMN)；order 未列的 key 追加末尾；hidden 过滤；NAME_COLUMN 锁定必显；无 PANEL_KEY 退化为原 COLUMNS）/ reload_columns()（重解析 + 重建 Treeview + refresh；若排序键已被隐藏则清除排序状态）。
- 编辑会话：`edit_session` 类属性 + _open_dialog / _notify_edit。
- 三处 `self.COLUMNS` → `self._visible_columns`：_match_one / _column_index / _insert_row。

### 5.23 game/ui/panels/{node,character,faction,troop}_panel.py

**node_panel.py** — PANEL_KEY = "node"，DEFAULT_GROUP = ("state", "county")

- 行模型 NodeRow：node_id / name / type / level / coords / state_name / county_name / owner_id / owner_name / is_capital / person_count（另预留 governor_name）。display_type = 郡治 或 type。
- `fetch_rows` 循环外调一次 `world.count_characters_by_node()`，把人数传给 `NodeRow.from_node(..., person_count=)`；聚合不缓存，每次 refresh 现算（登场开关 / undo / redo 后自动跟着变）。
- COLUMNS：州 52 / 郡 62 / 规模 42 / 类型 46 / 势力 64 / 主官 56 / 人物 42；NAME_COLUMN = 县（110，左对齐）。
- GROUP_DIMS：faction(势力) / state(州) / county(郡) / type(类型)。
- 右键：行名（禁用）/ 编辑（单选，edit=True）/ 据点情报 / 人物情报 / 势力情报 / 定位到地图 / 全部展开折叠。情报三项目前只写日志。

**character_panel.py** — PANEL_KEY = "character"，DEFAULT_GROUP = ("faction",)

- 行模型 CharacterRow：id / name / family_name / sex / faction_id / faction_name / node_id / node_name / role / **appeared** / 五维 / coords。
- COLUMNS：势力 60 / 所在 76 / 身份 48 / 统 34 / 武 34 / 智 34 / 政 34 / 魅 34；NAME_COLUMN = 姓名（110，左对齐，`lambda r: r.name` —— 去表字）。
- GROUP_DIMS：faction(势力，默认) / node(所在) / role(身份) / sex(性别) / **appear(登场 → 已登场 / 未登场)**。默认分组维持 ("faction",)，不强制先按登场分。
- `priority_name()`：返回玩家势力名，用于分组置顶（只对最外层生效）。
- 右键：人物情报 / 复制编号 / **设为登场·设为未登场** / 定位到据点 / 全部展开折叠。
  - 开关标签按右键那行的 appeared 现状态决定：已登场 →「设为未登场」，未登场 →「设为登场」。
  - 纯开关：只翻 appeared，**不碰** faction / node / location / role（设为登场后仍「在野」；设为未登场保留归属，可逆）。
  - `edit=True` 标识 → 非编辑模式下由 build_menu 统一置灰（不在入口里写模式判断）。
- 行数 = World.characters 全量（1049），未登场的人也在列表里（否则没法编辑他们）。

**faction_panel.py** — PANEL_KEY = "faction"，CUSTOM_GROUPING = True

色块：

- __init__ 加 `self._swatches = {}` + `self._swatch_size = self._compute_swatch_size()`
- `_compute_swatch_size()`：读 ttk 主题行高，返回 max(8, 行高 − 6)
- `_make_swatch(color)`：先整块填 `#000000`，再在 (1, 1, size-1, size-1) 填势力色
- `_swatch_for(row)`：PhotoImage 缓存，refresh 前 clear()
- NAME_COLUMN 用 `Column(..., image=self._swatch_for)`

行模型与列：

```python
@dataclass(frozen=True)
class FactionRow:
    id: str
    name: str
    color: str
    prestige: int
    gold: int
    food: int
    troops: int              # ★ 派生值
    stance: int
    ruler_name: str
    node_count: int = 0
    char_count: int = 0

    @classmethod
    def from_faction(cls, f, world, node_count=0, char_count=0):
        ruler = world.characters.get(f.ruler_id)
        return cls(
            id=f.id, name=f.name, color=f.color,
            prestige=f.prestige, gold=f.gold, food=f.food,
            troops=f.troops,
            stance=f.stance,
            ruler_name=ruler.name if ruler is not None else "—",
            node_count=node_count, char_count=char_count,
        )
```

类体内必须显式绑定 `COLUMNS = COLUMNS`（§8.3 第 27 条）：

```python
class FactionPanel(GenericListPanel):
    COLUMNS = COLUMNS           # ★ 必须：否则 self.COLUMNS 取基类默认 ()
    PANEL_KEY = "faction"
    CUSTOM_GROUPING = True
    ...
```

fetch_rows 循环外算一次聚合：

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

COLUMNS（模块级，8 列）：

```python
COLUMNS = (
    Column("ruler",    "君主", 70, "center", lambda r: r.ruler_name),
    Column("prestige", "威望", 60, "e", lambda r: f"{r.prestige:,}", sort_numeric=True),
    Column("gold",     "金",   60, "e", lambda r: f"{r.gold:,}",     sort_numeric=True),
    Column("food",     "粮",   70, "e", lambda r: f"{r.food:,}",     sort_numeric=True),
    Column("troops",   "兵力", 70, "e", lambda r: f"{r.troops:,}",   sort_numeric=True),
    Column("nodes",    "据点", 55, "e", lambda r: str(r.node_count), sort_numeric=True),
    Column("chars",    "人物", 55, "e", lambda r: str(r.char_count), sort_numeric=True),
    Column("stance",   "关系", 50, "center", lambda r: r.stance_text),
)
```

_edit 复用 faction_edit：

```python
def _edit(self, row):
    if self.edit_session is None:
        return
    world = getattr(self.game_state, "world", None)
    if world is None:
        return
    f = world.factions.get(row.id)
    if f is None:
        logger.warning("势力不存在：%s", row.id)
        return
    logger.debug("编辑势力：%s %s", f.id, f.name)

    from game.ui.dialogs.faction_edit import edit_faction
    if edit_faction(self, world, f, self.edit_session, self._open_dialog):
        self._notify_edit()
```

**troop_panel.py** — PANEL_KEY = "troop"，**空壳**：`fetch_rows()` 恒返回 []；无 GROUP_DIMS、无右键菜单覆写（继承基类）。行模型 TroopRow（name / general / troops / morale / state）；COLUMNS：主将 80 / 兵力 70 / 士气 60 / 状态 80；NAME_COLUMN = 部队。

### 5.24 game/ui/widgets/collapsible.py / window_utils.py

**CollapsibleSection** — `CollapsibleSection(master, title, desc="", on_reset=None, expanded=False, font_family=...)`；属性 `body`（内容容器）；方法 `toggle()` / `set_expanded(flag)`（pack/pack_forget body 并切换 ▶/▼）。on_reset 非空时右侧出现「↺ 恢复本组默认」，回调签名 `on_reset(self)`。

**window_utils** — 两个函数：`maximize(window)`（依次试 state("zoomed") / attributes("-zoomed") / geometry 兜底）、`center_on_parent(child, parent, width, height)`（相对 parent 居中并夹在屏幕内）。

### 5.25 tools/

| 文件 | 作用 |
|---|---|
| build_scenario_190.py | 生成 190 年默认剧本：FACTIONS 常量（name/color/stance/capital/territories/max_cities）+ CORE 人物种子 + 网络投票扩展 + affinity 兜底 + 全量人物 appeared 预计算 |
| 头像.py | 头像批量重命名 / 重名复制 / 对账。顶部三开关：APPLY / REMOVE_ORIGINAL / FORCE |
| characters/314.py | 从 xlsx 生成 characters.json |
| map/*.py | 地图预处理（县域边界生成 / 精简 / 道路生成 / 重叠与过小面积诊断） |

**头像.py 行为表：**

| 场景 | 处理 |
|---|---|
| 蔡瑁.jpg，数据唯一 | 重命名 → 0088-蔡瑁.jpg |
| 张南.jpg，数据两人 | 复制 2 份 → 0651-张南.jpg、0652-张南.jpg；原文件保留（REMOVE_ORIGINAL = False） |
| 数据里无此人 | 不动，归入「未匹配-不动」 |
| 已是 {id}-{name} 格式 | 跳过（stem 匹配不上人名，归入「未匹配-不动」） |
| 目标已存在 | 跳过并报告（FORCE = False） |

load_characters 兼容 `{id: {...}}` / `{"characters": {...}}` / `[...]` 三种结构。

---

## 6. 程序完整运行流程

### 6.1 启动阶段

```text
main.main()
 ├─ setup_logging()                 LOG_ENABLED=True → userdata/logs/app_YYYYMMDD_HHMMSS.log
 │                                  LOG_ENABLED=False → logging.disable(CRITICAL)，返回 None
 ├─ install_sys_excepthook()        LOG_ENABLED=True → 未捕获异常 → CRITICAL
 │                                  LOG_ENABLED=False → no-op，交回 Python stderr
 ├─ logger.info("应用启动…")
 └─ MainWindow()
     ├─ install_tk_excepthook(root) ★ 紧跟 Tk() 之后
     │                              LOG_ENABLED=False 时为 no-op
     ├─ SettingsManager → apply()   就地写回 style
     ├─ _build_layout()             TopBar + MapCanvas + SidePanel + StatusBar
     │   └─ set_game_mode / set_edit_enabled  按 APP_MODE 切按钮
     ├─ _bind_shortcuts()
     └─ after(120, _auto_load_default)
         ├─ load_geojson(DEFAULT_MAP_PATH, silent=True)
         └─ _load_default_scenario() → _load_scenario(path)
```

顺序约束：setup_logging() 必须在 MainWindow() 之前，否则构造期间的日志丢失（§8.3 第 48 条）。

### 6.2 地图 + 剧本加载流程

```text
load_geojson(path, silent)
 └─ MapCanvas.load_geojson
     ├─ GeoData.from_file(DEFAULT_MAP_PATH)      分类 / LOD / bbox / 索引
     ├─ load_water(DEFAULT_WATER_PATH)           失败仅告警
     ├─ load_roads(DEFAULT_ROADS_PATH)           失败仅告警
     └─ renderer.set_data(geo) → redraw

_load_scenario(path)                                 编辑模式下额外做 ①–④
 ├─ ScenarioLoader.load(path, geo_data)              §5.10
 ├─ game_state.sync_from_world(world)
 ├─ renderer.set_world(world)
 ├─ side_panel.refresh_all()
 ├─ map_canvas.redraw()
 ① baseline_snap = ScenarioWriter.serialize(world)
 ② edit_session = EditSession(world, baseline_snap)
 ③ self._baseline_raw = raw                      写回模板
 ④ side_panel.set_edit_session(...) → _sync_undo_redo_state()（含 _refresh_title）
```

### 6.3 剧本生成流程（离线）

```text
tools/build_scenario_190.py
 ├─ FACTIONS 常量（52 家：name / color / stance / capital / territories / max_cities）
 ├─ territories 展开：4 位 = 整郡，6 位 = 单县；按 level 优先取大城市，受 max_cities 限制
 ├─ 人物分配：CORE 手写种子 + 网络投票扩展 + affinity 兜底（只分 id ≤ 1000 的历史人物）
 ├─ appeared 预计算：compute_appeared（规则见 §4.4），全量 1049 人都写
 └─ 写出 scenarios/default.json（factions / characters / nodes 三段，均以 id 为键）
```

### 6.4 主循环交互

| 触发 | 调用链 |
|---|---|
| 鼠标移动 | _on_motion → 40ms 节流 → _process_motion |
| ↳ 反查 | viewport.unproject → data.find_location_detail(lon, lat) → dict |
| ↳ 拼装 | MapCanvas._location_callback(info) → MainWindow._on_location_change(info) |
| ↳ 势力 | MainWindow._faction_at(node_id) → world.node(id) → node.owner → world.faction(id) → f.name |
| ↳ 显示 | status_bar.set_location(text) → 州 · 郡 · 县 · 势力 （经度°E, 纬度°N） |
| 鼠标离开 | _on_leave → _location_callback(None) → 状态栏清空 |
| 滚轮 / 拖拽 | viewport.zoom / pan_pixels → renderer.zoom / pan |
| 顶部信息栏 | 200ms 轮询 game_state.get_display_items() |
| 设置保存 | _on_settings_applied → 地图相关则 map_canvas.redraw()；PANEL_COLUMNS* 则 side_panel.reload_panel_columns() |
| 面板列重载 | side_panel.reload_panel_columns() → 各 panel reload_columns() → _resolve_columns() 读 style.PANEL_COLUMNS → _build_tree_in() + refresh() |
| 据点右键 → 定位 | MenuItem「定位到地图」 → GenericListPanel.locate_on_map → MapController.fit_to_node |
| 据点右键 → 展开/折叠 | MenuItem「全部展开/折叠」 → GenericListPanel._toggle_all |
| 据点列头点击 | _on_heading_click → _sort_key/_sort_desc → refresh |
| 据点分组切换 | GroupBar._toggle → on_change → NodePanel.refresh |
| 人物列头点击 | _on_heading_click → refresh |
| 人物右键 → 定位到据点 | MenuItem「定位到据点」 → GenericListPanel.locate_on_map |
| 人物右键 → 人物情报 | CharacterPanel._open_info_window(row) → world.character(row.id) → CharacterInfoWindow(self, ch, world=world, ...) |
| ★ 情报窗加载头像 | _find_portrait_path() 拼 {id}-{name}.{ext} → Image.open → convert("RGB") → thumbnail → ImageTk.PhotoImage → self._photo 保引用 |
| ★ 情报窗画雷达图 | _build_radar() → Canvas 硬编码坐标画 5 层五边形 + 轴线 + 数据多边形，无 winfo_width 查询 |
| ★ 情报窗关系区 | _build_relations() → 8 字段；_resolve_name(id) → world.character(id) → display_name()；命中 → _link_label（蓝字 + hand2），未命中 → _muted_label（灰 "—"） |
| ★ 情报窗点关系人 | _link_label 绑 <Button-1> → _open_character(cid) → 新 CharacterInfoWindow(self._top, ch, world=self.world, ...) |
| ★ 情报窗居中 | center_on_parent(self, self._top, 600, max(winfo_reqheight(), 640)) |
| 人物分组切换 | GroupBar._toggle → on_change → CharacterPanel.refresh → priority_name 玩家置顶 |
| 搜索输入 | SearchBar._on_write → _on_search_change → refresh |
| 左键点选 | _on_release（位移 ≤ 4px）→ _handle_click → renderer.set_selected |
| hover 高亮 | _process_motion → renderer.set_hover → _redraw_hover（吃 5 开关） |
| hover tooltip | _process_motion → _location_callback → MainWindow._on_location_change → _update_tooltip |
| 地图右键（县上） | MapCanvas._on_right_click → MainWindow._on_map_right_click → _build_node_context_menu |
| 地图右键（空白） | _on_map_right_click(node_id=None) → _build_empty_context_menu |
| 反向定位 | 右键「定位到列表→据点」→ _locate_to_list → side_panel.select_panel → NodePanel.scroll_to_row |
| 设置 → 面板列 | 设置窗口 panels tab → Listbox 上移/下移/显示隐藏 → 「保存」→ settings.save/apply → on_applied → _on_settings_applied → side_panel.reload_panel_columns |
| 据点右键 → 编辑 | NodePanel._edit → dialogs.node_edit.edit_node → EditDialog → dlg.get_changed() → 郡治互斥（可选）→ edit_session.execute(cmd) → _notify_edit |
| 地图右键 → 编辑据点 | _edit_node_from_map(node_id) → 同一个 edit_node → session.execute → side_panel.refresh_all() + on_edit_executed() |
| 地图右键 → 编辑势力 | _edit_faction_from_map(fid) → dialogs.faction_edit.edit_faction → EditDialog（FACTION_FIELDS）→ session.execute(FactionEditCommand) → side_panel.refresh_all() + on_edit_executed() |
| 势力面板右键 → 编辑 | FactionPanel._edit → dialogs.faction_edit.edit_faction（与地图右键同一函数）→ session.execute → _notify_edit |
| ↳ 编辑弹窗字段 | 编号 / 势力名 / 颜色 / 威望 / 关系 / 金钱 / 军粮 / **兵力**（后三者 readonly，值取 property） |
| ↳ 编辑后刷新 | SidePanel.on_panel_edit() → refresh_all()（4 面板）→ _edit_callback → MainWindow.on_edit_executed() → _sync_undo_redo_state()（含 _refresh_title）+ _redraw_map() |
| Ctrl+Z / Ctrl+Shift+Z | _on_undo/_on_redo（_modal_open 时直接 return）→ edit_session.undo/redo → refresh_all + _sync_undo_redo_state（含 _refresh_title）+ _redraw_map |
| Ctrl+S / Ctrl+Shift+S | _on_save_scenario（无改动 → 状态栏提示，不写文件）→ _save_to_path → ScenarioWriter.save(world, path, raw, baseline) → rebase + clear + _sync_undo_redo_state（含 _refresh_title） |
| 未保存提示 | 编辑/undo/redo/保存/加载后，_sync_undo_redo_state → _refresh_title → root.title 追加或去掉 " *" |
| 关窗 / 选择剧本拦截 | _confirm_discard() → edit_session.is_dirty() → askyesnocancel → 非 True 则中止 |
| 编辑入口置灰 | TopBar.set_edit_enabled(editable) 批量控菜单项；右键 MenuItem(edit=True) → build_menu(edit_enabled=edit_session is not None)；地图右键 tk.Menu 直建 → state = "normal" if self.editable else "disabled" |

### 6.5 模块协作关系

```text
main.py ── config.logging_setup（setup_logging / sys hook / LOG_ENABLED）
   │
   └─ ui.main_window ──┬─ config.settings_manager ─ config.style
                       │                            └ config.settings_schema
                       │                                 └ get_panel_columns_meta()
                       ├─ core.game_state
                       ├─ core.scenario ─── core.world ─── core.faction
                       │                    ├─ core.character
                       │                    └─ core.node
                       │                    └─ count_nodes_by_owner / count_characters_by_faction
                       │                       count_characters_by_node（均过 appeared）
                       ├─ core.edit_session ─── core.edit_commands
                       ├─ core.scenario_writer（serialize / diff / save）
                       ├─ ui.top_bar
                       ├─ ui.status_bar
                       ├─ ui.map_canvas ─── map.viewport
                       │                   map.renderer ─── map.geo_data
                       │                                  └ core.territory（保留）
                       │   hover 回调 → MainWindow._on_location_change
                       │   右键回调 → MainWindow._on_map_right_click
                       │                ├─ _edit_node_from_map → dialogs.node_edit
                       │                └─ _edit_faction_from_map → dialogs.faction_edit
                       ├─ ui.map_controller
                       ├─ ui.settings_window ──── config.settings_schema
                       │                       └─ ui.widgets.collapsible
                       ├─ ui.character_info_window ──── Pillow（Image / ImageTk，仅头像）
                       │                            ├─ Canvas（雷达图，无 Pillow）
                       │                            ├─ ui.window_utils.center_on_parent
                       │                            └─ core.world.character（关系区解析）
                       └─ ui.side_panel ──── panels.faction_panel ──┐
                                          ├─ panels.node_panel ─────┤
                                          │   └─ dialogs.node_edit ─┤─ dialogs.edit_dialog
                                          │                         │  └─ dialogs.field_spec
                                          │                         │     + node_fields / faction_fields
                                          ├─ panels.character_panel ┤── panels.list（通用框架）
                                          │   └─ ui.character_info_window
                                          └─ panels.troop_panel ────┘
                                          └─ reload_panel_columns()
                       config.constants ──── LOG_ENABLED / APP_MODE
                       config.logging_setup ──── userdata/logs/*.log
tools.build_scenario_190  ──── scenarios/default.json
tools.头像                 ──── assets/portrait/*
tools.characters.314      ──── assets/characters.json

编辑链路：面板/地图右键 → dialogs.{node_edit,faction_edit} → EditDialog（数据驱动）→ Command → EditSession.execute → 面板刷新 + 地图重绘 + 标题刷新。 UI 层不得直接改 World，一切经 Command（§8.3 第 38 条）。

人物情报链路：人物面板右键「人物情报」→ CharacterInfoWindow(panel, ch, world, ...) → 主窗口居中 → 四区（头像/雷达图/关系/生平）。点关系人 → _open_character → 新 CharacterInfoWindow(self._top, ch, world=self.world, ...)。雷达图纯 Canvas；头像走 Pillow；关系区查 world.character。

兵力链路：势力面板 fetch_rows → FactionRow.from_faction(f) → f.troops property → 遍历 world.nodes（_nodes_ref）求 owner 匹配的 troops 之和。势力编辑弹窗 FACTION_FIELDS → Field("troops", "readonly") → EditDialog._build_field 走 getattr(faction, "troops") 读 property。

日志：所有模块 logger = logging.getLogger(__name__)，根 logger 只挂一个 FileHandler（userdata/logs/）。LOG_ENABLED=False 时整条链路静默。
```

---

## 7. 全局变量与配置项

### 7.1 constants.py

```python
# 路径
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
DEFAULT_MAP_PATH = ASSETS_DIR / "map.geojson"
DEFAULT_WATER_PATH = ASSETS_DIR / "water.geojson"
DEFAULT_ROADS_PATH = ASSETS_DIR / "roads.geojson"
DEFAULT_CHARACTERS_PATH = ASSETS_DIR / "characters.json"
SCENARIOS_DIR = PROJECT_ROOT / "scenarios"
DEFAULT_SCENARIO_PATH = SCENARIOS_DIR / "default.json"

# 窗口
APP_TITLE = "暗耻三国志"
WINDOW_SIZE = "1440x900"        # 未被使用（窗口走 maximize）
MIN_WINDOW_SIZE = (1024, 640)

# 应用模式（编译期）
MODE_EDIT = "edit"     # 剧本编辑模式
MODE_GAME = "game"     # 游戏模式（未实现）
APP_MODE  = MODE_EDIT  # 全局开关：编译期切换

# 日志
LOG_ENABLED = True     # ★ 编译期日志总开关：False 一键关闭全部日志
LOG_DIR = PROJECT_ROOT / "userdata" / "logs"
```

APP_MODE 只被 MainWindow.__init__ 读一次（self.editable），其余模块读 `edit_session is not None`（§8.3 第 42 条）。

LOG_ENABLED 只被 logging_setup.py 读（三处入口），其余模块不感知。

### 7.2 设置窗口可改

设置窗口（`settings_window.py`）把下列 style 项暴露成 UI，保存后写入 userdata/settings.json 并就地改写 style 模块：

| Tab | 内容 |
|---|---|
| 外观 | THEME 各色、FONT_SIZES、FONT_CANDIDATES（部分项需重启，保存后弹提示） |
| 操作 | MAP_INTERACTION 5 个 hover 开关 |
| 面板列 | node / character / faction / troop 四面板的列顺序与显隐 |
| 游戏 | 游戏相关项（骨架，内容少） |

保存流程：草稿 → settings.set_many → save → apply → 回调 _on_settings_applied（§5.19）。

### 7.3 代码内常量

| 位置 | 值 | 含义 |
|---|---|---|
| MapCanvas._MIN_VALID_SIZE | 10 | 布局未完成阈值 |
| TopBar._REFRESH_INTERVAL_MS | 200 | 信息栏轮询 |
| GeoData._assign_lod 四档 | 0 / 15 / 45 / 100 | 县界 / 水体共用；染色层不吃 |
| MAP_STYLE.city_line.dash | (3, 5) | 县界虚线节奏 |
| MapCanvas.fit_to_node 的 margin | 0.7 | 定位留边距 |
| MapCanvas.fit_to_node 的 max_scale | 200 | 小 boundary 放大上限 |
| hover 节流 | 40 ms | _process_motion |
| 标签刷新节流 | 30 ms | _schedule_label_refresh |
| settle redraw | 180 ms | 滚轮静默后补绘 |
| renderer.zoom 重投影阈值 | _cum_scale > 2.0 / < 0.5 | 超过触发 draw_full |
| 据点面板默认分组 | ["state", "county"] | GroupBar.initial_selected |
| 人物面板默认分组 | ["faction"] | GroupBar.initial_selected |
| 人物面板玩家势力置顶 | priority_name = faction.name | 只对最外层生效 |
| 势力色块尺寸 | 行高 − 6 | 动态计算（_compute_swatch_size，最小 8） |
| 势力色块黑边 | 1 px | img.put("#000000", to=(0,0,size,size)) |
| character_id_range 默认 | [1, 1000] | 老剧本兼容用；190 剧本不写 |
| character_id_range 不写 | [1, 9999] | 全部加载 |
| Character.appeared 默认 | True | 老剧本无该字段 → 全部登场 |
| 登场判定分界 | year − birth_year ≥ 16 | 另有「已分配势力 → true」优先 |
| 190 剧本势力 / 人物 / 登场 / 据点 | 52 / 1049 / 469 / 555 | 定稿 |
| Character._DEFAULT_STAT | 50 | 五维缺省值 |
| 选中描边 | #00C8FF / 2px | renderer.SELECT_TAG |
| hover 描边 | #00BFFF / 2px | renderer.HOVER_TAG |
| hover 填充 | lighten_color(color, 0.45) | 蒙白 45%（无主县 #F5F5F5） |
| 点击判定阈值 | 4 px | 位移 ≤ 4px 算点击，否则拖拽 |
| 面板 selectmode | extended | 多选（Ctrl / Shift / Ctrl+A） |
| MAP_INTERACTION 默认 | tooltip 开；border / fill / faction_all / region 关 | 5 开关 |
| PANEL_COLUMNS 默认 | {order: [], hidden: []} × 4 panel | 空 = 用 COLUMNS 声明顺序 + 全显示 |
| 面板列配置 tab | TABS 里 key = panels | 位于「操作」与「游戏」之间 |
| 面板列 UI | Listbox + 上移/下移/显示隐藏 | 双击 = 切换显隐 |
| 头像目录 | assets/portrait/ | 当前 739 张 |
| 头像命名 | {id}-{name}.{ext} | |
| 头像扩展名 | .jpg/.jpeg/.png/.gif/.bmp/.webp | 头像.py 的 IMAGE_EXTS |
| 头像缩放上限 | 200 × 200 | CharacterInfoWindow.MAX_W / MAX_H |
| 头像重采样 | Image.LANCZOS | 高质量缩略 |
| 头像.py 默认开关 | APPLY / REMOVE_ORIGINAL / FORCE = False | 三开关全保守 |
| APP_MODE 默认 | MODE_EDIT（= "edit"） | 编译期切换 |
| EditSession.max_depth | 5 | undo 栈深度，超出裁剪最旧命令 |
| ScenarioWriter 元字段 | version/id/name/desc/start/player_faction/character_id_range | 不参与 diff |
| 日志目录 | userdata/logs/ | constants.LOG_DIR |
| 日志文件名 | app_YYYYMMDD_HHMMSS.log | 秒级唯一，每次启动一个 |
| _MAX_LOG_FILES | 30 | 超出删最旧（_cleanup_old_logs） |
| 日志级别 | 文件 DEBUG；无控制台 handler | 只挂 FileHandler，终端静默 |
| 日志格式 | 时间.毫秒 [级别] [session] 模块: 消息 | %(asctime)s.%(msecs)03d … |
| session id | 8 位十六进制 | uuid.uuid4().hex[:8] |
| 日志时间格式 | %Y-%m-%d %H:%M:%S | Formatter(datefmt=…) |
| install_tk_excepthook 时机 | Tk() 之后立即 | 越早越好，构造期回调异常才抓得到 |
| LOG_ENABLED 默认 | True | 编译期开关，风格同 APP_MODE |
| 未保存提示格式 | `APP_TITLE [- 剧本文件名] [ *]` | 唯一刷新入口 _sync_undo_redo_state → _refresh_title |
| 未保存星号 | " *"（空格 + 星号） | 编辑后出现；undo 回 baseline / 保存 / 加载后消失 |
| 地图右键「编辑势力」显示条件 | 该据点有 owner 且 world.factions 里存在 | 无势力 / 脏 owner → 不显示该项 |
| 地图右键「编辑势力」文案 | `编辑势力：{faction.name}` | |
| 地图右键「编辑势力」入口 | MainWindow._edit_faction_from_map | 与 FactionPanel._edit 共用 dialogs.faction_edit.edit_faction |
| 人物情报窗口宽 / 最小高 | 600 / 640 | 宽固定，高自适应 |
| 人物情报窗口 resizable | (False, True) | 宽不可调，高可调 |
| 雷达图 Canvas 尺寸 | 340 × 340 | 坐标硬编码，不问 winfo_width |
| 雷达图中心 / 半径 | (170, 170) / 130 | 顶点半径 |
| 雷达图网格层数 | 5 | 20/40/60/80/100 |
| 雷达图轴上限 | 100 | > 100 截断画；数值列表显真值 |
| 雷达图轴顺序 | 统 → 武 → 智 → 政 → 魅 | 正上起，顺时针 72° |
| 雷达图轴角度公式 | -π/2 + i * 2π/5 | 弧度制 |
| 雷达图无势力色 | #7F8C8D / #5D6D7E | 填充 / 描边 |
| 雷达图 stipple | "gray50" | 半透明近似 |
| 雷达图顶点小圆半径 | 3 | 数据顶点 |
| 雷达图标签间距 | 顶点外 18px；数值再下 14px | RADAR_LABEL_GAP / RADAR_NUM_GAP |
| 关系可点姓名色 | #1F6FBF | 蓝，cursor = hand2 |
| 关系未命中色 | #999999 | 灰，不可点 |
| 关系姓名格式 | display_name（带表字） | 不带势力 |
| 生平占位文案 | 「（生平未收录）」 | 灰色斜体（BIO_FG = #888888） |
| 人物情报窗口居中基准 | master.winfo_toplevel() | 游戏主窗口 |
| 人物情报窗口 world 参数 | 可选（None → 关系全 "—"） | 由 CharacterPanel 传入 |
| 势力兵力口径 | Σ node.troops (owner = 本势力) + Σ troop.troops | 部队项恒 0 |
| 势力兵力列位置 | 粮后、据点前 | 资源类连排（金 / 粮 / 兵力） |
| 势力兵力列宽 / 对齐 | 70 / "e" / 千分位 / sort_numeric | 同金 / 粮 |

---

## 8. 已知逻辑限制与待完善清单

### 8.1 未实现功能

| 入口 | 现状 |
|---|---|
| 存档 / 新游戏 / 读档 | 提示「尚未实现」 |
| 内政 / 军事 / 外交 | 空实现 |
| 外交交互 | 只有 stance 字段 |
| 部队面板 | 只清空（TroopPanel.fetch_rows 返回 []） |
| Troop 数据模型 | 未建（部队项恒 0，见 §8.4） |
| type 差异化的能力 / 玩法 | 未做 |
| 设置窗口「游戏」tab | 骨架 |
| 县界 / 县面 hover | 不做 |
| dash 可调 | 不支持 |
| 郡面分级调色 | 字段全保留但不消费 |
| 字体可在 UI 里改 | 只支持更换候选字体，不支持任意路径 |
| 据点面板「主官」列 | 占位 |
| 据点面板右键三项 | 占位（据点情报 / 人物情报 / 势力情报），只写日志 |
| 据点面板字体 / 字号可调 | 不支持 |
| 据点面板列宽 / 分组 / 排序持久化 | 不支持 |
| 人物情报窗口雷达图交互 | 无 hover / 数值 tooltip / 点击轴突出 |
| 人物情报窗口生平 | 只占位（灰色斜体「（生平未收录）」），数据源未定 |
| 人物情报窗口单例 | 无 —— 重复右键会开多个窗口 |
| 人物面板状态持久化 | 不支持 |
| Character.location 运行时变更 | 未实现（字段已存，无逻辑） |
| Character.node 归属变更 | 未实现 |
| 人物面板势力分组顺序可调 | 未实现（目前仅玩家置顶 + 其余字典序） |
| hover 近邻兜底显示势力 | 未实现（见 §8.3 第 17 条） |
| 势力色块间距可调 | 未实现（受 ttk 主题控制，不可直接调） |
| 搜索正则 / 跨字段 / 拼音 | 只留 parse_query 接口，未实现 |
| 搜索匹配表字 | 姓名列去表字后，搜表字不再命中 |
| 反向定位（人物 / 势力 / 部队） | 占位，state = "disabled" |
| region 高亮州面 | 只做郡面（基础版），州面 MultiPolygon 未做 |
| 地图情报三项右键 | 占位，只写日志 |
| 面板列拖拽排序 | 只做 Listbox + 上移/下移 |
| 面板列宽 / 排序状态持久化 | 不支持（列宽由 Column.width 决定） |
| NAME_COLUMN 可配置 | 锁定必显，不参与配置 |
| Character.portrait 字段清理 | 保留但不再消费（§3.3） |
| characters.json 的 location_name / affiliation | 垃圾字段未清理（§3.3） |
| 头像缺图提示 | 只显示「（无头像）」，无占位图 |
| 据点 owner 编辑 + 级联 | 推迟到 phase2 |
| 势力新建 / 删除 / 消亡 | 推迟到 phase2（World.add_faction 等为 NotImplementedError） |
| 人物编辑 | 未做（弹窗骨架已就绪，未接 CHARACTER_FIELDS） |
| GameState.change_gold / food | 未适配派生值（编辑模式不跑回合，标记 TODO(phase3)） |
| 设置窗口「日志」入口 | 只做后端，无 UI |
| 日志级别 / 保留数量配置化 | 不支持（_MAX_LOG_FILES = 30 硬编码） |
| 未保存提示运行时可切换 | 不支持（星号常开，不写入 settings） |
| 编辑弹窗单例 | 未做（同一实体可开多个弹窗） |
| 人物面板「在野」组标签 | 显示 "—"（faction_name 的兜底值），不显示「在野」 |
| 势力面板 hover 展示兵力 | 未做（只在列 + 弹窗展示） |
| 状态栏 / 地图 tooltip 展示势力兵力 | 未做（只在列 + 弹窗展示） |

### 8.2 数据层缺失

| 项 | 现状 |
|---|---|
| Troop（部队）模型 | 完全没有；势力兵力里的「部队项」恒为 0 |
| 人物生平 / 传记文本 | 无数据源，人物情报窗口生平区只占位 |
| 重名人物 | characters.json 的 _ambiguous_names 有 5 组，头像按「同名复制多份」处理 |
| 悬空引用 | _missing_refs 当前为 0，但加载时仍需容错 |
| 据点主官 | 无字段；据点面板「主官」列占位（人数列已由 count_characters_by_node 接上） |
| 县的人口 / 兵役 / 特产等内政数据 | 无 |
| 势力间外交关系矩阵 | 无，只有 stance（相对玩家的单一值） |
| 山地数据 | mountains.geojson 已下载但未接入 GeoData |
| 剧本 nodes 覆盖 | 555 / 1152 县，其余县无主 |

### 8.3 逻辑与性能限制（★ 永久约束）

**地图与渲染**

1. 无 LOD 的图层 + 全量重绘：render_points 已按 CITY_LEVEL_MIN_SCALE 做 LOD 过滤，render_lines（106 条郡界）仍全量重绘、仅 bbox 视口裁剪。县点因此从静态层移入动态层——每次 zoom/pan 后 30 ms 都会重建全部可见点（bbox 裁剪后通常数十至数百个），配合县名同步刷新，这是「同显同隐」的必要代价，当前量级可接受。若后续卡顿，可让 pan 路径跳过县点/标签重建（平移不改变 scale，半径无需重算），只让 zoom 触发。
2. `<Configure>` 全量重绘：尺寸变化且非首次 fit 时无条件 `draw_full()`，拖动 PanedWindow 分隔条会触发连续全量重绘，可能卡顿；且**不调整缩放比例**（刻意设计，避免视野被重置）。
3. 异常静默吞掉：render_polygon / render_line / render_point / render_roads / 水域绘制外层 `except Exception: pass`，几何出错时不报错也不提示，排查困难。县 level 越界这类问题就属于典型受害场景——因此必须在数据入口钳制、在查表处用 `.get`。
4. 标签不做视口预筛：render_label_group 与 render_city_labels 对每个标签都调 `project()` 再判断屏幕范围，未先按 bbox 裁剪；且每次 refresh_dynamic 都会重建全部标签对象（含每字 4 次描边绘制）。县点层已做 bbox 粗筛（_visible_bounds），但 render_city_labels 仍逐标签 project()，未预筛。
5. 空间索引为线性扫描：find_state_at / find_county_at 遍历全部环做 bbox 粗筛 + 射线法，未建 R 树/网格；鼠标 40 ms 节流下勉强可用但非最优。
6. 只取外环：_build_index 只用 `polygon[0]`，忽略多边形内环（孔洞），带洞的州面判定可能误判。
7. 县名匹配用固定 0.4° 距离：find_location / find_location_detail 的县名靠最近标签，边界或标签稀疏处可能匹配到邻县或返回 None。
8. `midpoint_of_line` 为死代码，无任何调用者（州名中点逻辑已内联在 GeoData._classify）。
9. `_cum_scale` 复位时机：全量重绘会清零累计缩放，因此长时间单向缩放时会出现周期性的全量重绘停顿。
10. 道路无 LOD、无空间索引：render_roads 每次全量遍历约 600 条线段做 bbox 粗筛，配合 refresh_dynamic 在每次缩放/平移后重建全部道路 canvas 对象。当前量级可接受；道路若扩展到数千条，应优先给 `GeoData.roads` 建网格索引，并在低缩放级别下按 road_type 分级显示。
11. 动态图层重建 + `tag_lower` 的额外开销：refresh_dynamic 每次需 delete → 重绘 → tag_lower 三段操作；Tk 的 tag_lower 需要遍历该 tag 下所有对象并调整其在显示列表中的位置，对象越多成本越高。若日后卡顿，替代方案是给静态层打 tag 后整体上提/下压，或改为分层 Canvas 布局（每层一个独立 Canvas 叠放）。
12. `CITY_LEVEL_MIN_SCALE` / `shape_by_level` / `radius_by_level` 都是**硬编码定长字典**：等级数量一旦变动（如改成 1–20），三张表都要手工同步。后续可统一改为「按 min_level / max_level + 曲线公式程序化生成」。
13. 县点与县名「同显同隐」依赖同表同判：两者都读 CITY_LEVEL_MIN_SCALE，但分处 render_points 与 render_city_labels 两处。若日后有人只改一处阈值，就会破坏一致性；建议抽出 `_visible_by_level(level, scale)` 公共方法统一判定。
14. ★ `_drawn` 置位时机是易错点：`_drawn` 同时被 draw_full 用作「几何层完成」标志、被 refresh_dynamic 用作执行守卫。draw_full 内**必须**在 `_draw_geometry()` 之后、`refresh_dynamic()` 之前置 True；一旦误置于方法末尾，首帧动态层会被守卫 `if not self._drawn: return` 跳过，表现为「开图只有州郡边界，鼠标一动/一缩放才补全」。修改 draw_full 时请勿调整这两行的相对位置。
15. ★ refresh_dynamic 的绘制顺序决定层级：Tk 后画盖先画，标签必须**最后**绘制才能位于最顶。当前正确顺序为 `_draw_water() → render_roads() → render_points() → _draw_labels()`，其中 `_draw_labels()` 保持在末尾。若调整顺序（例如把标签提到最前），标签会被县点/道路/水域遮挡；tag_lower 只调整几何层，不会挽救标签被埋的问题。
16. ★ `_city_index` 从 3 元组改 4 元组，任何解包处必须同步：现在是 `(bbox, 县名, ring, 县 id)`。已改：_build_city_index / find_city_at / _find_city_with_id。将来新增遍历处务必 4 元组解包。
17. hover 兜底不返回 node_id：find_location_detail 里，如果 _find_city_with_id 未命中多边形，回落到 find_nearest_label → 只有县名，无 id；结果：近邻兜底时不显示势力名。
18. ★ MapCanvas 与 World 解耦：MapCanvas 只输出地理信息 dict（state / county / city / node_id / lon / lat），势力名由 MainWindow._on_location_change 拼装。**不要**给 MapCanvas 塞 World 引用。

**面板与 UI**

19. Tab 索引硬编码：MainWindow._on_menu_action 用 `notebook.select(1/2/3)`，调整 SidePanel._add_tabs 顺序会静默错位。
20. `WINDOW_SIZE` 常量定义了但从未使用（窗口走 maximize）。
21. 势力色块大小必须动态计算：不能硬编码（不同系统 ttk 行高不同）。_compute_swatch_size 优先读 `Style.lookup("Treeview", "rowheight")`，退化到 `TkDefaultFont.metrics("linespace") + 6`；色块 = 行高 − 2。
22. PhotoImage 必须显式填整块：`img.put(color)` 单色字符串在部分 Tk 版本只填左上角一个像素，**必须** `img.put(color, to=(0, 0, size, size))`。
23. PhotoImage 必须保引用：FactionPanel._swatches 缓存、CharacterInfoWindow._photo 属性。Tk 不持 PhotoImage 引用，不存 → GC 后显示空白。每次 refresh / 每次开窗，先 clear() 再重建。
24. 势力色块带黑边：先整块填 #000000，再在 (1, 1, size-1, size-1) 填势力色。想调边框粗细改 to 起点；想调颜色改 #000000。
25. ★ 面板的 COLUMNS / NAME_COLUMN 等类属性必须显式绑定：框架读的是 `self.COLUMNS`（类属性），不是模块级变量。只要模块里有 `COLUMNS = (...)`，**类体内必须写 `COLUMNS = COLUMNS`**，否则 self.COLUMNS 取到基类默认 `()`，Treeview 只剩 #0 列。症状：面板只显示名称列 / 势力名一列，其它列全消失。NAME_COLUMN 之所以没暴露此坑：FactionPanel 在 __init__ 里设了**实例属性** self.NAME_COLUMN，绕过了类属性查找。将来重写 / 新增任何 panel，类体内必须显式绑定模块级配置到类属性。**不要**为了「省事」把模块级变量直接改名成类属性——分组复用（如 GROUP_DIMS 同时喂 GroupBar 和 build_tree）会失效。
26. ★ 面板列配置必须兼容「用户旧配置 + 框架新列」：用户在设置窗口调整过列顺序后，PANEL_COLUMNS[k].order 被写进 userdata/settings.json；将来在 COLUMNS 里加新列，用户旧配置里没这个 key。_resolve_columns 的规则：order 中的 key 优先排前，**未出现的按声明顺序追加到末尾 + 默认显示**。**不要**把 order 当白名单（否则加列后用户看不到新列），**不要**在加载配置时把未知 key 报错（将来列被删除时同理）。
27. ★ 三列等宽用 grid + columnconfigure(uniform=)：父/母/配偶三列等宽不能用 pack 的 expand（内容长度会拉宽各自列），要用 `frame.columnconfigure(i, weight=1, uniform="rel")` + 子 widget `grid(sticky="w")`。uniform 的 key 可任取，同组共享即可。列表型关系（义兄弟/亲爱/厌恶）仍用 pack side="left"。
28. ★ 雷达图用 Canvas 不用 Pillow：雷达图的中文轴标签（统/武/智/政/魅）用 Pillow 画需要 `ImageFont.truetype(font_path)`，要字体文件绝对路径；跨平台字体路径不同（Windows msyh.ttc / Linux Noto Sans CJK / macOS PingFang.ttc）→ 脆。tkinter Canvas 的 create_text 直接用字体名 → 中文天然可用。结论：**雷达图永远走 Canvas**；Pillow 只用于头像。将来的雷达图扩展（hover / tooltip / 点击轴突出）也走 Canvas 事件。
29. ★ Canvas 尺寸固定，不问 winfo_width：CharacterInfoWindow.__init__ 里布局未完成，winfo_width 拿到的是 1。雷达图坐标全部用硬编码的 RADAR_SIZE = 340 计算。想改尺寸：改 RADAR_SIZE / RADIUS 两个常量，其它按比例自动跟随。
30. ★ `self._top = master.winfo_toplevel()` 必须在 __init__ 里存：Toplevel.winfo_toplevel() 返回自己（不是父），不能直接用来拿主窗口；master（panel，Frame）的 winfo_toplevel() 才是主窗口。跳转窗口时传的 master 已是主窗口，路径自洽。**不要**用 self.master 拿主窗口（多一层 Toplevel 会断链）。用途：居中基准、跳转窗口的 master。
31. ★ 关系区查不到的人显示「—」不可点：world 为 None 或 world.character(id) 返回 None（不在 World.characters 里）→ 走 _muted_label 灰色 "—"。不要显示原始 id（用户不易读），**关系区**不要显示「（未登场）」之类状态（该状态只出现在窗口标题，见 §5.20）。血缘（blood）是字符串标签，不查人物、不可点；世代（generation）是数字。

**依赖与资产**

32. ★ Pillow 是唯一的第三方依赖：只用在 game/ui/character_info_window.py，加载时 `try: from PIL import Image, ImageTk` → 失败时 `_PIL_OK = False`，窗口降级显示「未安装 Pillow」，不崩。**不要**在 core/ / map/ 层引入 Pillow —— 保持数据层无依赖。雷达图 / 关系区是纯 tkinter Canvas / Widget，不引入新的第三方依赖。仓库内没有 requirements.txt，需自行 `pip install Pillow`。
33. ★ 头像路径拼 {id}-{name}，不读 portrait 字段：Character.portrait 字段保留但不再消费；拼路径只用 ch.id + ch.name，**不含表字**。名字含空格 / 特殊字符时需与 tools/头像.py 保持一致（工具也按原样拼）。
34. ★ Image.open 后必须 convert("RGB")：部分 PNG 带 alpha 通道 → ImageTk.PhotoImage 可能不认；灰度图 / 调色板图同理。统一 convert("RGB") 最稳。
35. ★ 缩略用 thumbnail 而非 resize：thumbnail 保比例、只缩不放；想固定尺寸、允许放大才用 resize。默认「不超过 200×200」，小图原样。

**编辑系统**

36. ★ 改 World 只走 Command：UI 层（弹窗/面板/菜单）不得直接赋值实体字段，只能构造 Command → EditSession.execute()。任何「直接赋值 World 字段」绕过 session 的代码 = bug。
37. ★ baseline_snap 必须在 bind_factions() 之后序列化：否则 Faction.gold/food/troops property 尚未注入 nodes 引用，值为 0。顺序：bind_factions → serialize → EditSession(world, baseline_snap)。
38. ★ raw 必须保留用于增量写回：`ScenarioWriter.save(world, path, raw, baseline_snap)` 三个参数都要；raw 是加载时的原始 dict，写回时作为模板（保留未改动字段原值）。
39. ★ Ctrl+Shift+S / Ctrl+Shift+Z 的 keysym 必须大写：正确 `<Control-Shift-S>` / `<Control-Shift-Z>`；错误 `<Control-Shift-s>`（小写不触发）。
40. ★ 新增编辑入口必须登记，不得各自写模式判断：右键菜单用 `MenuItem(..., edit=True)` → 由 `build_menu(edit_enabled=)` 统一置灰，判定 = `edit_session is not None`；顶部菜单用 `TopBar._add_edit_command()` 加项 → 自动登记进 _edit_entries，`set_edit_enabled()` 一键全禁；地图右键（tk.Menu 直建，不走 build_menu）用 `state = "normal" if self.editable else "disabled"`。**不要**在每个新入口里复制 `if APP_MODE == MODE_EDIT`（模式判断只在 MainWindow）。
41. ★ 列表/渲染显示「可编辑实体」时必须查 World，不能只读 GeoData：Node.type / level / is_capital 来自 map.geojson（GeoData.shapes_point），但编辑只改 World 的 Node。渲染端（renderer._effective_level）与加载端（scenario._apply_node_overrides）都要以 World 为准。加新的可编辑静态字段时，三处必须同步：Node.to_dict（写）/ _apply_node_overrides（读）/ 渲染或面板（显示）。
42. ★ 势力编辑必须走共用流程：弹窗路径 dialogs/faction_edit.py::edit_faction，不得内联到面板或 MainWindow。势力面板右键 `FactionPanel._edit → edit_faction(self, ...)`（parent = panel）；地图右键 `MainWindow._edit_faction_from_map → edit_faction(self.root, ...)`（parent = root）。两者共用同一个 EditDialog + FACTION_FIELDS + FactionEditCommand。加新的势力字段只需改 faction_fields.py，两处入口同步生效。**不要**用 FactionPanel 实例方法做地图侧入口（会引入循环依赖）。
43. ★ 地图右键「编辑势力」只在有主据点显示：显示条件 = node.owner 非空 且 world.factions 里存在该 id。无势力 / owner 脏数据 → **不 add_command**（隐藏而非置灰）。owner 脏数据要 logger.warning（不崩，不静默）。state 由 self.editable 决定（同「编辑据点」）。**不要**在空白右键菜单里加编辑势力项。
44. ★ 势力兵力（Faction.troops）是派生值，无 setter：口径 = Σ node.troops (owner = 本势力) + Σ troop.troops (faction_id = 本势力)；部队项恒为 0。**_troops_ref 不建**（没有 Troop 容器可注入，别留空属性误导后人）。将来 Troop 落地后，只在 Faction 加 _troops_ref + World.bind_factions 补注入，property 内部展开求和。from_dict / to_dict 与 gold/food 一样不读写 troops（剧本里出现会被静默忽略）。想改兵力 → 改 Node.troops（编辑弹窗），不直接改 Faction。编辑弹窗中 troops 走 readonly kind：直接 `getattr(faction, "troops")` 命中 property，无需 display_fn。

**日志**

45. ★ 日志一律用 %s 惰性格式化，禁止 f-string：正例 `logger.info("加载剧本：%s", path)`；反例 `logger.info(f"加载剧本：{path}")`（日志未输出时也白拼字符串）。高频路径不打日志：_process_motion / find_location_detail / _on_location_change / draw_full。
46. ★ 两个异常钩子的安装时机：setup_logging() + install_sys_excepthook() 必须在 MainWindow() 之前（main.py 里）；install_tk_excepthook(root) 必须紧跟 Tk() 之后（越早越好，构造期的回调异常才抓得到）。sys.excepthook 接不到 tkinter 回调异常，必须单独覆盖 Tk.report_callback_exception。
47. ★ _SessionFilter 挂 handler，不挂 logger：`handler.addFilter(_SessionFilter())` —— filter 在 handler 上才会给每条 record 注入 session；格式化串用 %(session)s。挂错地方会导致 KeyError: 'session'。
48. ★ LOG_ENABLED 是编译期开关：默认 True（保持原行为）。False 时：不建 userdata/logs/、不清理旧日志、不挂 FileHandler、`logging.disable(logging.CRITICAL)`、`_LOG_FILE_PATH = None`；也不接管 sys.excepthook / Tk.report_callback_exception，交回原生 stderr（不静默吞异常）。只改 constants.py 一处，其余模块不感知；**不要**散落 `if LOG_ENABLED` 判断——只在 logging_setup.py 三处入口判断。风格与 APP_MODE 一致：编译期，运行时不可切。
49. ★ 未保存提示只有一个刷新入口：`MainWindow._refresh_title` 是唯一读 `edit_session.is_dirty()` 渲染标题的地方；所有 dirty 状态变化点都经 `_sync_undo_redo_state → _refresh_title`。覆盖路径：_load_scenario / on_edit_executed / _on_undo / _on_redo / _save_to_path。**不要**在任何其他方法里直接改 `root.title()`。星号格式固定 " *"（空格 + 星号），不做 i18n。每次调用 is_dirty() 会做一次 serialize + diff，成本可接受（只在用户动作时触发）。

### 8.4 建议的下一步

- ★ **Troop 数据模型（phase2 前置）**：
  - core/troop.py（字段：id / faction_id / node_id / troops / morale / …）
  - World.troops 容器 + bind_factions 同时注入 _troops_ref
  - Faction.troops property 展开部队求和（TODO 注释已就位）
  - 剧本 characters 段扩 troop 段；scenario_writer serialize / diff
- ★ **部队面板落地**：TroopPanel 目前只 fetch_rows 返回 []；与人物面板同构接入
- 实现「出征 / 调动」：改 Character.location，不动 node
- 人物情报窗口单例化（同一人物只开一个窗口，重复右键聚焦已开窗口）
- 人物情报窗口生平数据源（拼装式编年？静态文本？）
- 人物情报窗口雷达图 hover / 数值 tooltip / 点击轴突出
- 关系人姓名旁边加势力名（当前选了纯姓名，可加开关）
- Character.affinity 参与势力关系计算
- 非首都据点兵/钱/粮细化
- 存档系统 / 新游戏流程 / 回合流程
- type 赋予玩法差异
- 外交入口（改 stance）
- 接入 mountains.geojson
- 人工核查 _ambiguous_names（5 组重名）
- 清理 characters.json 的 location_name / affiliation 字段（顺手删 Character.portrait）
- hover 近邻兜底也返回 node_id（find_nearest_label 加 id 输出）
- 势力面板组内排序可调（当前威望降序）
- 面板列宽持久化（PANEL_COLUMNS 里加 widths 字段）
- 面板列配置支持拖拽（tkinter 需手写，暂用按钮替代）
- 搜索匹配扩展到表字（_match_one 加 family_name 字段）
- 据点 owner 编辑 + 级联弹窗（phase2：改 owner → 人物 faction/node/location 联动）
- 势力新建 / 删除 / 消亡（phase2：World.add_faction / remove_faction / remove_faction_if_empty）
- 人物编辑（复用 §9.4 弹窗骨架，新增 CharacterEditCommand + CHARACTER_FIELDS）
- GameState.change_gold/food 适配派生值（phase3：Faction.gold 已无 setter）
- 编辑弹窗多实例控制 / 滚动（同一实体只开一个窗口；字段 > 10 时加滚动）
- 设置窗口「日志」tab（查看当前日志路径 / 打开目录 / 切换级别）
- 日志配置化（_MAX_LOG_FILES / 级别 / 是否输出控制台，从 userdata/settings.json 读）
- edit_dialog 字段值实时校验反馈（当前只有提交时校验，红字提示在按钮栏）
- 未保存提示运行时可切（放 settings 里；当前固定常开）
- 势力面板 hover / tooltip 展示兵力
- 状态栏 / 地图 tooltip 展示势力兵力
- 抽出 `_visible_by_level(level, scale)` 统一县点与县名的显隐判定（§8.3 第 13 条）
- 三张定长表（CITY_LEVEL_MIN_SCALE / shape_by_level / radius_by_level）改为程序化生成（§8.3 第 12 条）

---

## 9. 剧本编辑器设计

### 9.1 总体原则

- **改 World 只走 Command**：UI 层（弹窗 / 面板 / 菜单）不得直接赋值实体字段，只能构造 Command 交给 EditSession.execute()。
- **模式判断只在 MainWindow**：`self.editable` 由 APP_MODE 一次性决定；其余模块一律读 `edit_session is not None`。
- **弹窗数据驱动**：EditDialog 只认 Field.kind，没有「if 据点 elif 势力」的业务分支。
- **编辑入口统一标识**：右键 `MenuItem.edit = True`、顶部菜单 `_add_edit_command()`、地图右键 `state=...`，三处各有登记机制（§8.3 第 40 条）。

### 9.2 Command 与 EditSession

见 §10。

### 9.3 增量保存（ScenarioWriter）

`serialize(world) -> dict`：

- 写元字段 version / id / name / desc / start{year,month,xun} / player_faction，可选 character_id_range。
- factions / characters / nodes 三段用各类 to_dict()。
- Faction.to_dict **不含** gold / food / troops（派生值）；Node.to_dict 写全 7 字段；Character.to_dict 全 31 字段（含 appeared）。

`diff(current, baseline) -> {section: {id: {field: (old, new)}}}`：

- 只扫 factions / characters / nodes 三段；**元字段不参与 diff**。
- 按 current 的实体/字段遍历，`old_val != new_val` 才收录。

`save(world, path, raw, baseline_snap)` — 五步增量写回：

```text
1. current = serialize(world)
2. delta   = diff(current, baseline_snap)
3. output  = deepcopy(raw)
4. 按 delta 用 current 的新值覆盖 output（逐层 setdefault，id 不存在则新建）
5. json.dump(output, f, ensure_ascii=False, indent=2)
```

未改动字段保留 raw 的原始形态（键序 / 额外键都不动）。异常先记日志再 raise。

### 9.4 数据驱动弹窗（EditDialog / Field）

`Field` 是 NamedTuple：

```python
Field(key, label, kind, default=None, options=(), min=None, max=None,
      editable=True, hint="", display_fn=None)
```

6 种 kind 的语义：

| kind | 控件 | 读值 | 校验 |
|---|---|---|---|
| readonly | Label（`display_fn(value, world) -> str`） | 不收集 | 无 |
| int | Entry + StringVar | `int(strip)` | min/max 越界在按钮栏红字报错 |
| str | Entry | 原字符串 | 无 |
| bool | Checkbutton(BooleanVar) | bool | 无 |
| choice | ttk.Combobox（readonly），options = [(value, label)] | label → value 反查 | 无 |
| color | 色块 Label + hex Entry + colorchooser | hex 字符串 | 仅接受 `#` + 6 位，否则忽略 |

`EditDialog(master, fields, entity, world=None, title="编辑")`：

- transient 到 `master.winfo_toplevel()`，相对主窗口居中，`grab_set`。
- `_build_field` 是唯一的 kind 分支树（readonly → bool → choice → color → 其余 int/str）。
- `get_changed() -> (new_values, old_values)`：只返回 `old != v` 的字段；`ok` 标志表示用户点了确定。
- 取消 / Esc / 关闭窗口 → `_cancel()`（ok = False）。

### 9.5 字段表

**NODE_FIELDS（10 项）**

| key | 标签 | kind | 约束 |
|---|---|---|---|
| id | 编号 | readonly | |
| name | 县名 | readonly | |
| coords | 坐标 | readonly | display_fn 格式化为 `(x, y)`，空为 "—" |
| owner | 势力 | readonly | display_fn 查 world.faction(v).name，否则「无主」 |
| type | 类型 | choice | (("城","城"), ("关隘","关隘"), ("渡口","渡口")) |
| level | 规模 | int | 1 – 10 |
| is_capital | 郡治 | bool | |
| troops | 兵力 | int | ≥ 0 |
| gold | 金钱 | int | ≥ 0 |
| food | 军粮 | int | ≥ 0 |

**FACTION_FIELDS（8 项）**

| key | 标签 | kind | 约束 |
|---|---|---|---|
| id | 编号 | readonly | |
| name | 势力名 | str | |
| color | 颜色 | color | |
| prestige | 威望 | int | ≥ 0 |
| stance | 关系 | int | -100 – 100 |
| gold | 金钱 | readonly | 派生值 |
| food | 军粮 | readonly | 派生值 |
| troops | 兵力 | readonly | 派生值（§8.3 第 44 条） |

### 9.6 共用编辑流程

两个模块签名一致：`edit_node(parent, world, node, session, open_dialog) -> bool`、`edit_faction(parent, world, faction, session, open_dialog) -> bool`。`open_dialog(dlg_factory) -> dlg` 由调用方注入（面板 / 地图共用）。

**edit_node 步骤：**

1. 守卫 `session is None or world is None or node is None` → False（非编辑模式直接返回）。
2. 函数内惰性 import（EditDialog / NODE_FIELDS / NodeEditCommand / CompositeCommand）。
3. 开弹窗；`dlg is None or not dlg.ok` → False。
4. `new_values, old_values = dlg.get_changed()`；空 → False。
5. **郡治互斥**：若 `new_values.get("is_capital") is True`，遍历 world.nodes 找 `id != node.id` 且 `county_id == node.county_id` 且 `is_capital` 为真的据点；`messagebox.askyesno("郡治冲突", …)` ——
   - 用户拒绝 → **整体取消返回 False（不提交任何改动）**；
   - 用户同意 → append `NodeEditCommand(other.id, {"is_capital": True}, {"is_capital": False})` 并 break（只处理第一个）。
6. append `NodeEditCommand(node.id, old_values, new_values)`；单条直接 execute，多条包 `CompositeCommand(cmds, "设置郡治")`。
7. `session.execute(cmd)` → True（调用方负责刷新面板 / 地图）。

**edit_faction 步骤：** 守卫 → 弹窗 → get_changed() → 空则 False → `session.execute(FactionEditCommand(faction.id, old_values, new_values))`（无互斥逻辑）。

**调用方：**

| 入口 | parent | 后续 |
|---|---|---|
| NodePanel._edit | self（panel） | _notify_edit |
| MainWindow._edit_node_from_map | self.root | side_panel.refresh_all() + on_edit_executed() |
| FactionPanel._edit | self（panel） | _notify_edit |
| MainWindow._edit_faction_from_map | self.root | side_panel.refresh_all() + on_edit_executed() |

---

## 10. 编辑会话设计

### 10.1 EditSession

```python
class Command:                      # 抽象基类
    def do(self, world):  raise NotImplementedError
    def undo(self, world): raise NotImplementedError
    def label(self) -> str: return "操作"

class CompositeCommand(Command):    # do 顺序执行、undo 逆序执行
    def __init__(self, commands, label="复合操作"):
        self.commands = list(commands); self._label = label

class EditSession:
    max_depth = 5                   # undo 栈深度，超出丢弃最旧

    def __init__(self, world, baseline_snapshot: dict):
        self._world = world
        self._baseline = baseline_snapshot
        self._undo_stack = []; self._redo_stack = []
```

| 方法 | 语义 |
|---|---|
| execute(cmd) | `cmd.do(world)` → push undo 栈 → 超出 max_depth 则 `pop(0)` 丢弃最旧 → `_redo_stack.clear()` |
| undo() | 栈空静默返回；否则 pop → `cmd.undo(world)` → push redo 栈 |
| redo() | 栈空静默返回；否则 pop → `cmd.do(world)` → push undo 栈（**不再裁剪 max_depth**） |
| can_undo() / can_redo() | 栈非空判断 |
| baseline（property） | 当前 baseline 快照，供 ScenarioWriter.save 用 |
| is_dirty() | `bool(diff(serialize(world), baseline))` |
| clear() | 清空两个栈（保存 / 另存为后调用） |
| rebase() | `_baseline = serialize(world)` |

**dirty 判定机制**：全量重新序列化 + 与 baseline 逐字段 diff，**不是标志位**。因此把字段改回原值会自然变干净。dirty 驱动三处：窗口标题 " *"（_refresh_title）、保存前短路（无改动不写文件）、关闭拦截（_confirm_discard）。

**接线**：加载剧本时 `baseline_snap = serialize(world)` 建 session；保存后 `rebase() → clear() → 重读 _baseline_raw`。

### 10.2 具体命令

```python
class NodeEditCommand(Command):
    def __init__(self, node_id, old_values: dict, new_values: dict): ...
    def label(self): return f"编辑据点 {node_id}"

class FactionEditCommand(Command):
    def __init__(self, faction_id, old_values: dict, new_values: dict): ...
    def label(self): return f"编辑势力 {faction_id}"

class CharacterEditCommand(Command):
    def __init__(self, character_id, old_values: dict, new_values: dict): ...
    def label(self): return f"编辑人物 {character_id}"
```

- 约定：`old_values / new_values` 均为 `{field: value}` dict，**只含真正变化的字段**（由 EditDialog.get_changed 保证）。
- do 遍历 new_values `setattr`，undo 遍历 old_values `setattr`；构造时 `dict()` 拷贝一份。
- 命令类**没有** get_changed 方法。
- CharacterEditCommand 当前唯一用法：人物面板「设为登场 / 未登场」开关
  （`session.execute(CharacterEditCommand(cid, {"appeared": old}, {"appeared": not old}))`）；
  将来的完整人物编辑（CHARACTER_FIELDS）沿用同一个命令。
- TODO(phase2)：owner 级联、FactionCreate / Delete。

### 10.3 测试

| 文件 | 覆盖 |
|---|---|
| tests/test_composite_command.py | CompositeCommand 的顺序 / 逆序语义 |
| tests/test_scenario_writer.py | serialize / diff / save 的增量写回 |
| tests/test_character_appeared.py | appeared 全量加载 / 老剧本兼容 / 开关命令 + dirty / 归属字段保留 |

---

（文档结束）
