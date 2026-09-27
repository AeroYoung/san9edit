# -*- coding: utf-8 -*-
"""外官：官名生成规则（§3.2 / §3.3 / §3.4）+ World 查询 + 剧本加载（§3.1 / §4）。"""

from game.core.official_title import (
    RANK_CITY, RANK_COUNTY, RANK_STATE, city_title, county_title, make_title,
    rank_of, state_title,
)
from game.core.scenario import ScenarioLoader
from game.core.scenario_writer import ScenarioWriter


class _MockGeo:
    """最小 geo_data：一个县点 + 一条郡界（给 _build_region_names 用）。"""
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
        self.shapes_line = [
            {"properties": {"郡id": "1303", "郡名": "陈留郡", "州名": "兖州"}},
        ]


def _raw(officials=None):
    raw = {
        "version": 2, "id": "test", "name": "测试", "desc": "",
        "start": {"year": 190, "month": 1, "xun": 1},
        "player_faction": "0521",
        "factions": {"0521": {"name": "曹操", "color": "#2928EF",
                              "prestige": 1000, "stance": 0}},
        "characters": {"0521": {"faction": "0521", "node": "130301",
                                "location": "130301", "role": "君主"}},
        "nodes": {"130301": {"owner": "0521", "troops": 8000,
                             "gold": 1000, "food": 20000}},
    }
    if officials is not None:
        raw["officials"] = officials
    return raw


# ============================================================
# 官名规则
# ============================================================
def test_state_title():
    assert state_title("07", "司州") == "司隶校尉"          # 司州特例
    assert state_title("04", "荆州", {"02"}) == "荆州刺史"
    assert state_title("02", "冀州", {"02"}) == "冀州牧"
    assert state_title("08", "徐州", {"08", "11"}) == "徐州牧"


def test_county_title():
    assert county_title("河南尹") == "河南尹"               # 尹：原样
    assert county_title("京兆尹") == "京兆尹"
    assert county_title("蜀郡属国") == "蜀郡属国都尉"        # 属国
    assert county_title("中山国") == "中山相"               # 国：前缀 ≥ 2 字
    assert county_title("常山国") == "常山相"
    assert county_title("赵国") == "赵国相"                 # 国：前缀 1 字
    assert county_title("颍川郡") == "颍川太守"
    assert county_title("东郡") == "东郡太守"               # 郡：前缀 1 字保留「郡」
    assert county_title("蜀郡") == "蜀郡太守"


def test_city_title():
    assert city_title("阳翟", "城", 4) == "阳翟令"
    assert city_title("长安", "城", 1) == "长安令"
    # 去「县」只在**前缀 ≥ 2 字**时做（与郡 / 国同一条守卫）
    assert city_title("樊县", "城", 9) == "樊县长"      # §3.4 示例
    assert city_title("范县", "城", 9) == "范县长"
    assert city_title("邺县", "城", 2) == "邺县令"
    assert city_title("平原", "城", 4) == "平原令"
    assert city_title("玉门关", "关隘", 4) == "玉门关都尉"
    assert city_title("武关", "关隘", 4) == "武关都尉"
    assert city_title("桥门", "关隘", 10) == "桥门障尉"     # level ≥ 6 → 障尉
    assert city_title("瓜里津", "渡口", 5) == "瓜里津长"
    assert city_title("界桥", "渡口", 5) == "界桥津长"
    assert city_title("棘津城", "渡口", 5) == "棘津城津长"


def test_rank_and_dispatch():
    assert rank_of("07") == RANK_STATE
    assert rank_of("0707") == RANK_COUNTY
    assert rank_of("070701") == RANK_CITY
    assert rank_of("070") is None
    assert make_title("04", state_name="荆州") == "荆州刺史"
    assert make_title("0407", county_name="南阳郡") == "南阳太守"
    assert make_title("040701", city_name="宛县", level=2) == "宛县令"


