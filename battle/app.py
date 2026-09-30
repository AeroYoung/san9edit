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
