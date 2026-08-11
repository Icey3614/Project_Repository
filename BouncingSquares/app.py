"""桌宠模式主程序：多方块铺满整个屏幕运动，支持碰撞、拖拽、序号管理。"""
from __future__ import annotations

import colorsys
import math
import random
import time
import tkinter as tk

from settings_dialog import AdjustPopup
from win_utils import (
    TRANSPARENT_COLOR,
    apply_desktop_pet_styles,
    position_window,
    virtual_screen,
)

FONT_FAMILY = "Microsoft YaHei UI"

GRAVITY_ACCEL = 1200.0  # 重力加速度（像素/秒²）


class Square:
    """单个方块：位置、速度、色相，以及可选的逐方块覆盖配置（含重量）。"""

    __slots__ = ("x", "y", "vx", "vy", "hue", "size", "speed", "color", "weight")

    def __init__(self, x: float, y: float, vx: float, vy: float, hue: float = 0.0,
                 size: float | None = None, speed: float | None = None,
                 color: str | None = None, weight: float | None = None):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.hue = hue
        self.size = size
        self.speed = speed
        self.color = color
        self.weight = weight


class BounceApp:
    """管理多个方块在透明全屏 Canvas 上的运动与交互。"""

    TICK_MS = 16  # 约 60 FPS
    DRAG_THRESHOLD = 4  # 位移超过该像素数才算拖动，否则视为点击
    DISPLAY_POLL_MS = 1000  # 显示器配置检查间隔（热插拔自适应）
    MAX_SQUARES = 20

    def __init__(self, root: tk.Tk, settings: dict,
                 screen_rect: tuple[int, int, int, int] | None = None) -> None:
        self.root = root
        self.settings = settings
        self._screen_rect = screen_rect
        self.size = float(settings["size"])
        self.speed = float(settings["speed"])
        self.color = str(settings.get("color", "#4c8bf5"))
        self.random_color = bool(settings.get("random_color", False))
        self.gravity = bool(settings.get("gravity", False))
        self.space_paused = str(settings.get("space_paused", "none"))

        self.canvas = tk.Canvas(root, bg=TRANSPARENT_COLOR, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        # 禁止打包器按内容重算窗口尺寸，窗口大小完全由外部几何/SetWindowPos 控制
        self.root.pack_propagate(False)

        self.width = 1
        self.height = 1
        self._initialized = False
        self._running = True
        self._last_time = time.monotonic()
        self._saved_state: tuple | None = None
        self._press_pos: tuple[int, int] | None = None
        self._dragged = False
        self._drag_index: int | None = None
        self._drag_was_running = False
        self._drag_dx = 0.0
        self._drag_dy = 0.0
        self._after_id: str | None = None
        self._display_poll_id: str | None = None
        self.squares: list[Square] = []

        self.canvas.bind("<Configure>", self._on_resize)
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_right_click)
        self.root.bind("<Unmap>", self._on_minimize)
        self.root.bind("<Map>", self._on_restore)
        self.root.bind("<Escape>", lambda _e: self.root.destroy())
        self.root.bind("<space>", self._on_space)

        self._draw()
        self._after_id = self.root.after(self.TICK_MS, self._tick)
        self._display_poll_id = self.root.after(self.DISPLAY_POLL_MS, self._poll_display)

    # ---------- 初始化 / 布局 ----------

    def _on_resize(self, _event: tk.Event | None = None) -> None:
        self.width = max(self.canvas.winfo_width(), 1)
        self.height = max(self.canvas.winfo_height(), 1)
        if not self._initialized and self.width > 1 and self.height > 1:
            self._initialized = True
            self._create_initial_squares()
        else:
            r = self.size / 2
            for sq in self.squares:
                sq.x = min(max(sq.x, r), self.width - r)
                sq.y = min(max(sq.y, r), self.height - r)

    def _create_initial_squares(self) -> None:
        """初始在屏幕中央集中创建方块，互不重叠。"""
        count = max(1, int(self.settings.get("count", 1)))
        overrides = self.settings.get("squares") or []
        # 环半径按最大方块尺寸计算，保证大小不同的方块初始也不重叠
        max_size = self.size
        for cfg in overrides[:count]:
            if cfg and cfg.get("size"):
                max_size = max(max_size, float(cfg["size"]))
        self.squares = []
        for i in range(count):
            x, y = self._ring_position(i, count, max_size)
            cfg = overrides[i] if i < len(overrides) else None
            vx, vy = self._velocity_for(
                i, count,
                angle=cfg.get("angle") if cfg else None,
                speed=cfg.get("speed") if cfg else None,
            )
            self.squares.append(Square(
                x, y, vx, vy, hue=random.random(),
                size=cfg.get("size") if cfg else None,
                speed=cfg.get("speed") if cfg else None,
                color=cfg.get("color") if cfg else None,
                weight=cfg.get("weight") if cfg else None,
            ))

    def _ring_position(self, index: int, count: int,
                       ring_size: float | None = None) -> tuple[float, float]:
        """把方块均匀排布在以屏幕中心为圆心的环上，保证互不重叠。"""
        cx, cy = self.width / 2, self.height / 2
        if count == 1:
            return cx, cy
        size = ring_size if ring_size is not None else self.size
        radius = (size / (2 * math.sin(math.pi / count))) * 1.02
        angle = 2 * math.pi * index / count - math.pi / 2
        r = size / 2
        x = min(max(cx + radius * math.cos(angle), r), self.width - r)
        y = min(max(cy + radius * math.sin(angle), r), self.height - r)
        return x, y

    def _velocity_for(self, index: int, count: int,
                      angle: float | None = None,
                      speed: float | None = None) -> tuple[float, float]:
        """按设置计算速度向量；多方块固定角度时自动分散，避免平行同向。"""
        if self.settings.get("random") and angle is None:
            angle = random.uniform(0.0, 360.0)
        else:
            base = float(angle if angle is not None else self.settings.get("angle", 45.0))
            angle = base + index * (360.0 / max(count, 1))
        angle = math.radians(angle % 360)
        spd = float(speed if speed is not None else self.speed)
        return spd * math.cos(angle), spd * math.sin(angle)

    # ---------- 逐方块取值（有覆盖用覆盖，否则用全局） ----------

    def _size_of(self, sq: Square) -> float:
        return float(sq.size) if sq.size else self.size

    def _speed_of(self, sq: Square) -> float:
        return float(sq.speed) if sq.speed else self.speed

    def _color_of(self, sq: Square) -> str:
        return sq.color if sq.color else self.color

    def _weight_of(self, sq: Square) -> float:
        return float(sq.weight) if sq.weight else 1.0

    # ---------- 运动 ----------

    def _tick(self) -> None:
        now = time.monotonic()
        dt = now - self._last_time
        self._last_time = now
        if self._running:
            self._move(dt)
        self._draw()
        self._after_id = self.root.after(self.TICK_MS, self._tick)

    def _move(self, dt: float) -> None:
        if self.random_color:
            for sq in self.squares:
                sq.hue = (sq.hue + dt * 0.35) % 1.0

        # 细分时间步：防止大尺寸/高速方块“嵌入”对方后才反弹，
        # 也防止小方块高速时直接穿过对方（隧穿）
        if self.squares:
            max_speed = max(abs(sq.vx) + abs(sq.vy) for sq in self.squares)
            travel = max_speed * 2 * dt  # 两方块相对接近的最坏距离
            step_target = max(self.size * 0.1, 2.0)  # 每子步移动不超过尺寸的 1/10
            substeps = math.ceil(travel / step_target) if travel > 0 else 1
            # 保证单个子步绝不会跨过整个方块（防隧穿）
            substeps = max(substeps, math.ceil(travel / max(self.size, 1.0)) + 1)
            substeps = min(substeps, 32)
        else:
            substeps = 1
        sub_dt = dt / substeps

        # 先解决上一帧遗留/拖拽放下造成的重叠，避免“先穿过再反弹”
        self._resolve_collisions()

        for _ in range(substeps):
            for idx, sq in enumerate(self.squares):
                if idx == self._drag_index:
                    continue  # 拖动中的方块位置由鼠标控制
                if self.gravity:
                    sq.vy += GRAVITY_ACCEL * sub_dt
                sq.x += sq.vx * sub_dt
                sq.y += sq.vy * sub_dt
                r = self._size_of(sq) / 2

                if sq.x - r < 0:
                    sq.x = 2 * r - sq.x
                    sq.vx = abs(sq.vx)
                elif sq.x + r > self.width:
                    sq.x = 2 * (self.width - r) - sq.x
                    sq.vx = -abs(sq.vx)

                # 上下边界完全弹性反弹（动能守恒，无衰减）
                if sq.y - r < 0:
                    sq.y = 2 * r - sq.y
                    sq.vy = abs(sq.vy)
                elif sq.y + r > self.height:
                    sq.y = 2 * (self.height - r) - sq.y
                    sq.vy = -abs(sq.vy)

            self._resolve_collisions()

    def _resolve_collisions(self) -> None:
        """方块两两弹性碰撞（质量按面积，逐方块尺寸）。

        只要发生重叠就立即处理：先按法线交换法向速度（完全弹性，
        动能守恒），再把双方完全分离到恰好接触，杜绝可见重叠。
        """
        n = len(self.squares)
        for i in range(n):
            if i == self._drag_index:
                continue
            a = self.squares[i]
            for j in range(i + 1, n):
                if j == self._drag_index:
                    continue
                b = self.squares[j]
                ra = self._size_of(a) / 2
                rb = self._size_of(b) / 2
                min_dist = ra + rb
                dx = b.x - a.x
                dy = b.y - a.y
                dist = math.hypot(dx, dy)
                if dist >= min_dist:
                    continue
                if dist > 1e-6:
                    nx, ny = dx / dist, dy / dist
                else:
                    # 完全重合：用默认法线，接近判定会自动交换速度并分离
                    nx, ny = 1.0, 0.0
                v1n = a.vx * nx + a.vy * ny
                v2n = b.vx * nx + b.vy * ny
                if v2n - v1n < 0:  # 正在靠近才反弹
                    ma = self._weight_of(a) * ra * ra  # 质量 = 重量 × 面积
                    mb = self._weight_of(b) * rb * rb
                    v1n2 = ((ma - mb) * v1n + 2 * mb * v2n) / (ma + mb)
                    v2n2 = ((mb - ma) * v2n + 2 * ma * v1n) / (ma + mb)
                    a.vx += (v1n2 - v1n) * nx
                    a.vy += (v1n2 - v1n) * ny
                    b.vx += (v2n2 - v2n) * nx
                    b.vy += (v2n2 - v2n) * ny
                overlap = (min_dist - dist) / 2 if dist > 1e-6 else min_dist / 2
                a.x -= nx * overlap
                a.y -= ny * overlap
                b.x += nx * overlap
                b.y += ny * overlap

    # ---------- 绘制 ----------

    def _draw(self) -> None:
        self.canvas.delete("all")
        for idx, sq in enumerate(self.squares):
            size = self._size_of(sq)
            r = size / 2
            color = self._current_color(sq)
            self.canvas.create_rectangle(
                sq.x - r, sq.y - r, sq.x + r, sq.y + r,
                fill=color, outline="#222222", width=2,
            )
            self.canvas.create_text(
                sq.x, sq.y, text=str(idx + 1),
                fill=self._text_color(color),
                font=(FONT_FAMILY, max(8, int(size / 3))),
            )

    def _current_color(self, sq: Square) -> str:
        if self.random_color:
            rr, gg, bb = colorsys.hsv_to_rgb(sq.hue, 1.0, 1.0)
            return "#%02x%02x%02x" % (int(rr * 255), int(gg * 255), int(bb * 255))
        return self._color_of(sq)

    @staticmethod
    def _text_color(hex_color: str) -> str:
        try:
            r = int(hex_color[1:3], 16)
            g = int(hex_color[3:5], 16)
            b = int(hex_color[5:7], 16)
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            return "#000000" if luminance > 140 else "#ffffff"
        except ValueError:
            return "#ffffff"

    # ---------- 命中 / 交互 ----------

    def _square_at(self, cx: float, cy: float) -> int | None:
        for i, sq in enumerate(self.squares):
            r = self._size_of(sq) / 2
            if abs(cx - sq.x) <= r and abs(cy - sq.y) <= r:
                return i
        return None

    def _in_square(self, screen_x: int, screen_y: int) -> bool:
        """命中测试：屏幕坐标是否落在任一方块上（区域点击/穿透）。"""
        x = screen_x - self.canvas.winfo_rootx()
        y = screen_y - self.canvas.winfo_rooty()
        return self._square_at(x, y) is not None

    def _on_press(self, event: tk.Event) -> None:
        idx = self._square_at(event.x, event.y)
        if idx is None:
            return
        self._drag_index = idx
        self._press_pos = (event.x, event.y)
        self._dragged = False
        self._drag_was_running = self._running
        self._drag_dx = 0.0
        self._drag_dy = 0.0

    def _on_drag(self, event: tk.Event) -> None:
        if self._drag_index is None or self._press_pos is None:
            return
        dx = event.x - self._press_pos[0]
        dy = event.y - self._press_pos[1]
        if not self._dragged and (abs(dx) > self.DRAG_THRESHOLD or abs(dy) > self.DRAG_THRESHOLD):
            self._dragged = True
        if self._dragged:
            sq = self.squares[self._drag_index]
            r = self._size_of(sq) / 2
            sq.x = min(max(event.x, r), self.width - r)
            sq.y = min(max(event.y, r), self.height - r)
            if dx or dy:
                self._drag_dx, self._drag_dy = dx, dy
            self._press_pos = (event.x, event.y)

    def _on_release(self, _event: tk.Event) -> None:
        if self._drag_index is None:
            return
        idx = self._drag_index
        self._drag_index = None
        self._press_pos = None
        if self._dragged:
            sq = self.squares[idx]
            if self._drag_was_running and (self._drag_dx or self._drag_dy):
                # 运动中拖拽：松手后按最后拖动方向运动，速度不变
                speed = math.hypot(sq.vx, sq.vy) or self.speed
                mag = math.hypot(self._drag_dx, self._drag_dy)
                sq.vx = speed * self._drag_dx / mag
                sq.vy = speed * self._drag_dy / mag
            # 暂停中拖拽：只改变位置（已在 _on_drag 中完成）
        else:
            # 单击：暂停 / 继续
            self._running = not self._running
            self._last_time = time.monotonic()
        self._dragged = False

    def _on_right_click(self, _event: tk.Event) -> None:
        """右键方块：先暂停（便于管理），再弹出调整窗口。"""
        self._pause_and_open_popup()

    def _on_space(self, _event: tk.Event | None = None) -> None:
        """空格：运动中暂停并弹出设置界面；暂停时按设置决定是否继续。"""
        if self._running:
            self._pause_and_open_popup()
        elif self.space_paused == "resume":
            self.resume_all()

    def _pause_and_open_popup(self) -> None:
        if self._running:
            self._running = False
            self._last_time = time.monotonic()
        popup = getattr(self, "_popup", None)
        if popup is not None and popup.winfo_exists():
            popup.lift()
            return
        self._popup = AdjustPopup(
            self.root,
            defaults=self._current_settings(),
            on_apply=self._apply_settings,
            on_quit=self.root.destroy,
            on_close_and_run=self.resume_all,
            on_add=self.add_square,
            on_delete=self.delete_square,
            count_getter=lambda: len(self.squares),
            on_square_apply=self.set_square_config,
            on_square_reset=self.reset_square_config,
            space_paused=self.space_paused,
            on_space_paused=self.set_space_paused,
        )

    def resume_all(self) -> None:
        """恢复所有方块运动（用于“关闭并运行”）。"""
        self._running = True
        self._last_time = time.monotonic()

    def set_space_paused(self, value: str) -> None:
        """设置暂停时按空格的行为：none=无操作，resume=继续运行。"""
        self.space_paused = "resume" if value == "resume" else "none"
        self.settings["space_paused"] = self.space_paused

    # ---------- 方块管理 ----------

    def add_square(self) -> int | None:
        """追加一个方块（新序号自动为当前最大序号 +1）。"""
        if len(self.squares) >= self.MAX_SQUARES:
            return None
        x, y = self._find_free_spot()
        count = len(self.squares) + 1
        vx, vy = self._velocity_for(len(self.squares), count)
        self.squares.append(Square(x, y, vx, vy, hue=random.random()))
        return len(self.squares)

    def set_square_config(self, index: int, cfg: dict) -> None:
        """给指定方块设置独立配置（大小/速度/方向/颜色）。"""
        if not 0 <= index < len(self.squares):
            return
        sq = self.squares[index]
        sq.size = float(cfg["size"]) if cfg.get("size") else None
        sq.speed = float(cfg["speed"]) if cfg.get("speed") else None
        sq.color = str(cfg["color"]) if cfg.get("color") else None
        sq.weight = float(cfg["weight"]) if cfg.get("weight") else None
        if cfg.get("angle") is not None:
            angle = math.radians(float(cfg["angle"]) % 360)
            spd = self._speed_of(sq)
            sq.vx = spd * math.cos(angle)
            sq.vy = spd * math.sin(angle)
        r = self._size_of(sq) / 2
        sq.x = min(max(sq.x, r), self.width - r)
        sq.y = min(max(sq.y, r), self.height - r)

    def reset_square_config(self, index: int) -> None:
        """清除指定方块的独立配置，恢复跟随全局设置。"""
        if not 0 <= index < len(self.squares):
            return
        sq = self.squares[index]
        sq.size = None
        sq.speed = None
        sq.color = None
        sq.weight = None
        angle = math.degrees(math.atan2(sq.vy, sq.vx)) % 360
        sq.vx = self.speed * math.cos(math.radians(angle))
        sq.vy = self.speed * math.sin(math.radians(angle))

    def delete_square(self, number: int) -> int | None:
        """按显示序号删除方块；删除后剩余方块自动重新编号。"""
        n = int(number)
        if not 1 <= n <= len(self.squares):
            return None
        del self.squares[n - 1]
        if self._drag_index is not None:
            if self._drag_index == n - 1:
                self._drag_index = None
                self._press_pos = None
                self._dragged = False
            elif self._drag_index > n - 1:
                self._drag_index -= 1
        return len(self.squares)

    def _find_free_spot(self) -> tuple[float, float]:
        """从屏幕中心向外螺旋寻找不与现有方块重叠的位置。"""
        cx, cy = self.width / 2, self.height / 2
        max_size = max([self._size_of(sq) for sq in self.squares] or [self.size])
        r = max_size
        step = max(8, int(max_size))
        for radius in range(0, max(self.width, self.height), step):
            for k in range(24):
                angle = 2 * math.pi * k / 24
                x = cx + radius * math.cos(angle)
                y = cy + radius * math.sin(angle)
                x = min(max(x, r), self.width - r)
                y = min(max(y, r), self.height - r)
                if all(
                    math.hypot(x - sq.x, y - sq.y) >= (self._size_of(sq) + max_size) / 2
                    for sq in self.squares
                ):
                    return x, y
        return cx, cy

    def _current_settings(self) -> dict:
        """当前状态快照，作为调整弹窗的默认值。"""
        first = self.squares[0] if self.squares else None
        angle = math.degrees(math.atan2(first.vy, first.vx)) % 360 if first else 0.0
        return {
            "angle": angle,
            "random": bool(self.settings.get("random", False)),
            "size": int(self.size),
            "speed": float(self.speed),
            "color": self.color,
            "random_color": self.random_color,
            "gravity": bool(self.gravity),
            "space_paused": self.space_paused,
            "count": len(self.squares),
            "squares": [
                ({"size": sq.size, "speed": sq.speed, "color": sq.color,
                  "weight": sq.weight}
                 if sq.size or sq.speed or sq.color or sq.weight else None)
                for sq in self.squares
            ],
        }

    def _apply_settings(self, values: dict) -> None:
        """应用调整弹窗的新参数到所有方块（位置保留）。"""
        self.size = float(values["size"])
        self.speed = float(values["speed"])
        self.color = str(values["color"])
        self.random_color = bool(values["random_color"])
        self.gravity = bool(values.get("gravity", self.gravity))
        self.settings = {**self.settings, **values}
        count = len(self.squares)
        for i, sq in enumerate(self.squares):
            if sq.size or sq.speed or sq.color:
                continue  # 已单独配置的方块保持自己的速度，不受全局参数影响
            sq.vx, sq.vy = self._velocity_for(i, count)
        for sq in self.squares:
            r = self._size_of(sq) / 2
            sq.x = min(max(sq.x, r), self.width - r)
            sq.y = min(max(sq.y, r), self.height - r)
        self._last_time = time.monotonic()

    # ---------- 窗口状态 ----------

    def _on_minimize(self, _event: tk.Event | None = None) -> None:
        """最小化/隐藏时：暂停运动，并记住所有方块状态。"""
        if self._running or self._drag_index is not None:
            self._saved_state = (
                self._running,
                [(sq.x, sq.y, sq.vx, sq.vy, sq.hue, sq.size, sq.speed, sq.color, sq.weight)
                 for sq in self.squares],
            )
            self._running = False
            self._drag_index = None
            self._press_pos = None
            self._dragged = False

    def _on_restore(self, _event: tk.Event | None = None) -> None:
        """恢复显示时：从记忆的状态继续原来的运动。"""
        if self._saved_state is not None:
            running, states = self._saved_state
            self._saved_state = None
            self.squares = [Square(*st) for st in states]
            self._running = running
            self._last_time = time.monotonic()
            if self._screen_rect:
                position_window(self.root, *self._screen_rect)

    def _apply_desktop_styles(self) -> None:
        apply_desktop_pet_styles(self.root, self._in_square, self._screen_rect)

    def _poll_display(self) -> None:
        """周期性检查显示器配置；接入/拔除显示器后自动重新适配窗口范围。"""
        if self._screen_rect is not None:
            try:
                new_rect = virtual_screen()
                if new_rect and new_rect != self._screen_rect:
                    self._screen_rect = new_rect
                    self._apply_desktop_styles()
            except Exception:
                pass
        self._display_poll_id = self.root.after(self.DISPLAY_POLL_MS, self._poll_display)

    def destroy(self) -> None:
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        if self._display_poll_id is not None:
            self.root.after_cancel(self._display_poll_id)
            self._display_poll_id = None
