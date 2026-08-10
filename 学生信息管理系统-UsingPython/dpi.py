# -*- coding: utf-8 -*-
"""高 DPI 支持：开启进程级 DPI 感知，并提供逻辑像素 -> 物理像素换算。

tkinter 在高分屏（如 200% 缩放）下如果不开 DPI 感知，整个窗口会被 Windows
位图拉伸，文字与界面看起来“模糊/马赛克”。开启感知后，Tk 以原生分辨率渲染，
但窗口几何尺寸与像素类参数都要按 DPI 系数放大，保持原有视觉效果。
"""
import ctypes

_scale = 1.0


def enable_dpi_awareness():
    """开启进程级 DPI 感知（必须在创建任何 Tk 窗口之前调用）。"""
    global _scale
    try:
        shcore = ctypes.windll.shcore
        shcore.SetProcessDpiAwareness.argtypes = [ctypes.c_int]
        shcore.SetProcessDpiAwareness.restype = ctypes.c_long
        if shcore.SetProcessDpiAwareness(2) == 0:  # 每显示器 DPI 感知
            return True
    except Exception:
        pass
    try:
        if ctypes.windll.user32.SetProcessDPIAware():  # 系统 DPI 感知（降级）
            return True
    except Exception:
        pass
    _scale = 1.0
    return False


def set_scale_from_root(root):
    """根据当前显示器 DPI 计算缩放系数（1 英寸实际像素 / 96）。"""
    global _scale
    try:
        _scale = root.winfo_fpixels("1i") / 96.0
    except Exception:
        _scale = 1.0
    return _scale


def scale(value):
    """逻辑像素 -> 物理像素。"""
    return int(round(value * _scale))


def P(value):
    """缩放 padding / 间距（支持整数或二元组）。"""
    if isinstance(value, (tuple, list)):
        return tuple(scale(v) for v in value)
    return scale(value)


def geom(width, height):
    """生成按 DPI 缩放后的 Tk 几何尺寸字符串。"""
    return f"{scale(width)}x{scale(height)}"


def minsz(width, height):
    """生成按 DPI 缩放后的最小尺寸参数。"""
    return scale(width), scale(height)
