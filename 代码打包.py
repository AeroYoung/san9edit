# pack_for_review.py
"""打包本次需求评审所需代码，输出 markdown（超 300KB 自动分卷）。"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_NAME = "review_pack"
MAX_TOTAL = 300 * 1024      # 单文档上限
VOL_TARGET = 90 * 1024      # 分卷目标大小

# 本次需要评审的代码文件（相对项目根）
CODE_FILES = [
    "game/config/rules.py",
    "game/core/military_title.py",
    "game/core/character.py",
    "game/ui/panels/character_panel.py",
]

EXT_LANG = {
    ".py": "python", ".json": "json", ".md": "markdown",
    ".txt": "text", ".toml": "toml", ".yaml": "yaml", ".yml": "yaml",
}


def _read(rel: str):
    p = ROOT / rel
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"[读取失败] {e}"


def _section(rel: str) -> str:
    lang = EXT_LANG.get(Path(rel).suffix, "text")
    text = _read(rel)
    if text is None:
        return f"### {rel}\n[缺] {rel}\n"
    return f"### {rel}\n\n```{lang}\n{text}\n```\n"


def main():
    sections = [_section(rel) for rel in CODE_FILES]
    missing = [r for r in CODE_FILES if not (ROOT / r).exists()]

    header = (
        "# 需求评审代码包\n\n"
        f"项目根：{ROOT}\n\n"
        f"文件数：{len(CODE_FILES)}（缺 {len(missing)}）\n\n"
    )
    if missing:
        header += "缺失文件：\n" + "\n".join(f"- [缺] {m}" for m in missing) + "\n\n"

    total = len(header.encode("utf-8")) + sum(len(s.encode("utf-8")) for s in sections)

    outputs = []
    if total <= MAX_TOTAL:
        out = ROOT / f"{BASE_NAME}.md"
        out.write_text(header + "\n".join(sections), encoding="utf-8")
        outputs.append(out)
    else:
        buf, buf_size, idx = [header], len(header.encode("utf-8"))
        for sec in sections:
            size = len(sec.encode("utf-8"))
            if buf_size + size > VOL_TARGET and len(buf) > 1:
                out = ROOT / f"{BASE_NAME}_{idx:02d}.txt"
                out.write_text("".join(buf), encoding="utf-8")
                outputs.append(out)
                idx += 1
                buf, buf_size = [], 0
            buf.append(sec)
            buf_size += size
        if buf:
            out = ROOT / f"{BASE_NAME}_{idx:02d}.txt"
            out.write_text("".join(buf), encoding="utf-8")
            outputs.append(out)

    print("=" * 60)
    for o in outputs:
        print(f"输出：{o}  （{o.stat().st_size / 1024:.1f} KB）")
    print("=" * 60)
    print("请把上面所有文件的内容贴回对话（如有分卷，全部贴回）。")


if __name__ == "__main__":
    main()