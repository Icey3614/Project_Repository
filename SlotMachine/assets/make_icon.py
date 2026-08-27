"""Generate assets/icon.ico. Run once:  python assets/make_icon.py"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 256
OUT = Path(__file__).resolve().parent / "icon.ico"

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# rounded card background
d.rounded_rectangle(
    (8, 8, 248, 248),
    radius=58,
    fill=(27, 28, 51, 255),
    outline=(70, 74, 120, 255),
    width=8,
)

# three reel windows
for x in (38, 94, 150):
    d.rounded_rectangle(
        (x, 64, x + 46, 158),
        radius=14,
        fill=(18, 19, 42, 255),
        outline=(90, 94, 130, 255),
        width=4,
    )

# symbols: cherry (red circle), lemon (yellow ellipse), star (gold polygon)
d.ellipse((46, 96, 78, 128), fill=(242, 85, 95, 255), outline=(126, 27, 40, 255), width=4)
d.ellipse((104, 98, 128, 122), fill=(255, 217, 61, 255), outline=(170, 130, 20, 255), width=4)

cx, cy, r = 173, 111, 24
points = []
for k in range(10):
    radius = r if k % 2 == 0 else r * 0.45
    angle = -90 + k * 36
    points.append(
        (cx + radius * math.cos(math.radians(angle)), cy + radius * math.sin(math.radians(angle)))
    )
d.polygon(points, fill=(255, 209, 102, 255), outline=(180, 130, 30, 255))

# lever on the right
d.line((206, 220, 228, 86), fill=(174, 182, 198, 255), width=14)
d.line((209, 214, 227, 92), fill=(232, 237, 245, 255), width=4)
d.ellipse((212, 60, 244, 92), fill=(242, 85, 95, 255), outline=(126, 27, 40, 255), width=5)

img.save(OUT, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"icon written: {OUT}")
