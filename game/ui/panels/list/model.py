# -*- coding: utf-8 -*-
"""分组树节点。

分组树是「组」与「叶子行」的嵌套结构：
    Group(children=[Group, ...])   嵌套组
    Group(children=[Row, ...])     叶子组（组内是数据行）
"""

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


@dataclass
class Group:
    title: str
    children: List[Any]                    # list[Group] 或 list[Row]
    tags: Tuple[str, ...] = ("group",)     # 组头的 Treeview tag
    open: bool = True                      # 组头初始是否展开
    row_tag: Optional[str] = None          # 组内数据行的 tag（可选）
    count: Optional[int] = None            # 叶子行数（None = 组头不显示计数）

    def has_subgroups(self) -> bool:
        """children 首元素是 Group 则为嵌套组，否则为叶子行。"""
        return bool(self.children) and isinstance(self.children[0], Group)

    def leaf_count(self) -> int:
        """该组下的叶子行数（递归）。"""
        if self.has_subgroups():
            return sum(c.leaf_count() for c in self.children)
        return len(self.children)

    def label(self) -> str:
        """组头显示文本：有计数 →「组名（N）」，否则原样。

        title 本身不带计数，才能在刷新前后保持同一身份（就地更新靠它匹配组头）。
        """
        if self.count is None:
            return self.title
        return f"{self.title}（{self.count}）"
