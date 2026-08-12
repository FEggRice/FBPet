"""Frame-source detection: a single image, an animated GIF/APNG, or a sprite
sheet. Pure Pillow logic, no GUI dependency. Returns per-state RGBA frame
lists plus the display size (fit within `box`, never upscaled)."""
from __future__ import annotations

from PIL import Image


def load_frames(path: str, sheet: dict, animations: dict, box: tuple[int, int]) -> tuple[dict, tuple[int, int]]:
    img = Image.open(path)

    # Animated GIF/APNG: one shared loop for every state.
    if getattr(img, "is_animated", False):
        frames = [_resize(_rgba(img, i), box) for i in range(img.n_frames)]
        return {name: list(frames) for name in animations}, frames[0].size

    img = img.convert("RGBA")
    if not _is_sheet(sheet, *img.size):
        frame = _resize(img, box)
        return {name: [frame] for name in animations}, frame.size

    # Sprite sheet: crop each state's row into cell frames.
    cw, ch = sheet["cellWidth"], sheet["cellHeight"]
    cols = img.width // cw
    out = {}
    for name, anim in animations.items():
        row = anim.get("row", 0)
        n = min(anim.get("frames", cols), cols)
        out[name] = [img.crop((i * cw, row * ch, (i + 1) * cw, (row + 1) * ch)) for i in range(n)]
    return out, (cw, ch)


def _rgba(img, index: int) -> Image.Image:
    img.seek(index)
    return img.copy().convert("RGBA")


def _resize(img: Image.Image, box: tuple[int, int]) -> Image.Image:
    bw, bh = box
    iw, ih = img.size
    scale = min(bw / iw, bh / ih, 1.0)  # fit inside box, never upscale
    return img.resize((max(1, int(iw * scale)), max(1, int(ih * scale))), Image.LANCZOS)


def _is_sheet(sheet: dict, w: int, h: int) -> bool:
    cw = sheet.get("cellWidth") or 0
    ch = sheet.get("cellHeight") or 0
    if not cw or not ch or w % cw or h % ch:
        return False
    return (w // cw) * (h // ch) > 1  # a single cell = a plain image
