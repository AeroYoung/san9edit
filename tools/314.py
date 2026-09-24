# -*- coding: utf-8 -*-
"""从《314英雄集结武将数据.xlsx》生成 characters.json。

用法（把本脚本和 xlsx 放在同一个文件夹，直接运行）：
    python build_characters.py

行为：
    - 自动找脚本同目录下的 .xlsx / .xlsm / .csv（取第一个）
    - 输出 characters.json 到脚本同目录
    - 若同目录下已有 characters.json，会被覆盖

依赖：
    - xlsx: openpyxl（仅生成阶段用，游戏运行时不需要）
    - csv : 标准库
"""

import csv
import json
import sys
from pathlib import Path


# ---------- 列索引（0-based） ----------
C_ID             = 0     # 编号
C_NAME           = 1     # 姓名
C_FAMILY_NAME    = 2     # 字
# C_FACTION      = 3     # 军团（基础数据留空，不读）
# C_LOCATION     = 4     # 所在（留空，不读）
# C_AFFILIATION  = 5     # 所属（留空，不读）
# C_ROLE         = 6     # 身份（留空，不读）
C_LEADERSHIP     = 7
C_MIGHT          = 8
C_INTELLIGENCE   = 9
C_POLITICS       = 10
C_CHARISMA       = 11
C_PORTRAIT       = 12
C_TRAITS         = 13    # 个性
C_FORMATIONS     = 14    # 阵型
C_TACTICS        = 15    # 战法
C_START_OFFICIAL = 16
C_SEX            = 17
C_APPEAR_YEAR    = 18
C_BIRTH_YEAR     = 19
C_DEATH_YEAR     = 20
C_AFFINITY       = 21
C_BLOOD          = 22
C_FATHER         = 23
C_MOTHER         = 24
C_GENERATION     = 25
C_SPOUSE         = 26
C_SWORN          = 27    # 义兄弟
C_LIKED          = list(range(28, 36))    # 亲爱武将 1–8
C_DISLIKED       = list(range(36, 44))    # 厌恶武将 1–8


# ---------- 工具 ----------
def cell(row, idx):
    if idx >= len(row):
        return ""
    v = row[idx]
    return "" if v is None else str(v).strip()


def to_int(v, default=0):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def split_multi(s):
    """按空格/顿号/逗号切分。"""
    if not s:
        return []
    for sep in ("、", "，", ","):
        s = s.replace(sep, " ")
    return [x for x in s.split() if x]


# ---------- 定位输入文件 ----------
def find_input(here):
    """在脚本同目录找 xlsx / xlsm / csv，取第一个。"""
    for ext in (".xlsx", ".xlsm", ".csv"):
        for p in sorted(here.glob(f"*{ext}")):
            if p.name.startswith("~$"):     # Excel 临时文件
                continue
            return p
    return None


# ---------- 读表 ----------
def read_xlsx(path):
    try:
        from openpyxl import load_workbook
    except ImportError:
        print("=" * 60)
        print("ERROR: 缺少 openpyxl。")
        print("请先运行：pip install openpyxl")
        print("或者：把 xlsx 用 Excel 另存为 'CSV UTF-8' 再跑。")
        print("=" * 60)
        sys.exit(1)
    wb = load_workbook(path, data_only=True)
    ws = wb.active
    return [list(row) for row in ws.iter_rows(values_only=True)]


def read_csv(path):
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


