---
kind: dependency_management
name: 多语言依赖管理：Python requirements.txt + npm lockfile + Docker 构建锁定
category: dependency_management
scope:
    - '**'
source_files:
    - daily_stock_analysis/requirements.txt
    - daily_stock_analysis/pyproject.toml
    - daily_stock_analysis/apps/dsa-web/package.json
    - daily_stock_analysis/apps/dsa-web/package-lock.json
    - daily_stock_analysis/apps/dsa-desktop/package.json
    - daily_stock_analysis/apps/dsa-desktop/package-lock.json
    - daily_stock_analysis/docker/Dockerfile
    - daily_stock_analysis/.github/requirements-ci.txt
---

本仓库采用多语言、多子项目的依赖管理策略，分别针对 Python 后端、Web 前端与 Electron 桌面端进行独立声明与锁定。

**1. Python 后端依赖管理**
- 核心清单文件为根目录 `requirements.txt`，使用 `>=` 指定最低版本并辅以注释说明优先级与兼容性约束（如 exchange-calendars 4.5.x 与 pandas 3 Timedelta "T" 不兼容、longbridge 在 Linux/Python<3.12 下固定为 0.2.74）。
- 通过 `-r ../requirements.txt` 引用方式在 `.github/requirements-ci.txt` 中复用后端依赖，CI 额外引入 flake8、pytest 用于测试与 lint。
- 未使用 pipenv/poetry/uv 等现代工具，也未提交 `requirements.lock` 或 `poetry.lock`，依赖版本由开发者手动维护。
- `pyproject.toml` 仅包含 black、isort、bandit 等代码风格与安全扫描配置，不包含依赖声明。
- Docker 镜像基于 `python:3.11-slim-bookworm`，通过 `pip install -r requirements.txt` 安装依赖，并使用 `--mount=type=cache,target=/root/.cache/pip` 缓存加速。

**2. Web 前端依赖管理（React/Vite）**
- 位于 `apps/dsa-web/package.json`，使用 `^` 语义化版本控制，同时提交 `package-lock.json`（lockfileVersion 3）锁定精确版本。
- 通过 `engines` 字段强制 Node >=20.19.0 <27、npm >=10。
- 构建脚本使用 `vite build`，测试使用 `vitest run`，E2E 使用 Playwright。

**3. Electron 桌面端依赖管理**
- 位于 `apps/dsa-desktop/package.json`，依赖 electron-updater，开发依赖 electron 与 electron-builder。
- 同样提交 `package-lock.json` 锁定版本。
- 通过 `electron-builder` 打包为 Windows NSIS 安装包与 macOS DMG，发布到 GitHub Releases。

**4. 容器化与构建锁定**
- `docker/Dockerfile` 采用多阶段构建：第一阶段使用 `node:20-slim` 构建前端静态资源，第二阶段基于 `python:3.11-slim-bookworm` 安装 Python 依赖。
- 前端构建使用 `npm ci` 确保可重复安装，Python 依赖通过 `pip install -r requirements.txt` 安装。
- 镜像内预装 wkhtmltopdf、字体等系统依赖以支持 Markdown 转图片功能。

**5. 特殊依赖处理**
- Git 直接依赖：`alphasift` 通过 `git+https://...#egg=alphasift` 从 GitHub 特定 commit 安装。
- 平台条件依赖：`longbridge` 根据操作系统和 Python 版本选择不同版本（Linux+Python<3.12 固定 0.2.74，其他情况使用 >=4.0.5,<5）。
- 可选依赖：`httpx[socks]` 启用 SOCKS 代理支持。

**6. 约定与约束**
- Python 依赖按数据源优先级排序（efinance > akshare > tushare > pytdx > baostock > yfinance），体现回退策略。
- LLM 相关依赖（litellm、tiktoken、openai）明确排除已知问题版本（如 `!=1.82.7,!=1.82.8`）。
- 所有前端子项目均提交 lockfile，确保构建可重现。
- 未使用私有 PyPI 源或 vendoring 策略，依赖直接从官方源获取。