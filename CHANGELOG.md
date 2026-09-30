# 变更日志

记录项目每轮的改动。分类：Added / Changed / Removed / Fixed。

---

## 2026-09-25 · 人物登场字段 appeared

### Added
- 人物登场字段 `Character.appeared`（剧本动态字段，缺省 True，老剧本兼容）（`core/character.py`）
- 人物编辑命令 `CharacterEditCommand`（`core/edit_commands.py`）
- 人物查询与聚合 `World.characters_at` / `count_characters_by_node`（`core/world.py`）
- 人物面板：分组维度「登场」+ 右键「设为登场 / 设为未登场」开关（`character_panel`）
- 人物情报窗口：未登场人物标题追加「（未登场）」（`character_info_window`）
- 登场判定规则 `compute_appeared`（`tools/build_scenario_190.py`）
- 测试 `tests/test_character_appeared.py`（加载兼容 / 开关 / dirty / 计数口径）

### Changed
- 剧本加载第三层：按年份筛人 → 应用登场状态，`World.characters` 收全量 1049 人（含未登场与穿越人物）（`core/scenario.py`）
- 190 剧本：改为全量写人物（1049 条 / 每人 5 字段 / 按 id 排序），不再写 `character_id_range`（`tools/build_scenario_190.py`、`scenarios/default.json`）
- 人物 / 据点人物数口径：未登场人物不再计入（`core/world.py`、`faction_panel`、`node_panel`）

### Removed
- `ScenarioLoader._filter_by_year`，由 `_apply_appeared` 取代（`core/scenario.py`）
- 190 剧本的 `character_id_range` 字段（老剧本仍兼容读取）（`tools/build_scenario_190.py`）

### Fixed
- 未登场人物被算作势力 / 据点的人物（`core/world.py`）
- 据点面板「人物」列恒为 0 的占位（`node_panel`）

---

## 2026-09-26 · 人物移动到据点

### Added
- 人物面板右键「移动到据点」（`character_panel`）
- 移动弹窗：据点单选列表 + 实时信息块 + 登场询问 + 二次确认（`ui/dialogs/move_to_node.py`）
- 列表框架 `SELECT_MODE` 类属性，弹窗内可强制单选（`panels/list/panel.py`）
- 单元测试 `tests/test_move_to_node.py`

### Changed
- 移动会同时改 `node` / `location`，`faction` 跟随目标据点 owner（`ui/dialogs/move_to_node.py`）
- README 同步：§5.21 / §5.23 / §6.4 / §8.3 第 50 条 / §8.4 / §10.2

---

## 2026-09-26 · 外官系统与 190 剧本重制

### Added
- 官名生成模块 `core/official_title.py`（州 / 郡 / 县规则，纯函数无依赖）
- `World.officials` 容器 + `official_of` / `officials_of_character` / `official_label`（`core/world.py`）
- 剧本 `officials` 段与加载 `_apply_officials`（`core/scenario.py`、`scenarios/default.json`）
- 据点面板「主官」列接县外官、州 / 郡分组标题追加「官名-姓名」（`node_panel`）
- 人物面板「官职」列 + 人物情报窗口官职行（`character_panel`、`character_info_window`）
- 列表框架 `SELECT_MODE`、`Group.subtitle` + `subtitle_fn` 钩子、`_fit_name_column()` 按组标题自适应 #0 列宽（`panels/list/`）
- 单元测试 `tests/test_official.py`

### Changed
- 剧本生成脚本重制：50 家 `MONARCHS` 名单 + 自动划地盘（郡级先占满本郡 / 州级只吃一郡）+ 官名生成校验 + 县点邻接配色（`tools/build_scenario_190.py`）
- 势力名一律取君主本人姓名（`tools/build_scenario_190.py`）
- 据点面板列头「规模」改为「等级」（`node_panel`）
- README 同步：§0 / §1 / §2 / §3.5 / §4.4 / §4.5 / §4.6 / §5.10 / §5.20 / §5.22 / §5.23 / §7.3 / §8.1 / §10.3

### Removed
- 势力 刘璋、刘琦、刘勋；扬州刺史改由许贡担任（`tools/build_scenario_190.py`）
- 夷洲（琉球）不再有任何势力占据（`tools/build_scenario_190.py`）