# ---------- 主流程 ----------
def main():
    here = Path(__file__).resolve().parent
    src = find_input(here)
    if src is None:
        print("=" * 60)
        print(f"ERROR: 在 {here} 下没有找到 .xlsx / .xlsm / .csv 文件")
        print("请把脚本和武将数据表放在同一个文件夹里。")
        print("=" * 60)
        sys.exit(1)

    print(f"输入: {src.name}")

    suffix = src.suffix.lower()
    if suffix in (".xlsx", ".xlsm"):
        rows = read_xlsx(src)
    elif suffix == ".csv":
        rows = read_csv(src)
    else:
        print(f"ERROR: 不支持的格式 {suffix}")
        sys.exit(1)

    if len(rows) < 2:
        print("ERROR: 表为空或没有数据行")
        sys.exit(1)

    data_rows = rows[1:]   # 跳过表头
    print(f"数据行: {len(data_rows)}")

    # ---------- 第一遍：建 名字 → [id, ...] 索引 ----------
    name_to_ids = {}
    for row in data_rows:
        cid_raw = to_int(cell(row, C_ID), 0)
        if cid_raw <= 0:
            continue
        name = cell(row, C_NAME)
        if not name:
            continue
        name_to_ids.setdefault(name, []).append(f"{cid_raw:04d}")

    ambiguous = {n: sorted(ids) for n, ids in name_to_ids.items() if len(ids) > 1}
    # 同名取编号最小的
    name_to_id = {n: sorted(ids)[0] for n, ids in name_to_ids.items()}

    # ---------- 第二遍：构造人物 ----------
    characters = {}
    missing_refs = {}

    def to_ref(name_val):
        if not name_val:
            return None
        rid = name_to_id.get(name_val)
        if rid is None:
            missing_refs[name_val] = missing_refs.get(name_val, 0) + 1
        return rid

    def to_refs(cols, row):
        out = []
        for c in cols:
            rid = to_ref(cell(row, c))
            if rid:
                out.append(rid)
        return out

    for row in data_rows:
        cid_raw = to_int(cell(row, C_ID), 0)
        if cid_raw <= 0:
            continue
        cid = f"{cid_raw:04d}"

        characters[cid] = {
            "name":         cell(row, C_NAME),
            "family_name":  cell(row, C_FAMILY_NAME),
            "sex":          cell(row, C_SEX) or "男",
            "portrait":     to_int(cell(row, C_PORTRAIT), 0),
            "leadership":   to_int(cell(row, C_LEADERSHIP), 50),
            "might":        to_int(cell(row, C_MIGHT), 50),
            "intelligence": to_int(cell(row, C_INTELLIGENCE), 50),
            "politics":     to_int(cell(row, C_POLITICS), 50),
            "charisma":     to_int(cell(row, C_CHARISMA), 50),
            "appear_year":  to_int(cell(row, C_APPEAR_YEAR), 0),
            "birth_year":   to_int(cell(row, C_BIRTH_YEAR), 0),
            "death_year":   to_int(cell(row, C_DEATH_YEAR), 0),
            "affinity":     to_int(cell(row, C_AFFINITY), 0),
            "blood":        cell(row, C_BLOOD),
            "father":       to_ref(cell(row, C_FATHER)),
            "mother":       to_ref(cell(row, C_MOTHER)),
            "generation":   to_int(cell(row, C_GENERATION), 1),
            "spouse":       to_ref(cell(row, C_SPOUSE)),
            "sworn_brothers": to_refs([C_SWORN], row),
            "liked":        to_refs(C_LIKED, row),
            "disliked":     to_refs(C_DISLIKED, row),
            "start_official": to_int(cell(row, C_START_OFFICIAL), 0),
            "traits":       split_multi(cell(row, C_TRAITS)),
            "formations":   split_multi(cell(row, C_FORMATIONS)),
            "tactics":      split_multi(cell(row, C_TACTICS)),
            # ★ 剧本填充，基础数据留空
            "faction":       None,
            "location_name": None,
            "affiliation":   None,
            "role":          None,
        }

    # ---------- 输出 ----------
    out = {
        "version": 1,
        "source": src.name,
        "count": len(characters),
        "characters": characters,
        "_name_index": name_to_id,
        "_ambiguous_names": ambiguous,
        "_missing_refs": missing_refs,
    }

    out_path = here / "characters.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print("-" * 60)
    print(f"OK: {len(characters)} 个人物 → {out_path.name}")
    print(f"    重名: {len(ambiguous)} 个")
    if ambiguous:
        for n, ids in list(ambiguous.items())[:10]:
            print(f"      {n} → {ids}")
        if len(ambiguous) > 10:
            print(f"      ...（共 {len(ambiguous)} 个，全部记录在 json 里）")
    print(f"    找不到的引用: {len(missing_refs)} 个")
    if missing_refs:
        for n, cnt in list(missing_refs.items())[:10]:
            print(f"      {n} (×{cnt})")
        if len(missing_refs) > 10:
            print(f"      ...（共 {len(missing_refs)} 个）")
    print("-" * 60)


if __name__ == "__main__":
    main()