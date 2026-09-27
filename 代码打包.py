#!/usr/bin/env python3
"""打包需要审查的代码和数据片段，输出 markdown 文档。"""

import json
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_BASE = "review_pack"
MAX_TOTAL_KB = 300
TARGET_VOL_KB = 90

CODE_FILES = [
    "game/core/faction.py",
    "game/core/world.py",
    "game/core/scenario.py",
    "game/core/scenario_writer.py",
    "game/core/edit_commands.py",
    "game/core/edit_session.py",
    "game/core/official_title.py",
    "game/config/style.py",
    "game/map/renderer.py",
    "game/ui/main_window.py",
    "game/ui/character_info_window.py",
    "game/ui/panels/faction_panel.py",
    "game/ui/panels/list/panel.py",
    "game/ui/dialogs/field_spec.py",
    "game/ui/dialogs/edit_dialog.py",
    "game/ui/dialogs/faction_fields.py",
    "game/ui/dialogs/faction_edit.py",
    "game/ui/dialogs/node_fields.py",
    "game/ui/dialogs/node_edit.py",
    "tools/build_scenario_190.py",
]


def read_code(rel_path):
    full = PROJECT_ROOT / rel_path
    if not full.exists():
        return f"[缺] {rel_path}"
    try:
        text = full.read_text(encoding="utf-8")
    except Exception as e:
        return f"[读失败] {rel_path}: {e}"
    return f"### {rel_path}\n\n```python\n{text}\n```\n"


def slice_json(rel_path, meta_keys, sections):
    full = PROJECT_ROOT / rel_path
    if not full.exists():
        return f"[缺] {rel_path}"
    try:
        data = json.loads(full.read_text(encoding="utf-8"))
    except Exception as e:
        return f"[读失败] {rel_path}: {e}"

    result = {}
    for k in meta_keys:
        if k in data:
            result[k] = data[k]

    for section, limit in sections.items():
        if section not in data:
            continue
        seg = data[section]
        if isinstance(seg, dict):
            items = list(seg.items())[:limit]
            result[section] = dict(items)
        elif isinstance(seg, list):
            result[section] = seg[:limit]

    # 附加刘备相关
    if "factions" in data and isinstance(data["factions"], dict):
        for fid in ("0521",):
            if fid in data["factions"]:
                result.setdefault("factions", {})[fid] = data["factions"][fid]
    if "characters" in data and isinstance(data["characters"], dict):
        for cid in ("0003",):
            if cid in data["characters"]:
                result.setdefault("characters", {})[cid] = data["characters"][cid]

    text = json.dumps(result, ensure_ascii=False, indent=2)
    return f"### {rel_path}（截取）\n\n```json\n{text}\n```\n"


def build_sections():
    sections = []
    for rel in CODE_FILES:
        sections.append(read_code(rel))
    sections.append(slice_json(
        "scenarios/default.json",
        ["version", "id", "name", "desc", "start", "player_faction"],
        {"factions": 5, "officials": 5, "characters": 3, "nodes": 3},
    ))
    sections.append(slice_json(
        "assets/characters.json",
        ["version", "source", "count"],
        {"characters": 3},
    ))
    return sections


def write_volumes(sections):
    total_bytes = sum(len(s.encode("utf-8")) for s in sections)
    if total_bytes <= MAX_TOTAL_KB * 1024:
        out = PROJECT_ROOT / f"{OUTPUT_BASE}.txt"
        out.write_text("".join(sections), encoding="utf-8")
        return [out]

    volumes = []
    cur = []
    cur_size = 0
    for s in sections:
        s_bytes = len(s.encode("utf-8"))
        if cur and cur_size + s_bytes > TARGET_VOL_KB * 1024:
            volumes.append(cur)
            cur = []
            cur_size = 0
        cur.append(s)
        cur_size += s_bytes
    if cur:
        volumes.append(cur)

    paths = []
    for i, vol in enumerate(volumes, 1):
        out = PROJECT_ROOT / f"{OUTPUT_BASE}_{i:02d}.txt"
        out.write_text("".join(vol), encoding="utf-8")
        paths.append(out)
    return paths


def main():
    sections = build_sections()
    paths = write_volumes(sections)
    print("输出文件：")
    for p in paths:
        size_kb = p.stat().st_size / 1024
        print(f"  {p}  ({size_kb:.1f} KB)")
    print("\n请把以上文件内容贴回对话。")


if __name__ == "__main__":
    main()