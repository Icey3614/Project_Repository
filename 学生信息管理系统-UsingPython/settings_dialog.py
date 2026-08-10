# -*- coding: utf-8 -*-
"""设置对话框：主题（浅色/深色）与语言（简中/繁中/英文/俄文）。"""
import tkinter as tk

import ttkbootstrap as ttk

import dpi
import i18n
import settings
from gui_utils import dialog_header


class SettingsDialog(tk.Toplevel):
    """设置窗口，保存后立即应用并重建当前页面。"""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title(i18n.tr("设置"))
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        dialog_header(self, i18n.tr("设置"))
        self._build()
        self._center(parent)

    def _center(self, parent):
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _build(self):
        body = ttk.Frame(self, padding=dpi.P(24))
        body.pack(fill="both", expand=True)

        # 主题
        ttk.Label(
            body, text=i18n.tr("主题"), font=("Microsoft YaHei UI", 12, "bold")
        ).pack(anchor="w", pady=(0, dpi.P(6)))
        self.theme_var = tk.StringVar(value="dark" if self.app.dark else "light")
        theme_row = ttk.Frame(body)
        theme_row.pack(anchor="w", pady=(0, dpi.P(16)))
        ttk.Radiobutton(
            theme_row, text=i18n.tr("浅色"), value="light",
            variable=self.theme_var,
        ).pack(side="left", padx=dpi.P((0, 20)))
        ttk.Radiobutton(
            theme_row, text=i18n.tr("深色"), value="dark",
            variable=self.theme_var,
        ).pack(side="left")

        # 语言
        ttk.Label(
            body, text=i18n.tr("语言"), font=("Microsoft YaHei UI", 12, "bold")
        ).pack(anchor="w", pady=(0, dpi.P(6)))
        self.lang_var = tk.StringVar(value=i18n.get_language())
        lang_row = ttk.Frame(body)
        lang_row.pack(anchor="w", pady=(0, dpi.P(18)))
        for code, name in i18n.LANGS.items():
            ttk.Radiobutton(
                lang_row, text=name, value=code, variable=self.lang_var,
            ).pack(side="left", padx=dpi.P((0, 16)))

        btns = ttk.Frame(body)
        btns.pack(pady=(dpi.P(6), 0))
        ttk.Button(
            btns, text=i18n.tr("保存"), width=12, command=self._save,
        ).pack(side="left", padx=dpi.P(8))
        ttk.Button(
            btns, text=i18n.tr("取消"), width=12,
            style="Secondary.TButton", command=self.destroy,
        ).pack(side="left", padx=dpi.P(8))
        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())
        self.focus_force()

    def _save(self):
        dark = self.theme_var.get() == "dark"
        lang = self.lang_var.get()
        settings.save_settings(theme="dark" if dark else "light", lang=lang)
        self.destroy()
        self.app.apply_settings(dark, lang)
