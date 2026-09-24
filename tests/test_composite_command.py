# -*- coding: utf-8 -*-
"""§12.2 第 19 条验收：CompositeCommand do/undo 顺序。"""

from game.core.world import World
from game.core.node import Node
from game.core.edit_session import CompositeCommand
from game.core.edit_commands import NodeEditCommand


def _make_world():
    world = World()
    world.nodes["010101"] = Node("010101", "甲县", (110, 30))
    world.nodes["010102"] = Node("010102", "乙县", (111, 31))
    return world


def test_composite_do_undo():
    world = _make_world()

    c1 = NodeEditCommand("010101", {"level": 5}, {"level": 9})
    c2 = NodeEditCommand("010102", {"gold": 0}, {"gold": 100})

    composite = CompositeCommand([c1, c2], "设置郡治")
    composite.do(world)

    # do：两个字段都变
    assert world.nodes["010101"].level == 9
    assert world.nodes["010102"].gold == 100

    # undo：逆序还原
    composite.undo(world)
    assert world.nodes["010101"].level == 5
    assert world.nodes["010102"].gold == 0


def test_composite_label():
    c1 = NodeEditCommand("010101", {}, {})
    c2 = NodeEditCommand("010102", {}, {})
    composite = CompositeCommand([c1, c2], "设置郡治")
    assert composite.label() == "设置郡治"
