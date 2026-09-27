# -*- coding: utf-8 -*-
"""右侧面板深度编辑扩展：势力新建 / 删除级联、据点易主级联、外官编辑。

全走纯逻辑 + Command（不建 Tk 窗口）。
"""

import pytest

from game.core.scenario import ScenarioLoader
from game.core.scenario_writer import ScenarioWriter
from game.core.world import World
from game.core.node import Node
from game.core.faction import Faction
from game.core.character import Character
from game.core.edit_session import CompositeCommand, EditSession
from game.ui.dialogs.faction_lifecycle import (
    FactionCreatePlan, build_create_commands, build_delete_commands,
    plan_delete)
from game.ui.dialogs.node_owner import (
    build_commands as build_owner_commands, person_change,
    plan_owner_changes)
from game.ui.dialogs.official_edit import (
    OfficialEditPlan, build_official_commands, region_options)


class _Row:
    def __init__(self, node_id):
        self.node_id = node_id


@pytest.fixture
def world():
    w = World()
    w.factions["0521"] = Faction("0521", "曹操", color="#2928EF")
    w.factions["0035"] = Faction("0035", "袁绍", color="#E8C500")
    w.add_faction  # noqa: B018  （保持接口存在）
    w.nodes["090201"] = Node("090201", "濮阳", (114.0, 34.0), owner="0521")
    w.nodes["090202"] = Node("090202", "东阿", (114.1, 34.1), owner="0521")
    w.nodes["090502"] = Node("090502", "樊县", (114.2, 34.2))          # 无主
    w.nodes["020801"] = Node("020801", "南皮", (116.0, 38.0), owner="0035")
    w.county_names["0902"] = "东郡"
    w.state_names["09"] = "兖州"
    w.characters["0521"] = Character("0521", "曹操", faction="0521",
                                     node="090201", location="090201",
                                     role="君主")
    w.characters["0014"] = Character("0014", "尹礼", faction="0521",
                                     node="090202", location="090202",
                                     appeared=True, role="一般")
    w.characters["0065"] = Character("0065", "区星", appeared=True)     # 在野、已登场
    w.officials["09"] = {"name": "兖州刺史", "character_id": "0521", "rank": "州"}
    w.officials["0902"] = {"name": "东郡太守", "character_id": "0521", "rank": "郡"}
    for f in w.factions.values():
        f._nodes_ref = w.nodes
    return w


def _session(world):
    return EditSession(world, ScenarioWriter.serialize(world))


# ============================================================
# 势力新建
# ============================================================
def test_create_faction_and_undo(world):
    plan = FactionCreatePlan("0065", {"name": "区星", "color": "#112233",
                                      "prestige": 800, "stance": 0},
                             node_id="090502", character_id="0065")
    session = _session(world)
    session.execute(CompositeCommand(build_create_commands(world, plan),
                                     "新建势力"))

    assert "0065" in world.factions
    assert world.factions["0065"].name == "区星"
    assert world.character("0065").faction == "0065"       # 势力 id = 君主 id
    assert world.character("0065").node == "090502"
    assert world.node("090502").owner == "0065"
    assert session.is_dirty() is True

    session.undo()
    assert "0065" not in world.factions
    assert world.character("0065").faction is None
    assert world.node("090502").owner is None
    assert session.is_dirty() is False


def test_create_faction_keeps_node_other_persons(world):
    """都城已有的人物保持原样（需求 §3.1）。"""
    world.characters["0099"] = Character("0099", "路人", faction="0521",
                                         node="090502", location="090502",
                                         appeared=True)
    plan = FactionCreatePlan("0065", {"name": "区星", "color": "#112233",
                                      "prestige": 0, "stance": 0},
                             node_id="090502", character_id="0065")
    plan_cmds = build_create_commands(world, plan)
    # 只应有：势力 + 君主 + 据点 owner 三条，不含 0099
    assert len(plan_cmds) == 3


# ============================================================
# 势力删除
# ============================================================
def test_delete_faction_cascade_and_undo(world):
    plan = plan_delete(world, "0521")
    assert set(plan.node_ids) == {"090201", "090202"}
    assert set(plan.character_ids) == {"0521", "0014"}
    assert set(plan.official_ids) == {"09", "0902"}        # 君主担任的外官被删

    session = _session(world)
    session.execute(CompositeCommand(build_delete_commands(world, plan),
                                     "删除势力"))

    assert "0521" not in world.factions
    assert world.node("090201").owner is None
    assert world.character("0014").faction is None
    assert world.character("0014").node is None
    assert world.character("0014").appeared is True        # 登场状态不变
    assert world.official_of("09") is None
    assert world.official_of("0902") is None

    session.undo()
    assert "0521" in world.factions
    assert world.node("090201").owner == "0521"
    assert world.character("0014").faction == "0521"
    assert world.character("0014").node == "090202"
    assert world.official_of("09")["name"] == "兖州刺史"
    assert session.is_dirty() is False


