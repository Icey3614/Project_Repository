"""命令行入口。"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from . import __version__
from .config import ALGORITHMS, SIZE_KEYS, Settings, load_settings
from .generator import generate_maze
from .renderer import render_to_file


def _fix_io() -> None:
    """windowed exe 中 stdout/stderr 为 None，重定向到 devnull 避免 print 崩溃。"""
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="maze",
        description="迷宫生成器（平面俯瞰），支持小/中/大/超大四种规模随机生成。",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "--settings",
        metavar="PATH",
        default=None,
        help="设置文件路径（默认自动查找 settings.json）",
    )

    sub = parser.add_subparsers(dest="command")

    gen = sub.add_parser("generate", help="生成迷宫并保存为 PNG")
    gen.add_argument(
        "--size",
        choices=SIZE_KEYS,
        default=None,
        help=f"规模预设: {', '.join(SIZE_KEYS)}",
    )
    gen.add_argument("--width", type=int, default=None, help="自定义宽度（格数）")
    gen.add_argument("--height", type=int, default=None, help="自定义高度（格数）")
    gen.add_argument("--algorithm", choices=ALGORITHMS, default=None, help="生成算法")
    gen.add_argument("--seed", type=int, default=None, help="随机种子；不填则每次随机")
    gen.add_argument("--cell-size", type=int, default=None, help="每个格子的像素大小")
    gen.add_argument("--output", default=None, help="输出 PNG 路径")

    sub.add_parser("gui", help="打开图形界面")
    return parser


def cmd_generate(args: argparse.Namespace, settings: Settings) -> int:
    preset = settings.get_preset(args.size)
    width = args.width or preset.width
    height = args.height or preset.height
    cell_size = args.cell_size or preset.cell_size
    algorithm = args.algorithm or settings.algorithm
    seed = args.seed if args.seed is not None else settings.seed

    maze = generate_maze(width, height, algorithm=algorithm, seed=seed)
    out = Path(args.output) if args.output else settings.output_dir / settings.output_name
    render_to_file(maze, settings.style, cell_size, out)
    print(f"已生成 {width} x {height} 迷宫 -> {out}")
    print(f"  算法: {algorithm} | 种子: {maze.seed}")
    return 0


def main(argv: list[str] | None = None) -> int:
    _fix_io()
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        settings = load_settings(args.settings)
    except (OSError, ValueError) as exc:
        print(f"设置加载失败: {exc}", file=sys.stderr)
        return 2

    if args.command == "generate":
        return cmd_generate(args, settings)
    if args.command == "gui" or not argv:
        import tkinter as tk

        from .gui import MazeApp, enable_dpi_awareness

        enable_dpi_awareness()  # 必须在创建 Tk 窗口前调用
        root = tk.Tk()
        MazeApp(root, settings)
        root.mainloop()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
