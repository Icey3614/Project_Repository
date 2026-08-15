"""使用 Pillow 将迷宫渲染为平面俯瞰 PNG。"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from .config import Style
from .generator import WALL_E, WALL_N, WALL_S, WALL_W, Maze


def _draw_marker(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    color: str,
    ratio: float,
    cell_size: int,
    margin: int,
) -> None:
    size = max(2, int(cell_size * ratio))
    px = margin + x * cell_size + (cell_size - size) // 2
    py = margin + y * cell_size + (cell_size - size) // 2
    draw.rounded_rectangle([px, py, px + size, py + size], radius=max(2, size // 5), fill=color)


def render_maze(maze: Maze, style: Style, cell_size: int) -> Image.Image:
    """渲染迷宫俯瞰图，返回 PIL Image。"""
    margin = max(style.margin, style.wall_width)
    img_w = margin * 2 + maze.width * cell_size
    img_h = margin * 2 + maze.height * cell_size
    img = Image.new("RGB", (img_w, img_h), style.background)
    draw = ImageDraw.Draw(img)

    for y in range(maze.height):
        for x in range(maze.width):
            px = margin + x * cell_size
            py = margin + y * cell_size
            walls = maze.walls[y][x]
            if walls & WALL_N:
                draw.line([(px, py), (px + cell_size, py)], fill=style.wall_color, width=style.wall_width)
            if walls & WALL_W:
                draw.line([(px, py), (px, py + cell_size)], fill=style.wall_color, width=style.wall_width)

    # 外框右边界与下边界
    right = margin + maze.width * cell_size
    bottom = margin + maze.height * cell_size
    draw.line([(right, margin), (right, bottom)], fill=style.wall_color, width=style.wall_width)
    draw.line([(margin, bottom), (right, bottom)], fill=style.wall_color, width=style.wall_width)

    # 起点（左上，绿色）与终点（右下，红色）
    _draw_marker(draw, 0, 0, style.start_color, style.start_size_ratio, cell_size, margin)
    _draw_marker(
        draw,
        maze.width - 1,
        maze.height - 1,
        style.end_color,
        style.end_size_ratio,
        cell_size,
        margin,
    )
    return img


def render_to_file(
    maze: Maze, style: Style, cell_size: int, output_path: str | Path
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img = render_maze(maze, style, cell_size)
    img.save(path)
    return path
