"""LED 点阵电子横幅核心逻辑：文本 -> 点阵亮度列。"""

import os

from PIL import Image, ImageDraw, ImageFont

# LED 两态颜色（亮 / 灭），避免暗红中间色造成的模糊
LEVEL_COLORS = (
    (8, 2, 2),       # 灭：几乎不可见
    (255, 62, 30),   # 亮：主题亮红
)

FONT_CANDIDATES = (
    "C:/Windows/Fonts/msyh.ttc",
    "C:/Windows/Fonts/msyhbd.ttc",
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/simsun.ttc",
    "C:/Windows/Fonts/Deng.ttf",
)


def load_font(size: int):
    """按优先级加载支持中文的系统字体。"""
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _gray_to_level(gray: int, threshold: int = 130) -> int:
    # 二值化：超过阈值即点亮，让字形边缘干脆清晰
    return 1 if gray >= threshold else 0


def _render_part_columns(part, font, rows, scale, threshold):
    """渲染一段文本并缩放到点阵列。"""
    probe = Image.new("L", (1, 1), 0)
    draw = ImageDraw.Draw(probe)
    bbox = draw.textbbox((0, 0), part, font=font)
    w = max(bbox[2] - bbox[0], 2)
    h = max(bbox[3] - bbox[1], 2)
    img = Image.new("L", (w, h), 0)
    ImageDraw.Draw(img).text((-bbox[0], -bbox[1]), part, font=font, fill=255)
    cols = max(round(w / scale), 1)
    # 一次性缩放到 rows×cols 点阵（BOX 为块平均），避免逐格采样
    small = img.resize((cols, rows), Image.BOX)
    return [
        [_gray_to_level(small.getpixel((c, r)), threshold) for r in range(rows)]
        for c in range(cols)
    ]


def render_text_columns(
    text: str,
    rows: int = 32,
    scale: int = 4,
    gap: int = 12,
    threshold: int = 130,
):
    """把文本渲染成 LED 点阵，返回每列的亮度值列表（每个值 0 或 1）。

    gap 表示消息重复之间的空白列数，模拟真实横幅的滚动间隔。
    """
    text = text if text else "你好，世界！"
    font = load_font(rows * scale)
    # 分块渲染，避免长文本生成超大图片（Pillow 像素上限/内存问题）
    step = max(64, int(4_000_000 / (rows * scale * rows * scale)))
    columns = []
    for i in range(0, len(text), step):
        columns.extend(_render_part_columns(text[i : i + step], font, rows, scale, threshold))

    # 垂直居中：把实际用到的行移到点阵中间
    used = [(c, r) for c in range(len(columns)) for r in range(rows) if columns[c][r]]
    if used:
        top = min(r for _, r in used)
        bottom = max(r for _, r in used)
        shift = (rows - (bottom - top + 1)) // 2 - top
        if shift > 0:
            columns = [[0] * shift + col[: rows - shift] for col in columns]
        elif shift < 0:
            columns = [col[-shift:] + [0] * (-shift) for col in columns]

    columns.extend([[0] * rows for _ in range(gap)])
    return columns


def render_preview_image(
    text: str,
    rows: int = 32,
    cols: int = 192,
    out_path: str = "preview.png",
    cell: int = 14,
    gap_px: int = 3,
    offset: int | None = None,
):
    """把一帧画面渲染成 PNG（用于预览/测试）。"""
    columns = render_text_columns(text, rows=rows)
    n = len(columns)
    if offset is None:
        offset = max((cols - n) // 2, 0)

    width, height = cols * cell, rows * cell
    img = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    d = cell - gap_px
    radius = max(d // 3, 1)
    for c in range(cols):
        col = columns[(offset + c) % n]
        for r in range(rows):
            x, y = c * cell, r * cell
            draw.rounded_rectangle((x, y, x + d, y + d), radius=radius, fill=LEVEL_COLORS[col[r]])
    img.save(out_path)
    return out_path
