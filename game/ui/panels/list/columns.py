# -*- coding: utf-8 -*-
"""列表列定义 —— 单一真相源。

加列 / 改宽度 / 改取值只改这里。
image 字段是自定义列渲染扩展点（如势力色块：文本前加图片）。

列顺序的排列规则也在这里（arrange_column_keys）—— 面板渲染与设置窗口
的列 Listbox 共用它，避免两处各写一份、把新列放去不同位置。
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
    # 排序键（缺省 = 用显示值）。显示值不便排序时用（如「登场」显示 ✓/✗ 但按 bool 排）
    sort_key: Optional[Callable[[Any], Any]] = None


def arrange_column_keys(declared_keys, order=()):
    """按 PANEL_COLUMNS[k].order 把声明列 key 排成最终显示顺序。

    不处理 hidden —— 返回全部 key，隐藏过滤由调用方做（设置窗口还要把
    隐藏列以 ○ 显示出来）。

    规则：
      - order 中的 key = 用户自定义的位置，按其在 order 里的先后排出；
        order 里重复或已不存在的 key（列被删过）忽略。
      - order 中**未出现**的 key（框架新加的列）= 锚定到声明顺序中紧邻
        它前面那个已在 order 里的列**之后**；前面没有锚点则排最前。
        多个新列锚在同一处时，保持彼此的声明顺序。

    这样加新列时它会落在声明位置的附近，而不是被一律甩到末尾 ——
    用户曾调过列顺序，也不影响新列插在它该在的地方。
    """
    declared = list(declared_keys)
    declared_set = set(declared)

    stated = []
    seen = set()
    for k in order:
        if k in declared_set and k not in seen:
            seen.add(k)
            stated.append(k)

    # 未在 order 里的新列，按「前面最近的已定列」分桶（None = 排最前）
    after = {}
    anchor = None
    for k in declared:
        if k in seen:
            anchor = k
        else:
            after.setdefault(anchor, []).append(k)

    arranged = list(after.get(None, ()))
    for k in stated:
        arranged.append(k)
        arranged.extend(after.get(k, ()))
    return arranged
