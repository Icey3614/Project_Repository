"""无头自检：验证迷宫生成、移动碰撞、渲染性能与各界面/状态切换。"""

from __future__ import annotations

import math
import os
import sys
import tempfile
import time


def _log(msg: str) -> None:
    """兼容 exe 无控制台环境的安全输出。"""
    if sys.stdout is None:
        return
    try:
        print(msg)
    except Exception:
        pass


def run(qa_dir: str | None = None) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame
    pygame.init()

    from . import config as C
    from .app import App
    from .maze import Maze
    from .player import Player
    from .renderer import Renderer
    from .scores import Scores

    # 1) 三种难度迷宫：生成 + 可解性 + 出入口判定
    mazes: dict[str, Maze] = {}
    for key, d in C.DIFFICULTIES.items():
        m = Maze(d["cells"], d["cells"], seed=20260826)
        assert m.solve() is not None, f"{key} 迷宫不可解"
        assert m.in_goal(m.goal[0], m.goal[1]), f"{key} 出口判定异常"
        assert not m.in_goal(m.start[0], m.start[1]), f"{key} 入口即出口？"
        mazes[key] = m
        _log(f"[selftest] {key}: {m.width}x{m.height} 迷宫可解 OK")

    # 2) 玩家移动与碰撞
    p = Player(*mazes["medium"].start, yaw=math.pi / 2)
    for _ in range(60):
        p.update(1.0, 0.0, 1 / 60, mazes["medium"])
    assert p.y > 0.5, "玩家未能向前移动"
    _log(f"[selftest] 玩家移动/碰撞 OK（y={p.y:.2f}）")

    # 2.1) 跳跃：起跳上升，随后落回地面
    pj = Player(*mazes["small"].start, yaw=math.pi / 2)
    pj.update(0.0, 0.0, 1 / 60, mazes["small"], jump=True)
    assert not pj.grounded and pj.vz > 0, "起跳后应处于空中"
    guard = 0
    while not pj.grounded and guard < 300:
        pj.update(0.0, 0.0, 1 / 60, mazes["small"])
        guard += 1
    assert pj.grounded and abs(pj.z) < 0.01, f"应落回地面 z={pj.z}"
    _log("[selftest] 跳跃/重力/落地 OK")

    # 2.2) 登墙与空气墙：从 (1,1) 起跳向左跳上边界墙 (0,1) 顶
    pw = Player(1.5, 1.5, yaw=math.pi)
    pw.update(1.0, 0.0, 1 / 60, mazes["small"], jump=True)
    guard = 0
    while not pw.grounded and guard < 300:
        pw.update(1.0, 0.0, 1 / 60, mazes["small"])
        guard += 1
    assert pw.grounded and pw.z >= C.WALL_HEIGHT - 0.01, f"应站上墙顶 z={pw.z}"
    for _ in range(120):  # 继续朝边界外走，不能越界
        pw.update(1.0, 0.0, 1 / 60, mazes["small"])
    assert pw.x >= pw.radius - 0.001, f"空气墙失效 x={pw.x}"
    _log("[selftest] 登墙与空气墙 OK")

    # 2.3) 双击前进键进入奔跑，且移动更快
    pa = Player(*mazes["small"].start, yaw=math.pi / 2)
    pb = Player(*mazes["small"].start, yaw=math.pi / 2)
    now = time.perf_counter()
    pb.on_forward_press(now)
    pb.on_forward_press(now + 0.1)
    assert pb.sprint_active, "双击 W 应进入奔跑"
    for _ in range(10):
        pa.update(1.0, 0.0, 1 / 60, mazes["small"])
        pb.update(1.0, 0.0, 1 / 60, mazes["small"])
    assert pb.y > pa.y, "奔跑应比步行移动更远"
    _log("[selftest] 双击奔跑/加速 OK")

    # 3) 渲染性能抽查（窗口分辨率与 1080p 全屏；numpy 与纯 Python 两条路径）
    for w, h in ((C.RENDER_WIDTH, C.RENDER_HEIGHT), (1920, 1080)):
        r = Renderer(w, h, C.FOV_DEGREES)
        scr = pygame.Surface((w, h))
        p = Player(*mazes["large"].start, yaw=math.pi / 2)
        t0 = time.perf_counter()
        for i in range(20):
            p.yaw += 0.05
            p.pitch = 0.5 * math.sin(i * 0.3)
            r.render(scr, mazes["large"], p)
        avg_ms = (time.perf_counter() - t0) / 20 * 1000
        _log(f"[selftest] 渲染 {w}x{h} 平均 {avg_ms:.1f} ms/帧 OK")

    r_py = Renderer(C.RENDER_WIDTH, C.RENDER_HEIGHT, C.FOV_DEGREES, use_numpy=False)
    scr = pygame.Surface((C.RENDER_WIDTH, C.RENDER_HEIGHT))
    p = Player(*mazes["large"].start, yaw=math.pi / 2)
    for i in range(10):
        p.yaw += 0.05
        r_py.render(scr, mazes["large"], p)
    _log("[selftest] 纯 Python 渲染回退路径 OK")

    # 3.1) 回归：玩家位于墙格内/贴墙近距离时渲染不得卡死（曾因超大贴图列黑屏）
    r_edge = Renderer(C.RENDER_WIDTH, C.RENDER_HEIGHT)
    p_edge = Player(0.98, 1.5, yaw=0.0)
    p_edge.z, p_edge.grounded = 0.8, False
    t0 = time.perf_counter()
    for _ in range(10):
        r_edge.render(scr, mazes["small"], p_edge)
    edge_ms = (time.perf_counter() - t0) / 10 * 1000
    assert edge_ms < 80, f"贴墙渲染过慢 {edge_ms:.1f} ms"
    _log(f"[selftest] 贴墙/墙格内渲染回归 OK（{edge_ms:.1f} ms）")

    # 4) 状态切换：开始（自动全屏）→ 暂停（退出全屏）→ 继续（回到全屏）
    app = App(seed=20260826)
    assert app.state == "menu" and not app.fullscreen, "初始应为窗口主菜单"
    app._start_game("small")
    assert app.state == "playing" and app.fullscreen, "开始游戏应自动全屏"
    app._draw()
    app.show_map = True
    app._draw()
    app.show_map = False
    app._pause()
    assert app.state == "pause" and not app.fullscreen, "ESC 暂停应退出全屏"
    app._draw()
    app._resume()
    assert app.state == "playing" and app.fullscreen, "继续应回到全屏"
    app._draw_menu()
    app._on_win()
    app._draw()
    _log("[selftest] 全屏/暂停/继续/胜利界面切换 OK")

    # 5) 排行榜：记录、排序、最佳成绩
    scores_path = os.path.join(
        tempfile.gettempdir(), f"3DLabyrinth_test_{os.getpid()}.json")
    scores = Scores(scores_path)
    assert scores.add("small", 12.3, 20, 1) == 0, "首次成绩应为第 1 名"
    assert scores.add("small", 9.9, 15, 2) == 0, "更快成绩应升到第 1 名"
    assert scores.add("small", 11.0, 18, 3) == 1, "中间成绩应为第 2 名"
    assert scores.best("small")["time"] == 9.9, "最佳成绩错误"
    assert len(scores.top("small", 5)) == 3
    _log("[selftest] 排行榜 记录/排序/最佳 OK")

    # 6) 步数与探索迷雾：移动进入新格子计步，小地图底图可生成
    app._start_game("small")
    assert app.steps == 0 and app.explored is not None
    assert app.explored[app.maze.width + 1] == 1, "出生点应已探索"
    for _ in range(60):  # 逐帧小步前进，正常模拟游戏移动
        app.player.update(1.0, 0.0, 1 / 60, app.maze)
        app._refresh_cell_state()
    assert app.steps >= 1, f"移动后应至少计 1 步，实际 {app.steps}"
    app._draw()
    assert app._minimap_bg is not None, "小地图底图未生成"
    assert app._minimap_bg.get_width() > 0
    _log("[selftest] 步数统计与探索迷雾 OK")

    if qa_dir:
        os.makedirs(qa_dir, exist_ok=True)
        app._start_game("small")
        app._draw()
        pygame.image.save(app.window, os.path.join(qa_dir, "playing.png"))
        app.show_map = True
        app._draw()
        pygame.image.save(app.window, os.path.join(qa_dir, "map.png"))
        app.show_map = False
        app._draw_menu()
        pygame.image.save(app.window, os.path.join(qa_dir, "menu.png"))
        app._start_game("small")
        app._pause()
        app._draw()
        pygame.image.save(app.window, os.path.join(qa_dir, "pause.png"))
        app._resume()
        app._on_win()
        app._draw()
        pygame.image.save(app.window, os.path.join(qa_dir, "win.png"))
        _log(f"[selftest] 截图已保存到 {qa_dir}")

    pygame.quit()
    _log("[selftest] 全部通过 OK")
