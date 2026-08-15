"""迷宫寻路：BFS 最短路径，保证不穿墙。"""

from __future__ import annotations

from collections import deque

from .generator import Maze


def find_path(
    maze: Maze, start: tuple[int, int], goal: tuple[int, int]
) -> list[tuple[int, int]] | None:
    """返回 start 到 goal 的最短路径（含起终点），无法到达时返回 None。"""
    if not (maze.in_bounds(*start) and maze.in_bounds(*goal)):
        return None
    if start == goal:
        return [start]

    prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    queue: deque[tuple[int, int]] = deque([start])
    while queue:
        current = queue.popleft()
        if current == goal:
            break
        for nxt in maze.neighbors(*current):
            if nxt not in prev:
                prev[nxt] = current
                queue.append(nxt)

    if goal not in prev:
        return None

    path: list[tuple[int, int]] = []
    current: tuple[int, int] | None = goal
    while current is not None:
        path.append(current)
        current = prev[current]
    path.reverse()
    return path
