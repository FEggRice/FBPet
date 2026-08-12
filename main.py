import json
import os
import sys


def base_dir() -> str:
    # PyInstaller onefile extracts to a temp dir; data must live next to the exe.
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    here = base_dir()
    if not getattr(sys, "frozen", False):
        sys.path.insert(0, here)

    from pet.app import PetApp

    config_path = os.path.join(here, "config.json")
    if not os.path.exists(config_path):  # first run next to the exe: write defaults
        from pet.config import default_config

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config(), f, ensure_ascii=False, indent=2)

    PetApp(config_path).run()


if __name__ == "__main__":
    main()
