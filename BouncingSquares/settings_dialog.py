"""设置表单：ttkbootstrap 现代主题；支持重力与逐方块配置。"""
from __future__ import annotations

import colorsys
import math
import tkinter as tk
from tkinter import messagebox

from ttkbootstrap import (
    Button,
    Checkbutton,
    Combobox,
    Entry,
    Frame,
    Label,
    LabelFrame,
    Style,
)

WHEEL_SIZE = 180
FONT_FAMILY = "Microsoft YaHei UI"
THEME = "flatly"

PALETTE = [
    "#e74c3c", "#e67e22", "#f1c40f", "#2ecc71", "#1abc9c", "#3498db",
    "#9b59b6", "#e91e63", "#8d6e63", "#607d8b", "#111111", "#ffffff",
]


def _apply_theme(master) -> Style:
    """应用 ttkbootstrap 现代主题，并让窗口背景与主题一致。"""
    _ensure_style_alive(master)
    try:
        style = Style(theme=THEME)
    except Exception:
        _reset_style_singleton()
        try:
            style = Style(theme=THEME)
        except Exception:
            # 主题初始化失败时退回默认 ttk 样式，不影响使用
            import tkinter.ttk as _ttk

            style = _ttk.Style(master)
    try:
        master.configure(bg=style.colors.bg)
    except Exception:
        pass
    try:
        master.option_add("*Font", (FONT_FAMILY, 10))
    except Exception:
        pass
    return style


def _ensure_style_alive(master) -> None:
    """确保 ttkbootstrap 主题单例属于当前窗口的解释器。

    单例是进程级的，绑定在第一次创建它的窗口（设置框）所在解释器上；
    设置框关闭后，运行中的弹窗必须重建单例，否则创建弹窗会崩溃。
    """
    inst = Style.get_instance()
    if inst is None:
        return
    try:
        inst_master = getattr(inst, "master", None)
        if inst_master is None:
            return
        if inst_master.tk is not master.tk:
            _reset_style_singleton()
    except Exception:
        _reset_style_singleton()


def _reset_style_singleton() -> None:
    """销毁 ttkbootstrap 主题单例，使其在下一个窗口的解释器里重建。"""
    try:
        Style.instance = None
    except Exception:
        pass


