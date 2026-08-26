"""玩家：位置、朝向、移动、跳跃与碰撞。"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from . import config as C

if TYPE_CHECKING:
    from .maze import Maze


class Player:
    def __init__(self, x: float, y: float, yaw: float = 0.0):
        self.x = x
        self.y = y
        self.z = 0.0            # 高度：0 = 地面，1.0 = 墙顶
        self.vz = 0.0           # 垂直速度
        self.grounded = True
        self.yaw = yaw          # 水平朝向（弧度），0 = 面向 +x
        self.pitch = 0.0        # 俯仰角（弧度），正值抬头
        self.radius = C.PLAYER_RADIUS
        self.speed = C.WALK_SPEED
        self.sprint_active = False
        self._last_forward = -10.0
        self._sprint_idle = 0.0
        self.just_jumped = False
        self.just_landed = False

    def on_forward_press(self, now: float) -> None:
        """双击前进键（W / ↑）进入奔跑状态。"""
        if now - self._last_forward < C.DOUBLE_TAP_WINDOW:
            self.sprint_active = True
        self._last_forward = now

    def update(
        self,
        forward: float,
        strafe: float,
        dt: float,
        maze: "Maze",
        sprint_hold: bool = False,
        jump: bool = False,
    ) -> None:
        """逐帧更新。forward/strafe ∈ [-1, 1]，相对玩家朝向。"""
        self.just_jumped = False
        self.just_landed = False

        # 奔跑：双击激活；停止前进一段时间后自动退出
        if forward > 0:
            self._sprint_idle = 0.0
        elif self.sprint_active:
            self._sprint_idle += dt
            if self._sprint_idle > C.SPRINT_TIMEOUT:
                self.sprint_active = False

        speed = self.speed
        if (sprint_hold or self.sprint_active) and forward > 0:
            speed *= C.SPRINT_MULTIPLIER

        fx, fy = math.cos(self.yaw), math.sin(self.yaw)
        rx, ry = -fy, fx
        if forward or strafe:
            length = math.hypot(forward, strafe)
            dx = (fx * forward + rx * strafe) / length
            dy = (fy * forward + ry * strafe) / length
        else:
            dx = dy = 0.0
        step = speed * dt

        # ---------- 水平移动 ----------
        on_wall_top = self.grounded and self.z >= C.WALL_HEIGHT - 0.001

        if self.grounded:
            if on_wall_top:
                # 墙顶：自由移动，仅受迷宫边界空气墙限制
                self.x = max(self.radius, min(float(maze.width) - self.radius,
                                              self.x + dx * step))
                self.y = max(self.radius, min(float(maze.height) - self.radius,
                                              self.y + dy * step))
                if not maze.is_wall(int(self.x), int(self.y)):
                    self.grounded = False  # 走出墙缘，进入坠落
            else:
                nx = self.x + dx * step
                if not self._collides(nx, self.y, maze):
                    self.x = nx
                ny = self.y + dy * step
                if not self._collides(self.x, ny, maze):
                    self.y = ny
        elif self.z >= C.CLEARANCE_HEIGHT:
            # 高空：可越过墙体，但不能超出迷宫边界（空气墙）
            self.x = max(self.radius, min(float(maze.width) - self.radius,
                                          self.x + dx * step))
            self.y = max(self.radius, min(float(maze.height) - self.radius,
                                          self.y + dy * step))
        else:
            # 低空：仍受墙体阻挡，避免贴地穿墙
            nx = self.x + dx * step
            if not self._collides(nx, self.y, maze):
                self.x = nx
            ny = self.y + dy * step
            if not self._collides(self.x, ny, maze):
                self.y = ny

        # ---------- 垂直运动 ----------
        prev_z = self.z
        if jump and self.grounded:
            self.vz = C.JUMP_SPEED
            self.grounded = False
            self.just_jumped = True

        if not self.grounded:
            self.vz -= C.GRAVITY * dt
            self.z += self.vz * dt
            under_wall = maze.is_wall(int(self.x), int(self.y))
            if self.vz <= 0:
                if under_wall and self.z <= C.WALL_HEIGHT:
                    self.z = C.WALL_HEIGHT
                    self.vz = 0.0
                    self.grounded = True
                    self.just_landed = True
                elif self.z <= 0.0:
                    self.z = 0.0
                    self.vz = 0.0
                    self.grounded = True
                    self.just_landed = True
            elif under_wall and prev_z < C.WALL_HEIGHT - 0.001 and self.z >= C.WALL_HEIGHT:
                self.z = C.WALL_HEIGHT
                self.vz = 0.0
                self.grounded = True
                self.just_landed = True

    def _collides(self, x: float, y: float, maze: "Maze") -> bool:
        """圆形 vs 网格碰撞（越界视为墙）。"""
        r = self.radius
        x0 = math.floor(x - r)
        x1 = math.floor(x + r)
        y0 = math.floor(y - r)
        y1 = math.floor(y + r)
        for gy in range(y0, y1 + 1):
            for gx in range(x0, x1 + 1):
                if maze.is_wall(gx, gy):
                    return True
        return False
