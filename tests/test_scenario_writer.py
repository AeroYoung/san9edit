# -*- coding: utf-8 -*-
"""§12.2 第 20 条验收：序列化 round-trip + diff + 增量保存。"""

import json

from game.core.scenario import ScenarioLoader
from game.core.scenario_writer import ScenarioWriter
from game.core.world import World
from game.core.node import Node
from game.core.faction import Faction


class _MockGeo:
    """最小 geo_data：只有 shapes_point / shapes_line，供 _build_nodes_from_geo 用。"""
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


def _raw_scenario():
    return {
        "version": 2,
        "id": "default",
        "name": "测试",
        "desc": "",
        "start": {"year": 190, "month": 1, "xun": 1},
        "player_faction": "0521",
        "factions": {
            "0521": {"name": "曹操", "color": "#2928EF",
                     "prestige": 1000, "stance": 0},
        },
        "characters": {
            "0521": {"faction": "0521", "node": "130301",
                     "location": "130301", "role": "君主"},
        },
        "nodes": {
            "130301": {"owner": "0521", "troops": 8000,
                       "gold": 1000, "food": 20000},
        },
    }


def test_roundtrip():
    geo = _MockGeo()
    world = ScenarioLoader.from_dict(_raw_scenario(), geo)

    serialized = ScenarioWriter.serialize(world)

    # 结构检查：characters 含 node/location，nodes 含 owner
    assert serialized["characters"]["0521"]["node"] == "130301"
    assert serialized["characters"]["0521"]["location"] == "130301"
    assert serialized["nodes"]["130301"]["owner"] == "0521"
    # factions 不写 gold / food
    assert "gold" not in serialized["factions"]["0521"]
    assert "food" not in serialized["factions"]["0521"]

    # 重建：关键字段一致
    world2 = ScenarioLoader.from_dict(serialized, geo)
    assert world2.factions["0521"].name == "曹操"
    assert world2.nodes["130301"].owner == "0521"
    assert world2.characters["0521"].node == "130301"


def test_diff_empty_and_changed():
    geo = _MockGeo()
    world = ScenarioLoader.from_dict(_raw_scenario(), geo)
    baseline = ScenarioWriter.serialize(world)

    # 未改动 → diff 空
    assert ScenarioWriter.diff(ScenarioWriter.serialize(world), baseline) == {}

    # 改一个据点字段 → diff 只含该字段
    world.nodes["130301"].gold = 5000
    delta = ScenarioWriter.diff(ScenarioWriter.serialize(world), baseline)
    assert delta["nodes"]["130301"]["gold"] == (1000, 5000)
    # 其它 section 不出现
    assert "factions" not in delta


def test_save_incremental(tmp_path):
    geo = _MockGeo()
    raw = _raw_scenario()
    world = ScenarioLoader.from_dict(raw, geo)
    baseline = ScenarioWriter.serialize(world)

    # 改 gold + 改一个静态字段（type）
    world.nodes["130301"].gold = 5000
    world.nodes["130301"].type = "关隘"

    path = tmp_path / "out.json"
    ScenarioWriter.save(world, str(path), raw, baseline)

    saved = json.loads(path.read_text(encoding="utf-8"))
    node = saved["nodes"]["130301"]
    # 改动字段被写入
    assert node["gold"] == 5000
    assert node["type"] == "关隘"
    # 未改动字段保留 raw 原值
    assert node["owner"] == "0521"
    assert node["troops"] == 8000
    assert node["food"] == 20000
    # factions 段不含 gold/food
    assert "gold" not in saved["factions"]["0521"]
    assert "food" not in saved["factions"]["0521"]
