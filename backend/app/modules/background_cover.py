import numpy as np
from PIL import Image

from app.models.edit import EditTargetBBox


def estimate_background_color(image: Image.Image, bbox: EditTargetBBox) -> tuple[int, int, int]:
    cx = bbox.x + bbox.w / 2
    cy = bbox.y + bbox.h / 2
    margin = 20
    sample_x = max(0, int(cx - margin))
    sample_y = max(0, int(cy - margin))
    sample_w = min(image.width - sample_x, margin * 2)
    sample_h = min(image.height - sample_y, margin * 2)

    if sample_w < 1 or sample_h < 1:
        return (255, 255, 255)

    img_np = np.array(image.convert("RGB"))
    region = img_np[sample_y : sample_y + sample_h, sample_x : sample_x + sample_w]
    median_color = np.median(region, axis=(0, 1)).astype(int)
    return (int(median_color[0]), int(median_color[1]), int(median_color[2]))


def sample_dominant_background(image: Image.Image, bbox: EditTargetBBox) -> tuple[int, int, int]:
    pad = 10
    x1 = max(0, int(bbox.x) - pad)
    y1 = max(0, int(bbox.y) - pad)
    x2 = min(image.width, int(bbox.x + bbox.w) + pad)
    y2 = min(image.height, int(bbox.y + bbox.h) + pad)

    img_np = np.array(image.convert("RGB"))
    region = img_np[y1:y2, x1:x2]

    # Sample border pixels only
    top = region[0, :]
    bottom = region[-1, :]
    left = region[:, 0]
    right = region[:, -1]
    border = np.concatenate([top, bottom, left, right])
    brightness = border.mean(axis=1)
    channel_spread = border.max(axis=1) - border.min(axis=1)
    paper_like = border[(brightness > 185) & (channel_spread < 45)]
    if len(paper_like) >= max(8, len(border) * 0.15):
        median = np.median(paper_like, axis=0).astype(int)
    else:
        light_pixels = border[brightness >= np.percentile(brightness, 75)]
        median = np.median(light_pixels if len(light_pixels) else border, axis=0).astype(int)
    return (int(median[0]), int(median[1]), int(median[2]))


def inpaint_region(image: Image.Image, bbox: EditTargetBBox) -> Image.Image:
    import cv2

    img_np = np.array(image.convert("RGB"))
    mask = np.zeros(img_np.shape[:2], dtype=np.uint8)

    x1 = max(0, int(bbox.x))
    y1 = max(0, int(bbox.y))
    x2 = min(image.width, int(bbox.x + bbox.w))
    y2 = min(image.height, int(bbox.y + bbox.h))

    mask[y1:y2, x1:x2] = 255
    result = cv2.inpaint(img_np, mask, 3, cv2.INPAINT_TELEA)
    return Image.fromarray(result)


def create_cover_patch(
    image: Image.Image, bbox: EditTargetBBox, method: str = "sampled_background"
) -> Image.Image:
    if method == "white":
        color = (255, 255, 255)
    elif method == "sampled_background":
        color = sample_dominant_background(image, bbox)
    elif method == "inpaint":
        return inpaint_region(image, bbox)
    else:
        color = (255, 255, 255)

    img_np = np.array(image.convert("RGB"))
    x1 = max(0, int(bbox.x))
    y1 = max(0, int(bbox.y))
    x2 = min(image.width, int(bbox.x + bbox.w))
    y2 = min(image.height, int(bbox.y + bbox.h))
    img_np[y1:y2, x1:x2] = color
    return Image.fromarray(img_np)