class SquareConfigPanel(LabelFrame):
    """逐方块配置：选择序号后设置该方块的大小/速度/方向/颜色。"""

    def __init__(self, master, count_getter, initial_configs=None,
                 on_apply=None, on_reset=None, defaults=None):
        super().__init__(master, text="逐方块配置（可单独设置每个方块）", padding=10)
        self._count_getter = count_getter
        self._on_apply = on_apply
        self._on_reset = on_reset
        self._defaults = defaults or {}
        self._configs: list[dict | None] = list(initial_configs or [])
        self._color = str(defaults.get("color", "#3498db"))

        row1 = Frame(self)
        row1.pack(fill="x")
        Label(row1, text="选择方块:").pack(side="left")
        self._combo = Combobox(row1, state="readonly", width=8)
        self._combo.pack(side="left", padx=(4, 10))
        self._combo.bind("<<ComboboxSelected>>", lambda _e: self._load_selected())

        Label(row1, text="大小:").pack(side="left")
        self._size_entry = Entry(row1, width=6)
        self._size_entry.pack(side="left", padx=(2, 8))
        Label(row1, text="速度:").pack(side="left")
        self._speed_entry = Entry(row1, width=6)
        self._speed_entry.pack(side="left", padx=(2, 8))
        Label(row1, text="方向°:").pack(side="left")
        self._angle_entry = Entry(row1, width=6)
        self._angle_entry.pack(side="left", padx=(2, 8))
        Label(row1, text="重量:").pack(side="left", padx=(6, 2))
        self._weight_entry = Entry(row1, width=6)
        self._weight_entry.pack(side="left", padx=(2, 8))

        row2 = Frame(self)
        row2.pack(fill="x", pady=(8, 0))
        Label(row2, text="颜色:").pack(side="left")
        self._swatches: list[tk.Canvas] = []
        for color in PALETTE:
            sw = tk.Canvas(
                row2, width=20, height=20, bg=color, highlightthickness=2,
                highlightbackground="#cccccc", cursor="hand2",
            )
            sw.pack(side="left", padx=2)
            sw.bind("<Button-1>", lambda _e, c=color: self._set_color(c))
            self._swatches.append(sw)

        row3 = Frame(self)
        row3.pack(fill="x", pady=(8, 0))
        Button(row3, text="应用到该方块", command=self._apply,
                   bootstyle="primary").pack(side="left")
        Button(row3, text="恢复全局设置", command=self._reset,
                   bootstyle="secondary").pack(side="left", padx=6)
        self._status_label = Label(row3, text="", foreground="#888888")
        self._status_label.pack(side="left", padx=(10, 0))

        self.refresh_count()

    def refresh_count(self) -> None:
        count = max(1, int(self._count_getter()))
        while len(self._configs) < count:
            self._configs.append(None)
        self._configs = self._configs[:count]
        self._combo.configure(values=[f"方块 {i + 1}" for i in range(count)])
        if self._combo.current() not in range(count):
            self._combo.current(0)
        self._load_selected()

    def _load_selected(self) -> None:
        idx = max(0, self._combo.current())
        cfg = self._configs[idx] if 0 <= idx < len(self._configs) else None
        d = self._defaults
        size = cfg["size"] if cfg and cfg.get("size") else d.get("size", 80)
        speed = cfg["speed"] if cfg and cfg.get("speed") else d.get("speed", 300.0)
        angle = cfg["angle"] if cfg and cfg.get("angle") is not None else d.get("angle", 45.0)
        weight = cfg["weight"] if cfg and cfg.get("weight") else d.get("weight", 1.0)
        self._color = cfg["color"] if cfg and cfg.get("color") else d.get("color", "#3498db")
        for entry, value in ((self._size_entry, int(size)),
                             (self._speed_entry, float(speed)),
                             (self._angle_entry, float(angle) % 360),
                             (self._weight_entry, float(weight))):
            entry.delete(0, tk.END)
            entry.insert(0, str(value))
        self._mark_selected_swatch()
        if cfg:
            self._status_label.config(
                text=f"方块 {idx + 1}：已单独配置", foreground="#1d4ed8"
            )
        else:
            self._status_label.config(
                text=f"方块 {idx + 1}：跟随全局设置", foreground="#888888"
            )

    def _mark_selected_swatch(self) -> None:
        for sw in self._swatches:
            sw.configure(highlightbackground="#cccccc", highlightthickness=2)
        for sw in self._swatches:
            if str(sw["bg"]).lower() == self._color.lower():
                sw.configure(highlightbackground="#1d4ed8", highlightthickness=3)

    def _set_color(self, color: str) -> None:
        self._color = color
        self._mark_selected_swatch()

    def _apply(self) -> None:
        idx = self._combo.current()
        try:
            size = int(self._size_entry.get())
            speed = float(self._speed_entry.get())
            angle = float(self._angle_entry.get())
            weight = float(self._weight_entry.get())
        except ValueError:
            messagebox.showerror("输入错误", "大小、速度、方向和重量必须是数字。", parent=self.winfo_toplevel())
            return
        if not 10 <= size <= 1000:
            messagebox.showerror("输入错误", "大小需要在 10 ~ 1000 像素之间。", parent=self.winfo_toplevel())
            return
        if not 10 <= speed <= 5000:
            messagebox.showerror("输入错误", "速度需要在 10 ~ 5000 像素/秒之间。", parent=self.winfo_toplevel())
            return
        if not 0.1 <= weight <= 10:
            messagebox.showerror("输入错误", "重量需要在 0.1 ~ 10 之间。", parent=self.winfo_toplevel())
            return
        cfg = {"size": size, "speed": speed, "angle": angle % 360,
               "color": self._color, "weight": weight}
        self._configs[idx] = cfg
        if self._on_apply:
            self._on_apply(idx, cfg)
        self._status_label.config(
            text=f"方块 {idx + 1}：已单独配置", foreground="#1d4ed8"
        )

    def _reset(self) -> None:
        idx = self._combo.current()
        self._configs[idx] = None
        if self._on_reset:
            self._on_reset(idx)
        self._load_selected()

    def get_configs(self) -> list[dict | None]:
        return list(self._configs)


