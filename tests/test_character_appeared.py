# -*- coding: utf-8 -*-
"""登场字段 appeared：加载器兼容 + 设为登场开关 + 增量保存 round-trip。

对应需求 §6「边界与兼容」。
"""

import json

from game.config.constants import DEFAULT_CHARACTERS_PATH
from game.core.scenario import ScenarioLoader
from game.core.scenario_writer import ScenarioWriter
from game.core.edit_session import EditSession
from game.core.edit_commands import CharacterEditCommand


class _MockGeo:
    """最小 geo_data：只有 shapes_point / shapes_line。"""
    def __init__(self):
        self.shapes_point = [
            {
                "properties": {
                    "id": "130301", "县名": "陈留", "type": "城",
                    "level": 5, "is_capital": False,
                },
                "geometry": {"coordinates": [114.0, 34.0]},
            },
        ]
        self.shapes_line = []


def _raw(**kw):
    raw = {
        "version": 2,
        "id": "test",
        "name": "测试",
        "desc": "",
        "start": {"year": 190, "month": 1, "xun": 1},
        "player_faction": "0521",
        "factions": {
            "0521": {"name": "曹操", "color": "#2928EF",
                     "prestige": 1000, "stance": 0},
        },
        "characters": {},
        "nodes": {},
    }
    raw.update(kw)
    return raw


def test_full_roster_loaded_without_year_filter():
    """加载器不再按年份筛人：characters.json 全量进 World（含穿越人物）。"""
    world = ScenarioLoader.from_dict(_raw(), _MockGeo())
    base = json.loads(
        DEFAULT_CHARACTERS_PATH.read_text(encoding="utf-8"))["characters"]
    assert set(world.characters) == set(base)
    assert world.character("1049") is not None   # 穿越人物也在


def test_legacy_scenario_defaults_to_appeared():
    """老剧本无 appeared 字段 → 全部默认登场；character_id_range 仍生效。"""
    world = ScenarioLoader.from_dict(
        _raw(character_id_range=[1, 100]), _MockGeo())
    assert world.characters
    assert all(c.appeared for c in world.characters.values())
    # 白名单兼容：id > 100 的人不加载
    assert max(int(cid) for cid in world.characters) <= 100


def test_scenario_override_sets_appeared_false():
    """剧本写 appeared=false → 该人未登场，但仍在 World 里（可编辑）。"""
    world = ScenarioLoader.from_dict(
        _raw(characters={"0147": {"appeared": False}}), _MockGeo())
    ch = world.character("0147")
    assert ch is not None
    assert ch.appeared is False
    assert ch.faction is None       # 未登场人物归属字段为 null


def test_toggle_appeared_command_and_dirty():
    """设为登场 → dirty；undo → 回到未登场且干净（§6 第 4 / 5 行）。"""
    raw = _raw(characters={"0147": {"appeared": False}})
    world = ScenarioLoader.from_dict(raw, _MockGeo())
    session = EditSession(world, ScenarioWriter.serialize(world))
    assert session.is_dirty() is False

    session.execute(CharacterEditCommand(
        "0147", {"appeared": False}, {"appeared": True}))
    assert world.character("0147").appeared is True
    assert session.is_dirty() is True

    session.undo()
    assert world.character("0147").appeared is False
    assert session.is_dirty() is False


def test_toggle_keeps_faction_fields():
    """「设为未登场」保留已有归属字段（可逆），并写进增量保存。"""
    raw = _raw(characters={"0521": {"appeared": True, "faction": "0521",
                                    "node": "130301", "location": "130301",
                                    "role": "君主"}})
    world = ScenarioLoader.from_dict(raw, _MockGeo())
    baseline = ScenarioWriter.serialize(world)
    session = EditSession(world, baseline)

    session.execute(CharacterEditCommand(
        "0521", {"appeared": True}, {"appeared": False}))
    ch = world.character("0521")
    assert ch.appeared is False
    assert (ch.faction, ch.node, ch.location, ch.role) == (
        "0521", "130301", "130301", "君主")


def test_appeared_excluded_from_faction_and_node_counts():
    """未登场人物不算势力 / 据点的人物；设为登场上后重新计入（归属字段没动）。"""
    raw = _raw(characters={
        "0147": {"appeared": True, "faction": "0521",
                 "node": "130301", "location": "130301", "role": "一般"},
        "0148": {"appeared": False, "faction": "0521",
                 "node": "130301", "location": "130301", "role": "一般"},
    })
    world = ScenarioLoader.from_dict(raw, _MockGeo())

    assert world.count_characters_by_faction()["0521"] == 1
    assert world.count_characters_by_node()["130301"] == 1
    assert [c.id for c in world.characters_of("0521")] == ["0147"]
    assert [c.id for c in world.characters_at("130301")] == ["0147"]

    # 设为登场 → 归属字段没动，但两处口径都把它算进来
    world.character("0148").appeared = True
    assert world.count_characters_by_faction()["0521"] == 2
    assert world.count_characters_by_node()["130301"] == 2

    # 再设回未登场 → 落回 1
    world.character("0148").appeared = False
    assert world.count_characters_by_faction()["0521"] == 1
    assert world.count_characters_by_node()["130301"] == 1
