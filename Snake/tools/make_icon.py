"""生成应用图标：assets/icon.png 与 assets/icon.ico。"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(os.path.dirname(HERE), "assets")
SIZE = 256


def main() -> None:
    os.makedirs(ASSETS, exist_ok=True)
    pygame.init()
    surface = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)

    rect = pygame.Rect(0, 0, SIZE, SIZE)
    pygame.draw.rect(surface, (32, 36, 54), rect, border_radius=56)
    pygame.draw.rect(surface, (70, 76, 100), rect, width=3, border_radius=56)

    # 蛇（尾 → 头）
    body_color = (62, 158, 84)
    head_color = (105, 215, 122)
    segments = [
        ((68, 165), 16),
        ((95, 140), 20),
        ((122, 118), 23),
        ((152, 102), 27),
    ]
    for i, ((x, y), r) in enumerate(segments):
        color = head_color if i == len(segments) - 1 else body_color
        pygame.draw.circle(surface, color, (x, y), r)

    # 蛇眼
    hx, hy = segments[-1][0]
    pygame.draw.circle(surface, (255, 255, 255), (hx + 10, hy - 8), 6)
    pygame.draw.circle(surface, (20, 24, 32), (hx + 12, hy - 8), 3)

    # 食物
    pygame.draw.circle(surface, (255, 82, 82), (198, 56), 15)
    pygame.draw.circle(surface, (255, 170, 170), (194, 52), 5)

    png_path = os.path.join(ASSETS, "icon.png")
    ico_path = os.path.join(ASSETS, "icon.ico")
    pygame.image.save(surface, png_path)
    Image.open(png_path).convert("RGBA").save(
        ico_path,
        format="ICO",
        sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )
    print("ICON_OK", png_path, ico_path)


if __name__ == "__main__":
    main()
