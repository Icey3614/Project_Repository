"""Borderless transparent analog clock with hour, minute and second hands.

Features:
- No window decorations and a transparent background, so only the circular
  dial is visible. The window can be dragged anywhere.
- Left-click the face: all three hands spin in random directions for about
  three seconds and land smoothly on the correct current time.
- Left-press and drag the face: move the window.
- Right-click the face: open settings (12/24-hour dial, Arabic/Roman
  numerals, dial and hand colors via the system color picker, dial size).
- A weekday sub-dial at the 9 o'clock side and a month/day window at the
  3 o'clock side, like a mechanical watch.
- Press Esc or use the settings window's Exit button to quit.

The program always starts with the default configuration; settings changed in
the settings window apply to the current session only.
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import datetime
import math
import os
import random
import sys
import tkinter as tk
import tkinter.font as tkfont
from tkinter import colorchooser, ttk
import winreg

REFRESH_MS = 50
SPIN_DURATION_MIN = 2.8
SPIN_DURATION_MAX = 3.2
DRAG_THRESHOLD = 4
TRANSPARENT_BG = "#010101"
FALLBACK_BG = "#1e1e2e"
MIN_SIZE = 360
MAX_SIZE = 640
DEFAULT_SIZE = 480

MONTHS = (
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
)

DEFAULT_SETTINGS = {
    "dial": 12,
    "numerals": "arabic",
    "face_color": "#f8f8f2",
    "hour_color": "#2b3a67",
    "minute_color": "#496a81",
    "second_color": "#e5484d",
    "border_enabled": False,
    "border_sides": 12,
    "border_color": "#2b3a67",
    "size": DEFAULT_SIZE,
}

MIN_BORDER_SIDES = 3
MAX_BORDER_SIDES = 8

AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "Clock"

MANUAL_TEXT = """使用说明

基本操作
- 单击表盘：三根指针随机旋转约 3 秒，平滑回到当前时间
- 按住表盘拖动：移动时钟位置
- 右键表盘：打开设置窗口
- 按 Esc 或点设置里的"退出程序"：退出

设置选项
- 表盘间隔：12 小时制 / 24 小时制
- 数字样式：阿拉伯数字 / 罗马数字（24 小时制固定为阿拉伯数字）
- 显示边框：外切正多边形边框（3-8 边），点击表盘时随指针一起旋转，
  停止时保证有一条边与屏幕底边平行
- 颜色：表盘、时针、分针、秒针、边框可分别用系统色盘设置；
  修改表盘颜色时，星期盘与边框会自动换成高对比颜色
- 表盘大小：360-640 px 滑块调节
- 开机自启动：注册到当前用户的启动项

表盘内容
- 左侧星期盘：7 个点（周一在顶部），红针指向今天
- 右侧日期窗口：显示当前月份与日期
"""


# ------------------------------------------------------------- environment

def _enable_dpi_awareness() -> None:
    """Ask Windows for DPI awareness so the clock stays crisp."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass


