---
kind: external_dependency
name: Yahoo Finance 数据源
slug: yfinance
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
source_files:
    - requirements.txt
    - data_provider/yfinance_fetcher.py
---

YFinance 作为全球市场的后备数据源，优先级为 4，主要用于美股数据获取。在 requirements.txt 中明确标注为 Fallback 用途，当其他数据源不可用时自动切换。支持历史行情、实时价格、基本面数据等功能。