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
