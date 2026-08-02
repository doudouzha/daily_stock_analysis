---
kind: logging_system
name: 日志系统 — 基于 Python logging 的统一配置与分层输出
category: logging_system
scope:
    - '**'
source_files:
    - src/logging_config.py
    - main.py
    - tests/test_logging_config.py
---

## 1. 使用的框架与工具
- 基于 Python 标准库 `logging`，未引入第三方日志框架。
- 使用 `logging.handlers.RotatingFileHandler` 实现按大小轮转的文件日志。
- 通过自定义 `RelativePathFormatter` 将日志中的绝对路径转换为相对项目根的路径，便于容器/CI 环境阅读。

## 2. 核心文件与入口
- `src/logging_config.py`：统一的日志初始化模块，提供 `setup_logging()` 入口、日志格式常量、第三方库降噪列表、LiteLLM 日志级别解析等。
- `main.py`：应用主调度程序，在启动早期通过 `_setup_bootstrap_logging()` 输出 stderr-only 的临时日志，随后调用 `_setup_runtime_logging()` → `setup_logging(log_prefix="stock_analysis", ...)` 完成正式日志配置；若文件日志不可写则自动降级为仅控制台输出。
- `tests/test_logging_config.py`：对日志格式、LiteLLM 日志级别默认行为、无效值回退等进行回归测试。

## 3. 架构与约定
- **三层输出**
  - 控制台（stdout）：根据 `debug` 参数或 `console_level` 决定级别（调试模式 DEBUG，否则 INFO）。
  - 常规日志文件：`logs/<prefix>_YYYYMMDD.log`，INFO 级别，10MB 轮转，保留 5 个备份。
  - 调试日志文件：`logs/<prefix>_debug_YYYYMMDD.log`，DEBUG 级别，50MB 轮转，保留 3 个备份。
- **统一格式**
  - 格式模板：`%(asctime)s | %(levelname)-8s | %(name)s | %(pathname)s:%(lineno)d | %(message)s`，日期格式 `%Y-%m-%d %H:%M:%S`。
  - 所有 handler 共享同一个 `RelativePathFormatter`，保证路径一致性。
- **根 Logger 策略**
  - 根 logger 级别设为 `DEBUG`，实际过滤由各 handler 控制，避免遗漏任何级别的日志。
  - 每次 `setup_logging` 会先清空已有 handlers，防止重复添加。
- **第三方库降噪**
  - 默认降低 `urllib3`、`sqlalchemy`、`google`、`httpx` 等库的日志级别至 WARNING。
  - LiteLLM 相关 logger（`LiteLLM`、`LiteLLM Router`、`LiteLLM Proxy`、`litellm`）的级别通过环境变量 `LITELLM_LOG_LEVEL` 控制，默认 WARNING；传入非法值时回退到 WARNING 并记录警告。
- **启动阶段双阶段日志**
  - 在配置加载前，`main.py` 使用 `_setup_bootstrap_logging()` 向 stderr 输出最小化日志，确保早期错误可观测。
  - 配置加载后，通过 `_setup_runtime_logging()` 切换到正式的多 handler 配置，并在文件 I/O 失败时优雅降级。

## 4. 使用约定与约束
- **模块内获取 logger**：全仓库广泛采用 `logger = logging.getLogger(__name__)` 的模式，每个模块拥有独立命名空间。
- **日志级别使用**：业务逻辑中普遍使用 `logger.info` / `logger.debug` / `logger.warning`，错误场景通过异常捕获 + warning/error 记录，未见全局异常处理器统一打日志。
- **结构化字段**：当前日志以固定分隔符拼接字符串为主，未使用 JSON 结构化输出；但部分关键路径（如大盘复盘复用）通过格式化参数传递上下文键值，便于检索。
- **环境变量控制**
  - `LITELLM_LOG_LEVEL`：控制 LiteLLM 相关 logger 的级别，支持 DEBUG/INFO/WARNING/ERROR/CRITICAL，默认 WARNING。
  - `ENV_FILE`：指定 .env 文件路径，影响运行时环境变量加载，间接影响日志行为（如 log_dir 等配置）。
- **Docker/部署约束**：当日志目录不可写时，系统会记录警告并降级为仅控制台输出，官方 Docker 镜像会在 entrypoint 中修复权限。
- **测试保障**：`test_logging_config.py` 验证了日志格式包含 logger name、LiteLLM 默认安静、无效级别回退等行为，确保日志配置稳定性。

## 5. 与其他组件的集成点
- API 层（`api/app.py`、`api/middlewares/*`、`api/v1/endpoints/*`）均通过 `logging.getLogger(__name__)` 记录请求、认证、错误等信息，遵循同一日志格式。
- Bot 平台（`bot/commands/*`、`bot/platforms/*`）同样使用标准 logging，保持日志风格一致。
- 数据获取器（`data_provider/*`）通过被降噪的第三方 logger 减少噪音，关键错误由上层服务记录。