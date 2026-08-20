"""生成应用图标：深蓝圆角方块 + 白色人民币符号 ¥。"""

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent / "icon.ico"
SIZE = 256

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# 背景：深蓝圆角方块
draw.rounded_rectangle(
    [8, 8, SIZE - 8, SIZE - 8], radius=56, fill=(30, 42, 74, 255)
)

# ¥ 符号：两条斜线 + 竖线 + 两条横杠
white = (255, 255, 255, 255)
stroke = 18
cx = SIZE // 2
draw.line([(70, 62), (cx, 118)], fill=white, width=stroke)
draw.line([(SIZE - 70, 62), (cx, 118)], fill=white, width=stroke)
draw.line([(cx, 118), (cx, 196)], fill=white, width=stroke)
draw.line([(58, 146), (SIZE - 58, 146)], fill=white, width=stroke)
draw.line([(66, 172), (SIZE - 66, 172)], fill=white, width=stroke)

img.save(
    OUT,
    sizes=[
        (16, 16),
        (24, 24),
        (32, 32),
        (48, 48),
        (64, 64),
        (128, 128),
        (256, 256),
    ],
)
print(f"icon saved: {OUT}")