### Fixed
- 势力名与君主不一致的错位（如「赵韪」势力君主实为吴懿）（`tools/build_scenario_190.py`）
- 相邻势力配色过近：改为县点邻接判定 + 用色均衡（`tools/build_scenario_190.py`）
- 据点面板州 / 郡分组标题被 #0 列宽截断（`panels/list/panel.py`）

---

## 2026-09-26 · 悬停信息扩展、据点情报窗口与渲染修复

### Added
- 据点情报窗口（据点 / 外官 / 所属州郡 / 外官实际控制 / 宣称权冲突）（`ui/node_info_window.py`）
- 列表框架 `Group.values` + `group_values()` 钩子：组头信息可落到其它列（`panels/list/`）

### Changed
- 地图悬停 tooltip 改为 4 行：县 / 郡 / 州各级外官 + 势力名（不再显示驻军）（`main_window`）
- 州 / 郡组头的外官从 #0 标题挪进「主官」列；`#0` 恢复基宽并改为 `stretch=True`（`node_panel`、`panels/list/panel.py`）
- 据点面板「主官」列宽 56 → 112（`node_panel`）
- README 同步：§2 / §5.22 / §5.23 / §6.4 / §8.1 / §8.3 第 51 条

### Fixed
- 地图悬停 tooltip 在指针移出画布后不消失（节流任务未取消）（`ui/map_canvas.py`）
- 滚轮缩放后新暴露区域缺染色（静态地理层按视口裁剪）（`map/renderer.py`）

---

## 2026-09-26 · 右侧面板深度编辑扩展

### Added
- 势力新建 / 删除：`FactionCreateCommand` / `FactionDeleteCommand` + 新建弹窗与删除预览弹窗（`core/edit_commands.py`、`ui/dialogs/faction_lifecycle.py`、`faction_panel`）
- 据点批量易主：`ChangeOwnerDialog` + 可选的「同步调整人物归属」级联（`ui/dialogs/node_owner.py`、`node_panel`）
- 外官增删改：`OfficialSetCommand` / `OfficialRemoveCommand` + 外官编辑弹窗（限实控区域，两个可选级联默认关闭）（`ui/dialogs/official_edit.py`）
- 「编辑人物」窗口：姓名 / 字 / 性别 / 五维 / 登场 / 势力 / 所属 / 所在可编辑 + 外官区（`ui/character_info_window.py`）
- 通用单选列表 `PickList` + 通用据点选择窗 `pick_node`（`ui/dialogs/pick_list.py`、`move_to_node.py`）
- 组头悬停提示与「等 N 个」多值显示（`panels/list/`、`node_panel`）
- 单元测试 `tests/test_edit_extensions.py`

### Changed
- officials 段参与 serialize / diff（`core/scenario_writer.py`）
- `World.add_faction` / `remove_faction` 从占位改为实现（`core/world.py`）
- 据点编辑弹窗的 owner 由 readonly 改为 choice（无主 + 势力列表）（`dialogs/node_fields.py`、`node_edit.py`）
- 据点情报窗口的宣称权冲突改为三级判定：无冲突 / 小冲突 / 大冲突（`ui/node_info_window.py`）
- `#0` 列自动加宽改为「组标题 + 最长数据行」取大（不持久化）（`panels/list/panel.py`）
- README 同步：§2 / §3.5 / §5.21 / §5.22 / §5.23 / §6.4 / §8.1 / §8.4 / §9.5 / §10.2

---

## 2026-09-26 · 面板列宽与官名修正

### Changed
- 县官名拼接加「前缀 ≥ 2 字才去「县」」守卫：范县 → 范县长、邺县 → 邺县令（`core/official_title.py`）
- 据点面板列宽按侧栏可用宽度重排（州 46 / 郡 52 / 等级 38 / 类型 42 / 势力 54 / 主官 104 / 人物 38）（`node_panel`）
- 据点面板「编辑外官」的 open_dialog 改为等待弹窗关闭后再返回（`ui/character_info_window.py`）
- README 同步：§4.6（官名规则）/ §5.22（#0 列宽契约）/ §5.23（列宽与列宽预算）

