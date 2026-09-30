#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包 battle 模块待评审代码 → markdown（自动分卷）。

放在项目根目录，直接运行：
    python pack_for_review.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_STEM = "pack_review_battle"
MAX_SINGLE = 300 * 1024      # 单文档上限
VOL_TARGET = 90 * 1024       # 分卷目标

CODE_FILES = [
    "battle/render/symbol.py",
    "battle/render/widgets.py",
    "battle/render/unit_layer.py",
    "battle/config.py",
    "battle/balance.py",
    "battle/app.py",
]

JSON_SPECS = [
    ("battle/data/side_red.json", "head3"),
    ("battle/assets/maps/default.json", "meta"),
]


def slice_json(path: Path, mode: str) -> str:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"[解析失败] {exc}"

    if mode == "meta":
        if isinstance(raw, dict):
            out = {k: v for k, v in raw.items() if k != "tiles"}
            if "tiles" in raw:
                out["_tiles_omitted"] = f"省略 {len(raw.get('tiles') or [])} 条"
            return json.dumps(out, ensure_ascii=False, indent=2)
        return json.dumps(raw, ensure_ascii=False, indent=2)[:2000]

    if mode == "head3":
        if isinstance(raw, dict):
            units = raw.get("units")
            if isinstance(units, list):
                out = {k: v for k, v in raw.items() if k != "units"}
                out["units"] = units[:3]
                out["_units_total"] = len(units)
                return json.dumps(out, ensure_ascii=False, indent=2)
            return json.dumps(raw, ensure_ascii=False, indent=2)
        if isinstance(raw, list):
            return json.dumps(raw[:3], ensure_ascii=False, indent=2)
        return json.dumps(raw, ensure_ascii=False, indent=2)

    return json.dumps(raw, ensure_ascii=False, indent=2)


def build_sections() -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []

    for rel in CODE_FILES:
        p = ROOT / rel
        if not p.exists():
            sections.append((rel, f"[缺] {rel}"))
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception as exc:
            sections.append((rel, f"[读取失败] {exc}"))
            continue
        sections.append((rel, "```python\n" + text.rstrip() + "\n```"))

    for rel, mode in JSON_SPECS:
        p = ROOT / rel
        if not p.exists():
            sections.append((rel, f"[缺] {rel}"))
            continue
        sections.append((rel, "```json\n" + slice_json(p, mode).rstrip() + "\n```"))

    return sections


def write_docs(sections: list[tuple[str, str]]) -> list[Path]:
    blocks = [f"### {rel}\n\n{body}\n" for rel, body in sections]
    total = sum(len(b.encode("utf-8")) for b in blocks)

    if total <= MAX_SINGLE:
        out = ROOT / f"{OUT_STEM}.txt"
        header = "# battle 待评审打包\n\n"
        out.write_text(header + "\n".join(blocks), encoding="utf-8")
        return [out]

    vols: list[list[str]] = []
    cur: list[str] = []
    size = 0
    for b in blocks:
        bsize = len(b.encode("utf-8"))
        if cur and size + bsize > VOL_TARGET:
            vols.append(cur)
            cur = []
            size = 0
        cur.append(b)
        size += bsize
    if cur:
        vols.append(cur)

    outs: list[Path] = []
    for i, vol in enumerate(vols, 1):
        out = ROOT / f"{OUT_STEM}_{i:02d}.txt"
        header = f"# battle 待评审打包（第 {i}/{len(vols)} 卷）\n\n"
        out.write_text(header + "\n".join(vol), encoding="utf-8")
        outs.append(out)
    return outs


def main() -> None:
    sections = build_sections()
    outs = write_docs(sections)

    missing = [rel for rel, body in sections if body.startswith("[缺]")]
    print("=" * 60)
    print(f"输出文件数：{len(outs)}")
    for out in outs:
        size_kb = out.stat().st_size / 1024
        print(f"  {out}  ({size_kb:.1f} KB)")
    if missing:
        print("缺失文件：")
        for rel in missing:
            print(f"  [缺] {rel}")
    print("=" * 60)
    print("请把上面每个文件的内容整份贴回对话（分卷则逐卷贴）。")


if __name__ == "__main__":
    main()