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
        self.root.title("LTspice PWL Generator")
        self.root.geometry("1200x800")

        # PWL点のリスト [(時間, 値)]
        self.pwl_points = [(0, 0), (1e-6, 0)]  # 初期値: (0s, 0V), (1μs, 0V)

        # SI接頭語の定義
        self.time_prefixes = {
            'fs': 1e-15, 'ps': 1e-12, 'ns': 1e-9, 'μs': 1e-6, 'ms': 1e-3, 's': 1
        }
        self.voltage_prefixes = {
            'μV': 1e-6, 'mV': 1e-3, 'V': 1, 'kV': 1e3
        }
        self.current_prefixes = {
            'pA': 1e-12, 'nA': 1e-9, 'μA': 1e-6, 'mA': 1e-3, 'A': 1
        }

        # デフォルト単位
        self.time_unit = 'μs'
        self.value_unit = 'mV'
        self.source_type = 'Voltage'  # 'Voltage' or 'Current'

        # 表示範囲
        self.x_min, self.x_max = 0, 10
        self.y_min, self.y_max = -5, 5

        # 選択された点のインデックス
        self.selected_point = None

        # パン操作用の変数
        self.pan_start = None
        self.panning = False

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
        ttk.Label(control_frame, text="Source Type:").grid(row=0, column=0, padx=5, sticky="w")
        self.source_var = tk.StringVar(value=self.source_type)
        source_combo = ttk.Combobox(control_frame, textvariable=self.source_var,
                                   values=['Voltage', 'Current'], state='readonly', width=10)
        source_combo.grid(row=0, column=1, padx=5)
        source_combo.bind('<<ComboboxSelected>>', self.on_source_type_change)

        # 時間単位選択
        ttk.Label(control_frame, text="Time Unit:").grid(row=0, column=2, padx=5, sticky="w")
        self.time_unit_var = tk.StringVar(value=self.time_unit)
        time_combo = ttk.Combobox(control_frame, textvariable=self.time_unit_var,
                                 values=list(self.time_prefixes.keys()), state='readonly', width=8)
        time_combo.grid(row=0, column=3, padx=5)
        time_combo.bind('<<ComboboxSelected>>', self.on_unit_change)

        # 値単位選択
        ttk.Label(control_frame, text="Value Unit:").grid(row=0, column=4, padx=5, sticky="w")
        self.value_unit_var = tk.StringVar(value=self.value_unit)
        value_combo = ttk.Combobox(control_frame, textvariable=self.value_unit_var,
                                  values=list(self.voltage_prefixes.keys()), state='readonly', width=8)
        value_combo.grid(row=0, column=5, padx=5)
        value_combo.bind('<<ComboboxSelected>>', self.on_unit_change)
        self.value_combo = value_combo

        # ボタン
        ttk.Button(control_frame, text="Add Point", command=self.add_point).grid(row=0, column=6, padx=5)
        ttk.Button(control_frame, text="Delete Point", command=self.delete_point).grid(row=0, column=7, padx=5)
        ttk.Button(control_frame, text="Generate PWL", command=self.generate_pwl).grid(row=0, column=8, padx=5)
        ttk.Button(control_frame, text="Save", command=self.save_file).grid(row=0, column=9, padx=5)
        ttk.Button(control_frame, text="Load", command=self.load_file).grid(row=0, column=10, padx=5)

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
        y_max_spin = ttk.Spinbox(scroll_frame, from_=-1e6, to=1e6, increment=0.1,
                                textvariable=self.y_max_var, width=8, command=self.update_range)
        y_max_spin.pack()
        y_max_spin.bind('<Return>', lambda e: self.update_range())

        ttk.Label(scroll_frame, text="Min:").pack()
        y_min_spin = ttk.Spinbox(scroll_frame, from_=-1e6, to=1e6, increment=0.1,
                                textvariable=self.y_min_var, width=8, command=self.update_range)
        y_min_spin.pack()
        y_min_spin.bind('<Return>', lambda e: self.update_range())

        # X軸スクロール
        ttk.Label(scroll_frame, text="X Range").pack(pady=(20, 0))
        self.x_max_var = tk.DoubleVar(value=self.x_max)
        self.x_min_var = tk.DoubleVar(value=self.x_min)

        ttk.Label(scroll_frame, text="Max:").pack()
        x_max_spin = ttk.Spinbox(scroll_frame, from_=0, to=1e6, increment=0.1,
                                textvariable=self.x_max_var, width=8, command=self.update_range)
        x_max_spin.pack()
        x_max_spin.bind('<Return>', lambda e: self.update_range())

        ttk.Label(scroll_frame, text="Min:").pack()
        x_min_spin = ttk.Spinbox(scroll_frame, from_=0, to=1e6, increment=0.1,
                                textvariable=self.x_min_var, width=8, command=self.update_range)
        x_min_spin.pack()
        x_min_spin.bind('<Return>', lambda e: self.update_range())

        ttk.Button(scroll_frame, text="Auto Scale", command=self.auto_scale).pack(pady=10)
        ttk.Button(scroll_frame, text="Zoom In", command=self.zoom_in).pack(pady=2)
        ttk.Button(scroll_frame, text="Zoom Out", command=self.zoom_out).pack(pady=2)
        ttk.Button(scroll_frame, text="Pan Left", command=self.pan_left).pack(pady=2)
        ttk.Button(scroll_frame, text="Pan Right", command=self.pan_right).pack(pady=2)
        ttk.Button(scroll_frame, text="Pan Up", command=self.pan_up).pack(pady=2)
        ttk.Button(scroll_frame, text="Pan Down", command=self.pan_down).pack(pady=2)

        # 下部情報パネル
        info_frame = ttk.Frame(main_frame)
        info_frame.pack(fill=tk.X, pady=(5, 0))

        self.info_label = ttk.Label(info_frame, text="Left: select/drag points, Double-click: add | Wheel: zoom, Wheel+Ctrl/Shift: Y/X zoom, Middle/Right+drag: pan")
        self.info_label.pack(side=tk.LEFT)

        # PWL出力テキストエリア
        self.pwl_text = tk.Text(info_frame, height=3, width=50)
        self.pwl_text.pack(side=tk.RIGHT, padx=5)

        # マウスイベントのバインド
        self.canvas.mpl_connect('button_press_event', self.on_click)
        self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.canvas.mpl_connect('button_release_event', self.on_release)
        self.canvas.mpl_connect('scroll_event', self.on_scroll)

        # キーボードショートカット
        self.root.bind('<Control-plus>', lambda e: self.zoom_in())
        self.root.bind('<Control-minus>', lambda e: self.zoom_out())
        self.root.bind('<Control-equal>', lambda e: self.zoom_in())  # +キーのため
        self.root.bind('<Left>', lambda e: self.pan_left())
        self.root.bind('<Right>', lambda e: self.pan_right())
        self.root.bind('<Up>', lambda e: self.pan_up())
        self.root.bind('<Down>', lambda e: self.pan_down())
        self.root.bind('<Control-0>', lambda e: self.auto_scale())

        # フォーカスを設定してキーボードイベントを受け取れるようにする
        self.root.focus_set()

    def update_info_label(self):
        if self.selected_point is not None:
            time_scale = self.time_prefixes[self.time_unit]
            if self.source_type == 'Voltage':
                value_scale = self.voltage_prefixes[self.value_unit]
            else:
                value_scale = self.current_prefixes[self.value_unit]

            t, v = self.pwl_points[self.selected_point]
            t_display = t / time_scale
            v_display = v / value_scale

            self.info_label.config(text=f"Selected Point {self.selected_point + 1}: ({t_display:.3f} {self.time_unit}, {v_display:.3f} {self.value_unit}) - Press Delete Point to remove")
        else:
            self.info_label.config(text="Left: select/drag points, Double-click: add | Wheel: zoom, Wheel+Ctrl/Shift: Y/X zoom, Middle/Right+drag: pan")

    def on_source_type_change(self, event=None):
        self.source_type = self.source_var.get()
        if self.source_type == 'Voltage':
            self.value_combo['values'] = list(self.voltage_prefixes.keys())
            if self.value_unit not in self.voltage_prefixes:
                self.value_unit = 'mV'
                self.value_unit_var.set(self.value_unit)
        else:  # Current
            self.value_combo['values'] = list(self.current_prefixes.keys())
            if self.value_unit not in self.current_prefixes:
                self.value_unit = 'mA'
                self.value_unit_var.set(self.value_unit)
        self.update_plot()

    def on_unit_change(self, event=None):
        self.time_unit = self.time_unit_var.get()
        self.value_unit = self.value_unit_var.get()
        self.update_plot()

    def update_range(self):
        self.x_min = self.x_min_var.get()
        self.x_max = self.x_max_var.get()
        self.y_min = self.y_min_var.get()
        self.y_max = self.y_max_var.get()
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
        self.x_min_var.set(self.x_min - shift)
        self.x_max_var.set(self.x_max - shift)
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
        zoom_factor = 0.9 if event.button == 'up' else 1.1

        # マウス位置を中心にズーム
        x_center = event.xdata
        y_center = event.ydata

        if x_center is None or y_center is None:
            return

        # 修飾キーによる動作の分岐
        if hasattr(event, 'key') and event.key == 'control':
            # Ctrl+ホイール: 縦軸のみズーム
            y_range = (self.y_max - self.y_min) * zoom_factor / 2
            self.y_min_var.set(y_center - y_range)
            self.y_max_var.set(y_center + y_range)
        elif hasattr(event, 'key') and event.key == 'shift':
            # Shift+ホイール: 横軸のみズーム
            x_range = (self.x_max - self.x_min) * zoom_factor / 2
            self.x_min_var.set(x_center - x_range)
            self.x_max_var.set(x_center + x_range)
        else:
            # 通常のホイール: 両軸ズーム
            x_range = (self.x_max - self.x_min) * zoom_factor / 2
            y_range = (self.y_max - self.y_min) * zoom_factor / 2
            self.x_min_var.set(x_center - x_range)
            self.x_max_var.set(x_center + x_range)
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
        if self.source_type == 'Voltage':
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
        if self.source_type == 'Voltage':
            value_scale = self.voltage_prefixes[self.value_unit]
        else:
            value_scale = self.current_prefixes[self.value_unit]

        # 点を単位系に変換
        times = [p[0] / time_scale for p in self.pwl_points]
        values = [p[1] / value_scale for p in self.pwl_points]

        # PWL線の描画
        self.ax.plot(times, values, 'b-', linewidth=2, label='PWL')

        # 点の描画
        for i, (t, v) in enumerate(zip(times, values)):
            if i == self.selected_point:
                # 選択された点は赤色で大きく表示
                self.ax.plot(t, v, 'o', color='red', markersize=12, picker=True, markeredgecolor='darkred', markeredgewidth=2)
            else:
                self.ax.plot(t, v, 'o', color='blue', markersize=8, picker=True)
            self.ax.annotate(f'({t:.3f}, {v:.3f})',
                           (t, v), xytext=(5, 5), textcoords='offset points', fontsize=8)

        # グリッド
        self.ax.grid(True, alpha=0.3)

        # 軸ラベル
        unit_label = self.value_unit if self.source_type == 'Voltage' else self.value_unit
        self.ax.set_xlabel(f'Time ({self.time_unit})')
        self.ax.set_ylabel(f'{self.source_type} ({unit_label})')
        self.ax.set_title(f'PWL {self.source_type} Source')

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
                if self.source_type == 'Voltage':
                    value_scale = self.voltage_prefixes[self.value_unit]
                else:
                    value_scale = self.current_prefixes[self.value_unit]

                times = [p[0] / time_scale for p in self.pwl_points]
                values = [p[1] / value_scale for p in self.pwl_points]

                # 最も近い点を探す
                distances = [(abs(event.xdata - t) + abs(event.ydata - v)) for t, v in zip(times, values)]
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

                # 表示範囲を移動
                self.x_min_var.set(self.x_min + dx)
                self.x_max_var.set(self.x_max + dx)
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

    def add_point_at(self, x, y):
        time_scale = self.time_prefixes[self.time_unit]
        if self.source_type == 'Voltage':
            value_scale = self.voltage_prefixes[self.value_unit]
        else:
            value_scale = self.current_prefixes[self.value_unit]

        # 単位系を戻す
        real_time = x * time_scale
        real_value = y * value_scale

        # 時間順に挿入
        insert_index = 0
        for i, (t, v) in enumerate(self.pwl_points):
            if real_time > t:
                insert_index = i + 1
            else:
                break

        self.pwl_points.insert(insert_index, (real_time, real_value))
        self.update_plot()

    def add_point(self):
        # 最後の点の次の時間に追加
        if self.pwl_points:
            last_time = max(p[0] for p in self.pwl_points)
            time_scale = self.time_prefixes[self.time_unit]
            new_time = last_time + time_scale  # 1単位分後
        else:
            new_time = 0

        self.pwl_points.append((new_time, 0))
        self.pwl_points.sort(key=lambda x: x[0])  # 時間順にソート
        self.update_plot()

    def delete_point(self):
        if self.selected_point is not None and len(self.pwl_points) > 2:
            del self.pwl_points[self.selected_point]
            self.selected_point = None
            self.update_plot()
            self.update_info_label()
        elif self.selected_point is None:
            messagebox.showwarning("No Selection", "Please select a point first by clicking on it.")
        elif len(self.pwl_points) <= 2:
            messagebox.showwarning("Minimum Points", "At least 2 points are required for PWL.")

    def move_point(self, x, y):
        if self.selected_point is None:
            return

        time_scale = self.time_prefixes[self.time_unit]
        if self.source_type == 'Voltage':
            value_scale = self.voltage_prefixes[self.value_unit]
        else:
            value_scale = self.current_prefixes[self.value_unit]

        # 単位系を戻す
        real_time = x * time_scale
        real_value = y * value_scale

        self.pwl_points[self.selected_point] = (real_time, real_value)
        self.pwl_points.sort(key=lambda x: x[0])  # 時間順にソート

        # ソート後の新しいインデックスを見つける
        for i, (t, v) in enumerate(self.pwl_points):
            if abs(t - real_time) < 1e-12 and abs(v - real_value) < 1e-12:
                self.selected_point = i
                break

        self.update_plot()

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

        self.pwl_text.delete(1.0, tk.END)
        self.pwl_text.insert(tk.END, pwl_cmd)

    def generate_pwl(self):
        self.generate_pwl_text()
        # クリップボードにコピー
        self.root.clipboard_clear()
        self.root.clipboard_append(self.pwl_text.get(1.0, tk.END).strip())
        messagebox.showinfo("PWL Generated", "PWL command copied to clipboard!")

    def save_file(self):
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            data = {
                'pwl_points': self.pwl_points,
                'source_type': self.source_type,
                'time_unit': self.time_unit,
                'value_unit': self.value_unit,
                'x_range': [self.x_min, self.x_max],
                'y_range': [self.y_min, self.y_max]
            }
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            messagebox.showinfo("Saved", f"File saved: {filename}")

    def load_file(self):
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    data = json.load(f)

                self.pwl_points = data.get('pwl_points', [(0, 0), (1e-6, 0)])
                self.source_type = data.get('source_type', 'Voltage')
                self.time_unit = data.get('time_unit', 'μs')
                self.value_unit = data.get('value_unit', 'mV')

                x_range = data.get('x_range', [0, 10])
                y_range = data.get('y_range', [-5, 5])

                # UI更新
                self.source_var.set(self.source_type)
                self.time_unit_var.set(self.time_unit)
                self.value_unit_var.set(self.value_unit)

                self.x_min_var.set(x_range[0])
                self.x_max_var.set(x_range[1])
                self.y_min_var.set(y_range[0])
                self.y_max_var.set(y_range[1])

                self.on_source_type_change()
                self.update_range()

                messagebox.showinfo("Loaded", f"File loaded: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load file: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = PWLTool(root)
    root.mainloop()