### Fixed
- 人物窗口「编辑外官」点了保存却没生效（`open_dialog` 未等待弹窗关闭，读到的 `dlg.ok` 恒为 False）
- #0 列无法手动调宽：`stretch=True` + 每次刷新自动改宽把用户的拖动覆盖掉（改回 `stretch=False`，拖动后记住 `_name_width_manual`）
- #0 列自动加宽没算组标题（改为「最长组标题 + 最长数据行」取大）

---

## 2026-09-26 · 情报并入编辑窗与人物窗分组

### Added
- 据点 / 势力弹窗的只读信息块与只读形态：`EditDialog(info_sections=…, readonly=True)`（`dialogs/edit_dialog.py`）

### Changed
- 面板右键标签随模式切换：编辑模式「编辑据点 / 编辑人物 / 编辑势力」，游戏模式「据点情报 / 人物情报 / 势力情报」（`node_panel`、`character_panel`、`faction_panel`、`main_window` 地图右键）
- 「编辑人物」窗口按 `CollapsibleSection` 分四组：基础 / 五维 / 归属 / 外官（`ui/character_info_window.py`）
- 据点面板的情报三项改为指向实体自己的窗（君主人物窗 / 所属势力窗）（`node_panel`）
- README 同步：§2 / §5.20 / §5.21 / §5.23 / §6.4 / §8.1

### Removed
- 据点情报窗口 `ui/node_info_window.py`：内容并入编辑据点弹窗（`dialogs/node_edit.py::node_info_sections`）

---

## 2026-09-27 · 势力分类（独立 / 附庸）与编辑弹窗分组

### Added
- 势力分类三字段 `independent` / `overlord_id` / `vassal_value`，写入 `to_dict`、`from_dict` 容错并对附庸值 clamp（`core/faction.py`）
- 势力派生显示色纯函数 `faction_display_color`：独立用自身色、董卓固定深棕、附庸按附庸值混宗主色 + 同宗主色相偏移（`core/faction_color.py`）
- 加载期附庸关系校验 `_validate_vassals`：宗主空 / 不存在 / 本身是附庸 / 成环 → 递归移除该势力，日志 + 终端 + 清单三处提示（`core/scenario.py`、`core/world.py::vassal_removals`）
- 独立 ↔ 附庸联动的级联命令 `build_vassal_commands`：独立转附庸时原有附庸改指新宗主（`core/edit_commands.py`）
- 弹窗分组能力 `FieldGroup` + `EditDialog(sections=…, scroll=…)` 与联动钩子 `on_change` / `set_field_enabled`（`dialogs/field_spec.py`、`dialogs/edit_dialog.py`）
- 编辑势力弹窗三组：基本情况（只读）/ 可编辑信息 / 独立·附庸，含只读「显示色」与宗主下拉（`dialogs/faction_fields.py`、`dialogs/faction_edit.py`）
- 势力面板「独立/附庸」列 + 按宗主分组维度，宗主排在所在组第一行（`panels/faction_panel.py`）
- 人物窗口：五维与雷达图同组、轴标签可点改值、基础组横排（性别下拉）、关系 / 生平折叠组、纵向滚动条（`ui/character_info_window.py`）
- 剧本生成：董卓指定附庸名单 + 新建段煨 / 徐荣 / 胡轸 / 牛辅四势力、附庸关系推导 `derive_vassals`、附庸外官按占据据点现算（`tools/build_scenario_190.py`）
- 测试 `tests/test_faction_vassal.py`、`tests/test_build_scenario_vassal.py`

