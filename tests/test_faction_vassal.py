# -*- coding: utf-8 -*-
"""势力分类（独立 / 附庸）：数据字段 / 加载校验 / 颜色派生 / 编辑联动。

对应需求 §3.1 – §3.4、§3.9、§4、§9。
"""

import json

from game.core.edit_commands import FactionEditCommand, build_vassal_commands
from game.core.faction import Faction
from game.core.faction_color import (
    DONGZHUO_COLOR, faction_display_color,
)
from game.core.scenario import ScenarioLoader
from game.core.scenario_writer import ScenarioWriter


class _MockGeo:
    """最小 geo_data：两个县点 + 一条郡界。"""
    def __init__(self):
        self.shapes_point = [
            {
                "properties": {
                    "id": "130301", "县名": "陈留", "type": "城",
                    "level": 5, "is_capital": False,
                },
                "geometry": {"coordinates": [114.0, 34.0]},
            },
            {
                "properties": {
                    "id": "130302", "县名": "雍丘", "type": "城",
                    "level": 5, "is_capital": False,
                },
                "geometry": {"coordinates": [114.5, 34.5]},
            },
        ]
        self.shapes_line = []


def _raw(factions=None, characters=None, nodes=None):
    raw = {
        "version": 2,
        "id": "test",
        "name": "测试",
        "desc": "",
        "start": {"year": 190, "month": 1, "xun": 1},
        "player_faction": "0521",
        "factions": factions if factions is not None else {
            "0521": {"name": "曹操", "color": "#2928EF",
                     "prestige": 1000, "stance": 0},
        },
        "characters": characters if characters is not None else {},
        "nodes": nodes if nodes is not None else {},
    }
    return raw


def _load(raw):
    return ScenarioLoader.from_dict(raw, _MockGeo())


# ============================================================
# 1. 数据层：三个字段
# ============================================================
class TestFactionFields:
    def test_defaults_are_independent(self):
        f = Faction("0521", "曹操")
        assert f.independent is True
        assert f.overlord_id is None
        assert f.vassal_value == 0

    def test_to_dict_writes_all_three(self):
        f = Faction("0952", "刘备", independent=False, overlord_id="0736",
                    vassal_value=85)
        d = f.to_dict()
        assert d["independent"] is False
        assert d["overlord_id"] == "0736"
        assert d["vassal_value"] == 85

    def test_from_dict_defaults_for_old_scenario(self):
        f = Faction.from_dict("0521", {"name": "曹操", "color": "#2928EF",
                                       "prestige": 1000, "stance": 0})
        assert f.independent is True
        assert f.overlord_id is None
        assert f.vassal_value == 0

    def test_from_dict_clamps_vassal_value(self):
        # 附庸值 0 → 1（附庸不因 0 变独立）；≥100 → 99（本轮不实现融入）
        assert Faction.from_dict(
            "a", {"independent": False, "overlord_id": "b",
                  "vassal_value": 0}).vassal_value == 1
        assert Faction.from_dict(
            "a", {"independent": False, "overlord_id": "b",
                  "vassal_value": 100}).vassal_value == 99

    def test_from_dict_forces_zero_when_independent(self):
        f = Faction.from_dict("a", {"independent": True, "overlord_id": "b",
                                    "vassal_value": 70})
        assert f.vassal_value == 0

    def test_vassal_label(self):
        assert Faction("a", "甲").vassal_label() == "独立"
        f = Faction("a", "甲", independent=False, overlord_id="b",
                    vassal_value=50)
        assert f.vassal_label("乙") == "乙"
        assert f.vassal_label() == "b"


