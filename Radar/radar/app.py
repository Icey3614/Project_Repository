"""Tkinter front end for the simulation radar."""

from __future__ import annotations

import ctypes
import datetime
import math
import tempfile
import tkinter as tk
import traceback
from ctypes import wintypes
from pathlib import Path
from time import perf_counter

from .core import RadarModel, clockwise_angle

user32 = ctypes.windll.user32

# Palette (RGB tuples)
BG = (0x02, 0x0D, 0x07)
RING = (0x0C, 0x4D, 0x28)
TICK = (0x0C, 0x4D, 0x28)
SWEEP_MAX = (0x1F, 0xBF, 0x66)
HEAD = (0x8D, 0xFF, 0xC0)
BLIP_RED = (0xFF, 0x32, 0x32)
HUD = (0x1F, 0x7A, 0x45)


def _hex(color: tuple[int, int, int]) -> str:
    return "#%02X%02X%02X" % color


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))  # type: ignore[return-value]


def enable_dpi_awareness() -> float:
    """Make rendering crisp on high-DPI displays; returns the display scale factor."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()
        if dpi and dpi > 0:
            return dpi / 96.0
    except Exception:
        pass
    return 1.0


class RadarApp:
    """A square radar window whose disc represents the whole screen."""

    FPS = 60
    TRAIL_SEGMENTS = 46
    TRAIL_SPACING = 0.010  # radians between trail lines

    def __init__(self, root: tk.Tk, size: int = 213, rpm: float = 12.0, dpi_scale: float = 1.0):
        self.root = root
        self.size = size
        self.dpi = dpi_scale
        self.rpm = rpm
        self.model = RadarModel(rpm=rpm)
        self.canvas_px = max(300, round(size * dpi_scale))

        self.screen_w = user32.GetSystemMetrics(0)
        self.screen_h = user32.GetSystemMetrics(1)

        root.title("Simulation Radar")
        # Auto-place the window at the top-right corner of the screen.
        x = self.screen_w - self.canvas_px - round(60 * dpi_scale)
        root.geometry(f"{self.canvas_px}x{self.canvas_px}+{max(x, 0)}+{round(30 * dpi_scale)}")
        root.resizable(False, False)

        self.canvas = tk.Canvas(root, width=self.canvas_px, height=self.canvas_px, bg=_hex(BG), highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.center = self.canvas_px / 2.0
        self.margin = max(10, round(self.canvas_px * 0.044))
        self.disc_radius = self.canvas_px / 2.0 - self.margin

        self._build_static()
        self._trail: list[tuple[int, tuple[int, int, int]]] = []
        self._head_line: int | None = None
        self._build_sweep()

        self._blip_items: list[int] = []

        self._last = perf_counter()
        self._frames_left: int | None = None
        self._report_path: Path | None = None
        self.exit_code = 0
        self.root.report_callback_exception = lambda exc, val, tb: self._log_error()

        self._tick()

    # ------------------------------------------------------------------ UI

    def _build_static(self) -> None:
        cv = self.canvas
        c, R = self.center, self.disc_radius
        cv.create_oval(c - R, c - R, c + R, c + R, outline=_hex(RING), width=2)
        for frac in (0.25, 0.5, 0.75):
            r = R * frac
            cv.create_oval(c - r, c - r, c + r, c + r, outline=_hex(TICK), width=1)
        cv.create_line(c - R, c, c + R, c, fill=_hex(TICK))
        cv.create_line(c, c - R, c, c + R, fill=_hex(TICK))
        for i in range(24):
            a = i * math.tau / 24
            s, co = math.sin(a), math.cos(a)
            if i % 3 == 0:
                x1, y1, x2, y2 = c + (R - 12) * s, c - (R - 12) * co, c + (R - 2) * s, c - (R - 2) * co
                cv.create_line(x1, y1, x2, y2, fill=_hex(TICK), width=2)
            else:
                x1, y1, x2, y2 = c + (R - 7) * s, c - (R - 7) * co, c + (R - 2) * s, c - (R - 2) * co
                cv.create_line(x1, y1, x2, y2, fill=_hex(TICK), width=1)
        cv.create_oval(c - 3, c - 3, c + 3, c + 3, fill=_hex(HUD), outline="")

    def _build_sweep(self) -> None:
        cv = self.canvas
        for i in range(self.TRAIL_SEGMENTS):
            t = i / self.TRAIL_SEGMENTS
            color = _mix(BG, SWEEP_MAX, 0.55 * (1.0 - t) ** 1.6)
            lid = cv.create_line(self.center, self.center, self.center, self.center, fill=_hex(color), width=1)
            self._trail.append((lid, color))
        self._head_line = cv.create_line(
            self.center, self.center, self.center, self.center, fill=_hex(HEAD), width=2
        )

    def _update_sweep(self, cur: float) -> None:
        c, R = self.center, self.disc_radius
        for idx, (lid, _color) in enumerate(self._trail):
            a = cur - (idx + 1) * self.TRAIL_SPACING
            x = c + R * math.sin(a)
            y = c - R * math.cos(a)
            self.canvas.coords(lid, c, c, x, y)
        x = c + R * math.sin(cur)
        y = c - R * math.cos(cur)
        self.canvas.coords(self._head_line, c, c, x, y)

    # --------------------------------------------------------------- logic

    def _sample_cursor(self) -> None:
        pt = wintypes.POINT()
        if not user32.GetCursorPos(ctypes.byref(pt)):
            return
        dx = pt.x - self.screen_w / 2.0
        dy = pt.y - self.screen_h / 2.0
        max_r = min(self.screen_w, self.screen_h) / 2.0
        dist = math.hypot(dx, dy)
        if dist > max_r and dist > 0:
            scale = max_r / dist
            dx, dy = dx * scale, dy * scale
            dist = max_r
        self.model.set_cursor(clockwise_angle(dx, dy), dist / max_r)

    def _update_blips(self) -> None:
        cv = self.canvas
        for item in self._blip_items:
            cv.delete(item)
        self._blip_items.clear()
        c, R = self.center, self.disc_radius
        for echo in self.model.echoes:
            b = self.model.brightness(echo)
            if b <= 0.01:
                continue
            a = echo.angle
            r = echo.radius * R
            x = c + r * math.sin(a)
            y = c - r * math.cos(a)
            glow_r, core_r = 4 + 10 * b, 1.5 + 3.5 * b
            self._blip_items.append(
                cv.create_oval(
                    x - glow_r, y - glow_r, x + glow_r, y + glow_r,
                    fill=_hex(_mix(BG, BLIP_RED, 0.35 * b)), outline="",
                )
            )
            self._blip_items.append(
                cv.create_oval(
                    x - core_r, y - core_r, x + core_r, y + core_r,
                    fill=_hex(_mix(BG, BLIP_RED, 0.55 + 0.45 * b)), outline="",
                )
            )

    def _tick(self) -> None:
        try:
            now = perf_counter()
            dt = min(now - self._last, 0.25)
            self._last = now
            _prev, cur = self.model.step(dt)
            self._sample_cursor()
            self._update_sweep(cur)
            self._update_blips()
            if self._frames_left is not None:
                self._frames_left -= 1
                if self._frames_left <= 0:
                    self._finish_smoke(success=True)
                    return
        except Exception:
            # Never let a single frame kill the sweep loop.
            self._log_error()
            if self._frames_left is not None:
                self._finish_smoke(success=False)
                return
        self.root.after(max(1, int(1000 / self.FPS)), self._tick)

    def _log_error(self) -> None:
        try:
            path = Path(tempfile.gettempdir()) / "radar_error.log"
            with path.open("a", encoding="utf-8") as fh:
                fh.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}]\n{traceback.format_exc()}\n")
        except Exception:
            pass

    # ------------------------------------------------------------- testing

    def start_smoke_test(self, frames: int = 90, report: Path | None = None) -> None:
        self._frames_left = frames
        self._report_path = report

        def on_error(exc, val, tb):
            self._log_error()
            if self._report_path is not None:
                self._report_path.write_text("FAIL\n" + "".join(traceback.format_exception(exc, val, tb)))
            self.exit_code = 1
            self.root.destroy()

        self.root.report_callback_exception = on_error

    def _finish_smoke(self, success: bool) -> None:
        if self._report_path is not None:
            self._report_path.write_text("OK" if success else "FAIL")
        self.exit_code = 0 if success else 1
        self.root.destroy()


def run(size: int = 213, rpm: float = 12.0, smoke_test: bool = False) -> int:
    dpi_scale = enable_dpi_awareness()
    root = tk.Tk()
    app = RadarApp(root, size=size, rpm=rpm, dpi_scale=dpi_scale)
    if smoke_test:
        report = Path(tempfile.gettempdir()) / "radar_smoke_report.txt"
        try:
            report.unlink(missing_ok=True)
        except OSError:
            pass
        app.start_smoke_test(frames=90, report=report)
    root.mainloop()
    return app.exit_code
