### battle/config.py

```python
# -*- coding: utf-8 -*-
"""战斗模块结构配置常量（窗口 / tick / 路径 / 颜色）。

- 路径一律以 `battle/` 为基准由 `__file__` 反推，**不用 cwd**。
- 数值平衡参数不在本模块，见 `balance.py`。
"""

from pathlib import Path

# battle/config.py → battle/
BATTLE_ROOT = Path(__file__).resolve().parent

# ============================================================
# 窗口
# ============================================================
WINDOW_WIDTH = 1600
WINDOW_HEIGHT = 1300
WINDOW_TITLE = "兵棋作战"

# ============================================================
# 帧率与 tick
# ============================================================
FPS = 60            # 渲染帧率
TICK_MS = 100       # 每 tick 毫秒（步骤01 只写常量，不驱动模拟）
SPEED_PRESETS = {1: 100, 2: 50, 4: 25}   # 速度档位（步骤01 只写常量）

# ============================================================
# 地图与六宫格
# ============================================================
HEX_SIZE = 28       # 外接圆半径（像素）；地图 JSON 有值时以 JSON 为准
MAP_PATH = BATTLE_ROOT / "assets" / "maps" / "default.json"
FONT_PATH = BATTLE_ROOT / "assets" / "fonts" / "NotoSansSC-Regular.otf"  # 步骤01 只写常量，不加载

# 缩放上限：单格边长（外接圆半径）到 200 像素
ZOOM_MAX_HEX_EDGE_PX = 200.0
# 滚轮单格缩放倍率
ZOOM_STEP = 1.1

# ---- 静态层绘制策略 ----
# 视口外扩缓存：静态层 Surface 四周各多画这么多像素，平移在此范围内不重建
CACHE_MARGIN_PX = 256
# 视口内格数超过此值时，降级为「整块填充 + 地图外框」（不再逐格描线）
# 取值依据：20000 格对应的格距约 13 px —— 再小下去格线已糊成一片；
# 切换点的一次性重建实测约 103 ms，之后整段最远缩放均降为 O(1)。
SOLID_FILL_CELL_LIMIT = 20000

# ============================================================
# 颜色（RGB）
# ============================================================
COLOR_BG = (20, 22, 26)             # 窗口背景
COLOR_VIEWPORT_MARGIN = (38, 42, 48)  # 视口内、地图包围盒之外的底色
COLOR_HEX_FILL = (222, 226, 214)    # 六宫格填充
COLOR_HEX_LINE = (110, 118, 106)    # 六宫格描边

# ============================================================
# 阵营与兵棋符号
# ============================================================
PLAYER_SIDE = "red"                 # 玩家方；框选 / 选中只对它生效
SIDE_COLOR = {                      # 阵营框色
    "red": (196, 60, 60),
    "blue": (60, 96, 196),
}
SYMBOL_LINE_WIDTH = 2               # 符号描边线宽（屏幕像素，不随 zoom 变）
SYMBOL_FILL_ALPHA = 220             # 实心区填充 alpha（0–255）
SYMBOL_FONT_SIZE_MIN = 11           # 兵种小字字号下限（远侧）
SYMBOL_FONT_SIZE_MAX = 16           # 兵种小字字号上限（近侧）
SYMBOL_TROOP_FONT_MIN = 10          # 兵力数字字号下限
SYMBOL_TROOP_FONT_MAX = 14          # 兵力数字字号上限
LOD_FAR_MAX_PX = 12                 # 格边长 < 此值 → 远 LOD
LOD_NEAR_MIN_PX = 28                # 格边长 ≥ 此值 → 近 LOD；居中 = 中 LOD

# 初始缩放：让屏幕上的格边长正好落在 LOD_NEAR_MIN_PX 上 —— 开局即「近」LOD，
# 符号下方直接看得到兵力数字。水平进阶 = 1.5 × HEX_SIZE × zoom，
# 故取 LOD_NEAR_MIN_PX × 1.5；改 LOD_NEAR_MIN_PX 时初始缩放自动跟随。
INITIAL_HEX_STEP_PX = 1.5 * LOD_NEAR_MIN_PX
LOD_FAR_COLOR = SIDE_COLOR          # 远 LOD 小色块取阵营色
LOD_FAR_SIZE_PX = 6                 # 远 LOD 小色块边长（屏幕像素）
SELECT_HIGHLIGHT_COLOR = (255, 220, 60)   # 选中高亮描边
SELECT_HIGHLIGHT_WIDTH = 3
SELECT_BOX_COLOR = (255, 220, 60, 80)     # 框选虚线框填充（半透明）

# ============================================================
# 右侧面板组 / 底部控制台
# ============================================================
PANEL_WIDTH = 300
PANEL_MARGIN = 20
PANEL_BG_COLOR = (28, 32, 40, 220)        # 面板底板（RGBA 半透明）
PANEL_BORDER_COLOR = (90, 100, 120)
PANEL_CORNER_RADIUS = 8
PANEL_TAB_HEIGHT = 36
PANEL_TAB_TITLES = ("部队", "面板2", "面板3", "面板4")
CONSOLE_HEIGHT = 120
CONSOLE_MARGIN = 20
CONSOLE_BG_COLOR = PANEL_BG_COLOR
UI_FONT_PATH = FONT_PATH            # 面板 / 控制台字体

UNIT_DATA_PATHS = {                 # 双方部队数据（以 battle/ 为基准反推）
    "red": BATTLE_ROOT / "data" / "side_red.json",
    "blue": BATTLE_ROOT / "data" / "side_blue.json",
}

# ============================================================
# 其他
# ============================================================
RANDOM_SEED = None  # 供后续战斗复现使用
DEBUG = False       # 调试总开关

```

### battle/balance.py

```python
# -*- coding: utf-8 -*-
"""战斗模块数值配置。

三类十种兵种 + 3×3 克制矩阵。改平衡只改这一处。
纯数据，无逻辑、无 pygame。
"""

# ============================================================
# 兵种表：key → 兵种定义
# ============================================================
# category：骑 / 步 / 弓（克制矩阵用它做键）
# symbol_shape：diamond（菱形）/ rect（横长方形 + X）/ square（正方形）
# symbol_fill：solid / top_half / hollow / slash / fill_three /
#              fill_left_right / fill_bottom / upper_left_half
UNIT_TYPES = {
    # ---------------- 骑兵类（菱形） ----------------
    "cataphract": {
        "key": "cataphract", "name": "具装甲骑", "category": "骑",
        "troops_max": 3000, "move_points": 2,
        "attack_melee": 90, "attack_ranged": None, "attack_range": 1,
        "defense": 85,
        "stamina_cost_move": 3.0, "stamina_cost_attack": 8.0,
        "stamina_recover": 1.5, "morale_recover": 1.0,
        "attack_cooldown": 12, "morale_hit": 1.5,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "diamond", "symbol_fill": "solid",
    },
    "heavy_cavalry": {
        "key": "heavy_cavalry", "name": "重骑", "category": "骑",
        "troops_max": 2800, "move_points": 3,
        "attack_melee": 80, "attack_ranged": None, "attack_range": 1,
        "defense": 70,
        "stamina_cost_move": 2.5, "stamina_cost_attack": 7.0,
        "stamina_recover": 1.5, "morale_recover": 1.0,
        "attack_cooldown": 10, "morale_hit": 1.5,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "diamond", "symbol_fill": "top_half",
    },
    "light_cavalry": {
        "key": "light_cavalry", "name": "轻骑", "category": "骑",
        "troops_max": 2200, "move_points": 4,
        "attack_melee": 60, "attack_ranged": None, "attack_range": 1,
        "defense": 50,
        "stamina_cost_move": 2.0, "stamina_cost_attack": 6.0,
        "stamina_recover": 2.0, "morale_recover": 1.2,
        "attack_cooldown": 8, "morale_hit": 1.2,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "diamond", "symbol_fill": "hollow",
    },
    "horse_archer": {
        "key": "horse_archer", "name": "弓骑", "category": "骑",
        "troops_max": 1800, "move_points": 4,
        "attack_melee": 40, "attack_ranged": 55, "attack_range": 3,
        "defense": 40,
        "stamina_cost_move": 2.0, "stamina_cost_attack": 6.0,
        "stamina_recover": 2.0, "morale_recover": 1.2,
        "attack_cooldown": 9, "morale_hit": 1.2,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "diamond", "symbol_fill": "slash",
    },

    # ---------------- 步兵类（横长方形 + X） ----------------
    "heavy_armor": {
        "key": "heavy_armor", "name": "重甲", "category": "步",
        "troops_max": 3500, "move_points": 1,
        "attack_melee": 70, "attack_ranged": None, "attack_range": 1,
        "defense": 90,
        "stamina_cost_move": 4.0, "stamina_cost_attack": 8.0,
        "stamina_recover": 1.5, "morale_recover": 1.5,
        "attack_cooldown": 12, "morale_hit": 1.0,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "rect", "symbol_fill": "fill_three",
    },
    "armored": {
        "key": "armored", "name": "甲士", "category": "步",
        "troops_max": 3000, "move_points": 2,
        "attack_melee": 60, "attack_ranged": None, "attack_range": 1,
        "defense": 70,
        "stamina_cost_move": 3.0, "stamina_cost_attack": 7.0,
        "stamina_recover": 1.8, "morale_recover": 1.5,
        "attack_cooldown": 10, "morale_hit": 1.0,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "rect", "symbol_fill": "fill_left_right",
    },
    "light_armor": {
        "key": "light_armor", "name": "甲兵", "category": "步",
        "troops_max": 2500, "move_points": 2,
        "attack_melee": 50, "attack_ranged": None, "attack_range": 1,
        "defense": 55,
        "stamina_cost_move": 3.0, "stamina_cost_attack": 6.0,
        "stamina_recover": 2.0, "morale_recover": 1.5,
        "attack_cooldown": 9, "morale_hit": 1.0,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "rect", "symbol_fill": "fill_bottom",
    },
    "levy": {
        "key": "levy", "name": "徒卒", "category": "步",
        "troops_max": 2000, "move_points": 3,
        "attack_melee": 35, "attack_ranged": None, "attack_range": 1,
        "defense": 40,
        "stamina_cost_move": 2.0, "stamina_cost_attack": 5.0,
        "stamina_recover": 2.5, "morale_recover": 1.5,
        "attack_cooldown": 8, "morale_hit": 1.0,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "rect", "symbol_fill": "hollow",
    },

    # ---------------- 弓兵类（正方形） ----------------
    "crossbow": {
        "key": "crossbow", "name": "弩士", "category": "弓",
        "troops_max": 1800, "move_points": 2,
        "attack_melee": 25, "attack_ranged": 90, "attack_range": 4,
        "defense": 35,
        "stamina_cost_move": 3.0, "stamina_cost_attack": 8.0,
        "stamina_recover": 2.0, "morale_recover": 1.2,
        "attack_cooldown": 14, "morale_hit": 1.0,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "square", "symbol_fill": "upper_left_half",
    },
    "archer": {
        "key": "archer", "name": "步弓", "category": "弓",
        "troops_max": 1600, "move_points": 3,
        "attack_melee": 30, "attack_ranged": 70, "attack_range": 3,
        "defense": 30,
        "stamina_cost_move": 2.5, "stamina_cost_attack": 7.0,
        "stamina_recover": 2.2, "morale_recover": 1.2,
        "attack_cooldown": 10, "morale_hit": 1.0,
        "morale_kill": 8.0, "morale_rout": 5.0,
        "symbol_shape": "square", "symbol_fill": "hollow",
    },
}

# ============================================================
# 克制矩阵：COUNTER_MATRIX[攻方类别][守方类别] = 倍率（本步只写表不消费）
# ============================================================
COUNTER_MATRIX = {
    "骑": {"骑": 1.0, "步": 0.9, "弓": 1.3},
    "步": {"骑": 1.3, "步": 1.0, "弓": 0.9},
    "弓": {"骑": 0.9, "步": 1.3, "弓": 1.0},
}

```

### battle/app.py

