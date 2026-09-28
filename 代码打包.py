#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看 assets/characters.json 里五维数值的分布情况（默认：统率 leadership）。

纯标准库，不参与运行时，输出全走 print。

用法示例：
    python tools/characters/leadership_dist.py                 # 全体统率，档宽 5
    python tools/characters/leadership_dist.py --bucket 10     # 档宽改成 10
    python tools/characters/leadership_dist.py --stat might    # 改看武力
    python tools/characters/leadership_dist.py --no-transmigrate
    python tools/characters/leadership_dist.py --top 8         # 每档列 8 人
    python tools/characters/leadership_dist.py --group         # 历史 / 穿越分开各来一份
    python tools/characters/leadership_dist.py --base-troops 1150   # 试不同基准带兵
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

# 五维：字段名 -> 中文名
STATS = {
    "leadership":   "统率",
    "might":        "武力",
    "intelligence": "智力",
    "politics":     "政治",
    "charisma":     "魅力",
}

TRANSMIGRATE_MIN_ID = 1001   # id >= 此值视为穿越人物（README §0）
BAR_WIDTH = 40               # 直方图最长条的字符数


# ============================================================
#  带兵上限模型（按统率派生）—— 想改手感只动这四行
# ============================================================
BASE_L  = 50      # 基准统率（中位数武将）
BASE_T  = 1000    # 基准统率对应的最大带兵
MIN_T   = 200     # 带兵下限（低统率不至于为 0）
CAP_EXP = 2.2     # 曲线陡度：2.0 默认；2.5 更陡，1.5 更平，1.0 = 线性


def max_troops(leadership: int, exp: float = CAP_EXP) -> int:
    """按统率给出最大带兵上限。"""
    return max(MIN_T, int(BASE_T * (leadership / BASE_L) ** exp))
# ============================================================


def _pick_bar_char() -> str:
    """终端编码不支持方块字符时退回 '#'。"""
    try:
        "█".encode(sys.stdout.encoding or "utf-8")
        return "█"
    except (UnicodeEncodeError, LookupError):
        return "#"


BAR_CHAR = _pick_bar_char()


def find_characters_json() -> Path:
    """从脚本位置向上找含 assets/characters.json 的目录。"""
    here = Path(__file__).resolve()
    for base in here.parents:
        cand = base / "assets" / "characters.json"
        if cand.is_file():
            return cand
    return here.parent.parent.parent / "assets" / "characters.json"


def load_characters(path: Path) -> dict:
    """兼容 {id: {...}} / {"characters": {...}} / [...] 三种结构。"""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        inner = data.get("characters")
        if isinstance(inner, dict):
            return inner
        if isinstance(inner, list):
            return {str(r.get("id", i)): r for i, r in enumerate(inner)}
        return {k: v for k, v in data.items()
                if isinstance(v, dict) and "name" in v}

    if isinstance(data, list):
        return {str(r.get("id", i)): r for i, r in enumerate(data)}

    raise ValueError(f"无法识别的 characters.json 结构：{type(data).__name__}")


def to_int(v):
    """尽力转 int；失败返回 None。bool 不算数。"""
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        return int(v)
    if isinstance(v, str) and v.strip().lstrip("-").isdigit():
        return int(v)
    return None


def is_transmigrate(cid: str) -> bool:
    try:
        return int(cid) >= TRANSMIGRATE_MIN_ID
    except (TypeError, ValueError):
        return False


def collect(characters: dict, field: str, include_transmigrate: bool):
    """返回 ([(cid, name, value), ...], 缺失数)。"""
    rows, missing = [], 0
    for cid, rec in characters.items():
        if not isinstance(rec, dict):
            continue
        if not include_transmigrate and is_transmigrate(cid):
            continue
        v = to_int(rec.get(field))
        if v is None:
            missing += 1
            continue
        rows.append((cid, str(rec.get("name") or "?"), v))
    return rows, missing


def percentile(sorted_vals, p: float) -> float:
    """线性插值分位数。"""
    if not sorted_vals:
        return float("nan")
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    k = (len(sorted_vals) - 1) * p / 100.0
    lo, hi = int(k), min(int(k) + 1, len(sorted_vals) - 1)
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (k - lo)


