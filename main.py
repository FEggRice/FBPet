import json
import os


def base_dir() -> str:
    # 数据所在目录：源码运行时是当前文件所在目录
    return os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    # 程序入口：定位 config.json（不存在则写入默认配置），创建 PetApp 并进入 tkinter 主循环
    here = base_dir()

    from pet.app import PetApp

    config_path = os.path.join(here, "config.json")
    if not os.path.exists(config_path):  # 首次运行写入默认配置
        from pet.config import default_config

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(default_config(), f, ensure_ascii=False, indent=2)

    PetApp(config_path).run()


if __name__ == "__main__":
    main()
