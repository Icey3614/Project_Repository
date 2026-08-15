# -*- coding: utf-8 -*-
"""程序入口：先运行启动向导（自动检测 MySQL / 选择存储方式），再打开主窗口。"""
import tkinter as tk
from tkinter import ttk

import dpi
import i18n
from login_window import LoginFrame
import settings
from student_window import StudentFrame
from teacher_window import TeacherFrame
from ui_style import setup_style
from wizard import Wizard
from i18n import tr


class App(tk.Tk):
    """主窗口，负责登录页 / 学生页 / 教师页之间的切换。"""

    def __init__(self, storage, dark=False):
        # 若之前存在已销毁的 Tk 根窗口（如启动向导），重置 ttkbootstrap
        # 的单例样式，避免它继续引用已销毁的根（与 Window.destroy 行为一致）
        from ttkbootstrap import Style
        from ttkbootstrap.utils.fonts import Fonts

        Style.instance = None
        Fonts.reset()
        dpi.enable_dpi_awareness()
        super().__init__()
        self.storage = storage
        self.dark = dark
        self.title(tr('学生信息管理系统 - {}').format(tr(storage.mode)))
        self._setup_style()
        self._current = None
        self.geometry(dpi.geom(1020, 660))
        self.minsize(*dpi.minsz(940, 600))
        self._center_window()

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        self.show_login()

    def _center_window(self):
        self.update_idletasks()
        w, h = dpi.scale(1020), dpi.scale(660)
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{max(x, 0)}+{max(y, 0)}")

    def _setup_style(self):
        setup_style(self, dark=self.dark)
        self.option_add("*Font", ("Microsoft YaHei UI", 10))

    def toggle_theme(self):
        """在浅色/深色主题之间切换。"""
        self.dark = not self.dark
        setup_style(self, dark=self.dark)
        self._rebuild_current()

    def apply_settings(self, dark, lang):
        """应用设置（主题 + 语言），并重建当前页面。"""
        i18n.set_language(lang)
        self.dark = bool(dark)
        setup_style(self, dark=self.dark)
        self._rebuild_current()

    def _rebuild_current(self):
        current = getattr(self, "_current", None)
        if current and current[0] is not LoginFrame:
            self._switch(current[0], *current[1])
        else:
            self.show_login()

    def _switch(self, frame_class, *args):
        for child in self.container.winfo_children():
            child.destroy()
        self._current = (frame_class, args)
        frame_class(self.container, self, *args).pack(fill="both", expand=True)

    def show_login(self):
        self._switch(LoginFrame)

    def show_student(self, student):
        self._switch(StudentFrame, student)

    def show_teacher(self, teacher):
        self._switch(TeacherFrame, teacher)

    def destroy(self):
        # 退出时释放 Excel 数据目录的锁文件
        release = getattr(self.storage, "release", None)
        if release:
            try:
                release()
            except Exception:
                pass
        super().destroy()


def main():
    # 必须在创建任何 Tk 窗口之前开启 DPI 感知，避免高分屏下界面模糊
    dpi.enable_dpi_awareness()
    # 读取并应用上次的设置（语言作用于全局，主题用于主窗口）
    saved = settings.load_settings()
    i18n.set_language(saved["lang"])
    # 第一步：启动向导（自动检测 MySQL、输入账密/路径、首次/复用初始化）
    wizard = Wizard()
    wizard.mainloop()
    storage = wizard.result
    if storage is None:
        return  # 用户关闭了向导

    # 第二步：打开主窗口
    App(storage, dark=saved["theme"] == "dark").mainloop()


if __name__ == "__main__":
    main()
