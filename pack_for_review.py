#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""打包 battle/ 模块代码，输出 markdown，自动分卷。"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parent
OUT_BASE = ROOT / "_step02_review"
MAX_BYTES = 300 * 1024
TARGET_BYTES = 90 * 1024

CODE_FILES = [
    "battle/__init__.py",
    "battle/__main__.py",
    "battle/config.py",
    "battle/balance.py",
    "battle/api.py",
    "battle/app.py",
    "battle/core/__init__.py",
    "battle/core/hexgrid.py",
    "battle/core/map_data.py",
    "battle/render/__init__.py",
    "battle/render/camera.py",
    "battle/render/hex_renderer.py",
    "battle/sim/__init__.py",
    "battle/ai/__init__.py",
    "battle/docs/步骤01需求.md",
    "battle/docs/CHANGELOG.md",
]

JSON_SLICES = {
    "battle/assets/maps/default.json": {
        "head_keys": ["version", "id", "name", "cols", "rows",
                      "hex_size", "orientation"],
        "tiles_head": 3,
        "tiles_tail": 3,
    },
}

FONT_DIR_REL = "battle/assets/fonts"


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    except Exception as exc:
        return f"[读失败] {exc}"


def slice_json(path, spec):
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    try:
        data = json.loads(raw)
    except Exception as exc:
        return f"[JSON 解析失败] {exc}"

    out = {}
    for key in spec.get("head_keys", []):
        if key in data:
            out[key] = data[key]

    tiles = data.get("tiles")
    if isinstance(tiles, list):
        h, t = spec.get("tiles_head", 3), spec.get("tiles_tail", 3)
        if len(tiles) <= h + t:
            out["tiles"] = tiles
        else:
            out["tiles"] = (tiles[:h]
                            + [f"... (省略 {len(tiles) - h - t} 条) ..."]
                            + tiles[-t:])

    for key, val in data.items():
        if key not in out and key != "tiles":
            out[key] = val

    return json.dumps(out, ensure_ascii=False, indent=2)


def build_sections():
    sections = []
    for rel in CODE_FILES:
        p = ROOT / rel
        content = read_text(p)
        lang = "python" if rel.endswith(".py") else "text"
        sections.append((rel, content, lang))

    for rel, spec in JSON_SLICES.items():
        content = slice_json(ROOT / rel, spec)
        sections.append((rel, content, "json"))

    font_dir = ROOT / FONT_DIR_REL
    if font_dir.is_dir():
        names = sorted(x.name for x in font_dir.iterdir())
        body = "目录内容：\n" + "\n".join(f"- {n}" for n in names)
        sections.append((FONT_DIR_REL + "/", body, "text"))
    else:
        sections.append((FONT_DIR_REL + "/", None, "text"))

    return sections


def render_markdown(sections):
    out = ["# battle 模块代码打包（步骤02）"]
    for rel, content, lang in sections:
        out.append(f"\n### {rel}")
        if content is None:
            out.append(f"[缺] {rel}")
            continue
        fence = lang if lang in ("python", "json") else ""
        out.append(f"```{fence}")
        out.append(content.rstrip())
        out.append("```")
    return "\n".join(out) + "\n"


def split_by_file(text):
    marker = "\n### "
    if marker not in text:
        return text, []
    head, *rest = text.split(marker)
    return head, ["### " + chunk for chunk in rest]


def write_output(text):
    total = len(text.encode("utf-8"))
    if total <= MAX_BYTES:
        out = OUT_BASE.with_suffix(".md")
        out.write_text(text, encoding="utf-8")
        return [out]

    head, blocks = split_by_file(text)
    outs = []
    cur = head
    idx = 1
    for block in blocks:
        candidate = cur + "\n" + block if cur else block
        if len(candidate.encode("utf-8")) > TARGET_BYTES and cur != head:
            path = OUT_BASE.parent / f"{OUT_BASE.name}_{idx:02d}.md"
            path.write_text(cur, encoding="utf-8")
            outs.append(path)
            idx += 1
            cur = block
        else:
            cur = candidate
    if cur:
        path = OUT_BASE.parent / f"{OUT_BASE.name}_{idx:02d}.md"
        path.write_text(cur, encoding="utf-8")
        outs.append(path)
    return outs


def main():
    text = render_markdown(build_sections())
    outs = write_output(text)
    print("输出文件：")
    for p in outs:
        print(f"  {p}  ({p.stat().st_size} bytes)")
    print("\n请把上述文件内容贴回对话。")


if __name__ == "__main__":
    main()