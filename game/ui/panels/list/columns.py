# -*- coding: utf-8 -*-
"""列表列定义 —— 单一真相源。

加列 / 改宽度 / 改取值只改这里。
image 字段是自定义列渲染扩展点（如势力色块：文本前加图片）。
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional


@dataclass(frozen=True)
class Column:
    key: str
    title: str
    width: int
    anchor: str
    value: Callable[[Any], Any]
    sort_numeric: bool = False
    image: Optional[Callable[[Any], Any]] = None   # row -> PhotoImage | None