class SettingsForm(Frame):
    """方向 / 大小 / 速度 / 数量 / 重力 / 颜色 设置表单。"""

    def __init__(self, master, defaults: dict | None = None):
        super().__init__(master, padding=12)
        defaults = defaults or {}

        self._angle = tk.DoubleVar(master=master, value=float(defaults.get("angle", 45.0)))
        self._random_dir = tk.BooleanVar(master=master, value=bool(defaults.get("random", False)))
        self._size = tk.IntVar(master=master, value=int(defaults.get("size", 80)))
        self._speed = tk.DoubleVar(master=master, value=float(defaults.get("speed", 300.0)))
        self._count = tk.IntVar(master=master, value=int(defaults.get("count", 1)))
        self._gravity = tk.BooleanVar(master=master, value=bool(defaults.get("gravity", False)))
        self._color = tk.StringVar(master=master, value=str(defaults.get("color", "#4c8bf5")))
        self._random_color = tk.BooleanVar(
            master=master, value=bool(defaults.get("random_color", False))
        )

        self._build()
        self._angle.trace_add("write", self._update_preview)
        self._random_dir.trace_add("write", self._update_preview)
        self._random_color.trace_add("write", self._update_swatch)
        self._count.trace_add("write", self._on_count_change)
        self._update_preview()
        self._update_swatch()

    def _build(self) -> None:
        pad = {"padx": 10, "pady": 5}
        body = self

        Label(body, text="方向（角度，0°=向右，90°=向下）").grid(
            row=0, column=0, sticky="w", **pad
        )
        Entry(body, textvariable=self._angle, width=10).grid(
            row=0, column=1, sticky="e", **pad
        )
        Checkbutton(
            body, text="随机方向（勾选后忽略上面的角度）", variable=self._random_dir
        ).grid(row=1, column=0, columnspan=2, sticky="w", **pad)

        Label(body, text="边长（像素）").grid(row=2, column=0, sticky="w", **pad)
        Entry(body, textvariable=self._size, width=10).grid(
            row=2, column=1, sticky="e", **pad
        )
        Label(body, text="速度（像素/秒）").grid(row=3, column=0, sticky="w", **pad)
        Entry(body, textvariable=self._speed, width=10).grid(
            row=3, column=1, sticky="e", **pad
        )
        Label(body, text="方块数量（1 ~ 20）").grid(row=4, column=0, sticky="w", **pad)
        Entry(body, textvariable=self._count, width=10).grid(
            row=4, column=1, sticky="e", **pad
        )
        Checkbutton(
            body, text="全局重力（勾选后受重力下落、落地反弹；不勾选则匀速直线运动）",
            variable=self._gravity,
        ).grid(row=5, column=0, columnspan=2, sticky="w", **pad)

        self._preview = tk.Canvas(
            body, width=180, height=140, bg="#ffffff",
            highlightthickness=1, highlightbackground="#cccccc",
        )
        self._preview.grid(row=6, column=0, columnspan=2, sticky="ew", **pad)

        color_frame = LabelFrame(body, text="方块颜色（按住跟随选色 / 点击选定）", padding=10)
        color_frame.grid(row=7, column=0, columnspan=2, sticky="ew", **pad)

        self._wheel = tk.Canvas(
            color_frame, width=WHEEL_SIZE, height=WHEEL_SIZE, highlightthickness=0,
            cursor="hand2",
        )
        self._wheel.pack(side="left", padx=(0, 14))
        self._build_wheel()
        self._wheel.bind("<Button-1>", self._on_wheel_press)
        self._wheel.bind("<B1-Motion>", self._on_wheel_motion)

        right = Frame(color_frame)
        right.pack(side="left", fill="y")
        self._swatch = tk.Canvas(
            right, width=64, height=64, highlightthickness=1, highlightbackground="#cccccc",
        )
        self._swatch.pack(anchor="w")
        self._swatch_label = Label(right, text="")
        self._swatch_label.pack(anchor="w", pady=(6, 0))
        Checkbutton(
            right, text="随机颜色（运动中自动变化）", variable=self._random_color
        ).pack(anchor="w", pady=(10, 0))
        Label(
            right, text="勾选后颜色在运动中\n自动变化，暂停时不变",
            foreground="#888888", font=(FONT_FAMILY, 9),
        ).pack(anchor="w")

        self._square_panel = SquareConfigPanel(
            body,
            count_getter=lambda: self._count.get(),
            initial_configs=None,
            defaults=self.defaults(),
        )
        self._square_panel.grid(row=8, column=0, columnspan=2, sticky="ew", **pad)
        self._on_count_change()

    def defaults(self) -> dict:
        return {
            "angle": self._angle.get(),
            "size": self._size.get(),
            "speed": self._speed.get(),
            "color": self._color.get(),
            "weight": 1.0,
        }

    def set_count_visible(self, visible: bool) -> None:
        """运行时弹窗中隐藏“数量”输入行（数量由追加/删除控制）。"""
        for widget in self.grid_slaves(row=4):
            if visible:
                widget.grid()
            else:
                widget.grid_remove()

    def _on_count_change(self, *_args) -> None:
        if self._count.get() >= 2:
            self._square_panel.grid()
            self._square_panel.refresh_count()
        else:
            self._square_panel.grid_remove()

    def _build_wheel(self) -> None:
        """用 HSV 色相环生成色盘图片，并记录每个像素对应的颜色。"""
        size = WHEEL_SIZE
        img = tk.PhotoImage(master=self, width=size, height=size)
        cx = cy = (size - 1) / 2.0
        radius = size / 2.0 - 3
        self._wheel_colors: list[list[str | None]] = []
        rows: list[str] = []
        bg_hex = "#f5f5f5"
        for y in range(size):
            row_colors: list[str | None] = []
            put_row: list[str] = []
            for x in range(size):
                dist = math.hypot(x - cx, y - cy)
                if dist <= radius:
                    hue = (math.atan2(y - cy, x - cx) / (2 * math.pi)) % 1.0
                    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                    ri, gi, bi = int(r * 255), int(g * 255), int(b * 255)
                    row_colors.append(f"#{ri:02x}{gi:02x}{bi:02x}")
                    put_row.append(row_colors[-1])
                else:
                    put_row.append(bg_hex)
                    row_colors.append(None)
            rows.append("{" + " ".join(put_row) + "}")
            self._wheel_colors.append(row_colors)
        img.put(" ".join(rows))
        self._wheel_img = img
        self._wheel.create_image(0, 0, image=img, anchor="nw")
        self._wheel.create_oval(1, 1, size - 1, size - 1, outline="#bbbbbb")

    def _pick_color_at(self, x: int, y: int) -> None:
        if self._random_color.get():
            return
        if 0 <= y < WHEEL_SIZE and 0 <= x < WHEEL_SIZE:
            color = self._wheel_colors[y][x]
            if color:
                self._color.set(color)
                self._update_swatch()

    def _on_wheel_press(self, event: tk.Event) -> None:
        self._pick_color_at(event.x, event.y)

    def _on_wheel_motion(self, event: tk.Event) -> None:
        self._pick_color_at(event.x, event.y)

    def _update_swatch(self, *_args) -> None:
        self._swatch.delete("all")
        if self._random_color.get():
            self._swatch.create_text(
                32, 32, text="随机", fill="#666666", font=(FONT_FAMILY, 10)
            )
            self._swatch_label.config(text="运动中自动变化")
            return
        color = self._color.get()
        self._swatch.create_rectangle(2, 2, 62, 62, fill=color, outline="")
        self._swatch_label.config(text=color.upper())

    def _update_preview(self, *_args) -> None:
        canvas = self._preview
        canvas.delete("all")
        cw, ch = int(canvas["width"]), int(canvas["height"])
        cx, cy = cw // 2, ch // 2

        canvas.create_line(cx - 45, cy, cx + 45, cy, fill="#d9d9d9")
        canvas.create_line(cx, cy - 45, cx, cy + 45, fill="#d9d9d9")
        canvas.create_text(
            cx + 44, cy - 10, text="0° →", fill="#999999",
            anchor="e", font=(FONT_FAMILY, 9),
        )

        if self._random_dir.get():
            canvas.create_text(
                cx, cy, text="方向将随机选择", fill="#888888", font=(FONT_FAMILY, 9)
            )
            return

        try:
            angle = math.radians(float(self._angle.get()) % 360)
        except ValueError:
            return

        length = 48
        ex = cx + length * math.cos(angle)
        ey = cy + length * math.sin(angle)
        canvas.create_oval(cx - 3, cy - 3, cx + 3, cy + 3, fill="#2f6fed", outline="")
        canvas.create_line(cx, cy, ex, ey, width=3, fill="#2f6fed", arrow=tk.LAST)

    def get_values(self) -> dict | None:
        try:
            size = int(self._size.get())
            speed = float(self._speed.get())
            angle = float(self._angle.get())
            count = int(self._count.get())
        except ValueError:
            messagebox.showerror("输入错误", "方向、边长、速度和数量必须是数字。", parent=self.winfo_toplevel())
            return None
        if not 10 <= size <= 1000:
            messagebox.showerror("输入错误", "边长需要在 10 ~ 1000 像素之间。", parent=self.winfo_toplevel())
            return None
        if not 10 <= speed <= 5000:
            messagebox.showerror("输入错误", "速度需要在 10 ~ 5000 像素/秒之间。", parent=self.winfo_toplevel())
            return None
        if not 0 <= angle < 360:
            messagebox.showerror("输入错误", "方向角度需要在 0 ~ 360 之间。", parent=self.winfo_toplevel())
            return None
        if not 1 <= count <= 20:
            messagebox.showerror("输入错误", "方块数量需要在 1 ~ 20 之间。", parent=self.winfo_toplevel())
            return None
        return {
            "angle": angle,
            "size": size,
            "speed": speed,
            "count": count,
            "gravity": bool(self._gravity.get()),
            "random": bool(self._random_dir.get()),
            "color": self._color.get(),
            "random_color": bool(self._random_color.get()),
            "squares": self._square_panel.get_configs(),
        }


