# -*- coding: utf-8 -*-
"""具体命令：据点编辑、势力编辑、人物编辑。

约定：old_values / new_values 都是 {field: value} dict，只含真正变化的字段。
"""

from game.core.edit_session import Command


class NodeEditCommand(Command):
    def __init__(self, node_id, old_values: dict, new_values: dict):
        self.node_id = node_id
        self.old_values = dict(old_values)
        self.new_values = dict(new_values)

    def do(self, world):
        n = world.nodes[self.node_id]
        for k, v in self.new_values.items():
            setattr(n, k, v)

    def undo(self, world):
        n = world.nodes[self.node_id]
        for k, v in self.old_values.items():
            setattr(n, k, v)

    def label(self):
        return f"编辑据点 {self.node_id}"


class FactionEditCommand(Command):
    """势力静态字段编辑。同构 NodeEditCommand，操作 world.factions。"""
    def __init__(self, faction_id, old_values: dict, new_values: dict):
        self.faction_id = faction_id
        self.old_values = dict(old_values)
        self.new_values = dict(new_values)

    def do(self, world):
        f = world.factions[self.faction_id]
        for k, v in self.new_values.items():
            setattr(f, k, v)

    def undo(self, world):
        f = world.factions[self.faction_id]
        for k, v in self.old_values.items():
            setattr(f, k, v)

    def label(self):
        return f"编辑势力 {self.faction_id}"


class CharacterEditCommand(Command):
    """人物字段编辑。同构 NodeEditCommand，操作 world.characters。

    当前用于「设为登场 / 设为未登场」开关（new_values = {"appeared": bool}），
    将来的完整人物编辑沿用同一个命令。
    """
    def __init__(self, character_id, old_values: dict, new_values: dict):
        self.character_id = character_id
        self.old_values = dict(old_values)
        self.new_values = dict(new_values)

    def do(self, world):
        c = world.characters[self.character_id]
        for k, v in self.new_values.items():
            setattr(c, k, v)

    def undo(self, world):
        c = world.characters[self.character_id]
        for k, v in self.old_values.items():
            setattr(c, k, v)

    def label(self):
        return f"编辑人物 {self.character_id}"


# TODO(phase2): NodeEditCommand 支持 owner 字段 + 级联
# TODO(phase2): 新增 FactionCreateCommand / FactionDeleteCommand