```python
# -*- coding: utf-8 -*-
"""战斗模块主程序：pygame 初始化 + 事件 + 主循环。

日志初始化在 `__main__.py` 完成，本模块只从 `pygame.init()` 起步。
渲染顺序：六宫格静态层 → 部队层 → 右侧面板组 → 底部控制台。
"""

import logging
import os
import sys

import pygame

from battle import config
from battle.core.battle_state import BattleState
from battle.core.map_data import MapDataError, load_map
from battle.render.camera import Camera
from battle.render.console import Console
from battle.render.hex_renderer import HexRenderer
from battle.render.panel import Panel
from battle.render.unit_layer import UnitLayer

logger = logging.getLogger("battle.app")

_CLICK_TOLERANCE_PX = 4   # 位移 ≤ 此值算「单击」，否则算「框选」


def run() -> int:
    """启动战斗窗口并跑主循环。返回进程退出码。"""
    # 让窗口在桌面上居中（否则尺寸受桌面限制时可能被摆到屏幕外）
    os.environ.setdefault("SDL_VIDEO_CENTERED", "1")
    pygame.init()
    try:
        return _main_loop()
    finally:
        pygame.quit()


# ------------------------------------------------------------
def _main_loop() -> int:
    win_w, win_h = _fit_to_desktop(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
    if (win_w, win_h) != (config.WINDOW_WIDTH, config.WINDOW_HEIGHT):
        logger.info(
            "窗口尺寸超出桌面可用区域：%s×%s → 收窄为 %s×%s",
            config.WINDOW_WIDTH, config.WINDOW_HEIGHT, win_w, win_h,
        )

    screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
    pygame.display.set_caption(config.WINDOW_TITLE)

    try:
        map_data = load_map(config.MAP_PATH)
    except MapDataError as exc:
        logger.error("地图加载失败：%s", exc)
        _fatal_dialog(f"地图加载失败：\n{exc}")
        return 1
    except Exception as exc:
        logger.error("地图加载出现未预期异常", exc_info=True)
        _fatal_dialog(f"地图加载出现未预期异常：\n{exc}")
        return 1

    viewport_w, viewport_h = screen.get_size()
    camera = Camera.for_map(map_data, viewport_w, viewport_h)
    hex_renderer = HexRenderer(map_data.cols, map_data.rows, map_data.hex_size)

    # 战斗状态：两侧部队数据各自载入
    state = BattleState(map_data.cols, map_data.rows)
    for side in ("red", "blue"):
        path = config.UNIT_DATA_PATHS.get(side)
        if path is not None:
            state.from_json(path, side)
    logger.info("战斗模块启动：地图 %s（%s×%s 格），部队 %s 支",
                map_data.name, map_data.cols, map_data.rows, len(state.units))

    unit_layer = UnitLayer(state, map_data)

    # ---------------- 运行状态 ----------------
    selected = set()          # 选中部队 id
    is_playing = False        # 进行 / 暂停（本步不驱动模拟）
    inter = {"box_start": None, "box_rect": None, "panning": False, "anchor": (0, 0)}

    def toggle_play():
        nonlocal is_playing
        is_playing = not is_playing
        logger.debug("进行 / 暂停：%s", "进行" if is_playing else "暂停")

    def select_all():
        selected.clear()
        selected.update(u.id for u in state.units_of(config.PLAYER_SIDE))
        logger.debug("全选：%s 支", len(selected))

    def clear_selection():
        selected.clear()
        logger.debug("清空选择")

    def select_one(unit_id):
        """单击地图棋子 / 面板行的语义：己方 → 单选；空白或敌方 → 清空。"""
        unit = state.unit(unit_id)
        selected.clear()
        if unit is not None and unit.side == config.PLAYER_SIDE:
            selected.add(unit.id)

    panel = Panel(state, on_select_unit=select_one)
    console = Console(state, on_toggle_play=toggle_play,
                      on_select_all=select_all,
                      on_clear_selection=clear_selection)
    panel.layout((viewport_w, viewport_h))
    console.layout((viewport_w, viewport_h), panel.rect().width)

    clock = pygame.time.Clock()

    while True:
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    logger.info("收到退出事件，正常退出")
                    return 0

                if event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode(
                        (event.w, event.h), pygame.RESIZABLE)
                    viewport_w, viewport_h = screen.get_size()
                    camera.on_resize(viewport_w, viewport_h)
                    continue

                # UI 层先消费（面板 / 控制台内的点击与滚轮不落到地图）
                if panel.handle_event(event) or console.handle_event(event):
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:              # 左键：选中 / 框选
                        inter["box_start"] = event.pos
                        inter["box_rect"] = pygame.Rect(event.pos, (0, 0))
                    elif event.button in (2, 3):       # 中键 / 右键：平移
                        inter["panning"] = True
                        inter["anchor"] = event.pos
                    elif event.button == 4:
                        camera.zoom_at(config.ZOOM_STEP, *event.pos)
                    elif event.button == 5:
                        camera.zoom_at(1.0 / config.ZOOM_STEP, *event.pos)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and inter["box_start"] is not None:
                        _finish_left_drag(inter["box_start"], event.pos,
                                          camera, unit_layer, selected)
                        inter["box_start"] = None
                        inter["box_rect"] = None
                    elif event.button in (2, 3):
                        inter["panning"] = False

                elif event.type == pygame.MOUSEMOTION:
                    if inter["panning"]:
                        camera.pan(event.pos[0] - inter["anchor"][0],
                                   event.pos[1] - inter["anchor"][1])
                        inter["anchor"] = event.pos
                    elif inter["box_start"] is not None:
                        inter["box_rect"] = _rect_between(
                            inter["box_start"], event.pos)

                elif event.type == pygame.MOUSEWHEEL:
                    mx, my = pygame.mouse.get_pos()
                    factor = (config.ZOOM_STEP if event.y > 0
                              else 1.0 / config.ZOOM_STEP)
                    camera.zoom_at(factor, mx, my)

            screen.fill(config.COLOR_BG)
            hex_renderer.draw(screen, camera)
            unit_layer.draw(screen, camera, selected, inter["box_rect"])
            panel.draw(screen, (viewport_w, viewport_h), selected)
            console.draw(screen, (viewport_w, viewport_h),
                         _selected_units(state, selected), is_playing,
                         panel.rect().width)
            pygame.display.flip()

        except Exception:
            # 运行时逻辑异常：ERROR + traceback 入日志，尝试继续运行
            logger.error("主循环异常", exc_info=True)
            if not pygame.get_init():
                logger.critical("pygame 已不可用，退出")
                return 1

        clock.tick(config.FPS)


# ------------------------------------------------------------
def _finish_left_drag(start, end, camera, unit_layer, selected):
    """松手：位移小 → 单击（单选 / 清空）；位移大 → 框选玩家方单位。"""
    if (abs(end[0] - start[0]) <= _CLICK_TOLERANCE_PX
            and abs(end[1] - start[1]) <= _CLICK_TOLERANCE_PX):
        unit = unit_layer.hit_test(start, camera)
        selected.clear()
        if unit is not None and unit.side == config.PLAYER_SIDE:
            selected.add(unit.id)
        return

    rect = _rect_between(start, end)
    hits = unit_layer.box_select(rect, camera, config.PLAYER_SIDE)
    modifiers = pygame.key.get_mods()
    if not modifiers & (pygame.KMOD_CTRL | pygame.KMOD_SHIFT):
        selected.clear()
    selected.update(u.id for u in hits)
    logger.debug("框选：命中 %s 支，当前选中 %s 支", len(hits), len(selected))


def _rect_between(a, b):
    """由两点构造规范化的矩形（宽高非负）。"""
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    return pygame.Rect(x0, y0, x1 - x0, y1 - y0)


def _selected_units(state, selected):
    """选中集 → Unit 列表（按 id 升序）。"""
    return sorted((state.unit(uid) for uid in selected if state.unit(uid)),
                  key=lambda u: u.id)


def _fit_to_desktop(width, height):
    """把初始窗口尺寸夹进桌面可用区域。

    `config` 里的 1600×1300 是设计尺寸；实际显示器常比它小（尤其开了 DPI 缩放），
    窗口一旦高过工作区，窗口管理器只能把它挪出屏幕 —— 标题栏连同最小化 /
    最大化 / 关闭三个按钮会一起跑到屏幕外。这里预留标题栏与任务栏的余量。
    """
    try:
        sizes = pygame.display.get_desktop_sizes()
    except Exception:
        logger.warning("无法读取桌面分辨率，按配置尺寸建窗", exc_info=True)
        return width, height
    if not sizes:
        return width, height

    desktop_w, desktop_h = sizes[0]
    avail_w = max(320, desktop_w - 20)   # 左右边框余量
    avail_h = max(240, desktop_h - 90)   # 标题栏 + 任务栏余量
    return min(width, avail_w), min(height, avail_h)


def _fatal_dialog(message):
    """尽力弹窗提示；无可用弹窗后端时退回终端输出。"""
    box = getattr(pygame.display, "message_box", None)
    if box is not None:
        try:
            box(config.WINDOW_TITLE, message, pygame.display.MESSAGEBOX_ERROR)
            return
        except Exception:
            logger.warning("pygame 弹窗失败，退回终端输出", exc_info=True)
    print(message, file=sys.stderr)

```

### battle/render/panel.py

```python
# -*- coding: utf-8 -*-
"""右侧面板组（浮于地图之上，不占地图布局空间）。

4 个 Tab：Tab1「部队」实装列表，Tab2–4 内容区显示「（本步未实现）」。
只读数据：不写 `BattleState` / `Unit` 的任何字段。
"""

import logging

import pygame

from battle import config
from battle.render import unit_layer
from battle.render import widgets

logger = logging.getLogger("battle.render.panel")

_ROW_HEIGHT = 24
_PAD = 12
_TAB_ACTIVE_BG = (56, 64, 80)
_TAB_BG = (38, 44, 56)
_ROW_ALT_BG = (36, 41, 51)
_ROW_HOVER_BG = (52, 60, 74)
_SCROLLBAR_WIDTH = 6
_SCROLLBAR_BG = (38, 44, 54)
_SCROLLBAR_FG = (108, 118, 138)


class Panel:
    """右侧面板组。"""

    def __init__(self, state, on_select_unit=None, player_side=None):
        self.state = state
        self.on_select_unit = on_select_unit
        self.player_side = player_side or config.PLAYER_SIDE

        self.active_tab = 0
        self.scroll = 0

        self._rect = pygame.Rect(0, 0, 0, 0)
        self._tab_rects = []
        self._content = pygame.Rect(0, 0, 0, 0)
        self._bg = None
        self._viewport_key = None

    # ============================================================
    # 布局
    # ============================================================
    def layout(self, viewport_size):
        """按视口重算面板矩形；屏幕过小时按比例收窄（不遮挡整屏）。"""
        vw, vh = viewport_size
        width = self._panel_width(vw)
        margin = config.PANEL_MARGIN
        height = max(120, vh - 2 * margin)
        self._rect = pygame.Rect(vw - margin - width, margin, width, height)

        tab_h = config.PANEL_TAB_HEIGHT
        tab_w = width // max(1, len(config.PANEL_TAB_TITLES))
        self._tab_rects = [
            pygame.Rect(self._rect.left + i * tab_w,
                        self._rect.top, tab_w, tab_h)
            for i in range(len(config.PANEL_TAB_TITLES))
        ]
        self._content = pygame.Rect(self._rect.left + _PAD,
                                    self._rect.top + tab_h + 4,
                                    width - 2 * _PAD,
                                    height - tab_h - 4 - _PAD)

        self._viewport_key = (vw, vh)
        self._bg = widgets.make_round_panel(self._rect.size)
        self._clamp_scroll()

    def _panel_width(self, viewport_w):
        """面板宽度：不超过屏宽的 40%，且不低于最小可读宽度。"""
        return max(160, min(config.PANEL_WIDTH, int(viewport_w * 0.4)))

    def rect(self):
        return self._rect

    def point_inside(self, pos):
        return self._rect.collidepoint(pos)

    # ============================================================
    # 事件
    # ============================================================
    def handle_event(self, event):
        """返回 True = 事件已被面板消费（不再交给地图）。"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.point_inside(event.pos):
                return False
            return self._on_click(event.pos)

        if event.type == pygame.MOUSEWHEEL:
            if not self.point_inside(pygame.mouse.get_pos()):
                return False
            if self.active_tab == 0:
                self.scroll -= event.y * _ROW_HEIGHT * 3
                self._clamp_scroll()
            return True   # 面板内滚轮一律吞掉，不影响地图 zoom

        return False

    def _on_click(self, pos):
        for index, rect in enumerate(self._tab_rects):
            if rect.collidepoint(pos):
                self.active_tab = index
                self.scroll = 0
                return True

        if self.active_tab == 0:
            row = self._row_index_at(pos)
            if row is not None and self.on_select_unit is not None:
                self.on_select_unit(self._rows()[row].id)
        return True

    def _rows(self):
        return self.state.all_units()

    def _row_index_at(self, pos):
        if not self._content.collidepoint(pos):
            return None
        offset = pos[1] - self._content.top + self.scroll
        index = int(offset // _ROW_HEIGHT)
        if 0 <= index < len(self._rows()):
            return index
        return None

    def _clamp_scroll(self):
        total = len(self._rows()) * _ROW_HEIGHT
        self.scroll = max(0, min(self.scroll, max(0, total - self._content.height)))

    # ============================================================
    # 绘制
    # ============================================================
    def draw(self, surface, viewport_size, selected):
        if tuple(viewport_size) != self._viewport_key:
            self.layout(viewport_size)
        surface.blit(self._bg, self._rect.topleft)
        self._draw_tabs(surface)
        if self.active_tab == 0:
            self._draw_unit_list(surface, selected)
        else:
            self._draw_empty(surface)

    def _draw_tabs(self, surface):
        font = widgets.get_font(13)
        for index, rect in enumerate(self._tab_rects):
            active = index == self.active_tab
            pygame.draw.rect(surface, _TAB_ACTIVE_BG if active else _TAB_BG, rect)
            if active:
                pygame.draw.line(surface, config.SELECT_HIGHLIGHT_COLOR,
                                 rect.bottomleft, rect.bottomright, 2)
            widgets.draw_text(surface, config.PANEL_TAB_TITLES[index],
                              rect.center, font,
                              widgets.TEXT_COLOR if active else widgets.TEXT_DIM,
                              anchor="center", outline=False)

    def _draw_empty(self, surface):
        font = widgets.get_font(13)
        widgets.draw_text(surface, "（本步未实现）", self._content.center,
                          font, widgets.TEXT_DIM, anchor="center", outline=False)

    def _draw_unit_list(self, surface, selected):
        rows = self._rows()
        font = widgets.get_font(11)
        mouse = pygame.mouse.get_pos()
        surface.set_clip(self._content)

        offset = -self.scroll
        for index, unit in enumerate(rows):
            top = self._content.top + offset + index * _ROW_HEIGHT
            rect = pygame.Rect(self._content.left, top,
                               self._content.width, _ROW_HEIGHT)
            if rect.bottom < self._content.top:
                continue
            if rect.top > self._content.bottom:
                break
            self._draw_row(surface, rect, unit, font, unit.id in selected,
                           rect.collidepoint(mouse) and self._content.collidepoint(mouse))

        surface.set_clip(None)
        self._draw_scrollbar(surface)

    def _draw_scrollbar(self, surface):
        """列表超出可视区时画滚动条（不超出则不画）。"""
        total = len(self._rows()) * _ROW_HEIGHT
        view = self._content.height
        if total <= view or view <= 0:
            return

        track = pygame.Rect(self._content.right - _SCROLLBAR_WIDTH,
                            self._content.top, _SCROLLBAR_WIDTH, view)
        pygame.draw.rect(surface, _SCROLLBAR_BG, track)

        thumb_h = max(24, int(view * view / total))
        max_scroll = total - view
        offset = 0 if max_scroll <= 0 else int((view - thumb_h) * (self.scroll / max_scroll))
        thumb = pygame.Rect(track.x, track.y + offset, track.width, thumb_h)
        pygame.draw.rect(surface, _SCROLLBAR_FG, thumb)

    def _draw_row(self, surface, rect, unit, font, is_selected, hovered):
        if hovered:
            pygame.draw.rect(surface, _ROW_HOVER_BG, rect)
        elif is_selected:
            pygame.draw.rect(surface, _ROW_ALT_BG, rect)

        left = rect.left
        # 选中标记
        widgets.draw_text(surface, "●" if is_selected else "○",
                          (left + 6, rect.centery), font,
                          config.SELECT_HIGHLIGHT_COLOR if is_selected
                          else widgets.TEXT_DIM,
                          anchor="midleft", outline=False)
        # 阵营：色点 + 文字
        dot = pygame.Rect(left + 24, rect.centery - 4, 8, 8)
        pygame.draw.rect(surface, config.SIDE_COLOR.get(unit.side, (200, 200, 200)), dot)
        side_text = "红" if unit.side == "red" else "蓝"
        widgets.draw_text(surface, side_text, (left + 36, rect.centery), font,
                          widgets.TEXT_COLOR, anchor="midleft", outline=False)
        # 兵种
        widgets.draw_text(surface, unit.name, (left + 62, rect.centery), font,
                          widgets.TEXT_COLOR, anchor="midleft", outline=False)
        # 兵力（右对齐到 200）
        widgets.draw_text(surface, unit_layer.format_troops(unit.troops),
                          (left + 200, rect.centery), font, widgets.TEXT_COLOR,
                          anchor="midright", outline=False)
        # 坐标
        col, row = unit.offset()
        widgets.draw_text(surface, "(%s, %s)" % (col, row),
                          (left + 206, rect.centery), font, widgets.TEXT_DIM,
                          anchor="midleft", outline=False)

```

### battle/render/console.py

