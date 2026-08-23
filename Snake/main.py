"""贪吃蛇小游戏：入口与界面（pygame 实现）。

控制方式：
  单人：方向键 或 W/A/S/D 均可；支持快速连按（方向依次缓冲）
  双人：玩家1 用 W/A/S/D，玩家2 用方向键
  P 或 空格 暂停 / 继续；R 重新开始；M 或 Esc 返回主菜单
  也可以点击右侧栏的虚拟方向键与按钮

按键说明：程序同时监听按键事件、pygame 轮询和 Windows 物理按键，
因此即使在中文输入法状态下，W/A/S/D/P/M 也能正常响应。
"""
from __future__ import annotations

import ctypes
import math
import os
import sys

import pygame

from game import DOWN, LEFT, RIGHT, UP, SnakeGame
from settings import MAP_NAMES, Settings


# ---------- DPI 感知（必须在创建任何窗口之前开启） ----------
def enable_dpi_awareness() -> float:
    """开启进程级 DPI 感知，返回主显示器缩放系数（如 1.0 / 1.25 / 1.5）。"""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PER_MONITOR_AWARE_V2
        factor = ctypes.windll.shcore.GetScaleFactorForDevice(0)
        return max(factor / 100.0, 1.0)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
    return 1.0


DPI_SCALE = enable_dpi_awareness()


def S(value: float) -> int:
    """把逻辑尺寸换算为物理像素（按 DPI 缩放）。"""
    return round(value * DPI_SCALE)


FPS = 60
CELL = S(28)
TOP_BAR = S(64)
SIDEBAR_W = S(210)
MENU_SIZE = (S(640), S(660))
FOOD_SPAWN_INTERVAL = 2.0  # 秒：场上豆子每隔这么久自动新增一个

COLORS = {
    "bg_top": (24, 26, 38),
    "bg_bottom": (13, 14, 21),
    "card": (31, 34, 48),
    "card_light": (44, 48, 64),
    "border": (62, 68, 88),
    "grid": (44, 48, 62),
    "text": (238, 240, 246),
    "text_dim": (150, 156, 175),
    "accent": (0, 205, 225),
    "accent2": (118, 94, 240),
    "head": (92, 200, 105),
    "body": (50, 142, 68),
    "p2_head": (255, 178, 72),
    "p2_body": (214, 122, 42),
    "food": (255, 84, 84),
    "danger": (235, 77, 89),
    "ok": (86, 190, 96),
    "sidebar": (21, 23, 33),
}

PLAYER_COLORS = [
    {"head": COLORS["head"], "body": COLORS["body"]},
    {"head": COLORS["p2_head"], "body": COLORS["p2_body"]},
]

# 玩家1：WASD；玩家2：方向键（仅双人模式）
P1_DIR_KEYS = {
    pygame.K_w: UP,
    pygame.K_a: LEFT,
    pygame.K_s: DOWN,
    pygame.K_d: RIGHT,
}
P2_DIR_KEYS = {
    pygame.K_UP: UP,
    pygame.K_LEFT: LEFT,
    pygame.K_DOWN: DOWN,
    pygame.K_RIGHT: RIGHT,
}

# ---------- Windows 物理按键（不受输入法影响） ----------
USER32 = None
try:
    USER32 = ctypes.windll.user32
except Exception:
    pass

VK = {
    "w": 0x57, "a": 0x41, "s": 0x53, "d": 0x44,
    "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
    "p": 0x50, "m": 0x4D, "r": 0x52,
    "esc": 0x1B, "space": 0x20, "enter": 0x0D,
}


def vk_pressed(name: str) -> bool:
    if not USER32:
        return False
    return bool(USER32.GetAsyncKeyState(VK[name]) & 0x8000)


FALLBACK_ACTIONS = {
    "pause": ("p", "space"),
    "menu": ("m",),
    "restart": ("r",),
    "esc": ("esc",),
    "enter": ("enter",),
    "w": ("w",),
    "a": ("a",),
    "s": ("s",),
    "d": ("d",),
}

DIR_VECTORS = {"up": UP, "down": DOWN, "left": LEFT, "right": RIGHT}
RESULT_TITLES = {"p1": "玩家1 获胜！", "p2": "玩家2 获胜！", "draw": "平局！"}
RESULT_COLORS = {"p1": (86, 190, 96), "p2": (255, 178, 72), "draw": (238, 240, 246)}

SETTINGS_ROWS = [
    ("mode", "游戏模式"),
    ("duel_timer", "双人倒计时"),
    ("duel_time", "倒计时时长"),
    ("map", "地图大小"),
    ("speed", "移动速度"),
    ("wrap", "允许穿墙"),
    ("speed_up", "随长度加速"),
]
SETTINGS_LABELS = dict(SETTINGS_ROWS)


def resource_path(relative: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, relative)


