import json
import os
import sys


def base_dir() -> str:
    # 返回数据所在目录：打包后是 exe 所在文件夹（数据放在 exe 旁边），源码运行时是当前文件所在目录
    # PyInstaller onefile extracts to a temp dir; data must live next to the exe.
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    # 程序入口：定位 config.json（不存在则写入默认配置），创建 PetApp 并进入 tkinter 主循环
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
