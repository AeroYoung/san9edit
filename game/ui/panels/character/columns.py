# -*- coding: utf-8 -*-
"""人物面板列定义。"""

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Column:
    key: str
    title: str
    width: int
    anchor: str
    value: Callable[[Any], Any]
    sort_numeric: bool = False


COLUMNS = (
    Column("faction", "势力", 60, "center", lambda r: r.faction_name),
    Column("node",    "所在", 76, "center", lambda r: r.node_name),
    Column("role",    "身份", 48, "center", lambda r: r.role or "—"),
    Column("lead",    "统",   34, "center", lambda r: r.leadership, sort_numeric=True),
    Column("might",   "武",   34, "center", lambda r: r.might,      sort_numeric=True),
    Column("int",     "智",   34, "center", lambda r: r.intelligence, sort_numeric=True),
    Column("pol",     "政",   34, "center", lambda r: r.politics,   sort_numeric=True),
    Column("cha",     "魅",   34, "center", lambda r: r.charisma,   sort_numeric=True),
)

NAME_COLUMN = Column("name", "姓名", 110, "w", lambda r: r.display_name)

COLUMN_INDEX = {c.key: c for c in COLUMNS}
COLUMN_INDEX["name"] = NAME_COLUMN