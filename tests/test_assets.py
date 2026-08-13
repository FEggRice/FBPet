import os
import tempfile

from pet.assets import discover_characters, discover_sounds


def _touch(path):
    open(path, "w").close()


def test_discover_characters_lists_png_and_gif_only():
    with tempfile.TemporaryDirectory() as d:
        for f in ("b.png", "a.gif", "c.jpg", "notes.txt"):
            _touch(os.path.join(d, f))

        assert discover_characters(d) == ["a.gif", "b.png"]


def test_discover_characters_empty_dir():
    with tempfile.TemporaryDirectory() as d:
        assert discover_characters(d) == []


def test_discover_characters_prefers_sprites_folder():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "sprites"))
        _touch(os.path.join(d, "root.png"))
        _touch(os.path.join(d, "sprites", "b.png"))
        _touch(os.path.join(d, "sprites", "a.gif"))

        assert discover_characters(d) == ["a.gif", "b.png"]


def test_discover_sounds_lists_wavs_in_audio_dir_only():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "audio"))
        for f in ("startup.wav", "custom.wav"):
            _touch(os.path.join(d, "audio", f))
        _touch(os.path.join(d, "loose.wav"))  # not in audio/ → ignored

        assert discover_sounds(d) == ["custom.wav", "startup.wav"]


def test_discover_sounds_missing_audio_dir():
    with tempfile.TemporaryDirectory() as d:
        assert discover_sounds(d) == []
