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
