---
kind: external_dependency
name: Longbridge 开放平台
slug: longbridge
category: external_dependency
category_hints:
    - vendor_identity
    - auth_protocol
scope:
    - '**'
source_files:
    - requirements.txt
    - .env.example
---

Longbridge 提供港股和美股的增强数据，包括量比、换手率、PE 等字段。支持 OAuth 2.0 认证和 Legacy API Key 两种方式。Linux 环境下有特定的 wheel 依赖要求，Docker 部署时需要注意 glibc 版本兼容性。