### Changed
- 地图染色层、势力面板色块、人物窗口雷达图、势力弹窗「显示色」统一改用派生显示色，不写回 `Faction.color`（`map/renderer.py`、`panels/faction_panel.py`、`ui/character_info_window.py`）
- 编辑据点弹窗分两组：基本情况 / 归属与资源（`dialogs/node_fields.py`、`dialogs/node_edit.py`）
- 势力面板分组由固定 `CUSTOM_GROUPING` 改为框架 `GROUP_DIMS` + GroupBar，玩家/盟友/敌对/中立与宗主两种维度可切换（`panels/faction_panel.py`）
- 地图 tooltip 改为四行：首行所属势力加粗，其后县 / 郡 / 州各一行，无外官显示区名（`ui/main_window.py`）
- 剧本：刘备改平原太守并只辖平原 / 漯阴 / 高唐三县；势力 50 → 54 家、据点 626 → 616、外官 49 → 53 条（`tools/build_scenario_190.py`、`scenarios/default.json`）
- README 同步：§0 / §1 / §2.1 / §3.2 / §3.2.1 / §3.6 / §4.4 / §4.5 / §4.6 / §5.13 / §5.20 / §5.21 / §5.23 / §5.25 / §8.3 / §8.4 / §9.5 / §9.6 / §10.2 / §10.3

### Fixed
- 新增编辑入口时附庸关系可能被改坏：独立势力改为附庸后其原有附庸的宗主改为新宗主，否则下次加载会被判损坏移除（`core/edit_commands.py`、`dialogs/faction_edit.py`）
- 删除宗主势力时名下附庸未处理：现随删除级联自动独立，一次 undo 可退（`dialogs/faction_lifecycle.py`）
- 剧本生成中董卓名单据点被其他势力先占：改为名单优先抢占，并重算 `effective_capital`（`tools/build_scenario_190.py`）

---

## 2026-09-27 · 弹窗布局与可搜索下拉

### Added
- 可搜索下拉 `SearchableCombobox`：输入实时过滤 + `normalize()` 把非法输入纠正为合法选项（`ui/widgets/searchable_combo.py`）
- 弹窗分组布局 `FieldGroup.layout`（rows / two_cols / inline）+ `left_keys` / `left_info_titles` / `side_image` / `side_caption`（`dialogs/field_spec.py`）
- 弹窗 info 块的实体链接标记 `[[c:…]]` / `[[f:…]]` / `[[n:…]]` 与 `on_link_click` 回调，人物 / 势力 / 据点可互相跳转（`dialogs/edit_dialog.py`、`dialogs/faction_edit.py`、`dialogs/node_edit.py`）
- 人物编辑窗口新增「出生年」可编辑字段 + 只读「年龄」派生显示（`ui/character_info_window.py`）

### Changed
- 弹窗只读字段改为可拖选复制的只读 Entry；info 块改用 `tk.Text` 渲染（可拖选 / Ctrl+C，高度自适应）（`dialogs/edit_dialog.py`）
- 弹窗窗口改为可缩放，横向 / 纵向滚动条按内容与视口大小自动出现（`dialogs/edit_dialog.py`、`ui/character_info_window.py`）
- choice 字段改用可搜索下拉并在提交前 `normalize()`；int 字段加输入期校验（`dialogs/edit_dialog.py`）
- 编辑势力弹窗改为「基本情况（两栏 + 君主头像）/ 可编辑信息（两栏）/ 独立·附庸（一行）」布局（`dialogs/faction_fields.py`、`dialogs/faction_edit.py`）
- 编辑据点弹窗改为「据点属性（两栏）/ 基本情况（只读）」两组（`dialogs/node_fields.py`）
- 人物编辑窗口：基础组改为左头像 + 右字段，势力下拉改可搜索，保存 / 取消移到窗口底部（`ui/character_info_window.py`）
- README 同步：§0 / §2 / §5.20 / §5.21 / §5.24 / §8.3（新增永久约束 57–59）/ §9.4 / §9.5 / §9.6

### Removed
- `FACTION_SECTIONS` 常量，改由 `faction_sections()` 构造（`dialogs/faction_fields.py`）

### Fixed
- README §8.3 交叉引用编号错位：正文外的 13 处「§8.3 第 N 条」统一修正回来（涉及 §3.2 / §3.6 / §5.3 / §5.6 / §5.20 / §5.22 / §6.5 / §7.1）

---

## 2026-09-27 · 官职体系（外官位阶 + 武官）