def test_delete_faction_clears_player_faction(world):
    world.player_faction_id = "0521"
    plan = plan_delete(world, "0521")
    session = _session(world)
    session.execute(CompositeCommand(build_delete_commands(world, plan),
                                     "删除势力"))
    assert world.player_faction_id is None

    session.undo()
    assert world.player_faction_id == "0521"


def test_delete_faction_keeps_other_factions_officials(world):
    """只删「其人物属于被删势力」的外官条目（需求 §3.1）。"""
    world.officials["0208"] = {"name": "渤海太守", "character_id": "0035",
                               "rank": "郡"}
    plan = plan_delete(world, "0521")
    assert "0208" not in plan.official_ids


# ============================================================
# 据点易主
# ============================================================
def test_node_owner_cascade_and_undo(world):
    rows = [_Row("090202")]
    plans = plan_owner_changes(world, rows, "0035", cascade=True)
    assert plans[0].persons == ("0014",)                   # 已登场人物

    session = _session(world)
    session.execute(CompositeCommand(build_owner_commands(world, plans),
                                     "批量修改所属"))
    assert world.node("090202").owner == "0035"
    assert world.character("0014").faction == "0035"
    assert world.character("0014").node == "090202"

    session.undo()
    assert world.node("090202").owner == "0521"
    assert world.character("0014").faction == "0521"
    assert session.is_dirty() is False


def test_node_owner_without_cascade_only_touches_owner(world):
    plans = plan_owner_changes(world, [_Row("090202")], None, cascade=False)
    session = _session(world)
    session.execute(build_owner_commands(world, plans)[0])
    assert world.node("090202").owner is None
    assert world.character("0014").faction == "0521"       # 人物不动
    assert world.character("0014").node == "090202"


def test_person_change_only_real_changes(world):
    """势力已经一致时只改 node / location（需求 §4）。"""
    old, new = person_change(world, "0014", "090201", "0521")
    assert "faction" not in new
    assert new == {"node": "090201", "location": "090201"}
    assert old == {"node": "090202", "location": "090202"}


def test_skips_nodes_already_owned(world):
    plans = plan_owner_changes(world, [_Row("090201")], "0521", cascade=True)
    assert plans == []


# ============================================================
# 外官编辑
# ============================================================
def test_region_options_limited_to_faction(world):
    """可选行政区只限该势力实控区域（州 / 郡 / 县三层）。"""
    ids = [o.id for o in region_options(world, "0521")]
    assert ids == ["09", "0902", "090201", "090202"]
    assert [o.rank for o in region_options(world, "0521")] == ["州", "郡", "县", "县"]
    # 不属于该势力的据点不出现
    assert "020801" not in ids
    assert region_options(world, None) == []


def test_official_set_and_remove_with_cascade(world):
    plan = OfficialEditPlan(
        character_id="0065",
        set_items=(("0905", {"name": "东郡太守", "character_id": "0065",
                             "rank": "郡"}),),          # 没有 0905 也无妨：纯数据
        remove_regions=("0902",),
        move_to_seat=True, change_faction=False,
        seats={"0905": "090201"},
    )
    session = _session(world)
    session.execute(CompositeCommand(build_official_commands(world, plan),
                                     "编辑外官"))

    assert world.official_of("0902") is None                # 删除生效
    assert world.official_of("0905")["character_id"] == "0065"
    assert world.character("0065").node == "090201"         # 级联移动到治所
    assert session.is_dirty() is True

    session.undo()
    assert world.official_of("0902")["name"] == "东郡太守"
    assert world.official_of("0905") is None
    assert world.character("0065").node is None
    assert session.is_dirty() is False


def test_official_plan_no_cascade_by_default(world):
    plan = OfficialEditPlan(character_id="0065",
                            set_items=(("09", {"name": "兖州刺史",
                                               "character_id": "0065",
                                               "rank": "州"}),))
    cmds = build_official_commands(world, plan)
    assert len(cmds) == 1                                   # 只动外官，不动人物
    assert world.character("0065").node is None
