# -*- coding: utf-8 -*-
"""剧本加载：基础数据 + 剧本覆盖 + 按年份筛选 + GeoData 合并。

三层人物加载：
    1. assets/characters.json  → 全量静态数据（五维 / 关系 / 生卒…）
    2. scenarios/*.json        → 剧本覆盖（faction / node / role / …）
    3. 按年份筛选              → 只保留该年满 16 岁且已出生未死的人

约定：势力 id = 君主的人物 id。
"""

import json

from game.config.constants import DEFAULT_CHARACTERS_PATH
from game.core.faction import Faction
from game.core.character import Character
from game.core.node import Node
from game.core.world import World


class ScenarioLoader:
    @classmethod
    def load(cls, path, geo_data):
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return cls.from_dict(raw, geo_data)

    @classmethod
    def from_dict(cls, raw, geo_data):
        world = World()

        world.version = int(raw.get("version", 1))
        world.id = raw.get("id", "")
        world.name = raw.get("name", "")
        world.desc = raw.get("desc", "")

        start = raw.get("start") or {}
        world.year = int(start.get("year", 0))
        world.month = int(start.get("month", 0))
        world.xun = int(start.get("xun", 0))

        world.player_faction_id = raw.get("player_faction")
        world.character_id_range = raw.get("character_id_range")

        for fid, fdata in (raw.get("factions") or {}).items():
            world.factions[fid] = cls._build_faction(fid, fdata)

        # ---- ★ 三层人物加载 ----
        cls._load_base_characters(world, raw.get("character_id_range"))
        cls._apply_character_overrides(world, raw.get("characters") or {})
        cls._filter_by_year(world, world.year)

        cls._build_nodes_from_geo(world, geo_data)
        cls._build_region_names(world, geo_data)
        cls._apply_node_overrides(world, raw.get("nodes") or {})

        world.bind_factions()   # ★ 注入 nodes 引用（供 Faction.gold/food property）

        return world

    # ============================================================
    # 势力
    # ============================================================
    @staticmethod
    def _build_faction(fid, fdata):
        return Faction.from_dict(fid, fdata)

    # ============================================================
    # 人物：第一层 基础数据
    # ============================================================
    @classmethod
    def _load_base_characters(cls, world, id_range=None):
        if not DEFAULT_CHARACTERS_PATH.is_file():
            return
        with open(DEFAULT_CHARACTERS_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if id_range:
            lo, hi = int(id_range[0]), int(id_range[1])
        else:
            lo, hi = 1, 9999   # 默认不过滤

        for cid, cdata in (raw.get("characters") or {}).items():
            try:
                n = int(cid)
            except ValueError:
                continue
            if not (lo <= n <= hi):
                continue
            world.characters[cid] = Character.from_dict(cid, cdata)

    # ============================================================
    # 人物：第二层 剧本覆盖
    # ============================================================
    @staticmethod
    def _apply_character_overrides(world, overrides):
        for cid, od in overrides.items():
            ch = world.characters.get(cid)
            if ch is None:
                print(f"[Scenario] 警告：剧本人物 {cid} 在基础数据中不存在，已忽略")
                continue
            ch.apply_override(od)
            
    # ============================================================
    # 人物：第三层 按年份筛选（满 16 岁 + 已出生 + 未死）
    # ============================================================
    @staticmethod
    def _filter_by_year(world, year):
        if not year:
            return
        survivors = {}
        for cid, ch in world.characters.items():
            if ch.birth_year:
                if year - ch.birth_year < 16:
                    continue
                if ch.death_year and year > ch.death_year:
                    continue
            else:
                if ch.appear_year and ch.appear_year > year:
                    continue
            survivors[cid] = ch
        world.characters = survivors

    # ============================================================
    # 以下三个方法保持不变（原样照抄）
    # ============================================================
    @staticmethod
    def _build_region_names(world, geo_data):
        if geo_data is None:
            return
        for feat in getattr(geo_data, "shapes_line", []):
            props = feat.get("properties") or {}
            cid = props.get("郡id")
            if not cid:
                continue
            cname = props.get("郡名")
            sname = props.get("州名")
            if cname:
                world.county_names[cid] = cname
            if sname:
                world.state_names[cid[:2]] = sname

    @staticmethod
    def _build_nodes_from_geo(world, geo_data):
        if geo_data is None:
            return
        for feat in getattr(geo_data, "shapes_point", []):
            props = feat.get("properties") or {}
            geom = feat.get("geometry") or {}
            coords = geom.get("coordinates") or []
            if len(coords) < 2:
                continue
            nid = props.get("id")
            if not nid:
                continue
            world.nodes[nid] = Node(
                nid=nid,
                name=props.get("县名", ""),
                coords=(coords[0], coords[1]),
                type_=props.get("type", "城"),
                level=props.get("level", 5),
                is_capital=props.get("is_capital", False),
            )

    @staticmethod
    def _apply_node_overrides(world, overrides):
        for nid, ov in overrides.items():
            node = world.nodes.get(nid)
            if node is None:
                continue
            if "owner" in ov:
                node.owner = ov["owner"]
            if "troops" in ov:
                node.troops = int(ov["troops"])
            if "gold" in ov:
                node.gold = int(ov["gold"])
            if "food" in ov:
                node.food = int(ov["food"])