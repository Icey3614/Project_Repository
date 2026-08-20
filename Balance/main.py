"""DeepSeek 余额查看器入口。"""

import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

sys.path.insert(0, str(APP_DIR))

from deepseek_balance.app import main


if __name__ == "__main__":
    sys.exit(main(APP_DIR))
