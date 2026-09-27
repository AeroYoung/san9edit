#!/usr/bin/env python3
"""需求审查打包脚本：收集代码文件 + 数据片段，输出 markdown。

用法：
    python pack_for_review.py
输出：
    需求审查包.md                （单文档 ≤ 300KB 时）
    需求审查包_01.txt / _02.txt  （超 300KB 时分卷，每卷 ≤ 100KB）
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_BASE = "需求审查包"
MAX_SINGLE = 300 * 1024     # 单文档阈值
MAX_CHUNK  = 95 * 1024      # 分卷时每卷目标

# ── 本次要看的代码文件 ────────────────────────────────────────────
CODE_FILES = [
    "game/core/world.py",
    "game/core/character.py",
    "game/core/node.py",
    "game/core/scenario.py",
    "game/core/faction.py",
    "game/core/official_title.py",   # 可能不存在 → 标 [缺]
    "game/ui/panels/node_panel.py",
    "game/ui/panels/character_panel.py",
    "game/ui/character_info_window.py",
    "tools/build_scenario_190.py",
]

# ── 需要截取的 JSON 文件：路径 → 每段保留前 N 条 ────────────────────
JSON_SLICES = {
    "scenarios/default.json": 3,
}

# style.py 只截取这两个段
STYLE_KEYS = ("THEME", "PANEL_COLUMNS")


# ────────────────────────────────────────────────────────────────
def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def slice_style_py(path: Path) -> list[tuple[str, str]]:
    """从 style.py 里抽出 THEME / PANEL_COLUMNS 顶层赋值段。"""
    text = read_text(path)
    out: list[tuple[str, str]] = []
    for key in STYLE_KEYS:
        m = re.search(rf"^{key}\s*=\s*\{{", text, re.MULTILINE)
        if not m:
            continue
        start = m.start()
        end_m = re.search(r"^\}\s*$", text[m.end():], re.MULTILINE)
        end = m.end() + end_m.end() if end_m else len(text)
        out.append((f"{path.as_posix()}::{key}", text[start:end]))
    return out


def slice_scenario(data, n: int):
    """顶层元字段 + factions / characters / nodes 各保留前 n 条。"""
    if not isinstance(data, dict):
        return data
    out = {}
    for k, v in data.items():
        if k in ("factions", "characters", "nodes") and isinstance(v, dict):
            out[k] = dict(list(v.items())[:n])
        else:
            out[k] = v
    return out


def wrap_block(name: str, content: str, lang: str) -> str:
    return f"### {name}\n```{lang}\n{content}\n```\n\n"


def split_blocks(blocks, max_chunk):
    chunks, cur, cur_size = [], [], 0
    for b in blocks:
        n, c, lang = b
        s = len(wrap_block(n, c, lang).encode("utf-8"))
        if cur and cur_size + s > max_chunk:
            chunks.append(cur)
            cur, cur_size = [], 0
        cur.append(b)
        cur_size += s
    if cur:
        chunks.append(cur)
    return chunks


# ────────────────────────────────────────────────────────────────
def collect_blocks() -> list[tuple[str, str, str]]:
    blocks: list[tuple[str, str, str]] = []

    # 1) 代码文件
    for rel in CODE_FILES:
        p = ROOT / rel
        if p.exists():
            blocks.append((rel, read_text(p), "python"))
        else:
            blocks.append((rel, "[缺]", "text"))

    # 2) style.py 截取
    style_path = ROOT / "game/config/style.py"
    if style_path.exists():
        for name, frag in slice_style_py(style_path):
            blocks.append((name, frag, "python"))
    else:
        blocks.append(("game/config/style.py", "[缺]", "text"))

    # 3) JSON 截取
    for rel, n in JSON_SLICES.items():
        p = ROOT / rel
        if not p.exists():
            blocks.append((rel, "[缺]", "text"))
            continue
        try:
            data = json.loads(read_text(p))
        except Exception as e:
            blocks.append((rel, f"[JSON 解析失败] {e}", "text"))
            continue
        frag = json.dumps(slice_scenario(data, n),
                          ensure_ascii=False, indent=2)
        blocks.append((f"{rel}（截取：元字段 + 3 段各前 {n} 条）",
                       frag, "json"))

    return blocks


def main() -> int:
    blocks = collect_blocks()
    full = "".join(wrap_block(n, c, lang) for n, c, lang in blocks)
    size = len(full.encode("utf-8"))

    print(f"[i] 收集到 {len(blocks)} 个代码/数据块，共 {size:,} 字节")

    outs: list[Path] = []
    if size <= MAX_SINGLE:
        out = ROOT / f"{OUT_BASE}.md"
        out.write_text(full, encoding="utf-8")
        outs.append(out)
    else:
        chunks = split_blocks(blocks, MAX_CHUNK)
        for i, ch in enumerate(chunks, 1):
            out = ROOT / f"{OUT_BASE}_{i:02d}.txt"
            out.write_text(
                "".join(wrap_block(n, c, lang) for n, c, lang in ch),
                encoding="utf-8",
            )
            outs.append(out)

    print("\n[i] 输出：")
    for o in outs:
        print(f"    {o.name}  ({o.stat().st_size:,} 字节)")
    print("\n[i] 请把上面这些文件的内容，依次粘贴回对话。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())