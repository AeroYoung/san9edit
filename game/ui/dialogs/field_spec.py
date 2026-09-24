# -*- coding: utf-8 -*-
"""编辑弹窗的字段描述。

Field 是数据驱动的核心：EditDialog 只认 kind，不认业务。
"""

from typing import NamedTuple, Optional, Callable, Any


class Field(NamedTuple):
    key: str                          # 实体属性名
    label: str                        # UI 显示名
    kind: str                         # "int"/"str"/"bool"/"choice"/"color"/"readonly"
    default: Any = None
    options: tuple = ()               # choice 用：[(value, label), ...]
    min: Optional[int] = None         # int 用
    max: Optional[int] = None
    editable: bool = True
    hint: str = ""                    # UI 下方提示
    display_fn: Optional[Callable] = None
        # readonly 用：fn(value, world) -> str
        # 例如 owner：把 fid 显示为势力名或"无主"
