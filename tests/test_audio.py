import os
import tempfile

import pet.audio as audio_mod
from pet.audio import AudioPlayer


def _record_mci(monkeypatch):
    calls = []
    monkeypatch.setattr(audio_mod, "_mci", lambda cmd, *_: calls.append(cmd))
    return calls


def _make_files(d, names):
    for n in names:
        open(os.path.join(d, n), "w").close()


def test_register_folder_plays_random_mp3():
    with tempfile.TemporaryDirectory() as d:
        _make_files(d, ("a.mp3", "b.mp3", "c.wav", "skip.txt"))
        player = AudioPlayer()
        player.register_folder("click", d)
        played = []
        player._play_file = played.append
        for _ in range(30):
            player.play("click")

    assert played
    names = {os.path.basename(p) for p in played}
    assert names <= {"a.mp3", "b.mp3", "c.wav"}
    assert names == {"a.mp3", "b.mp3", "c.wav"}  # randomness reaches every file


def test_register_single_file_plays_it():
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "x.wav")
        open(wav, "w").close()
        player = AudioPlayer()
        player.register("k", wav)
        played = []
        player._play_file = played.append
        player.play("k")

    assert played == [wav]


def test_play_unknown_key_is_noop():
    player = AudioPlayer()
    played = []
    player._play_file = played.append
    player.play("nope")
    assert not played


def test_register_folder_missing_dir_is_noop():
    player = AudioPlayer()
    played = []
    player._play_file = played.append
    player.register_folder("click", os.path.join(tempfile.gettempdir(), "no_such_dir_xyz"))
    player.play("click")
    assert not played


class _FakeChannel:
    def __init__(self):
        self.play_calls = 0

    def play(self, snd):
        snd.play_calls += 1


class _FakeMixer:
    def __init__(self):
        self.sounds = []

    def Sound(self, path):
        snd = _FakeSound(path)
        self.sounds.append(snd)
        return snd

    def find_channel(self, force=False):
        return _FakeChannel()


class _FakeSound:
    def __init__(self, path):
        self.path = path
        self.play_calls = 0


class _FakePygame:
    def __init__(self):
        self.mixer = _FakeMixer()


def test_overlap_mode_plays_each_sound_on_pygame(monkeypatch):
    calls = _record_mci(monkeypatch)
    player = AudioPlayer()
    player.overlap = True
    player._pygame = _FakePygame()
    player._play_file("a.mp3")
    player._play_file("b.mp3")

    assert calls == []  # overlap mode never touches MCI
    assert [s.play_calls for s in player._pygame.mixer.sounds] == [1, 1]


def test_overlap_mode_falls_back_to_mci_when_pygame_unavailable(monkeypatch):
    calls = _record_mci(monkeypatch)
    player = AudioPlayer()
    player.overlap = True
    player._pygame = False  # pygame init failed
    player._play_file("a.mp3")

    assert "play _snd" in calls  # falls back to single-instance MCI


def test_pool_size_defaults_and_clamps():
    player = AudioPlayer()
    assert player.pool_size == AudioPlayer._POOL_SIZE
    player.set_pool_size(0)
    assert player.pool_size == 1
    player.set_pool_size(10)
    assert player.pool_size == 10


def test_set_pool_size_applies_to_active_pygame(monkeypatch):
    calls = []
    fake = _FakePygame()
    fake.mixer.set_num_channels = lambda n: calls.append(n)
    player = AudioPlayer()
    player._pygame = fake
    player.set_pool_size(4)
    assert calls == [4]


def test_normal_mode_reuses_one_instance(monkeypatch):
    calls = _record_mci(monkeypatch)
    player = AudioPlayer()  # overlap defaults False
    player._play_file("a.mp3")
    player._play_file("b.mp3")

    plays = [c for c in calls if c.startswith("play")]
    assert plays == ["play _snd", "play _snd"]
    assert "close _snd" in calls  # second click cut the first
