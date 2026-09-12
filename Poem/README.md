# 桌面诗词 (LitePoem)

## 功能

- 启动**立即**在右上角显示一首本地诗（无白块闪烁），同时后台联网拉取后无缝替换（仅正文，不含作者/出处）。
- **默认每 10 分钟**自动切换一句；联网时从接口拉取，失败或断网时从本地库随机（本地库含诗/词/曲）。
- **随机防重**：联网请求带随机参数破缓存、轮换源；并记录最近用过的作品/句子，避免连续轮播同一首；联网偏科或失败时自动回退到本地多样池。
- **右键诗句区域**手动切换；始终**置底**显示（不遮挡前台窗口），不掉任务栏与 Alt+Tab。
- 每次选中的诗句原文追加写入 exe 同目录的 `poem_history.jsonl`（JSONL，一行一首，含 `content`/`from`(篇名)/`from_who`(作者)/`at`），作为断网时本地库的一部分；内置诗句库已配好篇名与作者。
- 不掉进任务栏与 Alt+Tab（`WS_EX_TOOLWINDOW`），但在**系统托盘「隐藏的图标」**里可见；**左键点击托盘图标直接切换诗句**，右键弹出小菜单（打开设置 / 退出），点击其它位置自动收起。
- 楷体 (KaiTi)，与原件一致；**默认白色字体、无背景（仅文字）**，可在设置里用**色盘自选颜色**；字体默认大小下**始终多行**排版；背景/卡片**随文字收拢**（自适应宽度），并**紧贴主屏右缘**（约 5px）。
- 内置约 180 句经典诗词曲作为离线种子库；DPI 感知（PerMonitorV2）。

## 数据来源

- 主源：今日诗词 `https://v2.jinrishici.com/one.json`（诗/词/曲）
- 备用：一言 `https://v1.hitokoto.cn/?c=i`

## 构建（无需 VS / MSBuild）

```
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

输出：`PoemWidget.exe`（单文件，仅依赖 Windows 自带 .NET Framework 4.x，无需另装运行时）。

构建脚本使用 `csc.exe`（.NET Framework 自带），纯 C# 代码构建 WPF（不含 XAML），自动生成图标并内嵌 DPI 感知 manifest。

## 运行文件

- `PoemWidget.exe` 程序本身
- `settings.json` 设置（与 exe 同目录；不可写则回退 `%APPDATA%\LitePoem`）
- `poem_history.jsonl` 已选诗句历史（与 exe 同目录；不可写则回退 `%APPDATA%\LitePoem`）

## 设置项

更新间隔（分钟）、字体大小、**字体（系统已安装字体下拉选择）**、是否联网、背景样式（半透明卡片 / 纯白 / 无背景）、**字体颜色（色盘）**、开机自启。

## 源码结构

- `src/Program.cs` 入口（单实例）
- `src/AppRoot.cs` 主控：联网/离线切换、定时器、托盘、设置
- `src/MainWindow.cs` 右上角浮窗
- `src/PoemService.cs` 联网取诗 + 本地库 + 历史写读
- `src/SettingsWindow.cs`、`src/TrayIcon.cs`、`src/SeedPoems.cs` 等
