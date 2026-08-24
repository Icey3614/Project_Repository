import ctypes
import sys
import tkinter as tk


def enable_dpi_awareness() -> None:
    """让窗口按真实 DPI 渲染，避免文字被系统拉伸导致模糊。"""
    if sys.platform != "win32":
        return
    try:
        # 1 = SYSTEM_DPI_AWARE；若 manifest 已设置会返回 E_ACCESSDENIED，属正常。
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> None:
    enable_dpi_awareness()

    root = tk.Tk()
    root.title("Hello")
    root.geometry("320x160")
    root.resizable(False, False)

    label = tk.Label(
        root,
        text="hello world",
        font=("Microsoft YaHei UI", 20),
    )
    label.pack(expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
