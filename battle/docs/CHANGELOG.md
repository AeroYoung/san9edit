# 战斗模块变更日志

记录战斗模块每轮的改动。分类：Added / Changed / Removed / Fixed。

---

## 2026-09-30 · 步骤01 模块骨架与日志抽离

### Added
- 战斗模块骨架：`__init__.py` / `__main__.py`（入口，`python -m battle` 与 `python battle/__main__.py` 两种启动方式等价；启动时把项目根补进 `sys.path`，任意 cwd 均可）/ `app.py`（pygame 初始化 + 事件 + 主循环）/ `config.py` / `balance.py`（占位）/ `api.py`（无 pygame 的 `BattleSession` / `BattleConfig` / `BattleResult` 壳）
- 六宫格几何 `core/hexgrid.py`：`offset_to_axial` / `axial_to_offset` / `axial_to_world` / `world_to_axial` / `distance` / `neighbors` / `ring` + `world_bounds` / `hex_corners`
- 地图加载 `core/map_data.py`：`load_map()` + `MapData` 容器，缺失 / 损坏 / 字段非法抛 `MapDataError`
- 相机 `render/camera.py`：`world_to_screen` / `screen_to_world` / `pan` / `zoom_at` / `on_resize` + zoom 与中心夹取
- 静态层绘制 `render/hex_renderer.py`：按视口 (col, row) 区间逐格绘制（绝不遍历全图）+ 视口外扩缓存 `CACHE_MARGIN_PX`（平移落在外扩范围内只 blit 不重建）+ 低缩放合并绘制（视口内格数 > `SOLID_FILL_CELL_LIMIT` 时降级为整块填充 + 地图外框，绘制调用降为 O(1)）
- 默认地图 `assets/maps/default.json`（400 × 300 格 / hex_size 28 / flat / tiles 空）
- 空包与占位目录：`core/` / `sim/` / `ai/` / `render/` 的 `__init__.py`、`assets/fonts/`、`data/`、`saves/`
- 文档：`docs/整体需求.md`（由《战斗模块总需求》落成本文件）、`docs/CHANGELOG.md`（本文档）

### Changed
- 日志改为依赖主游戏级单一定义源 `shared.logging_setup`（实现细节见根目录 `CHANGELOG.md`）
- 地图 `cols` / `rows` / `hex_size` 改 JSON 即可生效，不改代码

### Fixed
- 窗口大于桌面可用区域时标题栏（最小化 / 最大化 / 关闭）跑到屏幕外：初始尺寸改按 `pygame.display.get_desktop_sizes()` 夹取，并设 `SDL_VIDEO_CENTERED` 居中（`app.py`）

---

## 2026-09-30 · 步骤02 部队数据模型与兵棋符号

### Added
- `core/unit.py`：Unit 数据模型（id / side / type / q,r / troops / morale / stamina / facing / general_id）+ 6 个只读派生属性（查兵种表）+ `Unit.from_dict(d, side)`
- `core/unit_types.py`：兵种定义查询层（`get` / `exists` / `category_of` / `counter_multiplier`）
- `core/battle_state.py`：BattleState 容器（`unit` / `units_of` / `unit_at` / `all_units` / `units_in_axial_rect`）+ `from_json(path, side)` 载入与全套校验
- `render/symbol.py`：兵棋符号纯几何绘制（3 种外形 × 8 种填充模式 + 兵种小字 / 兵力数字 / 士气体力小条 / 远 LOD 色块 / 选中高亮）
- `render/unit_layer.py`：部队层（按轴向矩形视口裁剪 + 三级 LOD + `hit_test` / `box_select` + 框选虚线框）
- `render/panel.py`：右侧面板组（4 Tab；Tab1「部队」列表可点可滚，Tab2–4 显示「（本步未实现）」）
- `render/console.py`：底部控制台（进行 / 暂停 + 选取展示区 + 4 个 disabled 部队按钮 + 全选 / 清空选择）
- `render/widgets.py`：UI 通用小部件（字体 / 文字描边 / 圆角底板 / 三态按钮 / 半透明矩形 / 虚线框）
- `data/side_red.json` / `data/side_blue.json`：各 12 支（骑 4 + 步 4 + 弓 4），显式偏移坐标，覆盖十种兵种
- `config.py`：阵营色 / 符号尺寸 / 三级 LOD 阈值 / 选中与框选配色 / 面板与控制台尺寸 / 部队数据路径

### Changed
- `balance.py`：由占位 `{}` 改为 10 条兵种定义（含 `symbol_shape` / `symbol_fill`）+ 3×3 `COUNTER_MATRIX`
- `app.py`：装配 BattleState / 部队层 / 面板 / 控制台；渲染顺序改为 静态层 → 部队层 → 面板 → 控制台
- **交互变更**：左键拖拽由「平移视口」改为「框选」；平移改走右键 / 中键拖拽；左键单击己方单位单选，点空白 / 敌方单位清空选中
- 面板 / 控制台先于地图消费事件（其内的点击与滚轮不落到地图）
- 字体加载：`config.UI_FONT_PATH` 文件不存在时退回系统 CJK 字体（仍只用 pygame，不引入第三方依赖）
- 「进行 / 暂停」的 ▶ / ⏸ 图标改为几何绘制（系统 CJK 字体不含这两个码位，直接渲染会出方框）

### Fixed
- 初始缩放落在中 LOD 区间（格边长 26.7 px < 28），开局看不到兵力数字：初始缩放改由 `LOD_NEAR_MIN_PX` 派生（`INITIAL_HEX_STEP_PX = 1.5 × LOD_NEAR_MIN_PX`），开局即「近」LOD（`config.py`）
- 符号每帧逐单位重建 alpha 小面：改按（外形 / 填充 / 阵营 / 取整格边长）缓存，FIFO 上限 128（`render/symbol.py`）
- 面板部队列表超出可视区时无滚动提示：补画滚动条，放得下时不画（`render/panel.py`）
