"""全局配置：分辨率、难度、操作手感参数。"""

# 窗口分辨率；内部渲染分辨率与窗口一致，避免放大导致的模糊
WINDOW_WIDTH = 1280
WINDOW_HEIGHT = 800
RENDER_WIDTH = WINDOW_WIDTH
RENDER_HEIGHT = WINDOW_HEIGHT

# 正式进入游戏后自动全屏；ESC 退出全屏并暂停，ESC 再次按下继续（回到全屏）
FULLSCREEN_ON_START = True

TITLE = "3D 迷宫"

# 水平视野（度）
FOV_DEGREES = 66

# 鼠标灵敏度与俯仰角限制（弧度）
MOUSE_SENSITIVITY = 0.0022
PITCH_LIMIT = 1.0

# 玩家
PLAYER_RADIUS = 0.22
WALK_SPEED = 3.6           # 格/秒
SPRINT_MULTIPLIER = 1.55   # Shift 加速倍率

# 跳跃与垂直运动（世界单位：格）
GRAVITY = 14.0             # 重力加速度 格/秒²
JUMP_SPEED = 5.8           # 起跳初速度，最高点 ≈ v²/2g ≈ 1.2 格（墙高 1.0）
EYE_HEIGHT = 0.5           # 地面时视线高度（格）
WALL_HEIGHT = 1.0          # 墙高（格），跳到墙顶时 z = 1.0
CLEARANCE_HEIGHT = 0.6     # 高于该高度可越过/登上墙体，低空仍受墙体阻挡

# 双击前进键进入奔跑
DOUBLE_TAP_WINDOW = 0.28   # 双击判定窗口（秒）
SPRINT_TIMEOUT = 0.35      # 停止前进多久后自动退出奔跑（秒）

# 纹理与明暗
TEXTURE_SIZE = 64
SHADE_LEVELS = 16
SHADE_PER_UNIT = 3.2       # 距离每增加多少格，明暗加深一级

# 到达出口判定半径（格）
GOAL_RADIUS = 0.5

# 常驻小地图与战争迷雾
MINIMAP_REVEAL_RADIUS = 8   # 探索半径（格）
MINIMAP_MAX_SIZE = 220      # 小地图最大边长（像素）
MINIMAP_CELL_MIN = 2        # 最小格子像素
MINIMAP_REFRESH_FRAMES = 4  # 每 N 帧重绘一次小地图底图

# 难度：单元格数（对应网格尺寸为 cells*2+1）
DIFFICULTIES = {
    "small":  {"name": "小迷宫", "hint": "简单", "cells": 11},
    "medium": {"name": "中迷宫", "hint": "中等", "cells": 21},
    "large":  {"name": "大迷宫", "hint": "困难", "cells": 31},
}
