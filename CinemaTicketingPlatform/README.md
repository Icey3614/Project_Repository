# 电影购票平台（Cinema Ticketing Platform）

模拟电影院的完整购票流程：实时座位图选座、下单支付、票务状态机（待支付/待使用/核销）、转赠、退款审核，以及场馆/排片管理后台。**交付形态为 Windows 桌面应用程序**，不依赖浏览器。

## 功能

- 消费者端：电影浏览、实时座位图选座（防超卖）、支付宝沙箱/模拟支付、待支付倒计时、转赠、退款申请、历史购买
- 管理端：电影/场馆管理、可视化座位编辑器、排片与冲突检测、退款审核、开场核销
- 支付：支付宝沙箱（RSA2 签名/验签、跳转支付、主动查单、异步回调、自动退款）

## 桌面版（免安装，推荐使用）

双击 `desktop/release/CinemaTicketingPlatform 0.8.0.exe` 即可运行（约 95MB，Windows 便携版）。

首次运行会自动弹出**配置向导**：

1. 检测本机 MySQL 服务 → 输入本机 MySQL 用户名/密码 → 自动建库、建表、写入种子数据
2. 输入自己的支付宝沙箱信息（应用ID/应用私钥/支付宝公钥），或跳过使用模拟支付

非首次运行直接读取 `%APPDATA%\CinemaTicketingPlatform\config.json`（首次运行时生成），无需重复配置。

默认账号：管理员 `admin / Admin@123456`，普通用户 `demo / Demo@123456`。

## 技术栈

- 桌面壳：Electron（独立窗口，DPI 感知）
- 前端：React + Vite + TypeScript + Ant Design（打包为静态资源，由内置后端托管）
- 后端：FastAPI + SQLAlchemy 2.0 + PyMySQL + MySQL 8
- 认证：JWT（PyJWT + bcrypt）

## 目录结构

- `desktop/`：Electron 桌面壳（主进程、打包配置）
- `backend/`：FastAPI 后端（含首次运行配置接口）
- `frontend/`：React 前端源码（构建后内嵌进应用）
- `docs/`：需求纪要、工程规范、API 大纲、环境初始化

## 开发者：重新构建桌面版

```powershell
# 1. 前端桌面模式构建
cd frontend
pnpm install
pnpm build --mode desktop

# 2. 打包后端 exe（PyInstaller）
cd ..\backend
.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller
.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --name backend --paths . `
  --distpath ..\desktop\backend-dist --workpath build --specpath build `
  --collect-submodules uvicorn --collect-submodules fastapi --collect-submodules sqlalchemy `
  --hidden-import pymysql --hidden-import cryptography --hidden-import apscheduler run.py

# 3. 拷贝前端产物并生成便携版 exe
Copy-Item ..\frontend\dist desktop\dist -Recurse -Force
cd ..\desktop
npm install
$env:ELECTRON_MIRROR='https://npmmirror.com/mirrors/electron/'
$env:ELECTRON_BUILDER_BINARIES_MIRROR='https://npmmirror.com/mirrors/electron-builder-binaries/'
npx electron-builder --win portable
```

开发者如需在浏览器中调试界面（仅开发用）：

```powershell
cd backend; .venv\Scripts\activate; uvicorn app.main:app --reload --port 8000
cd frontend; pnpm dev   # 浏览器打开 http://localhost:5173
```

## 安全与隐私

- 数据库与支付宝凭据保存在 `backend/.env`（gitignored，不入库）；桌面版保存在 `%APPDATA%` 配置文件中
- 源码、文档与 git 历史均不含任何个人信息或真实密钥
- 分享源码请使用 `.\export_clean.ps1`（仅导出 git 跟踪的文件，自动排除 .env、构建产物与依赖）
- 本地开发依赖（.venv、node_modules、构建产物）与真实 .env 已从项目目录移出，如需本地运行请移回或重新安装
