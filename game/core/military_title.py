# -*- coding: utf-8 -*-
"""武官官名体系（荣誉头衔）。

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

                                        
"""

from typing import Optional


# {rank: (官名, ...)}。rank 数字越小越尊贵。
MILITARY_TITLES = {
    1:  ("大将军",),
    2:  ("骠骑将军",),
    3:  ("车骑将军",),
    4:  ("卫将军",),
    5:  ("前将军",),
    6:  ("左将军",),
    7:  ("右将军",),
    8:  ("后将军",),
    9:  ("征东将军", "征南将军", "征西将军", "征北将军"),
    10: ("镇东将军", "镇南将军", "镇西将军", "镇北将军"),
    11: ("安东将军", "安南将军", "安西将军", "安北将军"),
    12: ("平东将军", "平南将军", "平西将军", "平北将军"),
    13: ("度辽将军", "伏波将军", "征虏将军"),
    14: ("虎牙将军", "横野将军", "捕虏将军", "奋威将军"),
    15: ("扬威将军", "振威将军", "建威将军", "建武将军"),
    16: ("奋武将军", "破虏将军", "讨虏将军", "荡寇将军"),
    17: ("讨逆将军", "安远将军", "平狄将军", "游击将军"),
    18: ("五官中郎将", "左中郎将", "右中郎将"),
    19: ("虎贲中郎将", "羽林中郎将", "使匈奴中郎将"),
    20: ("北中郎将", "东中郎将", "南中郎将", "西中郎将"),
    21: ("军师中郎将", "建威中郎将", "荡寇中郎将", "横野中郎将"),
    22: ("骑都尉", "奉车都尉", "驸马都尉"),
    23: ("屯骑校尉", "越骑校尉", "步兵校尉", "长水校尉", "射声校尉"),
    24: ("上军校尉", "中军校尉", "下军校尉", "典军校尉",
         "助军左校尉", "助军右校尉", "左校尉", "右校尉"),
    25: ("护乌桓校尉", "护鲜卑校尉", "护羌校尉", "戊己校尉"),
    26: ("军司马",),
    27: ("军假司马",),
    28: ("军曲候",),
    29: ("假候",),
    30: ("屯长",),
    31: ("队率",),
    32: ("什长",),
}

# 分界线：rank < UNIQUE_MAX_RANK 的官名在**同一势力内**唯一
UNIQUE_MAX_RANK = 26

# 反查表（模块导入时构建一次）
_RANK_BY_TITLE = {}
for _r, _titles in MILITARY_TITLES.items():
    for _t in _titles:
        _RANK_BY_TITLE[_t] = _r
del _r, _titles, _t

def all_titles() -> tuple:
    """全部武官官名（按 rank 升序）。"""
    out = []
    for rank in sorted(MILITARY_TITLES):
        out.extend(MILITARY_TITLES[rank])
    return tuple(out)

def rank_of(title) -> Optional[int]:
    """官名 → rank；未知官名 → None。"""
    if not title:
        return None
    return _RANK_BY_TITLE.get(title)

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