# -*- coding: utf-8 -*-
"""部队面板（空壳，接入框架，数据留白）。"""

from dataclasses import dataclass

from .list.panel import GenericListPanel
from .list.columns import Column


@dataclass(frozen=True)
class TroopRow:
    name: str
    general: str
    troops: int
    morale: int
    state: str


COLUMNS = (
    Column("general", "主将", 80, "center", lambda r: r.general),
    Column("troops",  "兵力", 70, "center", lambda r: r.troops, sort_numeric=True),
    Column("morale",  "士气", 60, "center", lambda r: r.morale, sort_numeric=True),
    Column("state",   "状态", 80, "center", lambda r: r.state),
)

NAME_COLUMN = Column("name", "部队", 100, "w", lambda r: r.name)


class TroopPanel(GenericListPanel):
    COLUMNS = COLUMNS
    NAME_COLUMN = NAME_COLUMN

    def fetch_rows(self):
        # 空壳：数据留白，后续接入
        return []
