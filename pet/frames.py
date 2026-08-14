"""Frame-source resolution for one pet image or per-state image files.

Sources, in priority order per state:
  1. `file` on the animation (a GIF/APNG or a single image, resolved vs base_dir)
  2. a row crop from the shared sprite sheet (when the animation names a `row`)
  3. the idle state's frames (fallback for states that name no source)

The shared sheet itself may also be a GIF (all states share it) or a single
image (becomes the idle base). Display size follows the idle state. Pure Pillow,
no GUI dependency."""
from __future__ import annotations

import os

from PIL import Image


def load_frames(path: str, base_dir: str, sheet: dict, animations: dict,
                box: tuple[int, int]) -> tuple[dict, tuple[int, int]]:
    # 核心函数：按优先级给每个动画状态取帧。
    # ① 动画自己的 file（GIF 取全部帧 / 单图取一帧）
    # ② 共享精灵表是动画则全员共用；否则按各状态 row 从表里裁一行
    # ③ 单图/无 row 的 idle 兜底为表的第一行或整图
    # ④ 仍未取到帧的状态复用 idle 帧。返回 (帧字典, 显示尺寸)
    states = list(animations)
    frames: dict[str, list] = {}

    # 1) explicit per-state image/gif files
    for name, anim in animations.items():
        fpath = anim.get("file")
        if fpath:
            resolved = os.path.join(base_dir, fpath)
            if os.path.exists(resolved):
                frames[name] = _load_image(resolved, box)

    sheet_img = Image.open(path) if os.path.exists(path) else None

    # 2a) the shared sheet is itself an animation → every state shares it
    if sheet_img is not None and getattr(sheet_img, "is_animated", False):
        gif = [_resize(_rgba(sheet_img, i), box) for i in range(sheet_img.n_frames)]
        for name in states:
            frames.setdefault(name, list(gif))
        return frames, _display(frames, box)

    if sheet_img is not None:
        sheet_img = _to_rgba(sheet_img)
        is_sheet = _is_sheet(sheet, sheet_img.width, sheet_img.height)
    else:
        is_sheet = False

    # 2b) states that name a row crop it from the sheet
    if is_sheet:
        cw, ch = sheet["cellWidth"], sheet["cellHeight"]
        cols = sheet_img.width // cw
        for name, anim in animations.items():
            if name in frames or anim.get("row") is None:
                continue
            row = anim["row"]
            n = min(anim.get("frames", cols), cols)
            frames[name] = [sheet_img.crop((i * cw, row * ch, (i + 1) * cw, (row + 1) * ch)) for i in range(n)]

    # 3) a single-image sheet becomes the idle base
    if "idle" not in frames and sheet_img is not None and not is_sheet:
        frames["idle"] = [_resize(sheet_img, box)]
    #   ...and if idle is row-less on a real sheet, default it to row 0
    if not frames.get("idle") and is_sheet:
        cw, ch = sheet["cellWidth"], sheet["cellHeight"]
        cols = sheet_img.width // cw
        n = min(animations.get("idle", {}).get("frames", cols), cols)
        frames["idle"] = [sheet_img.crop((i * cw, 0, (i + 1) * cw, ch)) for i in range(n)]

    # 4) anything still empty reuses the idle frames
    idle_frames = frames.get("idle") or []
    for name in states:
        if not frames.get(name):
            frames[name] = list(idle_frames) if idle_frames else []

    return frames, _display(frames, box)


def _load_image(path: str, box: tuple[int, int]) -> list:
    # 加载一张图：若是 GIF 则取全部帧，否则单帧；每帧都等比缩放到 box 内
    img = Image.open(path)
    if getattr(img, "is_animated", False):
        return [_resize(_rgba(img, i), box) for i in range(img.n_frames)]
    return [_resize(_to_rgba(img), box)]


def _rgba(img: Image.Image, index: int) -> Image.Image:
    # 取 GIF 第 index 帧并转成 RGBA（调 seek 定位到该帧）
    img.seek(index)
    return _to_rgba(img)


def _to_rgba(img: Image.Image) -> Image.Image:
    # 转 RGBA，并把透明像素的 RGB 清零：
    # 防止 GIF 的透明调色板色（常为绿色）在缩放时渗入边缘产生杂色
    rgba = img.copy().convert("RGBA")
    r, g, b, a = rgba.split()
    mask = a.point(lambda v: 255 if v == 0 else 0)
    black = Image.new("L", rgba.size, 0)
    return Image.merge("RGBA", (
        Image.composite(black, r, mask),
        Image.composite(black, g, mask),
        Image.composite(black, b, mask),
        a,
    ))


def _resize(img: Image.Image, box: tuple[int, int]) -> Image.Image:
    # 等比缩放到 box 内（小图也放大），并硬化 alpha 去毛边
    bw, bh = box
    iw, ih = img.size
    scale = min(bw / iw, bh / ih)  # fit inside box; upscale small pets for uniform size
    resized = img.resize((max(1, int(iw * scale)), max(1, int(ih * scale))), Image.LANCZOS)
    return _harden_alpha(resized)


def _harden_alpha(img: Image.Image) -> Image.Image:
    # 二值化 alpha：≥128 全不透明、否则全透明。
    # LANCZOS 缩放会留下半透明边缘，叠加透明色键会渗出紫边，这步把它去掉
    if img.mode != "RGBA":
        return img
    r, g, b, a = img.split()
    a = a.point(lambda v: 255 if v >= 128 else 0)
    return Image.merge("RGBA", (r, g, b, a))


def _is_sheet(sheet: dict, w: int, h: int) -> bool:
    # 判断图片是否为合法精灵表：尺寸能被 cellWidth/cellHeight 整除，且格子数 >1
    cw = sheet.get("cellWidth") or 0
    ch = sheet.get("cellHeight") or 0
    if not cw or not ch or w % cw or h % ch:
        return False
    return (w // cw) * (h // ch) > 1  # a single cell = a plain image


def _display(frames: dict, box: tuple[int, int]) -> tuple[int, int]:
    # 决定窗口显示尺寸：优先 idle 首帧，其次任一状态首帧，都没有则用 box
    if frames.get("idle") and frames["idle"]:
        return frames["idle"][0].size
    for imgs in frames.values():
        if imgs:
            return imgs[0].size
    return box
