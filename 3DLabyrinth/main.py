"""3D 迷宫游戏入口。

用法：
    python main.py            启动游戏
    python main.py --seed 42  固定迷宫种子（可复现同一迷宫）
    python main.py --selftest 无头自检（验证生成/渲染/界面）
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="3D 迷宫游戏")
    parser.add_argument("--seed", type=int, default=None, help="固定迷宫种子")
    parser.add_argument("--selftest", action="store_true", help="无头自检")
    parser.add_argument("--qa-dir", default=None, help="自检时把界面截图保存到该目录")
    args = parser.parse_args()

    if args.selftest:
        from game.selftest import run
        run(qa_dir=args.qa_dir)
        return

    from game.app import App
    App(seed=args.seed).run()


if __name__ == "__main__":
    main()
