# -*- coding: utf-8 -*-
"""就地刷新（GenericListPanel._reconcile）回归测试。

重点覆盖：子分组消失时，组内行的 item 会被连带删除 —— 这些行在新结构里还存在
（只是换了父组），若登记表不清理就会抛 TclError: Item xxx not found。

需要 Tk；无显示环境自动跳过。
"""

from dataclasses import dataclass

import pytest
import tkinter as tk

from game.ui.panels.list.columns import Column
from game.ui.panels.list.panel import GenericListPanel


@dataclass(frozen=True)
class _Row:
    id: str
    kind: str
    ok: bool


class _Panel(GenericListPanel):
    COLUMNS = (Column("ok", "状态", 40, "center",
                      lambda r: "✓" if r.ok else "✗"),)
    NAME_COLUMN = Column("name", "名称", 80, "w", lambda r: r.id)
    GROUP_DIMS = {
        "kind": ("类别", lambda r: r.kind),
        "ok":   ("状态", lambda r: "✓" if r.ok else "✗", ("✓", "✗")),
    }
    DEFAULT_GROUP = ()
    KEEP_VIEW_ON_EDIT = True

    def __init__(self, master, rows):
        self._rows = rows          # 不拷贝：测试直接改这个 list 模拟数据源变化
        super().__init__(master, object())

    def fetch_rows(self):
        return list(self._rows)

    def row_key(self, row):
        return row.id


@pytest.fixture(scope="module")
def root():
    """整个模块共用一个 Tk 根：反复 Tk() + destroy 会让 Tcl 解释器提前终结
    （invalid command name "tcl_findLibrary"）。"""
    try:
        r = tk.Tk()
    except tk.TclError as e:
        pytest.skip("无显示环境，跳过 Tk 测试：%s" % e)
    r.withdraw()
    yield r
    try:
        r.destroy()
    except tk.TclError:
        pass


def _group_by(panel, keys):
    panel.group_bar._selected[:] = list(keys)
    panel.refresh()


def _shape(panel):
    """树形结构快照（递归）：叶子 → 行名文本，组 → [组头文本, [子项...]]。"""
    def walk(item):
        kids = panel.tree.get_children(item)
        text = panel.tree.item(item, "text")
        return [text, [walk(k) for k in kids]] if kids else text
    return [walk(i) for i in panel.tree.get_children("")]


def test_reconcile_keeps_items_and_registry(root):
    rows = [_Row("a1", "A", True), _Row("a2", "A", False), _Row("b1", "B", True)]
    panel = _Panel(root, rows)
    _group_by(panel, ["kind", "ok"])
    assert _shape(panel) == [
        ["A（2）", [["✓（1）", ["a1"]], ["✗（1）", ["a2"]]]],
        ["B（1）", [["✓（1）", ["b1"]]]],
    ]

    item_a1 = panel._row_items["a1"]
    rows[1] = _Row("a2", "A", True)          # a2 转 ✓ → A 的「✗」子组消失
    panel.refresh(keep_view=True)

    assert _shape(panel) == [
        ["A（2）", [["✓（2）", ["a1", "a2"]]]],
        ["B（1）", [["✓（1）", ["b1"]]]],
    ]
    assert panel._row_items["a1"] == item_a1          # 未重建
    # 登记表与树一致：无失效 item 残留
    for item in panel._item_keys:
        assert panel.tree.exists(item)
    # 4 个组头（A / A>✓ / B / B>✓）+ 3 行 —— 消失的「A>✗」不应留下残留登记
    assert len(panel._item_keys) == len(panel._row_items) + 4


def test_reconcile_updates_row_values(root):
    rows = [_Row("a1", "A", True), _Row("a2", "A", True)]
    panel = _Panel(root, rows)
    _group_by(panel, ["kind"])

    item_a1 = panel._row_items["a1"]
    rows[0] = _Row("a1", "A", False)
    panel.refresh(keep_view=True)

    assert panel.tree.set(item_a1, "ok") == "✗"
    assert panel._row_items["a1"] == item_a1


def test_reconcile_group_header_count(root):
    rows = [_Row("a1", "A", True), _Row("a2", "A", True)]
    panel = _Panel(root, rows)
    _group_by(panel, ["kind"])
    assert _shape(panel) == [["A（2）", ["a1", "a2"]]]

    rows.append(_Row("a3", "A", True))
    panel.refresh(keep_view=True)
    assert _shape(panel) == [["A（3）", ["a1", "a2", "a3"]]]
    assert panel._item_keys[panel._row_items["a3"]] == ("row", "a3")


def test_reconcile_falls_back_when_tree_empty(root):
    panel = _Panel(root, [_Row("a1", "A", True)])
    _group_by(panel, ["kind"])
    for item in panel.tree.get_children(""):
        panel.tree.delete(item)
    panel._item_keys.clear()
    assert panel.refresh(keep_view=True) is None      # 不抛异常
    assert _shape(panel) == [["A（1）", ["a1"]]]
