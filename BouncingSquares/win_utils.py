"""Windows 窗口样式工具（桌宠模式专用）。"""
from __future__ import annotations

import ctypes
import tkinter as tk
from ctypes import wintypes

TRANSPARENT_COLOR = "#010203"  # 该颜色在 Windows 下会显示为透明

GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
GWL_WNDPROC = -4

LRESULT = ctypes.c_ssize_t
WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)

WM_NCHITTEST = 0x0084
HTCLIENT = 1
HTTRANSPARENT = -1


def enable_dpi_awareness() -> None:
    """让窗口按物理像素渲染，避免高分屏下字体模糊/马赛克。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_DPI_AWARE
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def work_area() -> tuple[int, int, int, int] | None:
    """主屏幕工作区（不含任务栏），失败返回 None。"""
    try:
        from ctypes import wintypes

        rect = wintypes.RECT()
        ok = ctypes.windll.user32.SystemParametersInfoW(
            0x0030, 0, ctypes.byref(rect), 0  # SPI_GETWORKAREA
        )
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if ok and w > 100 and h > 100:
            return w, h, rect.left, rect.top
    except Exception:
        pass
    return None


def virtual_screen() -> tuple[int, int, int, int] | None:
    """所有显示器组成的虚拟屏幕边界，返回 (x, y, w, h)（含负坐标显示器）。"""
    try:
        user32 = ctypes.windll.user32
        x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
        y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
        w = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
        h = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
        if w > 100 and h > 100:
            return x, y, w, h
    except Exception:
        pass
    return None


def top_level_hwnd(root: tk.Tk) -> int:
    """真正的顶层窗口句柄（Tk 的 winfo_id 返回的是内部包装窗口）。"""
    return ctypes.windll.user32.GetAncestor(root.winfo_id(), 2)  # GA_ROOT


def strip_frame_keep_taskbar(root: tk.Tk) -> bool:
    """去掉标题栏/边框，但保留任务栏按钮（Windows）。失败返回 False。"""
    try:
        user32 = ctypes.windll.user32
        hwnd = top_level_hwnd(root)
        style = user32.GetWindowLongPtrW(hwnd, GWL_STYLE)
        ex_style = user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        style &= ~(WS_CAPTION | WS_THICKFRAME)
        ex_style |= WS_EX_APPWINDOW
        ex_style &= ~WS_EX_TOOLWINDOW
        user32.SetWindowLongPtrW(hwnd, GWL_STYLE, style)
        user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex_style)
        return True
    except Exception:
        return False


_old_proc: WNDPROC | None = None
_proc_ref: WNDPROC | None = None
_hit_test = None
_wndproc_installed = False


def _region_wnd_proc(hwnd, msg, wparam, lparam):
    """WM_NCHITTEST：方块区域内可点击，其余区域鼠标穿透。"""
    try:
        if msg == WM_NCHITTEST and _hit_test is not None:
            x = ctypes.c_short(lparam & 0xFFFF).value
            y = ctypes.c_short((lparam >> 16) & 0xFFFF).value
            if _hit_test(x, y):
                return HTCLIENT
            return HTTRANSPARENT
    except Exception:
        pass
    return _old_proc(hwnd, msg, wparam, lparam)


def install_region_click_through(root: tk.Tk, hit_test) -> None:
    """方块区域可点击、其余区域鼠标穿透（Windows）。

    hit_test(screen_x, screen_y) -> bool：屏幕坐标是否落在方块上。
    重复调用只更新命中回调，不重复安装窗口过程。
    """
    global _old_proc, _proc_ref, _hit_test, _wndproc_installed
    try:
        user32 = ctypes.windll.user32
        hwnd = top_level_hwnd(root)
        _hit_test = hit_test
        if not _wndproc_installed:
            _proc_ref = WNDPROC(_region_wnd_proc)
            old_proc = user32.SetWindowLongPtrW(
                hwnd, GWL_WNDPROC, ctypes.cast(_proc_ref, ctypes.c_void_p).value
            )
            _old_proc = WNDPROC(old_proc)
            _wndproc_installed = True
    except Exception:
        pass


def position_window(root: tk.Tk, x: int, y: int, w: int, h: int) -> None:
    """把窗口精确放到指定屏幕位置（支持负坐标的扩展显示器）。

    注意：不能用 SWP_FRAMECHANGED，否则会触发 Tk 重新套用自身几何，
    导致 SetWindowPos 的效果被覆盖。
    """
    try:
        hwnd = top_level_hwnd(root)
        ctypes.windll.user32.SetWindowPos(
            hwnd, 0, x, y, w, h, 0x0004 | 0x0010  # NOZORDER|NOACTIVATE
        )
    except Exception:
        pass


def apply_desktop_pet_styles(root: tk.Tk, hit_test=None, rect=None) -> bool:
    """窗口已映射后调用：先让 Tk 记录正确尺寸，再去边框、精确定位、区域穿透。

    必须在事件循环中逐步结算（root.update），否则 Tk 会用自身几何覆盖定位。
    """
    if rect:
        _x, _y, w, h = rect
        root.geometry(f"{w}x{h}+0+0")  # pack 已不再重置；Tk 记录正确尺寸
        root.update()
    ok = strip_frame_keep_taskbar(root)
    root.update()
    if rect:
        position_window(root, *rect)
        root.update()
    if hit_test is not None:
        install_region_click_through(root, hit_test)
    return ok
