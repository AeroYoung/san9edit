# -*- coding: utf-8 -*-
"""默认维度分组：按 group_keys 递归分组，正交、点选顺序 = 嵌套顺序。"""

from .model import Group
from .sorting import sort_rows


def build_tree(rows, group_dims, group_keys,
               sort_key=None, sort_desc=False, columns_by_key=None,
               priority_name=None, row_priority=None, title_count=False):
    """按 group_keys 递归分组，最内层按 sort_key 排序。

    group_dims    : key -> (显示名, 取值函数) 或 (显示名, 取值函数, 固定组序)
    group_keys    : 从外到内的分组维度
    priority_name : 只对最外层分组生效，把指定组名提到最前（人物面板用）。
                    递归时不传递，避免子层误优先。
    row_priority  : 叶子行的优先排序键（如人物面板的「君主置顶 + 登场在前」）。
                    在用户列排序**之后**做稳定排序 → 优先键为主序、列排序为次序。
                    递归时逐层传递（最内层才真正生效）。
    title_count   : True → 每个组头带叶子行数（Group.count），显示成「组名（N）」
    """
    if not group_keys:
        return _sort_leaf(rows, sort_key, sort_desc, columns_by_key, row_priority)

    dim = group_dims.get(group_keys[0])
    if dim is None:
        return list(rows)

    _, getter = dim[0], dim[1]
    fixed_order = dim[2] if len(dim) > 2 else ()

    buckets = {}
    for r in rows:
        buckets.setdefault(getter(r), []).append(r)

    names = sorted(buckets.keys())
    if fixed_order:
        # 固定组序：列出的组按声明顺序在前，未列出的按名称排在后面
        rank = {n: i for i, n in enumerate(fixed_order)}
        names.sort(key=lambda n: (rank.get(n, len(rank)), n))
    if priority_name and priority_name in names:
        names.remove(priority_name)
        names.insert(0, priority_name)

    result = []
    for name in names:
        children = build_tree(
            buckets[name], group_dims, group_keys[1:],
            sort_key=sort_key, sort_desc=sort_desc,
            columns_by_key=columns_by_key,
            # 不传 priority_name → 只有最外层优先
            row_priority=row_priority, title_count=title_count,
        )
        group = Group(name, children)
        if title_count:
            group.count = group.leaf_count()
        result.append(group)
    return result


def _sort_leaf(rows, sort_key, sort_desc, columns_by_key, row_priority):
    """叶子行排序：先用户列排序，再按 row_priority 稳定排序（优先生效）。"""
    if sort_key and columns_by_key:
        rows = sort_rows(rows, columns_by_key, sort_key, sort_desc)
    if row_priority:
        rows = sorted(rows, key=row_priority)
    return list(rows)
