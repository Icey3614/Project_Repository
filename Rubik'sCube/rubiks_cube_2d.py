# -*- coding: utf-8 -*-
"""
2D 魔方 · 三角形圆环版 (Rubik's Cube 2D - Triangle Rings)

把三阶魔方的 54 张贴片映射到一幅"三角形三圆族"平面图上：
- 三个等边三角形顶点各有一族同心圆（每族 3 个圆，共 9 条圆环）；
- 54 颗色珠位于圆环交点，每条圆环恰好穿过 12 颗；
- 转动任意圆环，环上 12 颗色珠沿环滑动移位（三维转动 -> 二维环转）；
- 求解目标：6 个"瓣"（每对圆族中线两侧各 9 颗，共 6x9）各为一种
  颜色，对应魔方的 6 个面。

操作：
    鼠标左键点击圆环 -> 顺时针转一格；右键 -> 逆时针
    键盘 1-9 -> T0,T1,T2,L0,L1,L2,R0,R1,R2；Shift+数字 反向
    Ctrl+Z / Ctrl+Y -> 撤销 / 重做
"""

import ctypes
import math
import os
import random
import sys
import time

import pygame

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# --------------------------------------------------------------------------
# DPI 感知：必须在创建窗口前启用，否则 Windows 会拉伸导致画面模糊
# --------------------------------------------------------------------------
def _enable_dpi_awareness():
    try:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)   # 每显示器 DPI
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


_enable_dpi_awareness()


def _system_scale():
    """返回系统 DPI 缩放（如 125% -> 1.25）。"""
    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()
        if dpi and dpi > 0:
            return max(1.0, dpi / 96.0)
    except Exception:
        pass
    return 1.0


SCALE = _system_scale()

# 逻辑尺寸（以 96 DPI 为基准），再按缩放系数放大
LOGICAL_W, LOGICAL_H = 1120, 880
W, H = int(LOGICAL_W * SCALE), int(LOGICAL_H * SCALE)
FPS = 60

BG = (24, 27, 34)
PANEL_BG = (32, 36, 45)
PANEL_EDGE = (54, 60, 72)
TEXT_MAIN = (232, 236, 242)
TEXT_DIM = (148, 156, 170)
RING_COLOR = (128, 136, 150)
RING_HOVER = (255, 255, 255)
BEAD_OUTLINE = (14, 16, 21)

# 6 个"瓣"（= 6 个面）的颜色：白 黄 橙 蓝 绿 红
BRANCH_COLORS = [
    (240, 240, 240),
    (255, 208, 0),
    (255, 122, 20),
    (0, 118, 255),
    (0, 158, 80),
    (198, 30, 58),
]

FAMILIES = ("T", "L", "R")
FAMILY_ORDER = {"T": 0, "L": 1, "R": 2}
RING_NAMES = [f + str(i) for f in FAMILIES for i in (0, 1, 2)]
RADII = (0.803, 1.034, 1.263)   # 与参考图一致的半径比例


# --------------------------------------------------------------------------
# 几何：等边三角形顶点上的三族同心圆，54 个交点
# --------------------------------------------------------------------------
def _unit_centers():
    s3 = math.sqrt(3.0) / 2.0
    return {"T": (0.0, s3), "L": (-0.5, 0.0), "R": (0.5, 0.0)}


def _circle_intersections(c1, r1, c2, r2):
    x1, y1 = c1
    x2, y2 = c2
    d = math.hypot(x2 - x1, y2 - y1)
    a = (r1 * r1 - r2 * r2 + d * d) / (2.0 * d)
    h = math.sqrt(max(0.0, r1 * r1 - a * a))
    xm = x1 + a * (x2 - x1) / d
    ym = y1 + a * (y2 - y1) / d
    p1 = (xm + h * (y2 - y1) / d, ym - h * (x2 - x1) / d)
    p2 = (xm - h * (y2 - y1) / d, ym + h * (x2 - x1) / d)
    return [p1, p2]