# ============================================================
# 2. 序列化 / diff / 增量保存
# ============================================================
class TestWriterCoversVassalFields:
    def test_serialize_writes_three_fields(self):
        world = _load(_raw())
        section = ScenarioWriter.serialize(world)["factions"]["0521"]
        assert section["independent"] is True
        assert section["overlord_id"] is None
        assert section["vassal_value"] == 0

    def test_diff_and_save_cover_three_fields(self, tmp_path):
        world = _load(_raw(factions={
            "0521": {"name": "曹操", "color": "#2928EF",
                     "prestige": 1000, "stance": 0},
            "0736": {"name": "董卓", "color": "#5B2B2B",
                     "prestige": 1000, "stance": 0},
        }))
        baseline = ScenarioWriter.serialize(world)
        world.factions["0521"].independent = False
        world.factions["0521"].overlord_id = "0736"
        world.factions["0521"].vassal_value = 85

        delta = ScenarioWriter.diff(ScenarioWriter.serialize(world), baseline)
        assert delta["factions"]["0521"]["independent"] == (True, False)
        assert delta["factions"]["0521"]["overlord_id"] == (None, "0736")
        assert delta["factions"]["0521"]["vassal_value"] == (0, 85)

        path = tmp_path / "out.json"
        ScenarioWriter.save(world, str(path), _raw(), baseline)
        saved = json.loads(path.read_text(encoding="utf-8"))
        assert saved["factions"]["0521"]["independent"] is False
        assert saved["factions"]["0521"]["overlord_id"] == "0736"
        assert saved["factions"]["0521"]["vassal_value"] == 85


# ============================================================
# 3. 加载期附庸关系校验（§3.3）
# ============================================================
class TestVassalValidation:
    def test_independent_with_overlord_is_cleared(self):
        world = _load(_raw(factions={
            "0521": {"name": "曹操", "independent": True,
                     "overlord_id": "0736", "vassal_value": 0},
        }))
        assert "0521" in world.factions
        assert world.factions["0521"].overlord_id is None
        assert world.vassal_removals == []

    def test_vassal_without_overlord_is_removed(self):
        world = _load(_raw(
            factions={
                "0521": {"name": "曹操"},
                "0952": {"name": "刘备", "independent": False,
                         "overlord_id": None, "vassal_value": 50},
            },
            characters={"0952": {"faction": "0952", "node": "130301",
                                 "location": "130301"}},
            nodes={"130301": {"owner": "0952", "troops": 100,
                              "gold": 10, "food": 10}},
        ))
        assert "0952" not in world.factions
        assert world.nodes["130301"].owner is None          # 据点置无主
        assert world.characters["0952"].faction is None     # 人物下野
        assert len(world.vassal_removals) == 1
        assert world.vassal_removals[0][0] == "0952"

    def test_missing_overlord_is_removed(self):
        world = _load(_raw(factions={
            "0952": {"name": "刘备", "independent": False,
                     "overlord_id": "9999", "vassal_value": 50},
        }))
        assert "0952" not in world.factions
        assert "不存在" in world.vassal_removals[0][2]

    def test_overlord_is_itself_vassal_is_removed_recursively(self):
        # A → B → C（C 是附庸但没有宗主）：B 与 A 都应被递归移除
        world = _load(_raw(factions={
            "0521": {"name": "甲方", "independent": False,
                     "overlord_id": "0736", "vassal_value": 50},
            "0736": {"name": "乙方", "independent": False,
                     "overlord_id": "0952", "vassal_value": 50},
            "0952": {"name": "丙方", "independent": False,
                     "overlord_id": None, "vassal_value": 50},
        }))
        assert world.factions == {}
        assert {r[0] for r in world.vassal_removals} == {"0521", "0736", "0952"}

    def test_cycle_is_removed(self):
        world = _load(_raw(factions={
            "0521": {"name": "甲方", "independent": False,
                     "overlord_id": "0736", "vassal_value": 50},
            "0736": {"name": "乙方", "independent": False,
                     "overlord_id": "0521", "vassal_value": 50},
        }))
        assert world.factions == {}
        assert len(world.vassal_removals) == 2

    def test_valid_vassal_survives(self):
        world = _load(_raw(factions={
            "0521": {"name": "曹操"},
            "0952": {"name": "刘备", "independent": False,
                     "overlord_id": "0521", "vassal_value": 85},
        }))
        assert set(world.factions) == {"0521", "0952"}
        assert world.vassal_removals == []
        assert world.factions["0952"].vassal_value == 85


