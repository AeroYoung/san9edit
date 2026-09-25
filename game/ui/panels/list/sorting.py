# -*- coding: utf-8 -*-
"""按列排序。空值 / "—" 永远排最后。"""


def sort_rows(rows, columns_by_key, col_key, desc=False):
    col = columns_by_key.get(col_key)
    if col is None:
        return list(rows)

    def sort_key(row):
        v = col.value(row)
        is_empty = v is None or v == "" or v == "—"
        raw = col.sort_key(row) if col.sort_key else v   # ★ 排序键可独立于显示值
        if col.sort_numeric:
            try:
                num = float(raw)
            except (TypeError, ValueError):
                num = 0.0
            return (is_empty, num)
        return (is_empty, str(raw) if raw is not None else "")

    return sorted(rows, key=sort_key, reverse=desc)
