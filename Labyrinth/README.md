# 迷宫生成器（平面俯瞰）

基于 Python 的迷宫生成器，可随机生成**小 / 中 / 大 / 超大**四种规模的平面俯瞰迷宫，
支持命令行生成 PNG 和桌面图形界面，并可用 PyInstaller 打包为 `.exe`。

## 功能

- 两种生成算法：递归回溯（`recursive_backtracker`）、随机 Prim（`randomized_prim`），均为完美迷宫（无回路、任意两点唯一通路）
- 四档规模预设，尺寸和格子大小都在 `settings.json` 中配置，也可 CLI 自定义宽高
- 默认每次随机生成；填写种子后结果可复现
- 渲染为平面俯瞰 PNG（绿色=起点，红色=终点），颜色/线宽/边距可配置
- tkinter 图形界面：切换规模、填种子、换算法、重新生成、保存图片
- 绿色色块可用方向键（↑↓←→）在迷宫中移动，到达红色终点触发“寻路成功”提示
- 点击迷宫任意位置，绿色色块自动沿最短路径寻路（BFS，不穿墙）；无法到达时提示“此路不通”
- 重新生成迷宫前会弹窗确认，避免误触丢失当前进度
- 启用 Windows DPI 感知并使用矩形墙体绘制，界面清晰无马赛克感
- 迷宫随窗口大小等比缩放并自动居中（最大化时同步放大）
- 空格键暂停/继续自动寻路动画
- “显示移动轨迹”开关：勾选后色块走过的格子留下颜色标记，取消勾选清空记录

## 目录结构

```
labyrinth/
├── main.py              # 入口（python main.py gui / generate）
├── settings.json        # 设置：规模预设、算法、种子、样式、输出路径
├── maze/
│   ├── generator.py     # 迷宫生成算法与校验
│   ├── renderer.py      # Pillow 俯瞰图渲染
│   ├── gui.py           # tkinter 图形界面
│   ├── cli.py           # 命令行解析
│   └── config.py        # 设置加载
├── tests/               # 单元测试
├── build_exe.bat        # Windows 一键打包脚本
├── build_exe.ps1
└── output/              # 生成的迷宫图片
```

## 快速开始

```powershell
cd labyrinth   # 进入项目目录
python -m pip install -r requirements.txt

# 打开图形界面
python main.py gui

# 命令行生成一张随机中规模迷宫
python main.py generate --size medium

# 固定种子、自定义规模与输出路径
python main.py generate --size large --seed 42 --output output/my_maze.png

# 自定义宽高（不限于预设）
python main.py generate --width 25 --height 18 --cell-size 24 --output output/custom.png
```

## 操作说明（图形界面）

- 方向键 ↑ ↓ ← →：手动移动绿色色块（只能沿通道走）
- 鼠标点击迷宫任意格子：绿色色块自动沿最短路径移动过去
- 空格键：自动寻路过程中暂停/继续移动；暂停时再次点击可选择新目标，按空格后前往
- 空格键只控制色块移动，不会触发其他按钮（工具栏按钮不接收键盘焦点）
- 寻路过程中随时可点击其他格子，色块改为前往新位置
- 暂停时可用方向键手动移动，移动后清空原自动寻路目标
- 绿色色块碰到红色终点：弹出“寻路成功”，可选择下一场游戏（重新生成）或关闭
- “重新生成迷宫”：弹窗确认后重新随机生成并重置绿色色块
- “显示移动轨迹”：勾选后记录并标记色块走过的格子，取消勾选即清空

## 规模设置

在 `settings.json` 中修改 `presets`：

| 规模 | 默认格子数 | 默认格子像素 |
| --- | --- | --- |
| small（小规模） | 10 x 10 | 48 |
| medium（中规模） | 20 x 20 | 32 |
| large（大规模） | 35 x 35 | 18 |
| extra_large（超大规模） | 60 x 60 | 10 |

`size_preset` 决定默认规模；`seed` 为 `null` 时每次随机生成，填入数字则固定。

## 打包 exe

```powershell
.\build_exe.bat
# 或
.\build_exe.ps1
```

脚本会依次安装依赖、运行测试，然后用 PyInstaller 生成
`dist\MazeGenerator.exe`（单文件、无控制台窗口），并自动复制到项目**上一级目录**
`..\MazeGenerator.exe`（便于分发，不进入 git 仓库）。双击 exe 即打开图形界面；
也可以带命令行参数使用（输出不受控制台显示影响）：

```powershell
..\MazeGenerator.exe generate --size medium --seed 7 --output out.png
```

## Git 版本迭代流程

本项目使用 git 管理，每个迭代阶段打标签：

```powershell
git add -A
git commit -m "feat: 本次迭代内容"
git tag v1.1.0           # 语义化版本号：major.minor.patch
git push origin main --tags
```

当前标签：

- `v1.0.0` 生成核心（算法 / 渲染 / CLI / 设置）
- `v1.1.0` 图形界面 + exe 打包
- `v1.1.1` windowed exe 命令行兼容修复
- `v1.2.0` 界面清晰度优化、方向键移动、点击自动寻路、成功/确认弹窗
- `v1.3.0` 迷宫随窗口缩放居中、空格暂停/继续、移动轨迹开关
- `v1.4.0` 寻路中/暂停中改选目标、暂停中方向键移动

查看历史：`git log --oneline --decorate --graph`
