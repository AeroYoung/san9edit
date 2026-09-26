# -*- coding: utf-8 -*-
"""移动到据点：单人变更规则（§3.6）/ 命令生成（§3.9）/ 目标分类（§3.5）。

纯逻辑测试，不建 Tk 窗口。
"""

from game.core.world import World
from game.core.node import Node
from game.core.faction import Faction
from game.core.character import Character
from game.ui.dialogs.move_to_node import (
    KIND_BLOCKED, KIND_FACTION, KIND_FREE, KIND_NODE_ONLY, KIND_UNCHANGED,
    MovePlan, build_commands, plan_moves, target_owner,
)

TARGET = "130301"       # 有主
EMPTY = "999901"        # 无主
DIRTY = "999902"        # owner 脏数据（world.factions 里没有）


def _world():
    w = World()
    w.factions["0521"] = Faction("0521", "曹操", color="#2928EF")
    w.factions["0035"] = Faction("0035", "袁绍", color="#E8C500")
    w.nodes[TARGET] = Node(TARGET, "陈留", (114.0, 34.0), owner="0521")
    w.nodes[EMPTY] = Node(EMPTY, "空县", (115.0, 35.0))
    w.nodes[DIRTY] = Node(DIRTY, "脏县", (116.0, 36.0), owner="8888")
    w.nodes["130302"] = Node("130302", "己方县", (114.1, 34.1), owner="0035")
    return w


def _char(world, cid, name, faction=None, node=None, appeared=True):
    ch = Character(cid, name, faction=faction, node=node, location=node,
                   role="一般", appeared=appeared)
    world.characters[cid] = ch
    return ch


class _Row:
    """最小行模型：只需要 id。"""

    def __init__(self, cid):
        self.id = cid


def test_target_owner_dirty_is_none():
    w = _world()
    assert target_owner(w, w.node(TARGET)) == "0521"
    assert target_owner(w, w.node(EMPTY)) is None
    assert target_owner(w, w.node(DIRTY)) is None      # 脏数据视为无主
    assert target_owner(w, None) is None


def test_non_ruler_to_owned_node_switches_faction():
    """§3.6 第 5 条：非君主 → 有主且 faction 不同 → faction 跟随。"""
    w = _world()
    _char(w, "0001", "甲", faction="0035", node="130302")
    moves = plan_moves(w, [_Row("0001")], TARGET)
    m = moves[0]
    assert m.kind == KIND_FACTION
    assert m.new == {"node": TARGET, "location": TARGET, "faction": "0521"}
    assert m.old == {"node": "130302", "location": "130302", "faction": "0035"}


def test_non_ruler_same_faction_keeps_faction():
    """§3.6 第 4 条：faction 已等于目标 owner → 不变（不进 new）。"""
    w = _world()
    _char(w, "0001", "甲", faction="0521", node="130302")
    m = plan_moves(w, [_Row("0001")], TARGET)[0]
    assert m.kind == KIND_NODE_ONLY
    assert m.new == {"node": TARGET, "location": TARGET}
    assert "faction" not in m.new


def test_non_ruler_to_empty_node_becomes_free():
    """§3.6 第 6 条：目标无主 → faction = None（下野）。"""
    w = _world()
    _char(w, "0001", "甲", faction="0521", node="130302")
    m = plan_moves(w, [_Row("0001")], EMPTY)[0]
    assert m.kind == KIND_FREE
    assert m.new == {"node": EMPTY, "location": EMPTY, "faction": None}


def test_non_ruler_without_faction_to_empty_node():
    """本来就在野 → 只是换据点，不产生 faction 字段。"""
    w = _world()
    _char(w, "0001", "甲", faction=None, node="130302")
    m = plan_moves(w, [_Row("0001")], EMPTY)[0]
    assert m.kind == KIND_NODE_ONLY
    assert m.new == {"node": EMPTY, "location": EMPTY}


def test_ruler_blocked_off_own_node():
    """§3.6 第 1 / 2 条：君主到无主 / 他势力据点 → 阻断。"""
    w = _world()
    _char(w, "0521", "曹操", faction="0521", node="130302")
    for target in (EMPTY, DIRTY, "130302x"):
        if target == "130302x":
            w.nodes[target] = Node(target, "袁县", (1.0, 1.0), owner="0035")
        m = plan_moves(w, [_Row("0521")], target)[0]
        assert m.kind == KIND_BLOCKED, target
        assert m.new == {}


def test_ruler_to_own_node_allowed():
    """§3.6 第 3 条：君主到自己的据点 → 只改 node / location。"""
    w = _world()
    _char(w, "0521", "曹操", faction="0521", node="130302", appeared=True)
    m = plan_moves(w, [_Row("0521")], TARGET)[0]
    assert m.kind == KIND_NODE_ONLY
    assert m.new == {"node": TARGET, "location": TARGET}
    assert m.appeared_pending is False


def test_already_at_target_is_unchanged():
    """§3.10：已在目标据点 → 不计入变更。"""
    w = _world()
    _char(w, "0001", "甲", faction="0521", node=TARGET)
    m = plan_moves(w, [_Row("0001")], TARGET)[0]
    assert m.kind == KIND_UNCHANGED
    assert m.new == {}


def test_location_equal_target_not_in_new():
    """location 恰好已是目标 → 该字段不算变化（§3.9 只含真正变化）。"""
    w = _world()
    ch = _char(w, "0001", "甲", faction="0521", node="130302")
    ch.location = TARGET
    m = plan_moves(w, [_Row("0001")], TARGET)[0]
    assert m.new == {"node": TARGET}


def test_appeared_pending_and_ask_yes():
    """§3.7：未登场 + 目标有主 → 标记将询问；答是才写 appeared。"""
    w = _world()
    _char(w, "0001", "甲", faction=None, node="130302", appeared=False)
    preview = plan_moves(w, [_Row("0001")], TARGET, set_appeared=False)[0]
    assert preview.appeared_pending is True
    assert "appeared" not in preview.new

    agreed = plan_moves(w, [_Row("0001")], TARGET, set_appeared=True)[0]
    assert agreed.new.get("appeared") is True
    assert agreed.old.get("appeared") is False


def test_no_ask_when_target_ownerless():
    """§3.7：目标无主 → 不触发登场询问。"""
    w = _world()
    _char(w, "0001", "甲", faction="0521", node="130302", appeared=False)
    m = plan_moves(w, [_Row("0001")], EMPTY, set_appeared=True)[0]
    assert m.appeared_pending is False
    assert "appeared" not in m.new


def test_build_commands_skips_blocked_and_unchanged():
    """§3.9：阻断者 / 无变化者不进命令。"""
    w = _world()
    _char(w, "0001", "甲", faction="0521", node="130302")    # 同势力 → 仅换据点
    _char(w, "0002", "乙", faction="0521", node=TARGET)      # 已在目标
    _char(w, "0035", "袁绍", faction="0035", node="130302")  # 他势力君主 → 阻断
    moves = plan_moves(w, [_Row("0001"), _Row("0002"), _Row("0035")], TARGET)
    active = [m for m in moves if m.kind not in (KIND_UNCHANGED, KIND_BLOCKED)]
    plan = MovePlan(node_id=TARGET, owner="0521", moves=tuple(active),
                    blocked=tuple(m for m in moves if m.kind == KIND_BLOCKED),
                    unchanged=1)
    cmds = build_commands(plan)
    assert len(cmds) == 1
    assert cmds[0].character_id == "0001"
    assert cmds[0].new_values == {"node": TARGET, "location": TARGET}
    assert plan.unchanged == 1
    assert [m.name for m in plan.blocked] == ["袁绍"]