def _resource_dir() -> str:
    """Directory for writable files (settings.json) next to the program."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _bundle_dir() -> str:
    """Directory of bundled assets (read-only, inside the frozen archive)."""
    if getattr(sys, "frozen", False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def _icon_path() -> str:
    return os.path.join(_bundle_dir(), "clock.ico")


def _autostart_command() -> str:
    if getattr(sys, "frozen", False):
        return sys.executable
    exe = os.path.join(_resource_dir(), "Clock.exe")
    if os.path.exists(exe):
        return exe
    return os.path.abspath(__file__)


def _autostart_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0,
                             winreg.KEY_READ)
        try:
            value, _ = winreg.QueryValueEx(key, AUTOSTART_NAME)
            return value == _autostart_command()
        except FileNotFoundError:
            return False
        finally:
            winreg.CloseKey(key)
    except Exception:
        return False


def _set_autostart(enabled: bool) -> None:
    if sys.platform != "win32":
        return
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0,
                             winreg.KEY_SET_VALUE)
        try:
            if enabled:
                winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ,
                                  _autostart_command())
            else:
                try:
                    winreg.DeleteValue(key, AUTOSTART_NAME)
                except FileNotFoundError:
                    pass
        finally:
            winreg.CloseKey(key)
    except Exception:
        pass


def _enable_taskbar_button(root: tk.Tk) -> None:
    """Force a taskbar button for the borderless popup window."""
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        user32.GetWindowLongPtrW.restype = ctypes.c_longlong
        user32.GetWindowLongPtrW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
        user32.SetWindowLongPtrW.restype = ctypes.c_longlong
        user32.SetWindowLongPtrW.argtypes = [
            ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_longlong,
        ]

        # Collect every top-level window of this process: Tk can expose both
        # an inner and an outer window, and the shell only watches the one
        # that owns the taskbar button.
        handles: list[ctypes.wintypes.HWND] = []
        WNDENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
        )
        my_pid = ctypes.windll.kernel32.GetCurrentProcessId()

        @WNDENUMPROC
        def _collect(hwnd, _lparam):
            pid = ctypes.wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            if pid.value == my_pid:
                handles.append(ctypes.wintypes.HWND(hwnd))
            return True

        user32.EnumWindows(_collect, 0)
        if not handles:
            handles.append(ctypes.wintypes.HWND(root.winfo_id()))

        for hwnd in handles:
            ex_style = user32.GetWindowLongPtrW(hwnd, -20)  # GWL_EXSTYLE
            user32.SetWindowLongPtrW(hwnd, -20, ex_style | 0x00040000)  # WS_EX_APPWINDOW

        # Show the clock icon in the taskbar button / alt-tab.
        user32.LoadImageW.restype = ctypes.c_void_p
        user32.LoadImageW.argtypes = [
            ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_uint,
            ctypes.c_int, ctypes.c_int, ctypes.c_uint,
        ]
        user32.SendMessageW.argtypes = [
            ctypes.wintypes.HWND, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p,
        ]
        user32.SendMessageW.restype = ctypes.c_void_p
        icon = user32.LoadImageW(
            None, _icon_path(), 1, 32, 32, 0x00000010  # IMAGE_ICON, LR_LOADFROMFILE
        )
        if icon:
            for hwnd in handles:
                user32.SendMessageW(hwnd, 0x0080, 1, icon)  # WM_SETICON ICON_BIG
                user32.SendMessageW(hwnd, 0x0080, 0, icon)  # WM_SETICON ICON_SMALL
    except Exception:
        pass


# ---------------------------------------------------------------- settings

def _valid_hex(value: object) -> bool:
    return (
        isinstance(value, str) and len(value) == 7 and value[0] == "#"
        and all(c in "0123456789abcdefABCDEF" for c in value[1:])
    )


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))  # type: ignore[return-value]


def _luminance(color: str) -> float:
    r, g, b = _hex_to_rgb(color)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _contrast(color: str) -> str:
    """Ink color that reads well on the given background."""
    return "#f5f5f0" if _luminance(color) < 0.5 else "#3a3a55"


def _shade(color: str, factor: float) -> str:
    """Darken (factor<0) or lighten (factor>0) a hex color."""
    r, g, b = _hex_to_rgb(color)
    if factor < 0:
        k = 1 + factor
        r, g, b = r * k, g * k, b * k
    else:
        r, g, b = r + (255 - r) * factor, g + (255 - g) * factor, b + (255 - b) * factor
    return f"#{int(r):02x}{int(g):02x}{int(b):02x}"


def normalize_settings(settings: dict) -> dict:
    settings["dial"] = 24 if settings.get("dial") == 24 else 12
    if settings["dial"] == 24:
        settings["numerals"] = "arabic"
    elif settings.get("numerals") != "roman":
        settings["numerals"] = "arabic"
    for key in ("face_color", "hour_color", "minute_color", "second_color"):
        if not _valid_hex(settings.get(key)):
            settings[key] = DEFAULT_SETTINGS[key]
    if not _valid_hex(settings.get("border_color")):
        settings["border_color"] = DEFAULT_SETTINGS["border_color"]
    settings["border_enabled"] = bool(settings.get("border_enabled"))
    try:
        settings["border_sides"] = max(
            MIN_BORDER_SIDES,
            min(MAX_BORDER_SIDES, int(settings.get("border_sides", 12))),
        )
    except (TypeError, ValueError):
        settings["border_sides"] = DEFAULT_SETTINGS["border_sides"]
    try:
        settings["size"] = max(MIN_SIZE, min(MAX_SIZE, int(settings.get("size", DEFAULT_SIZE))))
    except (TypeError, ValueError):
        settings["size"] = DEFAULT_SIZE
    return settings


def load_settings() -> dict:
    """Always start from the default configuration."""
    return normalize_settings(dict(DEFAULT_SETTINGS))


def save_settings(settings: dict) -> None:
    """Config persistence is intentionally disabled."""
    pass


# ------------------------------------------------------------------- clock

def angles_for(now: datetime.datetime, dial: int) -> dict[str, float]:
    """Clockwise degrees from 12 o'clock for each hand at the given time."""
    seconds = now.second + now.microsecond / 1_000_000
    minutes = now.minute + seconds / 60
    hours = now.hour + minutes / 60
    if dial == 24:
        return {
            "hour": (hours % 24) * 15.0,
            "minute": minutes * 6.0,
            "second": seconds * 6.0,
        }
    return {
        "hour": (hours % 12) * 30.0,
        "minute": minutes * 6.0,
        "second": seconds * 6.0,
    }


