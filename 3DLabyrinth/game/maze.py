"""迷宫生成与查询。

使用递归回溯（DFS）生成“完美迷宫”：任意两个格子之间只有一条通路，
因此入口到出口必然连通、不会出现死路成环。
"""

from __future__ import annotations

import random
from collections import deque


class Maze:
    """一个矩形迷宫。

    grid 是二维数组 grid[y][x]，1 表示墙、0 表示通路。
    世界坐标与网格坐标一一对应：格心为 (x+0.5, y+0.5)，每格边长为 1。
    """

    def __init__(self, cols: int, rows: int, seed: int | None = None):
        self.cols = cols  # 单元格列数
        self.rows = rows  # 单元格行数
        self.seed = seed if seed is not None else random.randrange(1 << 30)
        self.rng = random.Random(self.seed)
        self.grid: list[list[int]] = []
        self.start: tuple[float, float] = (0.0, 0.0)
        self.goal: tuple[float, float] = (0.0, 0.0)
        self.entrance_walls: set[tuple[int, int]] = set()
        self.exit_walls: set[tuple[int, int]] = set()
        self._generate()

    @property
    def width(self) -> int:
        return len(self.grid[0])

    @property
    def height(self) -> int:
        return len(self.grid)

    def _generate(self) -> None:
        w = self.cols * 2 + 1
        h = self.rows * 2 + 1
        grid = [[1] * w for _ in range(h)]

        # 递归回溯：从左上角格子开始挖通路
        grid[1][1] = 0
        stack = [(1, 1)]
        while stack:
            cx, cy = stack[-1]
            candidates = []
            for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                nx, ny = cx + dx, cy + dy
                if 0 < nx < w - 1 and 0 < ny < h - 1 and grid[ny][nx] == 1:
                    candidates.append((nx, ny))
            if candidates:
                nx, ny = self.rng.choice(candidates)
                grid[cy + (ny - cy) // 2][cx + (nx - cx) // 2] = 0
                grid[ny][nx] = 0
                stack.append((nx, ny))
            else:
                stack.pop()

        # 入口：迷宫上边缘第一个格子；出口：迷宫下边缘最后一个格子
        grid[0][1] = 0
        grid[h - 1][w - 2] = 0
        self.grid = grid

        # 玩家出生在入口开口中心，出口判定中心在底部开口
        self.start = (1.5, 0.5)
        self.goal = (w - 1.5, h - 0.5)

        # 入口/出口附近的墙体用于特殊着色，方便辨认
        self.entrance_walls = {(0, 0), (2, 0), (0, 1), (2, 1)}
        self.exit_walls = {
            (w - 3, h - 1), (w - 1, h - 1),
            (w - 3, h - 2), (w - 1, h - 2),
        }

    def is_wall(self, gx: int, gy: int) -> bool:
        """越界一律视为墙。"""
        if gx < 0 or gy < 0 or gx >= self.width or gy >= self.height:
            return True
        return bool(self.grid[gy][gx])

    def in_goal(self, x: float, y: float, radius: float = 0.5) -> bool:
        gx, gy = self.goal
        return (x - gx) ** 2 + (y - gy) ** 2 <= radius * radius

    def solve(self) -> list[tuple[int, int]] | None:
        """BFS 求入口到出口的路径（用于自检与后续扩展）。"""
        start = (1, 1)
        goal = (self.width - 2, self.height - 2)
        queue = deque([start])
        prev = {start: None}
        while queue:
            cur = queue.popleft()
            if cur == goal:
                break
            cx, cy = cur
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nxt = (cx + dx, cy + dy)
                if nxt not in prev and not self.is_wall(*nxt):
                    prev[nxt] = cur
                    queue.append(nxt)
        else:
            return None
        path: list[tuple[int, int]] = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = prev[cur]
        return path[::-1]
