# API 余额查看器（DeepSeek）

一个基于 Python + PySide6 的桌面小工具，用于一键查看 API 余额、
累计消费金额，以及当前时段的峰谷定价情况（仅 DeepSeek 显示峰谷定价）。

## 功能

- 主界面显示：余额、累计消费金额、当前时段（高峰/闲时）、当前价格（每百万 tokens）
- 右上角图标按钮：刷新 / 设置 / 最小化 / 关闭
- 每 10 秒自动刷新余额，也可点击“刷新”立即更新
- 首次运行（同目录无 `config.json`）自动弹出设置界面
- 启动时若已有配置，会先做一次连接测试，连接失败自动弹出设置界面
- 设置界面：API Key、Base URL 下拉选择（内置主流平台，支持手动输入并记忆）、
  余额预警线（低于预警线时弹窗提醒）、连接测试、保存、一键清除配置
- 保存键始终可以保存（允许留空 API Key 生成空配置文件），并提示保存成功
- 一键清除配置会连同消费记录一起删除
- 配置保存在程序同目录的 `config.json`，不会写入代码
- Windows 11 Acrylic 毛玻璃风格、无边框小窗口，可拖拽移动

## Base URL 预置平台

- DeepSeek 官方（OpenAI 格式 / Anthropic 格式）
- OpenAI、智谱 GLM、阿里通义千问、Moonshot Kimi、百度千帆、
  腾讯混元、硅基流动、Groq

> 提示：余额查询接口是 DeepSeek 官方的 `/user/balance`，其他平台需配合
> 各自的余额接口才能生效；预置地址主要是方便切换填写。

## 峰谷定价说明

DeepSeek 自 2026-08-17 起实行峰谷定价：

- 高峰时段：北京时间 9:00–12:00、14:00–18:00
- 其余时间为闲时，价格 = 高峰价格 × 50%

程序按北京时间自动判断当前时段并显示对应价格。

## 使用

### 源码运行

```bash
python -m pip install -r requirements.txt
python main.py
```

### 打包 exe

双击 `build.bat`，或手动执行：

```bash
python -m PyInstaller --noconfirm --clean --onefile --windowed --name DeepSeekBalance main.py
```

生成的 `dist\DeepSeekBalance.exe` 即为一键运行版本，配置文件和消费记录
都会生成在 exe 同目录下。

> 首次运行 Windows SmartScreen 可能提示“未知发布者”，选择“仍要运行”即可
> （本工具没有代码签名）。

## 关于“累计消费金额”

DeepSeek 官方余额接口只返回当前余额，不提供累计消费。
本程序通过记录每次刷新时余额的**减少量**来推算累计消费（本地保存于
`state.json`），充值或赠金到账不会产生负消费，但该数值仅供参考，
清除配置后会重置。精确账单请以 DeepSeek 开放平台为准。

## 余额预警

在设置中勾选“低于预警线时弹窗提醒”并设置金额后，每次刷新若余额低于
预警线会弹窗提示；余额恢复到预警线以上后自动解除，避免反复弹窗。

## 目录结构

```
Balance/
├── main.py                  # 入口
├── deepseek_balance/
│   ├── app.py               # 应用启动逻辑
│   ├── config.py            # 配置与消费状态读写
│   ├── api.py               # DeepSeek API 客户端
│   ├── pricing.py           # 峰谷定价规则
│   └── ui.py                # 主窗口与设置界面
├── build.bat                # 一键打包脚本
└── requirements.txt
```
