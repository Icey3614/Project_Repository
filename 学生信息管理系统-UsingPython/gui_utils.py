# -*- coding: utf-8 -*-
"""界面通用工具：渐变背景、表格斑马纹、对话框头部。"""
import tkinter as tk
from tkinter import ttk

import dpi
from ui_style import PALETTE


def _blend(c1, c2, t):
    return "#%02x%02x%02x" % tuple(
        int(a + (b - a) * t) for a, b in zip(c1, c2)
    )


def _hex_to_rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def gradient(canvas, width, height, top, bottom):
    """在 Canvas 上绘制垂直渐变（顶部 top 色 → 底部 bottom 色）。"""
    canvas.delete("gradient")
    if width <= 0 or height <= 0:
        return
    steps = max(2, min(height, 160))
    top_rgb = _hex_to_rgb(top)
    bottom_rgb = _hex_to_rgb(bottom)
    for i in range(steps):
        t = i / (steps - 1)
        canvas.create_line(
            0,
            i,
            width,
            i,
            fill=_blend(top_rgb, bottom_rgb, t),
            tags="gradient",
        )
    canvas.tag_lower("gradient")


def zebra(tree):
    """为 Treeview 配置隔行变色标签。"""
    tree.tag_configure("odd", background=PALETTE.get("row_odd"))
    tree.tag_configure("even", background=PALETTE.get("row_even"))


def dialog_header(parent, title, subtitle=""):
    """在对话框顶部添加统一横幅。"""
    banner = ttk.Frame(parent, style="Banner.TFrame", padding=dpi.P((16, 10)))
    banner.pack(fill="x")
    ttk.Label(banner, text=title, style="Banner.TLabel").pack(side="left")
    if subtitle:
        ttk.Label(banner, text=subtitle, style="BannerNote.TLabel").pack(
            side="right"
        )
    return banner


def resolve_storage(parent):
    """从任意对话框/页面向上解析存储对象（兼容不同 parent 结构）。"""
    storage = getattr(parent, "storage", None)
    if storage is None:
        storage = getattr(getattr(parent, "app", None), "storage", None)
    return storage
