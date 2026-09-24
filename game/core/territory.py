# -*- coding: utf-8 -*-
"""势力控制范围：按郡统计控制力，判定主导/主要势力。

势力值（控制力）算法：
    单个据点权重 = (11 - level)          # level 1→10 分，level 10→1 分
    郡治据点再 ×CAPITAL_BONUS            # 郡治额外加成
    势力 F 在郡内的控制力 = Σ 权重(归 F 的据点)
    郡内总控制力          = Σ 权重(全部据点，含无主)
    势力 F 的势力值       = 控制力_F / 总控制力

分档：
    ratio > 0.8         → 主导势力（dominant）
    0.5 < ratio ≤ 0.8   → 主要势力（major）
    否则                 → 无

"主导必然也是主要"，所以只记一个 owner_id + ratio。
"""

from dataclasses import dataclass

CAPITAL_BONUS = 2.0


@dataclass
class CountyStat:
    county_id: str
    owner_id: str | None    # 控制力最高的有主势力（可能 <50%）
    ratio: float            # owner_id 的势力值（含无主据点作分母）

    @property
    def is_dominant(self) -> bool:
        return self.owner_id is not None and self.ratio > 0.8

    @property
    def is_major(self) -> bool:
        return self.owner_id is not None and self.ratio > 0.5


def compute_county_stats(world):
    """遍历 world.nodes，按郡聚合控制力。

    返回 {county_id: CountyStat}。county_id 为四位字符串。
    """
    if world is None:
        return {}

    buckets = {}    # {county_id: {owner_id_or_None: power}}
    for node in world.nodes.values():
        cid = node.county_id
        w = float(11 - node.level)
        if node.is_capital:
            w *= CAPITAL_BONUS
        bucket = buckets.setdefault(cid, {})
        bucket[node.owner] = bucket.get(node.owner, 0.0) + w

    stats = {}
    for cid, bucket in buckets.items():
        total = sum(bucket.values())
        if total <= 0:
            stats[cid] = CountyStat(cid, None, 0.0)
            continue
        owned = {k: v for k, v in bucket.items() if k is not None}
        if not owned:
            stats[cid] = CountyStat(cid, None, 0.0)
            continue
        owner_id, owner_power = max(owned.items(), key=lambda kv: kv[1])
        stats[cid] = CountyStat(cid, owner_id, owner_power / total)
    return stats