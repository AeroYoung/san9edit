# -*- coding: utf-8 -*-
"""人物情报窗口。

当前只显示头像。后续可扩展：五维 / 关系 / 生平。

头像路径约定：assets/portrait/{id}-{name}.{ext}
    例如 0651-张南.jpg
不再读取 Character.portrait 字段。
"""

import tkinter as tk

from game.config import constants as C
from game.config.style import THEME, FONT_SIZES
from game.ui.window_utils import center_on_parent

try:
    from PIL import Image, ImageTk
    _PIL_OK = True
except ImportError:
    _PIL_OK = False


PORTRAIT_DIR = C.ASSETS_DIR / "portrait"
PORTRAIT_EXTS = (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")

MAX_W = 200
MAX_H = 200


class CharacterInfoWindow(tk.Toplevel):
    def __init__(self, master, character, font_family="TkDefaultFont"):
        super().__init__(master)
        self.character = character
        self.font_family = font_family
        self._photo = None    # ★ 保引用，防 GC

        self.title(f"{character.display_name()} — 人物情报")
        self.transient(master)
        self.configure(bg=THEME["panel_bg"])
        self.resizable(False, False)

        self._build_ui()
        self._load_portrait()

        # 尺寸确定后再居中
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), 260)
        h = max(self.winfo_reqheight(), 340)
        center_on_parent(self, master, w, h)

        try:
            self.grab_set()
        except Exception:
            pass
        self.bind("<Escape>", lambda e: self.destroy())
        self.focus_set()

    # ------------------------------------------------------------
    def _build_ui(self):
        # 名字
        tk.Label(
            self, text=self.character.display_name(),
            bg=THEME["panel_bg"], fg="#222222",
            font=(self.font_family, FONT_SIZES["panel_title"] + 4, "bold"),
        ).pack(pady=(14, 6))

        # 头像框（固定 200×200，图片居中）
        frame = tk.Frame(
            self, bg=THEME["panel_header_bg"],
            width=MAX_W, height=MAX_H,
            highlightthickness=1,
            highlightbackground=THEME["status_sep"],
        )
        frame.pack(padx=16, pady=6)
        frame.pack_propagate(False)

        self._portrait_label = tk.Label(
            frame, bg=THEME["panel_header_bg"],
        )
        self._portrait_label.pack(expand=True, fill="both")

        tk.Frame(self, bg=THEME["panel_bg"], height=10).pack()

    # ------------------------------------------------------------
    def _find_portrait_path(self):
        base = f"{self.character.id}-{self.character.name}"
        for ext in PORTRAIT_EXTS:
            p = PORTRAIT_DIR / f"{base}{ext}"
            if p.is_file():
                return p
        return None

    def _load_portrait(self):
        path = self._find_portrait_path()
        if path is None:
            self._portrait_label.configure(
                text="（无头像）", fg="#999999",
                font=(self.font_family, FONT_SIZES["panel_body"]),
            )
            return

        if not _PIL_OK:
            self._portrait_label.configure(
                text="未安装 Pillow\n无法显示 JPG", fg="#B03A2E",
                font=(self.font_family, FONT_SIZES["panel_body"]),
            )
            return

        try:
            img = Image.open(path).convert("RGB")
            img.thumbnail((MAX_W, MAX_H), Image.LANCZOS)
            self._photo = ImageTk.PhotoImage(img)
            self._portrait_label.configure(image=self._photo, text="")
        except Exception as e:
            self._portrait_label.configure(
                text=f"（加载失败）\n{e}", fg="#B03A2E",
                font=(self.font_family, FONT_SIZES["panel_body"]),
            )