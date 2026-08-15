# -*- coding: utf-8 -*-
"""学生视图：查看本人信息，成绩图表支持单人查看与多人对比。"""
import tkinter as tk
from tkinter import messagebox

import ttkbootstrap as ttk

import dpi
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from gui_utils import dialog_header, resolve_storage
from i18n import tr
from settings_dialog import SettingsDialog

# 图表中文字体设置（Windows 下使用微软雅黑）
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

SUBJECTS = {
    "语文": "chinese_score",
    "数学": "math_score",
    "英语": "english_score",
}

# 多人对比时的颜色序列
COLORS = [
    "#1a5fb4", "#b3261e", "#1a7f37", "#b58310",
    "#7a3bb3", "#0e8a8a", "#d0455e", "#5c6b73",
    "#6a4e2e", "#2e6a4e",
]


def make_person(student, scores):
    """把学生信息与成绩组装成图表数据块。"""
    return {
        "student_id": student["student_id"],
        "name": student["name"],
        "scores": scores,
    }


class StudentFrame(ttk.Frame):
    """学生登录后的个人信息页（只读）。"""

    def __init__(self, parent, app, student):
        super().__init__(parent)
        self.app = app
        self.storage = app.storage
        self.student = student
        self.scores = []
        self._load_scores()
        self._build()

    def _load_scores(self):
        try:
            self.scores = self.storage.get_scores(self.student["student_id"])
        except Exception:
            self.scores = []

    def _build(self):
        s = self.student

        head = ttk.Frame(self, style="Banner.TFrame", padding=dpi.P((18, 10)))
        head.pack(fill="x")
        ttk.Label(head, text=tr('我的信息'), style="Banner.TLabel").pack(side="left")
        ttk.Button(
            head, text=tr('设置'), style="Secondary.TButton",
            icon="gear",
            command=lambda: SettingsDialog(self, self.app),
        ).pack(side="right", padx=(0, 8))
        ttk.Button(
            head, text=tr('修改密码'), style="Secondary.TButton", icon="key-fill",
            command=lambda: StudentChangePasswordDialog(self, self.student),
        ).pack(side="right", padx=(0, 8))
        ttk.Button(
            head, text=tr('返回登录'), style="Secondary.TButton",
            icon="box-arrow-right",
            command=self.app.show_login,
        ).pack(side="right", padx=(0, 8))
        ttk.Label(
            head, text=tr('身份：学生'), style="BannerNote.TLabel"
        ).pack(side="right", padx=(0, 18))

        card = ttk.Frame(self, style="Card.TFrame", padding=dpi.P(30))
        card.pack(padx=dpi.P(60), pady=dpi.P(24), fill="both", expand=True)

        fields = [
            (tr('学号'), s["student_id"]),
            (tr('姓名'), s["name"]),
            (tr('性别'), tr(s["gender"])),
            (tr('年龄'), "" if s["age"] is None else str(s["age"])),
            (
                tr('入学年份'),
                "" if s["enroll_year"] is None else str(s["enroll_year"]),
            ),
            (tr('班级'), s.get("class_name") or "—"),
        ]

        row = 0
        for label, value in fields:
            frame = ttk.Frame(card)
            frame.grid(
                row=row, column=0, padx=dpi.P(26), pady=dpi.P(11), sticky="w"
            )
            ttk.Label(
                frame, text=f"{label}：", font=("Microsoft YaHei UI", 11),
                style="Card.TLabel",
            ).pack(side="left")
            ttk.Label(
                frame,
                text=str(value),
                style="CardValue.TLabel",
            ).pack(side="left")
            row += 1

        bottom = ttk.Frame(card, style="Card.TFrame")
        bottom.grid(row=row, column=0, pady=dpi.P((22, 6)))
        if self.scores:
            years = sorted({r["year"] for r in self.scores})
            ttk.Label(
                bottom,
                text=tr('已登记 {} 个年份的成绩：{}').format(len(years), '、'.join(map(str, years))),
                font=("Microsoft YaHei UI", 11),
                style="Card.TLabel",
            ).pack()
            btn_row = ttk.Frame(bottom)
            btn_row.pack(pady=dpi.P((16, 0)))
            ttk.Button(
                btn_row,
                text=tr('查看成绩图表'),
                icon="bar-chart-line-fill",
                command=lambda: ChartDialog(
                    self, [make_person(self.student, self.scores)]
                ),
            ).pack(side="left", padx=dpi.P(8), ipady=dpi.P(4))
            ttk.Button(
                btn_row,
                text=tr('成绩对比'),
                bootstyle="success",
                icon="people-fill",
                command=self.on_compare,
            ).pack(side="left", padx=dpi.P(8), ipady=dpi.P(4))
        else:
            ttk.Label(
                bottom,
                text=tr('暂无成绩记录，请老师登记成绩后再查看图表'),
                foreground="gray",
                style="Card.TLabel",
            ).pack()

    def on_compare(self):
        CompareDialog(self, require_self=True, self_person=make_person(self.student, self.scores))