### Added
- 武官官名体系 `core/military_title.py`：32 rank / 84 官名常量表 + `rank_of` / `all_titles` / `is_unique` / `is_title_free` / `is_title_free_global` / `title_label`
- 外官位阶 rank 1–32：州级固定、郡级按县 level 分数分等（`county_score` / `county_rank` / `compute_county_ranks`）、县级按 level 映射、`official_rank_of_title`（`core/official_title.py`）
- `Character.military_title` 字段：加载可读，**不进 to_dict / 不参与 diff**（`core/character.py`）
- 官职体系窗口：按人物 / 按官职双模式 + 搜索 + 列头排序 + 位阶开关 + 全部外官开关 + 双击开人物情报（`ui/job_system_window.py`）
- `MainWindow._open_job_system_window()`（单例）+ `job_system` 动作分发（`ui/main_window.py`）
- 190 剧本武官分配 `assign_military_titles()`：君主史实武官 + 武力分档两阶段（`tools/build_scenario_190.py`、`scenarios/default.json`）

### Changed
- 顶部菜单重排为 文件 / 情报 / 游戏 / 查看 / 帮助：撤销 / 重做移入「文件」，删除「编辑」「势力」「命令」三个菜单（`ui/top_bar.py`）
- `TopBar._add_edit_command` 改为返回 (menu, index)；`set_edit_state` 按 `_undo_entry` / `_redo_entry` 定位，不再硬编码下标（`ui/top_bar.py`）
- README 同步：§0 / §1 / §2 / §3.3 / §4.6 / §5.15 / §5.16 / §5.25 / §5.26（新增小节）/ §6.5 / §7.3 / §8.1 / §8.4

### Fixed
- README §1 完成度清单的 190 剧本数字过期（势力 50 → 54、据点 611 → 616、外官 49 → 53），与 §4.5 对齐

---

## 2026-09-30 · 武官落盘与兵力上限系数

### Added
- 武官兵力上限系数：`MILITARY_TITLES` 由 `{rank: (官名, …)}` 改为 `{rank: (系数, (官名, …))}`（rank 1 = 4.35 → rank 32 = 1.02），新增 `SOLDIERS_CAP_NO_TITLE_FACTOR`（`config/rules.py`）
- 武官系数反查 `factor_of_rank` / `factor_of_title`（`core/military_title.py`）
- 兵力上限派生值 `Character.compute_soldiers_cap(leadership, military_title)`（静态纯函数）+ `soldiers_cap` property（`core/character.py`）
- 官职标签 `Character.job_label(world)` + `_officials_with_rank(world)`：武官 + 外官按 rank 串联，连接词取「、领 / 、兼 / 行」（`core/character.py`）
- 编辑人物窗口「官职」组：左武官可搜索下拉（label = `位阶 官名`，本势力已占用标「（已占用）」）+ 右外官区；保存时校验势力内唯一性（`ui/character_info_window.py`）
- 基础组只读「官职」行（可拖选 / Ctrl+C），高度随文本自动换行（`ui/character_info_window.py`）
- 190 剧本新增外官 070723「伊阙关都尉」（`scenarios/default.json`）

### Changed
- `Character.military_title` 由「不进 to_dict / 不参与 diff」改为**进序列化**，与 appeared / faction / node / location / role 同构（`core/character.py`）
- 兵力上限改为「统率曲线 × 武官 rank 系数」派生，原 `max_number_soldiers` 的调用点改走 `compute_soldiers_cap`（`ui/character_info_window.py`、`panels/character_panel.py`）
- 人物面板「官职」列改走 `job_label`（武官 + 外官串联，两者皆无仍留空），列宽 76 → 88（`panels/character_panel.py`）
- 人物情报窗口只读形态不再画头像与五维雷达图，只保留「官职」行 + 关系 + 生平（`ui/character_info_window.py`）
- `move_to_node.move_characters` 更名为 `dialog_move_characters`（`ui/dialogs/move_to_node.py`、`panels/character_panel.py`）
- 190 剧本 0231 / 0254 的势力与据点调整（`scenarios/default.json`）
- README 同步：§0 / §1 / §2 / §3.3 / §3.5 / §4.6 / §5.15 / §5.20 / §5.23 / §5.26 / §6.5 / §7.3 / §8.3 / §8.4 / §10.2

### Removed
- `config/rules.py::max_number_soldiers`，由 `Character.compute_soldiers_cap` 取代
