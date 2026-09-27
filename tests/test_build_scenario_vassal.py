# -*- coding: utf-8 -*-
"""剧本生成脚本的附庸相关规则（跑真实 map.geojson）。

覆盖：
    TERRITORY_CITIES   刘备 = 平原 / 漯阴 / 高唐（需求 §3.6）
    DONGZHUO_VASSALS   董卓名单据点解析
    official_from_territory  含郡治 → 郡太守；否则 → 第一个「城」的县令
"""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

_spec = importlib.util.spec_from_file_location(
    "build_scenario_190", ROOT / "tools" / "build_scenario_190.py")
B = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(B)


@pytest.fixture(scope="module")
def map_idx():
    return B.build_map_index()


def _city(map_idx, name):
    return map_idx["city_by_name"][name][0]


class TestLiuBeiTerritory:
    def test_only_three_counties(self, map_idx):
        """刘备只占平原郡三县：平原 + 漯阴 + 高唐（需求 §3.6）。"""
        spec = {"id": "0952", "name": "刘备", "spec_name": "刘备",
                "capital": "060101", "rank": "郡"}
        assert B.pick_territory(spec, map_idx, {}) == [
            _city(map_idx, "平原"), _city(map_idx, "漯阴"),
            _city(map_idx, "高唐"),
        ]

    def test_counties_are_in_pingyuan(self, map_idx):
        for name in B.TERRITORY_CITIES["刘备"]:
            assert map_idx["city"][_city(map_idx, name)]["county"] == "0601"


class TestDongzhuoVassalTerritory:
    def test_all_listed_cities_resolve(self, map_idx):
        for name, cities in B.DONGZHUO_VASSALS.items():
            resolved = B.resolve_city_names(cities, map_idx, name)
            assert len(resolved) == len(cities), name

    def test_huji_is_a_pass(self, map_idx):
        info = map_idx["city"][_city(map_idx, "伊阙关")]
        assert info["type"] == "关隘"


class TestOfficialFromTerritory:
    def test_county_seat_means_taishou(self, map_idx):
        """段煨据弘农（弘农郡郡治）→ 弘农太守。"""
        spec = {"name": "段煨", "cities": B.resolve_city_names(
            B.DONGZHUO_VASSALS["段煨"], map_idx, "段煨")}
        assert B.official_from_territory(spec, map_idx) == ("0705", "弘农太守")

    def test_no_county_seat_means_xianling(self, map_idx):
        """李傕只据东垣一县 → 东垣令。"""
        spec = {"name": "李傕", "cities": B.resolve_city_names(
            B.DONGZHUO_VASSALS["李傕"], map_idx, "李傕")}
        region, title = B.official_from_territory(spec, map_idx)
        assert region == _city(map_idx, "东垣")
        assert title == "东垣令"

    def test_skips_pass_seat(self, map_idx):
        """胡轸治所是关隘（伊阙关）→ 取第一个「城」梁县 → 梁县令。"""
        spec = {"name": "胡轸", "cities": B.resolve_city_names(
            B.DONGZHUO_VASSALS["胡轸"], map_idx, "胡轸")}
        region, title = B.official_from_territory(spec, map_idx)
        assert region == _city(map_idx, "梁县")
        assert title == "梁县令"

    def test_empty_territory(self, map_idx):
        assert B.official_from_territory({"cities": []}, map_idx) == (None, "")


class TestDeriveVassals:
    def _factions(self):
        def spec(fid, name, rank, capital):
            return {"id": fid, "name": name, "spec_name": name, "rank": rank,
                    "capital": capital, "independent": True,
                    "overlord_id": None, "vassal_value": 0}
        return {
            "0736": spec("0736", "董卓", "州", "070701"),
            "0201": spec("0201", "韩馥", "州", "020101"),
            "0203": spec("0203", "袁绍", "郡", "020801"),
            "0203b": spec("0203b", "张燕", "郡", "020301"),
            "0521": spec("0521", "曹操", "郡", "090201"),
            "0592": spec("0592", "段煨", "县", "070307"),
        }

    def test_mu_state_makes_vassal_but_lord_stays_independent(self):
        factions = self._factions()
        officials = {
            "02": {"name": "冀州牧", "character_id": "0201", "rank": "州"},
            "07": {"name": "司隶校尉", "character_id": "0736", "rank": "州"},
            "09": {"name": "兖州刺史", "character_id": "0903", "rank": "州"},
        }
        B.derive_vassals(factions, officials)
        assert factions["0203b"]["independent"] is False
        assert factions["0203b"]["overlord_id"] == "0201"
        assert factions["0203b"]["vassal_value"] == 10
        # 袁绍 / 曹操 强制独立
        assert factions["0203"]["independent"] is True
        assert factions["0521"]["independent"] is True
        # 董卓名单：覆盖自动规则，附庸值 85
        assert factions["0592"]["overlord_id"] == "0736"
        assert factions["0592"]["vassal_value"] == 85
        assert factions["0736"]["independent"] is True

    def test_zcishi_state_keeps_its_counties_independent(self):
        factions = self._factions()
        officials = {
            "02": {"name": "冀州刺史", "character_id": "0201", "rank": "州"},
        }
        B.derive_vassals(factions, officials)
        assert factions["0203b"]["independent"] is True
        assert factions["0203b"]["overlord_id"] is None
