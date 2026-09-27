# -*- coding: utf-8 -*-
"""编辑弹窗的字段描述。

Field 是数据驱动的核心：EditDialog 只认 kind，不认业务。
"""

from typing import NamedTuple, Optional, Callable, Any, Tuple


class FieldGroup(NamedTuple):
    """弹窗分组。分组只影响布局，不影响取值与校验。"""
    title: str
    fields: Tuple = ()
    desc: str = ""                     # 组标题下的说明行
    info: Tuple = ()                   # 只读信息块 ((标题, 文本), ...)
    # 以下为新增，均有默认值，不影响其它调用点：
    layout: str = "rows"               # "rows" | "two_cols" | "inline"
    left_keys: Tuple = ()              # two_cols：进左栏的字段 key（其余进右栏）
    left_info_titles: Tuple = ()       # two_cols：进左栏的 info 标题（其余进右栏）
    side_image: str = None             # two_cols：左栏顶部头像路径
    side_caption: str = None           # two_cols：头像下说明文字
    
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