def spin_plan(start: dict[str, float], end: dict[str, float],
              rng: random.Random) -> dict[str, dict]:
    """Random spin per hand; every hand lands exactly on its end angle."""
    plan = {}
    for hand, min_turns, max_turns in (
        ("hour", 0, 2),
        ("minute", 1, 4),
        ("second", 2, 5),
    ):
        direction = rng.choice((-1, 1))
        turns = rng.randint(min_turns, max_turns)
        if direction > 0:
            delta = (end[hand] - start[hand]) % 360
            distance = delta + turns * 360.0
        else:
            delta = (start[hand] - end[hand]) % 360
            distance = -(delta + turns * 360.0)
        plan[hand] = {"start": start[hand], "distance": distance}
    return plan


def ease_in_out(t: float) -> float:
    """Smooth ease-in-out (cubic) so the spin starts and ends gently."""
    if t < 0.5:
        return 4 * t * t * t
    u = -2 * t + 2
    return 1 - u * u * u / 2


class AnalogClock(tk.Canvas):
    """A borderless, draggable analog clock canvas."""

    def __init__(self, master: tk.Misc, **kwargs: object) -> None:
        kwargs.setdefault("bg", FALLBACK_BG)
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(master, **kwargs)
        self._settings = load_settings()
        # Border color auto-contrasts with the dial face (like the weekday
        # sub-dial); a manually chosen color is kept until the face changes.
        self._settings["border_color"] = _contrast(self._settings["face_color"])
        self._spin: dict | None = None
        self._press: dict | None = None
        self._settings_win: tk.Toplevel | None = None
        self._last_bg: str | None = None
        self._transparent = False
        self._poly_angle = 0.0
        self._angles = angles_for(datetime.datetime.now(), self._settings["dial"])

        self.bind("<Configure>", lambda _event: self._draw())
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Button-3>", lambda _event: self._open_settings())
        self.after(REFRESH_MS, self._update)

    # ------------------------------------------------------------------ time

    def _update(self) -> None:
        now = datetime.datetime.now()
        if self._spin is not None:
            elapsed = (now - self._spin["start"]).total_seconds()
            t = min(elapsed / self._spin["duration"], 1.0)
            eased = ease_in_out(t)
            angles = {
                hand: cfg["start"] + cfg["distance"] * eased
                for hand, cfg in self._spin["plan"].items()
            }
            if t >= 1.0:
                self._spin = None
        else:
            angles = angles_for(now, self._settings["dial"])
        self._poly_angle = 0.0
        if self._spin is not None and "poly" in self._spin:
            eased = ease_in_out(min((now - self._spin["start"]).total_seconds()
                                    / self._spin["duration"], 1.0))
            self._poly_angle = self._spin["poly"]["distance"] * eased
        self._angles = angles
        self._draw()
        self.after(REFRESH_MS, self._update)

    def _start_spin(self) -> None:
        now = datetime.datetime.now()
        duration = random.uniform(SPIN_DURATION_MIN, SPIN_DURATION_MAX)
        end = now + datetime.timedelta(seconds=duration)
        self._spin = {
            "start": now,
            "end": end,
            "duration": duration,
            "plan": spin_plan(
                angles_for(now, self._settings["dial"]),
                angles_for(end, self._settings["dial"]),
                random,
            ),
        }
        if self._settings["border_enabled"]:
            self._spin["poly"] = {
                "start": 0.0,
                "distance": random.choice((-1, 1)) * random.randint(1, 3) * 360.0,
            }

    # ------------------------------------------------------------- dragging

    def _within_face(self, x: int, y: int) -> bool:
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)
        cx, cy = width / 2, height / 2
        radius = min(width, height) / 2 - 4
        if radius <= 8:
            return False
        return (x - cx) ** 2 + (y - cy) ** 2 <= (radius * 0.99) ** 2

    def _on_press(self, event: tk.Event) -> None:
        if not self._within_face(event.x, event.y):
            return
        self._press = {
            "x": event.x_root,
            "y": event.y_root,
            "win_x": self.master.winfo_x(),
            "win_y": self.master.winfo_y(),
            "dragged": False,
        }

    def _on_drag(self, event: tk.Event) -> None:
        if self._press is None:
            return
        dx = event.x_root - self._press["x"]
        dy = event.y_root - self._press["y"]
        if abs(dx) > DRAG_THRESHOLD or abs(dy) > DRAG_THRESHOLD:
            self._press["dragged"] = True
        if self._press["dragged"]:
            x = self._press["win_x"] + dx
            y = self._press["win_y"] + dy
            self.master.geometry(f"+{int(x)}+{int(y)}")

    def _on_release(self, event: tk.Event) -> None:
        if self._press is None:
            return
        was_drag = self._press["dragged"]
        self._press = None
        if not was_drag and self._spin is None:
            self._start_spin()

    # ------------------------------------------------------------ settings

    def _open_settings(self) -> None:
        if self._settings_win is not None and self._settings_win.winfo_exists():
            self._settings_win.lift()
            self._settings_win.focus_force()
            return

        win = tk.Toplevel(self.master)
        win.title("时钟设置")
        win.resizable(False, False)
        win.transient(self.master)
        win.geometry(
            f"+{self.master.winfo_x() + 80}+{self.master.winfo_y() + 80}"
        )
        win.protocol(
            "WM_DELETE_WINDOW",
            lambda: (win.destroy(), setattr(self, "_settings_win", None)),
        )
        self._settings_win = win

        dial_var = tk.StringVar(value=str(self._settings["dial"]))
        numeral_var = tk.StringVar(value=self._settings["numerals"])
        size_var = tk.IntVar(value=self._settings["size"])
        ui = {"dial_var": dial_var, "numeral_var": numeral_var,
              "size_var": size_var, "swatches": {}, "size_label": None,
              "sides_btn": None}

        def apply_dial_numeral() -> None:
            self._apply_settings(int(dial_var.get()), numeral_var.get())
            self._sync_settings_ui(ui, self._settings)

        def pick_color(key: str, button: tk.Button) -> None:
            _, hex_color = colorchooser.askcolor(
                color=self._settings[key], parent=win, title="选择颜色"
            )
            if hex_color:
                if key == "face_color":
                    # Weekday sub-dial and border auto-contrast with the face.
                    self._settings["face_color"] = hex_color
                    self._settings["border_color"] = _contrast(hex_color)
                else:
                    self._settings[key] = hex_color
                button.configure(bg=hex_color, activebackground=hex_color)
                save_settings(self._settings)
                self._draw()
                self._sync_settings_ui(ui, self._settings)

        def apply_size(_value: str) -> None:
            self._apply_size(size_var.get())
            if ui["size_label"] is not None:
                ui["size_label"].configure(text=f"{size_var.get()} px")

        def show_manual() -> None:
            doc = tk.Toplevel(win)
            doc.title("使用说明")
            doc.resizable(True, True)
            doc.transient(win)
            doc.geometry("520x440")
            text = tk.Text(doc, width=56, height=20, wrap="word",
                           font=("Microsoft YaHei UI", 10))
            text.pack(fill="both", expand=True, padx=10, pady=(10, 4))
            text.insert("1.0", MANUAL_TEXT)
            text.configure(state="disabled")
            ttk.Button(doc, text="关闭", command=doc.destroy) \
                .pack(pady=(0, 10))

        autostart_var = tk.BooleanVar(value=_autostart_enabled())
        ui["autostart_var"] = autostart_var

        def toggle_autostart() -> None:
            _set_autostart(autostart_var.get())

        frame = ttk.Frame(win, padding=14)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="表盘间隔", font=("Microsoft YaHei UI", 10)) \
            .grid(row=0, column=0, sticky="w", pady=(0, 6))
        ttk.Radiobutton(frame, text="12 小时制", value="12", variable=dial_var,
                        command=apply_dial_numeral).grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(frame, text="24 小时制", value="24", variable=dial_var,
                        command=apply_dial_numeral).grid(row=1, column=1, sticky="w")

        ttk.Label(frame, text="数字样式", font=("Microsoft YaHei UI", 10)) \
            .grid(row=2, column=0, sticky="w", pady=(10, 6))
        ttk.Radiobutton(frame, text="阿拉伯数字", value="arabic",
                        variable=numeral_var, command=apply_dial_numeral) \
            .grid(row=2, column=1, sticky="w")
        ui["roman_btn"] = ttk.Radiobutton(frame, text="罗马数字", value="roman",
                                          variable=numeral_var,
                                          command=apply_dial_numeral)
        ui["roman_btn"].grid(row=3, column=1, sticky="w")

        # Border: circumscribed regular polygon.
        border_var = tk.BooleanVar(value=bool(self._settings["border_enabled"]))
        ui["border_var"] = border_var

        def ask_sides() -> int | None:
            dialog = tk.Toplevel(win)
            dialog.title("选择正多边形边数")
            dialog.resizable(False, False)
            dialog.transient(win)
            dialog.grab_set()
            result: dict = {"value": None}
            shape_names = {
                3: "三角形", 4: "四边形", 5: "五边形",
                6: "六边形", 7: "七边形", 8: "八边形",
            }
            var = tk.IntVar(value=self._settings["border_sides"])
            ttk.Label(dialog, text="请选择边数：",
                      font=("Microsoft YaHei UI", 10)) \
                .pack(padx=16, pady=(12, 6), anchor="w")
            for sides in range(MIN_BORDER_SIDES, MAX_BORDER_SIDES + 1):
                ttk.Radiobutton(
                    dialog,
                    text="%d 边形（%s）" % (sides, shape_names[sides]),
                    value=sides, variable=var,
                ).pack(padx=28, pady=1, anchor="w")
            buttons = ttk.Frame(dialog, padding=(16, 10))
            buttons.pack(fill="x")

            def confirm() -> None:
                result["value"] = var.get()
                dialog.destroy()

            def cancel() -> None:
                dialog.destroy()

            ttk.Button(buttons, text="确定", command=confirm).pack(side="right")
            ttk.Button(buttons, text="取消", command=cancel) \
                .pack(side="right", padx=(0, 6))
            dialog.wait_window()
            return result["value"]

        def toggle_border() -> None:
            if border_var.get():
                sides = ask_sides()
                if sides is None:
                    border_var.set(False)
                    return
                self._settings["border_sides"] = sides
                self._settings["border_enabled"] = True
            else:
                self._settings["border_enabled"] = False
            save_settings(self._settings)
            self._spin = None
            self._sync_settings_ui(ui, self._settings)

        def set_border_sides() -> None:
            sides = ask_sides()
            if sides is not None:
                self._settings["border_sides"] = sides
                save_settings(self._settings)
                self._sync_settings_ui(ui, self._settings)

        ttk.Label(frame, text="显示边框", font=("Microsoft YaHei UI", 10)) \
            .grid(row=4, column=0, sticky="w", pady=(10, 6))
        ttk.Checkbutton(frame, text="", variable=border_var,
                        command=toggle_border) \
            .grid(row=4, column=1, sticky="w", pady=(10, 6))
        ui["sides_btn"] = ttk.Button(frame, text="修改边数…", width=16,
                                     command=set_border_sides)
        ui["sides_btn"].grid(row=5, column=1, sticky="w", pady=(0, 4))
        ttk.Label(frame, text="边框颜色", font=("Microsoft YaHei UI", 10)) \
            .grid(row=6, column=0, sticky="w", pady=(4, 0))
        border_btn = tk.Button(
            frame, text="边框", width=7, relief="flat",
            bg=self._settings["border_color"],
            activebackground=self._settings["border_color"],
        )
        border_btn.configure(
            command=lambda k="border_color", b=border_btn: pick_color(k, b)
        )
        border_btn.grid(row=6, column=1, sticky="w", pady=1)
        ui["swatches"]["border_color"] = border_btn

        ttk.Label(frame, text="颜色", font=("Microsoft YaHei UI", 10)) \
            .grid(row=7, column=0, sticky="nw", pady=(12, 0))
        color_names = (
            ("face_color", "表盘"),
            ("hour_color", "时针"),
            ("minute_color", "分针"),
            ("second_color", "秒针"),
        )
        for offset, (key, label) in enumerate(color_names):
            row = 7 + offset
            btn = tk.Button(
                frame, text=label, width=7, relief="flat",
                bg=self._settings[key], activebackground=self._settings[key],
            )
            btn.configure(command=lambda k=key, b=btn: pick_color(k, b))
            btn.grid(row=row, column=1, sticky="w", pady=1)
            ui["swatches"][key] = btn

        size_row = 7 + len(color_names)
        ttk.Label(frame, text="表盘大小", font=("Microsoft YaHei UI", 10)) \
            .grid(row=size_row, column=0, sticky="w", pady=(12, 0))
        scale = tk.Scale(frame, from_=MIN_SIZE, to=MAX_SIZE, orient="horizontal",
                         variable=size_var, command=apply_size, length=170)
        scale.grid(row=size_row, column=1, sticky="w", pady=(12, 0))
        ui["size_label"] = ttk.Label(frame, text=f"{size_var.get()} px")
        ui["size_label"].grid(row=size_row + 1, column=1, sticky="w")

        ttk.Label(frame, text="开机自启动", font=("Microsoft YaHei UI", 10)) \
            .grid(row=size_row + 2, column=0, sticky="w", pady=(10, 4))
        ttk.Checkbutton(frame, variable=autostart_var,
                        command=toggle_autostart) \
            .grid(row=size_row + 2, column=1, sticky="w", pady=(10, 4))
        ttk.Button(frame, text="使用说明", command=show_manual) \
            .grid(row=size_row + 3, column=0, columnspan=2, sticky="we",
                  pady=(4, 0))
        ttk.Button(frame, text="退出程序", command=self.master.destroy) \
            .grid(row=size_row + 4, column=0, columnspan=2, sticky="we",
                  pady=(14, 0))

        self._sync_settings_ui(ui, self._settings)

    @staticmethod
    def _sync_settings_ui(ui: dict, settings: dict) -> None:
        if ui["dial_var"].get() == "24":
            ui["numeral_var"].set("arabic")
            ui["roman_btn"].state(["disabled"])
        else:
            ui["roman_btn"].state(["!disabled"])
        for key, btn in ui["swatches"].items():
            btn.configure(bg=settings[key], activebackground=settings[key])
        if ui.get("sides_btn") is not None:
            ui["sides_btn"].configure(
                text="修改边数（当前 %d 边）…" % settings["border_sides"]
            )
            border_state = "normal" if settings["border_enabled"] else "disabled"
            ui["swatches"]["border_color"].configure(state=border_state)

    def _apply_settings(self, dial: int, numerals: str) -> None:
        self._settings["dial"] = dial
        self._settings["numerals"] = numerals
        normalize_settings(self._settings)
        save_settings(self._settings)
        self._spin = None

    def _apply_size(self, size: int) -> None:
        size = max(MIN_SIZE, min(MAX_SIZE, int(size)))
        self._settings["size"] = size
        save_settings(self._settings)
        root = self.master
        center_x = root.winfo_x() + root.winfo_width() / 2
        center_y = root.winfo_y() + root.winfo_height() / 2
        root.geometry(f"{size}x{size}+{int(center_x - size / 2)}+{int(center_y - size / 2)}")

    # ---------------------------------------------------------------- draw

    def _draw(self) -> None:
        self.delete("all")
        width = max(self.winfo_width(), 1)
        height = max(self.winfo_height(), 1)
        cx, cy = width / 2, height / 2
        outer_radius = min(width, height) / 2 - 4
        if self._settings["border_enabled"]:
            sides = self._settings["border_sides"]
            radius = outer_radius * math.cos(math.pi / sides)
            self._draw_border(cx, cy, outer_radius)
        else:
            radius = outer_radius
        if radius <= 8:
            return

        self._draw_face(cx, cy, radius)
        self._draw_weekday_subdial(cx, cy, radius)
        self._draw_date_window(cx, cy, radius)
        self._draw_hands(cx, cy, radius)

    def _draw_border(self, cx: float, cy: float, outer_radius: float) -> None:
        """Circumscribed regular polygon around the dial.

        At rest (poly_angle == 0) one side is parallel to the bottom edge of
        the screen; the polygon rotates with the spin animation and always
        lands back on that orientation.
        """
        sides = max(MIN_BORDER_SIDES,
                    min(MAX_BORDER_SIDES, self._settings["border_sides"]))
        color = self._settings["border_color"]
        # Side 0's midpoint points straight down (180° in 12-o'clock terms).
        base = 180.0 - 180.0 / sides
        points: list[float] = []
        for k in range(sides):
            angle = math.radians(base + k * 360.0 / sides + self._poly_angle - 90)
            points.extend([
                cx + outer_radius * math.cos(angle),
                cy + outer_radius * math.sin(angle),
            ])
        self.create_polygon(*points, fill=color, outline=color, width=1)

    def _draw_face(self, cx: float, cy: float, radius: float) -> None:
        dial = self._settings["dial"]
        numerals = self._settings["numerals"]
        major_step = 30 if dial == 12 else 15
        major_count = 12 if dial == 12 else 24
        face = self._settings["face_color"]
        ink = _contrast(face)
        minor_tick = _shade(face, 0.10 if _luminance(face) < 0.5 else -0.10)
        rim = _shade(face, -0.25 if _luminance(face) >= 0.5 else 0.25)
        if not self._transparent and rim != self._last_bg:
            self._last_bg = rim
            self.configure(bg=rim)

        self.create_oval(
            cx - radius, cy - radius,
            cx + radius, cy + radius,
            fill=face,
            outline=rim,
            width=max(2, radius * 0.025),
        )

        # 60 minute ticks.
        for tick in range(60):
            angle = math.radians(tick * 6 - 90)
            outer = radius * 0.94
            inner = radius * 0.90
            self.create_line(
                cx + inner * math.cos(angle),
                cy + inner * math.sin(angle),
                cx + outer * math.cos(angle),
                cy + outer * math.sin(angle),
                fill=minor_tick,
                width=max(1, radius * 0.010),
            )

        # Major marks at every hour interval.
        for k in range(major_count):
            angle = math.radians(k * major_step - 90)
            outer = radius * 0.94
            inner = radius * 0.84
            self.create_line(
                cx + inner * math.cos(angle),
                cy + inner * math.sin(angle),
                cx + outer * math.cos(angle),
                cy + outer * math.sin(angle),
                fill=ink,
                width=max(2, radius * 0.022),
            )

        # Numerals.
        if dial == 12:
            labels = (
                ("I", "II", "III", "IV", "V", "VI", "VII",
                 "VIII", "IX", "X", "XI", "XII")
                if numerals == "roman"
                else tuple(str(i) for i in range(1, 13))
            )
            pos_radius = radius * 0.72
            font_size = (
                max(8, int(radius * 0.11)) if numerals == "roman"
                else max(9, int(radius * 0.13))
            )
            for index, label in enumerate(labels, start=1):
                angle = math.radians(index * 30 - 90)
                self.create_text(
                    cx + pos_radius * math.cos(angle),
                    cy + pos_radius * math.sin(angle),
                    text=label,
                    fill=ink,
                    font=("Segoe UI", font_size, "bold"),
                )
        else:
            labels = [str(k) if k else "24" for k in range(24)]
            pos_radius = radius * 0.76
            font_size = max(7, int(radius * 0.085))
            for k, label in enumerate(labels):
                angle = math.radians(k * 15 - 90)
                self.create_text(
                    cx + pos_radius * math.cos(angle),
                    cy + pos_radius * math.sin(angle),
                    text=label,
                    fill=ink,
                    font=("Segoe UI", font_size, "bold"),
                )

    def _draw_weekday_subdial(self, cx: float, cy: float, radius: float) -> None:
        """Small weekday dial: seven dots (Monday at the top) plus a pointer
        to today's weekday, placed in the sector between 10 and 11 o'clock."""
        now = datetime.datetime.now()
        today = now.weekday()  # 0 = Monday
        face = self._settings["face_color"]
        # The sub-dial automatically takes a high-contrast color relative to
        # the dial face, and its marks use the opposite of that.
        sub_fill = _contrast(face)
        ink = _contrast(sub_fill)
        pointer_color = self._settings["second_color"]

        sub_angle = math.radians(315 - 90)
        sub_cx = cx + 0.34 * radius * math.cos(sub_angle)
        sub_cy = cy + 0.34 * radius * math.sin(sub_angle)
        sr = 0.19 * radius
        seg = 360.0 / 7

        self.create_oval(
            sub_cx - sr, sub_cy - sr, sub_cx + sr, sub_cy + sr,
            fill=sub_fill, outline=ink,
            width=max(1, radius * 0.012),
        )

        # Seven evenly spaced dots, Monday at the top.
        dot_radius = 0.62 * sr
        dot_r = max(1.8, sr * 0.075)
        for k in range(7):
            a = math.radians(k * seg - 90)
            dx = sub_cx + dot_radius * math.cos(a)
            dy = sub_cy + dot_radius * math.sin(a)
            self.create_oval(
                dx - dot_r, dy - dot_r, dx + dot_r, dy + dot_r,
                fill=ink, outline="",
            )

        # pointer to today's weekday
        ap = math.radians(today * seg - 90)
        ptr_len = 0.40 * sr
        tail = 0.14 * sr
        self.create_line(
            sub_cx - tail * math.cos(ap),
            sub_cy - tail * math.sin(ap),
            sub_cx + ptr_len * math.cos(ap),
            sub_cy + ptr_len * math.sin(ap),
            fill=pointer_color, width=max(1.2, sr * 0.07),
            capstyle="round",
        )
        dot = max(1.4, sr * 0.075)
        self.create_oval(sub_cx - dot, sub_cy - dot, sub_cx + dot, sub_cy + dot,
                         fill=pointer_color, outline="")

    def _draw_date_window(self, cx: float, cy: float, radius: float) -> None:
        """Month/day window at the 3 o'clock side, like a mechanical watch."""
        now = datetime.datetime.now()
        text = f"{MONTHS[now.month - 1]} {now.day}"
        face = self._settings["face_color"]
        ink = _contrast(face)

        wcx = cx + 0.44 * radius
        wcy = cy
        ww = 0.36 * radius
        wh = 0.15 * radius
        outline_w = max(1, radius * 0.014)

        self.create_rectangle(
            wcx - ww / 2, wcy - wh / 2, wcx + ww / 2, wcy + wh / 2,
            fill="#ffffff", outline=ink, width=outline_w,
        )
        pad = radius * 0.022
        self.create_rectangle(
            wcx - ww / 2 + pad, wcy - wh / 2 + pad,
            wcx + ww / 2 - pad, wcy + wh / 2 - pad,
            outline=_shade(ink, 0.25), width=1,
        )
        font = tkfont.Font(family="Segoe UI",
                           size=max(5, int(radius * 0.05)), weight="bold")
        while font.measure(text) > ww * 0.88 and font.cget("size") > 5:
            font.configure(size=font.cget("size") - 1)
        self.create_text(
            wcx, wcy, text=text,
            fill="#33334d",
            font=font,
        )

    def _draw_hands(self, cx: float, cy: float, radius: float) -> None:
        hour_angle = self._angles["hour"]
        minute_angle = self._angles["minute"]
        second_angle = self._angles["second"]
        face = self._settings["face_color"]
        ink = _contrast(face)

        self._draw_hand(cx, cy, radius * 0.42, hour_angle,
                        self._settings["hour_color"], max(4, radius * 0.045))
        self._draw_hand(cx, cy, radius * 0.62, minute_angle,
                        self._settings["minute_color"], max(3, radius * 0.030))
        self._draw_hand(cx, cy, radius * 0.76, second_angle,
                        self._settings["second_color"], max(1.5, radius * 0.012),
                        tail=radius * 0.14)

        cap = max(4, radius * 0.055)
        self.create_oval(cx - cap, cy - cap, cx + cap, cy + cap,
                         fill=ink, outline="")

    def _draw_hand(self, cx: float, cy: float, length: float, angle_deg: float,
                   color: str, width: float, tail: float = 0.0) -> None:
        angle = math.radians(angle_deg - 90)
        tip = (cx + length * math.cos(angle), cy + length * math.sin(angle))
        base = (cx - tail * math.cos(angle), cy - tail * math.sin(angle))
        self.create_line(
            base[0], base[1], tip[0], tip[1],
            fill=color, width=width, capstyle="round",
        )


def main() -> None:
    _enable_dpi_awareness()
    root = tk.Tk()
    root.overrideredirect(True)
    root.resizable(False, False)

    clock = AnalogClock(root)
    clock.pack(fill="both", expand=True)

    size = clock._settings["size"]
    root.geometry(f"{size}x{size}")
    root.update_idletasks()

    if sys.platform == "win32":
        # Physical screen size for the DPI-aware process; Tk's own reported
        # size can be doubled on scaled displays and would push the window
        # off screen.
        screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    else:
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
    x = max(0, (screen_w - size) // 2)
    y = max(0, (screen_h - size) // 2)
    root.geometry(f"{size}x{size}+{x}+{y}")

    try:
        root.wm_attributes("-transparentcolor", TRANSPARENT_BG)
        clock._transparent = True
        clock.configure(bg=TRANSPARENT_BG)
    except tk.TclError:
        clock._transparent = False
        clock.configure(bg=FALLBACK_BG)

    try:
        root.iconbitmap(_icon_path())
    except Exception:
        pass
    _enable_taskbar_button(root)

    root.bind("<Escape>", lambda _event: root.destroy())
    root.after(50, root.focus_force)
    root.mainloop()


if __name__ == "__main__":
    main()
