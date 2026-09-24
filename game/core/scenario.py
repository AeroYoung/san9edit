# -*- coding: utf-8 -*-
"""剧本加载：读 JSON + 合并 GeoData，构造 World。

剧本 JSON 结构见 scenarios/default.json。
约定：势力 id = 君主的人物 id。
"""

import json

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

        for fid, fdata in (raw.get("factions") or {}).items():
            world.factions[fid] = cls._build_faction(fid, fdata)

        for cid, cdata in (raw.get("characters") or {}).items():
            world.characters[cid] = cls._build_character(cid, cdata)

        cls._build_nodes_from_geo(world, geo_data)
        cls._apply_node_overrides(world, raw.get("nodes") or {})

        return world

    @staticmethod
    def _build_faction(fid, fdata):
        return Faction(
            fid=fid,
            name=fdata.get("name", fid),
            color=fdata.get("color", "#888888"),
            prestige=fdata.get("prestige", 0),
            gold=fdata.get("gold", 0),
            food=fdata.get("food", 0),
            stance=fdata.get("stance", 0),
        )

    @staticmethod
    def _build_character(cid, cdata):
        return Character(
            cid=cid,
            name=cdata.get("name", cid),
            faction=cdata.get("faction"),
            node=cdata.get("node"),
            leadership=cdata.get("leadership", 50),
            might=cdata.get("might", 50),
            intelligence=cdata.get("intelligence", 50),
            politics=cdata.get("politics", 50),
            charisma=cdata.get("charisma", 50),
        )

    @staticmethod
    def _build_nodes_from_geo(world, geo_data):
        """遍历 geo_data.shapes_point，为每个城/关/津/... 建 Node。

        依赖 shapes_point[i].properties 里有 id/县名/level/type/is_capital。
        """
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