```python
# -*- coding: utf-8 -*-
"""底部控制台（浮于地图之上，不占地图布局空间）。

左起：进行/暂停按钮 · 选取展示区 · 部队按钮区（本步全 disabled）· 全选 / 清空选择。
只读数据：不写 `BattleState` / `Unit` 的任何字段。
"""

import logging

import pygame

from battle import config
from battle.render import unit_layer
from battle.render import widgets

logger = logging.getLogger("battle.render.console")

_PAD = 12
_GAP = 10
_BTN_H = 34
_PLAY_W = 90
_OTHER_W = 120
_UNIT_BTN_LABELS = ("移动", "攻击", "待命", "停止")
_MAX_SELECTED_TEXT = 6


class Console:
    """底部控制台。"""

    def __init__(self, state, on_toggle_play=None,
                 on_select_all=None, on_clear_selection=None):
        self.state = state
        self.on_toggle_play = on_toggle_play
        self.on_select_all = on_select_all
        self.on_clear_selection = on_clear_selection

        self._rect = pygame.Rect(0, 0, 0, 0)
        self._bg = None
        self._layout_key = None
        self._play_btn = None
        self._unit_btns = []
        self._select_all_btn = None
        self._clear_btn = None
        self._selection_rect = pygame.Rect(0, 0, 0, 0)

    # ============================================================
    # 布局
    # ============================================================
    def layout(self, viewport_size, panel_width):
        """按视口与面板实际宽度重算控制台矩形与内部按钮。"""
        vw, vh = viewport_size
        margin = config.CONSOLE_MARGIN
        height = max(80, min(config.CONSOLE_HEIGHT, int(vh * 0.15)))
        width = max(240, vw - 2 * margin - panel_width - config.PANEL_MARGIN)
        self._rect = pygame.Rect(margin, vh - margin - height, width, height)

        inner = self._rect.inflate(-2 * _PAD, -2 * _PAD)
        btn_y = inner.centery - _BTN_H // 2

        self._play_btn = widgets.Button(
            (inner.left, btn_y, _PLAY_W, _BTN_H), "进行",
            font_size=13, icon="play")

        right_x = inner.right - _OTHER_W
        other_w = (_OTHER_W - _GAP) // 2
        self._select_all_btn = widgets.Button(
            (right_x, btn_y, other_w, _BTN_H), "全选", font_size=12)
        self._clear_btn = widgets.Button(
            (right_x + other_w + _GAP, btn_y, other_w, _BTN_H), "清空选择",
            font_size=12)

        middle_left = self._play_btn.rect.right + _GAP
        middle_right = right_x - _GAP
        middle_w = max(80, middle_right - middle_left)
        sel_w = max(80, middle_w // 2 - _GAP)
        self._selection_rect = pygame.Rect(
            middle_left, inner.top, sel_w, inner.height)

        unit_left = self._selection_rect.right + _GAP
        unit_w = max(80, middle_right - unit_left)
        btn_w = min(72, max(40, (unit_w - 3 * 6) // 4))
        self._unit_btns = []
        for index, label in enumerate(_UNIT_BTN_LABELS):
            rect = (unit_left + index * (btn_w + 6), btn_y, btn_w, _BTN_H)
            self._unit_btns.append(
                widgets.Button(rect, label, enabled=False, font_size=12))

        self._layout_key = ((vw, vh), int(panel_width))
        self._bg = widgets.make_round_panel(self._rect.size)

    def rect(self):
        return self._rect

    def point_inside(self, pos):
        return self._rect.collidepoint(pos)

    # ============================================================
    # 事件
    # ============================================================
    def handle_event(self, event):
        """返回 True = 事件已被控制台消费。"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.point_inside(event.pos):
                return False
            return self._on_click(event.pos)

        if event.type == pygame.MOUSEWHEEL and self.point_inside(pygame.mouse.get_pos()):
            return True   # 控制台内滚轮吞掉，不影响地图 zoom

        return False

    def _on_click(self, pos):
        for btn in self._unit_btns:
            if btn.hit_test(pos):
                logger.debug("部队按钮「%s」本步未实现（disabled）", btn.label)
                return True

        if self._play_btn.hit_test(pos):
            if self.on_toggle_play is not None:
                self.on_toggle_play()
            return True
        if self._select_all_btn.hit_test(pos):
            if self.on_select_all is not None:
                self.on_select_all()
            return True
        if self._clear_btn.hit_test(pos):
            if self.on_clear_selection is not None:
                self.on_clear_selection()
            return True
        return True   # 控制台内其它点击一律吞掉

    # ============================================================
    # 绘制
    # ============================================================
    def draw(self, surface, viewport_size, selected_units, is_playing, panel_width):
        if (tuple(viewport_size), int(panel_width)) != self._layout_key:
            self.layout(viewport_size, panel_width)

        surface.blit(self._bg, self._rect.topleft)
        mouse = pygame.mouse.get_pos()

        self._play_btn.label = "暂停" if is_playing else "进行"
        self._play_btn.icon = "pause" if is_playing else "play"
        self._play_btn.draw(surface, mouse)
        for btn in self._unit_btns:
            btn.draw(surface, mouse)
        self._select_all_btn.draw(surface, mouse)
        self._clear_btn.draw(surface, mouse)

        self._draw_selection(surface, selected_units)

    def _draw_selection(self, surface, selected_units):
        font = widgets.get_font(11)
        title = widgets.get_font(12)

        widgets.draw_text(surface, "选取：%s 支" % len(selected_units),
                          (self._selection_rect.left, self._selection_rect.top),
                          title, widgets.TEXT_DIM, anchor="topleft", outline=False)

        if not selected_units:
            widgets.draw_text(surface, "（未选中任何部队）",
                              (self._selection_rect.left, self._selection_rect.top + 20),
                              font, widgets.TEXT_DIM, anchor="topleft", outline=False)
            return

        units = sorted(selected_units, key=lambda u: u.id)
        shown = units[:_MAX_SELECTED_TEXT]
        lines = ["%s %s %s" % (u.id, u.name,
                               unit_layer.format_troops(u.troops)) for u in shown]
        if len(units) > len(shown):
            lines.append("… 另有 %s 支" % (len(units) - len(shown)))

        y = self._selection_rect.top + 20
        for line in lines:
            if y + 14 > self._selection_rect.bottom:
                break
            widgets.draw_text(surface, line,
                              (self._selection_rect.left, y), font,
                              widgets.TEXT_COLOR, anchor="topleft", outline=False)
            y += 16

```

### battle/render/widgets.py

```python
# -*- coding: utf-8 -*-
"""UI 通用小部件：字体 / 文字 / 圆角底板 / 按钮（三态）/ 半透明矩形 / 虚线框。

纯绘制，**不**读也不写任何战斗数据。
"""

import logging
from pathlib import Path

import pygame

from battle import config

logger = logging.getLogger("battle.render.widgets")

# 按钮配色（UI 细节，不进 config.py 的结构配置表）
BUTTON_BG = (52, 58, 70)
BUTTON_BG_HOVER = (76, 84, 100)
BUTTON_BG_DISABLED = (36, 40, 48)
BUTTON_BORDER = (90, 100, 120)
BUTTON_TEXT = (228, 232, 238)
BUTTON_TEXT_DISABLED = (118, 124, 134)
TEXT_COLOR = (228, 232, 238)
TEXT_DIM = (150, 156, 166)
TEXT_OUTLINE = (0, 0, 0)

_FONT_CACHE = {}
_font_fallback_logged = False
_CJK_SYS_FONTS = "microsoftyahei,simhei,simsun,notosanscjksc"


# ============================================================
# 字体
# ============================================================
def get_font(size):
    """按字号取字体（带缓存）。

    优先 `config.UI_FONT_PATH`；字体文件不存在时退回系统 CJK 字体
    （pygame 自带能力，不引入第三方依赖）；再失败用 pygame 默认字体。
    """
    size = int(size)
    font = _FONT_CACHE.get(size)
    if font is None:
        font = _load_font(size)
        _FONT_CACHE[size] = font
    return font


def _load_font(size):
    global _font_fallback_logged
    path = Path(str(config.UI_FONT_PATH))
    try:
        if path.exists():
            return pygame.font.Font(str(path), size)
    except Exception:
        logger.warning("字体文件加载失败：%s", path, exc_info=True)

    if not _font_fallback_logged:
        _font_fallback_logged = True
        logger.warning("字体文件不存在：%s，退回系统 CJK 字体", path)
    try:
        return pygame.font.SysFont(_CJK_SYS_FONTS, size)
    except Exception:
        logger.warning("系统字体不可用，退回 pygame 默认字体", exc_info=True)
        return pygame.font.Font(None, size)


# ============================================================
# 文字
# ============================================================
def draw_text(surface, text, pos, font, color=TEXT_COLOR,
              anchor="topleft", outline_color=TEXT_OUTLINE, outline=True):
    """画一行文字，可带 1px 描边（保证在任意地图底色上都可读）。

    返回文字矩形（屏幕坐标）。
    """
    img = font.render(text, True, color)
    rect = img.get_rect(**{anchor: pos})
    if outline and outline_color is not None:
        shadow = font.render(text, True, outline_color)
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            surface.blit(shadow, rect.move(dx, dy))
    surface.blit(img, rect)
    return rect


# ============================================================
# 底板 / 填充
# ============================================================
def make_round_panel(size, bg_color=None, border_color=None, radius=None):
    """生成一块圆角半透明底板。调用方缓存它，避免每帧重建。"""
    bg_color = config.PANEL_BG_COLOR if bg_color is None else bg_color
    border_color = config.PANEL_BORDER_COLOR if border_color is None else border_color
    radius = config.PANEL_CORNER_RADIUS if radius is None else radius

    surf = pygame.Surface(size, pygame.SRCALPHA)
    rect = surf.get_rect()
    if bg_color is not None:
        pygame.draw.rect(surf, bg_color, rect, border_radius=radius)
    if border_color is not None and radius is not None:
        pygame.draw.rect(surf, border_color, rect, width=1, border_radius=radius)
    return surf


def draw_alpha_rect(surface, rect, rgba):
    """画一块半透明矩形（临时 surface，仅在需要时调用）。"""
    w, h = max(1, rect.width), max(1, rect.height)
    layer = pygame.Surface((w, h), pygame.SRCALPHA)
    layer.fill(rgba)
    surface.blit(layer, rect.topleft)


def draw_dashed_rect(surface, color, rect, dash=(6, 4), width=1):
    """画虚线矩形（四边各自分段；步长 = dash）。"""
    on, off = dash
    step = on + off

    for x in range(rect.left, rect.right, step):
        end = min(x + on, rect.right)
        pygame.draw.line(surface, color, (x, rect.top), (end, rect.top), width)
        pygame.draw.line(surface, color, (x, rect.bottom), (end, rect.bottom), width)
    for y in range(rect.top, rect.bottom, step):
        end = min(y + on, rect.bottom)
        pygame.draw.line(surface, color, (rect.left, y), (rect.left, end), width)
        pygame.draw.line(surface, color, (rect.right, y), (rect.right, end), width)


# ============================================================
# 按钮
# ============================================================
def draw_play_icon(surface, center, color):
    """「▶」三角：几何绘制，不依赖字体是否收录该码位。"""
    cx, cy = center
    points = [(cx - 5, cy - 6), (cx + 6, cy), (cx - 5, cy + 6)]
    pygame.draw.polygon(surface, color, points)


def draw_pause_icon(surface, center, color):
    """「⏸」双竖条：同样几何绘制。"""
    cx, cy = center
    pygame.draw.rect(surface, color, pygame.Rect(cx - 5, cy - 6, 4, 12))
    pygame.draw.rect(surface, color, pygame.Rect(cx + 2, cy - 6, 4, 12))


class Button:
    """三态按钮（normal / hover / disabled）。

    `enabled=False` 时**不**消费点击事件（点击交给上层写日志）。
    `icon` 取 `"play"` / `"pause"` / None —— 图标几何绘制在文字左侧。
    """

    def __init__(self, rect, label, enabled=True, font_size=12, icon=None):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.enabled = enabled
        self.font_size = font_size
        self.icon = icon
        self.hovered = False

    # ---------------- 事件 ----------------
    def hit_test(self, pos):
        return self.rect.collidepoint(pos)

    def handle_event(self, event):
        """返回 True = 本次事件已消费。"""
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.hit_test(event.pos)
        return False

    # ---------------- 绘制 ----------------
    def draw(self, surface, mouse_pos):
        self.hovered = self.enabled and self.rect.collidepoint(mouse_pos)
        if not self.enabled:
            bg = BUTTON_BG_DISABLED
        elif self.hovered:
            bg = BUTTON_BG_HOVER
        else:
            bg = BUTTON_BG

        pygame.draw.rect(surface, bg, self.rect,
                         border_radius=config.PANEL_CORNER_RADIUS - 2)
        pygame.draw.rect(surface, BUTTON_BORDER, self.rect, width=1,
                         border_radius=config.PANEL_CORNER_RADIUS - 2)

        color = BUTTON_TEXT if self.enabled else BUTTON_TEXT_DISABLED
        font = get_font(self.font_size)
        img = font.render(self.label, True, color)

        icon_w = 12 if self.icon else 0
        gap = 6 if self.icon else 0
        total = icon_w + gap + img.get_width()
        x = self.rect.centerx - total // 2
        if self.icon == "play":
            draw_play_icon(surface, (x + 6, self.rect.centery), color)
        elif self.icon == "pause":
            draw_pause_icon(surface, (x + 6, self.rect.centery), color)
        surface.blit(img, (x + icon_w + gap,
                           self.rect.centery - img.get_height() // 2))

```

### battle/render/camera.py

```python
# -*- coding: utf-8 -*-
"""相机：视口平移 / 缩放 / 世界⇄屏幕变换。

渲染层**只读数据**：本模块不写任何游戏状态。
"""

from battle import config
from battle.core import hexgrid


class Camera:
    """世界坐标（浮点，像素）与屏幕坐标之间的变换。

    属性：
        cx / cy   相机中心（世界坐标，浮点）
        zoom      像素 / 世界单位
    """

    def __init__(self, world_width, world_height, viewport_w, viewport_h,
                 hex_size):
        self.world_width = float(world_width)
        self.world_height = float(world_height)
        self.viewport_w = int(viewport_w)
        self.viewport_h = int(viewport_h)
        self.hex_size = float(hex_size)

        # 缩放范围
        self.zoom_max = config.ZOOM_MAX_HEX_EDGE_PX / self.hex_size
        self.zoom_min = self._compute_zoom_min()
        # 初始：每格水平进阶约 INITIAL_HEX_STEP_PX 像素
        self.zoom = config.INITIAL_HEX_STEP_PX / (1.5 * self.hex_size)

        self.cx = self.world_width / 2.0
        self.cy = self.world_height / 2.0

        self._clamp_zoom()
        self._clamp_center()

    # ------------------------------------------------------------
    # 变换
    # ------------------------------------------------------------
    def world_to_screen(self, x, y):
        """世界坐标 → 屏幕坐标。"""
        sx = (x - self.cx) * self.zoom + self.viewport_w / 2.0
        sy = (y - self.cy) * self.zoom + self.viewport_h / 2.0
        return sx, sy

    def screen_to_world(self, sx, sy):
        """屏幕坐标 → 世界坐标。"""
        x = (sx - self.viewport_w / 2.0) / self.zoom + self.cx
        y = (sy - self.viewport_h / 2.0) / self.zoom + self.cy
        return x, y

    def visible_world_rect(self):
        """当前视口覆盖的世界矩形 (x0, y0, x1, y1)，供渲染层裁剪。"""
        x0, y0 = self.screen_to_world(0, 0)
        x1, y1 = self.screen_to_world(self.viewport_w, self.viewport_h)
        return x0, y0, x1, y1

    # ------------------------------------------------------------
    # 操作
    # ------------------------------------------------------------
    def pan(self, dx, dy):
        """按屏幕像素位移平移视口。"""
        self.cx -= dx / self.zoom
        self.cy -= dy / self.zoom
        self._clamp_center()

    def zoom_at(self, factor, sx, sy):
        """以屏幕锚点 (sx, sy) 为不动点缩放，自动夹在 [zoom_min, zoom_max]。"""
        ax, ay = self.screen_to_world(sx, sy)
        self.zoom *= factor
        self._clamp_zoom()
        # 让锚点缩放后仍落在同一屏幕位置
        self.cx = ax - (sx - self.viewport_w / 2.0) / self.zoom
        self.cy = ay - (sy - self.viewport_h / 2.0) / self.zoom
        self._clamp_center()

    def on_resize(self, width, height):
        """窗口尺寸变化：重算视口并重夹缩放与中心。"""
        self.viewport_w = int(width)
        self.viewport_h = int(height)
        self.zoom_min = self._compute_zoom_min()
        self._clamp_zoom()
        self._clamp_center()

    # ------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------
    def _compute_zoom_min(self):
        """整张地图完整可见，且包围盒较长边 ≈ min(屏宽, 屏高) × 0.5。"""
        shorter = max(1.0, min(self.viewport_w, self.viewport_h))
        longer_side = max(self.world_width, self.world_height)
        return (shorter * 0.5) / longer_side

    def _clamp_zoom(self):
        if self.zoom_min > self.zoom_max:
            # 视口小到与上限打架时，优先保证不越上限
            self.zoom = self.zoom_max
            return
        self.zoom = max(self.zoom_min, min(self.zoom_max, self.zoom))

    def _clamp_center(self):
        self.cx = max(0.0, min(self.world_width, self.cx))
        self.cy = max(0.0, min(self.world_height, self.cy))

    # ------------------------------------------------------------
    @classmethod
    def for_map(cls, map_data, viewport_w, viewport_h):
        """按地图数据建相机（世界尺寸由 hexgrid 统一给出）。"""
        width, height = hexgrid.world_bounds(
            map_data.cols, map_data.rows, map_data.hex_size)
        return cls(width, height, viewport_w, viewport_h, map_data.hex_size)

```

### battle/render/unit_layer.py

