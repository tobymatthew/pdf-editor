from __future__ import annotations

import hashlib
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable, Optional

from PIL import ImageFont

from app.models.font import FontInfo

APP_FONT_DIR = Path(__file__).resolve().parents[1] / "fonts"
SYSTEM_SCAN_ROOTS = [
    Path("/System/Library/Fonts"),
    Path("/Library/Fonts"),
    Path.home() / "Library/Fonts",
]
FONT_EXTENSIONS = {".ttf", ".otf", ".ttc"}

_WEIGHT_HINTS: list[tuple[str, int]] = [
    ("thin", 100),
    ("extralight", 200),
    ("ultralight", 200),
    ("light", 300),
    ("book", 350),
    ("regular", 400),
    ("roman", 400),
    ("normal", 400),
    ("medium", 500),
    ("semibold", 600),
    ("demibold", 600),
    ("bold", 700),
    ("extrabold", 800),
    ("ultrabold", 800),
    ("black", 900),
    ("heavy", 900),
]


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _stable_font_id(path: Path) -> str:
    digest = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()
    return digest[:12]


def _infer_weight(*parts: str) -> Optional[int]:
    haystack = " ".join(parts).lower()
    for needle, weight in _WEIGHT_HINTS:
        if needle in haystack:
            return weight
    return None


def _read_font_metadata(path: Path) -> Optional[tuple[str, str, Optional[int]]]:
    try:
        font = ImageFont.truetype(str(path), size=16)
        family, style = font.getname()
    except Exception:
        return None

    family = (family or path.stem).strip() or path.stem
    style = (style or "Regular").strip() or "Regular"
    weight = _infer_weight(path.stem, family, style)
    return family, style, weight


def default_scan_roots() -> list[Path]:
    roots: list[Path] = [APP_FONT_DIR]
    for root in SYSTEM_SCAN_ROOTS:
        if root not in roots:
            roots.append(root)
    return roots


def discover_fonts(
    roots: Optional[Iterable[str | os.PathLike[str]]] = None,
    metadata_reader: Optional[Callable[[Path], Optional[tuple[str, str, Optional[int]]]]] = None,
) -> list[FontInfo]:
    reader = metadata_reader or _read_font_metadata
    scan_roots = [Path(root) for root in (default_scan_roots() if roots is None else roots)]
    discovered: dict[str, FontInfo] = {}

    for root in scan_roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in FONT_EXTENSIONS:
                continue
            resolved = path.resolve()
            font_id = _stable_font_id(resolved)
            if font_id in discovered:
                continue

            metadata = reader(resolved)
            if metadata is None:
                continue
            family, style, weight = metadata
            discovered[font_id] = FontInfo(
                id=font_id,
                family=family,
                style=style,
                weight=weight,
                path=str(resolved),
            )

    return sorted(
        discovered.values(),
        key=lambda font: (_normalize(font.family), _normalize(font.style), font.path),
    )


@lru_cache(maxsize=1)
def list_fonts() -> list[FontInfo]:
    return discover_fonts()


def refresh_fonts() -> list[FontInfo]:
    list_fonts.cache_clear()
    return list_fonts()


def find_font(
    font_id: Optional[str] = None,
    font_family: Optional[str] = None,
    fonts: Optional[Iterable[FontInfo]] = None,
) -> Optional[FontInfo]:
    registry = list(fonts if fonts is not None else list_fonts())

    if font_id:
        for font in registry:
            if font.id == font_id:
                return font

    if font_family:
        normalized_family = _normalize(font_family)
        family_matches = [
            font
            for font in registry
            if normalized_family
            in {
                _normalize(font.family),
                _normalize(f"{font.family} {font.style}"),
                _normalize(f"{font.family}-{font.style}"),
            }
        ]
        if family_matches:
            return sorted(
                family_matches,
                key=lambda font: (font.weight is None, font.weight or 400, _normalize(font.style), font.path),
            )[0]

    return None


def resolve_font_path(
    font_id: Optional[str] = None,
    font_family: Optional[str] = None,
    fonts: Optional[Iterable[FontInfo]] = None,
) -> Optional[str]:
    selected = find_font(font_id=font_id, font_family=font_family, fonts=fonts)
    if selected and Path(selected.path).exists():
        return selected.path

    for fallback_family in ("Arial", "Helvetica"):
        fallback = find_font(font_family=fallback_family, fonts=fonts)
        if fallback and Path(fallback.path).exists():
            return fallback.path

    return None