# ============================================================
# 4. 颜色派生（§3.4）
# ============================================================
class TestDisplayColor:
    def _factions(self):
        lord = Faction("0736", "董卓", color="#5B2B2B")
        a = Faction("0592", "段煨", color="#123456",
                    independent=False, overlord_id="0736", vassal_value=85)
        b = Faction("0428", "徐荣", color="#123456",
                    independent=False, overlord_id="0736", vassal_value=85)
        c = Faction("0301", "胡轸", color="#123456",
                    independent=False, overlord_id="0736", vassal_value=10)
        free = Faction("0521", "曹操", color="#2928EF")
        return {"0736": lord, "0592": a, "0428": b, "0301": c,
                "0521": free}, (lord, a, b, c, free)

    def test_independent_uses_own_color(self):
        factions, (_lord, _a, _b, _c, free) = self._factions()
        assert faction_display_color(free, factions) == "#2928EF"

    def test_dongzhuo_is_fixed_brown(self):
        factions, (lord, *_rest) = self._factions()
        assert faction_display_color(lord, factions) == DONGZHUO_COLOR

    def test_vassal_blends_toward_overlord(self):
        factions, (_lord, a, _b, _c, _free) = self._factions()
        own_only = Faction("0592", "段煨", color="#123456")
        assert faction_display_color(a, factions) != own_only.color

    def test_same_overlord_vassals_are_distinguishable(self):
        factions, (_lord, a, b, c, _free) = self._factions()
        colors = {faction_display_color(f, factions) for f in (a, b, c)}
        assert len(colors) == 3

    def test_does_not_write_back_color(self):
        factions, (_lord, a, *_rest) = self._factions()
        faction_display_color(a, factions)
        assert a.color == "#123456"


# ============================================================
# 5. 编辑联动（§3.9 / §4）
# ============================================================
class TestVassalCommands:
    def _world(self):
        """甲（独立）← 丙（附庸）；乙（独立）备用。"""
        return _load(_raw(factions={
            "0521": {"name": "甲方"},
            "0736": {"name": "乙方"},
            "0952": {"name": "丙方", "independent": False,
                     "overlord_id": "0521", "vassal_value": 30},
        }))

    def test_independent_to_vassal_moves_own_vassals(self):
        world = self._world()
        faction = world.factions["0521"]
        cmds = build_vassal_commands(
            world, faction,
            {"independent": True},
            {"independent": False, "overlord_id": "0736",
             "vassal_value": 85})
        assert len(cmds) == 2
        assert isinstance(cmds[0], FactionEditCommand)
        assert cmds[1].faction_id == "0952"
        assert cmds[1].new_values == {"overlord_id": "0736"}

    def test_vassal_to_independent_leaves_own_vassals(self):
        world = self._world()
        faction = world.factions["0952"]
        cmds = build_vassal_commands(
            world, faction,
            {"independent": False, "overlord_id": "0521", "vassal_value": 30},
            {"independent": True, "overlord_id": None, "vassal_value": 0})
        assert len(cmds) == 1

    def test_delete_overlord_frees_vassals(self):
        from game.ui.dialogs.faction_lifecycle import (
            build_delete_commands, plan_delete)
        world = self._world()
        plan = plan_delete(world, "0521")
        assert plan.vassal_ids == ("0952",)
        cmds = build_delete_commands(world, plan)
        vassal_cmds = [c for c in cmds if isinstance(c, FactionEditCommand)]
        assert len(vassal_cmds) == 1
        assert vassal_cmds[0].new_values == {
            "independent": True, "overlord_id": None, "vassal_value": 0}


# ============================================================
# 6. 势力面板：按宗主分组的组名与组内次序
# ============================================================
class TestLordGrouping:
    def _row(self, faction, lord_ids):
        from game.ui.panels.faction_panel import FactionRow
        world = _load(_raw())
        return FactionRow.from_faction(faction, world, lord_ids=lord_ids)

    def test_vassal_goes_to_overlord_group(self):
        row = self._row(Faction("0952", "刘备", independent=False,
                                overlord_id="0736", vassal_value=85), ())
        assert row.lord_group == "0736"

    def test_overlord_goes_to_its_own_group_first(self):
        row = self._row(Faction("0736", "董卓"), {"0736"})
        assert row.lord_group == "董卓"
        assert row.is_lord is True

    def test_plain_independent_is_grouped_as_independent(self):
        row = self._row(Faction("0521", "曹操"), {"0736"})
        assert row.lord_group == "独立"
        assert row.is_lord is False
