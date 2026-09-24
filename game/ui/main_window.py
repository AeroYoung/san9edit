# -*- coding: utf-8 -*-
"""主窗口。组装所有 UI 部件，处理跨模块的事件和业务。

布局（从上到下）：
    [TopBar     顶部栏：左侧信息 + 右侧菜单]
    [PanedWindow
        ├── MapCanvas    地图
        └── SidePanel    右侧 Tab]
    [StatusBar  状态栏]
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

from game.config import constants as C
from game.config.style import THEME, FONT_CANDIDATES
from game.core.game_state import GameState
from game.ui.top_bar import TopBar
from game.ui.status_bar import StatusBar
from game.ui.map_canvas import MapCanvas
from game.ui.side_panel import SidePanel
from game.ui.window_utils import maximize, center_on_parent
from game.config.settings_manager import SettingsManager
from game.ui.settings_window import SettingsWindow
from game.core.scenario import ScenarioLoader
from game.ui.map_controller import MapController

class MainWindow:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(C.APP_TITLE)
        self.root.minsize(*C.MIN_WINDOW_SIZE)

        # 先最大化，再进入后续构建
        maximize(self.root)

        self.font_family = self._pick_font_family()
        # 设置管理器必须先于任何读取 style 的部件创建，
        # 保证 apply() 已经把本地覆盖写回 style 字典。
        self.settings = SettingsManager()
        self.settings.apply()
        self.game_state = GameState()

        self._setup_theme()
        self._build_layout()
        self._bind_shortcuts()

        # 启动后加载默认地图。
        # 用 after 让窗口先完成一次布局，canvas 才有真实尺寸。
        self.root.after(120, self._auto_load_default)

    # ==========================================================
    # 初始化
    # ==========================================================
    def _pick_font_family(self):
        try:
            available = set(tkfont.families())
        except Exception:
            available = set()
        for name in FONT_CANDIDATES:
            if name in available:
                return name
        return "TkDefaultFont"

    def _setup_theme(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background=THEME["panel_bg"])
        style.configure("TPanedwindow", background=THEME["panel_bg"])
        style.configure("TNotebook", background=THEME["panel_bg"], borderwidth=0)
        style.configure("TNotebook.Tab",
                        padding=(14, 6), font=(self.font_family, 10))

    def _build_layout(self):
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        # ---------- 顶部栏（信息 + 菜单） ----------
        self.top_bar = TopBar(
            root, self.game_state, self.font_family,
            on_action=self._on_menu_action,
        )
        self.top_bar.grid(row=0, column=0, sticky="ew")

        # ---------- 中部：地图 + 侧面板 ----------
        pane = ttk.PanedWindow(root, orient="horizontal")
        pane.grid(row=1, column=0, sticky="nsew")

        self.map_canvas = MapCanvas(pane, self.font_family)
        self.map_controller = MapController(self.map_canvas)                  # ★
        self.side_panel = SidePanel(pane, self.game_state, self.map_controller)  # ★
        
        pane.add(self.map_canvas, weight=4)
        pane.add(self.side_panel, weight=1)

        self.map_canvas.set_location_callback(self._on_location_change)

        # ---------- 底部状态栏 ----------
        self.status_bar = StatusBar(root, self.font_family)
        self.status_bar.grid(row=2, column=0, sticky="ew")
        self.status_bar.set_message("就绪")

        # 缩放变化回调：地图缩放时更新状态栏
        self.map_canvas.set_zoom_callback(self._on_zoom_change)

    def _bind_shortcuts(self):
        r = self.root
        r.bind("<plus>",  lambda e: self.map_canvas.zoom(1.25))
        r.bind("<equal>", lambda e: self.map_canvas.zoom(1.25))
        r.bind("<minus>", lambda e: self.map_canvas.zoom(1 / 1.25))
        r.bind("<0>",     lambda e: self.map_canvas.reset_view())
        r.bind("<Control-o>", lambda e: self.open_geojson())

    # ==========================================================
    # 地图加载
    # ==========================================================
    def _auto_load_default(self):
        path = C.DEFAULT_MAP_PATH
        if not path.is_file():
            self.status_bar.set_message(
                f"未找到 {path.name}，请按 Ctrl+O 打开文件"
            )
            return
        ok = self.load_geojson(str(path), silent=True)
        if ok:
            self._load_default_scenario()

    def _load_default_scenario(self):
        """地图加载成功后，紧接着加载默认剧本，构造 World。"""
        path = C.DEFAULT_SCENARIO_PATH
        if not path.is_file():
            self.status_bar.set_message(f"未找到剧本 {path.name}")
            return

        geo = getattr(self, "_geo_data", None)
        if geo is None:
            # 兜底：从渲染器里拿
            geo = getattr(getattr(self.map_canvas, "renderer", None),
                          "data", None)
        if geo is None:
            self.status_bar.set_message("剧本加载失败：GeoData 尚未就绪")
            return

        try:
            world = ScenarioLoader.load(str(path), geo)
        except Exception as e:
            self.status_bar.set_message(f"剧本加载失败：{e}")
            return

        self._world = world
        self.game_state.sync_from_world(world)
        self.map_canvas.renderer.set_world(world)   # ★ 新
        self.status_bar.set_message(world.summary() + " | 玩家势力：曹操")
        self.side_panel.refresh_all()
        self.map_canvas.redraw()                    # ★ 新：触发一次全量重绘

        pf = world.player_faction()
        pf_name = pf.name if pf else "—"
        self.status_bar.set_message(
            f"{world.summary()}  |  玩家势力：{pf_name}"
        )
        # ★ 新增：刷新右侧面板（势力 / 据点 / 人物 / 部队）
        self.side_panel.refresh_all()

    def open_geojson(self):
        path = filedialog.askopenfilename(
            title="选择 GeoJSON 文件",
            filetypes=[("GeoJSON", "*.json *.geojson"), ("所有文件", "*.*")],
        )
        if path:
            self.load_geojson(path)

    def load_geojson(self, path, silent=False):
        try:
            data = self.map_canvas.load_geojson(path)
        except Exception as e:
            if silent:
                self.status_bar.set_message(f"自动加载失败：{e}")
            else:
                messagebox.showerror("加载失败", str(e))
            return False

        self._geo_data = data
        self.map_canvas.reset_view()
        self.status_bar.set_message(
            f"已加载 {os.path.basename(path)}  |  "
            f"{data.feature_count} 个要素  |  "
            f"州 {len(data.labels_state)} / "
            f"郡 {len(data.labels_county)} / "
            f"县 {len(data.labels_city)}"
        )
        return True

    # ==========================================================
    # 事件
    # ==========================================================
    def _on_location_change(self, info):
        """info 为 None 或 dict。"""
        if not info:
            self.status_bar.set_location("")
            return

        parts = [p for p in (info.get("state"),
                            info.get("county"),
                            info.get("city")) if p]
        faction = self._faction_at(info.get("node_id"))
        if faction:
            parts.append(faction)

        lon = info.get("lon", 0.0)
        lat = info.get("lat", 0.0)
        text = " · ".join(parts) + f"   （{lon:.2f}°E, {lat:.2f}°N）"
        self.status_bar.set_location(text)

    def _faction_at(self, node_id):
        """按据点 id 查势力名；无主 → None。"""
        if not node_id:
            return None
        world = getattr(self.game_state, "world", None)
        if world is None:
            return None
        node = world.node(node_id)
        if node is None or node.owner is None:
            return None
        f = world.faction(node.owner)
        return f.name if f else None

    def _on_zoom_change(self, scale):
        self.status_bar.set_zoom(f"缩放 {scale:.1f}")

    def _on_menu_action(self, action, **kw):
        if action == "quit":
            self.root.quit()
        elif action == "new_game":
            self._confirm_and_new_game()
        elif action == "load_game":
            self.open_geojson()
        elif action == "settings":
            self._open_settings()
        elif action == "save_game":
            self.status_bar.set_message("保存功能尚未实现")
        elif action == "view_zoom_in":
            self.map_canvas.zoom(1.25)
        elif action == "view_zoom_out":
            self.map_canvas.zoom(1 / 1.25)
        elif action == "view_reset":
            self.map_canvas.reset_view()
        elif action == "view_cities":
            self.side_panel.notebook.select(1)
        elif action == "view_characters":
            self.side_panel.notebook.select(2)
        elif action == "view_troops":
            self.side_panel.notebook.select(3)
        elif action == "end_turn":
            self._end_turn()
        elif action == "help_about":
            messagebox.showinfo(
                "关于", f"{C.APP_TITLE}\n\n回合制策略游戏原型\n版本 0.1"
            )
        else:
            self.status_bar.set_message(f"[菜单] {action}")

    # ==========================================================
    # 游戏流程
    # ==========================================================
    def _end_turn(self):
        self.game_state.advance_turn()
        self.side_panel.refresh_all()
        self.status_bar.set_message(
            f"回合推进 → {self.game_state.date_text()}"
        )

    def _open_settings(self):
        win = getattr(self, "_settings_win", None)
        if win is not None and win.winfo_exists():
            win.lift()
            win.focus_set()
            return
        self._settings_win = SettingsWindow(
            self.root, self.settings, self.font_family,
            on_applied=self._on_settings_applied,
        )

    def _on_settings_applied(self, changed_paths):
        """设置窗口保存后调用。

        - MAP_STYLE / CITY_LEVEL_MIN_SCALE / LAYER_VISIBILITY：立即重绘地图；
        - THEME / FONT_SIZES / FONT_CANDIDATES：需重启，窗口自己已提示。
        """
        map_dirty = False
        for p in changed_paths:
            if p.startswith("MAP_STYLE.") \
            or p.startswith("CITY_LEVEL_MIN_SCALE") \
            or p.startswith("LAYER_VISIBILITY."):
                map_dirty = True
                break
        if map_dirty and getattr(self, "map_canvas", None) is not None:
            try:
                self.map_canvas.redraw()
            except Exception:
                pass
        self.status_bar.set_message("设置已保存")

    def _confirm_and_new_game(self):
        if messagebox.askyesno("新游戏",
                               "确定要开始新游戏吗？当前进度不会保存。"):
            self.status_bar.set_message("新游戏（尚未实现）")

    # ==========================================================
    def run(self):
        self.root.mainloop()