"""游戏主循环：主菜单、游玩、地图、胜利画面。"""

from __future__ import annotations

import ctypes
import math
import os
import time
from ctypes import wintypes
from collections import deque

import pygame

from . import config as C
from .audio import Audio
from .maze import Maze
from .player import Player
from .renderer import Renderer
from .scores import Scores


FONT_CANDIDATES = (
    r"C:\Windows\Fonts\msyh.ttc",    # 微软雅黑
    r"C:\Windows\Fonts\msyhbd.ttc",  # 微软雅黑粗体
    r"C:\Windows\Fonts\simhei.ttf",  # 黑体
    r"C:\Windows\Fonts\simsun.ttc",  # 宋体
    r"C:\Windows\Fonts\Deng.ttf",    # 等线
)


def load_font(size: int) -> pygame.font.Font:
    """直接按字体文件加载，绕开 pygame 字体枚举（部分 Windows 上会崩溃）。"""
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return pygame.font.Font(path, size)
            except pygame.error:
                continue
    return pygame.font.Font(None, size)


def enable_dpi_awareness() -> None:
    """声明进程 DPI 感知，窗口按物理像素渲染，避免系统缩放导致画面模糊。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class App:
    DIFF_KEYS = {pygame.K_1: "small", pygame.K_2: "medium", pygame.K_3: "large"}

    def __init__(self, seed: int | None = None):
        Audio.preinit()
        pygame.init()
        pygame.display.set_caption(C.TITLE)
        enable_dpi_awareness()
        self.clock = pygame.time.Clock()

        self.font_small = load_font(20)
        self.font_mid = load_font(30)
        self.font_big = load_font(64)
        self.font_huge = load_font(96)
        self.audio = Audio()
        self.scores = Scores()

        self.seed = seed
        self.state = "menu"  # menu / playing / pause / win
        self.difficulty_key: str | None = None
        self.maze: Maze | None = None
        self.player: Player | None = None
        self.run_started_at = 0.0
        self.pause_started: float | None = None
        self.elapsed = 0.0
        self.show_map = False
        self.fullscreen = False
        self.menu_index = 0
        self.running = True
        self._space_held = False
        self.steps = 0
        self.last_cell: tuple[int, int] | None = None
        self.last_rank = -1
        self.explored: bytearray | None = None
        self._minimap_bg: pygame.Surface | None = None
        self._minimap_cell = 2
        self._minimap_counter = 0
        self._set_video_mode(False)

    # ---------- 主循环 ----------

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(60) / 1000.0, 0.05)
            self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()
        pygame.quit()

    # ---------- 事件与更新 ----------

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return
            if event.type != pygame.KEYDOWN:
                continue
            if self.state == "menu":
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key in self.DIFF_KEYS:
                    self.audio.play_select()
                    self._start_game(self.DIFF_KEYS[event.key])
                elif event.key == pygame.K_UP:
                    self.menu_index = (self.menu_index - 1) % len(C.DIFFICULTIES)
                    self.audio.play_select()
                elif event.key == pygame.K_DOWN:
                    self.menu_index = (self.menu_index + 1) % len(C.DIFFICULTIES)
                    self.audio.play_select()
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.audio.play_select()
                    self._start_game(list(C.DIFFICULTIES)[self.menu_index])
            elif self.state == "playing":
                if event.key == pygame.K_ESCAPE:
                    self._pause()
                elif event.key in (pygame.K_w, pygame.K_UP):
                    self.player.on_forward_press(time.perf_counter())
            elif self.state == "pause":
                if event.key == pygame.K_ESCAPE:
                    self._resume()
                elif event.key in (pygame.K_m, pygame.K_q):
                    self.audio.play_select()
                    self._to_menu()
            elif self.state == "win":
                if event.key == pygame.K_r:
                    self.audio.play_select()
                    self._start_game(self.difficulty_key)
                elif event.key == pygame.K_m:
                    self.audio.play_select()
                    self._to_menu()
                elif event.key == pygame.K_ESCAPE:
                    self.running = False

    def _update(self, dt: float) -> None:
        if self.state == "playing":
            self._update_playing(dt)
        elif self.state == "win":
            self.elapsed = time.perf_counter() - self.run_started_at

    def _update_playing(self, dt: float) -> None:
        # 鼠标视角（射击游戏手感）
        if pygame.mouse.get_focused():
            mx, my = pygame.mouse.get_rel()
            self.player.yaw += mx * C.MOUSE_SENSITIVITY
            self.player.pitch -= my * C.MOUSE_SENSITIVITY
            self.player.pitch = max(-C.PITCH_LIMIT, min(C.PITCH_LIMIT, self.player.pitch))

        # 键盘输入基于硬件按键状态，中英文输入法下均有效
        focused = pygame.key.get_focused()
        keys = pygame.key.get_pressed() if focused else None
        self.show_map = bool(keys and keys[pygame.K_g])
        space_down = bool(keys and keys[pygame.K_SPACE])
        jump = space_down and not self._space_held and not self.show_map
        self._space_held = space_down

        if keys and not self.show_map:
            forward = (1 if keys[pygame.K_w] or keys[pygame.K_UP] else 0) - \
                      (1 if keys[pygame.K_s] or keys[pygame.K_DOWN] else 0)
            strafe = (1 if keys[pygame.K_d] or keys[pygame.K_RIGHT] else 0) - \
                     (1 if keys[pygame.K_a] or keys[pygame.K_LEFT] else 0)
            shift = bool(keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT])
            self.player.update(forward, strafe, dt, self.maze,
                               sprint_hold=shift, jump=jump)

        if self.player.just_jumped:
            self.audio.play_jump()
        if self.player.just_landed:
            self.audio.play_land()
        self._refresh_cell_state()
        self.elapsed = time.perf_counter() - self.run_started_at
        if self.maze.in_goal(self.player.x, self.player.y, C.GOAL_RADIUS) \
                and self.player.z < 0.5:
            self._on_win()

    def _refresh_cell_state(self) -> None:
        """步数统计（进入新格子记一步）并刷新探索区域。"""
        cell = (int(self.player.x), int(self.player.y))
        if cell != self.last_cell:
            self.steps += 1
            self.last_cell = cell
            self.audio.play_step()
        self._update_explored()

    def _update_explored(self) -> None:
        """BFS 按视线半径点亮已探索区域（墙不阻挡扩散）。"""
        m = self.maze
        w, h = m.width, m.height
        if self.explored is None or len(self.explored) != w * h:
            self.explored = bytearray(w * h)
        start = (int(self.player.x), int(self.player.y))
        radius = C.MINIMAP_REVEAL_RADIUS
        queue = deque([(start, 0)])
        seen = {start}
        while queue:
            (cx, cy), dist = queue.popleft()
            self.explored[cy * w + cx] = 1
            if dist >= radius:
                continue
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    if m.grid[ny][nx]:
                        self.explored[ny * w + nx] = 1
                    else:
                        queue.append(((nx, ny), dist + 1))

    def _start_game(self, key: str) -> None:
        cells = C.DIFFICULTIES[key]["cells"]
        self.difficulty_key = key
        self.maze = Maze(cells, cells, seed=self.seed)
        self.player = Player(self.maze.start[0], self.maze.start[1], yaw=math.pi / 2)
        self.run_started_at = time.perf_counter()
        self.elapsed = 0.0
        self.pause_started = None
        self._space_held = False
        self.steps = 0
        self.last_cell = (int(self.player.x), int(self.player.y))
        self.last_rank = -1
        self.explored = bytearray(self.maze.width * self.maze.height)
        self._minimap_bg = None
        self._minimap_counter = 0
        self.state = "playing"
        if C.FULLSCREEN_ON_START:
            self._set_video_mode(True)
        self._grab_mouse()
        self._update_explored()
        self.audio.start_music()
        self.audio.play_select()

    def _on_win(self) -> None:
        self.elapsed = time.perf_counter() - self.run_started_at
        self.last_rank = self.scores.add(
            self.difficulty_key, self.elapsed, self.steps, self.maze.seed)
        self.state = "win"
        self._release_mouse()
        self.audio.play_win()

    def _to_menu(self) -> None:
        self.state = "menu"
        self.show_map = False
        self.pause_started = None
        self._set_video_mode(False)
        self._release_mouse()
        self.audio.stop_music()

    def _pause(self) -> None:
        """ESC：退出全屏并暂停游戏（计时冻结）。"""
        if self.state != "playing":
            return
        self.pause_started = time.perf_counter()
        self.state = "pause"
        self._set_video_mode(False)
        self._release_mouse()
        self.audio.play_pause()

    def _resume(self) -> None:
        """继续游戏：回到全屏，暂停时间不计入用时。"""
        if self.state != "pause":
            return
        now = time.perf_counter()
        if self.pause_started is not None:
            self.run_started_at += now - self.pause_started
        self.pause_started = None
        self.state = "playing"
        if C.FULLSCREEN_ON_START:
            self._set_video_mode(True)
        self._grab_mouse()
        self.audio.play_resume()

    def _set_video_mode(self, fullscreen: bool) -> None:
        """切换窗口/全屏（无边框全屏，避免独占全屏模式切换卡顿）。"""
        if fullscreen:
            size = pygame.display.get_desktop_sizes()[0]
            if size[0] <= 0 or size[1] <= 0:
                size = (C.WINDOW_WIDTH, C.WINDOW_HEIGHT)
            flags = pygame.NOFRAME
        else:
            size = (C.WINDOW_WIDTH, C.WINDOW_HEIGHT)
            flags = 0
        self.window = pygame.display.set_mode(size, flags)
        self.frame = pygame.Surface(size)
        self.renderer = Renderer(size[0], size[1], C.FOV_DEGREES)
        self.fullscreen = fullscreen
        if fullscreen:
            self._move_window(0, 0)          # 全屏必须铺满屏幕左上角
        else:
            self._center_window()            # 窗口模式居中
        self._disable_ime()

    def _move_window(self, x: int, y: int) -> None:
        """直接移动游戏窗口（pygame 不提供窗口定位接口）。"""
        try:
            hwnd = pygame.display.get_wm_info().get("window")
            if not hwnd:
                return
            ctypes.windll.user32.SetWindowPos(
                wintypes.HWND(hwnd), None, x, y, 0, 0, 0x0001 | 0x0004)  # NOSIZE | NOZORDER
        except Exception:
            pass

    def _center_window(self) -> None:
        """按窗口实际尺寸居中（考虑 DPI/系统调整后的真实尺寸）。"""
        try:
            hwnd = pygame.display.get_wm_info().get("window")
            if not hwnd:
                return
            user32 = ctypes.windll.user32
            rect = wintypes.RECT()
            user32.GetWindowRect(wintypes.HWND(hwnd), ctypes.byref(rect))
            sw, sh = pygame.display.get_desktop_sizes()[0]
            w, h = rect.right - rect.left, rect.bottom - rect.top
            user32.SetWindowPos(
                wintypes.HWND(hwnd), None,
                max(0, (sw - w) // 2), max(0, (sh - h) // 2),
                0, 0, 0x0001 | 0x0004)
        except Exception:
            pass

    def _disable_ime(self) -> None:
        """解除系统输入法与本窗口的关联，中文/英文输入法下 WASD 都生效。"""
        try:
            hwnd = pygame.display.get_wm_info().get("window")
            if not hwnd:
                return
            imm32 = ctypes.WinDLL("imm32", use_last_error=True)
            imm32.ImmAssociateContext.argtypes = [wintypes.HWND, wintypes.HANDLE]
            imm32.ImmAssociateContext.restype = wintypes.HANDLE
            imm32.ImmAssociateContext(hwnd, None)
        except Exception:
            pass

    def _grab_mouse(self) -> None:
        try:
            pygame.mouse.set_visible(False)
            pygame.event.set_grab(True)
            pygame.mouse.get_rel()
        except pygame.error:
            pass

    def _release_mouse(self) -> None:
        try:
            pygame.event.set_grab(False)
            pygame.mouse.set_visible(True)
        except pygame.error:
            pass

    # ---------- 绘制 ----------

    def _draw(self) -> None:
        if self.state == "menu":
            self._draw_menu()
            return

        self.renderer.render(self.frame, self.maze, self.player)
        self.window.blit(self.frame, (0, 0))
        self._draw_hud()
        self._draw_minimap()
        if self.show_map:
            self._draw_map_overlay()
        if self.state == "pause":
            self._draw_pause_overlay()
        elif self.state == "win":
            self._draw_win_overlay()

    def _draw_menu(self) -> None:
        w, h = self.window.get_size()
        self.window.fill((20, 22, 30))

        title = self.font_huge.render("3D 迷宫", True, (240, 244, 252))
        sub = self.font_small.render(
            "WASD 移动 · 鼠标视角 · 空格 跳跃 · G 查看地图", True, (148, 156, 175))
        self.window.blit(title, (w // 2 - title.get_width() // 2, int(h * 0.16)))
        self.window.blit(sub, (w // 2 - sub.get_width() // 2, int(h * 0.16) + title.get_height() + 18))

        y0 = int(h * 0.42)
        for i, key in enumerate(C.DIFFICULTIES):
            d = C.DIFFICULTIES[key]
            label = f"[{i + 1}] {d['name']}  ·  {d['hint']}  ·  {d['cells']}×{d['cells']} 格"
            color = (255, 205, 90) if i == self.menu_index else (198, 204, 216)
            if i == self.menu_index:
                label = "> " + label
            text = self.font_mid.render(label, True, color)
            self.window.blit(text, (w // 2 - text.get_width() // 2, y0 + i * 64))

        hint = self.font_small.render(
            "↑ / ↓ 选择 · 回车 开始 · 1 / 2 / 3 直接选择 · ESC 退出", True, (130, 138, 155))
        self.window.blit(hint, (w // 2 - hint.get_width() // 2, int(h * 0.85)))

        # 当前难度最佳成绩
        selected = list(C.DIFFICULTIES)[self.menu_index]
        best = self.scores.best(selected)
        if best:
            line = f"最佳：{best['time']:.1f} 秒 · {best['steps']} 步 · {best['date']}"
            color = (180, 205, 235)
        else:
            line = "暂无成绩，来创造第一个纪录吧"
            color = (130, 140, 158)
        best_surf = self.font_small.render(line, True, color)
        self.window.blit(best_surf, (w // 2 - best_surf.get_width() // 2, int(h * 0.72)))

    def _draw_hud(self) -> None:
        w, h = self.window.get_size()
        # 准星（暂停/胜利时隐藏）
        if self.state not in ("win", "pause"):
            cx, cy = w // 2, h // 2
            pygame.draw.line(self.window, (255, 255, 255), (cx - 10, cy), (cx - 6, cy), 2)
            pygame.draw.line(self.window, (255, 255, 255), (cx + 6, cy), (cx + 10, cy), 2)
            pygame.draw.line(self.window, (255, 255, 255), (cx, cy - 10), (cx, cy - 6), 2)
            pygame.draw.line(self.window, (255, 255, 255), (cx, cy + 6), (cx, cy + 10), 2)

        d = C.DIFFICULTIES[self.difficulty_key]
        gx, gy = int(self.player.x), int(self.player.y)
        extra = " · 奔跑中" if self.player.sprint_active else ""
        info = f"{d['name']} · 位置 ({gx}, {gy}) · 种子 {self.maze.seed}{extra}"
        info_surf = self.font_small.render(info, True, (235, 238, 245))
        self.window.blit(info_surf, (16, 12))

        t = int(self.elapsed)
        time_surf = self.font_small.render(
            f"用时 {t // 60:02d}:{t % 60:02d} · 步数 {self.steps}", True, (235, 238, 245))
        self.window.blit(time_surf, (w - time_surf.get_width() - 16, 12))

        if not self.show_map:
            hint = "WASD 移动 · 空格 跳跃 · G 地图 · Shift/双击W 奔跑 · ESC 菜单"
            hint_surf = self.font_small.render(hint, True, (215, 220, 230))
            self.window.blit(hint_surf, (16, h - hint_surf.get_height() - 14))

    def _draw_map_overlay(self) -> None:
        """按住空格时显示的二维平面图。"""
        w, h = self.window.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((8, 10, 16, 195))
        maze = self.maze
        mw, mh = maze.width, maze.height
        margin = 48
        scale = min((w - 2 * margin) / mw, (h - 2 * margin) / mh)
        ox = (w - mw * scale) / 2
        oy = (h - mh * scale) / 2
        cell = max(1, math.ceil(scale))

        for gy in range(mh):
            for gx in range(mw):
                if maze.grid[gy][gx]:
                    rect = (round(ox + gx * scale), round(oy + gy * scale), cell, cell)
                    pygame.draw.rect(overlay, (168, 174, 186, 255), rect)

        # 入口（蓝）与出口（绿）
        ent = (round(ox + 1 * scale), round(oy + 0 * scale), cell, cell)
        pygame.draw.rect(overlay, (70, 130, 255, 255), ent)
        ext = (round(ox + (mw - 2) * scale), round(oy + (mh - 1) * scale), cell, cell)
        pygame.draw.rect(overlay, (60, 220, 110, 255), ext)

        def label(text, color, x, y):
            s = self.font_small.render(text, True, color)
            overlay.blit(s, (int(x), int(y)))

        label("入口", (150, 195, 255), ox + 1 * scale - 14, oy + 0 * scale - 26)
        label("出口", (120, 255, 160), ox + (mw - 2) * scale - 14, oy + (mh - 1) * scale + cell + 4)

        # 当前位置与朝向
        px, py = self.player.x, self.player.y
        sx, sy = round(ox + px * scale), round(oy + py * scale)
        pygame.draw.circle(overlay, (255, 70, 70, 255), (sx, sy), 8)
        fx, fy = math.cos(self.player.yaw), math.sin(self.player.yaw)
        pygame.draw.line(overlay, (255, 255, 255, 255), (sx, sy),
                         (sx + fx * 24, sy + fy * 24), 3)
        pos_label = self.font_small.render("当前位置", True, (255, 220, 160))
        lx = max(8, min(w - pos_label.get_width() - 8, sx + 14))
        ly = max(8, min(h - pos_label.get_height() - 8, sy - pos_label.get_height() - 10))
        overlay.blit(pos_label, (lx, ly))

        tip = self.font_small.render("按住 G 查看地图，松开关闭", True, (200, 208, 220))
        overlay.blit(tip, (w // 2 - tip.get_width() // 2, h - tip.get_height() - 14))
        self.window.blit(overlay, (0, 0))

    def _draw_minimap(self) -> None:
        """右下角常驻小地图：已探索区域 + 当前位置（战争迷雾）。"""
        if self.state not in ("playing", "pause") or self.show_map:
            return
        if self._minimap_bg is None or self._minimap_counter % C.MINIMAP_REFRESH_FRAMES == 0:
            self._build_minimap_surface()
        self._minimap_counter += 1

        bg = self._minimap_bg
        ww, wh = self.window.get_size()
        x0 = ww - bg.get_width() - 14
        y0 = wh - bg.get_height() - 14
        self.window.blit(bg, (x0, y0))

        ox = x0 + 4
        oy = y0 + 4
        cell = self._minimap_cell
        m = self.maze
        # 入口（蓝）/ 出口（绿），仅已探索时显示
        if self.explored[0 * m.width + 1]:
            pygame.draw.rect(self.window, (70, 130, 255),
                             (ox + 1 * cell, oy + 0 * cell, cell, cell))
        if self.explored[(m.height - 1) * m.width + (m.width - 2)]:
            pygame.draw.rect(self.window, (60, 220, 110),
                             (ox + (m.width - 2) * cell, oy + (m.height - 1) * cell, cell, cell))
        # 当前位置与朝向
        px = round(ox + self.player.x * cell)
        py = round(oy + self.player.y * cell)
        pygame.draw.circle(self.window, (255, 80, 80), (px, py), max(2, cell // 2))
        fx, fy = math.cos(self.player.yaw), math.sin(self.player.yaw)
        pygame.draw.line(self.window, (255, 255, 255), (px, py),
                         (round(px + fx * cell * 2.2), round(py + fy * cell * 2.2)), 2)

    def _build_minimap_surface(self) -> None:
        m = self.maze
        w, h = m.width, m.height
        cell = max(C.MINIMAP_CELL_MIN, C.MINIMAP_MAX_SIZE // max(w, h))
        mw, mh = w * cell, h * cell
        surf = pygame.Surface((mw + 8, mh + 8), pygame.SRCALPHA)
        pygame.draw.rect(surf, (10, 14, 22, 195), surf.get_rect(), border_radius=6)
        ox = oy = 4
        explored = self.explored
        for gy in range(h):
            row = gy * w
            base = oy + gy * cell
            for gx in range(w):
                if not explored[row + gx]:
                    continue
                if m.grid[gy][gx]:
                    pygame.draw.rect(surf, (150, 156, 168, 235),
                                     (ox + gx * cell, base, cell, cell))
                else:
                    pygame.draw.rect(surf, (38, 42, 52, 220),
                                     (ox + gx * cell, base, cell, cell))
        self._minimap_bg = surf
        self._minimap_cell = cell

    def _draw_pause_overlay(self) -> None:
        w, h = self.window.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((8, 10, 16, 175))
        self.window.blit(overlay, (0, 0))

        title = self.font_huge.render("已暂停", True, (255, 220, 90))
        self.window.blit(title, (w // 2 - title.get_width() // 2, int(h * 0.24)))

        sub = self.font_small.render("已退出全屏，暂停计时", True, (190, 198, 210))
        self.window.blit(sub, (w // 2 - sub.get_width() // 2, int(h * 0.40)))

        ops = self.font_small.render(
            "[ESC] 继续（回到全屏） · [M] 返回主菜单", True, (180, 188, 200))
        self.window.blit(ops, (w // 2 - ops.get_width() // 2, int(h * 0.50)))

    def _draw_win_overlay(self) -> None:
        w, h = self.window.get_size()
        overlay = pygame.Surface((w, h), pygame.SRCALPHA)
        overlay.fill((10, 16, 12, 175))
        self.window.blit(overlay, (0, 0))

        title = self.font_huge.render("恭喜通关！", True, (255, 220, 90))
        self.window.blit(title, (w // 2 - title.get_width() // 2, int(h * 0.16)))

        d = C.DIFFICULTIES[self.difficulty_key]
        t = int(self.elapsed)
        stats = self.font_mid.render(
            f"{d['name']} · 用时 {t // 60:02d}:{t % 60:02d} · 步数 {self.steps} · 种子 {self.maze.seed}",
            True, (225, 230, 238))
        self.window.blit(stats, (w // 2 - stats.get_width() // 2, int(h * 0.30)))

        if self.last_rank == 0:
            rank_text = "★ 新纪录！用时最快！"
        elif self.last_rank > 0:
            rank_text = f"本局第 {self.last_rank + 1} 名"
        else:
            rank_text = "未进入本难度前五"
        rank_surf = self.font_mid.render(rank_text, True, (255, 210, 120))
        self.window.blit(rank_surf, (w // 2 - rank_surf.get_width() // 2, int(h * 0.38)))

        top = self.scores.top(self.difficulty_key, 3)
        if top:
            head = self.font_small.render(f"{d['name']} 前三名", True, (190, 198, 210))
            self.window.blit(head, (w // 2 - head.get_width() // 2, int(h * 0.46)))
            for i, e in enumerate(top):
                line = self.font_small.render(
                    f"{i + 1}. {e['time']:.1f} 秒 · {e['steps']} 步 · {e['date']}",
                    True, (215, 220, 230))
                self.window.blit(line, (w // 2 - line.get_width() // 2, int(h * 0.46) + 34 + i * 32))

        ops = self.font_small.render(
            "[R] 再来一局 · [M] 主菜单 · [ESC] 退出", True, (180, 188, 200))
        self.window.blit(ops, (w // 2 - ops.get_width() // 2, int(h * 0.66)))
