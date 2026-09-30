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
from battle.core import hexgrid
from battle.core.battle_state import BattleState
from battle.core.map_data import MapDataError, load_map
from battle.render.camera import Camera
from battle.render.console import Console
from battle.render.hex_renderer import HexRenderer
from battle.render.minimap import Minimap
from battle.render.panel import Panel
from battle.render.unit_layer import UnitLayer
from battle.render import widgets
from battle.sim.clock import Clock
from battle.sim.command import MoveCommand
from battle.sim.pathfinding import find_path
from battle.sim.step import step as sim_step

logger = logging.getLogger("battle.app")

_CLICK_TOLERANCE_PX = 4   # 位移 ≤ 此值算「单击」，否则算「框选」

def _mouse_on_ui(pos, panel, console, minimap):
    """鼠标是否落在 UI 覆盖区（面板 / 控制台 / 小地图）。"""
    return (panel.rect().collidepoint(pos)
            or console.rect().collidepoint(pos)
            or minimap.rect().collidepoint(pos))

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
    win_w, win_h = _startup_size()
    logger.info("启动窗口尺寸：%s×%s（桌面可用区域）", win_w, win_h)

    screen = pygame.display.set_mode((win_w, win_h), pygame.RESIZABLE)
    pygame.display.set_caption(config.WINDOW_TITLE)
    pygame.display.set_icon(_make_app_icon())

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
    sim_clock = Clock()       # tick 时钟（启动即运行）
    inter = {"box_start": None, "box_rect": None, "panning": False,
             "anchor": (0, 0), "right_start": None, "target_mode": False}
    motion = {}               # id → 旧 (q, r)：本 tick 位移插值用（渲染只读）
    menu = {"rect": None, "items": []}
    notice = {"text": "", "until": 0}

    def show_notice(text):
        notice["text"] = text
        notice["until"] = pygame.time.get_ticks() + config.NOTICE_DURATION_MS
        logger.debug("提示：%s", text)

    def advance_sim():
        """推进一个 tick，并记录本 tick 的位移（供渲染插值）。"""
        before = {u.id: (u.q, u.r) for u in state.units.values()}
        sim_step(state)
        motion.clear()
        for uid, pos in before.items():
            unit = state.unit(uid)
            if unit is not None and (unit.q, unit.r) != pos:
                motion[uid] = pos

    def toggle_play():
        running = sim_clock.toggle()
        logger.debug("进行 / 暂停：%s", "进行" if running else "暂停")

    def step_once():
        """单步：未暂停先自动暂停，再推进恰好一个 tick。"""
        sim_clock.request_step()
        advance_sim()
        logger.debug("单步：tick = %s", state.tick)

    def apply_panel_selection(unit_ids, mode):
        """面板行点击 → 落到共用选中集。

        mode：`"replace"`（单击，替换）/ `"toggle"`（Ctrl，切换）/ `"range"`（Shift，区间替换）。
        面板只报「点了哪些行、用什么语义」，选中集始终由 app 持有。
        """
        if mode == "toggle":
            for uid in unit_ids:
                if uid in selected:
                    selected.discard(uid)
                else:
                    selected.add(uid)
            return
        selected.clear()
        selected.update(unit_ids)

    def locate_on_map(unit):
        """面板右键「定位到地图」：把相机中心移到该部队所在格。"""
        wx, wy = hexgrid.axial_to_world(unit.q, unit.r, map_data.hex_size)
        camera.center_on_world(wx, wy)
        logger.debug("面板定位到地图：%s %s", unit.id, (unit.q, unit.r))

    # ---------------- 命令交互 ----------------
    def enter_target_mode():
        """进入目标格选择态（右键菜单「移动」与控制台「移动」按钮共用）。"""
        if not selected:
            show_notice("先选中部队，再点「移动」")
            return
        inter["target_mode"] = True
        show_notice("选择目标格（Esc 取消）")

    def issue_move(screen_pos):
        """目标格选择态点击：给选中部队各下一道 MoveCommand。"""
        inter["target_mode"] = False
        wx, wy = camera.screen_to_world(*screen_pos)
        target = hexgrid.world_to_axial(wx, wy, map_data.hex_size)
        col, row = hexgrid.axial_to_offset(*target)
        if not (0 <= col < map_data.cols and 0 <= row < map_data.rows):
            show_notice("目标格在地图外，已取消")
            return

        orders = 0
        for uid in selected:
            unit = state.unit(uid)
            if unit is None or unit.side != config.PLAYER_SIDE:
                continue          # 敌方不下命令（命令过滤点）
            path = find_path(state, unit, target)
            if path is None:
                logger.warning("目标不可达：%s → %s", unit.id, target)
                show_notice("目标不可达：%s" % unit.id)
                continue
            if not path:
                continue      # 已在目标格：不建空路径命令（否则命令列会空挂一个「移动」）
            unit.command = MoveCommand(target, path)
            orders += 1
        if orders:
            logger.debug("下达移动命令：%s 支 → %s", orders, target)

    def open_map_menu(pos):
        if inter["target_mode"] or not selected:
            return
        menu["items"] = [("移动", enter_target_mode)]
        menu["rect"] = _menu_rect(pos, [label for label, _cb in menu["items"]])

    def click_map_menu(pos):
        """菜单内左键：命中项执行回调；一律关掉菜单。"""
        index = _menu_index(menu["rect"], pos, len(menu["items"]))
        item = menu["items"][index] if index is not None else None
        menu["rect"] = None
        menu["items"] = []
        if item is not None:
            item[1]()
        return True

    def close_map_menu():
        menu["rect"] = None
        menu["items"] = []

    panel = Panel(state, on_selection=apply_panel_selection,
                  on_locate=locate_on_map)
    minimap = Minimap(state, map_data)
    console = Console(state, on_toggle_play=toggle_play, on_step=step_once,
                      on_speed=sim_clock.set_speed, on_move=enter_target_mode)
    panel.layout((viewport_w, viewport_h))
    minimap.layout((viewport_w, viewport_h), panel.rect().width)
    console.layout((viewport_w, viewport_h), panel.rect().width,
                   minimap.rect().width)

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

                # 地图右键菜单打开时优先处理（模态）
                if menu["rect"] is not None:
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if event.button == 1:
                            click_map_menu(event.pos)
                            continue
                        if event.button == 3:
                            close_map_menu()
                    elif event.type == pygame.MOUSEWHEEL:
                        close_map_menu()

                # UI 层先消费（小地图 / 面板 / 控制台内的点击与滚轮不落到地图）
                if (minimap.handle_event(event, camera)
                        or panel.handle_event(event) or console.handle_event(event)):
                    continue

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        toggle_play()      # 与点击「进行 / 暂停」完全等价
                    elif event.key == pygame.K_ESCAPE:
                        if inter["target_mode"]:
                            inter["target_mode"] = False
                            show_notice("已取消移动")
                        close_map_menu()
                    continue

                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:              # 左键：下令 / 选中 / 框选
                        if inter["target_mode"]:
                            issue_move(event.pos)
                            continue
                        inter["box_start"] = event.pos
                        inter["box_rect"] = pygame.Rect(event.pos, (0, 0))
                    elif event.button in (2, 3):       # 中键 / 右键：平移（右键单击另出菜单）
                        inter["panning"] = True
                        inter["anchor"] = event.pos
                        if event.button == 3:
                            inter["right_start"] = event.pos
                    elif event.button in (4, 5):
                        if not _mouse_on_ui(event.pos, panel, console, minimap):
                            factor = (config.ZOOM_STEP if event.button == 4
                                    else 1.0 / config.ZOOM_STEP)
                            camera.zoom_at(factor, *event.pos)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and inter["box_start"] is not None:
                        _finish_left_drag(inter["box_start"], event.pos,
                                          camera, unit_layer, selected)
                        inter["box_start"] = None
                        inter["box_rect"] = None
                    elif event.button == 3:
                        inter["panning"] = False
                        start = inter["right_start"]
                        inter["right_start"] = None
                        if (start is not None
                                and abs(event.pos[0] - start[0]) <= _CLICK_TOLERANCE_PX
                                and abs(event.pos[1] - start[1]) <= _CLICK_TOLERANCE_PX):
                            open_map_menu(event.pos)   # 右键单击（未拖拽）→ 菜单
                    elif event.button == 2:
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
                    if _mouse_on_ui((mx, my), panel, console, minimap):
                        continue
                    factor = (config.ZOOM_STEP if event.y > 0
                            else 1.0 / config.ZOOM_STEP)
                    camera.zoom_at(factor, mx, my)

            screen.fill(config.COLOR_BG)
            hex_renderer.draw(screen, camera)
            unit_layer.draw(screen, camera, selected, inter["box_rect"],
                            motion, sim_clock.progress())
            if inter["target_mode"]:
                _draw_target_mark(screen, camera, map_data)
            panel.draw(screen, (viewport_w, viewport_h), selected)
            minimap.draw(screen, camera)
            console.draw(screen, (viewport_w, viewport_h), not sim_clock.paused,
                         panel.rect().width, minimap.rect().width, sim_clock.speed)
            _draw_map_menu(screen, menu)
            _draw_notice(screen, notice)
            pygame.display.flip()

        except Exception:
            # 运行时逻辑异常：ERROR + traceback 入日志，尝试继续运行
            logger.error("主循环异常", exc_info=True)
            if not pygame.get_init():
                logger.critical("pygame 已不可用，退出")
                return 1

        for _ in range(sim_clock.advance(clock.tick(config.FPS))):
            advance_sim()      # 一帧可推进多次，防卡帧丢 tick

