import os
import tempfile

from PIL import Image

from pet.frames import load_frames

ANIMS = {"idle": {"row": 0, "frames": 2}, "clicked": {"row": 1, "frames": 2}}


def _save(img, path):
    img.save(path)
    return path


def _gif(path, colors=((255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255))):
    imgs = [Image.new("RGBA", (60, 60), c) for c in colors]
    imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=80, loop=0)
    return path


def test_small_image_is_upscaled_to_fit_box():
    with tempfile.TemporaryDirectory() as d:
        path = _save(Image.new("RGBA", (200, 100), (255, 0, 0, 255)), os.path.join(d, "a.png"))
        frames, size = load_frames(path, d, {}, ANIMS, box=(400, 400))

    assert len(frames["idle"]) == 1
    assert len(frames["clicked"]) == 1
    assert size == (400, 200)  # smaller than box → upscaled to fit (uniform size)
    assert frames["idle"][0].mode == "RGBA"


def test_oversized_image_fits_within_box_preserving_aspect():
    with tempfile.TemporaryDirectory() as d:
        path = _save(Image.new("RGBA", (200, 100), (255, 0, 0, 255)), os.path.join(d, "big.png"))
        frames, size = load_frames(path, d, {}, ANIMS, box=(100, 100))

    assert size == (100, 50)


def test_animated_sheet_gives_same_frames_for_every_state():
    with tempfile.TemporaryDirectory() as d:
        path = _gif(os.path.join(d, "a.gif"))
        frames, size = load_frames(path, d, {}, ANIMS, box=(128, 128))

    assert len(frames["idle"]) == 3
    assert len(frames["clicked"]) == 3
    assert size == (128, 128)  # 60×60 gif upscaled to the 128 box


def test_sprite_sheet_crops_per_state_row():
    sheet = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    sheet.putpixel((5, 5), (255, 0, 0, 255))    # idle row 0, col 0
    sheet.putpixel((55, 5), (255, 0, 0, 255))   # idle row 0, col 1
    sheet.putpixel((5, 55), (255, 0, 0, 255))   # clicked row 1, col 0
    with tempfile.TemporaryDirectory() as d:
        path = _save(sheet, os.path.join(d, "sheet.png"))
        frames, size = load_frames(path, d, {"cellWidth": 50, "cellHeight": 50}, ANIMS, box=(50, 50))

    assert len(frames["idle"]) == 2
    assert len(frames["clicked"]) == 2
    assert size == (50, 50)
    assert frames["idle"][1].getpixel((5, 5))[3] == 255
    assert frames["clicked"][0].getpixel((5, 5))[3] == 255


def test_per_state_file_gif_and_single_image():
    with tempfile.TemporaryDirectory() as d:
        _gif(os.path.join(d, "a.gif"))
        _save(Image.new("RGBA", (40, 40), (0, 0, 255, 255)), os.path.join(d, "b.png"))
        animations = {"idle": {"file": "a.gif"}, "reminder": {"file": "b.png"}}
        frames, size = load_frames(os.path.join(d, "missing.png"), d, {}, animations, box=(128, 128))

    assert len(frames["idle"]) == 3
    assert len(frames["reminder"]) == 1
    assert frames["idle"][0].size == (128, 128)
    assert size == (128, 128)  # display follows the idle state


def test_states_without_file_reuse_idle_frames():
    with tempfile.TemporaryDirectory() as d:
        _gif(os.path.join(d, "a.gif"))
        animations = {"idle": {"file": "a.gif"}, "clicked": {}}
        frames, _ = load_frames(os.path.join(d, "missing.png"), d, {}, animations, box=(128, 128))

    assert len(frames["clicked"]) == 3
    assert frames["clicked"][0].size == (128, 128)


def test_resized_edges_have_no_semi_transparent_pixels():
    """LANCZOS resize blends transparent border into the pet, so edge pixels get
    alpha 1-254 and bleed the magenta key through → purple border. After the fix
    every resized frame is binary alpha (0 or 255)."""
    img = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    for y in range(80, 120):
        for x in range(80, 120):
            img.putpixel((x, y), (255, 255, 255, 255))
    with tempfile.TemporaryDirectory() as d:
        path = _save(img, os.path.join(d, "square.png"))
        frames, _ = load_frames(path, d, {}, {"idle": {}}, box=(100, 100))

    frame = frames["idle"][0]
    alphas = {frame.getpixel((x, y))[3] for x in range(frame.width) for y in range(frame.height)}
    assert alphas <= {0, 255}
