# -*- coding: utf-8 -*-
"""命令模型（纯逻辑，**不** import pygame）。

不做 undo / redo（战斗模块无编辑会话概念）；只提供战斗模块自用的 `label()`。
"""

import logging

from battle.core import hexgrid

logger = logging.getLogger("battle.sim.command")


class Command:
    """命令基类。子类必须实现 `label()`。"""

    def label(self):
        """命令文本（控制台 / 面板显示用）。"""
        raise NotImplementedError


class MoveCommand(Command):
    """移动到目标格。

    字段只有 `target` 与 `path` —— 遇敌策略 / 自动追击 / 路径偏好本步不建
    （无战斗无敌人，建了就是死字段）。
    """

    def __init__(self, target, path=None):
        self.target = (int(target[0]), int(target[1]))           # 轴向坐标
        self.path = [(int(q), int(r)) for q, r in (path or [])]  # 不含起点格

    def label(self):
        col, row = hexgrid.axial_to_offset(*self.target)
        return "移动 → (%s, %s)" % (col, row)

    def __repr__(self):
        return "MoveCommand(target=%s, path=%d 格)" % (self.target, len(self.path))
