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

    def has_subgroups(self) -> bool:
        """children 首元素是 Group 则为嵌套组，否则为叶子行。"""
        return bool(self.children) and isinstance(self.children[0], Group)