def load_font(size: int) -> pygame.font.Font:
    """加载中文字体；尺寸按 DPI 缩放以保证清晰。"""
    pixel_size = S(size)
    for path in (
        r"C:\Windows\Fonts\msyh.ttc",      # 微软雅黑
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simhei.ttf",    # 黑体
        r"C:\Windows\Fonts\simsun.ttc",    # 宋体
        r"C:\Windows\Fonts\Deng.ttf",      # 等线
    ):
        try:
            if os.path.exists(path):
                return pygame.font.Font(path, pixel_size)
        except (OSError, pygame.error):
            continue
    return pygame.font.Font(None, pixel_size)


def lerp_color(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float):
    return tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))


def draw_gradient(
    surface: pygame.Surface,
    rect,
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
    radius: int = 0,
) -> None:
    x, y, w, h = pygame.Rect(rect).topleft + pygame.Rect(rect).size
    strips = max(1, h // S(3))
    step = h // strips
    for i in range(strips):
        t = i / max(1, strips - 1)
        strip_h = step if i < strips - 1 else h - step * (strips - 1)
        pygame.draw.rect(
            surface,
            lerp_color(top, bottom, t),
            (x, y + i * step, w, strip_h),
            border_radius=radius,
        )


class App:
    def __init__(self) -> None:
        pygame.init()
        pygame.key.set_repeat(400, 50)
        pygame.display.set_caption("贪吃蛇 Snake")

        self.settings = Settings.load()
        self.screen = pygame.display.set_mode(MENU_SIZE)
        self.clock = pygame.time.Clock()
        self.fonts: dict[int, pygame.font.Font] = {}

        self.icon_image: pygame.Surface | None = None
        try:
            path = resource_path(os.path.join("assets", "icon.png"))
            if os.path.exists(path):
                self.icon_image = pygame.image.load(path).convert_alpha()
                pygame.display.set_icon(self.icon_image)
        except Exception:
            pass

        self.state = "menu"  # menu / settings / playing / paused / gameover
        self.game: SnakeGame | None = None
        self.result: str | None = None   # 双人结果：p1 / p2 / draw
        self.won = False                 # 单人铺满地图胜利
        self.move_accum = 0.0
        self.time_left: float | None = None
        self.food_timer = 0.0
        self.settings_index = 0
        self.hover_pos: tuple[int, int] | None = None
        self.hot_rects: list[tuple[pygame.Rect, str]] = []
        self._prev_actions: set[str] = set()

    # ---------- 工具 ----------
    def font(self, size: int) -> pygame.font.Font:
        if size not in self.fonts:
            self.fonts[size] = load_font(size)
        return self.fonts[size]

    def enter_menu(self) -> None:
        self.state = "menu"
        self.screen = pygame.display.set_mode(MENU_SIZE)

    def enter_settings(self) -> None:
        self.state = "settings"
        self.settings_index = 0

    def enter_game(self) -> None:
        cols, rows = self.settings.grid_size
        duel = self.settings.mode == "duel"
        if duel:
            initial_food_count = 3 if cols <= 15 else 5
        else:
            initial_food_count = 3
        self.game = SnakeGame(
            cols,
            rows,
            wrap=self.settings.wrap,
            mode=self.settings.mode,
            initial_food_count=initial_food_count,
        )
        self.result = None
        self.won = False
        self.move_accum = 0.0
        self.food_timer = 0.0
        self.time_left = (
            float(self.settings.duel_time)
            if (duel and self.settings.duel_timer)
            else None
        )
        self.state = "playing"
        win_w = cols * CELL + SIDEBAR_W
        win_h = TOP_BAR + max(rows * CELL, S(560))
        self.screen = pygame.display.set_mode((win_w, win_h))

    def restart_game(self) -> None:
        self.enter_game()

    # ---------- 事件 ----------
    def handle_event(self, event: pygame.event.Event) -> None:
        if self.state == "menu":
            self.handle_menu_event(event)
        elif self.state == "settings":
            self.handle_settings_event(event)
        elif self.state == "playing":
            self.handle_playing_event(event)
        elif self.state == "paused":
            self.handle_paused_event(event)
        elif self.state == "gameover":
            self.handle_gameover_event(event)

    def handle_menu_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.enter_game()
            elif event.key == pygame.K_ESCAPE:
                self.quit()
        elif event.type == pygame.MOUSEMOTION:
            self.hover_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.trigger_hot(event.pos)

    def handle_settings_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_w):
                self.settings_index = (self.settings_index - 1) % len(SETTINGS_ROWS)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self.settings_index = (self.settings_index + 1) % len(SETTINGS_ROWS)
            elif event.key in (pygame.K_LEFT, pygame.K_a):
                self.adjust_current(-1)
            elif event.key in (pygame.K_RIGHT, pygame.K_d):
                self.adjust_current(1)
            elif event.key in (pygame.K_ESCAPE, pygame.K_BACKSPACE, pygame.K_b):
                self.enter_menu()
        elif event.type == pygame.MOUSEMOTION:
            self.hover_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if not self.trigger_hot(event.pos):
                self.select_row_at(event.pos)

    def handle_playing_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if not self.game:
                return
            if event.key in P1_DIR_KEYS:
                self.game.set_direction(0, P1_DIR_KEYS[event.key])
            elif event.key in P2_DIR_KEYS:
                player = 1 if self.game.mode == "duel" else 0
                self.game.set_direction(player, P2_DIR_KEYS[event.key])
            elif event.key in (pygame.K_p, pygame.K_SPACE):
                self.state = "paused"
            elif event.key in (pygame.K_m, pygame.K_ESCAPE):
                self.enter_menu()
        elif event.type == pygame.MOUSEMOTION:
            self.hover_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.trigger_hot(event.pos)

    def handle_paused_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_p, pygame.K_SPACE, pygame.K_RETURN):
                self.state = "playing"
            elif event.key == pygame.K_r:
                self.restart_game()
            elif event.key in (pygame.K_m, pygame.K_ESCAPE):
                self.enter_menu()
        elif event.type == pygame.MOUSEMOTION:
            self.hover_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.trigger_hot(event.pos)

    def handle_gameover_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_r, pygame.K_RETURN, pygame.K_SPACE):
                self.restart_game()
            elif event.key in (pygame.K_m, pygame.K_ESCAPE):
                self.enter_menu()
        elif event.type == pygame.MOUSEMOTION:
            self.hover_pos = event.pos
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.trigger_hot(event.pos)

    def adjust_current(self, delta: int) -> None:
        field = SETTINGS_ROWS[self.settings_index][0]
        self.settings.adjust(field, delta)
        self.settings.save()

    def settings_rows_rects(self) -> list[tuple[str, pygame.Rect, pygame.Rect, pygame.Rect]]:
        rows = []
        for field, _ in SETTINGS_ROWS:
            row = pygame.Rect(S(150), S(112) + len(rows) * S(56), S(340), S(48))
            left_btn = pygame.Rect(row.left, row.top, S(44), row.height)
            right_btn = pygame.Rect(row.right - S(44), row.top, S(44), row.height)
            rows.append((field, row, left_btn, right_btn))
        return rows

    def select_row_at(self, pos: tuple[int, int]) -> None:
        for index, (_, row, _, _) in enumerate(self.settings_rows_rects()):
            if row.collidepoint(pos):
                self.settings_index = index
                return

    def trigger_hot(self, pos: tuple[int, int]) -> bool:
        for rect, action in self.hot_rects:
            if rect.collidepoint(pos):
                self.run_action(action)
                return True
        return False

    def run_action(self, action: str) -> None:
        if action == "start":
            self.enter_game()
        elif action == "settings":
            self.enter_settings()
        elif action == "quit":
            self.quit()
        elif action == "back":
            self.enter_menu()
        elif action == "restart":
            self.restart_game()
        elif action == "menu":
            self.enter_menu()
        elif action == "resume":
            self.state = "playing"
        elif action == "pause_toggle":
            self.state = "paused" if self.state == "playing" else "playing"
        elif action.startswith("dir:"):
            _, player, name = action.split(":")
            vector = DIR_VECTORS.get(name)
            if vector and self.game:
                self.game.set_direction(int(player), vector)
        elif action.startswith("adj:"):
            _, field, delta = action.split(":")
            self.settings.adjust(field, int(delta))
            if field == "wrap" and self.game:
                self.game.wrap = self.settings.wrap
            self.settings.save()

    def quit(self) -> None:
        self.settings.save()
        pygame.quit()
        sys.exit(0)

    # ---------- 输入兜底：轮询物理按键 ----------
    def poll_direction_keys(self) -> None:
        """pygame 键盘状态轮询（部分场景事件丢失时兜底）。"""
        if not self.game:
            return
        pressed = pygame.key.get_pressed()
        duel = self.game.mode == "duel"
        for key, direction in P1_DIR_KEYS.items():
            if pressed[key]:
                self.game.set_direction(0, direction)
        for key, direction in P2_DIR_KEYS.items():
            if pressed[key]:
                self.game.set_direction(1 if duel else 0, direction)

    def poll_fallback_keys(self) -> None:
        """Windows 物理按键（中文输入法下也能响应 WASD / P / M 等）。"""
        if not USER32 or not pygame.key.get_focused():
            return

        # 方向：按住持续生效
        if self.state == "playing" and self.game:
            duel = self.game.mode == "duel"
            for name, direction, player in (
                ("w", UP, 0), ("a", LEFT, 0), ("s", DOWN, 0), ("d", RIGHT, 0),
                ("up", UP, 1), ("left", LEFT, 1), ("down", DOWN, 1), ("right", RIGHT, 1),
            ):
                if player == 1 and not duel:
                    player = 0
                if vk_pressed(name):
                    self.game.set_direction(player, direction)

        # 动作键：边沿触发
        now = {name for name, keys in FALLBACK_ACTIONS.items() if any(vk_pressed(k) for k in keys)}
        newly = now - self._prev_actions
        self._prev_actions = now
        if not newly:
            return

        if self.state == "playing":
            if "pause" in newly:
                self.state = "paused"
            elif "menu" in newly:
                self.enter_menu()
        elif self.state == "paused":
            if "pause" in newly or "enter" in newly:
                self.state = "playing"
            elif "restart" in newly:
                self.restart_game()
            elif "menu" in newly:
                self.enter_menu()
        elif self.state == "gameover":
            if "restart" in newly or "enter" in newly:
                self.restart_game()
            elif "menu" in newly:
                self.enter_menu()
        elif self.state == "menu":
            if "enter" in newly or "pause" in newly:
                self.enter_game()
            elif "esc" in newly:
                self.quit()
        elif self.state == "settings":
            if "w" in newly:
                self.settings_index = (self.settings_index - 1) % len(SETTINGS_ROWS)
            elif "s" in newly:
                self.settings_index = (self.settings_index + 1) % len(SETTINGS_ROWS)
            elif "a" in newly:
                self.adjust_current(-1)
            elif "d" in newly:
                self.adjust_current(1)
            elif "esc" in newly:
                self.enter_menu()

    # ---------- 更新 ----------
    def update(self, dt: float) -> None:
        if self.state == "playing" and self.game:
            self.poll_direction_keys()
            self.poll_fallback_keys()
            speed = self.game.effective_speed(0, self.settings.speed, self.settings.speed_up)
            interval = 1.0 / speed
            self.move_accum += dt
            steps = 0
            while self.move_accum >= interval and steps < 8:
                self.move_accum -= interval
                self.game.step()
                steps += 1

            # 豆子持续随机刷新（没有固定上限，不吃也会不断出现）
            self.food_timer += dt
            if self.food_timer >= FOOD_SPAWN_INTERVAL:
                self.food_timer = 0.0
                self.game.spawn_one_food()

            status, result = self.game.status()
            if status == "over":
                self.result = result
                self.won = False
                self.state = "gameover"
            elif self.game.mode == "single" and not self.game.foods:
                self.won = True
                self.state = "gameover"

            # 双人倒计时
            if (
                self.state == "playing"
                and self.game.mode == "duel"
                and self.settings.duel_timer
                and self.time_left is not None
            ):
                self.time_left -= dt
                if self.time_left <= 0:
                    self.time_left = 0.0
                    self.result = self.game.end_by_timer()
                    self.won = False
                    self.state = "gameover"

    # ---------- 绘制 ----------
    def draw(self) -> None:
        self.draw_background()
        self.hot_rects = []
        if self.state == "menu":
            self.draw_menu()
        elif self.state == "settings":
            self.draw_settings()
        elif self.state == "playing":
            self.draw_playfield()
        elif self.state == "paused":
            self.draw_playfield()
            self.draw_overlay_card(
                "已暂停",
                [("继续游戏", "resume"), ("重新开始", "restart"), ("返回主菜单", "menu")],
                "P/空格 继续 · R 重开 · M/Esc 主菜单",
            )
        elif self.state == "gameover":
            self.draw_playfield()
            duel = self.game is not None and self.game.mode == "duel"
            if duel:
                title = RESULT_TITLES.get(self.result, "游戏结束")
            else:
                title = "胜利！" if self.won else "游戏结束"
            self.draw_overlay_card(
                title,
                [("再来一局", "restart"), ("返回主菜单", "menu")],
                "R/回车 重开 · M/Esc 主菜单",
            )

    def draw_background(self) -> None:
        draw_gradient(
            self.screen,
            (0, 0, self.screen.get_width(), self.screen.get_height()),
            COLORS["bg_top"],
            COLORS["bg_bottom"],
        )

    def draw_menu(self) -> None:
        w = self.screen.get_width()

        icon_rect = pygame.Rect(0, 0, S(88), S(88))
        icon_rect.center = (w // 2, S(120))
        if self.icon_image:
            scaled = pygame.transform.smoothscale(self.icon_image, icon_rect.size)
            self.screen.blit(scaled, icon_rect)
        else:
            pygame.draw.circle(self.screen, COLORS["card_light"], icon_rect.center, S(44))
            pygame.draw.circle(self.screen, COLORS["accent"], icon_rect.center, S(38), S(2))

        title = self.font(44).render("贪吃蛇", True, COLORS["text"])
        self.screen.blit(title, title.get_rect(center=(w // 2, S(190))))
        sub = self.font(18).render("Snake · 方向键 / WASD 双控制", True, COLORS["text_dim"])
        self.screen.blit(sub, sub.get_rect(center=(w // 2, S(234))))

        card = pygame.Rect(0, 0, S(380), S(140))
        card.center = (w // 2, S(322))
        self.draw_panel(card, radius=S(16))
        cols, rows = self.settings.grid_size
        mode_text = "双人竞技" if self.settings.mode == "duel" else "单人游戏"
        timer_text = ""
        if self.settings.mode == "duel" and self.settings.duel_timer:
            timer_text = f" · 倒计时 {self.settings.duel_time}秒"
        lines = [
            f"模式：{mode_text}{timer_text}",
            f"地图：{MAP_NAMES[self.settings.map_key]}（{cols}×{rows}）",
            f"速度：{self.settings.speed} 格/秒 · 穿墙：{'开' if self.settings.wrap else '关'}",
            f"随长度加速：{'开' if self.settings.speed_up else '关'}",
        ]
        for i, line in enumerate(lines):
            text = self.font(17).render(line, True, COLORS["text_dim"])
            self.screen.blit(
                text, text.get_rect(center=(w // 2, card.top + S(26) + i * S(27)))
            )

        buttons = [
            (pygame.Rect(0, 0, S(210), S(48)), "开始游戏", "start", "primary"),
            (pygame.Rect(0, 0, S(210), S(48)), "游戏设置", "settings", "secondary"),
            (pygame.Rect(0, 0, S(210), S(42)), "退出游戏", "quit", "ghost"),
        ]
        for i, (rect, label, action, kind) in enumerate(buttons):
            rect.centerx = w // 2
            rect.y = S(428) + i * S(56)
            self.draw_button(rect, label, action, kind)

        hint = self.font(15).render(
            "回车开始 · Esc 退出 · 中文输入法下按键同样有效",
            True,
            COLORS["text_dim"],
        )
        self.screen.blit(hint, hint.get_rect(center=(w // 2, S(632))))

    def draw_settings(self) -> None:
        w = self.screen.get_width()
        title = self.font(32).render("游戏设置", True, COLORS["text"])
        self.screen.blit(title, title.get_rect(center=(w // 2, S(50))))

        card = pygame.Rect(0, 0, S(400), S(420))
        card.center = (w // 2, S(310))
        self.draw_panel(card, radius=S(18))

        for index, (field, row, left_btn, right_btn) in enumerate(
            self.settings_rows_rects()
        ):
            selected = index == self.settings_index
            bg = COLORS["card_light"] if selected else COLORS["card"]
            pygame.draw.rect(self.screen, bg, row, border_radius=S(12))
            if selected:
                pygame.draw.rect(
                    self.screen,
                    COLORS["accent"],
                    pygame.Rect(row.left, row.top, S(5), row.height),
                    border_radius=S(2),
                )
            name = self.font(17).render(SETTINGS_LABELS[field], True, COLORS["text"])
            self.screen.blit(name, (row.left + S(54), row.centery - name.get_height() // 2))
            value = self.settings_value(field)
            val = self.font(17).render(
                value, True, COLORS["accent"] if selected else COLORS["text"]
            )
            self.screen.blit(val, (row.left + S(160), row.centery - val.get_height() // 2))
            lx, ly = left_btn.center
            pygame.draw.polygon(
                self.screen,
                COLORS["text_dim"],
                [(lx - S(6), ly), (lx + S(3), ly - S(8)), (lx + S(3), ly + S(8))],
            )
            rx, ry = right_btn.center
            pygame.draw.polygon(
                self.screen,
                COLORS["text_dim"],
                [(rx + S(6), ry), (rx - S(3), ry - S(8)), (rx - S(3), ry + S(8))],
            )
            self.hot_rects.append((left_btn, f"adj:{field}:-1"))
            self.hot_rects.append((right_btn, f"adj:{field}:1"))

        hint = self.font(15).render(
            "↑/↓ 或 W/S 选择 · ←/→ 或 A/D 调整 · Esc 返回", True, COLORS["text_dim"]
        )
        self.screen.blit(hint, hint.get_rect(center=(w // 2, S(548))))
        back_rect = pygame.Rect(0, 0, S(200), S(46))
        back_rect.centerx = w // 2
        back_rect.y = S(584)
        self.draw_button(back_rect, "返回主菜单", "back", "secondary")

    def settings_value(self, field: str) -> str:
        if field == "mode":
            return "单人游戏" if self.settings.mode == "single" else "双人竞技"
        if field == "duel_timer":
            return "开" if self.settings.duel_timer else "关"
        if field == "duel_time":
            return f"{self.settings.duel_time} 秒"
        if field == "map":
            cols, rows = self.settings.grid_size
            return f"{MAP_NAMES[self.settings.map_key]} {cols}×{rows}"
        if field == "speed":
            return f"{self.settings.speed} 格/秒"
        if field == "wrap":
            return "开" if self.settings.wrap else "关"
        if field == "speed_up":
            return "开" if self.settings.speed_up else "关"
        return ""

    # ---------- 游戏画面 ----------
    def draw_playfield(self) -> None:
        if not self.game:
            return
        grid_w = self.game.width * CELL
        grid_h = self.game.height * CELL
        grid_rect = pygame.Rect(0, TOP_BAR, grid_w, grid_h)
        pygame.draw.rect(self.screen, (17, 18, 26), grid_rect)
        for x in range(self.game.width + 1):
            pygame.draw.line(
                self.screen,
                COLORS["grid"],
                (x * CELL, TOP_BAR),
                (x * CELL, TOP_BAR + grid_h),
            )
        for y in range(self.game.height + 1):
            pygame.draw.line(
                self.screen,
                COLORS["grid"],
                (0, TOP_BAR + y * CELL),
                (grid_w, TOP_BAR + y * CELL),
            )
        pygame.draw.rect(self.screen, COLORS["border"], grid_rect, width=2)

        for fx, fy in self.game.foods:
            center = (fx * CELL + CELL // 2, TOP_BAR + fy * CELL + CELL // 2)
            pygame.draw.circle(self.screen, (150, 50, 50), center, CELL // 2 - 2)
            pygame.draw.circle(self.screen, COLORS["food"], center, CELL // 2 - 5)
            pygame.draw.circle(
                self.screen, (255, 160, 160), (center[0] - S(3), center[1] - S(3)), 2
            )

        for player, snake in enumerate(self.game.snakes):
            colors = PLAYER_COLORS[player % len(PLAYER_COLORS)]
            dimmed = not snake.alive
            head_color = lerp_color(colors["head"], (70, 72, 82), 0.65 if dimmed else 0.0)
            body_color = lerp_color(colors["body"], (70, 72, 82), 0.65 if dimmed else 0.0)
            for index, (sx, sy) in enumerate(snake.cells):
                rect = pygame.Rect(
                    sx * CELL + S(2),
                    TOP_BAR + sy * CELL + S(2),
                    CELL - S(4),
                    CELL - S(4),
                )
                color = head_color if index == 0 else body_color
                pygame.draw.rect(self.screen, color, rect, border_radius=S(8))
                if index > 0 and not dimmed:
                    pygame.draw.rect(
                        self.screen,
                        lerp_color(body_color, (255, 255, 255), 0.08),
                        rect,
                        width=1,
                        border_radius=S(8),
                    )

            hx, hy = snake.head
            dx, dy = snake.direction
            cx = hx * CELL + CELL // 2
            cy = TOP_BAR + hy * CELL + CELL // 2
            px, py = -dy, dx
            if snake.alive:
                for side in (-1, 1):
                    ex = cx + dx * S(4) + px * side * S(4)
                    ey = cy + dy * S(4) + py * side * S(4)
                    pygame.draw.circle(
                        self.screen, (12, 12, 18), (int(ex), int(ey)), S(3)
                    )

        self.draw_top_bar()
        self.draw_sidebar()

    def draw_top_bar(self) -> None:
        if not self.game:
            return
        if self.game.mode == "duel":
            s0, s1 = self.game.snakes
            speed = self.game.effective_speed(0, self.settings.speed, self.settings.speed_up)
            left = (
                f"P1 得分 {s0.eaten} · 长度 {s0.length}    "
                f"P2 得分 {s1.eaten} · 长度 {s1.length}"
            )
            left_text = self.font(17).render(left, True, COLORS["text"])
            self.screen.blit(left_text, (S(14), (TOP_BAR - left_text.get_height()) // 2))
            if self.settings.duel_timer and self.time_left is not None:
                seconds = max(0, math.ceil(self.time_left))
                color = COLORS["danger"] if seconds <= 10 else COLORS["text_dim"]
                right = f"倒计时 {seconds}s · 速度 {speed}"
                right_text = self.font(17).render(right, True, color)
                self.screen.blit(
                    right_text,
                    (
                        self.screen.get_width() - right_text.get_width() - S(14),
                        (TOP_BAR - right_text.get_height()) // 2,
                    ),
                )
            else:
                right = f"速度 {speed} · P 暂停 · M 主菜单"
                right_text = self.font(15).render(right, True, COLORS["text_dim"])
                self.screen.blit(
                    right_text,
                    (
                        self.screen.get_width() - right_text.get_width() - S(14),
                        (TOP_BAR - right_text.get_height()) // 2,
                    ),
                )
            return

        snake = self.game.snakes[0]
        speed = self.game.effective_speed(0, self.settings.speed, self.settings.speed_up)
        chips = [
            ("得分", str(snake.eaten)),
            ("长度", str(snake.length)),
            ("速度", f"{speed} 格/秒"),
            ("豆子", str(len(self.game.foods))),
        ]
        chip_w, chip_h = S(104), S(40)
        x = S(14)
        y = (TOP_BAR - chip_h) // 2
        for label, value in chips:
            rect = pygame.Rect(x, y, chip_w, chip_h)
            pygame.draw.rect(self.screen, COLORS["card_light"], rect, border_radius=S(10))
            pygame.draw.rect(self.screen, COLORS["border"], rect, width=1, border_radius=S(10))
            lab = self.font(13).render(label, True, COLORS["text_dim"])
            val = self.font(17).render(value, True, COLORS["text"])
            self.screen.blit(lab, (rect.x + S(12), rect.y + S(5)))
            self.screen.blit(val, (rect.x + S(12), rect.y + S(21)))
            x += chip_w + S(10)

        right = "P 暂停 · M 主菜单"
        right_text = self.font(15).render(right, True, COLORS["text_dim"])
        self.screen.blit(
            right_text,
            (
                self.screen.get_width() - right_text.get_width() - S(14),
                (TOP_BAR - right_text.get_height()) // 2,
            ),
        )

    def draw_sidebar(self) -> None:
        if not self.game:
            return
        grid_w = self.game.width * CELL
        side = pygame.Rect(
            grid_w, TOP_BAR, SIDEBAR_W, self.screen.get_height() - TOP_BAR
        )
        pygame.draw.rect(self.screen, COLORS["sidebar"], side)
        pygame.draw.line(
            self.screen,
            COLORS["border"],
            (grid_w, TOP_BAR),
            (grid_w, side.bottom),
            S(2),
        )
        x = side.centerx

        # 双人倒计时（醒目显示）
        y = TOP_BAR + S(12)
        if self.game.mode == "duel" and self.settings.duel_timer and self.time_left is not None:
            seconds = max(0, math.ceil(self.time_left))
            color = COLORS["danger"] if seconds <= 10 else COLORS["accent"]
            text = self.font(24).render(f"倒计时 {seconds}s", True, color)
            self.screen.blit(text, text.get_rect(center=(x, y + S(12))))
            y += S(48)

        # 虚拟方向键
        label = self.font(15).render("方向键", True, COLORS["text_dim"])
        self.screen.blit(label, label.get_rect(center=(x, y + S(8))))
        pad_up_y = y + S(52)
        pad_row_y = y + S(104)
        pad_buttons = [
            ("up", (x, pad_up_y)),
            ("left", (x - S(42), pad_row_y)),
            ("down", (x, pad_row_y)),
            ("right", (x + S(42), pad_row_y)),
        ]
        for name, center in pad_buttons:
            rect = pygame.Rect(0, 0, S(42), S(42))
            rect.center = center
            hover = self.hover_pos is not None and rect.collidepoint(self.hover_pos)
            fill = COLORS["card_light"] if hover else (26, 29, 41)
            pygame.draw.circle(self.screen, fill, center, S(19))
            pygame.draw.circle(
                self.screen,
                COLORS["accent"] if hover else COLORS["border"],
                center,
                S(19),
                S(2),
            )
            px, py = center
            if name == "up":
                points = [(px, py - S(6)), (px - S(7), py + S(4)), (px + S(7), py + S(4))]
            elif name == "down":
                points = [(px, py + S(6)), (px - S(7), py - S(4)), (px + S(7), py - S(4))]
            elif name == "left":
                points = [(px - S(6), py), (px + S(4), py - S(7)), (px + S(4), py + S(7))]
            else:
                points = [(px + S(6), py), (px - S(4), py - S(7)), (px - S(4), py + S(7))]
            pygame.draw.polygon(
                self.screen,
                COLORS["accent"] if hover else COLORS["text_dim"],
                points,
            )
            self.hot_rects.append((rect, f"dir:0:{name}"))

        if self.game.mode == "duel":
            note = self.font(12).render("玩家1 WASD · 玩家2 方向键", True, COLORS["text_dim"])
        else:
            note = self.font(12).render("方向键 / WASD", True, COLORS["text_dim"])
        self.screen.blit(note, note.get_rect(center=(x, y + S(132))))
        bean = self.font(13).render(f"场上豆子 {len(self.game.foods)}", True, COLORS["accent"])
        self.screen.blit(bean, bean.get_rect(center=(x, y + S(152))))

        # 实时设置
        y = y + S(176)
        speed = self.game.effective_speed(0, self.settings.speed, self.settings.speed_up)
        self.draw_sidebar_row(y, "速度", f"{speed}", minus="adj:speed:-1", plus="adj:speed:+1")
        y += S(46)
        self.draw_sidebar_row(
            y, "允许穿墙", "开" if self.settings.wrap else "关", toggle="adj:wrap:1"
        )
        y += S(46)
        self.draw_sidebar_row(
            y, "随长度加速", "开" if self.settings.speed_up else "关", toggle="adj:speed_up:1"
        )

        # 底部按钮
        bh, gap = S(38), S(10)
        bottom = self.screen.get_height() - S(14)
        if self.state == "gameover":
            items = [("重新开始", "restart", "primary"), ("返回主菜单", "menu", "ghost")]
        else:
            items = [
                ("暂停/继续", "pause_toggle", "primary"),
                ("重新开始", "restart", "secondary"),
                ("返回主菜单", "menu", "ghost"),
            ]
        start_y = bottom - len(items) * bh - (len(items) - 1) * gap
        for i, (label, action, kind) in enumerate(items):
            rect = pygame.Rect(
                side.left + S(14),
                start_y + i * (bh + gap),
                SIDEBAR_W - S(28),
                bh,
            )
            self.draw_button(rect, label, action, kind, size=15)

    def draw_sidebar_row(
        self,
        y: int,
        label: str,
        value: str,
        minus: str | None = None,
        plus: str | None = None,
        toggle: str | None = None,
    ) -> None:
        side_left = self.game.width * CELL
        lab = self.font(14).render(label, True, COLORS["text"])
        self.screen.blit(lab, (side_left + S(14), y + S(4)))
        if toggle:
            on = value == "开"
            btn = pygame.Rect(side_left + SIDEBAR_W - S(66), y, S(52), S(34))
            fill = COLORS["accent"] if on else COLORS["card_light"]
            pygame.draw.rect(self.screen, fill, btn, border_radius=S(10))
            pygame.draw.rect(self.screen, COLORS["border"], btn, width=1, border_radius=S(10))
            t = self.font(14).render(value, True, COLORS["text"])
            self.screen.blit(t, t.get_rect(center=btn.center))
            self.hot_rects.append((btn, toggle))
        else:
            minus_btn = pygame.Rect(side_left + SIDEBAR_W - S(68), y, S(28), S(34))
            plus_btn = pygame.Rect(side_left + SIDEBAR_W - S(36), y, S(28), S(34))
            val = self.font(14).render(value, True, COLORS["text"])
            self.screen.blit(val, (side_left + S(68), y + S(4)))
            for btn, symbol, action in (
                (minus_btn, "−", minus),
                (plus_btn, "+", plus),
            ):
                pygame.draw.rect(self.screen, COLORS["card_light"], btn, border_radius=S(10))
                pygame.draw.rect(
                    self.screen, COLORS["border"], btn, width=1, border_radius=S(10)
                )
                sym = self.font(17).render(symbol, True, COLORS["text"])
                self.screen.blit(sym, sym.get_rect(center=btn.center))
                self.hot_rects.append((btn, action))

    def draw_overlay_card(
        self,
        title: str,
        buttons: list[tuple[str, str]],
        hint: str,
    ) -> None:
        overlay = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
        overlay.fill((8, 8, 14, 165))
        self.screen.blit(overlay, (0, 0))

        w, h = self.screen.get_size()
        card = pygame.Rect(0, 0, S(460), S(300))
        card.center = (w // 2, h // 2)
        pygame.draw.rect(
            self.screen, (10, 10, 16), card.move(0, S(5)), border_radius=S(20)
        )
        pygame.draw.rect(self.screen, COLORS["card"], card, border_radius=S(20))
        pygame.draw.rect(self.screen, COLORS["border"], card, width=1, border_radius=S(20))

        title_color = COLORS["text"]
        if title == "游戏结束":
            title_color = COLORS["danger"]
        elif title == "胜利！":
            title_color = COLORS["ok"]
        elif title in RESULT_TITLES.values():
            for key, value in RESULT_TITLES.items():
                if value == title:
                    title_color = RESULT_COLORS[key]
                    break
        title_text = self.font(38).render(title, True, title_color)
        self.screen.blit(title_text, title_text.get_rect(center=(w // 2, card.top + S(58))))

        if self.game:
            if self.game.mode == "duel":
                info = (
                    f"P1 得分 {self.game.snakes[0].eaten} · "
                    f"P2 得分 {self.game.snakes[1].eaten}"
                )
            else:
                snake = self.game.snakes[0]
                info = f"得分 {snake.eaten} · 长度 {snake.length}"
            info_text = self.font(20).render(info, True, COLORS["text_dim"])
            self.screen.blit(
                info_text, info_text.get_rect(center=(w // 2, card.top + S(102)))
            )

        bh = S(46)
        n = len(buttons)
        gap = S(16)
        bw = min(S(150), (S(460) - S(32) - gap * (n - 1)) // n)
        total = bw * n + gap * (n - 1)
        x0 = (w - total) // 2
        y0 = card.top + S(140)
        for i, (label, action) in enumerate(buttons):
            rect = pygame.Rect(x0 + i * (bw + gap), y0, bw, bh)
            kind = "primary" if i == 0 else "secondary"
            self.draw_button(rect, label, action, kind)

        hint_text = self.font(15).render(hint, True, COLORS["text_dim"])
        self.screen.blit(hint_text, hint_text.get_rect(center=(w // 2, card.top + S(212))))

    def draw_panel(self, rect, radius: int = S(16)) -> None:
        pygame.draw.rect(self.screen, COLORS["card"], rect, border_radius=radius)
        pygame.draw.rect(
            self.screen, COLORS["border"], rect, width=1, border_radius=radius
        )

    def draw_button(
        self,
        rect: pygame.Rect,
        label: str,
        action: str,
        kind: str = "secondary",
        size: int = 20,
    ) -> None:
        rect = pygame.Rect(rect)
        hover = self.hover_pos is not None and rect.collidepoint(self.hover_pos)

        pygame.draw.rect(
            self.screen, (10, 10, 15), rect.move(0, S(3)), border_radius=S(12)
        )
        if kind == "primary":
            fill = lerp_color(COLORS["accent"], (255, 255, 255), 0.12 if hover else 0.0)
            pygame.draw.rect(self.screen, fill, rect, border_radius=S(12))
            pygame.draw.rect(
                self.screen,
                lerp_color(COLORS["accent"], (255, 255, 255), 0.25),
                rect,
                width=1,
                border_radius=S(12),
            )
            text_color = (255, 255, 255)
        elif kind == "ghost":
            pygame.draw.rect(
                self.screen,
                COLORS["border"],
                rect,
                width=1,
                border_radius=S(12),
            )
            text_color = COLORS["accent"] if hover else COLORS["text_dim"]
        else:
            fill = lerp_color(COLORS["card_light"], (255, 255, 255), 0.08 if hover else 0.0)
            pygame.draw.rect(self.screen, fill, rect, border_radius=S(12))
            pygame.draw.rect(
                self.screen, COLORS["border"], rect, width=1, border_radius=S(12)
            )
            text_color = COLORS["text"]

        text = self.font(size).render(label, True, text_color)
        self.screen.blit(text, text.get_rect(center=rect.center))
        self.hot_rects.append((rect, action))

    def run(self) -> None:
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                else:
                    self.handle_event(event)
            self.update(dt)
            self.draw()
            pygame.display.flip()


def main() -> None:
    App().run()


if __name__ == "__main__":
    main()
