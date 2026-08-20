"""应用入口逻辑。"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from .config import load_config
from .ui import APP_STYLE, MainWindow, SettingsDialog


def _arg_value(args: list[str], flag: str) -> str | None:
    if flag in args:
        index = args.index(flag)
        if index + 1 < len(args):
            return args[index + 1]
    return None


def _arg_int(args: list[str], flag: str) -> int | None:
    value = _arg_value(args, flag)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _load_icon(app_dir: Path) -> QIcon | None:
    """加载应用图标：打包后从 _MEIPASS 读取，源码运行从 assets 读取。"""
    if getattr(sys, "frozen", False):
        icon_path = Path(sys._MEIPASS) / "assets" / "icon.ico"
    else:
        icon_path = app_dir / "assets" / "icon.ico"
    if icon_path.exists():
        return QIcon(str(icon_path))
    return None


def main(app_dir: Path) -> int:
    args = sys.argv[1:]
    demo = "--demo" in args
    shot_main = _arg_value(args, "--screenshot")
    shot_settings = _arg_value(args, "--screenshot-settings")
    grab_main = _arg_value(args, "--grab")
    grab_settings = _arg_value(args, "--grab-settings")
    pos_x = _arg_int(args, "--pos-x") or 0
    pos_y = _arg_int(args, "--pos-y") or 0

    app = QApplication(sys.argv)
    app.setApplicationName("API 余额")
    app.setStyleSheet(APP_STYLE)
    app.setFont(QFont("Microsoft YaHei UI", 10))

    icon = _load_icon(app_dir)
    if icon is not None:
        app.setWindowIcon(icon)

    config = load_config(app_dir)
    window = MainWindow(app_dir, config, demo=demo)
    if icon is not None:
        window.setWindowIcon(icon)
    if pos_x or pos_y:
        window.move(pos_x, pos_y)
    window.show()

    if grab_main:
        # 直接渲染窗口内容（不含桌面背景），用于布局自检
        QTimer.singleShot(
            1800,
            lambda: (
                window.grab().save(grab_main),
                app.quit(),
            ),
        )
    elif grab_settings:
        dialog = SettingsDialog(app_dir, config, parent=window)
        dialog.move(pos_x, pos_y)
        dialog.show()
        QTimer.singleShot(
            1800,
            lambda: (
                dialog.grab().save(grab_settings),
                app.quit(),
            ),
        )
    elif shot_main:
        QTimer.singleShot(
            2000,
            lambda: (
                QApplication.primaryScreen().grabWindow(0).save(shot_main),
                app.quit(),
            ),
        )
    elif shot_settings:
        dialog = SettingsDialog(app_dir, config, parent=window)
        dialog.move(pos_x, pos_y)
        dialog.show()
        QTimer.singleShot(
            2000,
            lambda: (
                QApplication.primaryScreen().grabWindow(0).save(shot_settings),
                app.quit(),
            ),
        )
    else:
        if config is None and not demo:
            if not window.open_settings_first_run():
                return 0
    return app.exec()
