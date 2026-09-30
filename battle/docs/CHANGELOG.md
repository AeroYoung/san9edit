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

---

## 2026-09-30 · 步骤02 修订（UI 调整）

### Added
- `render/minimap.py`：小地图（地图外框 + 视口黄框 + 双方部队点 + 单击 / 拖动定位），与大地图共用同一个 `Camera`
- 窗口图标：`app.py` 的 `_make_app_icon()` 几何绘制（圆角底板 + 平顶六边形），`set_mode` 后立即设置
- 面板「部队情报组」：9 个字段（编号 / 阵营 / 兵种 / 坐标 / 兵力 / 士气 / 体力 / 状态 / 当前命令）
- 面板分组：兵种 / 状态两个维度 + 组头折叠 + 组内排序
- 面板表头：7 列（符号 / 部队 / 状态 / 兵力 / 士气 / 体力 / 命令）、双击排序、拖动与双击自适应列宽
- 面板多选：单击替换 / Ctrl 切换 / Shift 区间
- `Camera.center_on_world(x, y)`：小地图定位的唯一写入入口
- `symbol.render_thumbnail()`：面板符号列缩略图，复用同一套几何 / 填充 / 缓存
- `config.py`：字体字号 / Tab 阵营 / 面板行底色 / 情报组 / 控制台 / 小地图 / 图标 7 组常量；`PANEL_WIDTH` 300 → 420

### Changed
- 面板拆为「我方部队 / 敌方部队」两个 Tab，各只列本方部队；Tab3 / Tab4 留空
- 控制台：进行 / 暂停按钮放大到 160×80 并按状态换绿 / 红配色；命令按钮改 5 个（移动 / 攻击 / 待命 / 撤退 / 停止）、2 行排布、全部 disabled
- 选中语义：左键单击敌方单位也选中；框选不再按 side 过滤（选中集可含红蓝双方）
- 空格键与点击「进行 / 暂停」等价
- 事件顺序：小地图 → 面板 → 控制台 → `KEYDOWN` → 地图
- 渲染顺序：六宫格 → 部队层 → 面板 → 小地图 → 控制台
- 面板分组时只缩进「符号 + 部队」两列，右侧数值列保持原宽度
- 控制台高度不低于按钮组所需高度，窗口缩小时按钮不再溢出底板

### Removed
- 控制台「选取展示区」「全选」「清空选择」及其回调 `on_select_all` / `on_clear_selection`
- 小地图左上角的「小地图」文字标注

### Fixed
- 窗口缩小时控制台按钮组溢出底板（高度按内容所需夹取，极矮时按内高等比收缩按钮）
- 分组折叠标记 ▾ / ▸ 在系统 CJK 字体下渲染为方框：改用收录的 ▼ / ▲
