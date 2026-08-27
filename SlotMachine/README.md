# 🎰 Slot Machine（仿真老虎机）

一个用 **Python + CustomTkinter** 编写的三滚轮老虎机小游戏：右侧有可拖拽拉杆，拉下后三个滚轮依次开始转动并逐个停止；深色现代 App 风格，支持 Windows 高 DPI 缩放，可一键打包成单个 `.exe`。

## 功能

- 三个独立滚轮，连续卷轴仿真：加速 → 匀速 → 减速 → 停止抖动，逐个停下，动画流畅
- 右侧拉杆：按住红色球头向下拖动即可开转（直接点击拉杆、点 SPIN 按钮或按空格/回车也可以）
- 5 条赔付线（上 / 中 / 下 + 两条对角线），三个滚轮各自独立卷带
- 累积 Jackpot（每次下注抽取 2% 注入彩池）与三钻石免费转
- ✨ Wild 万能符号（免费转出现）+ Scatter 免费转（3×3 窗口 ≥3 钻石）
- AUTO 自动连转、点击滚轮提前停，转动节奏自己掌控
- 中英文界面一键切换（L 键），语言自动记忆
- 设置面板（⚙）：音效开关、音量三档、语言、自动转间隔、重置统计，全部自动存档
- 7 种符号赔率表，参数全部外置在 `config.json`，基础 RTP ≈ 92%
- 下注可调（5–100），初始 1000 分，可随时重置；积分 / 下注 / 设置自动存档到 `save.json`
- 中奖数字滚动、金色粒子特效、单局结算明细、近失提示、连胜计数、音效反馈（wav）+ 静音开关（M 键）
- 底部统计：Spins / 胜率 / 最高赢 / 理论 RTP / 实测返奖率
- Per-Monitor DPI Aware：高分屏下文字与界面保持清晰
- 现代深色 UI：圆角卡片、柔和配色、Segoe UI 字体
- 窗口自动适配屏幕高度，小屏也不溢出

## 运行

```bash
python -m pip install -r requirements.txt
python main.py
```

## 打包 .exe

```powershell
powershell -ExecutionPolicy Bypass -File .\build_exe.ps1
```

脚本会先安装打包依赖，再用 PyInstaller 生成单文件窗口程序，产物为 `dist\SlotMachine.exe`（含版本信息与 DPI 感知）。
如需单独分发，直接把该 exe 复制到任意位置即可（首次运行会在 exe 旁自动生成 `config.json` 与 `save.json`）。

## 版本管理

项目使用 git 管理，当前版本 `v0.1.0`。

后续迭代建议：

```bash
# 1. 改代码，并在 main.py 顶部更新 __version__
# 2. 提交
git add .
git commit -m "feat: describe the change"
# 3. 打新版本标签
git tag v0.2.0
```

查看历史版本：`git tag` 或 `git log --oneline --decorate`。

## 目录结构

| 文件 | 说明 |
| --- | --- |
| `main.py` | 游戏主程序（入口） |
| `config.json` | 玩法参数（赔率、卷带、Jackpot、对子规则），可自行调整 |
| `save.json` | 运行时自动生成的存档（积分、下注、统计） |
| `requirements.txt` | 运行依赖 |
| `requirements-dev.txt` | 打包/开发依赖（PyInstaller、Pillow） |
| `build_exe.ps1` | 一键打包脚本 |
| `version_info.txt` | exe 版本信息资源 |
| `assets/icon.ico` | 应用图标（由 `assets/make_icon.py` 生成） |
| `assets/make_sounds.py` | 音效生成脚本（`python assets/make_sounds.py`） |
| `assets/sounds/` | 生成的 wav 音效，打包时自动包含 |
| `tests/test_features.py` | 功能测试（打包前自动运行） |
| `.github/workflows/build.yml` | CI：打 tag 时自动构建 exe |
| `CHANGELOG.md` | 版本更新记录 |
