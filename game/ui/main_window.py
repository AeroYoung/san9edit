# -*- coding: utf-8 -*-
"""主窗口。组装所有 UI 部件，处理跨模块的事件和业务。

布局（从上到下）：
    [TopBar     顶部栏：左侧信息 + 右侧菜单]
    [PanedWindow
        ├── MapCanvas    地图
        └── SidePanel    右侧 Tab]
    [StatusBar  状态栏]
"""

import logging
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter import font as tkfont

from game.config import constants as C
from game.config.style import THEME, FONT_CANDIDATES, MAP_INTERACTION
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

logger = logging.getLogger(__name__)


class MainWindow:
    def __init__(self):
        logger.info("初始化 MainWindow，APP_MODE=%s", C.APP_MODE)
        self.root = tk.Tk()
        # ★ 紧跟 Tk() 之后，越早越好，避免构造期间的 tk 回调异常丢失
        from game.config.logging_setup import install_tk_excepthook
        install_tk_excepthook(self.root)

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
        self._tooltip = None       # hover 浮窗
        self._map_menus = []       # 地图右键菜单引用（防 GC）

        # 剧本编辑模式（D9：模式判断只在这里）
        self.editable = (C.APP_MODE == C.MODE_EDIT)
        self.edit_session = None
        self._modal_open = False
        self._scenario_path = str(C.DEFAULT_SCENARIO_PATH)
        self._baseline_raw = None

        self._setup_theme()
        self._build_layout()
        self._bind_shortcuts()

        # 关闭窗口拦截（编辑模式下有未保存改动时弹确认）
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

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
        self.map_canvas.set_right_click_callback(self._on_map_right_click)

        # ---------- 底部状态栏 ----------
        self.status_bar = StatusBar(root, self.font_family)
        self.status_bar.grid(row=2, column=0, sticky="ew")
        self.status_bar.set_message("就绪")

        # 缩放变化回调：地图缩放时更新状态栏
        self.map_canvas.set_zoom_callback(self._on_zoom_change)

        # 按 APP_MODE 统一切换编辑入口 / 回合按钮
        self.top_bar.set_game_mode(not self.editable)
        self.top_bar.set_edit_enabled(self.editable)
        logger.debug("布局构建完成")

    def _bind_shortcuts(self):
        r = self.root
        r.bind_all("<plus>",  lambda e: self.map_canvas.zoom(1.25))
        r.bind_all("<equal>", lambda e: self.map_canvas.zoom(1.25))
        r.bind_all("<minus>", lambda e: self.map_canvas.zoom(1 / 1.25))
        r.bind_all("<0>",     lambda e: self.map_canvas.reset_view())
        r.bind_all("<Control-o>", lambda e: self.open_geojson())
        # 剧本编辑快捷键（弹窗打开时由 _modal_open 屏蔽）
        # ★ 用 bind_all 而不是 bind：只绑在 root 上时，一旦键盘焦点落在别的 Toplevel
        #   （或菜单关闭后焦点被清空），按键就不会派发到 root，快捷键表现为「没反应」。
        r.bind_all("<Control-s>", lambda e: self._on_save_scenario())
        r.bind_all("<Control-Shift-S>", lambda e: self._on_save_as())
        r.bind_all("<Control-z>", lambda e: self._on_undo())
        r.bind_all("<Control-Shift-Z>", lambda e: self._on_redo())
        logger.debug("快捷键绑定完成")

    # ==========================================================
    # 地图加载
    # ==========================================================
    def _auto_load_default(self):
        path = C.DEFAULT_MAP_PATH
        logger.info("自动加载默认地图：%s", path)
        if not path.is_file():
            logger.warning("默认地图不存在：%s", path)
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
        self._load_scenario(path)

    def _load_scenario(self, path):
        """加载指定剧本文件，构造 World，并（编辑模式）重建编辑会话。"""
        logger.info("加载剧本：%s", path)
        geo = getattr(self, "_geo_data", None)
        if geo is None:
            # 兜底：从渲染器里拿
            geo = getattr(getattr(self.map_canvas, "renderer", None),
                          "data", None)
        if geo is None:
            logger.warning("剧本加载失败：GeoData 尚未就绪")
            self.status_bar.set_message("剧本加载失败：GeoData 尚未就绪")
            return

        try:
            world = ScenarioLoader.load(str(path), geo)
        except Exception as e:
            logger.error("剧本加载失败：%s", path, exc_info=True)
            self.status_bar.set_message(f"剧本加载失败：{e}")
            return

        self._world = world
        self.game_state.sync_from_world(world)
        self.map_canvas.renderer.set_world(world)
        self.side_panel.refresh_all()
        self.map_canvas.redraw()

        pf = world.player_faction()
        pf_name = pf.name if pf else "—"
        self.status_bar.set_message(
            f"{world.summary()}  |  玩家势力：{pf_name}"
        )

        logger.info("剧本加载完成：%s", world.summary())

        # 编辑模式：建立编辑会话 + baseline 快照（§10.7）
        if self.editable:
            logger.debug("建立 EditSession，生成 baseline 快照")
            from game.core.scenario_writer import ScenarioWriter
            from game.core.edit_session import EditSession
            baseline_snap = ScenarioWriter.serialize(world)
            self.edit_session = EditSession(world, baseline_snap)
            self._baseline_raw = self._load_raw_scenario(path)
            self._scenario_path = str(path)
            self.side_panel.set_edit_session(
                self.edit_session,
                on_edit=self.on_edit_executed,
                open_dialog=self.open_edit_dialog,
            )
            self._sync_undo_redo_state()

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
            logger.error("地图加载失败：%s", path, exc_info=True)
            if silent:
                self.status_bar.set_message(f"自动加载失败：{e}")
            else:
                messagebox.showerror("加载失败", str(e))
            return False

        logger.info("加载地图：%s  要素=%d",
                    os.path.basename(path), data.feature_count)
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
            self._hide_tooltip()
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
        self._update_tooltip(info)

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

    # ==========================================================
    # hover tooltip
    # ==========================================================
    def _update_tooltip(self, info):
        if not MAP_INTERACTION.get("highlight_hover_tooltip", True):
            self._hide_tooltip()
            return
        node_id = info.get("node_id")
        if not node_id:
            self._hide_tooltip()
            return
        world = getattr(self.game_state, "world", None)
        if world is None:
            self._hide_tooltip()
            return
        node = world.node(node_id)
        if node is None:
            self._hide_tooltip()
            return

        faction_name = "无主"
        if node.owner:
            f = world.faction(node.owner)
            faction_name = f.name if f else "无主"
        text = f"{node.name}\n势力：{faction_name}\n驻军：{node.troops:,}"

        px = info.get("px", 0)
        py = info.get("py", 0)
        rootx = self.map_canvas.canvas.winfo_rootx()
        rooty = self.map_canvas.canvas.winfo_rooty()
        self._show_tooltip(text, rootx + px + 14, rooty + py + 14)

    def _show_tooltip(self, text, x, y):
        if self._tooltip is None:
            self._tooltip = tk.Toplevel(self.root)
            self._tooltip.overrideredirect(True)
            try:
                self._tooltip.attributes("-topmost", True)
            except Exception:
                pass
            self._tooltip_lbl = tk.Label(
                self._tooltip, text=text, bg="#FFFFE0", fg="#333333",
                relief="solid", bd=1, padx=8, pady=4, justify="left",
                font=(self.font_family, 10),
            )
            self._tooltip_lbl.pack()
        else:
            self._tooltip_lbl.config(text=text)
        self._tooltip.geometry(f"+{x}+{y}")

    def _hide_tooltip(self):
        if self._tooltip is not None:
            try:
                self._tooltip.destroy()
            except Exception:
                pass
            self._tooltip = None

    # ==========================================================
    # 地图右键菜单
    # ==========================================================
    def _on_map_right_click(self, node_id, event):
        logger.debug("地图右键：node_id=%s", node_id)
        menu = tk.Menu(self.root, tearoff=0)
        self._map_menus.append(menu)
        if node_id:
            self._build_node_context_menu(menu, node_id)
        else:
            self._build_empty_context_menu(menu)
        focus = self.root.focus_get()
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()
            # ★ 同列表右键：菜单关闭后焦点会丢，快捷键随之失效 —— 收回来
            if focus is not None and focus.winfo_exists():
                focus.focus_set()
            else:
                self.map_canvas.canvas.focus_set()

    def _build_node_context_menu(self, menu, node_id):
        world = getattr(self, "_world", None)
        node = world.nodes.get(node_id) if world is not None else None

        faction = None
        if node is not None and node.owner and world is not None:
            faction = world.factions.get(node.owner)
            if faction is None:
                logger.warning("据点 %s 的 owner=%s 无对应势力",
                               node_id, node.owner)

        # ★ 编辑类入口：状态由 APP_MODE 单点决定（D9）
        edit_state = "normal" if self.editable else "disabled"

        menu.add_command(label="编辑据点",
                         command=lambda: self._edit_node_from_map(node_id),
                         state=edit_state)

        # 有势力 → 显示「编辑势力：XXX」；无势力 / 脏 owner → 不显示
        if faction is not None:
            menu.add_command(
                label=f"编辑势力：{faction.name}",
                command=lambda fid=faction.id: self._edit_faction_from_map(fid),
                state=edit_state,
            )

        menu.add_separator()
        menu.add_command(label="据点情报",
                         command=lambda: self._map_intel("node", node_id))
        menu.add_command(label="人物情报",
                         command=lambda: self._map_intel("character", node_id))
        menu.add_command(label="势力情报",
                         command=lambda: self._map_intel("faction", node_id))
        menu.add_separator()
        locate = tk.Menu(menu, tearoff=0)
        locate.add_command(label="据点",
                           command=lambda: self._locate_to_list("node", node_id))
        locate.add_command(label="人物", state="disabled")
        locate.add_command(label="势力", state="disabled")
        locate.add_command(label="部队", state="disabled")
        menu.add_cascade(label="定位到列表", menu=locate)


    def _build_empty_context_menu(self, menu):
        menu.add_command(label="复位视图", command=self.map_canvas.reset_view)
        menu.add_command(label="放大", command=lambda: self.map_canvas.zoom(1.25))
        menu.add_command(label="缩小",
                         command=lambda: self.map_canvas.zoom(1 / 1.25))

    def _edit_node_from_map(self, node_id):
        """★ 地图右键 →「编辑据点」：与面板右键共用同一套编辑流程。"""
        logger.info("地图右键编辑据点：%s", node_id)
        world = getattr(self, "_world", None)
        if world is None or self.edit_session is None:
            return
        node = world.nodes.get(node_id)
        if node is None:
            logger.warning("据点不存在：%s", node_id)
            return
        from game.ui.dialogs.node_edit import edit_node
        if edit_node(self.root, world, node,
                     self.edit_session, self.open_edit_dialog):
            self.side_panel.refresh_all()
            self.on_edit_executed()

    def _edit_faction_from_map(self, faction_id):
        """★ 地图右键 →「编辑势力」：与面板右键共用 edit_faction。"""
        logger.info("地图右键编辑势力：%s", faction_id)
        world = getattr(self, "_world", None)
        if world is None or self.edit_session is None:
            return
        f = world.factions.get(faction_id)
        if f is None:
            logger.warning("势力不存在：%s", faction_id)
            return
        from game.ui.dialogs.faction_edit import edit_faction
        if edit_faction(self.root, world, f,
                        self.edit_session, self.open_edit_dialog):
            self.side_panel.refresh_all()
            self.on_edit_executed()

    def _map_intel(self, kind, node_id):
        logger.debug("地图情报：kind=%s node=%s", kind, node_id)

    # ==========================================================
    # 双向定位（地图 → 列表）
    # ==========================================================
    def _locate_to_list(self, tab_key, node_id):
        panel = self.side_panel.select_panel(tab_key)
        if panel is not None and hasattr(panel, "scroll_to_row"):
            panel.scroll_to_row(node_id)

    def _on_zoom_change(self, scale):
        self.status_bar.set_zoom(f"缩放 {scale:.1f}")

    def _on_menu_action(self, action, **kw):
        logger.debug("菜单动作：%s", action)
        if action == "quit":
            self._on_close()
        elif action == "select_scenario":
            self._on_select_scenario()
        elif action == "save_scenario":
            self._on_save_scenario()
        elif action == "save_scenario_as":
            self._on_save_as()
        elif action == "undo":
            self._on_undo()
        elif action == "redo":
            self._on_redo()
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
        if self.editable:
            return   # 编辑模式禁用回合推进
        self.game_state.advance_turn()
        self.side_panel.refresh_all()
        self.status_bar.set_message(
            f"回合推进 → {self.game_state.date_text()}"
        )

    def _open_settings(self):
        logger.info("打开设置窗口")
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
        logger.info("设置已应用：%s", changed_paths)
        map_dirty = False
        panel_dirty = False
        for p in changed_paths:
            if p.startswith("MAP_STYLE.") \
            or p.startswith("CITY_LEVEL_MIN_SCALE") \
            or p.startswith("LAYER_VISIBILITY."):
                map_dirty = True
            elif p.startswith("PANEL_COLUMNS"):      # ★
                panel_dirty = True
                
        if map_dirty and getattr(self, "map_canvas", None) is not None:
            logger.debug("地图重绘（设置变更）")
            try:
                self.map_canvas.redraw()
            except Exception:
                logger.warning("地图重绘失败", exc_info=True)

        if panel_dirty:                              # ★
            side = getattr(self, "side_panel", None)
            if side is not None and hasattr(side, "reload_panel_columns"):
                logger.debug("重载面板列（设置变更）")
                try:
                    side.reload_panel_columns()
                except Exception:
                    logger.warning("面板列重载失败", exc_info=True)

        self.status_bar.set_message("设置已保存")

    def _confirm_and_new_game(self):
        if messagebox.askyesno("新游戏",
                               "确定要开始新游戏吗？当前进度不会保存。"):
            self.status_bar.set_message("新游戏（尚未实现）")

    # ==========================================================
    # 剧本编辑：会话 / 弹窗 / 保存
    # ==========================================================
    def open_edit_dialog(self, dlg_factory):
        """打开模态弹窗，屏蔽全局快捷键。供面板调用。"""
        logger.debug("打开编辑弹窗（模态）")
        self._modal_open = True
        try:
            dlg = dlg_factory()
            self.root.wait_window(dlg)
            return dlg
        finally:
            self._modal_open = False

    def on_edit_executed(self):
        """面板编辑执行后由 SidePanel 转发。"""
        logger.debug("编辑已执行：刷新面板 + 重绘地图")
        self._sync_undo_redo_state()
        self._redraw_map()

    def _redraw_map(self):
        """编辑后重绘地图（据点 level / 势力颜色等可能已变）。"""
        canvas = getattr(self, "map_canvas", None)
        if canvas is None:
            return
        try:
            canvas.redraw()
        except Exception:
            logger.warning("地图重绘失败", exc_info=True)

    def _refresh_title(self):
        """窗口标题：APP_TITLE [- 剧本文件名] [*]。

        未加载剧本 → 只显示 APP_TITLE；
        已加载 → 追加剧本文件名；
        有未保存改动 → 追加 " *"。
        """
        title = C.APP_TITLE
        world = getattr(self, "_world", None)
        if world is not None and self._scenario_path:
            title = f"{title} - {os.path.basename(self._scenario_path)}"
        if self.edit_session is not None and self.edit_session.is_dirty():
            title += " *"
        self.root.title(title)

    def _sync_undo_redo_state(self):
        if self.edit_session is None:
            self.top_bar.set_edit_state(False, False)
        else:
            self.top_bar.set_edit_state(
                self.edit_session.can_undo(),
                self.edit_session.can_redo(),
            )
        self._refresh_title()


    def _load_raw_scenario(self, path):
        import json
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _on_close(self):
        """关闭窗口 / 退出菜单：有未保存改动时拦截。"""
        logger.info("请求关闭窗口")
        if self._confirm_discard():
            self.root.destroy()

    def _confirm_discard(self):
        """有未保存改动时弹「放弃 / 取消」。True = 可继续（丢弃）。"""
        if self.edit_session is not None and self.edit_session.is_dirty():
            logger.info("存在未保存改动，询问用户")
            ans = messagebox.askyesnocancel(
                "未保存的改动", "有未保存的改动，是否放弃？")
            return ans is True
        return True

    def _on_save_scenario(self):
        if self._modal_open:
            # 弹窗持着键盘，快捷键会被吞 —— 明确反馈，不要静默返回
            logger.info("保存被跳过：弹窗打开中")
            self.status_bar.set_message("弹窗打开中，先关闭弹窗再保存")
            return
        if self.edit_session is None:
            logger.warning("保存失败：未加载剧本")
            self.status_bar.set_message("未加载剧本")
            return
        if not self.edit_session.is_dirty():
            logger.info("无改动，跳过保存")
            self.status_bar.set_message("无改动，未保存")
            return
        self._save_to_path(self._scenario_path)

    def _on_save_as(self):
        if self._modal_open:
            return
        if self.edit_session is None:
            self.status_bar.set_message("未加载剧本")
            return
        path = filedialog.asksaveasfilename(
            title="另存为",
            initialdir=str(C.SCENARIOS_DIR),
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("所有文件", "*.*")],
        )
        if not path:
            logger.debug("另存为取消")
            return
        self._save_to_path(path)
        self._scenario_path = path   # 上下文切换到新文件

    def _save_to_path(self, path):
        from game.core.scenario_writer import ScenarioWriter
        world = getattr(self, "_world", None)
        if world is None or self.edit_session is None:
            return
        logger.info("保存剧本 → %s", path)
        try:
            ScenarioWriter.save(world, path, self._baseline_raw,
                                self.edit_session.baseline)
        except Exception as e:
            logger.error("保存失败：%s", path, exc_info=True)
            messagebox.showerror("保存失败", str(e))
            return
        self.edit_session.rebase()
        self.edit_session.clear()
        self._baseline_raw = self._load_raw_scenario(path)
        self._sync_undo_redo_state()
        logger.info("保存成功：%s", path)
        self.status_bar.set_message(f"已保存 → {path}")

    def _on_undo(self):
        if self._modal_open or self.edit_session is None:
            logger.debug("undo 被跳过：modal_open=%s 有会话=%s",
                         self._modal_open, self.edit_session is not None)
            return
        logger.debug("触发 undo")
        self.edit_session.undo()
        # keep_view：就地刷新，撤销后保住滚动位置 / 选中项 / 展开状态
        self.side_panel.refresh_all(keep_view=True)
        self._sync_undo_redo_state()
        self._redraw_map()

    def _on_redo(self):
        if self._modal_open or self.edit_session is None:
            return
        logger.debug("触发 redo")
        self.edit_session.redo()
        self.side_panel.refresh_all(keep_view=True)
        self._sync_undo_redo_state()
        self._redraw_map()

    def _on_select_scenario(self):
        if self._modal_open:
            return
        if not self._confirm_discard():
            return
        path = filedialog.askopenfilename(
            title="选择剧本",
            initialdir=str(C.SCENARIOS_DIR),
            filetypes=[("JSON", "*.json"), ("所有文件", "*.*")],
        )
        if not path:
            return
        logger.info("选择剧本：%s", path)
        from pathlib import Path
        self._load_scenario(Path(path))

    # ==========================================================
    def run(self):
        logger.info("进入 mainloop")
        self.root.mainloop()