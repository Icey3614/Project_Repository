# -*- coding: utf-8 -*-
"""生成游戏图标 icon.ico / icon.png（三角形三圆 + 彩色珠子）。"""

import math

from PIL import Image, ImageDraw

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((8, 8, SIZE - 8, SIZE - 8), radius=48, fill=(32, 36, 45),
                    outline=(70, 78, 94), width=6)

CT = (128, 64)
CL = (52, 200)
CR = (204, 200)
R = 112

for cx, cy in (CT, CL, CR):
    d.ellipse((cx - R, cy - R, cx + R, cy + R), outline=(128, 136, 150), width=7)


def inter(c1, r1, c2, r2):
    x1, y1 = c1
    x2, y2 = c2
    dd = math.hypot(x2 - x1, y2 - y1)
    a = (r1 * r1 - r2 * r2 + dd * dd) / (2 * dd)
    h = math.sqrt(max(0.0, r1 * r1 - a * a))
    xm = x1 + a * (x2 - x1) / dd
    ym = y1 + a * (y2 - y1) / dd
    return [(xm + h * (y2 - y1) / dd, ym - h * (x2 - x1) / dd),
            (xm - h * (y2 - y1) / dd, ym + h * (x2 - x1) / dd)]


colors = [(255, 122, 20), (0, 118, 255), (0, 158, 80),
          (198, 30, 58), (255, 208, 0), (240, 240, 240)]
pts = inter(CT, R, CL, R) + inter(CT, R, CR, R) + inter(CL, R, CR, R)
for (x, y), c in zip(pts, colors):
    d.ellipse((x - 15, y - 15, x + 15, y + 15), fill=c, outline=(14, 16, 21), width=4)

img.save("icon.png")
img.save("icon.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48),
                            (64, 64), (128, 128), (256, 256)])
print("icon.ico / icon.png generated")
