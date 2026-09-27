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