# ------------------------------------------------------------
# 地图右键菜单（只放「移动」一项）
_MAP_MENU_ITEM_H = 26
_MAP_MENU_PAD_X = 12
_MAP_MENU_PAD_Y = 6
_MAP_MENU_MIN_W = 120
_MAP_MENU_BG = (44, 50, 62)


def _menu_rect(pos, labels):
    """按屏幕坐标算菜单矩形，并夹在窗口内。"""
    font = widgets.get_font(config.FONT_SIZE_PANEL_CELL)
    width = max(_MAP_MENU_MIN_W,
                max(font.size(text)[0] for text in labels) + 2 * _MAP_MENU_PAD_X)
    height = len(labels) * _MAP_MENU_ITEM_H + 2 * _MAP_MENU_PAD_Y
    surface = pygame.display.get_surface()
    max_x = max(0, (surface.get_width() if surface else 10 ** 6) - width - 4)
    max_y = max(0, (surface.get_height() if surface else 10 ** 6) - height - 4)
    return pygame.Rect(min(max(pos[0], 0), max_x),
                       min(max(pos[1], 0), max_y), width, height)


def _menu_index(rect, pos, count):
    """菜单内命中项下标；未命中 → None。"""
    if rect is None or not rect.collidepoint(pos):
        return None
    index = (pos[1] - rect.top - _MAP_MENU_PAD_Y) // _MAP_MENU_ITEM_H
    return index if 0 <= index < count else None


