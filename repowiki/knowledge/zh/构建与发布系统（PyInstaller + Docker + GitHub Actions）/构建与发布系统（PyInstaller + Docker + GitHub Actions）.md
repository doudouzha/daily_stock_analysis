---
kind: build_system
name: 构建与发布系统（PyInstaller + Docker + GitHub Actions）
category: build_system
scope:
    - '**'
source_files:
    - requirements.txt
    - pyproject.toml
    - docker/Dockerfile
    - docker/docker-compose.yml
    - .github/workflows/ci.yml
    - .github/workflows/docker-publish.yml
    - .github/workflows/desktop-release.yml
    - .github/workflows/create-release.yml
    - scripts/build-backend-macos.sh
    - scripts/build-backend.ps1
    - scripts/build-desktop-macos.sh
    - scripts/build-all-macos.sh
    - scripts/ci_gate.sh
    - scripts/check_static_assets.py
    - apps/dsa-web/package.json
    - apps/dsa-desktop/package.json
---

## 1. 使用的系统与工具
- **Python 依赖管理**：`requirements.txt` 声明运行时依赖，`.github/requirements-ci.txt` 用于 CI 环境；`pyproject.toml` 仅配置 Black、isort、Bandit 等代码质量工具。
- **前端构建**：React + Vite（`apps/dsa-web/package.json`），通过 `npm ci` / `npm run build` 生成静态资源到 `static/`。
- **桌面应用打包**：Electron + Electron Builder（`apps/dsa-desktop/package.json`），输出 Windows 安装包和 macOS DMG。
- **后端可执行文件**：PyInstaller 将 Python 源码冻结为单目录可执行产物 `dist/backend/stock_analysis`，并内嵌 static/strategies 等数据。
- **容器化**：多阶段 Dockerfile（Node 20 构建前端 → Python 3.11-slim-bookworm 运行后端），`docker-compose.yml` 提供 analyzer/server 两种运行模式。
- **CI/CD**：GitHub Actions 工作流覆盖 PR 检查、Docker 镜像构建推送、桌面端跨平台打包与 GitHub Release 发布。

## 2. 核心文件与位置
- 依赖清单：`requirements.txt`、`.github/requirements-ci.txt`
- 代码规范配置：`pyproject.toml`（Black/isort/Bandit）
- Docker 镜像与编排：`docker/Dockerfile`、`docker/docker-compose.yml`、`docker/entrypoint.sh`
- 构建脚本：`scripts/build-backend-macos.sh`、`scripts/build-backend.ps1`、`scripts/build-desktop-macos.sh`、`scripts/build-all-macos.sh`、`scripts/ci_gate.sh`、`scripts/check_static_assets.py`
- CI 工作流：`.github/workflows/ci.yml`、`.github/workflows/docker-publish.yml`、`.github/workflows/desktop-release.yml`、`.github/workflows/create-release.yml`
- 前端包定义：`apps/dsa-web/package.json`、`apps/dsa-desktop/package.json`

## 3. 架构与约定
- **多阶段构建**：Dockerfile 先用 `node:20-slim` 编译前端静态资源，再复制到 Python 基础镜像中，避免在运行镜像中安装 Node。
- **非 root 运行**：镜像创建 `dsa` 用户（UID 1000），数据/日志/报告目录预创建并授权，entrypoint 在启动时修复 bind mount 权限。
- **环境变量驱动**：`WEBUI_HOST`、`API_PORT`、`TZ=Asia/Shanghai`、`DATABASE_PATH`、`LOG_DIR` 等通过 `.env` 注入，compose 使用 `env_file` 加载。
- **版本与标签**：Release 由 `vX.Y.Z` 注解标签触发，`docker-publish.yml` 提取 tag 作为 `DSA_WEB_VERSION` 和 `DSA_WEB_REVISION` 传入构建参数，同时生成 `latest`、`sha` 等多标签。
- **产物结构**：PyInstaller 输出 `dist/backend/stock_analysis/`（含 `_internal/` 或同级 `static`、`strategies`），Electron 输出 Windows installer + zip 以及 macOS DMG，Docker 镜像暴露 8000 端口并提供 `/api/health` 健康检查。
- **缓存策略**：GitHub Actions 使用 `actions/cache` 缓存 pip/npm/electron 依赖，Docker Buildx 使用 GHA cache 加速镜像构建。

## 4. 约定与约束
- **依赖版本锁定**：`requirements.txt` 对关键库使用 `>=` 与上限组合（如 `litellm>=1.80.10,!=1.82.7,!=1.82.8,<2.0.0`），对 Linux+Python<3.12 的 longbridge SDK 使用条件依赖。
- **CI 门禁**：`ci.yml` 在 PR 上执行语法检查、flake8 致命错误检测、确定性测试与离线测试套件；`ci_gate.sh` 统一封装这些步骤。
- **Docker 健康检查**：`HEALTHCHECK` 轮询 `/api/health` 或 `/health`，失败时回退到 Python 探针。
- **桌面签名约束**：macOS 构建强制验证未签名 App Bundle 与 DMG 内容，防止 Gatekeeper 误判；Windows/macOS 双架构并行构建。
- **Release 前置校验**：`docker-publish.yml` 要求带注解信息的 tag（`git tag -a`），否则拒绝发布；`create-release.yml` 自动生成 release notes。
- **静态资源一致性**：构建前后均调用 `check_static_assets.py` 校验 `static/` 引用完整性，确保 PyInstaller 打包后前端资源不缺失。
- **策略文件完整性**：构建脚本统计 `strategies/*.yaml` 数量并与打包产物对比，防止遗漏内置策略。