"""迷宫生成算法。

提供两种生成“完美迷宫”（任意两点之间有且仅有一条通路）的算法：
- recursive_backtracker：递归回溯（迭代式 DFS），生成蜿蜒曲折的迷宫；
- randomized_prim：随机 Prim，生成分支更均匀的迷宫。
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Callable, Iterator

# 四面墙的位掩码
WALL_N = 1
WALL_E = 2
WALL_S = 4
WALL_W = 8
ALL_WALLS = WALL_N | WALL_E | WALL_S | WALL_W

# 方向 -> (dx, dy, 当前格墙位, 相邻格墙位)
DIRECTIONS: dict[str, tuple[int, int, int, int]] = {
    "n": (0, -1, WALL_N, WALL_S),
    "s": (0, 1, WALL_S, WALL_N),
    "e": (1, 0, WALL_E, WALL_W),
    "w": (-1, 0, WALL_W, WALL_E),
}


@dataclass
class Maze:
    """迷宫数据：walls[y][x] 是 (x, y) 单元格四周墙的位掩码。"""

    width: int
    height: int
    walls: list[list[int]]
    algorithm: str
    seed: int

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def neighbors(self, x: int, y: int) -> Iterator[tuple[int, int]]:
        """返回与 (x, y) 相邻、且之间没有墙的格子。"""
        for dx, dy, here, _there in DIRECTIONS.values():
            nx, ny = x + dx, y + dy
            if self.in_bounds(nx, ny) and not (self.walls[y][x] & here):
                yield nx, ny

    def is_perfect(self) -> bool:
        """校验：所有格子连通，且通道数 = 格子数 - 1（生成树，无回路）。"""
        if self.width < 1 or self.height < 1:
            return False
        total = self.width * self.height
        openings = 0
        for y in range(self.height):
            for x in range(self.width):
                walls = self.walls[y][x]
                if not (walls & WALL_E) and x + 1 < self.width:
                    openings += 1
                if not (walls & WALL_S) and y + 1 < self.height:
                    openings += 1
        if openings != total - 1:
            return False
        # BFS：从左上角出发，应能到达所有格子
        visited = [[False] * self.width for _ in range(self.height)]
        stack = [(0, 0)]
        visited[0][0] = True
        count = 1
        while stack:
            x, y = stack.pop()
            for nx, ny in self.neighbors(x, y):
                if not visited[ny][nx]:
                    visited[ny][nx] = True
                    count += 1
                    stack.append((nx, ny))
        return count == total


def _new_walls(width: int, height: int) -> list[list[int]]:
    return [[ALL_WALLS] * width for _ in range(height)]


def generate_recursive_backtracker(
    width: int, height: int, rng: random.Random
) -> list[list[int]]:
    walls = _new_walls(width, height)
    visited = [[False] * width for _ in range(height)]
    visited[0][0] = True
    stack = [(0, 0)]
    order = list(DIRECTIONS.items())
    while stack:
        x, y = stack[-1]
        rng.shuffle(order)
        for _name, (dx, dy, here, there) in order:
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and not visited[ny][nx]:
                walls[y][x] &= ~here
                walls[ny][nx] &= ~there
                visited[ny][nx] = True
                stack.append((nx, ny))
                break
        else:
            stack.pop()
    return walls


def generate_randomized_prim(
    width: int, height: int, rng: random.Random
) -> list[list[int]]:
    walls = _new_walls(width, height)
    visited = [[False] * width for _ in range(height)]
    # frontier 元素: (候选格 x, y, 已加入格的 x, y, 方向 dx, dy)
    frontier: list[tuple[int, int, int, int, int, int]] = []

    def add_frontier(x: int, y: int) -> None:
        for dx, dy, _here, _there in DIRECTIONS.values():
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and not visited[ny][nx]:
                frontier.append((nx, ny, x, y, dx, dy))

    visited[0][0] = True
    add_frontier(0, 0)
    while frontier:
        idx = rng.randrange(len(frontier))
        nx, ny, px, py, dx, dy = frontier.pop(idx)
        if visited[ny][nx]:
            continue
        visited[ny][nx] = True
        for _name, (ddx, ddy, here, there) in DIRECTIONS.items():
            if ddx == dx and ddy == dy:
                walls[py][px] &= ~here
                walls[ny][nx] &= ~there
                break
        add_frontier(nx, ny)
    return walls


ALGORITHM_FUNCS: dict[str, Callable[[int, int, random.Random], list[list[int]]]] = {
    "recursive_backtracker": generate_recursive_backtracker,
    "randomized_prim": generate_randomized_prim,
}
ALGORITHMS = tuple(ALGORITHM_FUNCS)


def generate_maze(
    width: int,
    height: int,
    algorithm: str = "recursive_backtracker",
    seed: int | None = None,
) -> Maze:
    """生成迷宫。

    seed 为 None 时使用系统随机源选取种子（每次结果不同）；
    指定 seed 后结果可复现。
    """
    if width < 2 or height < 2:
        raise ValueError("迷宫尺寸至少为 2x2")
    if algorithm not in ALGORITHM_FUNCS:
        raise ValueError(f"未知算法: {algorithm}，可选: {', '.join(ALGORITHMS)}")
    if seed is None:
        seed = random.SystemRandom().randrange(2**32)
    rng = random.Random(seed)
    walls = ALGORITHM_FUNCS[algorithm](width, height, rng)
    return Maze(
        width=width,
        height=height,
        walls=walls,
        algorithm=algorithm,
        seed=seed,
    )
