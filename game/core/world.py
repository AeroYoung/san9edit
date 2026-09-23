# -*- coding: utf-8 -*-
"""游戏世界：聚合剧本数据 + 全部据点。

World 不负责加载（由 ScenarioLoader 负责），只做数据容器。
nodes 包含 map.geojson 里的全部据点，剧本只覆盖部分。
"""


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

        # 数据容器
        self.factions = {}      # id -> Faction
        self.characters = {}    # id -> Character
        self.nodes = {}         # id -> Node

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

    def node(self, nid):
        return self.nodes.get(nid)

    def character(self, cid):
        return self.characters.get(cid)

    def faction(self, fid):
        return self.factions.get(fid)

    # ---------- 统计 ----------
    def summary(self):
        return (f"{self.name} "
                f"({self.year}年{self.month}月) — "
                f"势力 {len(self.factions)} / "
                f"人物 {len(self.characters)} / "
                f"据点 {len(self.nodes)}")

    def __repr__(self):
        return f"<World {self.id!r} {self.summary()}>"