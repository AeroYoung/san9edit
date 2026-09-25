#!/usr/bin/env python3
"""把本次需求所需的代码 + JSON 截取拼成单个文本文件（供对话粘贴）。

用法：
    python pack_for_review.py            # 输出单个 打包_人物登场字段.md
    python pack_for_review.py --split    # 按 ~80KB 分卷成 打包_人物登场字段_01.txt ...
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE = "打包_人物登场字段"

CODE_FILES = [
    "game/core/character.py",
    "game/core/scenario.py",
    "game/core/scenario_writer.py",
    "game/core/world.py",
    "game/core/edit_commands.py",
    "game/core/edit_session.py",
    "game/ui/panels/character_panel.py",
    "game/ui/panels/list/panel.py",
    "game/ui/panels/list/columns.py",
    "game/ui/panels/list/context_menu.py",
    "game/ui/panels/list/grouping.py",
    "game/ui/dialogs/node_edit.py",
    "game/ui/dialogs/edit_dialog.py",
    "game/ui/dialogs/field_spec.py",
    "game/ui/dialogs/node_fields.py",
    "game/ui/character_info_window.py",
    "game/config/constants.py",
    "tools/build_scenario_190.py",
]


# ---------- JSON 截取 ----------
def _take(d, n, tail=False):
    if not isinstance(d, dict):
        return {}
    items = list(d.items())
    return dict(items[-n:] if tail else items[:n])


def slice_characters_json(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    chars = raw.get("characters", {})
    name_index = raw.get("_name_index", {}) or {}
    return {
        "_截取说明": "前 3 + 末 3；_ambiguous_names/_missing_refs 原样；_name_index 给 size + 前 3 样例",
        "version": raw.get("version"),
        "source": raw.get("source"),
        "count": raw.get("count"),
        "characters_head": _take(chars, 3),
        "characters_tail": _take(chars, 3, tail=True),
        "_ambiguous_names": raw.get("_ambiguous_names"),
        "_missing_refs": raw.get("_missing_refs"),
        "_name_index_size": len(name_index),
        "_name_index_sample": _take(name_index, 3),
    }


def slice_default_json(path: Path):
    raw = json.loads(path.read_text(encoding="utf-8"))
    meta = {k: v for k, v in raw.items()
            if k not in ("factions", "characters", "nodes")}
    return {
        "_截取说明": "顶层元字段全量；factions 前 1；characters 前 3；nodes 前 2",
        "meta": meta,
        "factions_sample": _take(raw.get("factions", {}), 1),
        "characters_head": _take(raw.get("characters", {}), 3),
        "nodes_head": _take(raw.get("nodes", {}), 2),
        "_counts": {
            "factions": len(raw.get("factions", {})),
            "characters": len(raw.get("characters", {})),
            "nodes": len(raw.get("nodes", {})),
        },
    }


# ---------- 组装 ----------
def collect() -> tuple[str, list[str]]:
    parts: list[str] = []
    missing: list[str] = []

    parts.append(f"# {BASE}\n")
    parts.append("本文件由 pack_for_review.py 生成，包含本次需求所需的代码与 JSON 截取。\n")

    parts.append("\n## 一、代码文件\n")
    for rel in CODE_FILES:
        p = ROOT / rel
        if not p.is_file():
            missing.append(rel)
            parts.append(f"\n### [缺] {rel}\n")
            continue
        code = p.read_text(encoding="utf-8", errors="replace")
        parts.append(f"\n### {rel}\n")
        parts.append(f"```python\n{code}\n```\n")

    parts.append("\n## 二、JSON 截取\n")

    cj = ROOT / "assets" / "characters.json"
    parts.append("\n### assets/characters.json（截取）\n")
    if cj.is_file():
        parts.append("```json\n" + json.dumps(
            slice_characters_json(cj), ensure_ascii=False, indent=2) + "\n```\n")
    else:
        missing.append("assets/characters.json")
        parts.append("[缺]\n")

    dj = ROOT / "scenarios" / "default.json"
    parts.append("\n### scenarios/default.json（截取）\n")
    if dj.is_file():
        parts.append("```json\n" + json.dumps(
            slice_default_json(dj), ensure_ascii=False, indent=2) + "\n```\n")
    else:
        missing.append("scenarios/default.json")
        parts.append("[缺]\n")

    return "".join(parts), missing


def write_single(text: str) -> Path:
    out = ROOT / f"{BASE}.md"
    out.write_text(text, encoding="utf-8")
    return out


def write_split(text: str, chunk_kb: int = 80) -> list[Path]:
    limit = chunk_kb * 1024
    # 按 "### " 分节切，尽量不切断单个文件
    sections = text.split("\n### ")
    head = sections[0]
    sections = ["### " + s for s in sections[1:]]

    chunks: list[str] = []
    cur = head
    for sec in sections:
        if len(cur.encode("utf-8")) + len(sec.encode("utf-8")) > limit and cur:
            chunks.append(cur)
            cur = sec
        else:
            cur += "\n" + sec
    if cur:
        chunks.append(cur)

    outs: list[Path] = []
    for i, ch in enumerate(chunks, 1):
        p = ROOT / f"{BASE}_{i:02d}.txt"
        p.write_text(ch, encoding="utf-8")
        outs.append(p)
    return outs


def main() -> None:
    text, missing = collect()
    size_kb = len(text.encode("utf-8")) / 1024

    print(f"项目根：{ROOT}")
    print(f"总内容：{size_kb:.1f} KB")
    if missing:
        print(f"⚠️  缺失 {len(missing)} 个文件（正文中标为 [缺]）：")
        for m in missing:
            print(f"     {m}")
    print()

    if "--split" in sys.argv or size_kb > 300:
        if "--split" not in sys.argv:
            print("（超过 300KB，自动分卷）")
        outs = write_split(text)
        print(f"✅ 已分卷 {len(outs)} 个文件：")
        for p in outs:
            print(f"   {p.name}  ({p.stat().st_size/1024:.1f} KB)")
        print("\n把这几个 txt 按顺序逐个粘贴/上传即可。")
    else:
        out = write_single(text)
        print(f"✅ 已生成单文件：{out}")
        print(f"   {out.stat().st_size/1024:.1f} KB")
        print("\n直接上传这个 .md 给我，或把内容粘贴过来。")
        print("如果粘贴超长被截断，改跑：python pack_for_review.py --split")


if __name__ == "__main__":
    main()