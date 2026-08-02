---
kind: external_dependency
name: TickFlow 实时行情
slug: tickflow
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
source_files:
    - requirements.txt
    - .env.example
---

TickFlow 是 A 股市场的专业数据源，提供日 K 线、实时行情、股票列表等功能。支持批量预取和自定义除权方式（forward/backward/forward_additive/backward_additive）。当权限不足时会自动降级到其他数据源。