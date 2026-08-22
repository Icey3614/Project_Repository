# 2D 魔方 · 三角形圆环版 (Rubik's Cube 2D - Triangle Rings)

用 Python + pygame 编写的魔方二维化游戏：把三阶魔方的 54 张贴片铺到一幅**三角形三圆族**平面图上，三维转动变成平面上的**圆环转动**。

![图标](icon.png)

## 二维化原理

- 以等边三角形的三个顶点为圆心，各自画一族同心圆（每族 3 个，共 **9 条圆环**）。
- **54 颗色珠**恰好位于圆环的交点上，每条圆环穿过 12 颗色珠。
- 转动任意圆环，环上 12 颗色珠沿环滑动一格——这就是"三维转动"在二维上的样子。
- 6 个"瓣"（每对圆族中线两侧各 9 颗，共 6×9）对应魔方的 6 个面。
- **求解目标**：6 个瓣各为一种颜色。

## 操作

| 操作 | 说明 |
| --- | --- |
| 鼠标左键点击圆环 | 该环顺时针转一格 |
| 鼠标右键点击圆环 | 该环逆时针转一格 |
| 键盘 `1`-`9` | 对应 `T0 T1 T2 / L0 L1 L2 / R0 R1 R2` 九条环 |
| `Shift` + 数字 | 逆时针 |
| `Ctrl+Z` / `Ctrl+Y` | 撤销 / 重做 |
| 右侧控制台按钮 | 打乱 / 重置 / 撤销 / 重做 / 逐环转动 |

## 运行

直接运行打包好的程序：

```
dist\RubiksCube2D.exe
```

或从源码运行（需要 Python 3.10+）：

```
pip install -r requirements.txt
python rubiks_cube_2d.py
```

Windows 下也可以双击 `start.bat`。

## 打包成 .exe

```
powershell -ExecutionPolicy Bypass -File build_exe.ps1
```

脚本会自动生成图标、运行自检，然后用 PyInstaller 打包出单文件 `dist\RubiksCube2D.exe`。

## 技术说明

- **DPI 感知**：启动时通过 `SetProcessDpiAwareness` 启用每显示器 DPI 感知，并按系统缩放系数放大全部界面，避免高 DPI 下模糊。
- **字体**：直接加载系统中文字体文件（微软雅黑等），不再依赖字体名枚举，避免中文显示乱码/方块。
- **模型**：状态为 54 个颜色；圆环转动是环上 12 个位置的颜色循环移位，任何一步都有严格逆操作，打乱后必然可还原。
- **自检**：`python rubiks_cube_2d.py --selftest` 验证 9 环 × 12 珠、6 瓣 × 9 珠、顺逆互逆与打乱还原。

## 版本历史（git）

- `v0-net`：第一版，十字展开图（六面平铺网图）。
- `v1-rings`：第二版，三角形三圆族主题 + DPI 感知 + 中文字体修复。

## 目录结构

```
Rubik'sCube/
├── rubiks_cube_2d.py   # 游戏主程序（模型 + 界面 + 动画）
├── make_icon.py        # 生成 icon.ico / icon.png
├── build_exe.ps1       # 一键打包脚本
├── requirements.txt    # Python 依赖
├── start.bat           # 双击启动
├── icon.ico / icon.png # 程序图标
└── dist/
    └── RubiksCube2D.exe
```