class StudentChangePasswordDialog(tk.Toplevel):
    """学生修改自己的登录密码。"""

    def __init__(self, parent, student):
        super().__init__(parent)
        self.storage = resolve_storage(parent)
        self.student_id = student["student_id"]
        self.title(tr('修改登录密码'))
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        dialog_header(self, tr('修改登录密码'), tr('学号：{}').format(self.student_id))
        self._build()
        self._center(parent)

    def _center(self, parent):
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _build(self):
        body = ttk.Frame(self, padding=dpi.P(22))
        body.pack(fill="both", expand=True)
        ttk.Label(
            body, text=tr('正在修改学号 {} 的登录密码').format(self.student_id), foreground="gray"
        ).grid(row=0, column=0, columnspan=2, pady=(0, 12))

        self.var_old = tk.StringVar()
        self.var_new = tk.StringVar()
        self.var_confirm = tk.StringVar()

        def add_entry(label, var, row):
            ttk.Label(body, text=label).grid(
                row=row, column=0, padx=6, pady=7, sticky="e"
            )
            ttk.Entry(body, textvariable=var, width=22, show="*").grid(
                row=row, column=1, padx=6, pady=7
            )

        add_entry(tr('原密码：'), self.var_old, 1)
        add_entry(tr('新密码：'), self.var_new, 2)
        add_entry(tr('确认新密码：'), self.var_confirm, 3)
        ttk.Label(
            body, text=tr('密码长度至少 6 位，且需同时包含字母和数字'), foreground="gray"
        ).grid(
            row=4, column=0, columnspan=2, pady=(4, 10)
        )

        btns = ttk.Frame(body)
        btns.grid(row=5, column=0, columnspan=2, pady=(6, 0))
        ttk.Button(btns, text=tr('确定'), width=12, command=self._save).pack(
            side="left", padx=8
        )
        ttk.Button(
            btns, text=tr('取消'), width=12, style="Secondary.TButton",
            command=self.destroy,
        ).pack(side="left", padx=8)
        self.bind("<Return>", lambda e: self._save())
        self.bind("<Escape>", lambda e: self.destroy())
        self.focus_force()

    def _save(self):
        old = self.var_old.get()
        new = self.var_new.get()
        confirm = self.var_confirm.get()
        if new != confirm:
            messagebox.showwarning(tr('提示'), tr('两次输入的新密码不一致'), parent=self)
            return
        try:
            self.storage.change_student_password(self.student_id, old, new)
        except ValueError as exc:
            messagebox.showwarning(tr('无法修改'), str(exc), parent=self)
            return
        except Exception as exc:
            messagebox.showerror(tr('存储错误'), str(exc), parent=self)
            return
        try:
            self.storage.add_log(
                self.student_id, tr('学生'), tr('修改密码'), self.student_id
            )
        except Exception:
            pass
        messagebox.showinfo(tr('成功'), tr('密码已修改，下次登录请使用新密码'), parent=self)
        self.destroy()


