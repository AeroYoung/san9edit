# -*- coding: utf-8 -*-
"""打包 battle/ 相关文件供需求分析（步骤02 UI 调整）。"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAX_SINGLE = 300 * 1024      # 单文档上限，超过则分卷
VOL_TARGET = 90 * 1024       # 每卷目标大小

CODE_FILES = [
    "battle/config.py",
    "battle/balance.py",
    "battle/app.py",
    "battle/render/panel.py",
    "battle/render/console.py",
    "battle/render/widgets.py",
    "battle/render/camera.py",
    "battle/render/unit_layer.py",
    "battle/render/symbol.py",
    "battle/render/hex_renderer.py",
    "battle/core/unit.py",
    "battle/core/unit_types.py",
    "battle/core/battle_state.py",
    "battle/core/hexgrid.py",
    "battle/core/map_data.py",
    "battle/docs/步骤02需求.md",
]

JSON_FULL = [
    "battle/assets/maps/default.json",
]

JSON_SLICED = [
    ("battle/data/side_red.json", 3, 0),
    ("battle/data/side_blue.json", 3, 0),
]


def read_text(rel):
    p = ROOT / rel
    if not p.exists():
        return None
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return p.read_text(encoding="utf-8", errors="replace")


def slice_json(path, head, tail):
    """顶层元字段 + 指定段的 head 条 + tail 条。"""
    p = ROOT / path
    if not p.exists():
        return None, "[缺] " + path
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return None, "[读取失败] %s: %s" % (path, e)

    if not isinstance(data, dict):
        return data, None

    out = {}
    # 元字段（非 list 值直接保留）
    for k, v in data.items():
        if not isinstance(v, list):
            out[k] = v

    # list 段做截取
    for k, v in data.items():
        if not isinstance(v, list):
            continue
        seg = v[:head] if head else []
        if tail and len(v) > head + tail:
            seg = seg + ["……（省略 %d 条）……" % (len(v) - head - tail)] + v[-tail:]
        out[k] = seg
    return out, None


def block(title, lang, text):
    return "### %s\n\n```%s\n%s\n```\n\n" % (title, lang, text)


def build_blocks():
    blocks = []
    missing = []

    for rel in CODE_FILES:
        txt = read_text(rel)
        if txt is None:
            missing.append(rel)
            blocks.append(block(rel, "text", "[缺] " + rel))
        else:
            lang = "markdown" if rel.endswith(".md") else "python"
            blocks.append(block(rel, lang, txt))

    for rel in JSON_FULL:
        txt = read_text(rel)
        if txt is None:
            missing.append(rel)
            blocks.append(block(rel, "text", "[缺] " + rel))
        else:
            blocks.append(block(rel, "json", txt))

    for rel, head, tail in JSON_SLICED:
        data, err = slice_json(rel, head, tail)
        if err:
            missing.append(rel)
            blocks.append(block(rel, "text", err))
        else:
            note = "截取：元字段 + 首 %d 条" % head
            body = "// %s\n" % note + json.dumps(data, ensure_ascii=False, indent=2)
            blocks.append(block(rel, "json", body))

    return blocks, missing


def write_volumes(blocks):
    total = sum(len(b.encode("utf-8")) for b in blocks)
    if total <= MAX_SINGLE:
        out = ROOT / "pack_for_review.md"
        out.write_text("".join(blocks), encoding="utf-8")
        return [out]

    volumes, cur, size = [], [], 0
    for b in blocks:
        bs = len(b.encode("utf-8"))
        if cur and size + bs > VOL_TARGET:
            volumes.append(cur)
            cur, size = [], 0
        cur.append(b)
        size += bs
    if cur:
        volumes.append(cur)

    outs = []
    for i, vol in enumerate(volumes, 1):
        out = ROOT / ("pack_for_review_%02d.txt" % i)
        out.write_text("".join(vol), encoding="utf-8")
        outs.append(out)
    return outs


def main():
    blocks, missing = build_blocks()
    outs = write_volumes(blocks)

    print("=" * 52)
    for o in outs:
        print("输出：%s  (%.1f KB)" % (o.name, o.stat().st_size / 1024))
    if missing:
        print("-" * 52)
        print("缺失（已在正文标 [缺]）：")
        for m in missing:
            print("  " + m)
    print("-" * 52)
    print("请把上面文件内容贴回对话。")
    print("=" * 52)


if __name__ == "__main__":
    main()