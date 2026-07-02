import os
import json
import math
import time
import uuid
from typing import Optional

from PIL import Image

from app import config
from app.models.signature import SignatureInfo


def _signatures_dir() -> str:
    return os.path.join(config.DATA_DIR, "signatures")


def _index_path() -> str:
    return os.path.join(_signatures_dir(), "index.json")


def _image_path(signature_id: str) -> str:
    return os.path.join(_signatures_dir(), f"{signature_id}.png")


def _load_index() -> list[dict]:
    path = _index_path()
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.loads(f.read())


def _save_index(entries: list[dict]) -> None:
    directory = _signatures_dir()
    os.makedirs(directory, exist_ok=True)
    with open(_index_path(), "w") as f:
        json.dump(entries, f, indent=2)


def _sample_background(image: Image.Image) -> tuple[float, float, float]:
    width, height = image.size
    if width == 0 or height == 0:
        return (255.0, 255.0, 255.0)

    inset_x = max(0, min(width // 8, width - 1))
    inset_y = max(0, min(height // 8, height - 1))
    sample_points = [
        (0, 0),
        (width - 1, 0),
        (0, height - 1),
        (width - 1, height - 1),
        (inset_x, inset_y),
        (width - 1 - inset_x, inset_y),
        (inset_x, height - 1 - inset_y),
        (width - 1 - inset_x, height - 1 - inset_y),
    ]
    pixels = [image.getpixel((x, y))[:3] for x, y in sample_points]
    count = len(pixels) or 1
    return tuple(sum(pixel[i] for pixel in pixels) / count for i in range(3))


def _color_distance(a: tuple[int, int, int], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((channel - reference) ** 2 for channel, reference in zip(a, b)))


def _process_signature_image(image: Image.Image, aggressive: bool = False) -> Image.Image:
    """Normalize to RGBA PNG, remove paper-like backgrounds, and trim empty margins."""
    rgba = image.convert("RGBA")
    background = _sample_background(rgba)
    data = rgba.getdata()
    new_data = []
    transparent_brightness = 224 if not aggressive else 195
    transparent_distance = 52 if not aggressive else 95
    soften_brightness = 210 if not aggressive else 185
    soften_distance = 70 if not aggressive else 120
    for r, g, b, a in data:
        if a == 0:
            new_data.append((r, g, b, a))
            continue

        brightness = (r + g + b) / 3
        distance = _color_distance((r, g, b), background)
        if brightness >= transparent_brightness and distance <= transparent_distance:
            new_data.append((255, 255, 255, 0))
        elif brightness >= soften_brightness and distance <= soften_distance:
            new_alpha = max(0, min(a, int(a * 0.2)))
            new_data.append((r, g, b, new_alpha))
        else:
            new_data.append((r, g, b, a))
    rgba.putdata(new_data)

    bbox = rgba.getbbox()
    if bbox:
        rgba = rgba.crop(bbox)
    return rgba


def list_signatures() -> list[SignatureInfo]:
    return [SignatureInfo(**entry) for entry in _load_index()]


def create_signature(image_bytes: bytes, name: str, aggressive: bool = False) -> SignatureInfo:
    from io import BytesIO

    raw = Image.open(BytesIO(image_bytes))
    processed = _process_signature_image(raw, aggressive=aggressive)

    signature_id = uuid.uuid4().hex[:12]
    directory = _signatures_dir()
    os.makedirs(directory, exist_ok=True)
    processed.save(_image_path(signature_id), "PNG")

    entry = {
        "id": signature_id,
        "name": name or f"Signature {time.strftime('%Y-%m-%d %H:%M')}",
        "width": processed.width,
        "height": processed.height,
        "created_at": time.time(),
    }
    entries = _load_index()
    entries.append(entry)
    _save_index(entries)
    return SignatureInfo(**entry)


def get_signature_path(signature_id: str) -> Optional[str]:
    if not _entry_exists(signature_id):
        return None
    path = _image_path(signature_id)
    return path if os.path.exists(path) else None


def get_signature_meta(signature_id: str) -> Optional[SignatureInfo]:
    for entry in _load_index():
        if entry["id"] == signature_id:
            return SignatureInfo(**entry)
    return None


def _entry_exists(signature_id: str) -> bool:
    return any(entry["id"] == signature_id for entry in _load_index())


def delete_signature(signature_id: str) -> bool:
    entries = _load_index()
    filtered = [entry for entry in entries if entry["id"] != signature_id]
    if len(filtered) == len(entries):
        return False
    _save_index(filtered)
    path = _image_path(signature_id)
    if os.path.exists(path):
        os.remove(path)
    return True
