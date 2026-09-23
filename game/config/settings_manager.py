# -*- coding: utf-8 -*-
"""设置管理：加载默认值、合并本地覆盖、就地写回 style 模块。

设计要点
--------
1. style.py 是“默认值来源”，运行时以本管理器为准。
2. apply() **就地**修改 style.py 中的 THEME / MAP_STYLE / CITY_LEVEL_MIN_SCALE /
   LAYER_VISIBILITY 等 dict 对象本身，而不是替换它们。这样所有
   `from game.config.style import MAP_STYLE` 的模块自动看到新值，
   无需改动它们的读取方式。
3. 本地文件只保存与默认值不同的项，用点号路径做 key，例如：
       {
         "version": 1,
         "overrides": {
           "THEME.info_bg": "#1A2530",
           "MAP_STYLE.point.size_divisor": 900,
           "CITY_LEVEL_MIN_SCALE.7": 320,
           "LAYER_VISIBILITY.water": true
         }
       }
   这样 style.py 未来新增字段时，老配置文件不会报错。
"""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List

from game.config import constants as C
from game.config import style as _style


# ============================================================
# 默认值快照（模块级：仅在首次 import 时执行一次）
# ============================================================
_DEFAULTS: Dict[str, Any] = {
    "THEME":               deepcopy(getattr(_style, "THEME", {})),
    "FONT_SIZES":          deepcopy(getattr(_style, "FONT_SIZES", {})),
    "FONT_CANDIDATES":     list(getattr(_style, "FONT_CANDIDATES", ())),
    "MAP_STYLE":           deepcopy(getattr(_style, "MAP_STYLE", {})),
    "CITY_LEVEL_MIN_SCALE": dict(getattr(_style, "CITY_LEVEL_MIN_SCALE", {})),
    "LAYER_VISIBILITY":    deepcopy(getattr(_style, "LAYER_VISIBILITY", {})),
}


# ============================================================
# 路径 / 类型工具
# ============================================================
def _find_key_in_dict(d, key_str):
    """在 d 中找 key_str；不存在则尝试 int(key_str)。返回实际 key 或 None。"""
    if not isinstance(d, dict):
        return None
    if key_str in d:
        return key_str
    try:
        ik = int(key_str)
    except (ValueError, TypeError):
        return None
    return ik if ik in d else None


def _get_child(d, key_str):
    k = _find_key_in_dict(d, key_str)
    if k is None:
        raise KeyError(key_str)
    return d[k]


def _coerce(value, template):
    """按 template 的类型把 value 转成合适的 Python 类型。"""
    if template is None:
        return value
    if isinstance(template, bool):
        return bool(value)
    if isinstance(template, int):
        try:
            return int(value)
        except (ValueError, TypeError):
            return template
    if isinstance(template, float):
        try:
            return float(value)
        except (ValueError, TypeError):
            return template
    if isinstance(template, str):
        return str(value)
    if isinstance(template, dict):
        if not isinstance(value, dict):
            return deepcopy(template)
        out = {}
        for k, v in value.items():
            tk = _find_key_in_dict(template, k)
            if tk is None:
                continue
            out[tk] = _coerce(v, template[tk])
        return out
    if isinstance(template, (list, tuple)):
        return list(value) if isinstance(value, (list, tuple)) else list(template)
    return value


def _apply_inplace(target, source):
    """把 source 的叶子值写回 target，保持 target 的对象 id 不变。"""
    if not isinstance(target, dict) or not isinstance(source, dict):
        return
    for k, v in source.items():
        if isinstance(v, dict) and isinstance(target.get(k), dict):
            _apply_inplace(target[k], v)
        else:
            target[k] = v


# ============================================================
# 主类
# ============================================================
class SettingsManager:
    def __init__(self, path=None):
        self.path = (Path(path) if path
             else (C.PROJECT_ROOT / "userdata" / "settings.json"))
        self.defaults: Dict[str, Any] = deepcopy(_DEFAULTS)
        self.current:  Dict[str, Any] = deepcopy(_DEFAULTS)
        self._listeners: List[Callable[[List[str]], None]] = []

        self.load()
        self.apply()

    # ---------- 加载 / 保存 ----------
    def load(self):
        self.current = deepcopy(self.defaults)
        if not self.path.is_file():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception:
            return
        overrides = data.get("overrides") or {}
        for path_str, value in overrides.items():
            try:
                template = self._get_from(self.defaults, path_str)
            except KeyError:
                continue          # 已废弃的项，忽略
            coerced = _coerce(value, template)
            try:
                self._set_into(self.current, path_str, coerced)
            except KeyError:
                continue

    def save(self):
        data = {
            "version": 1,
            "overrides": self._compute_overrides(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ---------- 读写 ----------
    def get(self, path_str):
        return self._get_from(self.current, path_str)

    def get_default(self, path_str):
        return self._get_from(self.defaults, path_str)

    def set(self, path_str, value):
        self._set_into(self.current, path_str, value)

    def set_many(self, mapping):
        for k, v in mapping.items():
            try:
                self.set(k, v)
            except KeyError:
                continue

    def reset_all(self):
        self.current = deepcopy(self.defaults)

    def reset_paths(self, paths):
        """把指定的若干路径恢复为默认值（用于“恢复本组默认”）。"""
        for p in paths:
            try:
                d = self._get_from(self.defaults, p)
                self._set_into(self.current, p, deepcopy(d))
            except KeyError:
                continue

    # ---------- 生效 / 通知 ----------
    def apply(self):
        _apply_inplace(getattr(_style, "THEME", {}),
                       self.current["THEME"])
        _apply_inplace(getattr(_style, "FONT_SIZES", {}),
                       self.current["FONT_SIZES"])
        _apply_inplace(getattr(_style, "MAP_STYLE", {}),
                       self.current["MAP_STYLE"])
        _apply_inplace(getattr(_style, "CITY_LEVEL_MIN_SCALE", {}),
                       self.current["CITY_LEVEL_MIN_SCALE"])
        _apply_inplace(getattr(_style, "LAYER_VISIBILITY", {}),
                       self.current["LAYER_VISIBILITY"])
        try:
            _style.FONT_CANDIDATES = tuple(self.current["FONT_CANDIDATES"])
        except Exception:
            pass

    def register_listener(self, fn):
        self._listeners.append(fn)

    def notify(self, changed_paths):
        for fn in list(self._listeners):
            try:
                fn(changed_paths)
            except Exception:
                pass

    # ---------- 差异 ----------
    def changed_paths(self):
        out: Dict[str, Any] = {}
        self._diff(self.defaults, self.current, "", out)
        return list(out.keys())

    def has_overrides(self):
        return bool(self.changed_paths())

    # ---------- 内部 ----------
    @staticmethod
    def _get_from(root, path_str):
        node = root
        for part in path_str.split("."):
            node = _get_child(node, part)
        return node

    @staticmethod
    def _set_into(root, path_str, value):
        parts = path_str.split(".")
        node = root
        for part in parts[:-1]:
            node = _get_child(node, part)
        k = _find_key_in_dict(node, parts[-1])
        if k is None:
            raise KeyError(path_str)
        node[k] = value

    def _compute_overrides(self):
        out: Dict[str, Any] = {}
        self._diff(self.defaults, self.current, "", out)
        return out

    def _diff(self, default, current, prefix, out):
        if isinstance(current, dict):
            for k, v in current.items():
                d = default.get(k) if isinstance(default, dict) else None
                path = f"{prefix}.{k}" if prefix else str(k)
                self._diff(d, v, path, out)
        else:
            if current != default:
                out[prefix] = current