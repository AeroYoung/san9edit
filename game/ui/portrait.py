# -*- coding: utf-8 -*-
"""头像加载（Pillow 只在这里用，其它地方不得引入）。

路径约定：assets/portrait/{id}-{name}.{ext}，不读 Character.portrait 字段。
未安装 Pillow 或找不到文件 → 返回 (None, 说明文字)，由调用方降级显示。
"""

import logging

from game.config import constants as C

logger = logging.getLogger(__name__)

PORTRAIT_DIR = C.ASSETS_DIR / "portrait"
PORTRAIT_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")

try:
    from PIL import Image, ImageTk
    PIL_OK = True
except ImportError:          # pragma: no cover - 取决于运行环境
    PIL_OK = False
    logger.warning("未安装 Pillow，无法显示头像")


def portrait_path(character_id, name):
    """按 {id}-{name}.{ext} 拼路径；找不到 → None。"""
    base = f"{character_id}-{name}"
    for ext in PORTRAIT_EXTS:
        path = PORTRAIT_DIR / f"{base}{ext}"
        if path.is_file():
            return path
    return None


def load_thumbnail(path, width, height, master=None):
    """打开 + 等比缩略 → (PhotoImage | None, 说明文字 | None)。

    ★ 调用方必须持有返回的 PhotoImage 引用，否则被 GC 后显示空白。
    """
    if path is None:
        return None, "（无头像）"
    if not PIL_OK:
        return None, "未安装 Pillow\n无法显示 JPG"
    try:
        img = Image.open(path).convert("RGB")      # 带 alpha / 灰度图统一转 RGB
        img.thumbnail((width, height), Image.LANCZOS)
        return ImageTk.PhotoImage(img, master=master), None
    except Exception as e:                          # noqa: BLE001 - 降级不崩
        logger.warning("头像加载失败：%s", path, exc_info=True)
        return None, f"（加载失败）\n{e}"
