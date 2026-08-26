"""光线投射渲染器。

经典 Wolfenstein 风格第一人称渲染：逐列发射射线求墙距，按距离取纹理列
缩放绘制，并用 Z 缓冲区保证出口/入口标记不被墙体遮挡。
"""

from __future__ import annotations

import math
import random
from typing import TYPE_CHECKING

import pygame

from . import config as C

if TYPE_CHECKING:
    from .maze import Maze
    from .player import Player

try:
    import numpy as np
except ImportError:  # numpy 可选：没有时自动回退到纯 Python 渲染
    np = None

TS = C.TEXTURE_SIZE


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _brick_texture(base, mortar, noise_seed: int = 7):
    """程序化生成砖墙纹理。"""
    surf = pygame.Surface((TS, TS))
    surf.fill(mortar)
    brick_h, brick_w = 16, 32
    for by in range(0, TS, brick_h):
        offset = 0 if (by // brick_h) % 2 == 0 else brick_w // 2
        for bx in range(-brick_w, TS, brick_w):
            rect = pygame.Rect(bx + offset + 1, by + 1, brick_w - 2, brick_h - 2)
            pygame.draw.rect(surf, base, rect)
            hi = tuple(_clamp(c + 26, 0, 255) for c in base)
            lo = tuple(_clamp(c - 18, 0, 255) for c in base)
            pygame.draw.line(surf, hi, (rect.left, rect.top), (rect.right - 1, rect.top))
            pygame.draw.line(surf, lo, (rect.left, rect.bottom - 1), (rect.right - 1, rect.bottom - 1))
    # 轻微噪点，让墙面不那么呆板
    rng = random.Random(noise_seed)
    px = pygame.PixelArray(surf)
    for _ in range(TS * TS // 8):
        x, y = rng.randrange(TS), rng.randrange(TS)
        c = surf.unmap_rgb(px[x, y])
        d = rng.randint(-9, 9)
        px[x, y] = (_clamp(c.r + d, 0, 255), _clamp(c.g + d, 0, 255), _clamp(c.b + d, 0, 255))
    del px
    return surf


def _shaded_variants(base, tint=None):
    """生成一组距离明暗变体；tint 为叠加色（入口蓝 / 出口绿）。"""
    out = []
    for i in range(C.SHADE_LEVELS):
        f = 1.0 - i / (C.SHADE_LEVELS * 1.7)
        v = max(0, min(255, int(255 * f)))
        s = base.copy()
        s.fill((v, v, v), special_flags=pygame.BLEND_RGB_MULT)
        if tint is not None:
            s.fill(tint, special_flags=pygame.BLEND_RGB_ADD)
        out.append(s)
    return out


def _make_ring_sprite(color, inner, radius: int = 26, width: int = 5, glow=None):
    """生成出口/入口的悬浮标记（环形）。"""
    surf = pygame.Surface((64, 64), pygame.SRCALPHA)
    if glow is not None:
        pygame.draw.circle(surf, glow, (32, 32), radius + 9)
    pygame.draw.circle(surf, color, (32, 32), radius, width)
    pygame.draw.circle(surf, inner, (32, 32), 9)
    return surf


class Renderer:
    # 纹理/贴图列在所有渲染器实例间共享（切换窗口/全屏时无需重建，避免卡顿）
    _shared = None

    def __init__(self, width: int, height: int, fov_deg: float = 66.0,
                 use_numpy: bool | None = None):
        self.w = width
        self.h = height
        self.fov_deg = fov_deg
        self.plane_scale = math.tan(math.radians(fov_deg / 2))
        self.zbuffer = [0.0] * width
        # 每列的相机偏移是常量，预计算一次，省去逐帧除法
        cam_xs = [(2.0 * x / width - 1.0) for x in range(width)]
        self.use_numpy = (np is not None) if use_numpy is None else (use_numpy and np is not None)
        self.cam_xs = np.array(cam_xs, dtype=np.float64) if self.use_numpy else cam_xs

        if Renderer._shared is None:
            base_wall = _brick_texture((146, 116, 78), (98, 76, 50))
            textures = {
                "normal": _shaded_variants(base_wall),
                "entrance": _shaded_variants(base_wall, tint=(20, 60, 160)),
                "exit": _shaded_variants(base_wall, tint=(30, 160, 70)),
            }
            # 预切出每个明暗等级、每个纹理 x 的 1 像素列，逐帧只做缩放
            columns = {
                kind: [
                    [tex.subsurface((tx, 0, 1, TS)) for tx in range(TS)]
                    for tex in variants
                ]
                for kind, variants in textures.items()
            }
            # 墙顶面纹理（站在墙上/高处时可见）
            top_wall = _brick_texture((128, 124, 116), (94, 90, 82), noise_seed=21)
            top_columns = [
                [tex.subsurface((tx, 0, 1, TS)) for tx in range(TS)]
                for tex in _shaded_variants(top_wall)
            ]
            Renderer._shared = (textures, columns, top_columns)
        self.textures, self.columns, self.top_columns = Renderer._shared

        self.goal_sprite = _make_ring_sprite(
            (90, 235, 120, 255), (255, 255, 255, 230),
            radius=26, width=5, glow=(40, 150, 70, 90),
        )
        self.start_sprite = _make_ring_sprite(
            (110, 170, 255, 255), (255, 255, 255, 200), radius=20, width=4,
        )

        self.ceiling = self._vertical_gradient((124, 148, 176), (50, 58, 70))
        self.floor = self._vertical_gradient((42, 42, 48), (98, 98, 104))

    def _vertical_gradient(self, top, bottom) -> pygame.Surface:
        surf = pygame.Surface((self.w, self.h))
        for y in range(self.h):
            t = y / max(1, self.h - 1)
            c = tuple(int(a + (b - a) * t) for a, b in zip(top, bottom))
            pygame.draw.line(surf, c, (0, y), (self.w - 1, y))
        return surf

    def render(self, screen: pygame.Surface, maze: "Maze", player: "Player") -> None:
        """按 numpy 是否可用选择渲染路径。"""
        if self.use_numpy:
            self._render_numpy(screen, maze, player)
        else:
            self._render_python(screen, maze, player)

    def _render_numpy(self, screen: pygame.Surface, maze: "Maze", player: "Player") -> None:
        """numpy 向量化光线投射：整批列同时推进 DDA，逐列只剩贴图绘制。"""
        w, h = self.w, self.h
        dir_x, dir_y = math.cos(player.yaw), math.sin(player.yaw)
        plane_x, plane_y = -dir_y * self.plane_scale, dir_x * self.plane_scale
        px, py = player.x, player.y
        cam_eye = C.EYE_HEIGHT + player.z

        # 俯仰：整个画面沿垂直方向平移（抬头画面下移，低头画面上移）
        pitch_shift = int(math.tan(player.pitch) * h * 0.75)
        horizon = int(_clamp(h / 2 + pitch_shift, 0, h))
        if horizon > 0:
            screen.blit(self.ceiling, (0, 0), (0, 0, w, horizon))
        if horizon < h:
            screen.blit(self.floor, (0, horizon), (0, horizon, w, h - horizon))

        mw, mh = maze.width, maze.height
        grid = np.asarray(maze.grid, dtype=np.uint8)
        kind_grid = np.zeros((mh, mw), dtype=np.int8)
        for gx, gy in maze.entrance_walls:
            kind_grid[gy, gx] = 1
        for gx, gy in maze.exit_walls:
            kind_grid[gy, gx] = 2

        cam = self.cam_xs
        rdx = dir_x + plane_x * cam
        rdy = dir_y + plane_y * cam

        map_x = np.full(w, int(px), dtype=np.int64)
        map_y = np.full(w, int(py), dtype=np.int64)

        delta_x = np.full(w, 1e30)
        delta_y = np.full(w, 1e30)
        nz = rdx != 0
        delta_x[nz] = np.abs(1.0 / rdx[nz])
        nz = rdy != 0
        delta_y[nz] = np.abs(1.0 / rdy[nz])

        step_x = np.where(rdx < 0, -1, 1).astype(np.int64)
        step_y = np.where(rdy < 0, -1, 1).astype(np.int64)

        side_x = np.where(rdx < 0, (px - map_x) * delta_x, (map_x + 1 - px) * delta_x)
        side_y = np.where(rdy < 0, (py - map_y) * delta_y, (map_y + 1 - py) * delta_y)

        hit = np.zeros(w, dtype=bool)
        side = np.zeros(w, dtype=np.int8)
        perp = np.full(w, 1e30)

        # 所有列同步推进 DDA，命中/越界的列被屏蔽
        for _ in range(mw + mh):
            active = ~hit
            if not active.any():
                break
            cross = side_x < side_y
            sxm = cross & active
            sym = (~cross) & active
            map_x += step_x * sxm.astype(np.int64)
            map_y += step_y * sym.astype(np.int64)
            side_x += delta_x * sxm
            side_y += delta_y * sym
            side = np.where(sxm, 0, 1)

            gx = np.clip(map_x, 0, mw - 1)
            gy = np.clip(map_y, 0, mh - 1)
            wall = grid[gy, gx] > 0
            out = (map_x < 0) | (map_x >= mw) | (map_y < 0) | (map_y >= mh)
            newly = active & (wall | out)
            wnew = newly & wall
            if wnew.any():
                perp[wnew] = np.where(side[wnew] == 0,
                                      side_x[wnew] - delta_x[wnew],
                                      side_y[wnew] - delta_y[wnew])
            hit |= newly

        self.zbuffer[:] = perp.tolist()
        valid_idx = np.nonzero(perp < 1e29)[0]
        if valid_idx.size:
            pv = perp[valid_idx]
            sd = side[valid_idx]
            rx = rdx[valid_idx]
            ry = rdy[valid_idx]
            mx = map_x[valid_idx]
            my = map_y[valid_idx]

            # 视线高度变化：墙顶/墙底在屏幕上的投影行（h 即焦距像素）
            inv_pv = 1.0 / np.maximum(pv, 1e-4)
            top_row = horizon + h * (cam_eye - C.WALL_HEIGHT) * inv_pv
            bottom_row = horizon + h * cam_eye * inv_pv
            line_h = np.rint(bottom_row - top_row).astype(np.int64)
            line_h = np.maximum(line_h, 1)
            # 上限保护：距离极小（贴墙/墙格内）时避免生成超大贴图列导致卡死
            line_h = np.minimum(line_h, h * 4)
            draw_start = np.rint(top_row).astype(np.int64)
            show_top = cam_eye > C.WALL_HEIGHT + 0.001
            far_row = horizon + h * (cam_eye - C.WALL_HEIGHT) / (np.maximum(pv, 1e-4) + 1.0)
            band_h = np.rint(top_row - far_row).astype(np.int64)
            band_h = np.maximum(band_h, 0)
            band_h = np.minimum(band_h, h * 2)

            wall_x = np.where(sd == 0, py + pv * ry, px + pv * rx)
            wall_x -= np.floor(wall_x)
            tex_x = (wall_x * TS).astype(np.int64)
            tex_x = np.minimum(tex_x, TS - 1)
            flip = ((sd == 0) & (rx > 0)) | ((sd == 1) & (ry < 0))
            tex_x[flip] = TS - 1 - tex_x[flip]

            level = (pv * C.SHADE_PER_UNIT).astype(np.int64)
            level += (sd == 1).astype(np.int64)
            np.clip(level, 0, C.SHADE_LEVELS - 1, out=level)

            kind = kind_grid[np.clip(my, 0, mh - 1), np.clip(mx, 0, mw - 1)]
            column_sets = (self.columns["normal"],
                           self.columns["entrance"],
                           self.columns["exit"])
            top_columns = self.top_columns
            for i, x in enumerate(valid_idx):
                lh = int(line_h[i])
                src = column_sets[kind[i]][level[i]][tex_x[i]]
                screen.blit(pygame.transform.scale(src, (1, lh)), (x, int(draw_start[i])))
                if show_top and band_h[i] > 0:
                    tsrc = top_columns[level[i]][tex_x[i]]
                    screen.blit(pygame.transform.scale(tsrc, (1, int(band_h[i]))),
                                (x, int(round(float(far_row[i])))))

        # 出口 / 入口标记（带 Z 缓冲，避免被墙挡住时仍画出）
        self._draw_sprite(screen, maze.goal, self.goal_sprite,
                          px, py, dir_x, dir_y, plane_x, plane_y, horizon, cam_eye)
        self._draw_sprite(screen, maze.start, self.start_sprite,
                          px, py, dir_x, dir_y, plane_x, plane_y, horizon, cam_eye)

    def _render_python(self, screen: pygame.Surface, maze: "Maze", player: "Player") -> None:
        w, h = self.w, self.h
        dir_x, dir_y = math.cos(player.yaw), math.sin(player.yaw)
        plane_x, plane_y = -dir_y * self.plane_scale, dir_x * self.plane_scale
        px, py = player.x, player.y
        cam_eye = C.EYE_HEIGHT + player.z

        # 俯仰：整个画面沿垂直方向平移（抬头画面下移，低头画面上移）
        pitch_shift = int(math.tan(player.pitch) * h * 0.75)
        horizon = int(_clamp(h / 2 + pitch_shift, 0, h))
        if horizon > 0:
            screen.blit(self.ceiling, (0, 0), (0, 0, w, horizon))
        if horizon < h:
            screen.blit(self.floor, (0, horizon), (0, horizon, w, h - horizon))

        grid = maze.grid
        mw, mh = maze.width, maze.height
        zbuf = self.zbuffer
        entrance_walls = maze.entrance_walls
        exit_walls = maze.exit_walls
        columns = self.columns
        cam_xs = self.cam_xs

        for x in range(w):
            cam = cam_xs[x]
            rdx = dir_x + plane_x * cam
            rdy = dir_y + plane_y * cam

            map_x, map_y = int(px), int(py)
            delta_x = abs(1 / rdx) if rdx else 1e30
            delta_y = abs(1 / rdy) if rdy else 1e30

            if rdx < 0:
                step_x, side_x = -1, (px - map_x) * delta_x
            else:
                step_x, side_x = 1, (map_x + 1 - px) * delta_x
            if rdy < 0:
                step_y, side_y = -1, (py - map_y) * delta_y
            else:
                step_y, side_y = 1, (map_y + 1 - py) * delta_y

            side = 0
            while True:
                if side_x < side_y:
                    side_x += delta_x
                    map_x += step_x
                    side = 0
                else:
                    side_y += delta_y
                    map_y += step_y
                    side = 1
                if map_x < 0 or map_x >= mw or map_y < 0 or map_y >= mh:
                    perp = 1e30
                    break
                if grid[map_y][map_x]:
                    perp = side_x - delta_x if side == 0 else side_y - delta_y
                    break

            zbuf[x] = perp
            if perp >= 1e29:
                continue

            # 视线高度变化：墙顶/墙底在屏幕上的投影行
            top_row = horizon + h * (cam_eye - C.WALL_HEIGHT) / max(perp, 1e-4)
            bottom_row = horizon + h * cam_eye / max(perp, 1e-4)
            line_h = max(1, min(int(round(bottom_row - top_row)), h * 4))
            draw_start = int(round(top_row))

            # 纹理横坐标
            if side == 0:
                wall_x = py + perp * rdy
            else:
                wall_x = px + perp * rdx
            wall_x -= math.floor(wall_x)
            tex_x = int(wall_x * TS)
            if (side == 0 and rdx > 0) or (side == 1 and rdy < 0):
                tex_x = TS - 1 - tex_x

            cell = (map_x, map_y)
            if cell in entrance_walls:
                kind = "entrance"
            elif cell in exit_walls:
                kind = "exit"
            else:
                kind = "normal"

            level = int(perp * C.SHADE_PER_UNIT)
            if side == 1:
                level += 1
            level = max(0, min(C.SHADE_LEVELS - 1, level))

            src = columns[kind][level][tex_x]
            screen.blit(pygame.transform.scale(src, (1, line_h)), (x, draw_start))
            if cam_eye > C.WALL_HEIGHT + 0.001:
                far_row = horizon + h * (cam_eye - C.WALL_HEIGHT) / (max(perp, 1e-4) + 1.0)
                band_h = min(int(round(top_row - far_row)), h * 2)
                if band_h > 0:
                    tsrc = self.top_columns[level][tex_x]
                    screen.blit(pygame.transform.scale(tsrc, (1, band_h)),
                                (x, int(round(far_row))))

        # 出口 / 入口标记（带 Z 缓冲，避免被墙挡住时仍画出）
        self._draw_sprite(screen, maze.goal, self.goal_sprite,
                          px, py, dir_x, dir_y, plane_x, plane_y, horizon, cam_eye)
        self._draw_sprite(screen, maze.start, self.start_sprite,
                          px, py, dir_x, dir_y, plane_x, plane_y, horizon, cam_eye)

    def _draw_sprite(
        self, screen, pos, sprite, px, py,
        dir_x, dir_y, plane_x, plane_y, horizon, cam_eye,
    ) -> None:
        w, h = self.w, self.h
        sx, sy = pos[0] - px, pos[1] - py
        dist = math.hypot(sx, sy)
        if dist < 1.5:
            return  # 标记就在脚下，无需绘制
        inv = 1.0 / (plane_x * dir_y - dir_x * plane_y)
        tx = inv * (dir_y * sx - dir_x * sy)
        ty = inv * (-plane_y * sx + plane_x * sy)
        if ty <= 0.1:
            return
        screen_x = int((w / 2) * (1 + tx / ty))
        size = max(1, min(int(abs(h / ty)), 4096))
        if screen_x < -size or screen_x > w + size:
            return
        scaled = pygame.transform.scale(sprite, (size, size))
        half = size // 2
        x0 = max(0, screen_x - half)
        x1 = min(w, screen_x + half)
        # 视线高度越高，地面附近的标记越靠下
        center_y = horizon + int(h * (cam_eye - 0.5) / ty)
        top = center_y - half
        for cx in range(x0, x1):
            if ty < self.zbuffer[cx]:
                strip = scaled.subsurface((cx - (screen_x - half), 0, 1, size))
                screen.blit(strip, (cx, top))