```python
# -*- coding: utf-8 -*-
"""部队绘制层：视口裁剪 + 三级 LOD + 命中测试 + 框选。

渲染层**只读数据**：不写 `BattleState` / `Unit` 的任何字段。
"""

import logging
import math

import pygame

from battle import config
from battle.core import hexgrid
from battle.render import symbol as sym
from battle.render import widgets

logger = logging.getLogger("battle.render.unit_layer")

_SQRT3 = math.sqrt(3.0)

LOD_FAR = "far"
LOD_MID = "mid"
LOD_NEAR = "near"

# 符号可能超出格子的余量（小字 / 小条 / 高亮圈），裁剪时放宽这么多像素
_CULL_MARGIN_PX = 64


class UnitLayer:
    """把 `BattleState` 里的单位画到屏幕上。"""

    def __init__(self, state, map_data):
        self.state = state
        self.cols = int(map_data.cols)
        self.rows = int(map_data.rows)
        self.hex_size = float(map_data.hex_size)

    # ============================================================
    # LOD
    # ============================================================
    def edge_px(self, camera):
        """屏幕上的格边长（像素）。"""
        return camera.zoom * self.hex_size

    def lod_of(self, camera):
        edge = self.edge_px(camera)
        if edge < config.LOD_FAR_MAX_PX:
            return LOD_FAR
        if edge >= config.LOD_NEAR_MIN_PX:
            return LOD_NEAR
        return LOD_MID

    def font_sizes(self, camera):
        """(兵种小字字号, 兵力数字字号)：按格边长在区间内插值。"""
        span = max(1e-6, config.LOD_NEAR_MIN_PX - config.LOD_FAR_MAX_PX)
        t = (self.edge_px(camera) - config.LOD_FAR_MAX_PX) / span
        t = max(0.0, min(1.0, t))
        label = config.SYMBOL_FONT_SIZE_MIN + t * (
            config.SYMBOL_FONT_SIZE_MAX - config.SYMBOL_FONT_SIZE_MIN)
        troops = config.SYMBOL_TROOP_FONT_MIN + t * (
            config.SYMBOL_TROOP_FONT_MAX - config.SYMBOL_TROOP_FONT_MIN)
        return int(round(label)), int(round(troops))

    # ============================================================
    # 绘制
    # ============================================================
    def draw(self, surface, camera, selected, box_rect=None):
        """画全部可见单位 + 选中高亮 +（拖拽中的）框选虚线框。"""
        lod = self.lod_of(camera)
        label_size, troop_size = self.font_sizes(camera)
        size_px = self.edge_px(camera)

        for unit, center in self._visible_units(camera):
            type_def = unit.type_def or {}
            shape = type_def.get("symbol_shape", sym.SHAPE_SQUARE)
            is_selected = unit.id in selected

            if lod == LOD_FAR:
                sym.draw_far_block(surface, center, unit.side)
                if is_selected:
                    sym.draw_highlight(surface, center, shape, size_px,
                                       is_block=True)
                continue

            sym.draw_symbol(surface, center, type_def, unit.side, size_px)
            sym.draw_bars(surface, center, unit.morale, unit.stamina,
                          shape, size_px)
            sym.draw_label(surface, center, unit.name,
                           shape, size_px, label_size)
            if lod == LOD_NEAR:
                sym.draw_troops(surface, center, format_troops(unit.troops),
                                shape, size_px, troop_size)
            if is_selected:
                sym.draw_highlight(surface, center, shape, size_px)

        if box_rect is not None and box_rect.width > 0 and box_rect.height > 0:
            self._draw_box(surface, box_rect)

    def _draw_box(self, surface, box_rect):
        """框选：半透明填充 + 虚线边框。"""
        widgets.draw_alpha_rect(surface, box_rect, config.SELECT_BOX_COLOR)
        widgets.draw_dashed_rect(surface, config.SELECT_HIGHLIGHT_COLOR,
                                 box_rect, dash=(6, 4), width=1)

    # ============================================================
    # 查询
    # ============================================================
    def hit_test(self, pos, camera):
        """屏幕点 → 该格单位；空格 / 无单位 → None。"""
        wx, wy = camera.screen_to_world(pos[0], pos[1])
        q, r = hexgrid.world_to_axial(wx, wy, self.hex_size)
        return self.state.unit_at(q, r)

    def box_select(self, box_rect, camera, side_filter=None):
        """返回矩形内的单位（只返回 `side_filter` 匹配的）。"""
        out = []
        for unit, center in self._visible_units(camera, margin=0):
            if side_filter is not None and unit.side != side_filter:
                continue
            if box_rect.collidepoint(center):
                out.append(unit)
        return out

    # ============================================================
    # 视口裁剪
    # ============================================================
    def _visible_units(self, camera, margin=_CULL_MARGIN_PX):
        """视口内的单位：(unit, 屏幕中心) 迭代器。

        先按视口反算轴向矩形做粗筛，再按屏幕坐标精筛 —— 不遍历全表。
        """
        q_lo, q_hi, r_lo, r_hi = self._axial_rect(camera)
        viewport_w = camera.viewport_w
        viewport_h = camera.viewport_h
        size = self.hex_size

        for unit in self.state.units_in_axial_rect(q_lo, q_hi, r_lo, r_hi):
            wx, wy = hexgrid.axial_to_world(unit.q, unit.r, size)
            sx, sy = camera.world_to_screen(wx, wy)
            if (-margin <= sx <= viewport_w + margin
                    and -margin <= sy <= viewport_h + margin):
                yield unit, (sx, sy)

    def _axial_rect(self, camera):
        """视口覆盖的轴向坐标矩形（保守取大，保证不漏）。"""
        x0, y0, x1, y1 = camera.visible_world_rect()
        size = self.hex_size

        q_lo = int(math.floor(x0 / (1.5 * size))) - 1
        q_hi = int(math.ceil(x1 / (1.5 * size))) + 1
        q_lo = max(0, min(self.cols - 1, q_lo))
        q_hi = max(0, min(self.cols - 1, q_hi))

        # y = √3·size·(r + q/2) ⇒ r = y/(√3·size) − q/2，按 q 的两端放宽
        r_lo = int(math.floor(y0 / (_SQRT3 * size) - q_hi / 2.0)) - 1
        r_hi = int(math.ceil(y1 / (_SQRT3 * size) - q_lo / 2.0)) + 1
        r_lo = max(0, min(self.rows - 1, r_lo))
        r_hi = max(0, min(self.rows - 1, r_hi))
        return q_lo, q_hi, r_lo, r_hi


def format_troops(troops):
    """兵力千分位文本。"""
    return format(int(troops), ",")

```

### battle/render/symbol.py

```python
# -*- coding: utf-8 -*-
"""兵棋符号绘制（纯几何，只读数据）。

外形按兵种类别：菱形（骑）/ 横长方形 + X（步）/ 正方形（弓）；
具体兵种靠**填充模式** + 框上方小字区分。规则见
`battle/docs/步骤02需求.md` §3.5。

所有尺寸都以「格边长」（`camera.zoom * HEX_SIZE`）为基准按比例给，
因此符号随 zoom 等比缩放，不「跳级」；描边线宽固定为屏幕像素。
"""

import math

import pygame

from battle import config
from battle.render import widgets

SHAPE_DIAMOND = "diamond"
SHAPE_RECT = "rect"
SHAPE_SQUARE = "square"

# 外形半宽 / 半高（× 格边长）
_EXTENT = {
    SHAPE_DIAMOND: (0.7, 0.7),
    SHAPE_RECT: (0.8, 0.4),
    SHAPE_SQUARE: (0.5, 0.5),
}

# 步兵横长方形被两条对角线切成的四个三角区（以矩形边命名）
_REGION_TOP = "top"
_REGION_RIGHT = "right"
_REGION_BOTTOM = "bottom"
_REGION_LEFT = "left"

# 填充模式 → 需要实心的区；`solid` / `top_half` / `upper_left_half` 另有分支
_REGION_FILLS = {
    "fill_three": (_REGION_RIGHT, _REGION_BOTTOM, _REGION_LEFT),
    "fill_left_right": (_REGION_RIGHT, _REGION_LEFT),
    "fill_bottom": (_REGION_BOTTOM,),
    "hollow": (),
}

_TEXT_COLOR = (230, 230, 230)
_BAR_BG = (60, 60, 60)
_MORALE_COLOR = (120, 200, 120)
_STAMINA_COLOR = (200, 170, 90)
_BAR_WIDTH = 4
_BAR_GAP = 3


# ============================================================
# 几何
# ============================================================
def extent(shape, size_px):
    """外形的 (半宽, 半高)。"""
    hw, hh = _EXTENT.get(shape, _EXTENT[SHAPE_SQUARE])
    return hw * size_px, hh * size_px


def shape_points(shape, center, size_px):
    """外形顶点（屏幕坐标）。

    返回顺序固定：
    - 菱形：上 / 右 / 下 / 左
    - 正方形与横长方形：左上 / 右上 / 右下 / 左下
    """
    cx, cy = center
    hw, hh = extent(shape, size_px)
    if shape == SHAPE_DIAMOND:
        return [(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)]
    return [(cx - hw, cy - hh), (cx + hw, cy - hh),
            (cx + hw, cy + hh), (cx - hw, cy + hh)]


def fill_polygons(shape, points, fill_mode):
    """该填充模式下需要实心的多边形列表（空列表 = 全空心）。"""
    if fill_mode == "solid":
        return [points]
    if fill_mode == "top_half":
        # 菱形沿水平中线切分，上半实心：上 / 右 / 左 三个顶点
        return [[points[0], points[1], points[3]]]
    if fill_mode == "upper_left_half":
        # 正方形沿「右上—左下」对角线切分，左上三角实心
        return [[points[0], points[1], points[3]]]
    if shape == SHAPE_RECT:
        tl, tr, br, bl = points
        cx = (tl[0] + br[0]) / 2.0
        cy = (tl[1] + br[1]) / 2.0
        center = (cx, cy)
        regions = {
            _REGION_TOP: [tl, tr, center],
            _REGION_RIGHT: [tr, br, center],
            _REGION_BOTTOM: [br, bl, center],
            _REGION_LEFT: [bl, tl, center],
        }
        return [regions[name] for name in _REGION_FILLS.get(fill_mode, ())]
    return []


def _midpoint(a, b):
    return ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)


# ============================================================
# 绘制：符号本体
# ============================================================
def draw_symbol(surface, center, type_def, side, size_px):
    """画符号本体（外形 + 填充 + 描边）；不含小字 / 数值 / 小条。

    同一（外形 / 填充 / 阵营 / 取整后的格边长）只在首次绘制时开 alpha 面，
    之后复用缓存 —— 平移时不再逐单位重建小面。缓存容量有上限，按 FIFO 淘汰。
    """
    key = (type_def.get("symbol_shape", SHAPE_SQUARE),
           type_def.get("symbol_fill", "hollow"),
           side, int(round(size_px)))
    cached = _SYMBOL_CACHE.get(key)
    if cached is None:
        cached = _render_symbol(*key)
        if len(_SYMBOL_CACHE) >= _SYMBOL_CACHE_LIMIT:
            _SYMBOL_CACHE.pop(next(iter(_SYMBOL_CACHE)))   # dict 保序 → FIFO
        _SYMBOL_CACHE[key] = cached

    layer, ox, oy = cached
    surface.blit(layer, (int(round(center[0])) - ox,
                         int(round(center[1])) - oy))


def _render_symbol(shape, fill_mode, side, size_px):
    """把符号画成一块以中心为基准的小面。

    返回 (surface, 符号中心在该面内的 x, y)。
    """
    color = config.SIDE_COLOR.get(side, (200, 200, 200))
    points = shape_points(shape, (0.0, 0.0), size_px)
    solids = fill_polygons(shape, points, fill_mode)

    pad = config.SYMBOL_LINE_WIDTH + 2
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    left = int(math.floor(min(xs))) - pad
    top = int(math.floor(min(ys))) - pad
    width = int(math.ceil(max(xs))) + pad - left
    height = int(math.ceil(max(ys))) + pad - top
    layer = pygame.Surface((max(1, width), max(1, height)), pygame.SRCALPHA)

    local_points = [(x - left, y - top) for x, y in points]
    alpha_color = (color[0], color[1], color[2], config.SYMBOL_FILL_ALPHA)
    for poly in solids:
        pygame.draw.polygon(layer, alpha_color,
                            [(x - left, y - top) for x, y in poly])

    pygame.draw.polygon(layer, color, local_points, config.SYMBOL_LINE_WIDTH)
    _draw_extra_lines(layer, shape, local_points, fill_mode, color)
    return layer, -left, -top


# 符号小面缓存：key = (外形, 填充, 阵营, 取整格边长)
_SYMBOL_CACHE = {}
_SYMBOL_CACHE_LIMIT = 128


def _draw_extra_lines(layer, shape, points, fill_mode, color):
    """步兵的 X 线，以及弓骑的中间斜线。"""
    if shape == SHAPE_RECT:
        pygame.draw.line(layer, color, points[0], points[2], config.SYMBOL_LINE_WIDTH)
        pygame.draw.line(layer, color, points[1], points[3], config.SYMBOL_LINE_WIDTH)
    elif fill_mode == "slash":
        # 菱形内的一条「/」斜线：从左下边中点穿过中心到右上边中点
        p_top, p_right, p_bottom, p_left = points
        pygame.draw.line(layer, color,
                         _midpoint(p_left, p_bottom),
                         _midpoint(p_top, p_right),
                         config.SYMBOL_LINE_WIDTH)


# ============================================================
# 绘制：附加信息
# ============================================================
def draw_label(surface, center, text, shape, size_px, font_size):
    """兵种小字：框上方居中。"""
    if not text:
        return
    _, hh = extent(shape, size_px)
    font = widgets.get_font(font_size)
    widgets.draw_text(surface, text, (center[0], center[1] - hh - 2),
                      font, _TEXT_COLOR, anchor="midbottom")


def draw_troops(surface, center, text, shape, size_px, font_size):
    """兵力数字：框下方居中。"""
    if not text:
        return
    _, hh = extent(shape, size_px)
    font = widgets.get_font(font_size)
    widgets.draw_text(surface, text, (center[0], center[1] + hh + 2),
                      font, _TEXT_COLOR, anchor="midtop")


def draw_bars(surface, center, morale, stamina, shape, size_px):
    """士气（左）/ 体力（右）竖条：0–100 映射到条高。"""
    hw, hh = extent(shape, size_px)
    bar_h = max(10, int(round(hh * 2)))
    top = center[1] - bar_h / 2.0

    for x, value, color in (
        (center[0] - hw - _BAR_GAP - _BAR_WIDTH, morale, _MORALE_COLOR),
        (center[0] + hw + _BAR_GAP, stamina, _STAMINA_COLOR),
    ):
        rect = pygame.Rect(int(round(x)), int(round(top)), _BAR_WIDTH, bar_h)
        pygame.draw.rect(surface, _BAR_BG, rect)
        ratio = max(0.0, min(1.0, float(value) / 100.0))
        if ratio > 0:
            fill_h = max(1, int(round(bar_h * ratio)))
            fill = pygame.Rect(rect.x, rect.bottom - fill_h, _BAR_WIDTH, fill_h)
            pygame.draw.rect(surface, color, fill)


def draw_far_block(surface, center, side, size_px=None):
    """远 LOD：小色块（不画外形 / 小字 / 数值 / 小条）。"""
    size = config.LOD_FAR_SIZE_PX if size_px is None else int(size_px)
    color = config.LOD_FAR_COLOR.get(side, (200, 200, 200))
    rect = pygame.Rect(0, 0, size, size)
    rect.center = (int(round(center[0])), int(round(center[1])))
    pygame.draw.rect(surface, color, rect)


def draw_highlight(surface, center, shape, size_px, is_block=False):
    """选中高亮：沿符号最外层描一圈（远 LOD 时围住小色块）。"""
    color = config.SELECT_HIGHLIGHT_COLOR
    width = config.SELECT_HIGHLIGHT_WIDTH
    if is_block:
        size = config.LOD_FAR_SIZE_PX + 2 * width
        rect = pygame.Rect(0, 0, size, size)
        rect.center = (int(round(center[0])), int(round(center[1])))
        pygame.draw.rect(surface, color, rect, width)
        return
    points = shape_points(shape, center, size_px * 1.12)
    pygame.draw.polygon(surface, color, points, width)

```

### battle/render/hex_renderer.py