def _build_layout():
    centers = _unit_centers()
    pairs = (("T", "L"), ("T", "R"), ("L", "R"))
    beads = []          # 每颗珠子: {pos, rings, branch}
    for pi, (fa, fb) in enumerate(pairs):
        for i, ra in enumerate(RADII):
            for j, rb in enumerate(RADII):
                for p in _circle_intersections(centers[fa], ra, centers[fb], rb):
                    ax, ay = centers[fa]
                    bx, by = centers[fb]
                    side = 0 if (bx - ax) * (p[1] - ay) - (by - ay) * (p[0] - ax) >= 0 else 1
                    beads.append({
                        "pos": p,
                        "rings": (FAMILY_ORDER[fa] * 3 + i, FAMILY_ORDER[fb] * 3 + j),
                        "branch": pi * 2 + side,
                    })
    assert len(beads) == 54

    # 每条环上的珠子（按角度排序）
    ring_beads = [[] for _ in range(9)]
    for idx, b in enumerate(beads):
        for rid in b["rings"]:
            ring_beads[rid].append(idx)
    ring_angles = []
    for rid in range(9):
        fam = FAMILIES[rid // 3]
        cx, cy = centers[fam]
        ring_beads[rid].sort(
            key=lambda i: math.atan2(beads[i]["pos"][1] - cy, beads[i]["pos"][0] - cx))
        ring_angles.append([
            math.atan2(beads[i]["pos"][1] - cy, beads[i]["pos"][0] - cx)
            for i in ring_beads[rid]
        ])

    # 6 个瓣
    branch_beads = [[] for _ in range(6)]
    for idx, b in enumerate(beads):
        branch_beads[b["branch"]].append(idx)

    # 屏幕变换（等比例缩放并居中到绘制区）
    xs = [b["pos"][0] for b in beads]
    ys = [b["pos"][1] for b in beads]
    xmin, xmax = min(xs) - RADII[2], max(xs) + RADII[2]
    ymin, ymax = min(ys) - RADII[2], max(ys) + RADII[2]
    play_w, play_h = 740 * SCALE, 740 * SCALE
    sx0, sy0 = 24 * SCALE, 96 * SCALE
    gscale = min(play_w / (xmax - xmin), play_h / (ymax - ymin))
    off_x = sx0 + (play_w - (xmax - xmin) * gscale) / 2.0 - xmin * gscale
    off_y = sy0 + (play_h - (ymax - ymin) * gscale) / 2.0 - ymin * gscale

    def to_screen(x, y):
        return off_x + x * gscale, off_y + y * gscale

    ring_center = {}
    ring_r = {}
    for rid in range(9):
        fam = FAMILIES[rid // 3]
        cx, cy = centers[fam]
        ring_center[rid] = to_screen(cx, cy)
        ring_r[rid] = RADII[rid % 3] * gscale

    return {
        "beads": beads,
        "ring_beads": ring_beads,
        "ring_angles": ring_angles,
        "branch_beads": branch_beads,
        "to_screen": to_screen,
        "ring_center": ring_center,
        "ring_r": ring_r,
        "gscale": gscale,
    }


LAYOUT = _build_layout()
BEADS = LAYOUT["beads"]
RING_BEADS = LAYOUT["ring_beads"]
RING_ANGLES = LAYOUT["ring_angles"]
BRANCH_BEADS = LAYOUT["branch_beads"]
TO_SCREEN = LAYOUT["to_screen"]
RING_CENTER = LAYOUT["ring_center"]
RING_R = LAYOUT["ring_r"]
GSCALE = LAYOUT["gscale"]
BEAD_R = max(10, int(0.081 * GSCALE * 0.92))
RING_WIDTH = max(2, int(0.010 * GSCALE))
HIT_R = BEAD_R + max(8, int(0.02 * GSCALE))


# --------------------------------------------------------------------------
# 模型：状态 = 54 个颜色；圆环转动 = 环上 12 个位置的颜色循环移位
# --------------------------------------------------------------------------
def solved_state():
    return tuple(BRANCH_COLORS[b["branch"]] for b in BEADS)


def apply_ring(state, ring_id, direction):
    """direction: +1 顺时针（角度增大），-1 逆时针。"""
    pos = RING_BEADS[ring_id]
    n = len(pos)
    lst = list(state)
    for k in range(n):
        lst[pos[(k + direction) % n]] = state[pos[k]]
    return tuple(lst)


def is_solved(state):
    for bi, branch in enumerate(BRANCH_BEADS):
        target = BRANCH_COLORS[bi]
        if any(state[i] != target for i in branch):
            return False
    return True


def random_scramble(state, n=30):
    moves = []
    prev = -1
    while len(moves) < n:
        rid = random.randrange(9)
        if rid == prev:
            continue
        d = random.choice((1, -1))
        moves.append((rid, d))
        state = apply_ring(state, rid, d)
        prev = rid
    return moves


def ring_under_point(pos):
    """命中检测：返回最近且足够近的圆环 id。"""
    best, bd = None, HIT_R
    for rid in range(9):
        cx, cy = RING_CENTER[rid]
        d = abs(math.hypot(pos[0] - cx, pos[1] - cy) - RING_R[rid])
        if d < bd:
            best, bd = rid, d
    return best


# --------------------------------------------------------------------------
# 字体：优先直接加载系统中文字体文件，避免 SysFont 乱码/回退问题
# --------------------------------------------------------------------------
_FONT_CACHE = {}


def load_font(size, bold=False):
    key = (round(size * SCALE), bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    size_px = round(size * SCALE)
    candidates = []
    if getattr(sys, "_MEIPASS", None):          # PyInstaller 打包目录
        candidates.append(os.path.join(sys._MEIPASS, "msyh.ttc"))
    candidates += [
        r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\msyhbd.ttc" if bold else r"C:\Windows\Fonts\msyh.ttc",
        r"C:\Windows\Fonts\simhei.ttf",
        r"C:\Windows\Fonts\simsun.ttc",
        r"C:\Windows\Fonts\Deng.ttf",
    ]
    for path in candidates:
        try:
            if os.path.exists(path):
                font = pygame.font.Font(path, size_px)
                _FONT_CACHE[key] = font
                return font
        except Exception:
            continue
    try:
        font = pygame.font.SysFont("microsoftyahei,simhei,segoeui,arial", size_px)
        _FONT_CACHE[key] = font
        return font
    except Exception:
        font = pygame.font.Font(None, size_px)
        _FONT_CACHE[key] = font
        return font


# --------------------------------------------------------------------------
# 圆环转动动画：12 颗色珠沿环滑到下一个位置
# --------------------------------------------------------------------------
class RingAnim:
    DUR = 0.22

    def __init__(self, prev_state, new_state, ring_id, direction):
        self.t = 0.0
        self.done = False
        self.prev = prev_state
        self.new = new_state
        self.ring_id = ring_id
        self.direction = direction
        pos = RING_BEADS[ring_id]
        angles = RING_ANGLES[ring_id]
        n = len(pos)
        self.movers = []
        for k in range(n):
            a0 = angles[k]
            a1 = angles[(k + direction) % n]
            self.movers.append((prev_state[pos[k]], a0, a1))

    def update(self, dt):
        if self.done:
            return
        self.t += dt / self.DUR
        if self.t >= 1.0:
            self.t = 1.0
            self.done = True

    def draw(self, surf):
        e = self.t * self.t * (3 - 2 * self.t)
        cx, cy = RING_CENTER[self.ring_id]
        r = RING_R[self.ring_id]
        for color, a0, a1 in self.movers:
            delta = ((a1 - a0 + math.pi) % (2 * math.pi)) - math.pi
            a = a0 + delta * e
            x = cx + r * math.cos(a)
            y = cy + r * math.sin(a)
            _draw_bead(surf, x, y, color)


def _draw_bead(surf, x, y, color):
    pygame.draw.circle(surf, BEAD_OUTLINE, (int(x), int(y)), BEAD_R)
    pygame.draw.circle(surf, color, (int(x), int(y)), BEAD_R - 2)


# --------------------------------------------------------------------------
# 按钮
# --------------------------------------------------------------------------
class Button:
    def __init__(self, rect, text, cb, font, color, hover, cb_alt=None):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.cb = cb
        self.cb_alt = cb_alt
        self.font = font
        self.color = color
        self.hover = hover

    def draw(self, surf, mpos):
        hovered = self.rect.collidepoint(mpos)
        pygame.draw.rect(surf, self.hover if hovered else self.color,
                         self.rect, border_radius=9)
        img = self.font.render(self.text, True, TEXT_MAIN)
        surf.blit(img, img.get_rect(center=self.rect.center))


# --------------------------------------------------------------------------
# 游戏主体
# --------------------------------------------------------------------------
class Game:
    def __init__(self):
        self.state = solved_state()
        self.history = []
        self.redo_stack = []
        self.move_count = 0
        self.move_log = []
        self.start_time = None
        self.elapsed = 0.0
        self.solved = True
        self.anim = None
        self.confetti = []
        self.hover_ring = None
        self.font_sm = load_font(15)
        self.font_md = load_font(18)
        self.font_lg = load_font(26, bold=True)
        self.font_title = load_font(28, bold=True)
        self.buttons = []
        self._build_buttons()

    # ---------------- 按钮 ----------------
    def _build_buttons(self):
        bx = PANEL_X + 20 * SCALE
        bw = PANEL_W - 40 * SCALE
        gap = 8 * SCALE
        row_h = 40 * SCALE

        def add(rect, text, cb, color=(48, 56, 70), hover=(63, 73, 90), cb_alt=None):
            self.buttons.append(Button(rect, text, cb, self.font_md, color, hover, cb_alt))

        # 9 条圆环按钮：3 列（T/L/R）× 3 行（环 0/1/2），左键顺、右键逆
        col_w = (bw - 2 * gap) / 3
        y = 218 * SCALE
        for col, fam in enumerate("TLR"):
            for i in range(3):
                rid = FAMILY_ORDER[fam] * 3 + i
                r = pygame.Rect(int(bx + col * (col_w + gap)), int(y + i * (row_h + gap)),
                                int(col_w), int(row_h))
                add(r, f"{fam}{i}", (lambda k: lambda: self.do_move(k))(rid),
                    cb_alt=(lambda k: lambda: self.do_move(k, prime=True))(rid))
        # 功能按钮
        ay = 396 * SCALE
        aw = (bw - 3 * 10 * SCALE) / 4
        add(pygame.Rect(int(bx), int(ay), int(aw), int(row_h)),
            "打乱", self.scramble, (58, 88, 66), (70, 108, 80))
        add(pygame.Rect(int(bx + aw + 10 * SCALE), int(ay), int(aw), int(row_h)),
            "重置", self.reset)
        add(pygame.Rect(int(bx + 2 * (aw + 10 * SCALE)), int(ay), int(aw), int(row_h)),
            "撤销", self.undo)
        add(pygame.Rect(int(bx + 3 * (aw + 10 * SCALE)), int(ay), int(aw), int(row_h)),
            "重做", self.redo)
        add(pygame.Rect(int(PANEL_X + PANEL_W - 96 * SCALE),
                        int(PANEL_Y + PANEL_H - 46 * SCALE),
                        int(76 * SCALE), int(32 * SCALE)),
            "退出", lambda: sys.exit(0))

    # ---------------- 操作 ----------------
    def do_move(self, ring_id, prime=False):
        direction = -1 if prime else 1
        if self.start_time is None:
            self.start_time = time.time()
        self.history.append((self.state, self.move_count, tuple(self.move_log)))
        self.redo_stack.clear()
        self.state = apply_ring(self.state, ring_id, direction)
        self.anim = RingAnim(self.history[-1][0], self.state, ring_id, direction)
        self.move_count += 1
        self.move_log.append(RING_NAMES[ring_id] + ("'" if prime else ""))
        if len(self.move_log) > 12:
            self.move_log.pop(0)
        self.solved = is_solved(self.state)
        if self.solved:
            self.elapsed = time.time() - self.start_time
            self._spawn_confetti()

    def scramble(self):
        self.history.append((self.state, self.move_count, tuple(self.move_log)))
        self.redo_stack.clear()
        moves = random_scramble(self.state, 30)
        for rid, d in moves:
            self.state = apply_ring(self.state, rid, d)
        self.anim = None
        self.move_count += len(moves)
        self.move_log = [RING_NAMES[rid] + ("'" if d < 0 else "")
                         for rid, d in moves[-12:]]
        self.start_time = time.time()
        self.elapsed = 0.0
        self.solved = False

    def reset(self):
        self.state = solved_state()
        self.history.clear()
        self.redo_stack.clear()
        self.move_count = 0
        self.move_log.clear()
        self.start_time = None
        self.elapsed = 0.0
        self.solved = True
        self.anim = None
        self.confetti.clear()

    def undo(self):
        if not self.history:
            return
        self.redo_stack.append((self.state, self.move_count, tuple(self.move_log)))
        self.state, self.move_count, log = self.history.pop()
        self.move_log = list(log)
        self.anim = None
        self.solved = is_solved(self.state)

    def redo(self):
        if not self.redo_stack:
            return
        self.history.append((self.state, self.move_count, tuple(self.move_log)))
        self.state, self.move_count, log = self.redo_stack.pop()
        self.move_log = list(log)
        self.anim = None
        self.solved = is_solved(self.state)

    def _spawn_confetti(self):
        cx = (24 + 740) / 2 * SCALE
        cy = 300 * SCALE
        for _ in range(46):
            ang = random.uniform(-math.pi, 0)
            spd = random.uniform(180, 430) * SCALE
            self.confetti.append({
                "x": cx + random.uniform(-100, 100) * SCALE,
                "y": cy,
                "vx": math.cos(ang) * spd * random.choice((-1, 1)),
                "vy": math.sin(ang) * spd,
                "color": random.choice(BRANCH_COLORS),
                "life": random.uniform(0.7, 1.5),
                "t": 0.0,
                "w": random.randint(5, 9),
            })

    # ---------------- 事件 ----------------
    def handle_event(self, ev):
        if ev.type == pygame.MOUSEBUTTONDOWN:
            if ev.button == 1:
                for b in self.buttons:
                    if b.rect.collidepoint(ev.pos):
                        b.cb()
                        return
                rid = ring_under_point(ev.pos)
                if rid is not None:
                    self.do_move(rid)
            elif ev.button == 3:
                for b in self.buttons:
                    if b.rect.collidepoint(ev.pos) and b.cb_alt:
                        b.cb_alt()
                        return
                rid = ring_under_point(ev.pos)
                if rid is not None:
                    self.do_move(rid, prime=True)
        elif ev.type == pygame.KEYDOWN:
            mods = ev.mod
            prime = bool(mods & (pygame.KMOD_SHIFT | pygame.KMOD_CAPS))
            if ev.key == pygame.K_z and (mods & pygame.KMOD_CTRL):
                self.undo()
            elif ev.key == pygame.K_y and (mods & pygame.KMOD_CTRL):
                self.redo()
            elif pygame.K_1 <= ev.key <= pygame.K_9:
                self.do_move(ev.key - pygame.K_1, prime=prime)

    def update(self, dt):
        if self.anim:
            self.anim.update(dt)
            if self.anim.done:
                self.anim = None
        if self.start_time is not None and not self.solved:
            self.elapsed = time.time() - self.start_time
        for p in self.confetti:
            p["t"] += dt
            p["vy"] += 640 * SCALE * dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
        self.confetti = [p for p in self.confetti if p["t"] < p["life"]]
        self.hover_ring = ring_under_point(pygame.mouse.get_pos())

    # ---------------- 绘制 ----------------
    def draw(self, surf):
        surf.fill(BG)
        self._draw_title(surf)
        self._draw_board(surf)
        self._draw_panel(surf)

    def _draw_title(self, surf):
        t = self.font_title.render("2D 魔方 · 三角形圆环", True, TEXT_MAIN)
        surf.blit(t, (24 * SCALE, 26 * SCALE))
        s = self.font_sm.render(
            "三个顶点各有一族同心圆，54 颗色珠位于圆环交点，转动圆环即转动魔方一层",
            True, TEXT_DIM)
        surf.blit(s, (24 * SCALE, 64 * SCALE))

    def _draw_board(self, surf):
        state = self.anim.prev if self.anim else self.state
        # 灰色圆环
        for rid in range(9):
            cx, cy = RING_CENTER[rid]
            pygame.draw.circle(surf, RING_COLOR, (int(cx), int(cy)),
                               int(RING_R[rid]), RING_WIDTH)
        # 色珠（静止层）
        for i, color in enumerate(state):
            x, y = TO_SCREEN(*BEADS[i]["pos"])
            _draw_bead(surf, x, y, color)
        # 动画层
        if self.anim:
            self.anim.draw(surf)
        # 悬停圆环高亮
        if self.hover_ring is not None:
            cx, cy = RING_CENTER[self.hover_ring]
            pygame.draw.circle(surf, RING_HOVER, (int(cx), int(cy)),
                               int(RING_R[self.hover_ring]), RING_WIDTH + 3)
            self._circular_arrow(surf, (int(cx), int(cy)),
                                 int(RING_R[self.hover_ring]) - BEAD_R,
                                 RING_HOVER, cw=True)

    @staticmethod
    def _circular_arrow(surf, center, r, color, cw=True):
        n = 30
        sweep = 1.5 * math.pi
        a0 = -math.pi / 2
        a1 = a0 + (sweep if cw else -sweep)
        pts = []
        for i in range(n + 1):
            a = a0 + (a1 - a0) * i / n
            pts.append((center[0] + r * math.cos(a), center[1] + r * math.sin(a)))
        pygame.draw.lines(surf, color, False, pts, 5)
        tip = pts[-1]
        tdir = math.pi / 2 if cw else -math.pi / 2
        dx, dy = math.cos(a1 + tdir), math.sin(a1 + tdir)
        base = (tip[0] - dx * 15, tip[1] - dy * 15)
        px, py = -dy, dx
        tri = [tip, (base[0] + px * 7, base[1] + py * 7),
               (base[0] - px * 7, base[1] - py * 7)]
        pygame.draw.polygon(surf, color, tri)

    def _draw_panel(self, surf):
        panel = pygame.Rect(PANEL_X, PANEL_Y, PANEL_W, PANEL_H)
        pygame.draw.rect(surf, PANEL_BG, panel, border_radius=14)
        pygame.draw.rect(surf, PANEL_EDGE, panel, 2, border_radius=14)
        x = PANEL_X + 20

        title = self.font_lg.render("控制台", True, TEXT_MAIN)
        surf.blit(title, (x, PANEL_Y + 16 * SCALE))

        y = PANEL_Y + 62 * SCALE
        surf.blit(self.font_md.render(
            f"用时   {int(self.elapsed // 60):02d}:{int(self.elapsed % 60):02d}",
            True, TEXT_MAIN), (x, y))
        surf.blit(self.font_md.render(f"步数   {self.move_count}", True, TEXT_MAIN),
                  (x, y + 30 * SCALE))
        state_color = (84, 205, 120) if self.solved else TEXT_MAIN
        state_txt = "已还原" if self.solved else "还原中..."
        surf.blit(self.font_md.render("状态   " + state_txt, True, state_color),
                  (x, y + 60 * SCALE))

        tip = self.font_sm.render("圆环（左键顺 / 右键逆）", True, TEXT_DIM)
        surf.blit(tip, (x, 190 * SCALE))

        for b in self.buttons:
            b.draw(surf, pygame.mouse.get_pos())

        log_txt = "最近:  " + "  ".join(self.move_log[-10:]) if self.move_log else "最近:  —"
        surf.blit(self.font_sm.render(log_txt, True, TEXT_DIM), (x, 452 * SCALE))

        hints = [
            "点击圆环转动，12 颗色珠沿环滑动",
            "键盘 1-9 对应 T0-T2/L0-L2/R0-R2",
            "Shift+数字 反向 · Ctrl+Z/Y 撤销重做",
            "目标：6 个色瓣各为一种颜色",
        ]
        hy = 496 * SCALE
        for htxt in hints:
            surf.blit(self.font_sm.render(htxt, True, TEXT_DIM), (x, hy))
            hy += 26 * SCALE

        if self.solved and self.move_count > 0:
            win = self.font_lg.render("还原成功！", True, (255, 208, 0))
            surf.blit(win, (30 * SCALE, 800 * SCALE))

        for p in self.confetti:
            alpha = max(0, 255 * (1 - p["t"] / p["life"]))
            c = p["color"]
            s = pygame.Surface((p["w"], p["w"]), pygame.SRCALPHA)
            s.fill((c[0], c[1], c[2], int(alpha)))
            surf.blit(s, (int(p["x"]), int(p["y"])))

    def run(self):
        pygame.display.set_caption("2D 魔方 · 三角形圆环版")
        pygame.display.set_icon(self._make_icon())
        screen = pygame.display.set_mode((W, H))
        clock = pygame.time.Clock()
        while True:
            dt = clock.tick(FPS) / 1000.0
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit(0)
                self.handle_event(ev)
            self.update(dt)
            self.draw(screen)
            pygame.display.flip()

    @staticmethod
    def _make_icon():
        s = pygame.Surface((64, 64), pygame.SRCALPHA)
        s.fill((0, 0, 0, 0))
        pygame.draw.circle(s, (150, 150, 150), (32, 18), 14, 2)
        pygame.draw.circle(s, (150, 150, 150), (17, 44), 14, 2)
        pygame.draw.circle(s, (150, 150, 150), (47, 44), 14, 2)
        pygame.draw.circle(s, BRANCH_COLORS[2], (32, 18), 4)
        pygame.draw.circle(s, BRANCH_COLORS[3], (17, 44), 4)
        pygame.draw.circle(s, BRANCH_COLORS[4], (47, 44), 4)
        return s


PANEL_X = int(784 * SCALE)
PANEL_Y = int(24 * SCALE)
PANEL_W = int((LOGICAL_W - 784 - 24) * SCALE)
PANEL_H = int((LOGICAL_H - 48) * SCALE)


# --------------------------------------------------------------------------
# 自检 & 截图
# --------------------------------------------------------------------------
def selftest():
    s = solved_state()
    assert is_solved(s)
    assert len(s) == 54
    assert all(len(RING_BEADS[i]) == 12 for i in range(9)), "每条环应有 12 颗"
    assert all(len(BRANCH_BEADS[i]) == 9 for i in range(6)), "每个瓣应有 9 颗"
    assert all(len(set(b["rings"])) == 2 for b in BEADS)
    for rid in range(9):
        s2 = apply_ring(s, rid, 1)
        assert not is_solved(s2), f"{RING_NAMES[rid]} 转动后不应保持还原"
        assert is_solved(apply_ring(s2, rid, -1)), "顺逆互逆"
        assert sorted(s2) == sorted(s), "转动只是置换颜色"
        s3 = apply_ring(s2, rid, 1)
        assert s3 == s or s3 != s2
    # 30 步打乱后逆序还原
    moves = random_scramble(s, 30)
    s4 = s
    for rid, d in moves:
        s4 = apply_ring(s4, rid, d)
    assert not is_solved(s4)
    for rid, d in reversed(moves):
        s4 = apply_ring(s4, rid, -d)
    assert is_solved(s4)
    print("selftest OK: 9 rings x 12 beads, 6 branches x 9 beads, inverse and scramble/reverse pass")


def screenshot(path):
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    pygame.init()
    pygame.display.set_mode((W, H))
    g = Game()
    g.draw(pygame.display.get_surface())
    pygame.image.save(pygame.display.get_surface(), path)
    print("screenshot saved:", path)
    print("scale:", round(SCALE, 2), "bead_r:", BEAD_R, "font:", g.font_md.name if hasattr(g.font_md, "name") else "ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        sys.exit(0)
    if "--screenshot" in sys.argv:
        i = sys.argv.index("--screenshot")
        screenshot(sys.argv[i + 1] if len(sys.argv) > i + 1 else "shot.png")
        sys.exit(0)
    pygame.init()
    Game().run()
