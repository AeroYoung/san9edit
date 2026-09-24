# -*- coding: utf-8 -*-
"""通用编辑会话：Command 模式 + 深度限制 + dirty 联动。

本模块不感知具体业务。所有改 World 的操作必须封装成 Command，
经 EditSession.execute() 执行。
"""


class Command:
    """单步命令基类。"""
    def do(self, world):
        raise NotImplementedError

    def undo(self, world):
        raise NotImplementedError

    def label(self) -> str:
        return "操作"


class CompositeCommand(Command):
    """组合命令：do 顺序执行、undo 逆序执行。

    第二阶段级联的核心。本阶段用于郡治互斥。
    """
    def __init__(self, commands, label="复合操作"):
        self.commands = list(commands)
        self._label = label

    def do(self, world):
        for c in self.commands:
            c.do(world)

    def undo(self, world):
        for c in reversed(self.commands):
            c.undo(world)

    def label(self):
        return self._label


class EditSession:
    max_depth = 5

    def __init__(self, world, baseline_snapshot: dict):
        """baseline_snapshot 是加载后立即 serialize(world) 得到的快照 dict。"""
        self._world = world
        self._baseline = baseline_snapshot
        self._undo_stack = []   # list[Command]
        self._redo_stack = []   # list[Command]

    def execute(self, cmd):
        """do + 入 undo 栈 + 清空 redo + 深度裁剪。"""
        cmd.do(self._world)
        self._undo_stack.append(cmd)
        if len(self._undo_stack) > self.max_depth:
            self._undo_stack.pop(0)
        self._redo_stack.clear()

    def undo(self):
        """弹 undo + undo + 入 redo 栈。栈空直接返回。"""
        if not self._undo_stack:
            return
        cmd = self._undo_stack.pop()
        cmd.undo(self._world)
        self._redo_stack.append(cmd)

    def redo(self):
        """弹 redo + do + 入 undo 栈。栈空直接返回。"""
        if not self._redo_stack:
            return
        cmd = self._redo_stack.pop()
        cmd.do(self._world)
        self._undo_stack.append(cmd)

    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    def is_dirty(self) -> bool:
        """current = serialize(world); return bool(diff(current, baseline))"""
        from game.core.scenario_writer import ScenarioWriter
        current = ScenarioWriter.serialize(self._world)
        return bool(ScenarioWriter.diff(current, self._baseline))

    def clear(self):
        """清空 undo/redo 栈。保存 / 另存为后调用。"""
        self._undo_stack.clear()
        self._redo_stack.clear()

    def rebase(self):
        """重设 baseline = serialize(world)。保存 / 另存为后调用。"""
        from game.core.scenario_writer import ScenarioWriter
        self._baseline = ScenarioWriter.serialize(self._world)