```python
# -*- coding: utf-8 -*-
"""六宫格绘制：视口裁剪 + 外扩缓存 + 低缩放合并绘制。

渲染层**只读数据**：不写任何游戏状态。

绘制策略
--------
1. **视口裁剪**：只遍历视口覆盖的 (col, row) 区间，绝不遍历全图 12 万格。
2. **外扩缓存**：静态层 Surface 比视口四周各大 `CACHE_MARGIN_PX`，平移只要
   新视口仍落在缓存覆盖范围内就直接复用，不重建。
3. **低缩放合并**：视口内格数超过 `SOLID_FILL_CELL_LIMIT` 时（此时单格已小于
   约 12 像素，逐格描线只会糊成一片），降级为「整块填充 + 地图外框」，
   把 O(格数) 的绘制降成 O(1)。
"""

import logging
import math

import pygame

from battle import config
from battle.core import hexgrid

logger = logging.getLogger("battle.render.hex_renderer")

_SQRT3 = math.sqrt(3.0)


class HexRenderer:
    """平顶六宫格静态层。"""

    def __init__(self, cols, rows, hex_size):
        self.cols = int(cols)
        self.rows = int(rows)
        self.hex_size = float(hex_size)
        self.margin = int(config.CACHE_MARGIN_PX)

        self._cache = None          # 外扩后的静态层 Surface
        self._key = None            # 建缓存时的相机状态
        self._blit_pos = (0, 0)     # 缓存贴到屏幕的位置

    # ------------------------------------------------------------
    # 对外
    # ------------------------------------------------------------
    def draw(self, surface, camera):
        """把静态层画到 surface 上（能复用缓存就只 blit）。"""
        if not self._can_reuse(camera):
            self._rebuild(camera)
        surface.blit(self._cache, self._blit_pos)

    def invalidate(self):
        """作废缓存（地图 / 配色变更后调用）。"""
        self._cache = None
        self._key = None

    # ------------------------------------------------------------
    # 缓存命中判断
    # ------------------------------------------------------------
    def _can_reuse(self, camera):
        """相机是否仍落在缓存覆盖范围内（缩放与视口尺寸必须一致）。"""
        if self._cache is None:
            return False
        zoom, cx, cy, vw, vh = self._key
        if zoom != camera.zoom or vw != camera.viewport_w or vh != camera.viewport_h:
            return False

        ox, oy = self._offset(camera)
        # 缓存覆盖屏幕 x ∈ [ox, ox+vw+2M)；要求 [0, vw) 落在其中
        if not (-2 * self.margin <= ox <= 0 and -2 * self.margin <= oy <= 0):
            return False
        # 非整数位移会让 blit 糊边 → 重建
        if abs(ox - round(ox)) > 1e-6 or abs(oy - round(oy)) > 1e-6:
            return False

        self._blit_pos = (int(round(ox)), int(round(oy)))
        return True

    def _offset(self, camera):
        """缓存原点相对当前视口左上角的屏幕偏移（浮点）。"""
        zoom, cx, cy, _vw, _vh = self._key
        return (-self.margin + (cx - camera.cx) * zoom,
                -self.margin + (cy - camera.cy) * zoom)

    # ------------------------------------------------------------
    # 重建
    # ------------------------------------------------------------
    def _rebuild(self, camera):
        w = max(1, camera.viewport_w) + 2 * self.margin
        h = max(1, camera.viewport_h) + 2 * self.margin
        layer = pygame.Surface((w, h))
        layer.fill(config.COLOR_VIEWPORT_MARGIN)

        col_lo, col_hi, row_lo, row_hi = self._visible_range(camera)
        cells = (col_hi - col_lo + 1) * (row_hi - row_lo + 1)

        if cells > config.SOLID_FILL_CELL_LIMIT:
            self._draw_coalesced(layer, camera, cells)
        else:
            self._draw_cells(layer, camera, col_lo, col_hi, row_lo, row_hi)

        self._cache = layer
        self._key = (camera.zoom, camera.cx, camera.cy,
                     camera.viewport_w, camera.viewport_h)
        self._blit_pos = (-self.margin, -self.margin)

    def _draw_cells(self, layer, camera, col_lo, col_hi, row_lo, row_hi):
        """逐格画六边形（填充 + 1px 描边）。"""
        size = self.hex_size
        to_layer = self._to_layer(camera)

        for col in range(col_lo, col_hi + 1):
            for row in range(row_lo, row_hi + 1):
                q, r = hexgrid.offset_to_axial(col, row)
                wx, wy = hexgrid.axial_to_world(q, r, size)
                pts = [to_layer(px, py)
                       for px, py in hexgrid.hex_corners(wx, wy, size)]
                pygame.draw.polygon(layer, config.COLOR_HEX_FILL, pts)
                pygame.draw.polygon(layer, config.COLOR_HEX_LINE, pts, 1)

        logger.debug(
            "静态层重建（逐格）：cols %s–%s rows %s–%s，%s 格，zoom=%.4f",
            col_lo, col_hi, row_lo, row_hi,
            (col_hi - col_lo + 1) * (row_hi - row_lo + 1), camera.zoom,
        )

    def _draw_coalesced(self, layer, camera, cells):
        """低缩放合并绘制：整块填充 + 地图外框（O(1) 次绘制调用）。"""
        world_w, world_h = hexgrid.world_bounds(
            self.cols, self.rows, self.hex_size)
        x0 = -self.hex_size
        y0 = -self.hex_size * _SQRT3 / 2.0

        to_layer = self._to_layer(camera)
        sx0, sy0 = to_layer(x0, y0)
        sx1, sy1 = to_layer(x0 + world_w, y0 + world_h)
        rect = pygame.Rect(int(round(sx0)), int(round(sy0)),
                           max(1, int(round(sx1 - sx0))),
                           max(1, int(round(sy1 - sy0))))

        pygame.draw.rect(layer, config.COLOR_HEX_FILL, rect)
        pygame.draw.rect(layer, config.COLOR_HEX_LINE, rect, 1)

        logger.debug(
            "静态层重建（合并）：视口内 %s 格 > %s，降级为整块填充，zoom=%.4f",
            cells, config.SOLID_FILL_CELL_LIMIT, camera.zoom,
        )

    # ------------------------------------------------------------
    # 坐标 / 裁剪
    # ------------------------------------------------------------
    def _to_layer(self, camera):
        """世界坐标 → 缓存 Surface 像素（缓存原点 = 屏幕 (-margin, -margin)）。"""
        margin = self.margin

        def convert(x, y):
            sx, sy = camera.world_to_screen(x, y)
            return sx + margin, sy + margin

        return convert

    def _visible_range(self, camera):
        """视口（含外扩）覆盖的 (col, row) 区间，已夹到地图范围内。"""
        margin = self.margin
        x0, y0 = camera.screen_to_world(-margin, -margin)
        x1, y1 = camera.screen_to_world(
            camera.viewport_w + margin, camera.viewport_h + margin)
        size = self.hex_size

        col_lo = int(math.floor(x0 / (1.5 * size))) - 1
        col_hi = int(math.ceil(x1 / (1.5 * size))) + 1
        col_lo = max(0, min(self.cols - 1, col_lo))
        col_hi = max(0, min(self.cols - 1, col_hi))

        # 奇数列的格中心比偶数列低半格，故上下各留 1 行余量
        row_lo = int(math.floor(y0 / (_SQRT3 * size))) - 1
        row_hi = int(math.ceil(y1 / (_SQRT3 * size))) + 1
        row_lo = max(0, min(self.rows - 1, row_lo))
        row_hi = max(0, min(self.rows - 1, row_hi))

        return col_lo, col_hi, row_lo, row_hi

```

### battle/core/unit.py

```python
# -*- coding: utf-8 -*-
"""部队数据模型（纯逻辑，**不** import pygame）。

一个部队 = 一个棋子。JSON 只存
`id` / `side` / `type` / `col` / `row` / `troops` / `morale` / `stamina` /
`facing` / `general_id`；兵力上限与能力值一律**查兵种表**，不在单位上硬编码。
"""

from battle.core import hexgrid
from battle.core import unit_types


class Unit:
    """棋子。构造后字段可读；派生值走 property。"""

    def __init__(self, uid, side, type_key, q, r,
                 troops, morale=100.0, stamina=100.0,
                 facing=0, general_id=None):
        self.id = uid
        self.side = side
        self.type = type_key
        self.q = q
        self.r = r
        self.troops = troops
        self.morale = morale
        self.stamina = stamina
        self.facing = facing
        self.general_id = general_id

        # 运行时字段：本步恒定
        self.alive = True
        self.death_reason = None
        self.command = None

    # ============================================================
    # 只读派生值（不落盘，一律查兵种表）
    # ============================================================
    @property
    def type_def(self):
        """兵种定义 dict；未知兵种 → None。"""
        return unit_types.get(self.type)

    @property
    def name(self):
        """兵种显示名（如「具装甲骑」）；未知 → 空串。"""
        t = self.type_def
        return t["name"] if t else ""

    @property
    def category(self):
        """兵种类别（骑 / 步 / 弓）；未知 → None。"""
        return unit_types.category_of(self.type)

    @property
    def troops_max(self):
        return self._from_type("troops_max", 0)

    @property
    def move_points(self):
        return self._from_type("move_points", 0)

    @property
    def attack(self):
        """近程攻击力（远程另取 attack_ranged，本步不消费）。"""
        return self._from_type("attack_melee", 0)

    @property
    def defense(self):
        return self._from_type("defense", 0)

    @property
    def attack_range(self):
        return self._from_type("attack_range", 1)

    @property
    def attack_cooldown(self):
        return self._from_type("attack_cooldown", 0)

    def _from_type(self, field, default):
        t = self.type_def
        return t[field] if t else default

    # ============================================================
    # 坐标
    # ============================================================
    def offset(self):
        """存储用的 odd-q 偏移坐标 (col, row)。"""
        return hexgrid.axial_to_offset(self.q, self.r)

    # ============================================================
    # 构造
    # ============================================================
    @classmethod
    def from_dict(cls, d, side):
        """读 JSON 一条记录构造 Unit。

        `side` 参数**优先于** `d["side"]`（防脏数据）。
        前置条件：`d` 已通过校验（id / type / col / row 齐全，数值已钳制）——
        校验与丢弃在 `core/battle_state.py` 里做。
        """
        col = int(d["col"])
        row = int(d["row"])
        q, r = hexgrid.offset_to_axial(col, row)
        return cls(
            uid=str(d["id"]),
            side=side,
            type_key=str(d["type"]),
            q=q, r=r,
            troops=int(d["troops"]),
            morale=float(d.get("morale", 100.0)),
            stamina=float(d.get("stamina", 100.0)),
            facing=int(d.get("facing", 0)),
            general_id=d.get("general_id"),
        )

```

### battle/core/unit_types.py

```python
# -*- coding: utf-8 -*-
"""兵种定义的查询层（纯逻辑，**不** import pygame）。

定义本体是纯数据，在 `battle/balance.py` 的 `UNIT_TYPES` / `COUNTER_MATRIX`；
本模块只做查询与取值，不重复定义、不改写表。
"""

import logging
from typing import Optional

from battle import balance

logger = logging.getLogger("battle.core.unit_types")


def get(key) -> Optional[dict]:
    """兵种 key → 定义 dict；未知 / 空 → None。"""
    if not key:
        return None
    return balance.UNIT_TYPES.get(key)


def exists(key) -> bool:
    """该兵种 key 是否在表内。"""
    return get(key) is not None


def category_of(key) -> Optional[str]:
    """兵种 key → 类别（骑 / 步 / 弓）；未知 → None。"""
    t = get(key)
    return t["category"] if t else None


def counter_multiplier(attacker_category, defender_category) -> float:
    """克制倍率：COUNTER_MATRIX[攻方类别][守方类别]；任一未知 → 1.0。"""
    row = balance.COUNTER_MATRIX.get(attacker_category)
    if not row:
        return 1.0
    return row.get(defender_category, 1.0)

```

### battle/core/battle_state.py

```python
# -*- coding: utf-8 -*-
"""战斗状态容器（纯逻辑，**不** import pygame）。

持有全部部队，并提供：
- 按 id / 阵营 / 轴向坐标查询
- 视口轴向矩形内的单位迭代（供部队层裁剪，不遍历全表）
- 从部队 JSON 载入并校验（见 `battle/docs/步骤02需求.md` §4）
"""

import json
import logging
from pathlib import Path

from battle.core import unit_types
from battle.core.unit import Unit

logger = logging.getLogger("battle.core.battle_state")


class BattleState:
    """units 容器 + 两套索引（按坐标 / 按列）。"""

    def __init__(self, cols=0, rows=0):
        self.cols = int(cols)
        self.rows = int(rows)

        self.units = {}        # id → Unit
        self._by_pos = {}      # (q, r) → Unit
        self._by_col = {}      # q → list[Unit]（插入序；矩形筛选靠 r 比较）

    # ============================================================
    # 查询
    # ============================================================
    def unit(self, uid):
        """按 id 取单位；不存在 → None。"""
        return self.units.get(uid)

    def units_of(self, side):
        """某一方的全部单位（按 id 升序）。"""
        return sorted((u for u in self.units.values() if u.side == side),
                      key=lambda u: u.id)

    def unit_at(self, q, r):
        """按**轴向坐标**取单位；该格为空 → None。"""
        return self._by_pos.get((q, r))

    def all_units(self):
        """全部单位（按 id 升序）。"""
        return sorted(self.units.values(), key=lambda u: u.id)

    def units_in_axial_rect(self, q_lo, q_hi, r_lo, r_hi):
        """轴向矩形内的单位。

        只遍历**命中矩形覆盖的列**及其列内单位，不遍历全表 —— 视口裁剪专用。
        """
        out = []
        for q in range(q_lo, q_hi + 1):
            for u in self._by_col.get(q, ()):
                if r_lo <= u.r <= r_hi:
                    out.append(u)
        return out

    # ============================================================
    # 载入
    # ============================================================
    def from_json(self, path, side):
        """读一个阵营的部队 JSON 并入本状态。

        两侧各调一次（同方 / 跨方的坐标重复都在这里拦）。
        返回成功并入的单位数；文件缺失 / 损坏 → 记 WARNING 并返回 0，不抛。
        """
        path = Path(path)
        name = path.name

        if not path.exists():
            logger.warning("部队数据文件不存在：%s（该方按 0 支部队处理）", path)
            return 0

        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            logger.warning("部队数据文件无法解析：%s（%s）", path, exc)
            return 0

        if not isinstance(raw, dict):
            logger.warning("部队数据顶层不是对象：%s", path)
            return 0

        entries = raw.get("units")
        if not isinstance(entries, list):
            logger.warning("部队数据缺少 units 数组：%s", path)
            return 0

        added = 0
        for index, entry in enumerate(entries):
            unit = self._parse_entry(entry, side, name, index)
            if unit is not None and self._add(unit, name):
                added += 1

        logger.info("部队数据载入：%s（side=%s，%s/%s 支）",
                    name, side, added, len(entries))
        return added

    # ============================================================
    # 内部：逐条校验
    # ============================================================
    def _parse_entry(self, entry, side, name, index):
        """校验一条 JSON 记录；不合法 → 记 WARNING 并返回 None。"""
        if not isinstance(entry, dict):
            logger.warning("%s 第 %s 条不是对象，丢弃", name, index)
            return None

        for key in ("id", "type", "col", "row"):
            if entry.get(key) is None:
                logger.warning("%s 第 %s 条缺字段 %s，丢弃（id=%s）",
                               name, index, key, entry.get("id"))
                return None

        type_key = str(entry["type"])
        if not unit_types.exists(type_key):
            logger.warning("%s 的兵种不在兵种表：%s（id=%s），丢弃",
                           name, type_key, entry.get("id"))
            return None

        coords = self._parse_coords(entry)
        if coords is None:
            logger.warning("%s 的坐标不是整数：col=%r row=%r（id=%s），丢弃",
                           name, entry.get("col"), entry.get("row"),
                           entry.get("id"))
            return None
        col, row = coords
        if not (0 <= col < self.cols and 0 <= row < self.rows):
            logger.warning("%s 的坐标越界：(col=%s, row=%s) 不在 %s×%s 内（id=%s），丢弃",
                           name, col, row, self.cols, self.rows, entry.get("id"))
            return None

        troops = self._clamp_troops(entry, type_key, name)
        if troops is None:
            return None

        morale, stamina = self._clamp_bars(entry)
        facing = self._mod_facing(entry)

        data = {
            "id": entry["id"], "type": type_key, "col": col, "row": row,
            "troops": troops, "morale": morale, "stamina": stamina,
            "facing": facing, "general_id": entry.get("general_id"),
        }
        return Unit.from_dict(data, side)

    def _parse_coords(self, entry):
        try:
            return int(entry["col"]), int(entry["row"])
        except (TypeError, ValueError):
            return None

    def _clamp_troops(self, entry, type_key, name):
        """兵力：缺 → 兵种表上限；越界 → 钳制 + WARNING；非数字 → 丢弃。"""
        t = unit_types.get(type_key)
        cap = t["troops_max"]
        raw = entry.get("troops")
        if raw is None:
            return cap
        try:
            value = int(raw)
        except (TypeError, ValueError):
            logger.warning("%s 的兵力不是整数：%r（id=%s），丢弃",
                           name, raw, entry.get("id"))
            return None
        if value < 0:
            logger.warning("%s 的兵力为负：%s（id=%s），钳制到 0",
                           name, value, entry.get("id"))
            return 0
        if value > cap:
            logger.warning("%s 的兵力超上限：%s > %s（id=%s），钳制到上限",
                           name, value, cap, entry.get("id"))
            return cap
        return value

    def _clamp_bars(self, entry):
        """士气 / 体力：缺省 100.0，钳制到 1–100。"""
        out = []
        for key in ("morale", "stamina"):
            try:
                value = float(entry.get(key, 100.0))
            except (TypeError, ValueError):
                value = 100.0
            out.append(max(1.0, min(100.0, value)))
        return out[0], out[1]

    def _mod_facing(self, entry):
        try:
            return int(entry.get("facing", 0)) % 6
        except (TypeError, ValueError):
            return 0

    # ============================================================
    # 内部：入库（(q,r) 唯一）
    # ============================================================
    def _add(self, unit, name):
        """加入索引；该格已被占（同方或跨方）→ 后到者丢弃 + WARNING。"""
        key = (unit.q, unit.r)
        if key in self._by_pos:
            other = self._by_pos[key]
            logger.warning("%s 的 (col=%s, row=%s) 已被 %s 占用（%s），丢弃 %s",
                           name, *unit.offset(), other.id, other.side, unit.id)
            return False

        self.units[unit.id] = unit
        self._by_pos[key] = unit
        self._by_col.setdefault(unit.q, []).append(unit)
        return True

```