def _draw_map_menu(surface, menu):
    rect = menu["rect"]
    if rect is None:
        return
    pygame.draw.rect(surface, _MAP_MENU_BG, rect)
    pygame.draw.rect(surface, config.PANEL_BORDER_COLOR, rect, 1)
    font = widgets.get_font(config.FONT_SIZE_PANEL_CELL)
    for index, (label, _callback) in enumerate(menu["items"]):
        y = rect.top + _MAP_MENU_PAD_Y + index * _MAP_MENU_ITEM_H + _MAP_MENU_ITEM_H // 2
        widgets.draw_text(surface, label, (rect.left + _MAP_MENU_PAD_X, y),
                          font, widgets.TEXT_COLOR, anchor="midleft", outline=False)


def _draw_target_mark(surface, camera, map_data):
    """目标格选择态：给鼠标下的格描一圈，表示处于可点选状态。"""
    wx, wy = camera.screen_to_world(*pygame.mouse.get_pos())
    q, r = hexgrid.world_to_axial(wx, wy, map_data.hex_size)
    center = hexgrid.axial_to_world(q, r, map_data.hex_size)
    points = [camera.world_to_screen(px, py)
              for px, py in hexgrid.hex_corners(center[0], center[1],
                                                map_data.hex_size)]
    pygame.draw.polygon(surface, config.TARGET_MARK_COLOR, points,
                        config.TARGET_MARK_WIDTH)


