#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把头像文件重命名为 {id}-{名字}.{ext}。

规则
----
1. 图片名 == 人物 name（精确匹配）→ 重命名为 {id}-{name}{ext}
2. 同名多人（如两个张南）→ 复制成 {id1}-张南.ext、{id2}-张南.ext
3. 数据里没有的人 → 不动，仅列出

安全
----
- 顶部 APPLY 常量控制执行：False = 只预览，True = 真正落盘
- 重名复制默认保留原文件（REMOVE_ORIGINAL = False）
- 目标已存在时默认跳过（FORCE = False）
- 幂等：已是 {id}-{name} 形式的文件不会再被处理

用法
----
    1. 先保持 APPLY = False 跑一次，看清单
    2. 确认无误后把 APPLY 改成 True，再跑
"""

import json
import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CHARS = PROJECT_ROOT / "assets" / "characters.json"
DEFAULT_PORTRAIT_DIR = PROJECT_ROOT / "assets" / "portrait"

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}


# ============================================================
# ★ 执行开关
# ============================================================
# False = 只预览（dry-run），不落盘
# True  = 真正执行
# 确认预览无误后，手动改成 True 再跑
APPLY = True

# 重名复制后是否删除原文件
# False = 保留原文件（默认，安全）
# True  = 复制后删掉原图
REMOVE_ORIGINAL = False

# 目标已存在时是否覆盖
# False = 跳过并报告
# True  = 覆盖
FORCE = False


def load_characters(path: Path) -> dict:
    """兼容 {id: {...}} / {"characters": {...}} / [...] 三种结构。"""
    raw = json.loads(path.read_text(encoding="utf-8"))

    def _norm_list(lst):
        return {str(c.get("id", i)): c for i, c in enumerate(lst)}

    if isinstance(raw, list):
        return _norm_list(raw)
    if isinstance(raw, dict):
        inner = raw.get("characters")
        if isinstance(inner, list):
            return _norm_list(inner)
        if isinstance(inner, dict):
            return {str(k): v for k, v in inner.items()}
        if all(isinstance(v, dict) for v in raw.values()):
            return {str(k): v for k, v in raw.items()}
    raise ValueError(f"无法识别的 characters.json 结构：{path}")


def scan_portraits(dir_: Path):
    return [p for p in sorted(dir_.iterdir())
            if p.is_file() and p.suffix.lower() in IMAGE_EXTS]


def build_plan(chars, portraits, keep_original):
    by_name = {}
    for cid, c in chars.items():
        nm = (c.get("name") or "").strip()
        if nm:
            by_name.setdefault(nm, []).append(cid)

    renames = []   # [(src, dst)]
    copies = []    # [(src, dst)]
    deletes = []   # [src]（仅 REMOVE_ORIGINAL=True 时非空）
    unknown = []   # [(src, stem)]
    skipped = []   # [(src, reason)]

    for p in portraits:
        stem = p.stem.strip()
        ids = by_name.get(stem)
        if not ids:
            unknown.append((p, stem))
            continue

        if len(ids) == 1:
            dst = p.with_name(f"{ids[0]}-{stem}{p.suffix}")
            if dst == p:
                skipped.append((p, "已是目标名"))
            else:
                renames.append((p, dst))
        else:
            for cid in ids:
                dst = p.with_name(f"{cid}-{stem}{p.suffix}")
                if dst == p:
                    skipped.append((p, f"已是目标名 {dst.name}"))
                    continue
                copies.append((p, dst))
            if not keep_original:
                deletes.append(p)

    return renames, copies, deletes, unknown, skipped


def print_plan(renames, copies, deletes, unknown, skipped, keep_original):
    print("=" * 70)
    print("重命名计划" + ("" if APPLY else "（预览）"))
    print("=" * 70)

    if renames:
        print(f"\n[重命名] {len(renames)} 个：")
        for src, dst in renames:
            print(f"  {src.name}  ->  {dst.name}")
    else:
        print("\n[重命名] 无")

    if copies:
        print(f"\n[复制] {len(copies)} 个（重名武将）：")
        for src, dst in copies:
            print(f"  {src.name}  ->  {dst.name}")

    if deletes:
        print(f"\n[删除原文件] {len(deletes)} 个：")
        for src in deletes:
            print(f"  {src.name}")

    if skipped:
        print(f"\n[跳过] {len(skipped)} 个：")
        for src, reason in skipped:
            print(f"  {src.name}  （{reason}）")

    if unknown:
        print(f"\n[未匹配-不动] {len(unknown)} 个：")
        for src, _ in unknown:
            print(f"  {src.name}")

    print()
    print("-" * 70)
    print(f"汇总：重命名 {len(renames)}，复制 {len(copies)}，"
          f"删除 {len(deletes)}，跳过 {len(skipped)}，未匹配 {len(unknown)}")
    print(f"重名源文件：{'保留' if keep_original else '删除'}")
    print("-" * 70)


def execute(renames, copies, deletes, force):
    done_ren = done_cop = done_del = 0
    failed = []

    for src, dst in renames:
        if dst.exists() and not force:
            failed.append((src, dst, "目标已存在"))
            continue
        try:
            if dst.exists() and force:
                dst.unlink()
            src.rename(dst)
            done_ren += 1
        except Exception as e:
            failed.append((src, dst, str(e)))

    for src, dst in copies:
        if dst.exists() and not force:
            failed.append((src, dst, "目标已存在"))
            continue
        try:
            shutil.copy2(src, dst)
            done_cop += 1
        except Exception as e:
            failed.append((src, dst, str(e)))

    for src in deletes:
        try:
            if src.exists():
                src.unlink()
                done_del += 1
        except Exception as e:
            failed.append((src, None, str(e)))

    return done_ren, done_cop, done_del, failed


def main():
    chars_path = DEFAULT_CHARS
    portrait_dir = DEFAULT_PORTRAIT_DIR

    if not chars_path.is_file():
        print(f"[错误] 找不到：{chars_path}", file=sys.stderr)
        return 2
    if not portrait_dir.is_dir():
        print(f"[错误] 找不到：{portrait_dir}", file=sys.stderr)
        return 2

    chars = load_characters(chars_path)
    portraits = scan_portraits(portrait_dir)
    print(f"人物数据：{len(chars)} 条")
    print(f"头像文件：{len(portraits)} 张\n")

    keep_original = not REMOVE_ORIGINAL
    renames, copies, deletes, unknown, skipped = build_plan(
        chars, portraits, keep_original=keep_original,
    )
    print_plan(renames, copies, deletes, unknown, skipped, keep_original)

    if not APPLY:
        print("\n>>> 这是预览。把顶部 APPLY 改成 True 才真正执行。")
        return 0

    print("\n>>> 执行中 ...")
    done_ren, done_cop, done_del, failed = execute(
        renames, copies, deletes, force=FORCE,
    )
    print(f"\n完成：重命名 {done_ren}，复制 {done_cop}，删除 {done_del}")
    if failed:
        print(f"\n失败 {len(failed)} 项：")
        for src, dst, reason in failed:
            tgt = f" -> {dst.name}" if dst else ""
            print(f"  {src.name}{tgt}  （{reason}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())