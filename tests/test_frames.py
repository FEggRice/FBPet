import os
import tempfile

from PIL import Image

from pet.frames import load_frames

ANIMS = {"idle": {"row": 0, "frames": 2}, "clicked": {"row": 1, "frames": 2}}


def _save(img, path):
    img.save(path)
    return path


def test_single_static_image_gives_one_frame_per_state_at_natural_size():
    with tempfile.TemporaryDirectory() as d:
        path = _save(Image.new("RGBA", (200, 100), (255, 0, 0, 255)), os.path.join(d, "a.png"))
        frames, size = load_frames(path, {}, ANIMS, box=(400, 400))

    assert len(frames["idle"]) == 1
    assert len(frames["clicked"]) == 1
    assert size == (200, 100)  # smaller than box → never upscale
    assert frames["idle"][0].mode == "RGBA"


def test_oversized_image_fits_within_box_preserving_aspect():
    with tempfile.TemporaryDirectory() as d:
        path = _save(Image.new("RGBA", (200, 100), (255, 0, 0, 255)), os.path.join(d, "big.png"))
        frames, size = load_frames(path, {}, ANIMS, box=(100, 100))

    assert size == (100, 50)


def test_animated_gif_gives_same_frames_for_every_state():
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "a.gif")
        imgs = [Image.new("RGBA", (60, 60), color) for color in ((255, 0, 0, 255), (0, 255, 0, 255), (0, 0, 255, 255))]
        imgs[0].save(path, save_all=True, append_images=imgs[1:], duration=80, loop=0)
        frames, size = load_frames(path, {}, ANIMS, box=(128, 128))

    assert len(frames["idle"]) == 3
    assert len(frames["clicked"]) == 3
    assert size == (60, 60)


def test_sprite_sheet_crops_per_state_row():
    sheet = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    sheet.putpixel((5, 5), (255, 0, 0, 255))    # idle row 0, col 0
    sheet.putpixel((55, 5), (255, 0, 0, 255))   # idle row 0, col 1
    sheet.putpixel((5, 55), (255, 0, 0, 255))   # clicked row 1, col 0
    with tempfile.TemporaryDirectory() as d:
        path = _save(sheet, os.path.join(d, "sheet.png"))
        frames, size = load_frames(path, {"cellWidth": 50, "cellHeight": 50}, ANIMS, box=(50, 50))

    assert len(frames["idle"]) == 2
    assert len(frames["clicked"]) == 2
    assert size == (50, 50)
    assert frames["idle"][1].getpixel((5, 5))[3] == 255
    assert frames["clicked"][0].getpixel((5, 5))[3] == 255
