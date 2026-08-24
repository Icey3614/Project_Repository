# Hello

一个简单的 Python + tkinter 桌面小程序：双击运行后弹出窗口，显示 "hello world"。

## 文件说明

- `hello.py` — 源码（已启用 Windows DPI 感知，高分辨率屏幕下文字清晰）
- `Hello.exe` — 打包好的可执行文件（Windows，双击即用，无需安装 Python）
- `Hello.spec` — PyInstaller 打包配置

## 运行

- 直接双击 `Hello.exe`。
- 或用源码运行：`python hello.py`（需要 Python 3 和 tkinter）。

## 重新打包

```powershell
python -m PyInstaller --onefile --windowed --clean --name Hello hello.py
```

打包结果在 `dist\Hello.exe`，可将其复制到项目根目录。