class CompareDialog(tk.Toplevel):
    """选择多名学生进行成绩对比。

    require_self=True（学生端）：图表自动包含本人，再从列表中选择其他同学；
    require_self=False（教师端）：任意选择学生，不限人数。
    """

    def __init__(self, parent, require_self=False, self_person=None):
        super().__init__(parent)
        self.storage = resolve_storage(parent)
        self.require_self = require_self
        self.self_person = self_person
        self.title(tr('成绩对比 - 选择学生'))
        self.geometry(dpi.geom(480, 520))
        self.minsize(*dpi.minsz(440, 420))
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        dialog_header(
            self,
            tr('成绩对比'),
            tr('不限人数') if not require_self else tr('自动包含本人'),
        )
        self._build()
        self._center(parent)

    def _center(self, parent):
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _build(self):
        body = ttk.Frame(self, padding=dpi.P(18))
        body.pack(fill="both", expand=True)

        if self.require_self:
            tip = tr('图表将自动包含你本人，请在下方选择要对比的同学（可多选，不限人数）。')
        else:
            tip = tr('请选择要对比的学生（按住 Ctrl/Shift 可多选，不限人数）。')
        ttk.Label(body, text=tip, foreground="gray", wraplength=430).pack(
            anchor="w", pady=(0, 10)
        )

        list_frame = ttk.Frame(body)
        list_frame.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(
            list_frame,
            selectmode="extended",
            font=("Microsoft YaHei UI", 10),
            exportselection=False,
        )
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        try:
            self.students = self.storage.list_students()
        except Exception as exc:
            self.students = []
            messagebox.showerror(tr('存储错误'), str(exc), parent=self)

        exclude = None
        if self.self_person:
            exclude = self.self_person["student_id"]
        self.students = [
            s for s in self.students if s["student_id"] != exclude
        ]
        for s in self.students:
            self.listbox.insert("end", f"{s['student_id']}　{s['name']}")

        if not self.students:
            ttk.Label(body, text=tr('没有可对比的其他学生'), foreground="gray").pack(
                pady=(10, 0)
            )

        btns = ttk.Frame(body)
        btns.pack(fill="x", pady=(14, 0))
        ttk.Button(btns, text=tr('开始对比'), command=self._confirm).pack(
            side="left", padx=(0, 8), ipady=3
        )
        ttk.Button(btns, text=tr('取消'), command=self.destroy).pack(side="left")
        self.bind("<Return>", lambda e: self._confirm())
        self.bind("<Escape>", lambda e: self.destroy())

    def _confirm(self):
        indexes = self.listbox.curselection()
        selected = [self.students[i] for i in indexes]
        persons = []
        if self.require_self:
            persons.append(self.self_person)
        for s in selected:
            try:
                scores = self.storage.get_scores(s["student_id"])
            except Exception as exc:
                messagebox.showerror(tr('存储错误'), str(exc), parent=self)
                return
            if not scores:
                messagebox.showinfo(
                    tr('提示'), tr('{}（{}）暂无成绩，已跳过').format(s['name'], s['student_id']), parent=self
                )
                continue
            persons.append(make_person(s, scores))

        if self.require_self:
            if len(persons) < 2:
                messagebox.showwarning(
                    tr('提示'), tr('请至少选择一名有成绩的同学进行对比'), parent=self
                )
                return
        else:
            if not persons:
                messagebox.showwarning(tr('提示'), tr('请至少选择一名有成绩的学生'), parent=self)
                return
        parent = self.master
        self.destroy()
        ChartDialog(parent=parent, persons=persons)


