"""迷宫生成器入口。

用法：
    python main.py gui                          # 打开图形界面
    python main.py generate --size medium       # 生成 PNG（默认随机）
    python main.py generate --seed 42 --size large --output out.png
"""

from maze.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
