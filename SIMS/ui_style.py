# -*- coding: utf-8 -*-
"""界面统一样式：基于 ttkbootstrap 主题（浅色 cosmo / 深色 darkly）+ 统一配色。

参考 GitHub 上 ttkbootstrap（israel-dryer/ttkbootstrap）的成熟做法：
- 使用 30 套现成主题中的 cosmo / darkly，控件自带现代质感与深色适配；
- 语义化 bootstyle（success / danger / secondary）与主题感知图标；
- 运行时切换主题（theme_use），无需重写控件。
"""
import ttkbootstrap as ttk
from ttkbootstrap import Style

import dpi

LIGHT_THEME = "cosmo"
DARK_THEME = "darkly"

PALETTE = {}


def _hex_to_rgb(color):
    color = color.lstrip("#")
    return tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))


def _darker(color, factor=0.86):
    """把颜色变深，用于按钮悬停/按下状态。"""
    r, g, b = _hex_to_rgb(color)
    return "#%02x%02x%02x" % tuple(max(0, int(c * factor)) for c in (r, g, b))


def setup_style(root, dark=False):
    """给窗口应用统一样式（ttkbootstrap 主题 + 自定义配色与样式名）。"""
    dpi.set_scale_from_root(root)
    theme_name = DARK_THEME if dark else LIGHT_THEME
    style = Style(theme=theme_name)
    style.theme_use(theme_name)

    if dark:
        BG = "#111827"
        CARD = "#1f2937"
        BANNER = "#1e3a8a"
        TEXT = "#e5e7eb"
        MUTED = "#9ca3af"
        PRIMARY = "#3b82f6"
        PRIMARY_DARK = "#2563eb"
        GREEN = "#22c55e"
        GREEN_DARK = "#16a34a"
        PURPLE = "#a78bfa"
        PURPLE_DARK = "#8b5cf6"
        RED = "#ef4444"
        RED_DARK = "#dc2626"
        SECONDARY = "#374151"
        SECONDARY_TEXT = "#e5e7eb"
        SECONDARY_DARK = "#4b5563"
        FIELD = "#282828"
        TREE_BG = "#1f2937"
        TREE_FG = "#e5e7eb"
        HEAD_BG = "#2b3548"
        HEAD_FG = "#bfdbfe"
        HEAD_LIGHT = "#3b4a66"
        HEAD_DARK = "#1b2333"
        HEAD_LINE = "#475569"
        SEL = "#2563eb"
        VALUE = "#93c5fd"
        NOTE = "#c7d2fe"
        ROW_EVEN = "#26313f"
        TREE_SEL_FG = "#ffffff"
    else:
        BG = "#eef2f7"
        CARD = "#ffffff"
        BANNER = "#1d4ed8"
        TEXT = "#1f2937"
        MUTED = "#6b7280"
        PRIMARY = "#2563eb"
        PRIMARY_DARK = "#1d4ed8"
        GREEN = "#16a34a"
        GREEN_DARK = "#15803d"
        PURPLE = "#7c3aed"
        PURPLE_DARK = "#6d28d9"
        RED = "#dc2626"
        RED_DARK = "#b91c1c"
        SECONDARY = "#e2e8f0"
        SECONDARY_TEXT = "#334155"
        SECONDARY_DARK = "#cbd5e1"
        FIELD = "#ffffff"
        TREE_BG = "#ffffff"
        TREE_FG = "#1f2937"
        HEAD_BG = "#e0e7ff"
        HEAD_FG = "#1e3a8a"
        HEAD_LIGHT = "#ffffff"
        HEAD_DARK = "#a3b0d0"
        HEAD_LINE = "#a3b0d0"
        SEL = "#2563eb"
        VALUE = "#1a5fb4"
        NOTE = "#bfdbfe"
        ROW_EVEN = "#f1f5f9"
        TREE_SEL_FG = "#ffffff"

    base_font = ("Microsoft YaHei UI", 10)

    style.configure(".", font=base_font)
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=TEXT)
    style.configure(
        "Title.TLabel",
        font=("Microsoft YaHei UI", 22, "bold"),
        foreground=PRIMARY,
        background=BG,
    )

    # ---- 按钮：默认主色 + 语义色（保留旧样式名，兼容现有代码） ----
    def _btn(name, bg, fg, active, pressed):
        style.configure(
            name,
            background=bg,
            foreground=fg,
            font=base_font,
            padding=dpi.P((14, 6)),
            borderwidth=0,
            focuscolor=fg,
        )
        style.map(
            name,
            background=[("active", active), ("pressed", pressed)],
            foreground=[("active", fg), ("pressed", fg)],
            bordercolor=[("focus", bg)],
        )

    _btn("TButton", PRIMARY, "#ffffff", PRIMARY_DARK, _darker(PRIMARY_DARK))
    _btn(
        "Secondary.TButton",
        SECONDARY,
        SECONDARY_TEXT,
        SECONDARY_DARK,
        _darker(SECONDARY_DARK),
    )
    _btn("Danger.TButton", RED, "#ffffff", RED_DARK, _darker(RED_DARK))
    _btn("Green.TButton", GREEN, "#ffffff", GREEN_DARK, _darker(GREEN_DARK))
    _btn("Purple.TButton", PURPLE, "#ffffff", PURPLE_DARK, _darker(PURPLE_DARK))

    # ---- 输入框 / 下拉框：配色交给主题（自动适配深浅色），只统一字体 ----
    style.configure("TEntry", font=base_font)
    style.configure("TCombobox", font=base_font)

    # ---- 表格 ----
    style.configure(
        "Treeview",
        rowheight=dpi.scale(30),
        background=TREE_BG,
        fieldbackground=TREE_BG,
        foreground=TREE_FG,
        borderwidth=0,
    )
    style.map(
        "Treeview",
        background=[("selected", SEL)],
        foreground=[("selected", TREE_SEL_FG)],
    )
    style.configure(
        "Treeview.Heading",
        background=HEAD_BG,
        foreground=HEAD_FG,
        font=("Microsoft YaHei UI", 10, "bold"),
        padding=(8, 7),
        relief="raised",
        borderwidth=dpi.scale(1),
        bordercolor=HEAD_LINE,
        lightcolor=HEAD_LIGHT,
        darkcolor=HEAD_DARK,
    )

    # ---- 选项卡 ----
    style.configure("TNotebook", borderwidth=0, tabmargins=(8, 8, 8, 0))
    style.configure(
        "TNotebook.Tab",
        padding=(16, 8),
        font=("Microsoft YaHei UI", 10),
    )

    # ---- 横幅 / 卡片 ----
    style.configure("Banner.TFrame", background=BANNER)
    style.configure(
        "Banner.TLabel",
        background=BANNER,
        foreground="#ffffff",
        font=("Microsoft YaHei UI", 16, "bold"),
    )
    style.configure("Card.TFrame", background=CARD)
    style.configure("Card.TLabel", background=CARD, foreground=TEXT)
    style.configure(
        "CardTitle.TLabel",
        background=CARD,
        foreground=TEXT,
        font=("Microsoft YaHei UI", 13, "bold"),
    )
    style.configure(
        "CardValue.TLabel",
        background=CARD,
        foreground=VALUE,
        font=("Microsoft YaHei UI", 12, "bold"),
    )
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("BannerNote.TLabel", background=BANNER, foreground=NOTE)
    style.configure("CardMuted.TLabel", background=CARD, foreground=MUTED)

    root.configure(bg=BG)

    PALETTE.update(
        {
            "dark": dark,
            "bg": BG,
            "card": CARD,
            "banner": BANNER,
            "text": TEXT,
            "muted": MUTED,
            "primary": PRIMARY,
            "green": GREEN,
            "purple": PURPLE,
            "red": RED,
            "secondary": SECONDARY,
            "secondary_text": SECONDARY_TEXT,
            "field": FIELD,
            "row_odd": TREE_BG,
            "row_even": ROW_EVEN,
            "selection": SEL,
            "dpi_scale": dpi.scale(1),
        }
    )
