"""桌面 GUI：预览迷宫、方向键移动、点击自动寻路、轨迹开关、保存图片。"""

from __future__ import annotations

import sys
import tkinter as tk
from collections import deque
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .config import SIZE_LABELS, Settings, load_settings
from .generator import DIRECTIONS, WALL_N, WALL_W, generate_maze
from .pathfinding import find_path
from .renderer import render_to_file

ALGORITHM_LABELS = {
    "recursive_backtracker": "递归回溯",
    "randomized_prim": "随机 Prim",
}
UI_FONT = "Microsoft YaHei UI"
KEY_TO_DIRECTION = {
    "up": "n",
    "down": "s",
    "left": "w",
    "right": "e",
}


def enable_dpi_awareness() -> None:
    """在创建窗口前启用 Windows DPI 感知，避免界面与字体模糊。"""
    if sys.platform != "win32":
        return
    try:
        import ctypes

        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 系统 DPI 感知
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


class MazeApp:
    """迷宫生成器主窗口。"""

    def __init__(self, root: tk.Tk, settings: Settings) -> None:
        self.root = root
        self.settings = settings
        self.style = settings.style
        self.maze = None
        self.green = (0, 0)  # 绿色色块（玩家）位置
        self.red = None  # 红色色块（终点）位置
        self._target: tuple[int, int] | None = None  # 自动寻路目标（高亮）
        self._path: deque[tuple[int, int]] = deque()
        self._anim_job: str | None = None
        self._anim_speed_ms = 55
        self._paused = False
        self._resize_job: str | None = None
        self._trail: list[tuple[int, int]] = []
        self._dialog: tk.Toplevel | None = None

        root.title(f"迷宫生成器 v{__version__}（平面俯瞰）")
        root.geometry("980x760")
        root.minsize(720, 520)
        root.option_add("*Font", (UI_FONT, 10))
        self._style = ttk.Style(root)
        self._style.configure(".", font=(UI_FONT, 10))

        self._build_toolbar()
        self._build_canvas()
        root.update_idletasks()  # 先完成布局，让首次绘制按真实画布尺寸缩放
        self.regenerate()

        # 键盘绑定在根窗口上，点击画布后依然生效
        root.bind("<Up>", self._on_arrow)
        root.bind("<Down>", self._on_arrow)
        root.bind("<Left>", self._on_arrow)
        root.bind("<Right>", self._on_arrow)
        root.bind("<space>", self._on_space)

    # ---------- 界面搭建 ----------

    def _build_toolbar(self) -> None:
        bar = ttk.Frame(self.root, padding=(8, 6))
        bar.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(bar, text="规模:").pack(side=tk.LEFT)
        self.size_var = tk.StringVar(value=SIZE_LABELS[self.settings.size_preset])
        self.size_combo = ttk.Combobox(
            bar,
            textvariable=self.size_var,
            values=list(SIZE_LABELS.values()),
            state="readonly",
            width=8,
            takefocus=0,
        )
        self.size_combo.pack(side=tk.LEFT, padx=(2, 10))

        ttk.Label(bar, text="种子(留空=随机):").pack(side=tk.LEFT)
        self.seed_var = tk.StringVar(
            value="" if self.settings.seed is None else str(self.settings.seed)
        )
        ttk.Entry(
            bar,
            textvariable=self.seed_var,
            width=10,
            validate="key",
            validatecommand=(self.root.register(self._validate_seed), "%P"),
        ).pack(
            side=tk.LEFT, padx=(2, 10)
        )

        ttk.Label(bar, text="算法:").pack(side=tk.LEFT)
        self.alg_var = tk.StringVar(value=ALGORITHM_LABELS[self.settings.algorithm])
        self.alg_combo = ttk.Combobox(
            bar,
            textvariable=self.alg_var,
            values=list(ALGORITHM_LABELS.values()),
            state="readonly",
            width=10,
            takefocus=0,
        )
        self.alg_combo.pack(side=tk.LEFT, padx=(2, 10))

        # 工具栏控件不接收键盘焦点：空格键只控制色块移动，不会触发按钮
        ttk.Button(
            bar, text="重新生成迷宫", command=self._ask_regenerate, takefocus=0
        ).pack(side=tk.LEFT, padx=4)
        ttk.Button(bar, text="保存图片", command=self.save_image, takefocus=0).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(
            bar, text="重新加载设置", command=self.reload_settings, takefocus=0
        ).pack(side=tk.LEFT, padx=4)

        self.trail_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            bar,
            text="显示移动轨迹",
            variable=self.trail_var,
            command=self._toggle_trail,
            takefocus=0,
        ).pack(side=tk.LEFT, padx=(10, 2))

        self.info_var = tk.StringVar(value="")
        ttk.Label(bar, textvariable=self.info_var).pack(side=tk.LEFT, padx=12)

        ttk.Label(
            bar, text="方向键移动 · 点击自动寻路 · 空格暂停", foreground="#666666"
        ).pack(side=tk.RIGHT)

    def _build_canvas(self) -> None:
        frame = ttk.Frame(self.root)
        frame.pack(fill=tk.BOTH, expand=True)
        self.canvas = tk.Canvas(frame, bg=self.style.background, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.configure(cursor="crosshair")

    # ---------- 弹窗 ----------

    def _make_dialog(self, title: str) -> tk.Toplevel:
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.protocol("WM_DELETE_WINDOW", self._close_dialog)
        self._dialog = dlg
        self._center_dialog(dlg)
        return dlg

    def _center_dialog(self, dlg: tk.Toplevel) -> None:
        dlg.update_idletasks()
        w = dlg.winfo_reqwidth()
        h = dlg.winfo_reqheight()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - h) // 3
        dlg.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _close_dialog(self) -> None:
        if self._dialog is not None:
            dlg = self._dialog
            self._dialog = None
            dlg.grab_release()
            dlg.destroy()

    def _show_confirm(self, title: str, message: str, on_yes) -> None:
        """通用确认弹窗：是 -> 执行 on_yes；否 -> 仅关闭。"""
        if self._dialog is not None:
            return
        dlg = self._make_dialog(title)
        ttk.Label(dlg, text=message, justify="center").pack(padx=30, pady=(22, 14))
        btns = ttk.Frame(dlg)
        btns.pack(pady=(0, 18))

        def yes() -> None:
            self._close_dialog()
            on_yes()

        ttk.Button(btns, text="是", width=10, command=yes).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="否", width=10, command=self._close_dialog).pack(
            side=tk.LEFT, padx=6
        )

    def _ask_regenerate(self) -> None:
        self._show_confirm(
            "重新生成迷宫",
            "确定要重新生成迷宫吗？\n（绿色色块的位置将被重置）",
            on_yes=self.regenerate,
        )

    def _show_success_dialog(self) -> None:
        if self._dialog is not None or self.maze is None:
            return
        dlg = self._make_dialog("寻路成功")
        ttk.Label(
            dlg, text="本次寻路成功！", font=(UI_FONT, 14, "bold"), foreground="#1f7a3d"
        ).pack(padx=34, pady=(24, 6))
        gx, gy = self.green
        ttk.Label(
            dlg,
            text=(
                f"迷宫 {self.maze.width} x {self.maze.height}\n"
                f"绿色色块到达终点 ({gx}, {gy})"
            ),
            justify="center",
            foreground="#555555",
        ).pack(pady=(0, 16))
        btns = ttk.Frame(dlg)
        btns.pack(pady=(0, 20))
        ttk.Button(
            btns, text="下一场游戏（重新生成）", command=self._next_game
        ).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="关闭", width=10, command=self._close_dialog).pack(
            side=tk.LEFT, padx=6
        )

    def _next_game(self) -> None:
        self._close_dialog()
        self.regenerate()

    # ---------- 迷宫生成与绘制 ----------

    def regenerate(self) -> None:
        self._cancel_animation()
        preset = self._current_preset()
        try:
            seed = self._resolve_seed()
            algorithm = next(
                k for k, v in ALGORITHM_LABELS.items() if v == self.alg_var.get()
            )
            self.maze = generate_maze(
                preset.width, preset.height, algorithm=algorithm, seed=seed
            )
        except ValueError as exc:
            messagebox.showerror("生成失败", str(exc))
            return
        self.green = (0, 0)
        self.red = (self.maze.width - 1, self.maze.height - 1)
        self._target = None
        self._trail = []
        self._draw_maze()
        self.info_var.set(self._status_text())

    def _status_text(self) -> str:
        gx, gy = self.green
        return (
            f"{self.maze.width} x {self.maze.height} · 算法={self.maze.algorithm} · "
            f"种子={self.maze.seed} · 绿块 ({gx},{gy})"
        )

    def _compute_layout(self) -> tuple[int, int, int, int]:
        """按当前画布尺寸计算等比缩放后的格子大小、墙厚与居中偏移。"""
        preset = self._current_preset()
        pad = 10
        avail_w = max(80, self.canvas.winfo_width())
        avail_h = max(80, self.canvas.winfo_height())
        usable_w = avail_w - pad * 2
        usable_h = avail_h - pad * 2
        base_cell = max(2, preset.cell_size)
        base_wall = max(1, self.style.wall_width)
        base_w = self.maze.width * base_cell
        base_h = self.maze.height * base_cell
        scale = min(usable_w / base_w, usable_h / base_h)
        scale = max(0.1, min(scale, 3.0))
        cell = max(2, int(base_cell * scale))
        wall = max(1, round(base_wall * scale))
        maze_w = self.maze.width * cell
        maze_h = self.maze.height * cell
        offset_x = pad + (usable_w - maze_w) // 2
        offset_y = pad + (usable_h - maze_h) // 2
        return cell, wall, offset_x, offset_y

    def _draw_maze(self) -> None:
        if self.maze is None:
            return
        self.canvas.delete("all")
        cell, wall, ox, oy = self._compute_layout()
        fg = self.style.wall_color
        inner = cell - wall  # 通道内径

        # 墙体用矩形填充绘制，边缘锐利无锯齿
        for y in range(self.maze.height):
            for x in range(self.maze.width):
                px = ox + x * cell
                py = oy + y * cell
                walls = self.maze.walls[y][x]
                if walls & WALL_N:
                    self.canvas.create_rectangle(
                        px, py, px + cell, py + wall, fill=fg, outline=""
                    )
                if walls & WALL_W:
                    self.canvas.create_rectangle(
                        px, py, px + wall, py + cell, fill=fg, outline=""
                    )

        right = ox + self.maze.width * cell
        bottom = oy + self.maze.height * cell
        self.canvas.create_rectangle(
            right - wall, oy, right, bottom, fill=fg, outline=""
        )
        self.canvas.create_rectangle(
            ox, bottom - wall, right, bottom, fill=fg, outline=""
        )

        # 移动轨迹
        if self.trail_var.get() and self._trail:
            for tx, ty in self._trail:
                self.canvas.create_rectangle(
                    ox + tx * cell + wall,
                    oy + ty * cell + wall,
                    ox + (tx + 1) * cell,
                    oy + (ty + 1) * cell,
                    fill=self.style.trail_color,
                    outline="",
                )

        # 自动寻路目标高亮
        if self._target is not None:
            tx, ty = self._target
            self.canvas.create_rectangle(
                ox + tx * cell + wall,
                oy + ty * cell + wall,
                ox + (tx + 1) * cell,
                oy + (ty + 1) * cell,
                fill="#dceefc",
                outline="",
            )

        # 终点（红色）与玩家（绿色，最后绘制盖在上面）
        if self.red is not None:
            self._draw_marker(self.red, self.style.end_color, cell, wall, ox, oy)
        self._draw_marker(self.green, self.style.start_color, cell, wall, ox, oy)

    def _draw_marker(
        self, pos: tuple[int, int], color: str, cell: int, wall: int, ox: int, oy: int
    ) -> None:
        mx, my = pos
        inner = cell - wall
        size = max(3, int(inner * self.style.start_size_ratio))
        px = ox + mx * cell + wall + (inner - size) // 2
        py = oy + my * cell + wall + (inner - size) // 2
        self.canvas.create_rectangle(
            px, py, px + size, py + size, fill=color, outline=""
        )

    def _on_canvas_resize(self, _event) -> None:
        """窗口大小变化时防抖重绘，实现等比缩放与居中。"""
        if self._resize_job is not None:
            self.root.after_cancel(self._resize_job)
        self._resize_job = self.root.after(50, self._redraw_after_resize)

    def _redraw_after_resize(self) -> None:
        self._resize_job = None
        if self.maze is not None:
            self._draw_maze()

    # ---------- 移动：方向键 / 自动寻路 / 暂停 ----------

    def _stop_anim_job(self) -> None:
        """仅取消排队的动画任务，不影响暂停状态。"""
        if self._anim_job is not None:
            self.root.after_cancel(self._anim_job)
            self._anim_job = None

    def _move_green(self, new_pos: tuple[int, int]) -> None:
        """移动绿块并记录轨迹、重绘。"""
        self.green = new_pos
        if self.trail_var.get():
            if not self._trail or self._trail[-1] != new_pos:
                self._trail.append(new_pos)
        self._draw_maze()

    def _on_arrow(self, event) -> str:
        if self._dialog is not None or self.maze is None:
            return "break"
        if self._anim_job is not None:
            return "break"  # 自动寻路动画进行中，先暂停或等待
        direction = KEY_TO_DIRECTION.get(event.keysym.lower())
        if direction is None:
            return "break"
        gx, gy = self.green
        dx, dy, here, _there = DIRECTIONS[direction]
        if self.maze.walls[gy][gx] & here:
            return "break"  # 有墙，不能通过
        nx, ny = gx + dx, gy + dy
        if not self.maze.in_bounds(nx, ny):
            return "break"
        if self._paused:
            # 暂停中手动移动：清空自动寻路记录并退出暂停
            self._paused = False
            self._path.clear()
            self._target = None
        self._move_green((nx, ny))
        self.info_var.set(self._status_text())
        self._check_success()
        return "break"

    def _on_space(self, event) -> str:
        """空格：暂停 / 继续当前移动动画。"""
        if self._dialog is not None or self.maze is None:
            return "break"
        if self._anim_job is None and not self._paused:
            return "break"  # 当前没有正在移动的色块
        if not self._paused:
            self._paused = True
            if self._anim_job is not None:
                self.root.after_cancel(self._anim_job)
                self._anim_job = None
            self.info_var.set("移动已暂停，按空格继续")
        else:
            self._paused = False
            self.info_var.set(self._status_text())
            self._step_animation()  # 继续
        return "break"

    def _on_canvas_click(self, event) -> None:
        if self._dialog is not None or self.maze is None:
            return
        cell, _wall, ox, oy = self._compute_layout()
        cx = int(self.canvas.canvasx(event.x))  # 考虑滚动偏移
        cy = int(self.canvas.canvasy(event.y))
        x = (cx - ox) // cell
        y = (cy - oy) // cell
        if not self.maze.in_bounds(x, y):
            return
        target = (x, y)
        if target == self.green:
            return
        path = find_path(self.maze, self.green, target)
        if path is None:
            messagebox.showinfo("此路不通", "无法到达该位置！")
            return
        self._target = target
        if self._paused:
            # 暂停中：只记录新路径与目标，按空格后开始移动
            self._stop_anim_job()
            self._path = deque(path[1:])
            self._draw_maze()
            self.info_var.set(f"已选择新目标 ({x}, {y})，按空格开始移动")
            return
        self.info_var.set(f"寻路中... 目标 ({x}, {y})")
        self._start_animation(path)

    def _start_animation(self, path: list[tuple[int, int]]) -> None:
        self._cancel_animation()
        self._path = deque(path[1:])
        self._step_animation()

    def _step_animation(self) -> None:
        if self.maze is None:
            self._anim_job = None
            return
        if self._paused:
            self._anim_job = None
            return
        if self._path:
            self._move_green(self._path.popleft())
            self._anim_job = self.root.after(self._anim_speed_ms, self._step_animation)
            return
        self._anim_job = None
        self._paused = False
        self._target = None
        self._draw_maze()
        self.info_var.set(self._status_text())
        self._check_success()

    def _cancel_animation(self) -> None:
        self._stop_anim_job()
        self._paused = False
        self._path.clear()

    def _check_success(self) -> None:
        if self.green == self.red:
            self._show_success_dialog()

    # ---------- 移动轨迹开关 ----------

    def _toggle_trail(self) -> None:
        if self.trail_var.get():
            # 重新开启：以当前位置为起点，开始新的轨迹
            if not self._trail and self.green is not None:
                self._trail = [self.green]
        else:
            self._trail = []  # 清空轨迹记录
        self._draw_maze()

    # ---------- 其他 ----------

    def save_image(self) -> None:
        if self.maze is None:
            return
        preset = self._current_preset()
        path = filedialog.asksaveasfilename(
            title="保存迷宫图片",
            defaultextension=".png",
            filetypes=[("PNG 图片", "*.png")],
            initialfile=self.settings.output_name,
        )
        if not path:
            return
        try:
            render_to_file(self.maze, self.style, preset.cell_size, path)
        except OSError as exc:
            messagebox.showerror("保存失败", str(exc))
            return
        messagebox.showinfo("保存成功", f"已保存到：\n{path}")

    def reload_settings(self) -> None:
        try:
            self.settings = load_settings()
        except (OSError, ValueError) as exc:
            messagebox.showerror("设置加载失败", str(exc))
            return
        self.style = self.settings.style
        self.size_var.set(SIZE_LABELS[self.settings.size_preset])
        self.alg_var.set(ALGORITHM_LABELS[self.settings.algorithm])
        self.canvas.configure(bg=self.style.background)
        self.regenerate()

    # ---------- 便捷方法 ----------

    def _current_preset(self):
        label = self.size_var.get()
        for key, text in SIZE_LABELS.items():
            if text == label:
                return self.settings.presets[key]
        return self.settings.get_preset()

    def _resolve_seed(self) -> int | None:
        text = self.seed_var.get().strip()
        if not text:
            return None
        return int(text)

    def _validate_seed(self, text: str) -> bool:
        """种子输入框只允许数字（留空表示随机）。"""
        return text == "" or text.isdigit()
