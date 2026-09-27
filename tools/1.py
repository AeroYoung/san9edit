# -*- coding: utf-8 -*-
"""预览：按 map.geojson 计算各郡分数 + 分等结果。

用法：
    python tools/preview_county_ranks.py

输出：
    1. 分数直方图（每 10 分一档）
    2. 各郡分数（降序，带 rank 归属）
    3. 金字塔分布汇总（每个 rank 的郡数与占比）
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
sys.path.insert(0, str(ROOT))


def load_cities():
    """返回 [(郡 id, 郡名, 县 level 列表)]。"""
    raw = json.loads((ASSETS / "map.geojson").read_text(encoding="utf-8"))
    counties = []
    for state in raw.get("states", []):
        sname = state.get("name", "")
        for county in state.get("counties", []):
            cid = county["id"]
            cname = f"{sname}·{county.get('name', '')}"
            levels = [c.get("level", 5)
                      for c in county.get("cities", [])]
            counties.append((cid, cname, levels))
    return counties


def score_of(levels):
    """郡分数 = Σ(11 − 县.level)。空郡得 0。"""
    return sum(11 - lv for lv in levels)


def print_histogram(scores):
    print("\n================ 分数直方图（每 10 分一档）================")
    if not scores:
        print("  （无数据）")
        return
    lo, hi = min(scores.values()), max(scores.values())
    band_lo = (lo // 10) * 10
    for band in range(band_lo, hi + 10, 10):
        n = sum(1 for s in scores.values() if band <= s < band + 10)
        bar = "█" * n
        print(f"  [{band:>3}-{band + 9:>3}]  {n:>3}  {bar}")


def print_all_counties(rows, ranks, fixed):
    print("\n================ 各郡分数（降序）================")
    for i, (cid, cname, score) in enumerate(rows, 1):
        if cid in fixed:
            tail = f"[固定 rank {fixed[cid]}]"
        else:
            tail = f"→ rank {ranks.get(cid, '?')}"
        print(f"  {i:>3}. {cid}  {cname:<18} 分数 {score:>3}  {tail}")


def print_distribution(ranks, thresholds, fixed):
    print("\n================ 金字塔分布 ================")
    print("  阈值表（分数 ≥ 阈值 → rank）：")
    for th, rk in thresholds:
        print(f"      ≥ {th:>3} → rank {rk}")
    print("  固定特例：")
    for cid, rk in fixed.items():
        print(f"      {cid} → rank {rk}")

    by_rank = defaultdict(list)
    for cid, rk in ranks.items():
        by_rank[rk].append(cid)
    total = len(ranks)

    print()
    for rk in sorted(by_rank):
        n = len(by_rank[rk])
        pct = n / total * 100 if total else 0
        bar = "█" * n
        print(f"  rank {rk:>2}：{n:>3} 郡（{pct:5.1f}%）  {bar}")
    print(f"  合计：{total} 郡")


def main():
    from game.core.official_title import (
        compute_county_ranks,
        COUNTY_RANK_THRESHOLDS,
        COUNTY_RANK_FIXED,
    )

    counties = load_cities()

    scores = {cid: score_of(levels) for cid, _name, levels in counties}
    ranks = compute_county_ranks(
        [{"id": cid, "level": lv}
         for cid, _name, levels in counties
         for lv in levels]
    )

    rows = sorted(
        [(cid, name, scores[cid]) for cid, name, _lv in counties],
        key=lambda r: (-r[2], r[0]),
    )

    print_histogram(scores)
    print_all_counties(rows, ranks, COUNTY_RANK_FIXED)
    print_distribution(ranks, COUNTY_RANK_THRESHOLDS, COUNTY_RANK_FIXED)


if __name__ == "__main__":
    main()