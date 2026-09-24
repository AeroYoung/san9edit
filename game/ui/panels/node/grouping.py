# -*- coding: utf-8 -*-
"""分组维度 + 嵌套树构建（分组正交，按用户点选顺序嵌套）。"""

from .sorting import sort_rows

# key -> (显示名, 取值函数)
GROUP_DIMS = {
    "faction": ("势力", lambda r: r.owner_name or "无主"),
    "state":   ("州",   lambda r: r.state_name or "（无）"),
    "county":  ("郡",   lambda r: r.county_name or "（无）"),
    "type":    ("类型", lambda r: r.type or "（无）"),
}


def build_tree(rows, group_keys,
               sort_key=None, sort_desc=False, columns_by_key=None):
    """按 group_keys 递归分组，最内层按 sort_key 排序。

    返回：
        [(组名, children), ...]
        children 是 [ (子组名, children), ... ] 或 [NodeRow, ...]
    仅靠 children[0] 是否为 tuple 判断层级。
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

    result = []
    for name in sorted(buckets.keys()):
        children = build_tree(
            buckets[name],
            group_keys[1:],
            sort_key=sort_key,
            sort_desc=sort_desc,
            columns_by_key=columns_by_key,
        )
        result.append((name, children))
    return result