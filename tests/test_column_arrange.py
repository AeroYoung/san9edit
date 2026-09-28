# -*- coding: utf-8 -*-
"""列排列规则（columns.arrange_column_keys）—— §8.3 第 26 条。

用户在设置窗口存过列顺序后，PANEL_COLUMNS[k].order 是**当时全部列**的快照；
框架后来在 COLUMNS 里加的新列不在里面。这些新列必须插在**声明位置附近**，
而不是被一律甩到末尾。
"""

from game.ui.panels.list.columns import arrange_column_keys


# character 面板的声明顺序。official / soldiers 是用户存过列顺序之后才加的列。
DECLARED = ["faction", "node", "role", "official", "lead",
            "might", "int", "pol", "cha", "soldiers", "appeared"]

# 用户设置窗口里存下的 order（当时还没有 official / soldiers）
SAVED = ["faction", "node", "role", "lead", "might", "int", "pol", "cha"]


def test_no_config_falls_back_to_declaration_order():
    assert arrange_column_keys(DECLARED) == DECLARED
    assert arrange_column_keys(DECLARED, []) == DECLARED


def test_new_columns_land_near_declared_position_not_at_end():
    """核心回归：official 插在 role 后、soldiers 插在 cha 后。"""
    assert arrange_column_keys(DECLARED, SAVED) == DECLARED


def test_user_order_wins_over_declaration_order():
    """用户把「登场」拖到最前 → 尊重；新列仍跟着各自的声明前邻走。"""
    order = ["appeared", "faction", "node", "role", "lead",
             "might", "int", "pol", "cha"]
    assert arrange_column_keys(DECLARED, order) == [
        "appeared", "faction", "node", "role", "official", "lead",
        "might", "int", "pol", "cha", "soldiers",
    ]


def test_new_column_before_any_stated_column_goes_first():
    """order 只定了 cha → cha 之前的列按声明序排最前，cha 之后照旧。"""
    result = arrange_column_keys(DECLARED, ["cha"])
    assert result == [
        "faction", "node", "role", "official", "lead", "might",
        "int", "pol", "cha", "soldiers", "appeared",
    ]


def test_unknown_and_duplicate_keys_ignored():
    assert arrange_column_keys(DECLARED, ["faction", "faction", "gone",
                                          "node"]) == DECLARED


def test_deleted_column_dropped_from_stale_config():
    """列被删掉后，旧配置里还留着它的 key → 忽略，不报错。"""
    assert arrange_column_keys(["a", "b", "d"], ["a", "b", "c", "d"]) == \
        ["a", "b", "d"]


def test_result_is_always_a_permutation_of_declared():
    for order in ([], SAVED, ["pol", "cha", "gone"], list(reversed(DECLARED))):
        result = arrange_column_keys(DECLARED, order)
        assert sorted(result) == sorted(DECLARED)
