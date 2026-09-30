# -*- coding: utf-8 -*-
"""右侧面板组（浮于地图之上，不占地图布局空间）。

Tab1「我方部队」/ Tab2「敌方部队」：分组按钮条 → 表头 → 列表 → 部队情报组。
Tab3 / Tab4 留空，内容区居中灰字。

只读数据：不写 `BattleState` / `Unit` 的任何字段。
"""

import logging

import pygame

from battle import balance
from battle import config
from battle.render import symbol as sym
from battle.render import unit_layer
from battle.render import widgets

logger = logging.getLogger("battle.render.panel")

_PAD = 12
_DOUBLE_CLICK_MS = 400
_DOUBLE_CLICK_SLOP = 4
_EDGE_HIT_PX = 3          # 列右边界命中半宽
_MIN_COL_W = 32
_MIN_NAME_W = 48
_SYMBOL_CELL_SCALE = 1.2  # 符号列缩略图边长 = 行高 × 此值
_VALUE_LABEL_W = 84       # 情报组标签列宽
_SCROLLBAR_W = 6

# 右键菜单
_MENU_ITEM_H = 26
_MENU_PAD_X = 12
_MENU_PAD_Y = 6
_MENU_MIN_W = 140
_MENU_BG = (44, 50, 62)
_MENU_TEXT_DISABLED = (118, 124, 134)

# 列定义：(key, 表头, 默认宽度权重, 对齐)
_COLUMNS = (
    ("symbol", "", 34, "center"),
    ("name", "部队", 96, "left"),
    ("status", "状态", 56, "center"),
    ("troops", "兵力", 62, "right"),
    ("morale", "士气", 52, "right"),
    ("stamina", "体力", 52, "right"),
    ("command", "命令", 76, "left"),
)
_NAME_INDEX = 1

# 分组维度：(key, 显示名)
_GROUP_DIMS = (("type", "兵种"), ("status", "状态"))
_DEFAULT_GROUP_DIM = "type"
_STATUS_TEXT = "待命"     # 本阶段固定值（命令系统未落地）

_ROW_ALT_BG = config.PANEL_ROW_ALT_BG
_ROW_HOVER_BG = config.PANEL_ROW_HOVER_BG
_ROW_SELECTED_BG = config.PANEL_ROW_SELECTED_BG
_GROUP_ROW_BG = (44, 50, 62)
_HEADER_FG = (176, 184, 196)
_SCROLLBAR_BG = (38, 44, 54)
_SCROLLBAR_FG = (108, 118, 138)
_GROUP_INDENT = 16


