# -*- coding: utf-8 -*-
"""剧本加载：基础数据 + 剧本覆盖 + 应用登场状态 + GeoData 合并。

三层人物加载：
    1. assets/characters.json  → 全量静态数据（五维 / 关系 / 生卒…）
    2. scenarios/*.json        → 剧本覆盖（appeared / faction / node / role / …）
    3. 应用登场状态            → 只读 appeared，不再按年份筛人

World.characters 收全量人物（含未登场 / 穿越人物）——未登场人物也要能被编辑器
查看与编辑，「设为登场」才有着落。登场与否看 Character.appeared，不看生卒年。

约定：势力 id = 君主的人物 id。
"""

import json
import logging

from game.config.constants import DEFAULT_CHARACTERS_PATH
from game.core.faction import Faction
from game.core.character import Character
from game.core.node import Node
from game.core.world import World

logger = logging.getLogger(__name__)


class ScenarioLoader:
    @classmethod
    def load(cls, path, geo_data):
        logger.info("加载剧本：%s", path)
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return cls.from_dict(raw, geo_data)

    @classmethod
    def from_dict(cls, raw, geo_data):
        logger.debug("剧本 id=%s name=%s version=%s",
                     raw.get("id"), raw.get("name"), raw.get("version"))
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
        cls._apply_appeared(world)

        cls._build_nodes_from_geo(world, geo_data)
        cls._build_region_names(world, geo_data)
        cls._apply_node_overrides(world, raw.get("nodes") or {})

        world.bind_factions()   # ★ 注入 nodes 引用（供 Faction.gold/food property）

        logger.info("剧本加载完成：%s", world.summary())
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
            logger.warning("人物基础数据不存在：%s", DEFAULT_CHARACTERS_PATH)
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
        logger.debug("基础人物加载：%d 人（range=%s）",
                     len(world.characters), id_range)

    # ============================================================
    # 人物：第二层 剧本覆盖
    # ============================================================
    @staticmethod
    def _apply_character_overrides(world, overrides):
        for cid, od in overrides.items():
            ch = world.characters.get(cid)
            if ch is None:
                logger.warning("剧本人物 %s 不在基础数据中，已忽略", cid)
                continue
            ch.apply_override(od)
        logger.debug("剧本覆盖：%d 条", len(overrides))


    # ============================================================
    # 人物：第三层 应用登场状态（只读 appeared，不筛人）
    # ============================================================
    @staticmethod
    def _apply_appeared(world):
        """应用登场状态：只读 appeared，**不删人**。

        未登场人物同样留在 World.characters（编辑器要能看到并改他们）。
        appeared 由剧本给出（生成期一次算死）；老剧本无该字段 → 默认 True。
        """
        appeared = 0
        for ch in world.characters.values():
            if not isinstance(ch.appeared, bool):
                # 脏数据（如 "true" / 0）归一化，不静默丢弃
                ch.appeared = bool(ch.appeared)
            if ch.appeared:
                appeared += 1
        logger.debug("应用登场状态：已登场 %d / 共 %d",
                     appeared, len(world.characters))

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
        logger.debug("从地图构建据点：%d", len(world.nodes))

    @staticmethod
    def _apply_node_overrides(world, overrides):
        for nid, ov in overrides.items():
            node = world.nodes.get(nid)
            if node is None:
                continue
            # 动态字段
            if "owner" in ov:
                node.owner = ov["owner"]
            if "troops" in ov:
                node.troops = int(ov["troops"])
            if "gold" in ov:
                node.gold = int(ov["gold"])
            if "food" in ov:
                node.food = int(ov["food"])
            # 静态字段（剧本可覆盖，编辑保存后回写）
            if "type" in ov:
                node.type = ov["type"]
            if "level" in ov:
                node.level = int(ov["level"])
            if "is_capital" in ov:
                node.is_capital = bool(ov["is_capital"])
        logger.debug("据点覆盖：%d 条", len(overrides))