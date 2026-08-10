# -*- coding: utf-8 -*-
"""登录界面：学生 / 教师 / 管理员三种身份登录（渐变背景 + 居中卡片）。"""
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk

import dpi
from gui_utils import gradient
from security import login_guard
from settings_dialog import SettingsDialog
from ui_style import PALETTE
from i18n import tr


def _log(storage, operator, role, action, target="", detail=""):
    try:
        storage.add_log(operator, role, action, target, detail)
    except Exception:
        pass


class LoginFrame(ttk.Frame):
    """主界面登录页：身份选择 + 学生登录 + 教师/管理员登录。"""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.storage = app.storage
        self.pages = ttk.Frame(self)
        self.pages.pack(fill="both", expand=True)
        self.show_choice()

    def clear(self):
        for child in self.pages.winfo_children():
            child.destroy()

    def _gradient_page(self):
        """创建带渐变背景的页面，返回 (page, canvas)。"""
        page = tk.Frame(self.pages, bg=PALETTE["bg"])
        page.pack(fill="both", expand=True)
        canvas = tk.Canvas(
            page, bg=PALETTE["bg"], highlightthickness=0, bd=0
        )
        canvas.pack(fill="both", expand=True)

        def redraw(event=None):
            gradient(
                canvas,
                canvas.winfo_width(),
                canvas.winfo_height(),
                PALETTE["banner"],
                PALETTE["bg"],
            )

        canvas.bind("<Configure>", redraw)
        page.update_idletasks()
        redraw()
        return page, canvas

    def _card(self, page, width, height):
        card = tk.Frame(
            page,
            bg=PALETTE["card"],
            highlightbackground=PALETTE["banner"],
            highlightthickness=0,
            bd=0,
        )
        card.place(
            relx=0.5,
            rely=0.5,
            anchor="center",
            width=dpi.scale(width),
            height=dpi.scale(height),
        )
        return card

    @staticmethod
    def _card_label(card, text, **kwargs):
        kwargs.setdefault("bg", PALETTE["card"])
        kwargs.setdefault("fg", PALETTE["text"])
        return tk.Label(card, text=text, **kwargs)

    def show_choice(self):
        self.clear()
        page, _ = self._gradient_page()
        card = self._card(page, 430, 575)

        self._card_label(
            card,
            tr('学生信息管理系统'),
            font=("Microsoft YaHei UI", 22, "bold"),
            fg=PALETTE["primary"],
        ).pack(pady=dpi.P((34, 6)))
        self._card_label(
            card,
            tr('请选择登录身份'),
            font=("Microsoft YaHei UI", 12),
            fg=PALETTE["muted"],
        ).pack(pady=dpi.P((0, 26)))

        def make_btn(text, style, command):
            btn = ttk.Button(
                card, text=text, style=style, command=command,
                icon={
                    "TButton": "person-fill",
                    "Green.TButton": "mortarboard-fill",
                    "Purple.TButton": "shield-lock-fill",
                }[style],
            )
            btn.pack(
                pady=dpi.P(7), ipady=dpi.P(7), fill="x", padx=dpi.P(46)
            )
            return btn

        make_btn(tr('学 生 登 录'), "TButton", self.show_student_login)
        make_btn(tr('教 师 登 录'), "Green.TButton", self.show_teacher_login)
        make_btn(tr('管理员登录'), "Purple.TButton", self.show_admin_login)

        self._card_label(
            card,
            tr('学生凭学号+密码登录；教师/管理员凭账号+密码登录'),
            font=("Microsoft YaHei UI", 9),
            fg=PALETTE["muted"],
        ).pack(pady=dpi.P((26, 0)))
        ttk.Button(
            card,
            text=tr('设置'),
            style="Secondary.TButton",
            icon="gear",
            command=lambda: SettingsDialog(self, self.app),
        ).pack(pady=dpi.P((16, 0)))
        self._card_label(
            card,
            tr('存储方式：{}').format(tr(self.storage.mode)),
            font=("Microsoft YaHei UI", 9),
            fg=PALETTE["muted"],
        ).pack(side="bottom", pady=dpi.P(14))

    def _login_card(self, title, fields, on_login):
        self.clear()
        page, _ = self._gradient_page()
        card = self._card(page, 400, 360)

        self._card_label(
            card,
            title,
            font=("Microsoft YaHei UI", 20, "bold"),
            fg=PALETTE["primary"],
        ).pack(pady=dpi.P((28, 22)))

        vars_ = {}
        entries = []
        for label, key, show in fields:
            self._card_label(
                card, label, font=("Microsoft YaHei UI", 11)
            ).pack(anchor="w", padx=dpi.P(46))
            var = tk.StringVar()
            entry = ttk.Entry(card, textvariable=var, width=30, show=show)
            entry.pack(fill="x", padx=dpi.P(46), pady=dpi.P((4, 12)))
            vars_[key] = var
            entries.append(entry)

        def do_login(_event=None):
            on_login(vars_)

        if entries:
            entries[0].focus_set()
            entries[-1].bind("<Return>", do_login)
        for entry in entries[:-1]:
            entry.bind(
                "<Return>",
                lambda e, nxt=entries[entries.index(entry) + 1]: nxt.focus_set(),
            )

        btns = tk.Frame(card, bg=PALETTE["card"])
        btns.pack(pady=dpi.P((16, 0)))
        ttk.Button(
            btns, text=tr('登  录'), width=13, icon="box-arrow-in-right",
            command=do_login,
        ).pack(
            side="left", padx=8
        )
        ttk.Button(
            btns,
            text=tr('返  回'),
            width=13,
            style="Secondary.TButton",
            icon="arrow-left",
            command=self.show_choice,
        ).pack(side="left", padx=8)
        return vars_

    def show_student_login(self):
        def on_login(vars_):
            student_id = vars_["student_id"].get().strip()
            password = vars_["password"].get()
            if not student_id or not password:
                messagebox.showwarning(tr('提示'), tr('请输入学号和密码'))
                return
            key = f"student:{student_id}"
            if login_guard.remaining(key) == 0:
                messagebox.showerror(
                    tr('登录已锁定'),
                    tr('连续输错密码次数过多，请 {} 秒后再试').format(login_guard.lock_seconds_left(key)),
                )
                return
            student = self.storage.student_login(student_id, password)
            if student is None:
                left = login_guard.record_failure(key)
                _log(
                    self.storage, student_id, tr('学生'), tr('登录失败'),
                    student_id, tr('剩余尝试次数：{}').format(left),
                )
                messagebox.showerror(
                    tr('登录失败'),
                    tr('学号或密码错误')
                    + (tr('（还可尝试 {} 次）').format(left) if left > 0 else tr('，账号已临时锁定')),
                )
                return
            login_guard.reset(key)
            _log(self.storage, student_id, tr('学生'), tr('登录成功'), student_id)
            self.app.show_student(student)

        self._login_card(
            tr('学生登录'),
            [(tr('学号：'), "student_id", None), (tr('密码：'), "password", "*")],
            on_login,
        )

    def show_teacher_login(self):
        self._show_account_login(tr('教师登录'), self.storage.teacher_login)

    def show_admin_login(self):
        self._show_account_login(tr('管理员登录'), self.storage.admin_login)

    def _show_account_login(self, title, login_method):
        def on_login(vars_):
            username = vars_["username"].get().strip()
            password = vars_["password"].get()
            if not username or not password:
                messagebox.showwarning(tr('提示'), tr('请输入账号和密码'))
                return
            key = f"account:{username}"
            if login_guard.remaining(key) == 0:
                messagebox.showerror(
                    tr('登录已锁定'),
                    tr('连续输错密码次数过多，请 {} 秒后再试').format(login_guard.lock_seconds_left(key)),
                )
                return
            account = login_method(username, password)
            if account is None:
                left = login_guard.record_failure(key)
                role_name = (
                    tr('管理员') if login_method is self.storage.admin_login else tr('教师')
                )
                _log(
                    self.storage, username, role_name, tr('登录失败'),
                    username, tr('剩余尝试次数：{}').format(left),
                )
                messagebox.showerror(
                    tr('登录失败'),
                    tr('账号或密码错误')
                    + (tr('（还可尝试 {} 次）').format(left) if left > 0 else tr('，账号已临时锁定')),
                )
                return
            login_guard.reset(key)
            role_name = tr('管理员') if account.get("role") == "admin" else tr('教师')
            _log(self.storage, username, role_name, tr('登录成功'), username)
            self.app.show_teacher(account)

        self._login_card(
            title,
            [(tr('账号：'), "username", None), (tr('密码：'), "password", "*")],
            on_login,
        )
