# -*- coding: utf-8 -*-
"""列表框架：组头计数、固定组序、叶子行优先排序、登场列排序键。"""

from game.ui.panels.list.columns import Column
from game.ui.panels.list.model import Group
from game.ui.panels.list.grouping import build_tree
from game.ui.panels.list.sorting import sort_rows


class _Row:
    """最小行模型：字段名对齐人物面板（faction_id / id / appeared）。"""

    def __init__(self, name, faction_id, appeared, ruler=False):
        self.name = name
        self.id = name if ruler else None      # 君主：faction_id == id
        self.faction_id = faction_id
        self.appeared = appeared


DIMS = {
    "faction": ("势力", lambda r: r.faction_id),
    "appear":  ("登场", lambda r: "已登场" if r.appeared else "未登场",
                ("已登场", "未登场")),
}
DIMS_FIXED_REVERSED = {
    "appear": ("登场", lambda r: "已登场" if r.appeared else "未登场",
               ("未登场", "已登场")),
}
COLS = {
    "name": Column("name", "姓名", 100, "w", lambda r: r.name),
    "appeared": Column("appeared", "登场", 50, "center",
                       lambda r: "✓" if r.appeared else "✗",
                       sort_numeric=True,
                       sort_key=lambda r: 0 if r.appeared else 1),
}

RULER = lambda r: (0 if r.faction_id == r.id else 1, 0 if r.appeared else 1)


def _rows():
    return [
        _Row("甲", "A", True),
        _Row("乙", "A", False),
        _Row("丙", "A", True),
        _Row("丁", "B", False),
        _Row("戊", "B", False),
    ]


def test_group_title_count_all_levels():
    groups = build_tree(_rows(), DIMS, ["faction"], title_count=True)
    assert [g.label() for g in groups] == ["A（3）", "B（2）"]
    assert [g.title for g in groups] == ["A", "B"]      # title 保持裸名（身份）
    assert [g.count for g in groups] == [3, 2]


def test_group_title_count_nested():
    groups = build_tree(_rows(), DIMS, ["faction", "appear"], title_count=True)
    assert [g.label() for g in groups] == ["A（3）", "B（2）"]
    assert [g.label() for g in groups[0].children] == ["已登场（2）", "未登场（1）"]
    assert groups[0].children[0].leaf_count() == 2


def test_group_label_without_count():
    groups = build_tree(_rows(), DIMS, ["faction"], title_count=False)
    assert [g.label() for g in groups] == ["A", "B"]
    assert all(g.count is None for g in groups)
    assert Group("A", []).label() == "A"


def test_fixed_group_order():
    """固定组序优先于名称排序（不依赖中文串排序的巧合）。"""
    groups = build_tree(_rows(), DIMS, ["appear"])
    assert [g.title for g in groups] == ["已登场", "未登场"]

    reversed_groups = build_tree(_rows(), DIMS_FIXED_REVERSED, ["appear"])
    assert [g.title for g in reversed_groups] == ["未登场", "已登场"]


def test_row_priority_ruler_then_appeared():
    """君主置顶 → 登场在前 → 未登场在后。"""
    rows = [
        _Row("甲", "A", False),
        _Row("乙", "A", True),
        _Row("A", "A", True, ruler=True),
        _Row("丙", "A", False),
    ]
    groups = build_tree(rows, DIMS, ["faction"], row_priority=RULER)
    assert [r.name for r in groups[0].children] == ["A", "乙", "甲", "丙"]


def test_row_priority_keeps_user_sort_as_secondary():
    """优先键为主序，用户列排序为次序（稳定排序）。"""
    rows = [_Row("乙", "A", True), _Row("甲", "A", True), _Row("丙", "A", False)]
    groups = build_tree(rows, DIMS, ["faction"], sort_key="name",
                        columns_by_key=COLS, row_priority=RULER)
    assert [r.name for r in groups[0].children] == ["乙", "甲", "丙"]


def test_row_priority_not_applied_without_faction():
    """不含 faction 的分组路径不排序（保持原顺序）。"""
    rows = [_Row("乙", "A", False), _Row("甲", "A", True)]
    groups = build_tree(rows, DIMS, ["appear"])
    for g in groups:
        assert [r.name for r in g.children] == [r.name for r in g.children]


def test_appeared_column_sort():
    """登场列：升序 ✓ 在前，降序 ✗ 在前。"""
    rows = [_Row("甲", "A", False), _Row("乙", "A", True)]
    asc = sort_rows(rows, COLS, "appeared")
    desc = sort_rows(rows, COLS, "appeared", desc=True)
    assert [r.name for r in asc] == ["乙", "甲"]
    assert [r.name for r in desc] == ["甲", "乙"]
    assert COLS["appeared"].value(rows[0]) == "✗"
