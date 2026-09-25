#!/usr/bin/env python3
# pack_for_review.py
# 放在项目根目录（与 main.py 同级），直接：python pack_for_review.py

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_BASENAME = "review_pack"
MAX_BYTES = 300 * 1024
TARGET_BYTES = 90 * 1024

CODE_FILES = [
    "game/core/character.py",
    "game/core/world.py",
    "game/core/edit_session.py",
    "game/core/edit_commands.py",
    "game/ui/panels/character_panel.py",
    "game/ui/panels/list/panel.py",
    "game/ui/panels/list/columns.py",
    "game/ui/panels/list/model.py",
    "game/ui/panels/list/sorting.py",
    "game/ui/panels/list/grouping.py",
    "game/ui/panels/list/group_bar.py",
    "game/ui/panels/list/context_menu.py",
    "game/ui/panels/list/search_bar.py",
    "game/ui/side_panel.py",
    "game/ui/main_window.py",
    "game/ui/panels/faction_panel.py",
    "game/config/style.py",
    "game/config/constants.py",
    "tests/test_character_appeared.py",
    "tests/test_composite_command.py",
]

FENCE = "```"


def fence(lang: str, body: str) -> str:
    return f"{FENCE}{lang}\n{body.rstrip()}\n{FENCE}\n"


def read_text(rel: str) -> str | None:
    p = ROOT / rel
    if not p.is_file():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8", errors="replace")


def load_json(rel: str):
    p = ROOT / rel
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def sample_dict(d: dict, n_first: int = 3, n_last: int = 2, extra_keys=()) -> dict:
    keys = list(d.keys())
    picked = []
    for k in keys[:n_first]:
        picked.append(k)
    for k in keys[-n_last:]:
        if k not in picked:
            picked.append(k)
    for k in extra_keys:
        if k in d and k not in picked:
            picked.append(k)
    return {k: d[k] for k in picked}


def slice_characters_json() -> str | None:
    data = load_json("assets/characters.json")
    if data is None:
        return None
    chars = data.get("characters", {})
    name_index = data.get("_name_index", {})
    out = {
        "version": data.get("version"),
        "source": data.get("source"),
        "count": data.get("count"),
        "_ambiguous_names": data.get("_ambiguous_names"),
        "_missing_refs": data.get("_missing_refs"),
        "_name_index_sample": dict(list(name_index.items())[:10]),
        "characters_sample": sample_dict(chars, n_first=3, n_last=2),
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


def slice_scenario_json() -> str | None:
    data = load_json("scenarios/default.json")
    if data is None:
        return None
    meta = {k: v for k, v in data.items() if k not in ("factions", "characters", "nodes")}
    factions = data.get("factions", {})
    chars = data.get("characters", {})
    nodes = data.get("nodes", {})
    extra_ids = ["0001", "0003", "0521", "0522", "0101"]
    out = {
        "meta": meta,
        "factions_sample": sample_dict(factions, n_first=5, n_last=0),
        "characters_sample": sample_dict(chars, n_first=10, n_last=5, extra_keys=extra_ids),
        "nodes_sample": sample_dict(nodes, n_first=3, n_last=0),
    }
    return json.dumps(out, ensure_ascii=False, indent=2)


def build_sections() -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []

    for rel in CODE_FILES:
        text = read_text(rel)
        title = f"### {rel}\n"
        if text is None:
            sections.append((title, "[缺] " + rel + "\n"))
        else:
            sections.append((title, fence("python", text)))

    for rel, slicer, lang in [
        ("assets/characters.json", slice_characters_json, "json"),
        ("scenarios/default.json", slice_scenario_json, "json"),
    ]:
        title = f"### {rel}（截取）\n"
        body = slicer()
        if body is None:
            sections.append((title, "[缺] " + rel + "\n"))
        else:
            sections.append((title, fence(lang, body)))

    return sections


def section_size(sec: tuple[str, str]) -> int:
    return len(sec[0].encode("utf-8")) + len(sec[1].encode("utf-8"))


def write_outputs(sections: list[tuple[str, str]]) -> list[Path]:
    total = sum(section_size(s) for s in sections)
    written: list[Path] = []

    if total <= MAX_BYTES:
        out = ROOT / f"{OUT_BASENAME}.md"
        with out.open("w", encoding="utf-8") as f:
            f.write("# review pack\n\n")
            for title, body in sections:
                f.write(title)
                f.write(body)
                f.write("\n")
        written.append(out)
        return written

    volumes: list[list[tuple[str, str]]] = []
    cur: list[tuple[str, str]] = []
    cur_size = 0
    for sec in sections:
        sz = section_size(sec)
        if cur and cur_size + sz > TARGET_BYTES:
            volumes.append(cur)
            cur = []
            cur_size = 0
        cur.append(sec)
        cur_size += sz
    if cur:
        volumes.append(cur)

    for i, vol in enumerate(volumes, 1):
        out = ROOT / f"{OUT_BASENAME}_{i:02d}.txt"
        with out.open("w", encoding="utf-8") as f:
            f.write(f"# review pack {i:02d}\n\n")
            for title, body in vol:
                f.write(title)
                f.write(body)
                f.write("\n")
        written.append(out)

    return written


def main() -> None:
    sections = build_sections()
    written = write_outputs(sections)
    print("=" * 60)
    for p in written:
        size = p.stat().st_size
        print(f"{p}  ({size / 1024:.1f} KB)")
    print("=" * 60)
    print("请把以上文件内容贴回对话。")


if __name__ == "__main__":
    main()