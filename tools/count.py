# -*- coding: utf-8 -*-
"""统计各势力按「最大带兵上限」的兵力总和。

口径：
    对每个 **已登场** 且 **有势力** 的人物，取 Character.soldiers_cap
    （= 按统率曲线 × 武官 rank 系数，常量见 config/rules.py），按势力求和。
    「在野」单列一行。

运行：
    python tools/count_max_troops.py [剧本路径]
    不带参数 → 用 constants.DEFAULT_SCENARIO_PATH
"""
import json
import sys
from pathlib import Path

# tools/ 不在包里，手动把项目根加入 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game.config.constants import (  # noqa: E402
    DEFAULT_MAP_PATH, DEFAULT_SCENARIO_PATH,
)
from game.core.scenario import ScenarioLoader  # noqa: E402
from game.map.geo_data import GeoData  # noqa: E402


def main():
    scenario_path = Path(sys.argv[1]) if len(sys.argv) > 1 \
        else DEFAULT_SCENARIO_PATH

    with open(scenario_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    geo = GeoData.from_file(DEFAULT_MAP_PATH)
    world = ScenarioLoader.from_dict(raw, geo)

    totals = {}   # faction_id -> 兵力上限总和
    counts = {}   # faction_id -> 参与统计的人数
    free_count = 0
    free_total = 0

    for ch in world.characters.values():
        if not ch.appeared:
            continue
        cap = ch.soldiers_cap
        if not ch.faction:
            free_count += 1
            free_total += cap
            continue
        totals[ch.faction] = totals.get(ch.faction, 0) + cap
        counts[ch.faction] = counts.get(ch.faction, 0) + 1

    rows = []
    for fid, total in totals.items():
        f = world.faction(fid)
        name = f.name if f is not None else fid
        rows.append((total, name, counts[fid], fid))
    rows.sort(reverse=True)     # 兵力降序

    print("=" * 56)
    print(f"{'势力':<10}{'兵力上限总和':>16}{'人数':>8}   势力 id")
    print("-" * 56)
    grand = 0
    for total, name, n, fid in rows:
        print(f"{name:<10}{total:>16,}{n:>8}   {fid}")
        grand += total
    print("-" * 56)
    print(f"{'合计':<10}{grand:>16,}{sum(counts.values()):>8}")
    print(f"{'（在野）':<10}{free_total:>16,}{free_count:>8}")
    print("=" * 56)


if __name__ == "__main__":
    main()