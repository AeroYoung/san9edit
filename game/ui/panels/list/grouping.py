# -*- coding: utf-8 -*-
"""默认维度分组：按 group_keys 递归分组，正交、点选顺序 = 嵌套顺序。"""

from .model import Group
from .sorting import sort_rows


def build_tree(rows, group_dims, group_keys,
               sort_key=None, sort_desc=False, columns_by_key=None,
               priority_name=None):
    """按 group_keys 递归分组，最内层按 sort_key 排序。

    group_dims   : key -> (显示名, 取值函数)
    group_keys   : 从外到内的分组维度
    priority_name: 只对最外层分组生效，把指定组名提到最前（人物面板用）。
                   递归时不传递，避免子层误优先。
    """
    if not group_keys:
        if sort_key and columns_by_key:
            return sort_rows(rows, columns_by_key, sort_key, sort_desc)
        return list(rows)

    dim = group_dims.get(group_keys[0])
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
            buckets[name], group_dims, group_keys[1:],
            sort_key=sort_key, sort_desc=sort_desc,
            columns_by_key=columns_by_key,
            # 不传 priority_name → 只有最外层优先
        )
        result.append(Group(name, children))
    return result
