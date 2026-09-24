# -*- coding: utf-8 -*-
"""游戏世界：聚合剧本数据 + 全部据点。

World 不负责加载（由 ScenarioLoader 负责），只做数据容器。
nodes 包含 map.geojson 里的全部据点，剧本只覆盖部分。
"""
from collections import Counter

class World:
    def __init__(self):
        # 元信息
        self.version = 1
        self.id = ""
        self.name = ""
        self.desc = ""
        self.year = 208
        self.month = 1
        self.xun = 1

        # 玩家势力 id（可为 None）
        self.player_faction_id = None

        # 人物 id 加载范围（剧本级过滤，可为 None）
        self.character_id_range = None

        # 数据容器
        self.factions = {}      # id -> Faction
        self.characters = {}    # id -> Character
        self.nodes = {}         # id -> Node
        # 州 / 郡 名字表（由 ScenarioLoader 从 GeoData 填）
        self.state_names = {}     # "01"   -> "并州"
        self.county_names = {}    # "0101" -> "上党郡"

    # ---------- 查询 ----------
    def player_faction(self):
        if self.player_faction_id is None:
            return None
        return self.factions.get(self.player_faction_id)

    def player_ruler(self):
        pf = self.player_faction()
        if pf is None:
            return None
        return self.characters.get(pf.ruler_id)

    def nodes_of(self, faction_id):
        return [n for n in self.nodes.values() if n.owner == faction_id]

    def characters_of(self, faction_id):
        return [c for c in self.characters.values() if c.faction == faction_id]

    def count_nodes_by_owner(self):
        """每个势力拥有的据点数。返回 dict[fid, int]，无主据点不计。"""
        return Counter(n.owner for n in self.nodes.values() if n.owner)

    def count_characters_by_faction(self):
        """每个势力的人物数。返回 dict[fid, int]，无势力人物不计。"""
        return Counter(c.faction for c in self.characters.values() if c.faction)

    def node(self, nid):
        return self.nodes.get(nid)

    def character(self, cid):
        return self.characters.get(cid)

    def faction(self, fid):
        return self.factions.get(fid)

    def state_name(self, sid):
        if not sid:
            return "—"
        return self.state_names.get(sid, sid)

    def county_name(self, cid):
        if not cid:
            return "—"
        return self.county_names.get(cid, cid)

    # ---------- 统计 ----------
    def bind_factions(self):
        """给每个 Faction 注入 nodes dict 引用（供 gold/food property 用）。
        由 ScenarioLoader.from_dict 末尾调用。
        """
        for f in self.factions.values():
            f._nodes_ref = self.nodes

    def add_faction(self, faction):
        """新增势力。只能被 Command 调用，UI 不得直接调。"""
        # TODO(phase2): 实现
        raise NotImplementedError("phase2")

    def remove_faction(self, fid):
        """删除势力。只能被 Command 调用。"""
        # TODO(phase2): 实现
        raise NotImplementedError("phase2")

    def remove_faction_if_empty(self, fid):
        """势力据点归零时删除。供 CompositeCommand 级联调用。"""
        # TODO(phase2): 实现
        raise NotImplementedError("phase2")

    def summary(self):
        return (f"{self.name} "
                f"({self.year}年{self.month}月) — "
                f"势力 {len(self.factions)} / "
                f"人物 {len(self.characters)} / "
                f"据点 {len(self.nodes)}")

    def __repr__(self):
        return f"<World {self.id!r} {self.summary()}>"