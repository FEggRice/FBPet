import json
import os

from pet.config import PetConfig

HERE = os.path.dirname(os.path.abspath(__file__))
ADQ = os.path.dirname(HERE)
CONFIG_PATH = os.path.join(ADQ, "config.json")


def test_load_real_config_has_animations_and_rest():
    cfg = PetConfig.load(CONFIG_PATH)

    assert "idle" in cfg.animations
    assert cfg.animations["idle"].get("frames", 1) >= 1
    assert cfg.rest["threshold"] > 0
    assert cfg.get("spriteSheet", "cellWidth") == 128


def test_save_then_load_round_trips_settings():
    path = os.path.join(ADQ, "key_counts_test_config.json")
    try:
        cfg = PetConfig.load(CONFIG_PATH)
        cfg.rest["threshold"] = 250
        cfg.animations["dance"] = {"row": 2, "frames": 5, "fps": 12, "loop": True}
        cfg.save(path)

        reloaded = PetConfig.load(path)
        assert reloaded.rest["threshold"] == 250
        assert reloaded.animations["dance"]["frames"] == 5
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_load_ensures_idle_animation():
    path = os.path.join(ADQ, "key_counts_test_config.json")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"rest": {"threshold": 50}}, f)

        cfg = PetConfig.load(path)
        assert "idle" in cfg.animations
        assert cfg.animations["idle"]["frames"] >= 1
    finally:
        if os.path.exists(path):
            os.remove(path)
