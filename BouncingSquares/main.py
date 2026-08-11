"""入口：先弹出设置框，再启动弹跳动画。"""
from __future__ import annotations

import atexit
import faulthandler
import sys
import traceback
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox

from app import BounceApp
from settings_dialog import SettingsDialog, _reset_style_singleton
from win_utils import TRANSPARENT_COLOR, enable_dpi_awareness, virtual_screen


APP_NAME = "弹跳正方形"

DEFAULT_SETTINGS = {
    "angle": 45.0,   # 角度制：0°=向右，90°=向下
    "size": 80,      # 边长（像素）
    "speed": 300.0,  # 速度（像素/秒）
    "count": 1,      # 方块数量
    "random": False,
    "gravity": False,  # 全局重力
    "color": "#4c8bf5",
    "random_color": False,
    "squares": [],   # 逐方块覆盖配置（可选）
}


def _base_dir() -> Path:
    """exe 打包后写到 exe 旁边；源码运行时写到项目目录。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = _base_dir()
ERROR_LOG = BASE_DIR / "error.log"
STARTUP_LOG = BASE_DIR / "startup.log"


def _log(msg: str) -> None:
    """把运行里程碑追加写入 startup.log，方便排查“闪退”。"""
    try:
        with STARTUP_LOG.open("a", encoding="utf-8") as fh:
            fh.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except OSError:
        pass


try:
    _fault_log = STARTUP_LOG.open("a", encoding="utf-8")
    faulthandler.enable(file=_fault_log)  # 原生崩溃（如 Tcl 段错误）也会写入日志
except Exception:
    pass


@atexit.register
def _on_exit() -> None:
    _log("进程退出")


def _report_fatal_error(exc: BaseException) -> None:
    """记录完整错误并弹窗提示，避免双击运行时“闪退”看不到原因。"""
    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    _log("致命错误: " + details.replace("\n", " | "))
    try:
        ERROR_LOG.write_text(details, encoding="utf-8")
    except OSError:
        pass
    try:
        print(details, file=sys.stderr)
    except Exception:
        pass
    try:
        messagebox.showerror(
            "程序出错",
            f"发生未处理的错误：\n\n{exc}\n\n"
            f"详细信息已保存到：\n{ERROR_LOG}\n\n请将 error.log 的内容发给开发者。",
        )
    except Exception:
        pass


def _ensure_single_instance() -> bool:
    """防止双击多次导致多个窗口；已有实例时返回 False。"""
    try:
        import ctypes

        global _MUTEX_HANDLE
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        _MUTEX_HANDLE = kernel32.CreateMutexW(None, False, APP_NAME + "_Mutex")
        already_exists = ctypes.get_last_error() == 183  # ERROR_ALREADY_EXISTS
        return not already_exists
    except Exception:
        return True


_MUTEX_HANDLE = None


def _icon_path() -> Path | None:
    """图标路径：exe 打包后从解压目录取，源码运行时从项目目录取。"""
    try:
        if getattr(sys, "frozen", False):
            candidate = Path(sys._MEIPASS) / "icon.ico"
        else:
            candidate = BASE_DIR / "icon.ico"
        return candidate if candidate.exists() else None
    except Exception:
        return None


def _set_window_icon(window: tk.Tk | tk.Toplevel) -> None:
    try:
        path = _icon_path()
        if path is not None:
            window.iconbitmap(str(path))
    except Exception:
        pass


def _apply_desktop_pet_window(root: tk.Tk, rect: tuple[int, int, int, int]) -> None:
    """把动画窗口配置成桌宠样式：透明、铺满整个虚拟屏幕、置顶。

    去边框、精确摆放与鼠标穿透需要在窗口映射后应用（见 app.py 的 _on_first_map）。
    """
    # 不设置 wm geometry：canvas pack 会把它重置掉，
    # 窗口尺寸/位置完全由映射后的 SetWindowPos 控制（支持负坐标显示器）

    root.attributes("-topmost", True)
    try:
        root.attributes("-transparentcolor", TRANSPARENT_COLOR)
    except tk.TclError:
        pass


def main(auto: bool = False) -> None:
    enable_dpi_awareness()  # 必须在创建任何窗口前调用，保证字体清晰
    _log("程序启动")

    if not _ensure_single_instance():
        _log("检测到已有实例，直接退出")
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(APP_NAME, "程序已经在运行中，请查看任务栏。")
        root.destroy()
        return

    if auto:
        settings = dict(DEFAULT_SETTINGS)
        _log("使用默认设置（--auto 快速启动）")
    else:
        _log("显示设置框")
        dialog = SettingsDialog(defaults=DEFAULT_SETTINGS)
        _set_window_icon(dialog)
        dialog.mainloop()  # 设置框是独立主窗口，关闭后返回
        _reset_style_singleton()  # 设置框解释器已销毁，重置主题单例供主窗口使用
        settings = dialog.get_result()
        if settings is None:
            _log("用户在设置框选择退出")
            return  # 用户点了“退出”或关闭了设置框

    _log(f"用户确认设置: {settings}")
    root = tk.Tk()
    root.title(APP_NAME)
    root.minsize(400, 300)
    _set_window_icon(root)
    rect = virtual_screen()
    if rect is None:
        rect = (
            0,
            0,
            root.winfo_screenwidth(),
            root.winfo_screenheight(),
        )
    _log(f"虚拟屏幕矩形: {rect}")
    _apply_desktop_pet_window(root, rect)

    _log("创建桌宠窗口")
    app = BounceApp(root, settings, rect)
    root.update()  # 让窗口完成映射
    app._apply_desktop_styles()  # 顶层应用桌宠样式（不能在事件回调内触发）
    _log("进入动画主循环")
    root.mainloop()
    _log("主循环结束，程序退出")


if __name__ == "__main__":
    try:
        main(auto="--auto" in sys.argv)
    except Exception as exc:
        _report_fatal_error(exc)
        sys.exit(1)