### battle/core/hexgrid.py

```python
# -*- coding: utf-8 -*-
"""六宫格几何与坐标变换（平顶 flat-top）。

纯函数，**不** import pygame。

坐标口径（与整体需求 §5 一致）：
- 存储 / JSON：odd-q 偏移坐标 `(col, row)`
- 内部计算：轴向坐标 `(q, r)`
- 渲染：世界像素坐标 `(x, y)`

`hex_size`（外接圆半径）一律由调用方注入，不在本模块写死。
其余模块**不得**自行实现坐标公式。
"""

import math

# 轴向邻居方向（6 个）
_DIRECTIONS = (
    (1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1),
)

_SQRT3 = math.sqrt(3.0)


# ============================================================
# 坐标变换
# ============================================================
def offset_to_axial(col, row):
    """odd-q 偏移 → 轴向。"""
    q = col
    r = row - (col - (col & 1)) // 2
    return q, r


def axial_to_offset(q, r):
    """轴向 → odd-q 偏移。"""
    col = q
    row = r + (q - (q & 1)) // 2
    return col, row


def axial_to_world(q, r, hex_size):
    """轴向 → 世界像素（格中心）。"""
    x = hex_size * 1.5 * q
    y = hex_size * _SQRT3 * (r + q / 2.0)
    return x, y


def world_to_axial(x, y, hex_size):
    """世界像素 → 轴向（鼠标拾取用），已做最近格取整。"""
    qf = (2.0 / 3.0) * x / hex_size
    rf = (-1.0 / 3.0 * x + _SQRT3 / 3.0 * y) / hex_size
    return _axial_round(qf, rf)


def _axial_round(qf, rf):
    """浮点轴向 → 最近整数轴向（立方体取整）。"""
    x = qf
    z = rf
    y = -x - z
    rx, ry, rz = round(x), round(y), round(z)
    dx, dy, dz = abs(rx - x), abs(ry - y), abs(rz - z)
    if dx > dy and dx > dz:
        rx = -ry - rz
    elif dy > dz:
        ry = -rx - rz
    else:
        rz = -rx - ry
    return int(rx), int(rz)


# ============================================================
# 距离 / 邻域
# ============================================================
def distance(a, b):
    """两个轴向坐标的格距。"""
    dq = a[0] - b[0]
    dr = a[1] - b[1]
    return (abs(dq) + abs(dr) + abs(dq + dr)) // 2


def neighbors(q, r):
    """6 个邻居的轴向坐标列表。"""
    return [(q + dq, r + dr) for dq, dr in _DIRECTIONS]


def ring(q, r, n):
    """半径 n 的环（含 n = 0 → 自身）。"""
    if n <= 0:
        return [(q, r)]
    out = []
    # 从「左下」方向的邻居起步，绕一圈
    cur_q = q + _DIRECTIONS[4][0] * n
    cur_r = r + _DIRECTIONS[4][1] * n
    for dq, dr in _DIRECTIONS:
        for _ in range(n):
            out.append((cur_q, cur_r))
            cur_q += dq
            cur_r += dr
    return out


# ============================================================
# 地图范围与顶点（供相机 / 渲染层复用）
# ============================================================
def world_bounds(cols, rows, hex_size):
    """整张地图的世界包围盒尺寸 (width, height)。"""
    width = hex_size * 1.5 * (cols - 1) + hex_size * 2.0
    height = hex_size * _SQRT3 * rows
    return width, height


def hex_corners(cx, cy, hex_size):
    """平顶六边形的 6 个顶点（世界坐标），从右侧顶点起逆时针。"""
    return [
        (cx + hex_size * math.cos(math.radians(60 * i)),
         cy + hex_size * math.sin(math.radians(60 * i)))
        for i in range(6)
    ]

```

### battle/core/map_data.py

```python
# -*- coding: utf-8 -*-
"""地图 JSON 加载。

纯逻辑，**不** import pygame。

地图文件不存在 / JSON 损坏 / 字段类型非法 → 抛 `MapDataError`，
由 `app.py` 捕获后 ERROR 入日志 + 弹窗 + 退出。
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger("battle.core.map_data")


class MapDataError(Exception):
    """地图文件缺失 / 无法解析 / 字段类型非法。"""


@dataclass
class MapData:
    """地图数据容器（字段 = 地图 JSON 的 8 个顶层字段）。"""

    version: int = 1
    id: str = "default"
    name: str = "默认地图"
    cols: int = 400
    rows: int = 300
    hex_size: int = 28
    orientation: str = "flat"
    tiles: list = field(default_factory=list)


def load_map(path) -> MapData:
    """读取地图 JSON 并返回 MapData。失败抛 MapDataError。"""
    p = Path(path)
    if not p.exists():
        raise MapDataError(f"地图文件不存在：{p}")

    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MapDataError(f"地图文件无法解析：{p}（{exc}）") from exc

    if not isinstance(raw, dict):
        raise MapDataError(f"地图文件顶层不是对象：{p}")

    data = MapData(
        version=_as_int(raw, "version", 1, p),
        id=_as_str(raw, "id", "default"),
        name=_as_str(raw, "name", "默认地图"),
        cols=_as_int(raw, "cols", 400, p),
        rows=_as_int(raw, "rows", 300, p),
        hex_size=_as_int(raw, "hex_size", 28, p),
        orientation=_as_str(raw, "orientation", "flat"),
        tiles=_as_tiles(raw, p),
    )

    if data.cols < 1 or data.rows < 1 or data.hex_size < 1:
        raise MapDataError(
            f"地图尺寸非法：cols={data.cols} rows={data.rows} "
            f"hex_size={data.hex_size}（{p}）"
        )

    logger.info(
        "地图加载完成：%s（%s × %s 格，hex_size=%s，orientation=%s，tiles=%s）",
        data.name, data.cols, data.rows, data.hex_size,
        data.orientation, len(data.tiles),
    )
    return data


def _as_int(raw, key, default, path):
    """取整数字段：缺失 → default；非数字 → 尝试 int()，仍失败 → 报错。"""
    if key not in raw or raw[key] is None:
        return default
    value = raw[key]
    if isinstance(value, bool):
        raise MapDataError(f"地图字段 {key} 类型非法：{value!r}（{path}）")
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise MapDataError(
            f"地图字段 {key} 无法转为整数：{value!r}（{path}）"
        ) from exc


def _as_str(raw, key, default):
    """取字符串字段：缺失 / 空 → default。"""
    value = raw.get(key)
    return value if isinstance(value, str) and value else default


def _as_tiles(raw, path):
    """取 tiles：缺失 = 全同质（空表）；存在但非 list → 报错。"""
    if "tiles" not in raw or raw["tiles"] is None:
        logger.warning("地图缺少 tiles 字段，按全同质处理：%s", path)
        return []
    tiles = raw["tiles"]
    if not isinstance(tiles, list):
        raise MapDataError(f"地图字段 tiles 类型非法：{type(tiles).__name__}（{path}）")
    return tiles

```

### battle/docs/步骤02需求.md

