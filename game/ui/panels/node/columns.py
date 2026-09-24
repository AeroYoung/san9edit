# -*- coding: utf-8 -*-
"""据点列表的列定义 —— 单一真相源。

加列 / 改宽度 / 改取值只改这里。
#0 列（县名）由 panel.py 单独处理，不在 COLUMNS 里。
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class Column:
    key: str
    title: str
    width: int
    anchor: str
    value: Callable[[Any], Any]
    sort_numeric: bool = False


COLUMNS = (
    Column("state",    "州",   52, "center", lambda r: r.state_name),
    Column("county",   "郡",   62, "center", lambda r: r.county_name),
    Column("level",    "规模", 42, "center", lambda r: r.level, sort_numeric=True),
        Column("type", "类型", 46, "center", lambda r: r.display_type),
    Column("owner",    "势力", 64, "center", lambda r: r.owner_name),
    Column("governor", "主官", 56, "center", lambda r: r.governor_name),
    Column("persons",  "人物", 42, "center", lambda r: r.person_count, sort_numeric=True),
)

# #0 列（县名）也参与排序时用的虚拟列
NAME_COLUMN = Column("name", "县", 110, "w", lambda r: r.name)

COLUMN_INDEX = {c.key: c for c in COLUMNS}
COLUMN_INDEX["name"] = NAME_COLUMN