class SettingsDialog(tk.Tk):
    """启动设置窗口（独立主窗口），取消时 result 为 None。"""

    def __init__(self, defaults: dict | None = None):
        super().__init__()
        self.title("初始设置")
        self.resizable(False, False)
        self.result: dict | None = None

        _apply_theme(self)
        self.form = SettingsForm(self, defaults)
        self.form.pack(fill="both", expand=True)

        footer = Frame(self, padding=12)
        footer.pack(fill="x")
        Button(footer, text="开始", command=self._on_ok, bootstyle="success").pack(
            side="left", padx=6
        )
        Button(footer, text="退出", command=self._on_cancel, bootstyle="secondary").pack(
            side="left", padx=6
        )

        self._center_on_screen()
        self.lift()
        self.update_idletasks()
        try:
            self.grab_set()
        except tk.TclError:
            pass
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Return>", lambda _e: self._on_ok())
        self.bind("<Escape>", lambda _e: self._on_cancel())

    def _center_on_screen(self) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_reqwidth()) // 2
        y = (self.winfo_screenheight() - self.winfo_reqheight()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _on_ok(self) -> None:
        values = self.form.get_values()
        if values is not None:
            self.result = values
            self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.destroy()

    def get_result(self) -> dict | None:
        return self.result


class AdjustPopup(tk.Toplevel):
    """右键弹出的调整窗口：修改参数、逐方块配置、追加/删除，或退出程序。"""

    def __init__(self, master, defaults: dict | None = None,
                 on_apply=None, on_quit=None, on_close_and_run=None,
                 on_add=None, on_delete=None, count_getter=None,
                 on_square_apply=None, on_square_reset=None,
                 space_paused="none", on_space_paused=None):
        super().__init__(master)
        self.title("调整设置")
        self.resizable(False, False)
        self._on_apply = on_apply
        self._on_quit = on_quit
        self._on_close_and_run = on_close_and_run
        self._on_space_paused = on_space_paused
        self._on_add = on_add
        self._on_delete = on_delete
        self._count_getter = count_getter

        _apply_theme(self)
        self.form = SettingsForm(self, defaults)
        self.form.pack(fill="both", expand=True)

        manage = LabelFrame(self, text="方块管理（暂停状态下）", padding=10)
        manage.pack(fill="x", padx=12)
        self._count_label = Label(manage, text="")
        self._count_label.pack(side="left", padx=(0, 10))
        Button(manage, text="追加 1 个", command=self._add).pack(side="left", padx=4)
        Label(manage, text="删除序号:").pack(side="left", padx=(12, 4))
        self._delete_entry = Entry(manage, width=5)
        self._delete_entry.pack(side="left")
        Button(manage, text="删除", command=self._delete).pack(side="left", padx=4)
        self._update_count()

        space_frame = Frame(self, padding=(12, 4))
        space_frame.pack(fill="x")
        Label(space_frame, text="暂停时按空格:").pack(side="left")
        self._space_combo = Combobox(
            space_frame, state="readonly", width=14,
            values=["无操作（用按钮继续）", "继续运行"],
        )
        self._space_combo.pack(side="left", padx=(4, 0))
        self._space_combo.current(0 if space_paused != "resume" else 1)
        self._space_combo.bind("<<ComboboxSelected>>", self._on_space_change)

        # 数量以运行时为准（由“追加/删除”控制），隐藏表单里的数量输入
        if self._count_getter:
            self.form._count.set(self._count_getter())
        self.form.set_count_visible(False)

        # 逐方块配置：复用表单内的面板，并把回调接到运行中的方块
        self.form._square_panel._on_apply = on_square_apply
        self.form._square_panel._on_reset = on_square_reset
        self.form._square_panel._defaults = defaults or {}
        self.form._square_panel._configs = list((defaults or {}).get("squares") or [])
        self.form._square_panel.grid()
        self.form._square_panel.refresh_count()

        footer = Frame(self, padding=12)
        footer.pack(fill="x")
        Button(footer, text="应用", command=self._apply, bootstyle="primary").pack(
            side="left", padx=6
        )
        Button(footer, text="关闭并运行", command=self._close_and_run,
               bootstyle="success").pack(side="left", padx=6)
        Button(footer, text="关闭", command=self.destroy,
               bootstyle="secondary").pack(side="left", padx=6)
        Button(footer, text="关闭程序", command=self._quit, bootstyle="danger").pack(
            side="left", padx=6
        )

        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Return>", lambda _e: self._apply())
        self.bind("<Escape>", lambda _e: self.destroy())
        self._center_on_screen()
        self.lift()
        try:
            self.grab_set()
        except tk.TclError:
            pass

    def _center_on_screen(self) -> None:
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_reqwidth()) // 2
        y = (self.winfo_screenheight() - self.winfo_reqheight()) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _apply(self) -> None:
        values = self.form.get_values()
        if values is not None and self._on_apply:
            values.pop("squares", None)  # 逐方块配置由面板按钮实时生效
            self._on_apply(values)  # 应用后保持窗口打开，便于继续调整

    def _close_and_run(self) -> None:
        """关闭调整窗口并自动恢复方块运动。"""
        if self._on_close_and_run:
            self._on_close_and_run()
        self.destroy()

    def _quit(self) -> None:
        if self._on_quit:
            self._on_quit()

    def _on_space_change(self, _event=None) -> None:
        if self._on_space_paused:
            self._on_space_paused(
                "resume" if self._space_combo.current() == 1 else "none"
            )

    def _update_count(self) -> None:
        if self._count_getter:
            self._count_label.config(text=f"当前方块数量: {self._count_getter()}")
            self.form._square_panel.refresh_count()

    def _add(self) -> None:
        if self._on_add:
            self._on_add()
        self._update_count()

    def _delete(self) -> None:
        try:
            n = int(self._delete_entry.get())
        except ValueError:
            return
        if self._on_delete and self._on_delete(n) is None:
            messagebox.showerror("删除失败", f"没有序号为 {n} 的方块。", parent=self)
        self._update_count()