```markdown
代码包已收到，信息够用。进入阶段 F。

---

# 步骤02 需求文档 · 部队数据模型 + 兵棋符号 + 面板组 + 控制台

> 落点：`battle/docs/步骤02需求.md`
> 主归属：战斗模块。
> 上游依据：`battle/docs/整体需求.md` §4.3 / §5 / §7 / §8 / §12 / §13 / §18。

---

## 0. 前置说明

下游 AI 开工前**必须**先读：

| 文档 | 章节 | 用途 |
|---|---|---|
| `battle/docs/整体需求.md` | §3、§4.3、§5、§7、§8、§9.2、§12、§13、§21 | 分层约定 / 性能 / 坐标 / 部队模型 / 兵种表 / 渲染规格 / 约束 |
| `battle/docs/模块说明.md` | §2、§3、§5、§7、§8 | 目录结构 / 分层硬约束 / 坐标口径 / 配置分工 / 术语表 |
| `battle/docs/步骤01需求.md` | §3.3、§3.6、§3.9、§3.10、§3.11 | 已有 `config` / `map_data` / `hex_renderer` / `app` / 交互的现状与接口 |
| `README.md`（主游戏） | §8.3 第 45 条 | 日志 %s 惰性格式化 |

术语一律以两份文档为准；**不自创**名词。`Unit` / `side` / `type` / `category` / `tick` / `LOD` / `symbol` 等的含义严格沿用 §8 术语表。

---

## 1. 背景问题

| 现状 | 问题 |
|---|---|
| 步骤01 只渲染空地图，无任何棋子 | 无法验证「地图 + 棋子」的整体观感，也无法进入后续 tick / 移动 / 攻击 |
| `balance.py` 只有占位 `{}` | 兵种表未落地，后续步骤无据可依 |
| `data/` 目录为空 | 没有双方部队数据，无法验证加载链路 |
| 无 `core/unit.py` / `core/battle_state.py` | 无数据模型承载部队 |
| 无 `render/symbol.py` | 兵棋符号（北约 APP-6 简化版）未实现 |
| 无侧边面板组 / 底部控制台 | 步骤03 的「暂停 / 继续 / 速度 / 下令」没有落点 |
| 步骤01 的空窗口只有地图，无从「选取部队」 | 后续的「单选 / 框选 / 命令」没有交互基础 |

---

## 2. 需求目标

1. **部队数据模型落地**：`core/unit.py` + `core/unit_types.py` + `core/battle_state.py`，纯逻辑无 pygame。
2. **兵种表落地**：`balance.py` 填充三类十种兵种定义 + 3×3 克制矩阵。
3. **双方部队数据**：`data/side_red.json` / `data/side_blue.json`，各 12 支，显式坐标。
4. **兵棋符号渲染**：按本文件 §3.5 的**新符号规则**（覆盖整体需求 §12.3 的旧符号），含阵营框色、兵种类别外形、兵种小字、兵力数字、士气·体力小条。
5. **三级 LOD**：远 / 中 / 近（阈值走 `config.py`）。
6. **右侧面板组 + 底部控制台**：浮于地图之上、局部尺寸、做美化。
7. **部队选取**：单击 / 框选（详见 §3.8），选中高亮 + 面板 + 控制台三处联动。
8. **范围可控**：不含 tick 推进、命令系统、移动、攻击、AI、胜负、地形。

---

## 3. 规则细节

### 3.1 新增文件与职责

    battle/
    ├── core/
    │   ├── unit.py              ★ Unit 数据模型（纯逻辑）
    │   ├── unit_types.py        ★ 兵种定义加载 / 查询（纯逻辑）
    │   └── battle_state.py      ★ 战斗状态容器（纯逻辑）
    ├── render/
    │   ├── symbol.py            ★ 兵棋符号绘制（纯几何）
    │   ├── unit_layer.py        ★ 部队绘制层（视口裁剪 + LOD + 命中测试）
    │   ├── panel.py             ★ 右侧面板组
    │   ├── console.py           ★ 底部控制台
    │   └── widgets.py           ★ UI 通用小部件（圆角面板底板 / 按钮 / 文字）
    └── data/
        ├── side_red.json        ★ 红方部队数据
        └── side_blue.json       ★ 蓝方部队数据

    battle/balance.py            ☆ 填充兵种表 + 克制矩阵
    battle/config.py             ☆ 追加新常量（见 §3.2）
    battle/app.py                ☆ 装配战斗状态 / 部队层 / 面板 / 控制台

### 3.2 `config.py` 追加常量（建议初值）

| 常量 | 建议初值 | 说明 |
|---|---|---|
| `PLAYER_SIDE` | `"red"` | 玩家方；框选 / 选中只对玩家方生效 |
| `SIDE_COLOR` | `{"red": (196, 60, 60), "blue": (60, 96, 196)}` | 阵营框色 |
| `SYMBOL_LINE_WIDTH` | 2 | 符号描边线宽（屏幕像素） |
| `SYMBOL_FILL_ALPHA` | 220 | 实心区填充 alpha（0–255） |
| `SYMBOL_FONT_SIZE_MIN` / `_MAX` | 11 / 16 | 兵种小字字号（按 zoom 在区间内插值） |
| `SYMBOL_TROOP_FONT_MIN` / `_MAX` | 10 / 14 | 兵力数字字号（同上） |
| `LOD_FAR_MAX_PX` | 12 | 屏幕上的格边长 < 此值 → **远** LOD |
| `LOD_NEAR_MIN_PX` | 28 | 屏幕上的格边长 ≥ 此值 → **近** LOD；介于两者 = **中** |
| `LOD_FAR_COLOR` | 同 `SIDE_COLOR` | 远 LOD 小色块颜色 |
| `LOD_FAR_SIZE_PX` | 6 | 远 LOD 小色块边长（屏幕像素） |
| `SELECT_HIGHLIGHT_COLOR` | (255, 220, 60) | 选中高亮描边色 |
| `SELECT_HIGHLIGHT_WIDTH` | 3 | 选中描边线宽 |
| `SELECT_BOX_COLOR` | (255, 220, 60, 80) | 框选虚线框填充（半透明） |
| `PANEL_WIDTH` | 300 | 右侧面板组宽度 |
| `PANEL_MARGIN` | 20 | 面板距屏幕边缘的间距 |
| `PANEL_BG_COLOR` | (28, 32, 40, 220) | 面板底板色（RGBA 半透明） |
| `PANEL_BORDER_COLOR` | (90, 100, 120) | 面板描边色 |
| `PANEL_CORNER_RADIUS` | 8 | 圆角半径 |
| `PANEL_TAB_HEIGHT` | 36 | Tab 条高度 |
| `PANEL_TAB_TITLES` | `("部队", "面板2", "面板3", "面板4")` | Tab 标题（后 3 个本轮留空） |
| `CONSOLE_HEIGHT` | 120 | 控制台高度 |
| `CONSOLE_MARGIN` | 20 | 控制台距屏幕边缘间距 |
| `CONSOLE_BG_COLOR` | 同 `PANEL_BG_COLOR` | |
| `UI_FONT_PATH` | 复用 `FONT_PATH` | 面板 / 控制台字体 |
| `UNIT_DATA_PATHS` | `{"red": "…/side_red.json", "blue": "…/side_blue.json"}` | 双方数据路径 |

所有路径以 `battle/` 为基准反推，**不用 cwd**。

### 3.3 部队数据模型（`core/unit.py`）

**字段表**（对齐整体需求 §7）：

| 字段 | 类型 | 来源 | 说明 |
|---|---|---|---|
| `id` | str | JSON 必填 | 唯一标识 |
| `side` | str | JSON 必填 | `red` / `blue` |
| `type` | str | JSON 必填 | 兵种 key，见 §3.4 |
| `q`, `r` | int | JSON 的 `col`, `row` 经 `hexgrid.offset_to_axial` 转 | 轴向坐标 |
| `troops` | int | JSON 可选（缺则查兵种表 `troops_max`） | 当前兵力 |
| `morale` | float | JSON 可选（缺省 100.0） | 士气 1–100 |
| `stamina` | float | JSON 可选（缺省 100.0） | 体力 1–100 |
| `facing` | int | JSON 可选（缺省 0） | 朝向 0–5，**本步只存不消费** |
| `alive` | bool | 运行时 | 本步恒 True |
| `death_reason` | str \| None | 运行时 | 本步恒 None |
| `command` | Command \| None | 运行时 | 本步恒 None |
| `general_id` | str \| None | JSON 可选 | 将领 id，**本步只存不消费** |

**只读派生属性**（不落盘，查兵种表）：

| 属性 | 取值 |
|---|---|
| `troops_max` | 兵种表 `troops_max` |
| `move_points` | 兵种表 `move_points` |
| `attack` | 兵种表 `attack_melee`（远程时用 `attack_ranged`，本步不消费） |
| `defense` | 兵种表 `defense` |
| `attack_range` | 兵种表 `attack_range` |
| `attack_cooldown` | 兵种表 `attack_cooldown` |

**构造约定**：`Unit.from_dict(d, side)` 读 JSON 一条；`side` 参数优先于 `d["side"]`（防脏数据）。

### 3.4 兵种表（`balance.py`）

**三类十种**（key 用英文，name 用中文，`category` 用「骑 / 步 / 弓」）：

| key | name | category | 符号 |
|---|---|---|---|
| `cataphract` | 具装甲骑 | 骑 | 菱形 / 实心 |
| `heavy_cavalry` | 重骑 | 骑 | 菱形 / 上半填充 |
| `light_cavalry` | 轻骑 | 骑 | 菱形 / 空心 |
| `horse_archer` | 弓骑 | 骑 | 菱形 / 中间斜线 |
| `heavy_armor` | 重甲 | 步 | 横长方形 + X / 左·右·下实心 |
| `armored` | 甲士 | 步 | 横长方形 + X / 左·右实心 |
| `light_armor` | 甲兵 | 步 | 横长方形 + X / 下实心 |
| `levy` | 徒卒 | 步 | 横长方形 + X / 空心 |
| `crossbow` | 弩士 | 弓 | 正方形 / 左上三角实心 |
| `archer` | 步弓 | 弓 | 正方形 / 空心 |

**字段**（对齐整体需求 §8）+ 新增 2 个符号字段：

| 字段 | 类型 | 说明 |
|---|---|---|
| `key` / `name` | str | 内部标识 / 显示名 |
| `category` | str | 骑 / 步 / 弓 |
| `troops_max` | int | 兵力上限 |
| `move_points` | int | 每 tick 移动格数 |
| `attack_melee` | int | 近程攻击力 |
| `attack_ranged` | int \| None | 远程攻击力（无远程则 None） |
| `attack_range` | int | 1 = 仅近程；≥ 2 = 可远程 |
| `defense` | int | 基础防御力 |
| `stamina_cost_move` | float | 每格移动消耗体力 |
| `stamina_cost_attack` | float | 攻击消耗体力（每次攻击开始扣一次） |
| `stamina_recover` | float | 静止每 tick 恢复体力 |
| `morale_recover` | float | 静止每 tick 恢复士气 |
| `attack_cooldown` | int | 攻击冷却 tick |
| `morale_hit` | float | 被击中每 tick 士气损失 |
| `morale_kill` | float | 击杀目标士气恢复 |
| `morale_rout` | float | 目标溃散士气恢复 |
| **`symbol_shape`** | str | `"diamond"` / `"rect"` / `"square"` |
| **`symbol_fill`** | str | 见 §3.5 填充枚举 |

**建议初值表**（后续平衡可改此表，不改代码）：

| key | troops_max | move_points | attack_melee | attack_ranged | attack_range | defense | stamina_cost_move | stamina_cost_attack | stamina_recover | morale_recover | attack_cooldown | morale_hit | morale_kill | morale_rout |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| cataphract | 3000 | 2 | 90 | – | 1 | 85 | 3.0 | 8.0 | 1.5 | 1.0 | 12 | 1.5 | 8.0 | 5.0 |
| heavy_cavalry | 2800 | 3 | 80 | – | 1 | 70 | 2.5 | 7.0 | 1.5 | 1.0 | 10 | 1.5 | 8.0 | 5.0 |
| light_cavalry | 2200 | 4 | 60 | – | 1 | 50 | 2.0 | 6.0 | 2.0 | 1.2 | 8 | 1.2 | 8.0 | 5.0 |
| horse_archer | 1800 | 4 | 40 | 55 | 3 | 40 | 2.0 | 6.0 | 2.0 | 1.2 | 9 | 1.2 | 8.0 | 5.0 |
| heavy_armor | 3500 | 1 | 70 | – | 1 | 90 | 4.0 | 8.0 | 1.5 | 1.5 | 12 | 1.0 | 8.0 | 5.0 |
| armored | 3000 | 2 | 60 | – | 1 | 70 | 3.0 | 7.0 | 1.8 | 1.5 | 10 | 1.0 | 8.0 | 5.0 |
| light_armor | 2500 | 2 | 50 | – | 1 | 55 | 3.0 | 6.0 | 2.0 | 1.5 | 9 | 1.0 | 8.0 | 5.0 |
| levy | 2000 | 3 | 35 | – | 1 | 40 | 2.0 | 5.0 | 2.5 | 1.5 | 8 | 1.0 | 8.0 | 5.0 |
| crossbow | 1800 | 2 | 25 | 90 | 4 | 35 | 3.0 | 8.0 | 2.0 | 1.2 | 14 | 1.0 | 8.0 | 5.0 |
| archer | 1600 | 3 | 30 | 70 | 3 | 30 | 2.5 | 7.0 | 2.2 | 1.2 | 10 | 1.0 | 8.0 | 5.0 |

**克制矩阵**（3×3，行 = 攻方类别、列 = 守方类别，默认 1.0；本步只写表不消费）：

| 攻 \ 守 | 骑 | 步 | 弓 |
|---|---|---|---|
| **骑** | 1.0 | 0.9 | 1.3 |
| **步** | 1.3 | 1.0 | 0.9 |
| **弓** | 0.9 | 1.3 | 1.0 |

### 3.5 兵棋符号规则（★ 本文件覆盖整体需求 §12.3 的符号方案）

**共同约定**：

- 阵营区分：**框色**（红 / 蓝），见 `config.SIDE_COLOR`。
- 兵种类别区分：**外形**（菱形 / 横长方形 / 正方形）。
- 具体兵种区分：**填充模式**（见下表）+ **框上方兵种小字**。
- 所有线条 / 填充 / 小字均以屏幕像素绘制（随 zoom 等比缩放，符号不「跳级」）。
- 描边线宽固定 `config.SYMBOL_LINE_WIDTH`（不随 zoom 变，保证远观清晰）。

**外形尺寸**（以平顶六宫格的内接区域为界，超出格边即视为违规）：

| 外形 | 屏幕尺寸（边长 / 宽高） |
|---|---|
| 菱形 | 对角线水平 `1.4 * HEX_SIZE`，垂直 `1.4 * HEX_SIZE` |
| 横长方形 | 宽 `1.6 * HEX_SIZE`，高 `0.8 * HEX_SIZE`（宽 : 高 = 2 : 1） |
| 正方形 | 边长 `1.0 * HEX_SIZE` |

**填充模式表**（符号设计详见下方示意）：

| key | 外形 | 填充模式 | 示意 |
|---|---|---|---|
| `cataphract` | 菱形 | **solid**（整块实心） | ◆ |
| `heavy_cavalry` | 菱形 | **top_half**（沿水平中线切分，上半实心） | ◒ 上半 |
| `light_cavalry` | 菱形 | **hollow**（仅描边） | ◇ |
| `horse_archer` | 菱形 | **slash**（沿垂直中线画一条斜线，不留填充） | ◇ 加斜线 |
| `heavy_armor` | 横长方形 + X | **fill_three**（左 / 右 / 下三区实心；上区空） | 见下 |
| `armored` | 横长方形 + X | **fill_left_right**（左 / 右两区实心） | 见下 |
| `light_armor` | 横长方形 + X | **fill_bottom**（仅下区实心） | 见下 |
| `levy` | 横长方形 + X | **hollow**（仅描边 + X） | 见下 |
| `crossbow` | 正方形 | **upper_left_half**（沿右上—左下对角线切分，左上三角实心） | ◤ |
| `archer` | 正方形 | **hollow**（仅描边） | □ |

**步兵横长方形 + X 分区的几何定义**：

- 横长方形边框（宽 2 : 高 1）。
- 沿**两条对角线**画 X，将矩形分成 **4 个三角形区域**：**上 / 右 / 下 / 左**（以矩形边命名，而非以对角线命名）。
- 每一区域的「实心」= 用 `config.SIDE_COLOR` 填充该三角形；「空」= 用背景色留白。
- 具体映射：
  - 重甲：**上**（空）、**右**（实）、**下**（实）、**左**（实）
  - 甲士：**上**（空）、**右**（实）、**下**（空）、**左**（实）
  - 甲兵：**上**（空）、**右**（空）、**下**（实）、**左**（空）
  - 徒卒：四区全空（仅边框 + X 线）

**附加信息**（保留整体需求 §12.3 的全部）：

| 元素 | 位置 | 内容 | 何时显示 |
|---|---|---|---|
| 兵种小字 | 框**上方**居中 | 兵种 `name`（如「具装甲骑」） | 中 / 近 LOD |
| 兵力数字 | 框**下方**居中 | `troops`（千分位） | 近 LOD |
| 士气小条 | 框**左侧**竖条 | `morale / 100` 填充比例，0–100 映射到条高 | 中 / 近 LOD |
| 体力小条 | 框**右侧**竖条 | `stamina / 100` 填充比例，0–100 映射到条高 | 中 / 近 LOD |
| 冷却小圆点 | 框右上角 | 本步恒不显示（`cooldown_left == 0`） | 后续步骤 |

**配色**：

| 元素 | 颜色 |
|---|---|
| 框描边 | `SIDE_COLOR[side]` |
| 框内实心区填充 | `SIDE_COLOR[side]`，`alpha = SYMBOL_FILL_ALPHA` |
| 空心区 | 透明（露出地图底色） |
| 兵种小字 | `(230, 230, 230)` + 1px 黑描边（保证各种地图底色上都可读） |
| 兵力数字 | 同上 |
| 士气小条 | 底 `(60, 60, 60)`，填充 `(120, 200, 120)` |
| 体力小条 | 底 `(60, 60, 60)`，填充 `(200, 170, 90)` |
| 选中描边 | `config.SELECT_HIGHLIGHT_COLOR`，线宽 `SELECT_HIGHLIGHT_WIDTH`，画在符号最外层 |

### 3.6 部队数据 JSON

**顶层结构**（两个文件同构）：

```json
{
  "version": 1,
  "id": "side_red",
  "name": "红方",
  "side": "red",
  "units": [ ... ]
}
```

**units 元素**（字段对齐 §3.3）：

```json
{
  "id": "r01",
  "side": "red",
  "type": "cataphract",
  "col": 30,
  "row": 40,
  "troops": 3000,
  "morale": 90.0,
  "stamina": 100.0,
  "facing": 0,
  "general_id": null
}
```

**坐标口径**：

- JSON 里写 **odd-q 偏移坐标** `col` / `row`（与整体需求 §5 一致）。
- 加载后由 `hexgrid.offset_to_axial(col, row)` 转成内部轴向 `q` / `r`。
- 显式写死，**不程序化生成**（地图与数据解耦）。

**初始布局建议**（具体数值由实现侧填，仅约束语义）：

| 阵营 | 大致位置 | 说明 |
|---|---|---|
| `red` | 地图左侧（`col` 约 40–90） | 12 支，纵向散开，互相不重叠 |
| `blue` | 地图右侧（`col` 约 310–360） | 12 支，纵向散开，互相不重叠 |

- 每方 12 支：骑兵 4 + 步兵 4 + 弓兵 4，十种兵种尽量覆盖（具装甲骑各 1，其余按需）。
- 所有 `(col, row)` 必须落在 `cols × rows` 内。
- 同一方内部不得出现同 `(col, row)`。

### 3.7 战斗状态容器（`core/battle_state.py`）

| 项 | 说明 |
|---|---|
| 容器 | `units: dict[id -> Unit]` |
| 查询 | `unit(id)` / `units_of(side)` / `unit_at(col, row)`（按轴向坐标） / `all_units()` |
| 加载 | `BattleState.from_json(path, side)`：读 JSON → 校验 → 构造 Unit 表 |
| 校验 | 见 §4 |

不 import pygame。

### 3.8 部队层（`render/unit_layer.py`）

**职责**：把 `BattleState` 中的单位画到屏幕上。

| 项 | 决定 |
|---|---|
| 视口裁剪 | 只遍历**视口覆盖的轴向坐标**范围内的单位（不得遍历全表）；用 `camera.visible_world_rect()` 反算轴向矩形，再按坐标筛选 |
| LOD 分级 | 见 §3.9 |
| 层顺序 | 六宫格静态层**之上**、面板组 / 控制台**之下** |
| 命中测试 | 提供 `hit_test(screen_pos) -> Unit \| None`：反算屏幕点所在轴向 → 取该格单位 |
| 框选 | 提供 `box_select(screen_rect, side_filter) -> list[Unit]`：返回矩形内单位（只返回 `side_filter` 匹配的） |
| 选中集 | 由 `app.py` 持有，`unit_layer` 只负责按选中集画高亮 |
| 不写数据 | 只读 `BattleState`，不改任何 Unit 字段 |

### 3.9 三级 LOD

「屏幕上的格边长」= `camera.zoom * HEX_SIZE`（像素）。

| 级别 | 阈值 | 显示内容 |
|---|---|---|
| **远** | 格边长 < `LOD_FAR_MAX_PX`（12） | 小色块（边长 `LOD_FAR_SIZE_PX` = 6px，颜色 = `SIDE_COLOR[side]`），**不显示**外形 / 小字 / 数值 / 小条 |
| **中** | `LOD_FAR_MAX_PX` ≤ 格边长 < `LOD_NEAR_MIN_PX`（28） | 完整符号（外形 + 填充 + 描边）+ **兵种小字** + 士气 / 体力小条 |
| **近** | 格边长 ≥ `LOD_NEAR_MIN_PX` | 完整符号 + 兵种小字 + 士气 / 体力小条 + **兵力数字** |

- 远视角下，**选中**的单位仍画 `SELECT_HIGHLIGHT_COLOR` 描边（小色块外围加一圈，宽度 = `SELECT_HIGHLIGHT_WIDTH`）。
- 阈值全部走 `config.py`，运行时可调。

### 3.10 右侧面板组（`render/panel.py`）

**布局**：

| 项 | 值 |
|---|---|
| 位置 | 贴右侧，距上 / 右 / 下各 `PANEL_MARGIN` = 20px |
| 宽度 | `PANEL_WIDTH` = 300px |
| 高度 | `viewport_h - 2 * PANEL_MARGIN` |
| 层级 | 浮于地图之上（后画 = 覆盖） |

**结构**：

| 区块 | 高度 | 内容 |
|---|---|---|
| Tab 条 | `PANEL_TAB_HEIGHT` = 36px | 4 个 Tab 标题（`PANEL_TAB_TITLES`），当前选中高亮 |
| 内容区 | 余下 | 当前 Tab 的内容 |

**4 个 Tab**：

| Tab | 本轮状态 |
|---|---|
| **部队** | **实装**：见下 |
| 面板2 / 面板3 / 面板4 | **留空**：内容区显示「（本步未实现）」灰色居中字 |

**「部队」Tab 内容**（列表）：

| 列 | 内容 |
|---|---|
| 阵营 | 红 / 蓝（用 `SIDE_COLOR` 小圆点 + 文字） |
| 兵种 | 兵种 `name` |
| 兵力 | `troops`（千分位） |
| 坐标 | `(col, row)`（偏移坐标，取整） |
| 选中 | 选中状态标记（● / ○） |

- 排序：按 `id` 升序。
- 点击某行 → **等效于单击地图上该单位**（加入 / 替换选中集，见 §3.8）。
- 滚动：单位数超出可视区时，鼠标滚轮滚动列表（**不影响地图 zoom**，鼠标在面板内时滚轮事件被面板吞掉）。
- 显示数量：本轮显示**全部**单位（24 支）。

### 3.11 底部控制台（`render/console.py`）

**布局**：

| 项 | 值 |
|---|---|
| 位置 | 贴底部，距左 / 下 / 右侧（右侧避开面板组）各 `CONSOLE_MARGIN` = 20px |
| 宽度 | `viewport_w - 2 * CONSOLE_MARGIN - PANEL_WIDTH - PANEL_MARGIN` |
| 高度 | `CONSOLE_HEIGHT` = 120px |
| 层级 | 浮于地图之上（后画 = 覆盖） |

**内部结构**（从左到右）：

| 区块 | 宽度 | 内容 |
|---|---|---|
| 进行 / 暂停按钮 | 90px | 一个按钮，显示「▶ 进行」/「⏸ 暂停」，**本轮点击仅切换图标与状态变量，不驱动模拟** |
| 选取展示区 | 剩余宽度的一半 | 显示当前选中部队（`id` + 兵种名 + 兵力），最多显示 N 个（超出显示「…」+ 计数） |
| 部队按钮区 | 剩余宽度的一半 | 4 个按钮：「移动」「攻击」「待命」「停止」，**本轮全部 `disabled`**（灰显，点击仅写 DEBUG 日志） |
| 其它按钮 | 120px | 「全选」「清空选择」 |

- 全部按钮统一走 `render/widgets.py` 的按钮部件（含 hover / disabled 三态）。
- 进行 / 暂停按钮的状态变量由 `app.py` 持有，本轮不消费。

### 3.12 交互（本步变更 + 新增）

| 操作 | 行为 |
|---|---|
| **左键单击部队** | 单选（清空旧选中，选中该单位）；点击空白 → 清空选中 |
| **左键拖拽（> 4px）** | **框选**：拉出矩形虚线框，松开时选中矩形内**玩家方**（`PLAYER_SIDE`）单位；Ctrl / Shift 按住时 → 追加到现有选中集 |
| **右键拖拽** | **平移视口**（步骤01 的左键拖拽平移改为右键拖拽） |
| **中键拖拽** | 平移视口（与右键等价，兼容有无中键的鼠标） |
| **滚轮** | 以鼠标为锚点缩放（不变） |
| **鼠标移动（无按键）** | 不改变选中集；仅记录 hover 单位（本步不显示 tooltip，留后续） |
| **窗口缩放** | 重算视口；面板 / 控制台按新尺寸重新布局 |
| **关闭窗口** | 正常退出（不变） |

- 框选虚线框颜色 `SELECT_BOX_COLOR`，线宽 1px，虚线步长 (6, 4)。
- 框选框仅在拖拽过程中绘制（松手即消失）。
- 面板 / 控制台 / Tab 条 / 按钮区域**不响应地图交互**（事件先给 UI 层，UI 层未消费再给地图）。

### 3.13 渲染顺序（`app.py` 主循环）

    1. screen.fill(COLOR_BG)
    2. hex_renderer.draw(screen, camera)        六宫格静态层
    3. unit_layer.draw(screen, camera)          部队层（含 LOD + 选中高亮 + 框选虚线框）
    4. panel.draw(screen, viewport_size)        右侧面板组
    5. console.draw(screen, viewport_size)      底部控制台
    6. pygame.display.flip()

### 3.14 `app.py` 装配变更

| 步骤 | 说明 |
|---|---|
| 启动 | 载地图 → 建相机 → 建 `BattleState`（载入两侧 JSON）→ 建 `unit_layer` / `panel` / `console` |
| 主循环 | 事件 → 分发给 UI 层（panel / console）→ 未消费的给地图交互 → 更新相机 → 渲染 |
| 状态 | `selected_units: set[id]` / `is_playing: bool` / `is_box_selecting: bool` / `box_rect` |
| 退出 | 不变 |

---

## 4. 边界与兼容

| 场景 | 处理 |
|---|---|
| 部队 JSON 文件缺失 | WARNING + 该方 0 支部队；不阻断启动 |
| 部队 JSON 解析失败 | WARNING（含文件名 + 异常）+ 该方 0 支部队；不阻断启动 |
| `units` 元素缺 `id` / `type` / `col` / `row` | 丢弃该单位 + WARNING（逐条） |
| `type` 不在兵种表 | 丢弃该单位 + WARNING；**不**用兜底符号（宁可缺失，避免误导） |
| `(col, row)` 越界（超出 `cols` / `rows`） | 丢弃该单位 + WARNING |
| 同 `(col, row)` 重复（同方或跨方） | **后到者**丢弃 + WARNING；先到者保留 |
| `troops` > `troops_max` | 钳制到 `troops_max` + WARNING |
| `troops` < 0 | 钳制到 0 + WARNING |
| `morale` / `stamina` 越界 | 钳制到 1–100 |
| `facing` 越界 | 取模 6 |
| 面板 / 控制台区域点击 | 不触发地图选中 / 平移 |
| 框选时选中的是敌方单位 | 不加入选中集（只选 `PLAYER_SIDE`） |
| 老步骤01 交互（左键拖拽平移） | **行为变更**（改为右键 / 中键平移）；在 CHANGELOG 中记录 |
| 地图 JSON `cols` / `rows` 改动 | 部队数据里的 `col` / `row` 若越界 → 按上文丢弃 + WARNING；不自动重排 |
| 面板 / 控制台与实际视口尺寸冲突（屏幕过小） | 面板宽度 / 控制台高度按比例缩到最小可读尺寸（≥ 屏宽的 40% / 屏高的 15%），保证 UI 不遮挡整屏 |

---

## 5. 不要做的事

| 项 | 说明 |
|---|---|
| tick 推进 | 只写按钮与状态变量，**不**驱动模拟 |
| 命令系统（Command 类 / 队列） | 不做；`Unit.command` 字段保留但恒 None |
| 移动 / 攻击 / 士气 / 体力规则 | 不做；这些字段只读不写 |
| AI（`ai/simple_ai.py`） | 不做 |
| 胜负判定 / 结算画面 / `battle_result.json` | 不做 |
| 地形 / 2.5D / 动画 | 不做 |
| 存档 / 热重载 | 不做 |
| `battle/api.py` 的实现 | 不做，保持空壳 |
| `battle/sim/` 下任何文件 | 不做，保持 `__init__.py` 空 |
| 给 `core/` / `sim/` / `api.py` 引入 pygame 或第三方库 | 禁止 |
| 面板列宽 / 排序状态持久化 | 不做 |
| 面板 tab 拖拽排序 | 不做 |
| hover tooltip | 不做（鼠标 move 仅记录 hover 单位，不显示） |
| 调试叠加层（`render/debug_overlay.py`） | 不做 |
| 部队图标贴图 / 预渲染缓存 | 不做；符号每帧几何重绘 |
| 引入 pygame 之外的第三方运行时依赖 | 不做；Pillow 记为**可选**（本步不消费，不写进 `requirements`） |
| 改 `hexgrid.py` 的坐标公式 | 不动 |
| 改 `map_data.py` 的地图格式 | 不动 |
| 改 `hex_renderer.py` 的静态层策略 | 不动 |
| 改 `shared/logging_setup.py` | 不动 |

---

## 6. 约束

| 约束 | 引用 |
|---|---|
| `core/` / `sim/` 不 import pygame | 模块说明 §3、整体需求 §3 |
| `render/` 只读数据 | 模块说明 §3、整体需求 §3 |
| `api.py` 不依赖 pygame | 模块说明 §3、整体需求 §16 |
| 坐标口径：JSON = 偏移 (col, row)，内部 = 轴向 (q, r)，渲染 = 世界像素 | 整体需求 §5 |
| 转换一律走 `hexgrid`，**不得**自行实现 | 模块说明 §5 |
| 禁止全图绘制 / 全图遍历 | 整体需求 §4.3 |
| 视口裁剪 | 整体需求 §4.3、§12.1 |
| 静态层与动态层分离 | 步骤01 已落地 |
| 配置集中：结构在 `config.py`，数值在 `balance.py` | 整体需求 §21 |
| tick 模型（毫秒 / 100ms 默认） | 整体需求 §6 |
| 数据层与渲染层分离 | 整体需求 §21 |
| 日志：`%s` 惰性格式化，禁 f-string | 主游戏 README §8.3 第 45 条 |
| logger 命名 `battle.xxx` | 模块说明 §6.3 |
| 日志级别 | 命中测试 / 每帧渲染路径**不**打日志 |

---

## 7. 验收清单

**部队数据模型**

- [ ] `core/unit.py` / `core/unit_types.py` / `core/battle_state.py` 存在，**均不** import pygame。
- [ ] `Unit` 具备 §3.3 的全部字段与只读派生属性。
- [ ] `balance.py` 的 `UNIT_TYPES` 含 10 条记录，字段齐全；`COUNTER_MATRIX` 为 3×3。
- [ ] `data/side_red.json` / `side_blue.json` 各含 12 支单位，坐标合法，无重复。

**部队渲染**

- [ ] 启动后地图左右两侧各出现 12 个棋子，均为对应阵营框色。
- [ ] 菱形 / 横长方形 / 正方形三种外形分别对应骑 / 步 / 弓，肉眼可辨。
- [ ] 十种兵种的填充模式与 §3.5 表一致（可逐种对照）。
- [ ] 兵种小字显示在框上方，兵力数字在框下方，士气 / 体力小条在框左右两侧。
- [ ] 缩放时 LOD 三级切换生效（远 = 小色块，中 = 符号，近 = 符号 + 数值）。
- [ ] 缩放 / 平移时棋子随地图同步移动，不出现漂移。

**选取**

- [ ] 左键单击己方棋子 → 该棋子高亮描边，控制台「选取展示区」与面板「部队」Tab 同步显示。
- [ ] 左键单击空白 / 敌方棋子 → 清空选中。
- [ ] 左键拖拽 → 拉出虚线框，松手后玩家方（red）范围内单位被选中。
- [ ] 右键拖拽 / 中键拖拽 → 平移视口（左键拖拽**不再**平移）。
- [ ] 滚轮缩放不变。

**面板 / 控制台**

- [ ] 右侧面板组与底部控制台浮于地图之上，不占地图布局空间。
- [ ] 面板 4 个 Tab：Tab 1「部队」显示列表；Tab 2–4 显示「（本步未实现）」。
- [ ] 面板列表点击某行 → 等效于单击地图上该单位。
- [ ] 控制台含进行/暂停按钮、选取展示区、4 个 disabled 的部队按钮、「全选」「清空选择」。
- [ ] 「全选」→ 选中全部玩家方单位；「清空选择」→ 清空选中集。
- [ ] 面板 / 控制台区域点击不触发地图平移 / 选中；鼠标在面板内滚轮**不**缩放地图。

**数据边界**

- [ ] 删除 `side_red.json` → 启动无红方单位，进程不崩，日志有 WARNING。
- [ ] 手动把某单位 `col` 改成 `10000` → 启动时该单位被丢弃 + WARNING。
- [ ] 手动把某单位 `type` 改成 `"unknown"` → 启动时该单位被丢弃 + WARNING。
- [ ] 手动让两单位同 `(col, row)` → 后到者被丢弃 + WARNING。

**分层与约束**

- [ ] `grep -r "import pygame" battle/core battle/sim battle/api.py` **无**输出。
- [ ] `battle/render/` 下无任何写 `BattleState` / `Unit` 字段的代码。
- [ ] 未引入 pygame 之外的第三方运行时依赖。

**文档**

- [ ] `battle/docs/步骤02需求.md` 存在（即本文档）。
- [ ] `battle/docs/CHANGELOG.md` 追加步骤02 条目（Added / Changed / Fixed）。

---

## 8. 完成后请提供什么

下游 AI 完成后，请报告：

1. **文件清单**：新建 / 修改的文件（相对路径），标出 `[新]` / `[改]`。
2. **兵种表定稿**：`balance.py` 里 `UNIT_TYPES` / `COUNTER_MATRIX` 的最终值（若与本文档建议值有出入，逐条说明原因）。
3. **符号实现说明**：每个兵种的绘制代码要点（外形 + 填充），确认与 §3.5 表一致。
4. **测试结果**：
   - `python -m battle` 一条命令，窗口内可见 24 个棋子（截图或描述）。
   - 缩放三次（近 / 中 / 远），确认 LOD 三级切换。
   - 单击 / 框选 / 右键平移 / 滚轮缩放各一条操作记录。
   - 删除 `side_red.json` 后的启动日志（应有 WARNING，无崩溃）。
5. **验收清单逐项确认**：勾选 / 未勾选 + 未勾选原因。
6. **未完成 / 偏离项**：与本文档不一致之处及理由。
7. **遗留问题**：已知限制 / 待步骤03 处理项。

---

（文档结束）
```

