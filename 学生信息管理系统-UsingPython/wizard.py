# -*- coding: utf-8 -*-
"""启动向导：自动检测 MySQL，引导用户选择存储方式并完成初始化。

流程：
1. 自动扫描检测本机是否存在 MySQL（TCP 连接 3306 端口）；
2. 检测到 MySQL：输入账号密码 → 连接 → 自动创建项目专属数据库；
   未检测到：输入路径 → 在该路径下创建 Excel 数据文件；
3. 无论哪种方式，都会判断是首次使用还是已有数据，然后进入主界面。
"""
import socket
import tkinter as tk
from tkinter import filedialog, messagebox

import ttkbootstrap as ttk

import config
import dpi
from excel_storage import ExcelStorage
from mysql_storage import MySqlStorage
import settings
from storage import StorageError
from ui_style import PALETTE, setup_style
from i18n import tr


def detect_mysql(host=config.DEFAULT_MYSQL_HOST, port=config.DEFAULT_MYSQL_PORT, timeout=1.5):
    """检测本机 MySQL 服务是否可达（端口是否开放）。"""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


class Wizard(tk.Tk):
    """启动向导窗口，完成后把选定的存储对象写入 result。"""

    def __init__(self):
        dpi.enable_dpi_awareness()
        super().__init__()
        self.title(tr('学生信息管理系统 - 启动向导'))
        dpi.set_scale_from_root(self)
        self.geometry(dpi.geom(560, 440))
        self.resizable(False, False)
        self.result = None
        self.pages = ttk.Frame(self)
        self.pages.pack(fill="both", expand=True)
        saved = settings.load_settings()
        setup_style(self, dark=saved["theme"] == "dark")
        self._center()
        self._show_detecting()

    def _center(self):
        self.update_idletasks()
        w, h = dpi.scale(560), dpi.scale(440)
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")

    def _clear(self):
        for child in self.pages.winfo_children():
            child.destroy()

    def _centered_page(self):
        """创建一个内容整体居中的页面，返回 (page, content)。"""
        page = ttk.Frame(self.pages)
        page.pack(fill="both", expand=True)
        content = ttk.Frame(page)
        content.place(relx=0.5, rely=0.5, anchor="center")
        return page, content

    # ------------------------------------------------------------ 检测

    def _show_detecting(self):
        self._clear()
        page = ttk.Frame(self.pages)
        page.pack(fill="both", expand=True)
        ttk.Label(
            page, text=tr('正在自动扫描 MySQL 数据库…'), font=("Microsoft YaHei UI", 14, "bold")
        ).pack(pady=(120, 18))
        progress = ttk.Progressbar(page, mode="indeterminate", length=260)
        progress.pack()
        progress.start(12)
        ttk.Label(
            page,
            text=tr('检测本机 3306 端口是否运行 MySQL 服务'),
            foreground=PALETTE["muted"],
        ).pack(pady=(16, 0))
        self.after(1300, self._finish_detecting)

    def _finish_detecting(self):
        if detect_mysql():
            self._show_mysql_form()
        else:
            self._show_excel_form(tr('未检测到 MySQL（端口 3306 无响应），将使用 Excel 表格存储。'))

    # ------------------------------------------------------------ MySQL

    def _show_mysql_form(self):
        self._clear()
        _page, content = self._centered_page()

        ttk.Label(content, text=tr('检测到 MySQL 数据库'), font=("Microsoft YaHei UI", 14, "bold")).pack(
            anchor="w"
        )
        ttk.Label(
            content,
            text=tr('输入数据库账号和密码，连接后将自动创建项目专属数据库 “{}”。').format(config.DATABASE_NAME),
            foreground=PALETTE["muted"],
            wraplength=480,
        ).pack(anchor="w", pady=(6, 18))

        form = ttk.Frame(content)
        form.pack(fill="x")

        self.var_host = tk.StringVar(value=config.DEFAULT_MYSQL_HOST)
        self.var_port = tk.StringVar(value=str(config.DEFAULT_MYSQL_PORT))
        self.var_user = tk.StringVar()
        self.var_password = tk.StringVar()

        def add_row(label, var, row, show=None):
            ttk.Label(form, text=label).grid(
                row=row, column=0, padx=(0, 10), pady=7, sticky="e"
            )
            ttk.Entry(form, textvariable=var, width=30, show=show).grid(
                row=row, column=1, pady=7
            )

        add_row(tr('主机：'), self.var_host, 0)
        add_row(tr('端口：'), self.var_port, 1)
        add_row(tr('用户名：'), self.var_user, 2)
        add_row(tr('密码：'), self.var_password, 3, show="*")

        error_label = ttk.Label(content, text="", foreground=PALETTE["red"])
        error_label.pack(anchor="w", pady=(10, 0))

        btns = ttk.Frame(content)
        btns.pack(fill="x", pady=(18, 0))
        ttk.Button(
            btns, text=tr('连接并初始化'), icon="plug-fill",
            command=lambda: self._try_mysql(error_label),
        ).pack(side="left", padx=(0, 10), ipady=dpi.P(4))
        ttk.Button(
            btns, text=tr('改用 Excel 存储'), style="Secondary.TButton",
            command=self._show_excel_form,
        ).pack(side="left")
        self.bind("<Return>", lambda e: self._try_mysql(error_label))

    def _try_mysql(self, error_label):
        username = self.var_user.get().strip()
        password = self.var_password.get()
        if not username or not password:
            error_label.config(text=tr('请输入用户名和密码'))
            return
        try:
            storage = MySqlStorage(
                self.var_host.get().strip() or "127.0.0.1",
                int(self.var_port.get().strip() or 3306),
                username,
                password,
            )
        except (ValueError, StorageError) as exc:
            error_label.config(text=str(exc))
            return
        messagebox.showinfo(tr('初始化完成'), storage.info, parent=self)
        self.finish(storage)

    # ------------------------------------------------------------ Excel

    def _show_excel_form(self, reason=None):
        self._clear()
        _page, content = self._centered_page()

        ttk.Label(content, text=tr('使用 Excel 表格存储'), font=("Microsoft YaHei UI", 14, "bold")).pack(
            anchor="w"
        )
        if reason:
            ttk.Label(content, text=reason, foreground=PALETTE["red"]).pack(
                anchor="w", pady=(6, 0)
            )
        ttk.Label(
            content,
            text=tr('请先选择一个存放路径，系统会在该路径下创建 students.xlsx、scores.xlsx、teachers.xlsx 三个数据文件。'),
            foreground=PALETTE["muted"],
            wraplength=480,
        ).pack(anchor="w", pady=(6, 18))

        self.var_path = tk.StringVar()
        row = ttk.Frame(content)
        row.pack(fill="x")
        ttk.Entry(row, textvariable=self.var_path, width=38).pack(side="left")
        ttk.Button(
            row, text=tr('浏览…'), style="Secondary.TButton",
            icon="folder2-open", command=self._browse_path,
        ).pack(side="left", padx=(8, 0))

        error_label = ttk.Label(content, text="", foreground=PALETTE["red"])
        error_label.pack(anchor="w", pady=(10, 0))

        btns = ttk.Frame(content)
        btns.pack(fill="x", pady=(18, 0))
        ttk.Button(
            btns, text=tr('确认并使用此路径'), icon="check-circle-fill",
            command=lambda: self._try_excel(error_label),
        ).pack(side="left", padx=(0, 10), ipady=dpi.P(4))
        ttk.Button(
            btns, text=tr('改用 MySQL 存储'), style="Secondary.TButton",
            command=self._show_mysql_form,
        ).pack(side="left")
        self.bind("<Return>", lambda e: self._try_excel(error_label))

    def _browse_path(self):
        path = filedialog.askdirectory(parent=self, title=tr('选择 Excel 数据存放目录'))
        if path:
            self.var_path.set(path)

    def _try_excel(self, error_label):
        path = self.var_path.get().strip()
        if not path:
            error_label.config(text=tr('请先输入或选择存放路径'))
            return
        try:
            storage = ExcelStorage(path)
        except StorageError as exc:
            error_label.config(text=str(exc))
            return
        messagebox.showinfo(tr('初始化完成'), storage.info, parent=self)
        self.finish(storage)

    # ------------------------------------------------------------ 完成

    def finish(self, storage):
        self.result = storage
        self.destroy()
