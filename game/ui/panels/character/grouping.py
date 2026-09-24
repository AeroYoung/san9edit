# -*- coding: utf-8 -*-
"""分组维度 + 嵌套树构建。

priority_name：只对最外层分组生效，把指定的组名提到最前。
（人物面板用来把玩家势力放到第一位）
"""

from .sorting import sort_rows

GROUP_DIMS = {
    "faction": ("势力", lambda r: r.faction_name or "在野"),
    "node":    ("所在", lambda r: r.node_name or "（无）"),
    "role":    ("身份", lambda r: r.role or "（无）"),
    "sex":     ("性别", lambda r: r.sex or "（未知）"),
}


def build_tree(rows, group_keys,
               sort_key=None, sort_desc=False, columns_by_key=None,
               priority_name=None):
    """按 group_keys 递归分组。

    priority_name：若不为 None 且出现在最外层组名里，提到最前。
    递归时不再传递，避免子层误优先。
    """
    if not group_keys:
        if sort_key and columns_by_key:
            return sort_rows(rows, columns_by_key, sort_key, sort_desc)
        return list(rows)

    dim = GROUP_DIMS.get(group_keys[0])
    if dim is None:
        return list(rows)

    _, getter = dim
    buckets = {}
    for r in rows:
        buckets.setdefault(getter(r), []).append(r)

    names = sorted(buckets.keys())
    if priority_name and priority_name in names:
        names.remove(priority_name)
        names.insert(0, priority_name)

    result = []
    for name in names:
        children = build_tree(
            buckets[name], group_keys[1:],
            sort_key=sort_key, sort_desc=sort_desc,
            columns_by_key=columns_by_key,
            # 注意：不传 priority_name → 只有最外层优先
        )
        result.append((name, children))
    return result