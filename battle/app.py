# -*- coding: utf-8 -*-
"""战斗模块主程序：pygame 初始化 + 事件 + 主循环。

日志初始化在 `__main__.py` 完成，本模块只从 `pygame.init()` 起步。
"""

import logging
import os
import sys

import pygame

from battle import config
from battle.core.map_data import MapDataError, load_map
from battle.render.camera import Camera
from battle.render.hex_renderer import HexRenderer

logger = logging.getLogger("battle.app")


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
    renderer = HexRenderer(map_data.cols, map_data.rows, map_data.hex_size)

    logger.info(
        "战斗模块启动：窗口 %s×%s，地图 %s（%s×%s 格，hex_size=%s），"
        "初始 zoom=%.4f（范围 %.4f–%.4f）",
        viewport_w, viewport_h, map_data.name, map_data.cols, map_data.rows,
        map_data.hex_size, camera.zoom, camera.zoom_min, camera.zoom_max,
    )

    clock = pygame.time.Clock()
    dragging = False
    last_pos = (0, 0)

    while True:
        try:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    logger.info("收到退出事件，正常退出")
                    return 0

                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        dragging = True
                        last_pos = event.pos
                    elif event.button == 4:      # 旧式滚轮上
                        camera.zoom_at(config.ZOOM_STEP, *event.pos)
                    elif event.button == 5:      # 旧式滚轮下
                        camera.zoom_at(1.0 / config.ZOOM_STEP, *event.pos)

                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1:
                        dragging = False

                elif event.type == pygame.MOUSEMOTION:
                    if dragging:
                        dx = event.pos[0] - last_pos[0]
                        dy = event.pos[1] - last_pos[1]
                        camera.pan(dx, dy)
                        last_pos = event.pos

                elif event.type == pygame.MOUSEWHEEL:
                    mx, my = pygame.mouse.get_pos()
                    factor = (config.ZOOM_STEP if event.y > 0
                              else 1.0 / config.ZOOM_STEP)
                    camera.zoom_at(factor, mx, my)

                elif event.type == pygame.VIDEORESIZE:
                    screen = pygame.display.set_mode(
                        (event.w, event.h), pygame.RESIZABLE)
                    camera.on_resize(*screen.get_size())

            screen.fill(config.COLOR_BG)
            renderer.draw(screen, camera)
            pygame.display.flip()

        except Exception:
            # 运行时逻辑异常：ERROR + traceback 入日志，尝试继续运行
            logger.error("主循环异常", exc_info=True)
            if not pygame.get_init():
                logger.critical("pygame 已不可用，退出")
                return 1

        clock.tick(config.FPS)


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
