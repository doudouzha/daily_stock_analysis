---
kind: external_dependency
name: SerpAPI 搜索引擎
slug: serpapi
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
source_files:
    - requirements.txt
    - .env.example
---

SerpAPI 用于获取实时金融新闻数据，支持百度等搜索引擎结果抓取。项目推荐使用 SerpAPI 作为新闻搜索的主要来源，特别是在 GitHub Actions 环境中。需要配置 SERPAPI_API_KEYS 环境变量。