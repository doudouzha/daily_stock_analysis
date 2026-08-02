---
kind: external_dependency
name: AkShare 金融数据接口
slug: akshare
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
source_files:
    - requirements.txt
    - data_provider/akshare_fetcher.py
---

AkShare 是项目的核心数据源之一，优先级为 1，提供 A 股、港股、美股等多市场金融数据。作为免费数据源，受上游限流和接口变动影响，稳定性不保证。项目实现了自动 fallback 机制，当 AkShare 不可用时自动切换到其他数据源。