class Panel:
    """右侧面板组。"""

    def __init__(self, state, on_selection=None, on_locate=None):
        self.state = state
        # on_selection(unit_ids, mode)：mode ∈ {"replace", "toggle", "range"}
        self.on_selection = on_selection
        # on_locate(unit)：右键「定位到地图」→ 由 app 负责相机移动
        self.on_locate = on_locate
        self.active_tab = 0
        self.group_dim = _DEFAULT_GROUP_DIM
        self.collapsed = set()          # 折叠的组 key
        self.sort_key = None
        self.sort_reverse = False
        self.scroll = 0
        self._anchor_row = None         # Shift 单击的锚（展示行序）

        self._widths = {}               # tab → 用户拖动后的像素列宽
        self._drag = None               # (col_index, start_x, start_width)
        self._last_click = (0, (0, 0))

        self._rect = pygame.Rect(0, 0, 0, 0)
        self._content = pygame.Rect(0, 0, 0, 0)
        self._bar_rect = pygame.Rect(0, 0, 0, 0)
        self._header_rect = pygame.Rect(0, 0, 0, 0)
        self._list_rect = pygame.Rect(0, 0, 0, 0)
        self._info_rect = pygame.Rect(0, 0, 0, 0)
        self._tab_rects = []
        self._dim_btns = []
        self._columns = []              # (key, 表头, 对齐, x, w)
        self._bg = None
        self._context_menu = None      # (rect, [(label, enabled, callback), ...])
        self._viewport_key = None

    # ============================================================
    # 尺寸
    # ============================================================
    @property
    def tab_h(self):
        return config.PANEL_TAB_HEIGHT

    @property
    def row_h(self):
        return config.FONT_SIZE_PANEL_CELL + 10

    @property
    def header_h(self):
        return config.FONT_SIZE_PANEL_HEADER + 12

    @property
    def bar_h(self):
        return config.FONT_SIZE_PANEL_CELL + 12

    # ============================================================
    # 布局
    # ============================================================
    def layout(self, viewport_size):
        """按视口重算面板矩形与各分区；屏幕过小时按比例收窄（不遮挡整屏）。"""
        vw, vh = viewport_size
        width = max(160, min(config.PANEL_WIDTH, int(vw * 0.4)))
        margin = config.PANEL_MARGIN
        height = max(160, vh - 2 * margin)
        self._rect = pygame.Rect(vw - margin - width, margin, width, height)

        tab_count = max(1, len(config.PANEL_TAB_TITLES))
        tab_w = width // tab_count
        self._tab_rects = [
            pygame.Rect(self._rect.left + i * tab_w, self._rect.top, tab_w, self.tab_h)
            for i in range(tab_count)
        ]

        self._content = pygame.Rect(self._rect.left + _PAD,
                                    self._rect.top + self.tab_h + 4,
                                    width - 2 * _PAD,
                                    height - self.tab_h - 4 - _PAD)

        info_h = max(config.UNIT_INFO_MIN_HEIGHT,
                     int(self._content.height * config.UNIT_INFO_HEIGHT_RATIO))
        if self._content.height - info_h - self.header_h - self.bar_h < self.row_h * 2:
            info_h = self.row_h + 8      # 面板过矮：情报组折叠为 1 行标题
        self._info_rect = pygame.Rect(self._content.left,
                                      self._content.bottom - info_h,
                                      self._content.width, info_h)

        self._bar_rect = pygame.Rect(self._content.left, self._content.top,
                                     self._content.width, self.bar_h)
        self._header_rect = pygame.Rect(self._content.left,
                                        self._content.top + self.bar_h,
                                        self._content.width, self.header_h)
        list_top = self._header_rect.bottom
        self._list_rect = pygame.Rect(self._content.left, list_top,
                                      self._content.width,
                                      max(0, self._info_rect.top - list_top))

        self._build_dim_buttons()
        self._build_columns()
        self._viewport_key = (vw, vh)
        self._bg = widgets.make_round_panel(self._rect.size)
        self._clamp_scroll()

    def _build_dim_buttons(self):
        self._dim_btns = []
        x = self._bar_rect.left
        for key, title in _GROUP_DIMS:
            btn = widgets.Button((x, self._bar_rect.top + 2, 72, self.bar_h - 6),
                                 title, font_size=config.FONT_SIZE_PANEL_CELL)
            self._dim_btns.append((key, btn))
            x += 78

    def _build_columns(self):
        """按当前 Tab 的列宽（用户拖动过则用像素值，否则按权重分配）重算各列 x / w。"""
        keys = [c[0] for c in _COLUMNS]
        widths = self._column_widths(len(keys))

        # 屏宽过小时从右往左裁列，保证 name 列不低于 _MIN_NAME_W
        # （用户手动拖过列宽则尊重用户值，只按 §3.10.8 裁切超出部分）
        if self._widths.get(self.active_tab) is None:
            while len(widths) > 2 and widths[_NAME_INDEX] < _MIN_NAME_W:
                widths = self._column_widths(len(widths) - 1)

        self._columns = []
        x = self._header_rect.left
        for index, (key, title, _weight, align) in enumerate(_COLUMNS[:len(widths)]):
            w = widths[index]
            self._columns.append((key, title, align, x, w))
            x += w

    def _column_widths(self, count):
        """列宽列表：用户拖动过 → 用像素；否则按默认权重分配，余量补到 name 列。"""
        saved = self._widths.get(self.active_tab)
        if saved is not None:
            return list(saved[:count])

        weights = [c[2] for c in _COLUMNS[:count]]
        total = float(sum(weights)) or 1.0
        content_w = self._header_rect.width
        widths = [int(round(content_w * w / total)) for w in weights]
        widths[_NAME_INDEX] += content_w - sum(widths)
        return widths

    def rect(self):
        return self._rect

    def point_inside(self, pos):
        return self._rect.collidepoint(pos)

    # ============================================================
    # 数据
    # ============================================================
    def _side(self):
        sides = config.PANEL_TAB_SIDES
        if 0 <= self.active_tab < len(sides):
            return sides[self.active_tab]
        return None

    def _units(self):
        side = self._side()
        if side is None:
            return []
        return self.state.units_of(side)

    def _entries(self):
        """展示项列表：`("group", key, 标题, 行数)` / `("row", unit)`。"""
        units = self._sorted_units(self._units())
        if self.group_dim is None:
            return [("row", u) for u in units], units

        buckets = {}
        for unit in units:
            key = self._group_key(unit)
            buckets.setdefault(key, []).append(unit)

        entries = []
        ordered = []
        for key in self._group_order(buckets):
            members = buckets[key]
            ordered.extend(members)
            entries.append(("group", key, "%s（%s）" % (key, len(members)), len(members)))
            if key not in self.collapsed:
                for unit in members:
                    entries.append(("row", unit))
        return entries, ordered

    def _sorted_units(self, units):
        if self.sort_key is None:
            return list(units)
        return sorted(units, key=self._sort_value(self.sort_key),
                      reverse=self.sort_reverse)

    def _sort_value(self, key):
        if key == "name":
            return lambda u: "%s %s" % (u.name, u.id)
        if key == "status":
            return lambda u: _STATUS_TEXT
        if key == "troops":
            return lambda u: u.troops
        if key == "morale":
            return lambda u: u.morale
        if key == "stamina":
            return lambda u: u.stamina
        if key == "command":
            return lambda u: ""
        return lambda u: u.id

    def _group_key(self, unit):
        if self.group_dim == "status":
            return _STATUS_TEXT
        return unit.name or "（未知兵种）"

    def _group_order(self, buckets):
        """组顺序：兵种按 balance.UNIT_TYPES 声明序；状态按字典序。"""
        if self.group_dim == "status":
            return sorted(buckets)
        declared = [t["name"] for t in balance.UNIT_TYPES.values()]
        known = [n for n in declared if n in buckets]
        extra = sorted(k for k in buckets if k not in declared)
        return known + extra

    def _row_units_in_order(self, entries):
        return [item[1] for item in entries if item[0] == "row"]

    # ============================================================
    # 事件
    # ============================================================
    def handle_event(self, event):
        """返回 True = 事件已被面板消费（不再交给地图）。"""
        # 0. 右键菜单打开时，拦截鼠标点击
        if self._context_menu is not None:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self._handle_menu_click(event.pos)
                    return True
                if event.button == 3:
                    self._close_context_menu()   # 关掉旧的，继续走下面重开
            elif event.type == pygame.MOUSEWHEEL:
                self._close_context_menu()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.point_inside(event.pos):
                return False
            return self._on_click(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            if not self.point_inside(event.pos):
                return False
            self._open_context_menu(event.pos)
            return True

        if event.type == pygame.MOUSEMOTION and self._drag is not None:
            self._on_drag(event.pos)
            return True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._drag is not None:
                self._drag = None
                return True
            return False

        if event.type == pygame.MOUSEWHEEL:
            if not self.point_inside(pygame.mouse.get_pos()):
                return False
            if self._list_rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll -= event.y * self.row_h * 3
                self._clamp_scroll()
            return True

        return False

    def _on_click(self, pos):
        # 1. Tab
        for index, rect in enumerate(self._tab_rects):
            if rect.collidepoint(pos):
                if index != self.active_tab:
                    self.active_tab = index
                    self.sort_key = None
                    self.sort_reverse = False
                    self.collapsed.clear()
                    self.scroll = 0
                    self._anchor_row = None
                    self._build_columns()
                    self._clamp_scroll()
                return True

        if self._side() is None:
            return True   # 留空 Tab：吞掉点击

        # 2. 分组维度按钮
        for key, btn in self._dim_btns:
            if btn.hit_test(pos):
                self.group_dim = None if self.group_dim == key else key
                self.scroll = 0
                self._anchor_row = None
                return True

        # 3. 表头：列边界拖动 / 双击
        if self._header_rect.collidepoint(pos):
            edge = self._edge_column_at(pos[0])
            double = self._is_double_click(pos)
            if edge is not None:
                if double:
                    self._autofit_column(edge)
                else:
                    self._drag = (edge, pos[0], self._columns[edge][4])
                return True
            column = self._column_at(pos[0])
            if column is not None and self._columns[column][0] != "symbol" and double:
                self._toggle_sort(self._columns[column][0])
            return True

        # 4. 列表区
        if self._list_rect.collidepoint(pos):
            self._on_list_click(pos)
        return True

    # ---------------- 右键菜单 ----------------
    def _open_context_menu(self, pos):
        if self._side() is None:
            return          # 空 Tab 不弹
        unit = None
        if self._list_rect.collidepoint(pos):
            entries, _ = self._entries()
            index = int((pos[1] - self._list_rect.top + self.scroll) // self.row_h)
            if 0 <= index < len(entries) and entries[index][0] == "row":
                unit = entries[index][1]
        items = self._build_menu_items(unit)
        rect = self._make_menu_rect(pos, items)
        self._context_menu = (rect, items)

    def _close_context_menu(self):
        self._context_menu = None

    def _build_menu_items(self, unit):
        items = []
        if unit is not None:
            items.append(("定位到地图", True,
                          lambda u=unit: self._locate(u)))
        items.append(("全部展开", True, self._expand_all))
        items.append(("全部折叠", True, self._collapse_all))
        return items

    def _make_menu_rect(self, pos, items):
        font = widgets.get_font(config.FONT_SIZE_PANEL_CELL)
        w = max((font.size(label)[0] for label, _, _ in items), default=80)
        w = max(_MENU_MIN_W, w + 2 * _MENU_PAD_X)
        h = len(items) * _MENU_ITEM_H + 2 * _MENU_PAD_Y
        x, y = pos
        try:
            sw, sh = pygame.display.get_surface().get_size()
        except Exception:
            sw = sh = 10 ** 6
        x = max(0, min(x, sw - w - 4))
        y = max(0, min(y, sh - h - 4))
        return pygame.Rect(x, y, w, h)

    def _handle_menu_click(self, pos):
        """菜单内左键：命中项执行回调；返回 True（事件被吞）。"""
        if self._context_menu is None:
            return False
        rect, items = self._context_menu
        if rect.collidepoint(pos):
            index = (pos[1] - rect.top - _MENU_PAD_Y) // _MENU_ITEM_H
            if 0 <= index < len(items):
                _label, enabled, cb = items[index]
                self._close_context_menu()
                if enabled and cb is not None:
                    cb()
                return True
        self._close_context_menu()
        return True

    def _locate(self, unit):
        if self.on_locate is not None:
            self.on_locate(unit)

    def _expand_all(self):
        self.collapsed.clear()
        self._clamp_scroll()

    def _collapse_all(self):
        entries, _ = self._entries()
        self.collapsed = {e[1] for e in entries if e[0] == "group"}
        self._clamp_scroll()

    def _on_list_click(self, pos):
        entries, _ = self._entries()
        index = int((pos[1] - self._list_rect.top + self.scroll) // self.row_h)
        if not (0 <= index < len(entries)):
            return
        item = entries[index]
        if item[0] == "group":
            key = item[1]
            if key in self.collapsed:
                self.collapsed.discard(key)
            else:
                self.collapsed.add(key)
            self._clamp_scroll()
            return

        unit = item[1]
        if self.on_selection is None:
            return
        mods = pygame.key.get_mods()
        if mods & pygame.KMOD_CTRL:
            self._anchor_row = index
            self.on_selection([unit.id], "toggle")
        elif mods & pygame.KMOD_SHIFT and self._anchor_row is not None:
            lo, hi = sorted((self._anchor_row, index))
            ids = [it[1].id for it in entries[lo:hi + 1] if it[0] == "row"]
            self.on_selection(ids, "range")
        else:
            self._anchor_row = index
            self.on_selection([unit.id], "replace")

    def _is_double_click(self, pos):
        now = pygame.time.get_ticks()
        last_ms, last_pos = self._last_click
        self._last_click = (now, pos)
        return (now - last_ms <= _DOUBLE_CLICK_MS
                and abs(pos[0] - last_pos[0]) <= _DOUBLE_CLICK_SLOP
                and abs(pos[1] - last_pos[1]) <= _DOUBLE_CLICK_SLOP)

    def _column_at(self, x):
        for index, (_key, _title, _align, left, width) in enumerate(self._columns):
            if left <= x < left + width:
                return index
        return None

    def _edge_column_at(self, x):
        """命中某列右边界（±_EDGE_HIT_PX）→ 该列下标。"""
        for index, (_key, _title, _align, left, width) in enumerate(self._columns):
            if abs(x - (left + width)) <= _EDGE_HIT_PX:
                return index
        return None

    def _on_drag(self, pos):
        index, start_x, start_w = self._drag
        if index >= len(self._columns):
            return
        width = max(_MIN_COL_W, min(int(self._header_rect.width * 0.6),
                                    start_w + (pos[0] - start_x)))
        widths = [c[4] for c in self._columns]
        widths[index] = width
        self._widths[self.active_tab] = widths
        self._rebuild_columns_keep_widths()

    def _rebuild_columns_keep_widths(self):
        widths = self._widths.get(self.active_tab)
        if not widths:
            return
        self._columns = []
        x = self._header_rect.left
        for index, (key, title, _w, align) in enumerate(_COLUMNS[:len(widths)]):
            self._columns.append((key, title, align, x, widths[index]))
            x += widths[index]

    def _autofit_column(self, index):
        key = self._columns[index][0]
        font = widgets.get_font(config.FONT_SIZE_PANEL_CELL)
        entries, _ = self._entries()
        widest = font.size(_COLUMNS[index][1])[0]
        for item in entries:
            if item[0] == "row":
                widest = max(widest, font.size(self._cell_text(item[1], key))[0])
        widths = [c[4] for c in self._columns]
        widths[index] = max(_MIN_COL_W,
                            min(int(self._header_rect.width * 0.6), widest + 16))
        self._widths[self.active_tab] = widths
        self._rebuild_columns_keep_widths()

    def _toggle_sort(self, key):
        if self.sort_key == key:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_key = key
            self.sort_reverse = False
        self.scroll = 0
        self._anchor_row = None

    def _clamp_scroll(self):
        total = len(self._entries()[0]) * self.row_h
        self.scroll = max(0, min(self.scroll, max(0, total - self._list_rect.height)))

    # ============================================================
    # 绘制
    # ============================================================
    def draw(self, surface, viewport_size, selected):
        if tuple(viewport_size) != self._viewport_key:
            self.layout(viewport_size)
        surface.blit(self._bg, self._rect.topleft)
        self._draw_tabs(surface)
        if self._side() is None:
            self._draw_empty(surface)
            return
        self._draw_dim_bar(surface)
        self._draw_header(surface)
        self._draw_list(surface, selected)
        self._draw_info(surface, selected)
        self._draw_context_menu(surface)

    def _draw_context_menu(self, surface):
        if self._context_menu is None:
            return
        rect, items = self._context_menu
        pygame.draw.rect(surface, _MENU_BG, rect)
        pygame.draw.rect(surface, config.PANEL_BORDER_COLOR, rect, 1)
        font = widgets.get_font(config.FONT_SIZE_PANEL_CELL)
        for i, (label, enabled, _cb) in enumerate(items):
            y = rect.top + _MENU_PAD_Y + i * _MENU_ITEM_H + _MENU_ITEM_H // 2
            color = widgets.TEXT_COLOR if enabled else _MENU_TEXT_DISABLED
            widgets.draw_text(surface, label, (rect.left + _MENU_PAD_X, y),
                              font, color, anchor="midleft", outline=False)

    def _draw_tabs(self, surface):
        font = widgets.get_font(config.FONT_SIZE_PANEL_TAB)
        for index, rect in enumerate(self._tab_rects):
            active = index == self.active_tab
            pygame.draw.rect(surface, (56, 64, 80) if active else (38, 44, 56), rect)
            if active:
                pygame.draw.line(surface, config.SELECT_HIGHLIGHT_COLOR,
                                 rect.bottomleft, rect.bottomright, 2)
            widgets.draw_text(surface, config.PANEL_TAB_TITLES[index], rect.center,
                              font,
                              widgets.TEXT_COLOR if active else widgets.TEXT_DIM,
                              anchor="center", outline=False)

    def _draw_empty(self, surface):
        font = widgets.get_font(config.FONT_SIZE_PANEL_CELL)
        widgets.draw_text(surface, "（本步未实现）", self._content.center, font,
                          widgets.TEXT_DIM, anchor="center", outline=False)

    def _draw_dim_bar(self, surface):
        mouse = pygame.mouse.get_pos()
        for key, btn in self._dim_btns:
            btn.bg_color = (config.PANEL_ROW_SELECTED_BG if key == self.group_dim
                            else widgets.BUTTON_BG)
            btn.draw(surface, mouse)
        font = widgets.get_font(config.FONT_SIZE_PANEL_CELL)
        title = dict(_GROUP_DIMS).get(self.group_dim)
        text = "平铺" if title is None else "分组：%s" % title
        widgets.draw_text(surface, text, (self._bar_rect.right - 4, self._bar_rect.centery),
                          font, widgets.TEXT_DIM, anchor="midright", outline=False)

    def _draw_header(self, surface):
        font = widgets.get_font(config.FONT_SIZE_PANEL_HEADER)
        for key, title, align, left, width in self._columns:
            if not title:
                continue
            if align == "left":
                widgets.draw_text(surface, title, (left + 4, self._header_rect.centery),
                                  font, _HEADER_FG, anchor="midleft", outline=False)
            elif align == "right":
                widgets.draw_text(surface, title, (left + width - 6, self._header_rect.centery),
                                  font, _HEADER_FG, anchor="midright", outline=False)
            else:
                widgets.draw_text(surface, title, (left + width // 2, self._header_rect.centery),
                                  font, _HEADER_FG, anchor="center", outline=False)
        pygame.draw.line(surface, config.PANEL_BORDER_COLOR,
                         self._header_rect.bottomleft, self._header_rect.bottomright, 1)

    def _cell_text(self, unit, key):
        if key == "name":
            return "%s %s" % (unit.name, unit.id)
        if key == "status":
            return _STATUS_TEXT
        if key == "troops":
            return unit_layer.format_troops(unit.troops)
        if key == "morale":
            return str(int(unit.morale))
        if key == "stamina":
            return str(int(unit.stamina))
        if key == "command":
            return ""
        return ""

    def _draw_list(self, surface, selected):
        entries, _ordered = self._entries()
        unit_font = widgets.get_font(config.FONT_SIZE_PANEL_CELL)
        mouse = pygame.mouse.get_pos()
        inner_hover = (self._list_rect.collidepoint(mouse)
                       and not self._is_over_ui(mouse))

        surface.set_clip(self._list_rect)
        for index, item in enumerate(entries):
            top = self._list_rect.top + index * self.row_h - self.scroll
            rect = pygame.Rect(self._list_rect.left, top, self._list_rect.width, self.row_h)
            if rect.bottom < self._list_rect.top:
                continue
            if rect.top > self._list_rect.bottom:
                break
            if item[0] == "group":
                self._draw_group_row(surface, rect, item, unit_font)
            else:
                self._draw_unit_row(surface, rect, item[1], unit_font,
                                    item[1].id in selected,
                                    inner_hover and rect.collidepoint(mouse))
        surface.set_clip(None)
        self._draw_scrollbar(surface, len(entries))

    def _is_over_ui(self, pos):
        """排除滚轮 / 点击落在滚动条上的情形。"""
        return pos[0] >= self._list_rect.right - _SCROLLBAR_W

    def _draw_group_row(self, surface, rect, item, font):
        pygame.draw.rect(surface, _GROUP_ROW_BG, rect)
        # 展开 / 折叠标记：系统 CJK 字体不含 ▾ / ▸（U+25BE / U+25B8），
        # 改用收录的大实心三角 ▼ / ▲（U+25BC / U+25B2）。
        arrow = "▼" if item[1] not in self.collapsed else "▲"
        widgets.draw_text(surface, "%s %s" % (arrow, item[2]), (rect.left + 4, rect.centery),
                          font, widgets.TEXT_COLOR, anchor="midleft", outline=False)

    def _draw_unit_row(self, surface, rect, unit, font, is_selected, hovered):
        if is_selected:
            pygame.draw.rect(surface, _ROW_SELECTED_BG, rect)
        elif hovered:
            pygame.draw.rect(surface, _ROW_HOVER_BG, rect)

        # 分组时只把最前面的「符号 + 部队」两列缩进一级（树形感），
        # 右侧数值列保持原 x / 宽度，避免被挤到截断。
        indent = _GROUP_INDENT if self.group_dim is not None else 0
        for index, (key, _title, align, left, width) in enumerate(self._columns):
            if index <= _NAME_INDEX:
                cell = pygame.Rect(left + indent, rect.top, width - indent, rect.height)
            else:
                cell = pygame.Rect(left, rect.top, width, rect.height)
            if key == "symbol":
                self._draw_symbol_cell(surface, cell, unit)
                continue
            text = self._cell_text(unit, key)
            if not text:
                continue
            text = self._fit_text(text, font, cell.width - 8)
            if align == "left":
                widgets.draw_text(surface, text, (cell.left + 4, cell.centery), font,
                                  widgets.TEXT_COLOR, anchor="midleft", outline=False)
            elif align == "right":
                widgets.draw_text(surface, text, (cell.right - 6, cell.centery), font,
                                  widgets.TEXT_COLOR, anchor="midright", outline=False)
            else:
                widgets.draw_text(surface, text, (cell.centerx, cell.centery), font,
                                  widgets.TEXT_COLOR, anchor="center", outline=False)

    def _draw_symbol_cell(self, surface, cell, unit):
        type_def = unit.type_def
        if not type_def:
            return
        thumb = sym.render_thumbnail(type_def, unit.side,
                                     self.row_h * _SYMBOL_CELL_SCALE)
        surface.blit(thumb, thumb.get_rect(center=cell.center))

    def _fit_text(self, text, font, max_w):
        if max_w <= 0:
            return ""
        if font.size(text)[0] <= max_w:
            return text
        ellipsis = "…"
        limit = max_w - font.size(ellipsis)[0]
        out = ""
        for ch in text:
            if font.size(out + ch)[0] > limit:
                break
            out += ch
        return out + ellipsis

    def _draw_scrollbar(self, surface, entry_count):
        total = entry_count * self.row_h
        view = self._list_rect.height
        if total <= view or view <= 0:
            return
        track = pygame.Rect(self._list_rect.right - _SCROLLBAR_W,
                            self._list_rect.top, _SCROLLBAR_W, view)
        pygame.draw.rect(surface, _SCROLLBAR_BG, track)
        thumb_h = max(24, int(view * view / total))
        max_scroll = total - view
        offset = 0 if max_scroll <= 0 else int((view - thumb_h) * (self.scroll / max_scroll))
        pygame.draw.rect(surface, _SCROLLBAR_FG,
                         pygame.Rect(track.x, track.y + offset, track.width, thumb_h))

    # ============================================================
    # 部队情报组
    # ============================================================
    def _info_unit(self, selected):
        """选中集与当前 Tab 的可见行求交，取展示顺序最靠前的一支。"""
        if not selected:
            return None
        for unit in self._row_units_in_order(self._entries()[0]):
            if unit.id in selected:
                return unit
        return None

    def _draw_info(self, surface, selected):
        pygame.draw.line(surface, config.PANEL_BORDER_COLOR,
                         self._info_rect.topleft,
                         (self._info_rect.right, self._info_rect.top), 1)
        font = widgets.get_font(config.FONT_SIZE_UNIT_INFO)
        unit = self._info_unit(selected)

        if self._info_rect.height <= self.row_h + 12:
            # 折叠形态：只显示一行标题（部队名）
            text = unit.name + " " + unit.id if unit else "（未选中部队）"
            widgets.draw_text(surface, text, self._info_rect.center, font,
                              widgets.TEXT_COLOR if unit else widgets.TEXT_DIM,
                              anchor="center", outline=False)
            return

        if unit is None:
            widgets.draw_text(surface, "（未选中部队）", self._info_rect.center, font,
                              widgets.TEXT_DIM, anchor="center", outline=False)
            return

        line_h = config.FONT_SIZE_UNIT_INFO + 10
        y = self._info_rect.top + 6
        for label, key in config.UNIT_INFO_FIELDS:
            if y + line_h > self._info_rect.bottom:
                break   # 超出高度不滚动，超出部分不画
            widgets.draw_text(surface, label,
                              (self._info_rect.left + _VALUE_LABEL_W - 8, y + line_h // 2),
                              font, widgets.TEXT_DIM, anchor="midright", outline=False)
            value = self._fit_text(self._info_value(unit, key), font,
                                   self._info_rect.width - _VALUE_LABEL_W - 8)
            widgets.draw_text(surface, value,
                              (self._info_rect.left + _VALUE_LABEL_W, y + line_h // 2),
                              font, widgets.TEXT_COLOR, anchor="midleft", outline=False)
            y += line_h

    def _info_value(self, unit, key):
        if key == "id":
            return unit.id
        if key == "side":
            return "红方" if unit.side == "red" else "蓝方"
        if key == "name":
            return unit.name
        if key == "offset":
            col, row = unit.offset()
            return "(%s, %s)" % (col, row)
        if key == "troops":
            return "%s / %s" % (unit_layer.format_troops(unit.troops),
                                unit_layer.format_troops(unit.troops_max))
        if key == "morale":
            return str(int(unit.morale))
        if key == "stamina":
            return str(int(unit.stamina))
        if key == "status":
            return _STATUS_TEXT
        if key == "command":
            return "（无）" if unit.command is None else str(unit.command)
        return ""
