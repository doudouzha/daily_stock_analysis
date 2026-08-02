---
kind: external_dependency
name: Tavily 新闻搜索
slug: tavily
category: external_dependency
category_hints:
    - vendor_identity
scope:
    - '**'
source_files:
    - requirements.txt
    - .env.example
---

Tavily 是通用新闻搜索 API，支持多语言新闻检索和摘要生成。项目将其作为新闻搜索的备选方案，与 SerpAPI、Bocha 等其他搜索服务形成互补。需要配置 TAVILY_API_KEYS 环境变量。