---
kind: external_dependency
name: Tushare Pro API
slug: tushare-pro
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
source_files:
    - requirements.txt
    - .env.example
---

Tushare Pro 是 A 股市场的高质量数据源，优先级为 2，需要 TUSHARE_TOKEN 配置。提供稳定的历史行情、财务数据、公告信息等服务。项目支持自定义接入地址，可指向自建网关或第三方兼容镜像，但需注意数据安全风险评估。