class ChartDialog(tk.Toplevel):
    """成绩图表窗口：支持多人对比（雷达图/折线图同时显示多人数据）。"""

    def __init__(self, parent, persons):
        super().__init__(parent)
        self.persons = persons
        self.years = sorted(
            {r["year"] for p in persons for r in p["scores"]}
        )
        names = "、".join(p["name"] for p in persons)
        self.title(tr('成绩图表 - {}').format(names))
        self.geometry(dpi.geom(780, 600))
        self.minsize(*dpi.minsz(680, 520))
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        dialog_header(self, tr('成绩图表'), names)
        self._build()
        self._center(parent)

    def _center(self, parent):
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(
            f"{self.winfo_width()}x{self.winfo_height()}+{max(x, 0)}+{max(y, 0)}"
        )

    def _build(self):
        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        radar_tab = ttk.Frame(notebook)
        line_tab = ttk.Frame(notebook)
        notebook.add(radar_tab, text=tr('雷达图（各科成绩）'))
        notebook.add(line_tab, text=tr('折线图（单科走势）'))

        self._build_radar_tab(radar_tab)
        self._build_line_tab(line_tab)

    # ------------------------------------------------------------ 雷达图

    def _build_radar_tab(self, tab):
        config = ttk.Frame(tab, padding=dpi.P((10, 10)))
        config.pack(fill="x")
        ttk.Label(config, text=tr('选择年份：')).pack(side="left")
        self.radar_year_var = tk.StringVar(value=str(self.years[-1]))
        ttk.Combobox(
            config,
            textvariable=self.radar_year_var,
            values=[str(y) for y in self.years],
            state="readonly",
            width=10,
        ).pack(side="left", padx=(0, 10))
        ttk.Button(config, text=tr('生成雷达图'), command=self.draw_radar).pack(
            side="left"
        )
        ttk.Label(
            config,
            text=tr('雷达图显示所选年份各人的语文/数学/英语成绩'),
            foreground="gray",
        ).pack(side="left", padx=14)

        self.radar_canvas_frame = ttk.Frame(tab)
        self.radar_canvas_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def draw_radar(self):
        year = int(self.radar_year_var.get())
        subject_keys = list(SUBJECTS.keys())
        labels = [tr(k) for k in subject_keys]
        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        angles_closed = angles + angles[:1]

        fig = Figure(figsize=(5.6, 4.8), dpi=100)
        ax = fig.add_subplot(111, polar=True)
        ax.set_theta_offset(np.pi / 2)
        ax.set_theta_direction(-1)
        ax.set_xticks(angles)
        ax.set_xticklabels(labels, fontsize=12)
        ax.set_rlim(0, 150)
        ax.set_yticks([50, 100, 150])
        ax.set_yticklabels(["50", "100", "150"], fontsize=9, color="gray")
        ax.set_title(tr('{} 年各科成绩对比').format(year), fontsize=13, pad=18)

        drawn = 0
        for person in self.persons:
            row = next((r for r in person["scores"] if r["year"] == year), None)
            if row is None:
                continue
            values = [
                float(row[SUBJECTS[k]]) if row[SUBJECTS[k]] is not None else 0.0
                for k in subject_keys
            ]
            color = COLORS[drawn % len(COLORS)]
            ax.plot(
                angles_closed,
                values + values[:1],
                color=color,
                linewidth=2,
                label=f"{person['name']}（{person['student_id']}）",
            )
            ax.fill(angles_closed, values + values[:1], color=color, alpha=0.12)
            if len(self.persons) == 1:
                for angle, value in zip(angles, values):
                    ax.annotate(
                        f"{value:.1f}",
                        xy=(angle, value),
                        xytext=(angle, value + 14),
                        ha="center",
                        fontsize=10,
                        color="#12407f",
                    )
            drawn += 1

        if drawn == 0:
            messagebox.showwarning(
                tr('提示'), tr('所选人员在 {year} 年都没有成绩记录').format(year=year), parent=self
            )
            return
        ax.legend(loc="lower right", bbox_to_anchor=(1.18, -0.08), fontsize=9)
        self._show(self.radar_canvas_frame, fig)

    # ------------------------------------------------------------ 折线图

    def _build_line_tab(self, tab):
        config = ttk.Frame(tab, padding=dpi.P((10, 10)))
        config.pack(fill="x")
        ttk.Label(config, text=tr('选择科目：')).pack(side="left")
        self.line_subject_var = tk.StringVar(value=tr('语文'))
        ttk.Combobox(
            config,
            textvariable=self.line_subject_var,
            values=[tr(k) for k in SUBJECTS],
            state="readonly",
            width=10,
        ).pack(side="left", padx=(0, 10))
        ttk.Button(config, text=tr('生成折线图'), command=self.draw_line).pack(
            side="left"
        )
        ttk.Label(
            config,
            text=tr('折线图显示各人该科目历年的成绩走势'),
            foreground="gray",
        ).pack(side="left", padx=14)

        self.line_canvas_frame = ttk.Frame(tab)
        self.line_canvas_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def draw_line(self):
        subject = self.line_subject_var.get()
        key = next(SUBJECTS[k] for k in SUBJECTS if tr(k) == subject)

        fig = Figure(figsize=(5.6, 4.8), dpi=100)
        ax = fig.add_subplot(111)
        all_years = []
        drawn = 0
        for person in self.persons:
            sorted_scores = sorted(person["scores"], key=lambda r: r["year"])
            years = [r["year"] for r in sorted_scores]
            values = [
                float(r[key]) if r[key] is not None else float("nan")
                for r in sorted_scores
            ]
            if not any(not np.isnan(v) for v in values):
                continue
            color = COLORS[drawn % len(COLORS)]
            ax.plot(
                years,
                values,
                marker="o",
                color=color,
                linewidth=2,
                markersize=6,
                label=f"{person['name']}（{person['student_id']}）",
            )
            if len(self.persons) == 1:
                for x, y in zip(years, values):
                    if not np.isnan(y):
                        ax.annotate(
                            f"{y:.1f}",
                            xy=(x, y),
                            xytext=(0, 8),
                            textcoords="offset points",
                            ha="center",
                            fontsize=9,
                        )
            all_years.extend(years)
            drawn += 1

        if drawn == 0:
            messagebox.showwarning(tr('提示'), tr('所选人员都还没有{}成绩').format(subject), parent=self)
            return
        if all_years:
            ax.set_xticks(sorted(set(all_years)))
            ax.set_xticklabels([str(y) for y in sorted(set(all_years))])
        ax.set_ylim(0, 160)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.set_title(tr('{}成绩对比').format(subject), fontsize=13)
        ax.set_xlabel(tr('年份'))
        ax.set_ylabel(tr('成绩'))
        ax.legend(loc="best", fontsize=9)
        self._show(self.line_canvas_frame, fig)

    # ------------------------------------------------------------ 通用

    @staticmethod
    def _clear(frame):
        for child in frame.winfo_children():
            child.destroy()

    def _show(self, frame, fig):
        self._clear(frame)
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