def _draw_notice(surface, notice):
    """屏幕左上的短提示（如目标不可达），到时自动消失。"""
    if not notice["text"] or pygame.time.get_ticks() > notice["until"]:
        return
    font = widgets.get_font(config.FONT_SIZE_CONSOLE)
    text = font.render(notice["text"], True, widgets.TEXT_COLOR)
    rect = pygame.Rect(0, 0, text.get_width() + 16, text.get_height() + 16)
    rect.topleft = (config.CONSOLE_MARGIN, config.CONSOLE_MARGIN)
    pygame.draw.rect(surface, _MAP_MENU_BG, rect, border_radius=6)
    pygame.draw.rect(surface, config.PANEL_BORDER_COLOR, rect, 1, border_radius=6)
    surface.blit(text, (rect.left + 8, rect.top + 8))


# ------------------------------------------------------------
def _finish_left_drag(start, end, camera, unit_layer, selected):
    """松手：位移小 → 单击（选中该格单位 / 点空白清空）；位移大 → 框选（不过滤阵营）。

    Ctrl / Shift + 框选 → 结果追加到现有选中集。
    """
    if (abs(end[0] - start[0]) <= _CLICK_TOLERANCE_PX
            and abs(end[1] - start[1]) <= _CLICK_TOLERANCE_PX):
        unit = unit_layer.hit_test(start, camera)
        selected.clear()
        if unit is not None:
            selected.add(unit.id)
        return

    rect = _rect_between(start, end)
    hits = unit_layer.box_select(rect, camera, None)
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

def _make_app_icon():
    """几何绘制的窗口图标：圆角底板 + 平顶六边形轮廓（不读外部文件）。"""
    size = int(config.APP_ICON_SIZE)
    icon = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.rect(icon, config.APP_ICON_BG, icon.get_rect(),
                     border_radius=max(2, size // 6))

    radius = size * 0.30
    corners = hexgrid.hex_corners(size / 2.0, size / 2.0, radius)
    pygame.draw.polygon(icon, config.APP_ICON_FG, corners,
                        max(2, size // 12))
    return icon

def _startup_size():
    """启动窗口尺寸 = 桌面可用区域（最大化效果）。

    读不到桌面尺寸时退回 config 的设计尺寸。
    减去的余量给标题栏 / 任务栏留位，避免标题栏被挤出屏幕。
    """
    try:
        sizes = pygame.display.get_desktop_sizes()
    except Exception:
        logger.warning("无法读取桌面分辨率，按配置尺寸建窗", exc_info=True)
        return config.WINDOW_WIDTH, config.WINDOW_HEIGHT
    if not sizes:
        return config.WINDOW_WIDTH, config.WINDOW_HEIGHT

    desktop_w, desktop_h = sizes[0]
    avail_w = max(320, desktop_w - 20)   # 左右边框余量
    avail_h = max(240, desktop_h - 90)   # 标题栏 + 任务栏余量
    return avail_w, avail_h

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
