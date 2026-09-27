# -*- coding: utf-8 -*-
"""编辑弹窗的字段描述。

Field 是数据驱动的核心：EditDialog 只认 kind，不认业务。
"""

from typing import NamedTuple, Optional, Callable, Any, Tuple


class FieldGroup(NamedTuple):
    """弹窗分组（需求 §3.8 / §3.11）：标题 + 字段 + 可选说明 / 只读信息块。

    分组只影响**布局**，不影响取值与校验 —— 那些仍按字段表整体走。
    """
    title: str
    fields: Tuple = ()
    desc: str = ""                     # 组标题下的说明行（CollapsibleSection.desc）
    info: Tuple = ()                   # 只读信息块 ((标题, 文本), ...)，画在字段上方


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