### battle/assets/maps/default.json

```json
{
  "version": 1,
  "id": "default",
  "name": "默认地图",
  "cols": 400,
  "rows": 300,
  "hex_size": 28,
  "orientation": "flat",
  "tiles": []
}

```

### battle/data/side_red.json

```json
// 截取：元字段 + 首 3 条
{
  "version": 1,
  "id": "side_red",
  "name": "红方",
  "side": "red",
  "units": [
    {
      "id": "r01",
      "side": "red",
      "type": "cataphract",
      "col": 184,
      "row": 143,
      "troops": 3000,
      "morale": 100.0,
      "stamina": 100.0,
      "facing": 0,
      "general_id": null
    },
    {
      "id": "r02",
      "side": "red",
      "type": "heavy_cavalry",
      "col": 184,
      "row": 147,
      "troops": 2800,
      "morale": 90.0,
      "stamina": 85.0,
      "facing": 0,
      "general_id": null
    },
    {
      "id": "r03",
      "side": "red",
      "type": "light_cavalry",
      "col": 184,
      "row": 151,
      "troops": 2200,
      "morale": 75.0,
      "stamina": 65.0,
      "facing": 0,
      "general_id": null
    }
  ]
}
```

### battle/data/side_blue.json

```json
// 截取：元字段 + 首 3 条
{
  "version": 1,
  "id": "side_blue",
  "name": "蓝方",
  "side": "blue",
  "units": [
    {
      "id": "b01",
      "side": "blue",
      "type": "cataphract",
      "col": 198,
      "row": 143,
      "troops": 3000,
      "morale": 100.0,
      "stamina": 100.0,
      "facing": 3,
      "general_id": null
    },
    {
      "id": "b02",
      "side": "blue",
      "type": "heavy_cavalry",
      "col": 198,
      "row": 147,
      "troops": 2800,
      "morale": 90.0,
      "stamina": 85.0,
      "facing": 3,
      "general_id": null
    },
    {
      "id": "b03",
      "side": "blue",
      "type": "light_cavalry",
      "col": 198,
      "row": 151,
      "troops": 2200,
      "morale": 75.0,
      "stamina": 65.0,
      "facing": 3,
      "general_id": null
    }
  ]
}
```

