#!/usr/bin/env python
"""Renders on-screen text as a transparent PNG for ffmpeg to overlay.

Uses Pillow's own font rendering rather than ffmpeg's `drawtext` filter:
drawtext requires ffmpeg to be built with libfreetype/fontconfig, and the
plain Homebrew `ffmpeg` formula is not (confirmed: `ffmpeg -filters` has no
drawtext entry). Pillow bundles its own text rendering, so this sidesteps
needing a custom ffmpeg build entirely.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FRAME_SIZE = (1280, 720)
FONT_CANDIDATES = [
    "/System/Library/Fonts/Helvetica.ttc",              # macOS
    "/System/Library/Fonts/Supplemental/Arial.ttf",      # macOS fallback
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",   # common Linux
]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    try:
        return ImageFont.load_default(size)  # Pillow >=10.1: scalable default
    except TypeError:
        return ImageFont.load_default()  # older Pillow: fixed-size bitmap fallback


def render_text_png(
    text: str, dest: Path, font_size: int = 46, frame_size: tuple[int, int] = FRAME_SIZE
) -> Path:
    """White text, centered horizontally, positioned in the lower fifth of
    the frame, transparent everywhere else — ready for an ffmpeg overlay."""
    img = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    font = _load_font(font_size)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    x = (frame_size[0] - text_w) / 2 - bbox[0]
    y = frame_size[1] * 0.82 - bbox[1]
    draw.text((x, y), text, font=font, fill=(255, 255, 255, 255))
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest)
    return dest
