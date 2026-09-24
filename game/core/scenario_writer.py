# -*- coding: utf-8 -*-
"""World ↔ JSON 序列化 + diff + 增量保存。

serialize：把 World 完整转成 dict（含元字段 + factions / characters / nodes）。
diff：逐实体逐字段对比，只返回变化的字段。
save：raw 原样 + 用户增量写回（未改动字段不出现，保留 raw 原始形态）。
"""

import copy
import json


class ScenarioWriter:
    @staticmethod
    def serialize(world) -> dict:
        """World → 完整 dict。

        含元字段：version / id / name / desc / start / player_faction / character_id_range
        factions 段：不写 gold / food（派生值）
        characters 段：全字段（含 portrait / faction / node / location / role）
        nodes 段：全字段（owner / troops / gold / food / type / level / is_capital）
        """
        result = {
            "version": world.version,
            "id": world.id,
            "name": world.name,
            "desc": world.desc,
            "start": {
                "year": world.year,
                "month": world.month,
                "xun": world.xun,
            },
            "player_faction": world.player_faction_id,
        }

        cr = getattr(world, "character_id_range", None)
        if cr:
            result["character_id_range"] = list(cr)

        result["factions"] = {
            fid: f.to_dict() for fid, f in world.factions.items()
        }
        result["characters"] = {
            cid: c.to_dict() for cid, c in world.characters.items()
        }
        result["nodes"] = {
            nid: n.to_dict() for nid, n in world.nodes.items()
        }
        return result

    @staticmethod
    def diff(current: dict, baseline: dict) -> dict:
        """逐实体逐字段对比。

        返回 {section: {id: {field: (old, new)}}}
        只返回变化的字段。
        section ∈ {"factions", "characters", "nodes"}。元字段不参与 diff。
        """
        result = {}
        for section in ("factions", "characters", "nodes"):
            cur = current.get(section) or {}
            base = baseline.get(section) or {}
            section_diff = {}
            for eid, cur_fields in cur.items():
                base_fields = base.get(eid) or {}
                field_diff = {}
                for field, new_val in cur_fields.items():
                    old_val = base_fields.get(field)
                    if old_val != new_val:
                        field_diff[field] = (old_val, new_val)
                if field_diff:
                    section_diff[eid] = field_diff
            if section_diff:
                result[section] = section_diff
        return result

    @staticmethod
    def save(world, path, raw: dict, baseline_snap: dict):
        """增量保存（§7.3 五步）。

        1. current = serialize(world)
        2. delta = diff(current, baseline_snap)
        3. output = deepcopy(raw)
        4. 用 current 里的新值覆盖 output 对应字段（id 不存在则新建空 dict）
        5. 写 JSON 到 path
        """
        current = ScenarioWriter.serialize(world)
        delta = ScenarioWriter.diff(current, baseline_snap)

        output = copy.deepcopy(raw)
        for section, entities in delta.items():
            out_section = output.setdefault(section, {})
            cur_section = current.get(section) or {}
            for eid, fields in entities.items():
                entry = out_section.setdefault(eid, {})
                cur_entry = cur_section.get(eid) or {}
                for field in fields:
                    entry[field] = cur_entry[field]

        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
