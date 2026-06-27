from typing import Optional
from PIL import Image, ImageDraw, ImageFont
import numpy as np

from app.models.edit import Edit, TextConfig, EditTargetBBox


def suggest_text_style(image: Image.Image, bbox: EditTargetBBox) -> TextConfig:
    font_size = max(8, int(bbox.h * 0.7))

    img_np = np.array(image.convert("RGB"))
    y1 = max(0, int(bbox.y))
    y2 = min(image.height, int(bbox.y + bbox.h))
    x1 = max(0, int(bbox.x))
    x2 = min(image.width, int(bbox.x + bbox.w))
    region = img_np[y1:y2, x1:x2]
    dark_pixels = region[region < 100]
    if len(dark_pixels) > 0:
        color_val = int(np.median(dark_pixels))
        color = f"#{color_val:02x}{color_val:02x}{color_val:02x}"
    else:
        color = "#111111"

    return TextConfig(
        x=bbox.x,
        y=bbox.y,
        font_size=font_size,
        font_family="Arial",
        color=color,
    )


def render_text(image: Image.Image, edit: Edit, font_path: Optional[str] = None) -> Image.Image:
    draw = ImageDraw.Draw(image)
    tc = edit.text
    bbox = edit.target_bbox

    try:
        if font_path:
            font = ImageFont.truetype(font_path, int(tc.font_size))
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    color = tc.color.lstrip("#")
    rgb = tuple(int(color[i : i + 2], 16) for i in (0, 2, 4))

    y_offset = tc.y
    if y_offset == 0:
        y_offset = bbox.y

    x_offset = tc.x
    if x_offset == 0:
        x_offset = bbox.x

    draw.text((x_offset, y_offset), tc.value, fill=rgb, font=font)
    return image
