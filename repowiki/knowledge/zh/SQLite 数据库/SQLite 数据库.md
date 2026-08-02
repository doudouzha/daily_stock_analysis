---
kind: external_dependency
name: SQLite 数据库
slug: sqlite
category: external_dependency
category_hints:
    - client_constraint
scope:
    - '**'
source_files:
    - .env.example
---

项目使用 SQLite 作为持久化存储，默认启用 WAL 模式提升并发写入性能。支持数据库路径配置、锁超时设置、写入重试机制。数据文件位于 data/stock_analysis.db，可通过 DATABASE_PATH 环境变量自定义位置。