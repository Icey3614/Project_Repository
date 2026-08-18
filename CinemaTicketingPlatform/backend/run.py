"""桌面端后端入口：启动 uvicorn（也用于 PyInstaller 打包）。"""

import argparse
import os
import sys

import app.main  # noqa: F401  确保打包时收集整个应用
import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=int(os.environ.get("CINEMA_PORT", "8000")))
    args = parser.parse_args()
    uvicorn.run("app.main:app", host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    sys.exit(main())
