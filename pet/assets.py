"""Placeholder asset generation: sprite sheet PNG (Pillow) + wav tones (stdlib).
Run on first launch; delete pet.png / audio/ to regenerate."""
from __future__ import annotations

import math
import os
import wave

from PIL import Image, ImageDraw

_KEY = (255, 0, 255)  # matches default transparentColor in config; never used in sprites


def ensure_assets(cfg, force: bool = False) -> None:
    sheet = cfg.sprite_sheet
    sheet_path = cfg.resolve(sheet.get("path", "pet.png"))
    if force or not os.path.exists(sheet_path):
        os.makedirs(os.path.dirname(sheet_path) or ".", exist_ok=True)
        _generate_sprite_sheet(sheet_path, sheet)

    for key, freq, seconds in (("startup", 660, 0.18), ("click", 880, 0.08), ("reminder", 440, 0.4)):
        path = cfg.resolve(cfg.audio.get(key, f"audio/{key}.wav"))
        if not os.path.exists(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            _write_wav(path, freq, seconds)


def _generate_sprite_sheet(path: str, sheet: dict) -> None:
    cols = sheet.get("cols", 8)
    rows = sheet.get("rows", 3)
    cw = sheet.get("cellWidth", 128)
    ch = sheet.get("cellHeight", 128)
    img = Image.new("RGBA", (cols * cw, rows * ch), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    body_colors = [(255, 165, 0), (79, 195, 247), (240, 98, 146)]  # idle / spawn / clicked
    for r in range(rows):
        body = body_colors[r] if r < len(body_colors) else body_colors[-1]
        for c in range(cols):
            t = c / max(1, cols - 1)
            _draw_cell(d, c * cw, r * ch, cw, ch, body, r, t)

    img.save(path, "PNG")


def _draw_cell(d: ImageDraw.ImageDraw, x: int, y: int, cw: int, ch: int, body, row: int, t: float) -> None:
    scale = 0.35 + 0.65 * t if row == 1 else 0.92  # spawn row grows in
    cx = x + cw / 2.0
    cy = y + ch / 2.0 + ch * 0.04
    R = cw * 0.32 * scale

    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=body, outline=(0, 0, 0, 120), width=3)

    ink = (60, 40, 25, 255)
    eye_y = cy - R * 0.08
    eye_dx = R * 0.36
    eye_r = R * 0.13
    blink = row == 0 and t >= 0.8

    if blink:
        lw = int(max(2, R * 0.09))
        d.line([cx - eye_dx - eye_r, eye_y, cx - eye_dx + eye_r, eye_y], fill=ink, width=lw)
        d.line([cx + eye_dx - eye_r, eye_y, cx + eye_dx + eye_r, eye_y], fill=ink, width=lw)
    else:
        d.ellipse([cx - eye_dx - eye_r, eye_y - eye_r, cx - eye_dx + eye_r, eye_y + eye_r], fill=ink)
        d.ellipse([cx + eye_dx - eye_r, eye_y - eye_r, cx + eye_dx + eye_r, eye_y + eye_r], fill=ink)

    my = cy + R * 0.32
    if row == 2:
        d.ellipse([cx - R * 0.2, my - R * 0.05, cx + R * 0.2, my + R * 0.25], fill=ink)  # surprised "o"
    else:
        lw = int(max(2, R * 0.07))
        d.arc([cx - R * 0.3, my - R * 0.15, cx + R * 0.3, my + R * 0.3], start=20, end=160, fill=ink, width=lw)  # smile


def _write_wav(path: str, freq: float, seconds: float) -> None:
    import array

    sample_rate = 44100
    n = int(sample_rate * seconds)
    attack = min(0.02, seconds / 4)
    samples = array.array("h")
    for i in range(n):
        t = i / sample_rate
        env = min(1.0, t / attack) * min(1.0, (seconds - t) / attack)
        samples.append(int(math.sin(2 * math.pi * freq * t) * env * 12000))

    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(samples.tobytes())
