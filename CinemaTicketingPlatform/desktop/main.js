const { app, BrowserWindow, dialog } = require("electron");
const { spawn } = require("child_process");
const http = require("http");
const net = require("net");
const path = require("path");

let backendProc = null;
let port = 8765;

// DPI 感知：按显示器缩放渲染
app.commandLine.appendSwitch("high-dpi-support", "1");
// 固定用户数据目录（首次运行配置的存放位置）
app.setName("CinemaTicketingPlatform");

function getFreePort() {
  return new Promise((resolve, reject) => {
    const srv = net.createServer();
    srv.unref();
    srv.on("error", reject);
    srv.listen(0, "127.0.0.1", () => {
      const p = srv.address().port;
      srv.close(() => resolve(p));
    });
  });
}

function backendSpawnInfo() {
  if (app.isPackaged) {
    const base = path.join(process.resourcesPath, "backend");
    return {
      cmd: path.join(base, "backend.exe"),
      args: ["--port", String(port)],
      cwd: base,
      env: {
        ...process.env,
        CINEMA_PORT: String(port),
        CINEMA_CONFIG: path.join(app.getPath("userData"), "config.json"),
        FRONTEND_DIST: path.join(process.resourcesPath, "frontend_dist"),
      },
    };
  }
  const root = path.join(__dirname, "..");
  return {
    cmd: path.join(root, "backend", ".venv", "Scripts", "python.exe"),
    args: ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", String(port)],
    cwd: path.join(root, "backend"),
    env: {
      ...process.env,
      CINEMA_PORT: String(port),
      CINEMA_CONFIG: path.join(app.getPath("userData"), "config.json"),
      FRONTEND_DIST: path.join(root, "frontend", "dist"),
    },
  };
}

function startBackend() {
  const info = backendSpawnInfo();
  backendProc = spawn(info.cmd, info.args, { cwd: info.cwd, env: info.env, stdio: "inherit" });
  backendProc.on("error", (err) => {
    console.error("后端启动失败:", err.message);
  });
}

function waitForHealth(timeoutMs) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs;
    const attempt = () => {
      if (Date.now() > deadline) return reject(new Error("后端启动超时"));
      const req = http.get(
        { host: "127.0.0.1", port, path: "/health", timeout: 2000 },
        (res) => {
          res.resume();
          if (res.statusCode === 200) resolve();
          else setTimeout(attempt, 500);
        }
      );
      req.on("error", () => setTimeout(attempt, 500));
      req.on("timeout", () => req.destroy());
    };
    attempt();
  });
}

const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.whenReady().then(async () => {
    try {
      port = await getFreePort();
    } catch {
      port = 8765;
    }
    startBackend();
    try {
      await waitForHealth(90000);
    } catch (err) {
      dialog.showErrorBox("启动失败", String(err));
      app.quit();
      return;
    }
    const win = new BrowserWindow({
      width: 1280,
      height: 820,
      minWidth: 960,
      minHeight: 640,
      autoHideMenuBar: true,
      useContentSize: true,
      title: "电影购票平台",
      backgroundColor: "#f5f5f5",
      webPreferences: {
        contextIsolation: true,
        nodeIntegration: false,
        sandbox: true,
      },
    });
    win.loadURL(`http://127.0.0.1:${port}`);
    win.on("closed", () => app.quit());
  });

  app.on("window-all-closed", () => app.quit());
  app.on("before-quit", () => {
    if (backendProc) backendProc.kill();
  });
}
