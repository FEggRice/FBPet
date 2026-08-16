#!/usr/bin/env python3
"""FBeePet 首次启动种子脚本(幂等):把 FBeePet 默认配置(zhipu/glm-5)
改为 DeepSeek,并清空磁盘上已有的 API key。API key 由用户在网页端
(设置 -> 模型提供商)输入,只存进程内存、不落盘,随桌宠退出清空。
用法:在 FBeePet/ 目录下运行:
    <python> seed_deepseek.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import delete, select

from backend.database import AsyncSessionLocal, init_db
from backend.modules.config.loader import ConfigLoader
from backend.models.setting import Setting


async def main() -> None:
    await init_db()  # 空库则建表并写默认配置
    loader = ConfigLoader()
    cfg = await loader.load()  # cfg 就是 loader.config,后续改动会写回

    # 只对接 DeepSeek:默认 provider 从 zhipu 换成 deepseek-chat
    cfg.model.provider = "deepseek"
    cfg.model.model = "deepseek-chat"

    # key 由用户网页端输入、只存内存,这里确保磁盘上没有任何残留 key
    ds = cfg.providers.get("deepseek")
    if ds is not None:
        ds.enabled = True
        ds.api_key = ""
        ds.api_keys = []
    else:
        from backend.modules.config.schema import ProviderConfig

        cfg.providers["deepseek"] = ProviderConfig(
            enabled=True, api_base="https://api.deepseek.com/v1"
        )

    # 只保留允许的 provider:ConfigLoader.save() 只 merge 不删行,
    # 所以必须直接把库里的历史残留 provider 行删掉,否则下次 load 还会读回来
    from backend.modules.providers.registry import ALLOWED_PROVIDER_IDS

    for pid in [p for p in cfg.providers if p not in ALLOWED_PROVIDER_IDS]:
        del cfg.providers[pid]

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Setting.key).where(Setting.key.like("config.providers.%"))
        )
        for key in result.scalars().all():
            provider_name = key.split(".")[2] if len(key.split(".")) >= 3 else ""
            if provider_name not in ALLOWED_PROVIDER_IDS:
                await session.execute(delete(Setting).where(Setting.key == key))
        await session.commit()

    await loader.save()
    print(
        "FBeePet seed: provider=deepseek model=deepseek-chat "
        f"(API key 由用户在网页端输入,不落盘;保留提供商: {', '.join(sorted(ALLOWED_PROVIDER_IDS))})"
    )


if __name__ == "__main__":
    asyncio.run(main())