def make_keyer(start: int, bkt: int, hi: int):
    """返回 (key_fn, last_key)。上界值归入最后一档。"""
    last = (hi - start) // bkt
    if (hi - start) % bkt == 0 and last > 0:
        last -= 1
    last_key = start + last * bkt

    def key(v: int) -> int:
        if v >= hi:
            return last_key
        return start + ((v - start) // bkt) * bkt

    return key, last_key


def render_bar(count: int, peak: int) -> str:
    if count <= 0 or peak <= 0:
        return ""
    return BAR_CHAR * max(1, round(count / peak * BAR_WIDTH))


def print_histogram(buckets, total, keyw, hi, bkt, last_key, label,
                    indent="  ", value_of=None, show_cap=False):
    peak = max((len(v) for v in buckets.values()), default=0)
    for k in sorted(buckets):
        items = buckets[k]
        cnt = len(items)
        upper = hi if k == last_key else k + bkt - 1
        pct = cnt / total * 100
        line = (f"{indent}[{k:>{keyw}}-{upper:>{keyw}}] {cnt:>5}  "
                f"{pct:>5.1f}%  {render_bar(cnt, peak)}")
        if show_cap and value_of is not None and cnt:
            caps = [max_troops(value_of(it)) for it in items]
            line += f"   平均带兵 {statistics.mean(caps):>5.0f}"
        print(line)


def main():
    global BASE_T   # 允许 --base-troops 覆盖

    ap = argparse.ArgumentParser(
        description="查看 characters.json 里五维数值的分布情况",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--stat", default="leadership", choices=sorted(STATS),
                    help="要统计的五维字段（默认 leadership=统率）")
    ap.add_argument("--bucket", type=int, default=5,
                    help="分档宽度（默认 5）")
    ap.add_argument("--top", type=int, default=5,
                    help="每档列出的代表人物数，0 = 不列（默认 5）")
    ap.add_argument("--no-transmigrate", action="store_true",
                    help=f"排除穿越人物（id >= {TRANSMIGRATE_MIN_ID}）")
    ap.add_argument("--group", action="store_true",
                    help="额外按历史 / 穿越分别输出一份直方图")
    ap.add_argument("--path", default=None,
                    help="characters.json 路径（默认自动定位）")
    ap.add_argument("--base-troops", type=int, default=None,
                    help="临时覆盖基准带兵 BASE_T（默认用文件里的值）")
    args = ap.parse_args()

    if args.bucket < 1:
        raise SystemExit("--bucket 必须 >= 1")
    if args.base_troops is not None:
        BASE_T = args.base_troops

    path = Path(args.path) if args.path else find_characters_json()
    if not path.is_file():
        raise SystemExit(f"找不到文件：{path}")

    characters = load_characters(path)
    label = STATS[args.stat]
    rows, missing = collect(characters, args.stat, not args.no_transmigrate)

    print("=" * 60)
    print(f"{label}（{args.stat}）分布统计")
    print("=" * 60)
    print(f"数据源    : {path}")
    print(f"总人数    : {len(characters)}")
    print(f"参与统计  : {len(rows)}")
    print(f"缺失/非法 : {missing}")
    if args.no_transmigrate:
        print(f"（已排除穿越人物 id >= {TRANSMIGRATE_MIN_ID}）")
    print()

    if not rows:
        raise SystemExit("没有可统计的数据。")

    values = sorted(v for _, _, v in rows)
    lo, hi = values[0], values[-1]
    mode, mode_n = Counter(values).most_common(1)[0]

    print("---- 描述统计 ----")
    print(f"最小 / 最大 : {lo} / {hi}")
    print(f"平均        : {statistics.mean(values):.2f}")
    print(f"中位数      : {statistics.median(values):.1f}")
    print(f"众数        : {mode}（{mode_n} 人）")
    if len(values) > 1:
        print(f"标准差      : {statistics.pstdev(values):.2f}")
    ps = "  ".join(f"P{p}={percentile(values, p):.1f}"
                   for p in (25, 50, 75, 90, 99))
    print(f"分位数      : {ps}")
    print()

    caps = [max_troops(v) for _, _, v in rows]
    print("---- 带兵上限（按统率派生）----")
    print(f"公式        : {BASE_T} × ({label}/{BASE_L})^{CAP_EXP}，下限 {MIN_T}")
    print(f"全体平均    : {statistics.mean(caps):.0f}")
    print(f"中位数      : {statistics.median(caps):.0f}")
    print(f"最小 / 最大 : {min(caps)} / {max(caps)}")
    print(f"合计兵力    : {sum(caps):,}")
    print()

    bkt = args.bucket
    start = (lo // bkt) * bkt
    key_fn, last_key = make_keyer(start, bkt, hi)
    keyw = max(2, len(str(hi)))

    buckets: dict[int, list] = {}
    for cid, name, v in rows:
        buckets.setdefault(key_fn(v), []).append((cid, name, v))

    print(f"---- 直方图（档宽 {bkt}，{label}）----")
    print_histogram(buckets, len(rows), keyw, hi, bkt, last_key, label,
                    indent="", value_of=lambda it: it[2], show_cap=True)
    print()

    if args.top > 0:
        print(f"---- 各档代表人物（{label}降序，每档前 {args.top} 名）----")
        for k in sorted(buckets, reverse=True):
            upper = hi if k == last_key else k + bkt - 1
            top = sorted(buckets[k], key=lambda r: (-r[2], r[0]))[:args.top]
            names = "  ".join(f"{n}({c}·{v}→{max_troops(v)})"
                              for c, n, v in top)
            more = len(buckets[k]) - len(top)
            tail = f"  …+{more}" if more > 0 else ""
            print(f"[{k:>{keyw}}-{upper:>{keyw}}] {names}{tail}")
        print()

    if args.group:
        all_rows, _ = collect(characters, args.stat, True)
        for title, pred in (("历史人物", lambda c: not is_transmigrate(c)),
                            ("穿越人物", is_transmigrate)):
            sub = [r for r in all_rows if pred(r[0])]
            if not sub:
                continue
            sv = sorted(v for _, _, v in sub)
            print(f"---- {title}（{len(sub)} 人）----")
            print(f"  最小 {sv[0]}  最大 {sv[-1]}  "
                  f"平均 {statistics.mean(sv):.2f}  "
                  f"中位 {statistics.median(sv):.1f}")
            sb: dict[int, list] = {}
            for cid, name, v in sub:
                sb.setdefault(key_fn(v), []).append(v)
            print_histogram(sb, len(sub), keyw, hi, bkt, last_key, title)
            print()


if __name__ == "__main__":
    main()