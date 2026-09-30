#!/usr/bin/env python3
"""打包战斗模块步骤01评审代码。项目根运行：python pack_for_review.py"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT_BASE = ROOT / "pack_for_review.md"
MAX_SINGLE = 300 * 1024
VOL_SIZE = 90 * 1024

EXPLICIT = [
    "main.py",
    "game/config/logging_setup.py",
    "game/config/constants.py",
]

AUTO_SCAN_DIRS = ["game"]
AUTO_SCAN_KEYWORD = "logging_setup"
EXPECT_ABSENT = ["battle", "shared"]   # 预期不存在，正文标 [缺]

def collect_files():
    files, seen = [], set()
    for rel in EXPLICIT:
        p = ROOT / rel
        if p.exists():
            files.append(p); seen.add(p)
    for d in AUTO_SCAN_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in sorted(base.rglob("*.py")):
            if p in seen:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if AUTO_SCAN_KEYWORD in text:
                files.append(p); seen.add(p)
    return files

def render(files):
    parts = ["# 战斗模块步骤01 · 评审代码包\n\n", f"共 {len(files)} 个文件\n\n"]
    for p in files:
        rel = p.relative_to(ROOT)
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            parts.append(f"### {rel}\n\n[读取失败] {e}\n\n")
            continue
        parts.append(f"### {rel}\n\n```python\n{text}\n```\n\n")
    for d in EXPECT_ABSENT:
        if not (ROOT / d).exists():
            parts.append(f"### {d}/\n\n[缺] 目录不存在（预期为空/待建）\n\n")
    return "".join(parts)

def split_and_write(text):
    if len(text.encode("utf-8")) <= MAX_SINGLE:
        OUT_BASE.write_text(text, encoding="utf-8")
        return [OUT_BASE]
    blocks = re.split(r"(?=^### )", text, flags=re.M)
    header, chunks, cur = blocks[0], [], blocks[0]
    for b in blocks[1:]:
        if len((cur + b).encode("utf-8")) > VOL_SIZE and cur != header:
            chunks.append(cur); cur = header + b
        else:
            cur += b
    if cur:
        chunks.append(cur)
    outs = []
    for i, c in enumerate(chunks, 1):
        p = ROOT / f"pack_for_review_{i:02d}.md"
        p.write_text(c, encoding="utf-8")
        outs.append(p)
    return outs

def main():
    text = render(collect_files())
    outs = split_and_write(text)
    print(f"输出 {len(outs)} 个文件：")
    for p in outs:
        print(f"  {p.name}  {p.stat().st_size/1024:.1f} KB")
    print("\n请把上述文件内容贴回对话。")

if __name__ == "__main__":
    main()