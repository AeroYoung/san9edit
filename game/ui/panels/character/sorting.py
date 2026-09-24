# -*- coding: utf-8 -*-
"""按列排序。空值 / "—" 永远排最后。"""


def sort_rows(rows, columns_by_key, col_key, desc=False):
    col = columns_by_key.get(col_key)
    if col is None:
        return list(rows)

    def sort_key(row):
        v = col.value(row)
        is_empty = v is None or v == "" or v == "—"
        if col.sort_numeric:
            try:
                num = float(v)
            except (TypeError, ValueError):
                num = 0.0
            return (is_empty, num)
        return (is_empty, str(v) if v is not None else "")

    return sorted(rows, key=sort_key, reverse=desc)