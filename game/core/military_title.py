# -*- coding: utf-8 -*-
"""武官官名体系（荣誉头衔）。

★ 官名表 MILITARY_TITLES 与唯一性分界 UNIQUE_MAX_RANK 是**可调策略常量**，
  放在 game/config/rules.py；本模块只剩反查与校验逻辑。

- 与行政区外官（core/official_title.py）**独立**：外官是行政职位，武官是荣誉头衔。
- 一人最多一个武官（Character.military_title）。
- Rank 1–25（军司马之上）**势力内唯一**：同一个势力里，一个官名同一时刻
  只能属于一个人；不同势力之间**可以**有同名武官。
  ★ 将来语义（本轮不实现，仅约定）：若两个势力分别有人物持有相同的武官
    title（rank < UNIQUE_MAX_RANK），会导致这两个势力的外交关系严重对立。
- Rank 26–32（军司马及以下）不限量，同一个势力里可以有多人。
- 本轮只做常量表 + 反查，不做编辑、不进序列化。

校验接口（供将来的编辑层用）：
    is_unique(title)                    → 该官名是否属于 rank < UNIQUE_MAX_RANK
    is_title_free(world, title, faction_id, exclude_cid=None)
                                        → 该势力内该官名是否还没被占用
    is_title_free_global(world, title, exclude_cid=None)
                                        → 全剧本内该官名是否还没被占用（跨势力）

系数接口（供 Character.soldiers_cap 用）：
    factor_of_rank(rank)                → 该 rank 的兵力上限系数；未知 → None
    factor_of_title(title)              → 该官名的兵力上限系数；未知 / None → None
                                        （调用方对 None 用 SOLDIERS_CAP_NO_TITLE_FACTOR 兜底）
"""

from typing import Optional

# ★ 官名表与唯一性分界是**可调策略常量**，统一放在 game/config/rules.py
from game.config.rules import MILITARY_TITLES, UNIQUE_MAX_RANK


# 反查表（模块导入时构建一次）
_RANK_BY_TITLE = {}     # 官名 → rank
_FACTOR_BY_RANK = {}    # rank → 系数
for _r, (_f, _titles) in MILITARY_TITLES.items():
    _FACTOR_BY_RANK[_r] = _f
    for _t in _titles:
        _RANK_BY_TITLE[_t] = _r
del _r, _f, _titles, _t


def all_titles() -> tuple:
    """全部武官官名（按 rank 升序）。"""
    out = []
    for rank in sorted(MILITARY_TITLES):
        out.extend(MILITARY_TITLES[rank][1])
    return tuple(out)


def rank_of(title) -> Optional[int]:
    """官名 → rank；未知官名 → None。"""
    if not title:
        return None
    return _RANK_BY_TITLE.get(title)


def factor_of_rank(rank) -> Optional[float]:
    """rank → 兵力上限系数；rank 为 None 或未知 → None。"""
    if rank is None:
        return None
    return _FACTOR_BY_RANK.get(rank)


def factor_of_title(title) -> Optional[float]:
    """官名 → 兵力上限系数；None / 未知官名 → None。"""
    return factor_of_rank(rank_of(title))


def is_unique(title) -> bool:
    """该官名是否「势力内唯一」（rank < UNIQUE_MAX_RANK）。未知官名 → False。

    仅判断官名自身的性质；「在某个具体势力里是否已被占用」见 is_title_free。
    """
    r = _RANK_BY_TITLE.get(title)
    return r is not None and r < UNIQUE_MAX_RANK


def is_title_free(world, title, faction_id, exclude_cid=None) -> bool:
    """该势力内该官名是否还没被占用。

    - 官名 rank ≥ UNIQUE_MAX_RANK → 恒 True（不限量）
    - 否则遍历 world.characters，检查 faction == faction_id 的人里
      是否已有人 military_title == title（exclude_cid 用于「编辑自己时排除自己」）

    本轮不消费（编辑层落地后再用）；此处先备好接口。
    """
    if not is_unique(title):
        return True
    if world is None:
        return True
    for c in world.characters.values():
        if exclude_cid is not None and c.id == exclude_cid:
            continue
        if getattr(c, "faction", None) != faction_id:
            continue
        if getattr(c, "military_title", None) == title:
            return False
    return True


def is_title_free_global(world, title, exclude_cid=None) -> bool:
    """全剧本内该官名是否还没被占用（跨势力）。

    - 官名 rank ≥ UNIQUE_MAX_RANK → 恒 True（不限量）
    - 否则遍历 world.characters，检查是否已有人 military_title == title
      （exclude_cid 用于「编辑自己时排除自己」）

    与 is_title_free 的区别：
        is_title_free         只查同一势力内是否重复
        is_title_free_global  查全剧本（190 剧本生成期采用的口径）
    """
    if not is_unique(title):
        return True
    if world is None:
        return True
    for c in world.characters.values():
        if exclude_cid is not None and c.id == exclude_cid:
            continue
        if getattr(c, "military_title", None) == title:
            return False
    return True


def title_label(title) -> str:
    """展示用文本（当前原样返回，将来可加位阶前缀）。"""
    return title or ""