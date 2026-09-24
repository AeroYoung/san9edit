# -*- coding: utf-8 -*-
"""分组维度 + 嵌套树构建。"""

from .sorting import sort_rows

GROUP_DIMS = {
    "faction": ("势力", lambda r: r.faction_name or "在野"),
    "node":    ("所在", lambda r: r.node_name or "（无）"),
    "role":    ("身份", lambda r: r.role or "（无）"),
    "sex":     ("性别", lambda r: r.sex or "（未知）"),
}


def build_tree(rows, group_keys,
               sort_key=None, sort_desc=False, columns_by_key=None):
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

    result = []
    for name in sorted(buckets.keys()):
        children = build_tree(
            buckets[name], group_keys[1:],
            sort_key=sort_key, sort_desc=sort_desc,
            columns_by_key=columns_by_key,
        )
        result.append((name, children))
    return result