---
kind: error_handling
name: FastAPI 全局异常处理与统一错误响应体系
category: error_handling
scope:
    - '**'
source_files:
    - api/v1/errors.py
    - api/middlewares/error_handler.py
    - api/app.py
    - src/llm/errors.py
---

该仓库采用 FastAPI + Starlette 构建的 API 服务，围绕 `HTTPException`、自定义中间件和统一的 JSON 错误体格式，形成了分层清晰的全局异常处理体系。

**1. 核心机制与组件**
- **统一错误体构造器**：`api/v1/errors.py` 提供 `error_body()`、`api_error()`、`error_json_response()` 三个辅助函数，所有业务端点通过 `api_error(status_code, error_code, message, detail=...)` 抛出结构化 HTTP 异常，返回固定字段 `{error, message, detail}` 的 JSON。
- **全局异常处理器注册**：`api/middlewares/error_handler.py` 中的 `add_error_handlers(app)` 在应用启动时注册三类处理器：
  - `HTTPException`：若 `detail` 已是 `{error, message}` 结构则透传，否则包装为统一格式；
  - `RequestValidationError`：422 响应，`detail` 携带 Pydantic 验证错误列表；
  - `Exception`（兜底）：500 响应，`message="服务器内部错误"`，仅在 DEBUG 日志开启时暴露 `detail`。
- **请求级中间件兜底**：`ErrorHandlerMiddleware(BaseHTTPMiddleware)` 作为额外一层捕获未处理异常，记录完整堆栈并返回 500 统一响应，防止进程崩溃。
- **LLM 层参数错误自愈**：`src/llm/errors.py` 不依赖传统异常类型，而是对 LiteLLM 抛出的 `BaseException` 做文本分类（如 temperature/top_p 等不支持参数），通过 `call_litellm_with_param_recovery()` 自动重试一次并缓存恢复策略。

**2. 关键文件与位置**
- `api/v1/errors.py` — 统一错误体构造与 `api_error` 抛出器
- `api/middlewares/error_handler.py` — 全局异常处理器注册 + 中间件兜底
- `api/app.py` — 在应用初始化末尾调用 `add_error_handlers(app)` 完成注册
- `src/llm/errors.py` — LiteLLM 生成参数错误的分类与一次性恢复逻辑
- 各 `api/v1/endpoints/*.py` — 业务端点中通过 `raise api_error(...)` 或 `return api_error(...)` 返回错误

**3. 架构与约定**
- **错误码分层**：HTTP 状态码由 `api_error` 传入（400/404/409/422/500 等），业务语义通过 `error` 字段（如 `validation_error`、`not_found`、`duplicate_market_review`、`internal_error`）表达，`message` 面向用户可读，`detail` 供调试。
- **中间件顺序**：`ErrorHandlerMiddleware` 包裹整个请求链路，`add_error_handlers` 注册的 `@app.exception_handler` 优先于中间件捕获已抛出的 `HTTPException` 和 `RequestValidationError`，兜底的 `Exception` 处理器仅处理未被任何 handler 捕获的异常。
- **日志策略**：中间件与通用异常处理器均使用 `logger.error` 记录路径、方法、完整堆栈；LLM 参数恢复失败时使用 `logger.warning` 标注原因。
- **无 panic/recover**：Python 侧不使用 `try/except ... finally` 做流程控制，也未见 `sys.exit` 或 `os._exit` 式退出，异常一律上抛至中间件/处理器收敛。

**4. 约束与规范**
- 业务端点应通过 `api.v1.errors.api_error` 抛出错误，而非直接 `raise HTTPException(detail="...")`，以保证响应体字段一致。
- 验证失败走 Pydantic 校验，由 `RequestValidationError` 处理器统一返回 422，无需手动构造。
- LLM 调用必须经 `call_litellm_with_param_recovery` 包装，以便对不支持的参数自动重试一次。
- 测试用例（如 `tests/test_system_config_api.py`）在独立 app 实例上也显式调用 `add_error_handlers(app)`，确保测试环境行为与生产一致。