# ============================================================
# 加载与查询
# ============================================================
def test_load_officials_and_queries():
    world = ScenarioLoader.from_dict(_raw({
        "13":   {"name": "兖州刺史", "character_id": "0521", "rank": "州"},
        "1303": {"name": "陈留太守", "character_id": "0521", "rank": "郡"},
        "130301": {"name": "陈留令", "character_id": "0521", "rank": "县"},
    }), _MockGeo())

    assert len(world.officials) == 3
    assert world.official_of("13")["name"] == "兖州刺史"
    assert world.official_of("9999") is None
    assert world.official_of("") is None

    # 一人多职：按行政区 id 排序（州 → 郡 → 县）
    got = world.officials_of_character("0521")
    assert [o["region_id"] for o in got] == ["13", "1303", "130301"]
    assert [o["name"] for o in got] == ["兖州刺史", "陈留太守", "陈留令"]
    assert world.officials_of_character("0001") == []

    # 分组标题用：「官名-姓名」
    assert world.official_label("13") == "兖州刺史-曹操"
    assert world.official_label("9999") == ""


def test_officials_dirty_reference_skipped():
    """人物不在 World.characters → warning + 跳过该条（§4）。"""
    world = ScenarioLoader.from_dict(_raw({
        "13": {"name": "兖州刺史", "character_id": "9999", "rank": "州"},
    }), _MockGeo())
    assert world.officials == {}


def test_officials_unknown_region_kept():
    """行政区 id 不在 GeoData → warning 但保留（§4）。"""
    world = ScenarioLoader.from_dict(_raw({
        "99": {"name": "野州刺史", "character_id": "0521", "rank": "州"},
    }), _MockGeo())
    assert world.official_of("99")["name"] == "野州刺史"


def test_legacy_scenario_without_officials():
    """老剧本无 officials 段 → 空 dict，不报错。"""
    world = ScenarioLoader.from_dict(_raw(), _MockGeo())
    assert world.officials == {}
    assert world.official_of("13") is None
    assert world.official_label("13") == ""
    assert world.officials_of_character("0521") == []


def test_serialize_and_diff_include_officials():
    """officials 段参与 serialize / diff（外官可增删改后）。"""
    world = ScenarioLoader.from_dict(_raw({
        "13": {"name": "兖州刺史", "character_id": "0521", "rank": "州"},
    }), _MockGeo())
    data = ScenarioWriter.serialize(world)
    assert data["officials"]["13"] == {"name": "兖州刺史",
                                       "character_id": "0521", "rank": "州"}

    # 改官名 → diff 只出该字段
    world.officials["13"]["name"] = "兖州牧"
    delta = ScenarioWriter.diff(ScenarioWriter.serialize(world), data)
    assert delta["officials"]["13"]["name"] == ("兖州刺史", "兖州牧")

    # 新增一条 → diff 里字段的 old 为 None
    world.officials["1303"] = {"name": "陈留太守",
                               "character_id": "0521", "rank": "郡"}
    delta = ScenarioWriter.diff(ScenarioWriter.serialize(world), data)
    assert delta["officials"]["1303"]["name"] == (None, "陈留太守")


def test_official_command_dirty_and_undo():
    """外官增改删走 Command：dirty 联动 + undo 还原。"""
    from game.core.edit_commands import OfficialRemoveCommand, OfficialSetCommand
    from game.core.edit_session import EditSession

    world = ScenarioLoader.from_dict(_raw({
        "13": {"name": "兖州刺史", "character_id": "0521", "rank": "州"},
    }), _MockGeo())
    session = EditSession(world, ScenarioWriter.serialize(world))
    assert session.is_dirty() is False

    session.execute(OfficialSetCommand(
        "1303", None, {"name": "陈留太守", "character_id": "0521", "rank": "郡"}))
    assert world.official_of("1303")["name"] == "陈留太守"
    assert session.is_dirty() is True

    session.undo()
    assert world.official_of("1303") is None
    assert session.is_dirty() is False

    session.execute(OfficialRemoveCommand("13", world.official_of("13")))
    assert world.official_of("13") is None
    session.undo()
    assert world.official_of("13")["name"] == "兖州刺史"
