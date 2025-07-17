import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import numpy as np
import json


class PWLTool:
    def __init__(self, root):
        self.root = root
        self.root.title("SPICE PWL Generator")
        self.root.geometry("1200x800")

        # PWL点のリスト [(時間, 値)]
        self.pwl_points = [(0, 0), (1e-6, 0)]  # 初期値: (0s, 0V), (1μs, 0V)

        # SI接頭語の定義
        self.time_prefixes = {
            "fs": 1e-15,
            "ps": 1e-12,
            "ns": 1e-9,
            "μs": 1e-6,
            "ms": 1e-3,
            "s": 1,
        }
        self.voltage_prefixes = {"μV": 1e-6, "mV": 1e-3, "V": 1, "kV": 1e3}
        self.current_prefixes = {
            "pA": 1e-12,
            "nA": 1e-9,
            "μA": 1e-6,
            "mA": 1e-3,
            "A": 1,
        }

        # デフォルト単位
        self.time_unit = "μs"
        self.value_unit = "mV"
        self.source_type = "Voltage"  # 'Voltage' or 'Current'

        # 表示範囲
        self.x_min, self.x_max = 0, 10
        self.y_min, self.y_max = -5, 5

        # 選択された点のインデックス
        self.selected_point = None

        # パン操作用の変数
        self.pan_start = None
        self.panning = False

        # グリッド拘束設定
        self.grid_snap_enabled = False
        self.time_grid_size = 1.0  # 現在の時間単位での値
        self.value_grid_size = 1.0  # 現在の値単位での値

        self.setup_ui()
        self.update_plot()

    def setup_ui(self):
        # メインフレーム
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 上部コントロールパネル
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 5))

        # ソースタイプ選択
        ttk.Label(control_frame, text="Source Type:").grid(
            row=0, column=0, padx=5, sticky="w"
        )
        self.source_var = tk.StringVar(value=self.source_type)
        source_combo = ttk.Combobox(
            control_frame,
            textvariable=self.source_var,
            values=["Voltage", "Current"],
            state="readonly",
            width=10,
        )
        source_combo.grid(row=0, column=1, padx=5)
        source_combo.bind("<<ComboboxSelected>>", self.on_source_type_change)

        # 時間単位選択
        ttk.Label(control_frame, text="Time Unit:").grid(
            row=0, column=2, padx=5, sticky="w"
        )
        self.time_unit_var = tk.StringVar(value=self.time_unit)
        time_combo = ttk.Combobox(
            control_frame,
            textvariable=self.time_unit_var,
            values=list(self.time_prefixes.keys()),
            state="readonly",
            width=8,
        )
        time_combo.grid(row=0, column=3, padx=5)
        time_combo.bind("<<ComboboxSelected>>", self.on_unit_change)

        # 値単位選択
        ttk.Label(control_frame, text="Value Unit:").grid(
            row=0, column=4, padx=5, sticky="w"
        )
        self.value_unit_var = tk.StringVar(value=self.value_unit)
        value_combo = ttk.Combobox(
            control_frame,
            textvariable=self.value_unit_var,
            values=list(self.voltage_prefixes.keys()),
            state="readonly",
            width=8,
        )
        value_combo.grid(row=0, column=5, padx=5)
        value_combo.bind("<<ComboboxSelected>>", self.on_unit_change)
        self.value_combo = value_combo

        # ボタン
        ttk.Button(control_frame, text="Add Point", command=self.add_point).grid(
            row=0, column=6, padx=5
        )
        ttk.Button(control_frame, text="Delete Point", command=self.delete_point).grid(
            row=0, column=7, padx=5
        )
        ttk.Button(control_frame, text="Generate PWL", command=self.generate_pwl).grid(
            row=0, column=8, padx=5
        )
        ttk.Button(control_frame, text="Save", command=self.save_file).grid(
            row=0, column=9, padx=5
        )
        ttk.Button(control_frame, text="Load", command=self.load_file).grid(
            row=0, column=10, padx=5
        )

        # 第2行: グリッド拘束設定
        # グリッド拘束チェックボックス
        self.grid_snap_var = tk.BooleanVar(value=self.grid_snap_enabled)
        grid_check = ttk.Checkbutton(
            control_frame,
            text="Grid Snap",
            variable=self.grid_snap_var,
            command=self.on_grid_snap_change,
        )
        grid_check.grid(row=1, column=0, columnspan=2, padx=5, sticky="w")

        # 時間グリッドサイズ
        ttk.Label(control_frame, text="Time Grid:").grid(
            row=1, column=2, padx=5, sticky="w"
        )
        self.time_grid_var = tk.DoubleVar(value=self.time_grid_size)
        time_grid_spin = ttk.Spinbox(
            control_frame,
            from_=0.001,
            to=1000,
            increment=0.1,
            textvariable=self.time_grid_var,
            width=8,
            command=self.on_grid_size_change,
        )
        time_grid_spin.grid(row=1, column=3, padx=5)
        time_grid_spin.bind("<Return>", lambda e: self.on_grid_size_change())
        # グリッドサイズの検証を追加
        self.time_grid_var.trace("w", self.validate_grid_size)

        # 値グリッドサイズ
        ttk.Label(control_frame, text="Value Grid:").grid(
            row=1, column=4, padx=5, sticky="w"
        )
        self.value_grid_var = tk.DoubleVar(value=self.value_grid_size)
        value_grid_spin = ttk.Spinbox(
            control_frame,
            from_=0.001,
            to=1000,
            increment=0.1,
            textvariable=self.value_grid_var,
            width=8,
            command=self.on_grid_size_change,
        )
        value_grid_spin.grid(row=1, column=5, padx=5)
        value_grid_spin.bind("<Return>", lambda e: self.on_grid_size_change())
        # グリッドサイズの検証を追加
        self.value_grid_var.trace("w", self.validate_grid_size)

        # グラフ表示エリア
        plot_frame = ttk.Frame(main_frame)
        plot_frame.pack(fill=tk.BOTH, expand=True)

        # Matplotlibの図とキャンバス
        self.fig = Figure(figsize=(12, 6), dpi=100)
        self.ax = self.fig.add_subplot(111)

        self.canvas = FigureCanvasTkAgg(self.fig, plot_frame)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # スクロールバー
        scroll_frame = ttk.Frame(plot_frame)
        scroll_frame.pack(side=tk.RIGHT, fill=tk.Y)

        # Y軸スクロール
        ttk.Label(scroll_frame, text="Y Range").pack()
        self.y_max_var = tk.DoubleVar(value=self.y_max)
        self.y_min_var = tk.DoubleVar(value=self.y_min)

        ttk.Label(scroll_frame, text="Max:").pack()
        y_max_spin = ttk.Spinbox(
            scroll_frame,
            from_=-1e6,
            to=1e6,
            increment=0.1,
            textvariable=self.y_max_var,
            width=8,
            command=self.update_range,
        )
        y_max_spin.pack()
        y_max_spin.bind("<Return>", lambda e: self.update_range())

        ttk.Label(scroll_frame, text="Min:").pack()
        y_min_spin = ttk.Spinbox(
            scroll_frame,
            from_=-1e6,
            to=1e6,
            increment=0.1,
            textvariable=self.y_min_var,
            width=8,
            command=self.update_range,
        )
        y_min_spin.pack()
        y_min_spin.bind("<Return>", lambda e: self.update_range())

        # X軸スクロール
        ttk.Label(scroll_frame, text="X Range").pack(pady=(20, 0))
        self.x_max_var = tk.DoubleVar(value=self.x_max)
        self.x_min_var = tk.DoubleVar(value=self.x_min)

        ttk.Label(scroll_frame, text="Max:").pack()
        x_max_spin = ttk.Spinbox(
            scroll_frame,
            from_=0,
            to=1e6,
            increment=0.1,
            textvariable=self.x_max_var,
            width=8,
            command=self.update_range,
        )
        x_max_spin.pack()
        x_max_spin.bind("<Return>", lambda e: self.update_range())

        ttk.Label(scroll_frame, text="Min:").pack()
        x_min_spin = ttk.Spinbox(
            scroll_frame,
            from_=0,
            to=1e6,
            increment=0.1,
            textvariable=self.x_min_var,
            width=8,
            command=self.update_range,
        )
        x_min_spin.pack()
        x_min_spin.bind("<Return>", lambda e: self.update_range())
        # X軸最小値の検証を追加
        self.x_min_var.trace("w", self.validate_x_min)

        ttk.Button(scroll_frame, text="Auto Scale", command=self.auto_scale).pack(
            pady=10
        )
        ttk.Button(scroll_frame, text="Zoom In", command=self.zoom_in).pack(pady=2)
        ttk.Button(scroll_frame, text="Zoom Out", command=self.zoom_out).pack(pady=2)
        ttk.Button(scroll_frame, text="Pan Left", command=self.pan_left).pack(pady=2)
        ttk.Button(scroll_frame, text="Pan Right", command=self.pan_right).pack(pady=2)
        ttk.Button(scroll_frame, text="Pan Up", command=self.pan_up).pack(pady=2)
        ttk.Button(scroll_frame, text="Pan Down", command=self.pan_down).pack(pady=2)

        # 下部情報パネル
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(5, 0))

        self.info_label = ttk.Label(
            info_frame,
            text="Left: select/drag points, Double-click: add | Wheel: zoom, Wheel+Ctrl/Shift: Y/X zoom, Middle/Right+drag: pan",
        )
        self.info_label.pack(side=tk.LEFT)

        # PWL出力テキストエリア
        self.pwl_text = tk.Text(info_frame, height=3, width=70)
        self.pwl_text.pack(side=tk.RIGHT, padx=5)

        # テキストエリアの変更を監視
        self.pwl_text.bind("<KeyRelease>", self.on_pwl_text_change)
        self.pwl_text.bind("<Button-1>", self.on_pwl_text_focus)  # フォーカス時

        # PWLテキスト解析用のフラグ
        self.updating_from_plot = False  # プロットからの更新中かどうか

        # マウスイベントのバインド
        self.canvas.mpl_connect("button_press_event", self.on_click)
        self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.canvas.mpl_connect("button_release_event", self.on_release)
        self.canvas.mpl_connect("scroll_event", self.on_scroll)

        # キーボードショートカット
        self.root.bind("<Control-plus>", lambda e: self.zoom_in())
        self.root.bind("<Control-minus>", lambda e: self.zoom_out())
        self.root.bind("<Control-equal>", lambda e: self.zoom_in())  # +キーのため
        self.root.bind("<Left>", lambda e: self.safe_pan_left(e))
        self.root.bind("<Right>", lambda e: self.safe_pan_right(e))
        self.root.bind("<Up>", lambda e: self.safe_pan_up(e))
        self.root.bind("<Down>", lambda e: self.safe_pan_down(e))
        self.root.bind("<Control-0>", lambda e: self.auto_scale())
        self.root.bind("<Delete>", lambda e: self.safe_delete_point(e))
        self.root.bind("<f>", lambda e: self.safe_auto_scale(e))
        self.root.bind("<F>", lambda e: self.safe_auto_scale(e))

        # フォーカスを設定してキーボードイベントを受け取れるようにする
        self.root.focus_set()

    def validate_x_min(self, *args):
        """X軸最小値が負にならないように制限"""
        try:
            value = self.x_min_var.get()
            if value < 0:
                self.x_min_var.set(0)
        except:
            pass

    def validate_grid_size(self, *args):
        """グリッドサイズが0以下にならないように制限"""
        try:
            time_value = self.time_grid_var.get()
            if time_value <= 0:
                self.time_grid_var.set(0.001)  # 最小値を0.001に設定

            value_value = self.value_grid_var.get()
            if value_value <= 0:
                self.value_grid_var.set(0.001)  # 最小値を0.001に設定
        except:
            # エラーが発生した場合はデフォルト値に戻す
            self.time_grid_var.set(1.0)
            self.value_grid_var.set(1.0)

    def on_grid_snap_change(self):
        """グリッド拘束設定の変更"""
        self.grid_snap_enabled = self.grid_snap_var.get()
        if self.grid_snap_enabled:
            # 既存の点をグリッドに拘束
            self.snap_all_points_to_grid()

    def on_grid_size_change(self):
        """グリッドサイズの変更"""
        try:
            # 値を取得し、最小値チェック
            time_size = self.time_grid_var.get()
            value_size = self.value_grid_var.get()

            # 0以下の場合は最小値に修正
            if time_size <= 0:
                time_size = 0.001
                self.time_grid_var.set(time_size)

            if value_size <= 0:
                value_size = 0.001
                self.value_grid_var.set(value_size)

            # 値を更新
            self.time_grid_size = time_size
            self.value_grid_size = value_size

            if self.grid_snap_enabled:
                # 既存の点をグリッドに拘束
                self.snap_all_points_to_grid()
        except Exception as e:
            # エラーが発生した場合はデフォルト値に戻す
            messagebox.showwarning(
                "Grid Size Error",
                f"Invalid grid size. Reset to default values.\nError: {e}",
            )
            self.time_grid_size = 1.0
            self.value_grid_size = 1.0
            self.time_grid_var.set(self.time_grid_size)
            self.value_grid_var.set(self.value_grid_size)

    def snap_to_grid(self, time_display, value_display):
        """値をグリッドに拘束"""
        if not self.grid_snap_enabled:
            return time_display, value_display

        try:
            # グリッドサイズが0以下の場合は拘束しない
            if self.time_grid_size <= 0 or self.value_grid_size <= 0:
                return time_display, value_display

            # グリッドサイズで丸める
            snapped_time = (
                round(time_display / self.time_grid_size) * self.time_grid_size
            )
            snapped_value = (
                round(value_display / self.value_grid_size) * self.value_grid_size
            )

            # 時間は0以上に制限
            snapped_time = max(0, snapped_time)

            return snapped_time, snapped_value
        except Exception as e:
            # エラーが発生した場合は元の値を返す
            return time_display, value_display

    def snap_all_points_to_grid(self):
        """全ての点をグリッドに拘束"""
        if not self.grid_snap_enabled:
            return

        time_scale = self.time_prefixes[self.time_unit]
        if self.source_type == "Voltage":
            value_scale = self.voltage_prefixes[self.value_unit]
        else:
            value_scale = self.current_prefixes[self.value_unit]

        new_points = []
        for t, v in self.pwl_points:
            # 表示単位に変換
            t_display = t / time_scale
            v_display = v / value_scale

            # グリッドに拘束
            t_snapped, v_snapped = self.snap_to_grid(t_display, v_display)

            # 実際の値に戻す
            real_time = t_snapped * time_scale
            real_value = v_snapped * value_scale

            new_points.append((real_time, real_value))

        self.pwl_points = new_points
        self.pwl_points.sort(key=lambda x: x[0])  # 時間順にソート
        self.update_plot()

    def update_info_label(self):
        if self.selected_point is not None:
            time_scale = self.time_prefixes[self.time_unit]
            if self.source_type == "Voltage":
                value_scale = self.voltage_prefixes[self.value_unit]
            else:
                value_scale = self.current_prefixes[self.value_unit]

            t, v = self.pwl_points[self.selected_point]
            t_display = t / time_scale
            v_display = v / value_scale

            self.info_label.config(
                text=f"Selected Point {self.selected_point + 1}: ({t_display:.3f} {self.time_unit}, {v_display:.3f} {self.value_unit}) - Press Delete Point to remove"
            )
        else:
            grid_status = " | Grid: ON" if self.grid_snap_enabled else ""
            self.info_label.config(
                text=f"Left: select/drag points, Double-click: add | Wheel: zoom, Wheel+Ctrl/Shift: Y/X zoom, Middle/Right+drag: pan{grid_status}"
            )

    def on_source_type_change(self, event=None):
        self.source_type = self.source_var.get()
        if self.source_type == "Voltage":
            self.value_combo["values"] = list(self.voltage_prefixes.keys())
            if self.value_unit not in self.voltage_prefixes:
                self.value_unit = "mV"
                self.value_unit_var.set(self.value_unit)
        else:  # Current
            self.value_combo["values"] = list(self.current_prefixes.keys())
            if self.value_unit not in self.current_prefixes:
                self.value_unit = "mA"
                self.value_unit_var.set(self.value_unit)
        self.update_plot()

    def on_unit_change(self, event=None):
        self.time_unit = self.time_unit_var.get()
        self.value_unit = self.value_unit_var.get()
        self.update_plot()

    def update_range(self):
        self.x_min = max(0, self.x_min_var.get())  # 時間軸の最小値を0以上に制限
        self.x_max = self.x_max_var.get()
        self.y_min = self.y_min_var.get()
        self.y_max = self.y_max_var.get()

        # X軸の最小値が修正された場合、変数も更新
        if self.x_min != self.x_min_var.get():
            self.x_min_var.set(self.x_min)

        self.update_plot()

    def zoom_in(self):
        """ズームイン（50%縮小）"""
        x_center = (self.x_min + self.x_max) / 2
        y_center = (self.y_min + self.y_max) / 2
        x_range = (self.x_max - self.x_min) * 0.25  # 50%縮小
        y_range = (self.y_max - self.y_min) * 0.25

        self.x_min_var.set(x_center - x_range)
        self.x_max_var.set(x_center + x_range)
        self.y_min_var.set(y_center - y_range)
        self.y_max_var.set(y_center + y_range)
        self.update_range()

    def zoom_out(self):
        """ズームアウト（2倍拡大）"""
        x_center = (self.x_min + self.x_max) / 2
        y_center = (self.y_min + self.y_max) / 2
        x_range = (self.x_max - self.x_min) * 1.0  # 2倍拡大
        y_range = (self.y_max - self.y_min) * 1.0

        self.x_min_var.set(x_center - x_range)
        self.x_max_var.set(x_center + x_range)
        self.y_min_var.set(y_center - y_range)
        self.y_max_var.set(y_center + y_range)
        self.update_range()

    def pan_left(self):
        """左にパン（25%移動）"""
        x_range = self.x_max - self.x_min
        shift = x_range * 0.25
        new_x_min = self.x_min - shift
        new_x_max = self.x_max - shift

        # 時間軸が負にならないように制限
        if new_x_min < 0:
            new_x_max = new_x_max - new_x_min  # 差分を調整
            new_x_min = 0

        self.x_min_var.set(new_x_min)
        self.x_max_var.set(new_x_max)
        self.update_range()

    def pan_right(self):
        """右にパン（25%移動）"""
        x_range = self.x_max - self.x_min
        shift = x_range * 0.25
        self.x_min_var.set(self.x_min + shift)
        self.x_max_var.set(self.x_max + shift)
        self.update_range()

    def pan_up(self):
        """上にパン（25%移動）"""
        y_range = self.y_max - self.y_min
        shift = y_range * 0.25
        self.y_min_var.set(self.y_min + shift)
        self.y_max_var.set(self.y_max + shift)
        self.update_range()

    def pan_down(self):
        """下にパン（25%移動）"""
        y_range = self.y_max - self.y_min
        shift = y_range * 0.25
        self.y_min_var.set(self.y_min - shift)
        self.y_max_var.set(self.y_max - shift)
        self.update_range()

    def on_scroll(self, event):
        """マウスホイールでのズーム操作"""
        if event.inaxes != self.ax:
            return

        # ズーム倍率
        zoom_factor = 0.9 if event.button == "up" else 1.1

        # マウス位置を中心にズーム
        x_center = event.xdata
        y_center = event.ydata

        if x_center is None or y_center is None:
            return

        # 修飾キーによる動作の分岐
        if hasattr(event, "key") and event.key == "control":
            # Ctrl+ホイール: 縦軸のみズーム
            y_range = (self.y_max - self.y_min) * zoom_factor / 2
            self.y_min_var.set(y_center - y_range)
            self.y_max_var.set(y_center + y_range)
        elif hasattr(event, "key") and event.key == "shift":
            # Shift+ホイール: 横軸のみズーム
            x_range = (self.x_max - self.x_min) * zoom_factor / 2
            new_x_min = x_center - x_range
            new_x_max = x_center + x_range

            # 時間軸が負にならないように制限
            if new_x_min < 0:
                new_x_max = new_x_max - new_x_min
                new_x_min = 0

            self.x_min_var.set(new_x_min)
            self.x_max_var.set(new_x_max)
        else:
            # 通常のホイール: 両軸ズーム
            x_range = (self.x_max - self.x_min) * zoom_factor / 2
            y_range = (self.y_max - self.y_min) * zoom_factor / 2

            new_x_min = x_center - x_range
            new_x_max = x_center + x_range

            # 時間軸が負にならないように制限
            if new_x_min < 0:
                new_x_max = new_x_max - new_x_min
                new_x_min = 0

            self.x_min_var.set(new_x_min)
            self.x_max_var.set(new_x_max)
            self.y_min_var.set(y_center - y_range)
            self.y_max_var.set(y_center + y_range)

        self.update_range()

    def auto_scale(self):
        if not self.pwl_points:
            return

        times = [p[0] for p in self.pwl_points]
        values = [p[1] for p in self.pwl_points]

        # 時間軸
        t_min, t_max = min(times), max(times)
        t_range = t_max - t_min
        margin = t_range * 0.1 if t_range > 0 else 1

        # 単位系に変換
        time_scale = self.time_prefixes[self.time_unit]
        self.x_min_var.set((t_min - margin) / time_scale)
        self.x_max_var.set((t_max + margin) / time_scale)

        # 値軸
        v_min, v_max = min(values), max(values)
        v_range = v_max - v_min
        margin = v_range * 0.1 if v_range > 0 else 1

        # 単位系に変換
        if self.source_type == "Voltage":
            value_scale = self.voltage_prefixes[self.value_unit]
        else:
            value_scale = self.current_prefixes[self.value_unit]

        self.y_min_var.set((v_min - margin) / value_scale)
        self.y_max_var.set((v_max + margin) / value_scale)

        self.update_range()

    def update_plot(self):
        self.ax.clear()

        if not self.pwl_points:
            return

        # 単位系の変換
        time_scale = self.time_prefixes[self.time_unit]
        if self.source_type == "Voltage":
            value_scale = self.voltage_prefixes[self.value_unit]
        else:
            value_scale = self.current_prefixes[self.value_unit]

        # 点を単位系に変換
        times = [p[0] / time_scale for p in self.pwl_points]
        values = [p[1] / value_scale for p in self.pwl_points]

        # PWL線の描画
        self.ax.plot(times, values, "b-", linewidth=2, label="PWL")

        # 点の描画
        for i, (t, v) in enumerate(zip(times, values)):
            if i == self.selected_point:
                # 選択された点は赤色で大きく表示
                self.ax.plot(
                    t,
                    v,
                    "o",
                    color="red",
                    markersize=12,
                    picker=True,
                    markeredgecolor="darkred",
                    markeredgewidth=2,
                )
            else:
                self.ax.plot(t, v, "o", color="blue", markersize=8, picker=True)
            self.ax.annotate(
                f"({t:.3f}, {v:.3f})",
                (t, v),
                xytext=(5, 5),
                textcoords="offset points",
                fontsize=8,
            )

        # グリッド
        self.ax.grid(True, alpha=0.3)

        # グリッド拘束が有効な場合、グリッド線を強調表示
        if (
            self.grid_snap_enabled
            and self.time_grid_size > 0
            and self.value_grid_size > 0
        ):
            try:
                # 時間グリッド線
                x_start = (self.x_min // self.time_grid_size) * self.time_grid_size
                x_grid_lines = []
                x = x_start
                count = 0  # 無限ループ防止
                while x <= self.x_max and count < 1000:  # 最大1000本のグリッド線
                    if x >= self.x_min:
                        x_grid_lines.append(x)
                    x += self.time_grid_size
                    count += 1

                for x_line in x_grid_lines:
                    self.ax.axvline(
                        x=x_line, color="gray", linestyle="-", alpha=0.5, linewidth=0.5
                    )

                # 値グリッド線
                y_start = (self.y_min // self.value_grid_size) * self.value_grid_size
                y_grid_lines = []
                y = y_start
                count = 0  # 無限ループ防止
                while y <= self.y_max and count < 1000:  # 最大1000本のグリッド線
                    if y >= self.y_min:
                        y_grid_lines.append(y)
                    y += self.value_grid_size
                    count += 1

                for y_line in y_grid_lines:
                    self.ax.axhline(
                        y=y_line, color="gray", linestyle="-", alpha=0.5, linewidth=0.5
                    )
            except Exception as e:
                # グリッド線描画でエラーが発生した場合は無視して続行
                pass

        # 軸ラベル
        unit_label = (
            self.value_unit if self.source_type == "Voltage" else self.value_unit
        )
        self.ax.set_xlabel(f"Time ({self.time_unit})")
        self.ax.set_ylabel(f"{self.source_type} ({unit_label})")
        self.ax.set_title(f"PWL {self.source_type} Source")

        # 表示範囲設定
        self.ax.set_xlim(self.x_min, self.x_max)
        self.ax.set_ylim(self.y_min, self.y_max)

        self.canvas.draw()
        self.generate_pwl_text()

    def on_click(self, event):
        if event.inaxes != self.ax:
            return

        # 中クリック（ホイールクリック）または右クリックでパン開始
        if event.button == 2 or event.button == 3:  # 中クリックまたは右クリック
            self.pan_start = (event.xdata, event.ydata)
            self.panning = True
            return

        # 左クリックの処理
        if event.button == 1:
            # 近い点を探す
            if self.pwl_points:
                time_scale = self.time_prefixes[self.time_unit]
                if self.source_type == "Voltage":
                    value_scale = self.voltage_prefixes[self.value_unit]
                else:
                    value_scale = self.current_prefixes[self.value_unit]

                times = [p[0] / time_scale for p in self.pwl_points]
                values = [p[1] / value_scale for p in self.pwl_points]

                # 最も近い点を探す
                distances = [
                    (abs(event.xdata - t) + abs(event.ydata - v))
                    for t, v in zip(times, values)
                ]
                min_distance = min(distances)

                # 選択の許容範囲
                tolerance = 0.1 * max(self.x_max - self.x_min, self.y_max - self.y_min)

                if min_distance < tolerance:
                    self.selected_point = distances.index(min_distance)
                    self.update_plot()
                    self.update_info_label()
                    return

            # 選択された点がない場合は選択解除
            self.selected_point = None
            self.update_plot()
            self.update_info_label()

            # 新しい点を追加
            if event.dblclick:
                self.add_point_at(event.xdata, event.ydata)

    def on_motion(self, event):
        if event.inaxes != self.ax:
            return

        # パン操作中の処理
        if self.panning and self.pan_start is not None:
            if event.xdata is not None and event.ydata is not None:
                dx = self.pan_start[0] - event.xdata
                dy = self.pan_start[1] - event.ydata

                # 新しい表示範囲を計算
                new_x_min = self.x_min + dx
                new_x_max = self.x_max + dx

                # 時間軸が負にならないように制限
                if new_x_min < 0:
                    new_x_max = new_x_max - new_x_min
                    new_x_min = 0

                # 表示範囲を移動
                self.x_min_var.set(new_x_min)
                self.x_max_var.set(new_x_max)
                self.y_min_var.set(self.y_min + dy)
                self.y_max_var.set(self.y_max + dy)
                self.update_range()
            return

        # 点の移動処理
        if self.selected_point is not None and event.button == 1:  # 左クリックドラッグ
            self.move_point(event.xdata, event.ydata)

    def on_release(self, event):
        # パン操作終了
        if event.button == 2 or event.button == 3:  # 中クリックまたは右クリック
            self.panning = False
            self.pan_start = None

    def find_unique_time(self, target_time, exclude_index=None):
        """重複しない時間を見つける"""
        time_scale = self.time_prefixes[self.time_unit]
        min_offset = 1e-6 * time_scale  # 最小オフセット（現在の時間単位の0.001倍）

        # グリッド拘束が有効な場合、グリッドサイズの半分を最小オフセットとする
        if self.grid_snap_enabled and self.time_grid_size > 0:
            grid_size_in_base = self.time_grid_size * time_scale
            min_offset = max(
                min_offset, grid_size_in_base * 0.0001
            )  # グリッドサイズの0.1%

        # 既存の時間リストを取得（除外するインデックスがあれば除く）
        existing_times = []
        for i, (t, v) in enumerate(self.pwl_points):
            if exclude_index is None or i != exclude_index:
                existing_times.append(t)

        # 目標時間が既存の時間と重複していないかチェック
        current_time = target_time
        offset_direction = 1  # 1なら右方向、-1なら左方向
        max_attempts = 100  # 無限ループ防止

        for attempt in range(max_attempts):
            # 現在時間が他の点と重複していないかチェック
            is_duplicate = False
            for existing_time in existing_times:
                if abs(current_time - existing_time) < min_offset / 2:
                    is_duplicate = True
                    break

            if not is_duplicate and current_time >= 0:
                return current_time

            # 重複している場合は少しずらす
            if offset_direction > 0:
                current_time = target_time + min_offset * attempt
                if current_time < 0:  # 負になる場合は右方向に切り替え
                    offset_direction = -1
                    current_time = target_time
            else:
                current_time = target_time - min_offset * attempt
                if current_time < 0:  # 負になる場合は右方向の大きなオフセット
                    current_time = target_time + min_offset * (attempt + 1)

        # 最終的に見つからない場合は、最大時間の後に配置
        if existing_times:
            max_time = max(existing_times)
            return max_time + min_offset
        else:
            return max(0, target_time)

    def add_point_at(self, x, y):
        time_scale = self.time_prefixes[self.time_unit]
        if self.source_type == "Voltage":
            value_scale = self.voltage_prefixes[self.value_unit]
        else:
            value_scale = self.current_prefixes[self.value_unit]

        # 表示単位での値
        t_display = x if x is not None else 0
        v_display = y if y is not None else 0

        # グリッドに拘束
        t_display, v_display = self.snap_to_grid(t_display, v_display)

        # 単位系を戻す
        real_time = t_display * time_scale
        real_value = v_display * value_scale

        # 時間が負にならないように制限
        real_time = max(0, real_time)

        # 重複しない時間を見つける
        unique_time = self.find_unique_time(real_time)

        # 時間順に挿入
        insert_index = 0
        for i, (t, v) in enumerate(self.pwl_points):
            if unique_time > t:
                insert_index = i + 1
            else:
                break

        self.pwl_points.insert(insert_index, (unique_time, real_value))
        self.update_plot()

    def add_point(self):
        # 最後の点の次の時間に追加
        if self.pwl_points:
            last_time = max(p[0] for p in self.pwl_points)
            time_scale = self.time_prefixes[self.time_unit]
            new_time = last_time + time_scale  # 1単位分後
        else:
            new_time = 0

        # 重複しない時間を見つける
        unique_time = self.find_unique_time(new_time)

        self.pwl_points.append((unique_time, 0))
        self.pwl_points.sort(key=lambda x: x[0])  # 時間順にソート
        self.update_plot()

    def delete_point(self):
        if self.selected_point is not None and len(self.pwl_points) > 2:
            del self.pwl_points[self.selected_point]
            self.selected_point = None
            self.update_plot()
            self.update_info_label()
        elif self.selected_point is None:
            messagebox.showwarning(
                "No Selection", "Please select a point first by clicking on it."
            )
        elif len(self.pwl_points) <= 2:
            messagebox.showwarning(
                "Minimum Points", "At least 2 points are required for PWL."
            )

    def move_point(self, x, y):
        if self.selected_point is None:
            return

        time_scale = self.time_prefixes[self.time_unit]
        if self.source_type == "Voltage":
            value_scale = self.voltage_prefixes[self.value_unit]
        else:
            value_scale = self.current_prefixes[self.value_unit]

        # 表示単位での値
        t_display = x if x is not None else 0
        v_display = y if y is not None else 0

        # グリッドに拘束
        t_display, v_display = self.snap_to_grid(t_display, v_display)

        # 単位系を戻す
        real_time = t_display * time_scale
        real_value = v_display * value_scale

        # 時間が負にならないように制限
        real_time = max(0, real_time)

        # 重複しない時間を見つける（現在選択中の点は除外）
        unique_time = self.find_unique_time(real_time, self.selected_point)

        self.pwl_points[self.selected_point] = (unique_time, real_value)
        self.pwl_points.sort(key=lambda x: x[0])  # 時間順にソート

        # ソート後の新しいインデックスを見つける
        for i, (t, v) in enumerate(self.pwl_points):
            if abs(t - unique_time) < 1e-12 and abs(v - real_value) < 1e-12:
                self.selected_point = i
                break

        self.update_plot()

    def on_pwl_text_focus(self, event):
        """PWLテキストエリアにフォーカスした時の処理"""
        # 自動更新を一時停止する場合などに使用
        pass

    def on_pwl_text_change(self, event):
        """PWLテキストエリアの内容が変更された時の処理"""
        if self.updating_from_plot:
            return  # プロットからの更新中は処理しない

        # 遅延実行でパースを行う（連続入力に対応）
        if hasattr(self, "_text_update_timer"):
            self.root.after_cancel(self._text_update_timer)

        self._text_update_timer = self.root.after(
            500, self.parse_pwl_text
        )  # 500ms後に実行

    def parse_pwl_text(self):
        """PWLテキストを解析してグラフを更新"""
        try:
            pwl_text = self.pwl_text.get(1.0, tk.END).strip()

            # PWLコマンドの解析
            if not pwl_text or pwl_text == "Need at least 2 points":
                return

            # PWL(...)形式から中身を抽出
            if pwl_text.startswith("PWL(") and pwl_text.endswith(")"):
                content = pwl_text[4:-1]  # PWL( と ) を除去
            else:
                # PWL(...)がない場合は、そのまま数値列として解釈
                content = pwl_text

            # 数値ペアを抽出
            parts = content.split()
            if len(parts) < 4 or len(parts) % 2 != 0:
                # 最低2点必要、かつペア数でなければエラー
                return

            # 新しいPWL点を作成
            new_points = []
            for i in range(0, len(parts), 2):
                try:
                    time_val = float(parts[i])
                    voltage_val = float(parts[i + 1])

                    # 時間が負でないことを確認
                    if time_val < 0:
                        time_val = 0

                    new_points.append((time_val, voltage_val))
                except ValueError:
                    # 数値変換エラーの場合は処理を中断
                    return

            # 時間順にソート
            new_points.sort(key=lambda x: x[0])

            # 最低2点必要
            if len(new_points) < 2:
                return

            # PWL点を更新
            self.pwl_points = new_points
            self.selected_point = None  # 選択をクリア

            # グリッド拘束が有効な場合は適用
            if self.grid_snap_enabled:
                self.snap_all_points_to_grid()
            else:
                self.update_plot()

        except Exception as e:
            # エラーが発生した場合は何もしない（無効な入力として扱う）
            pass

    def generate_pwl_text(self):
        if len(self.pwl_points) < 2:
            pwl_cmd = "Need at least 2 points"
        else:
            # 時間順にソート
            sorted_points = sorted(self.pwl_points, key=lambda x: x[0])

            # PWLコマンド生成
            pwl_pairs = []
            for t, v in sorted_points:
                pwl_pairs.append(f"{t:.6g} {v:.6g}")

            source_name = "V" if self.source_type == "Voltage" else "I"
            pwl_cmd = f"PWL({' '.join(pwl_pairs)})"

        # プロットからの更新フラグを立てる
        self.updating_from_plot = True

        # 現在のテキストと同じ場合は更新しない（カーソル位置保持のため）
        current_text = self.pwl_text.get(1.0, tk.END).strip()
        if current_text != pwl_cmd:
            # カーソル位置を保存
            cursor_pos = self.pwl_text.index(tk.INSERT)

            # テキストを更新
            self.pwl_text.delete(1.0, tk.END)
            self.pwl_text.insert(tk.END, pwl_cmd)

            # テキストエリアにフォーカスがある場合のみカーソル位置を復元
            if self.pwl_text == self.root.focus_get():
                try:
                    # 新しいテキストの長さを超えない範囲でカーソル位置を復元
                    new_length = len(pwl_cmd)
                    cursor_row, cursor_col = map(int, cursor_pos.split("."))

                    # 行数チェック（PWLテキストは通常1行なので1行目に制限）
                    if cursor_row > 1:
                        cursor_row = 1

                    # 列数チェック
                    if cursor_col > new_length:
                        cursor_col = new_length

                    # カーソル位置を復元
                    self.pwl_text.mark_set(tk.INSERT, f"{cursor_row}.{cursor_col}")
                except:
                    # エラーが発生した場合は末尾に設定
                    self.pwl_text.mark_set(tk.INSERT, tk.END)

        self.updating_from_plot = False

    def generate_pwl(self):
        self.generate_pwl_text()
        # クリップボードにコピー
        self.root.clipboard_clear()
        self.root.clipboard_append(self.pwl_text.get(1.0, tk.END).strip())
        messagebox.showinfo("PWL Generated", "PWL command copied to clipboard!")

    def save_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if filename:
            data = {
                "pwl_points": self.pwl_points,
                "source_type": self.source_type,
                "time_unit": self.time_unit,
                "value_unit": self.value_unit,
                "x_range": [self.x_min, self.x_max],
                "y_range": [self.y_min, self.y_max],
                "grid_snap_enabled": self.grid_snap_enabled,
                "time_grid_size": self.time_grid_size,
                "value_grid_size": self.value_grid_size,
            }
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Saved", f"File saved: {filename}")

    def load_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, "r") as f:
                    data = json.load(f)

                self.pwl_points = data.get("pwl_points", [(0, 0), (1e-6, 0)])
                self.source_type = data.get("source_type", "Voltage")
                self.time_unit = data.get("time_unit", "μs")
                self.value_unit = data.get("value_unit", "mV")

                x_range = data.get("x_range", [0, 10])
                y_range = data.get("y_range", [-5, 5])

                # グリッド設定の復元
                self.grid_snap_enabled = data.get("grid_snap_enabled", False)
                self.time_grid_size = data.get("time_grid_size", 1.0)
                self.value_grid_size = data.get("value_grid_size", 1.0)

                # UI更新
                self.source_var.set(self.source_type)
                self.time_unit_var.set(self.time_unit)
                self.value_unit_var.set(self.value_unit)
                self.grid_snap_var.set(self.grid_snap_enabled)
                self.time_grid_var.set(self.time_grid_size)
                self.value_grid_var.set(self.value_grid_size)

                self.x_min_var.set(x_range[0])
                self.x_max_var.set(x_range[1])
                self.y_min_var.set(y_range[0])
                self.y_max_var.set(y_range[1])

                self.on_source_type_change()
                self.update_range()

                messagebox.showinfo("Loaded", f"File loaded: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")

    def safe_pan_left(self, event):
        """フォーカスをチェックしてから左にパン"""
        if self.should_handle_arrow_key(event):
            self.pan_left()

    def safe_pan_right(self, event):
        """フォーカスをチェックしてから右にパン"""
        if self.should_handle_arrow_key(event):
            self.pan_right()

    def safe_pan_up(self, event):
        """フォーカスをチェックしてから上にパン"""
        if self.should_handle_arrow_key(event):
            self.pan_up()

    def safe_pan_down(self, event):
        """フォーカスをチェックしてから下にパン"""
        if self.should_handle_arrow_key(event):
            self.pan_down()

    def safe_delete_point(self, event):
        """フォーカスをチェックしてから点を削除"""
        if self.should_handle_key_action(event):
            self.delete_point()

    def safe_auto_scale(self, event):
        """フォーカスをチェックしてからオートスケール"""
        if self.should_handle_key_action(event):
            self.auto_scale()

    def should_handle_arrow_key(self, event):
        """矢印キーをパン操作で処理すべきかどうかを判定"""
        focused_widget = self.root.focus_get()

        # フォーカスされているウィジェットがない場合は処理する
        if focused_widget is None:
            return True

        # テキストウィジェット（PWL出力エリア）にフォーカスがある場合は処理しない
        if isinstance(focused_widget, tk.Text):
            return False

        # Spinboxにフォーカスがある場合は処理しない
        if isinstance(focused_widget, ttk.Spinbox):
            return False

        # Entryにフォーカスがある場合は処理しない
        if isinstance(focused_widget, (tk.Entry, ttk.Entry)):
            return False

        # Comboboxにフォーカスがある場合は処理しない
        if isinstance(focused_widget, ttk.Combobox):
            return False

        # その他の場合は処理する
        return True

    def should_handle_key_action(self, event):
        """キーアクションを処理すべきかどうかを判定"""
        focused_widget = self.root.focus_get()

        # フォーカスされているウィジェットがない場合は処理する
        if focused_widget is None:
            return True

        # テキストウィジェット（PWL出力エリア）にフォーカスがある場合は処理しない
        if isinstance(focused_widget, tk.Text):
            return False

        # Spinboxにフォーカスがある場合は処理しない
        if isinstance(focused_widget, ttk.Spinbox):
            return False

        # Entryにフォーカスがある場合は処理しない
        if isinstance(focused_widget, (tk.Entry, ttk.Entry)):
            return False

        # Comboboxにフォーカスがある場合は処理しない
        if isinstance(focused_widget, ttk.Combobox):
            return False

        # その他の場合は処理する
        return True


if __name__ == "__main__":
    root = tk.Tk()
    app = PWLTool(root)
    root.mainloop()
