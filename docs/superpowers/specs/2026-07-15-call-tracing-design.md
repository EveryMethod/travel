# 智能体 / MCP / 工具调用日志追踪组件设计

日期：2026-07-15
状态：已确认设计，待实现

## 背景

当前后端的旅行规划链路已经有清晰的外部调用边界：

- `src.app.services.llm_service.generate_json()` 调用 OpenAI-compatible LLM，承担智能体草案生成与修复。
- `src.app.services.mcp_client.call_tool()` 调用本地 MCP gateway。
- `src.app.mcp_gateway.call_tool()` 执行 AMap / Tavily 等工具请求。
- `src.app.graph.trip_planner` 通过 LangGraph 串联以上调用。

目标是在这些边界记录每一次智能体、MCP、工具调用的留痕，支持排障、审计和后续链路复盘。当前阶段不引入 OpenTelemetry、Collector、可视化 UI 或完整可观测平台。

## 目标

1. 每次 LLM / MCP / 工具调用都生成一条可查询的 span 记录。
2. 同一次 `/api/trips/plan` 或 `/api/trips/plan/stream` 请求下的所有 span 使用同一个 `trace_id`。
3. 调用记录同时写入数据库和结构化日志。
4. 默认只记录元数据和摘要，不保存完整 prompt、完整请求结果或敏感值。
5. 追踪系统自身失败时不影响旅行规划主流程。

## 非目标

- 不接入 OpenTelemetry。
- 不新增 trace 可视化后台页面。
- 不保存完整 prompt / response。
- 不做异步批量写入队列。
- 不实现复杂权限模型。
- 不新增后台清理 worker；先保留简单保留天数配置，后续有数据量压力再加清理机制。

## 方案选择

采用边界包装器方案：在真实外部调用边界使用统一 `trace_call()` 包裹业务函数。

```text
Trip API
  -> LangGraph nodes
    -> trace_call("agent.llm", generate_json)
    -> trace_call("mcp.client", call_tool)
      -> MCP Gateway
        -> trace_call("tool.execute", amap/tavily tool)
```

该方案改动少，覆盖现有关键调用路径，且不会提前引入事件总线或观测平台。

## 组件设计

### `app/core/tracing.py`

负责追踪上下文、摘要生成和边界包装。

建议提供最少入口：

```python
trace_call(kind, name, input_data, metadata, func)
current_trace_id()
```

实现要点：

- 使用 `contextvars` 保存当前 `trace_id` 和当前 `span_id`。
- 如果请求入口没有 trace，则生成 UUID。
- 每次 `trace_call()` 生成新的 `span_id`，并把当前 span 作为 `parent_span_id`。
- 记录 `started_at`、`ended_at`、`duration_ms`。
- 成功时记录 `status=ok` 与 `output_summary`。
- 异常时记录 `status=error`、`error_type`、`error_message`，然后原样抛出异常。
- finally 中调用 trace store 写数据库，并写结构化日志。

### `app/services/trace_store.py`

负责持久化追踪记录。

要求：

- DB 写入失败只记录 `trace_store_error` 日志，不影响主流程。
- 接收已经脱敏和截断后的数据，不在 store 层保存原始输入输出。
- 提供按 `trace_id` 查询 spans 的函数，供只读 API 使用。

### `CallTrace` 数据模型

可新增 `app/models/trace.py`，或按现有模型组织方式放入 `app/models/db.py`。实现时优先匹配项目现有 SQLAlchemy 模型模式。

字段：

| 字段 | 说明 |
|---|---|
| `id` | 自增主键 |
| `trace_id` | 一次用户请求的链路 ID |
| `span_id` | 当前调用 ID |
| `parent_span_id` | 上级调用 ID，可空 |
| `kind` | `agent.llm` / `mcp.client` / `tool.execute` |
| `name` | 模型名、MCP 工具名或网关工具名 |
| `status` | `ok` / `error` |
| `started_at` | 调用开始时间 |
| `ended_at` | 调用结束时间 |
| `duration_ms` | 调用耗时 |
| `input_summary` | 输入摘要 JSON |
| `output_summary` | 输出摘要 JSON |
| `error_type` | 异常类名，可空 |
| `error_message` | 异常信息，最多 500 字符 |
| `metadata` | 补充 JSON，如 HTTP 状态、节点名、模型配置摘要 |
| `created_at` | 入库时间 |

索引：

- `trace_id`
- `(kind, started_at)`

## 接入点

### API 请求入口

在 `/api/trips/plan` 和 `/api/trips/plan/stream` 创建或读取 `trace_id`：

- 未来如果前端传 `X-Trace-Id`，可复用该值。
- 当前先由后端生成 UUID。
- 响应头返回 `X-Trace-Id`，便于前端报错时定位。

### LLM 调用

`llm_service.generate_json()` 使用：

- `kind="agent.llm"`
- `name=settings.llm_name`
- `input_summary` 记录消息数量、角色列表、总字符数、是否要求 JSON。
- `output_summary` 记录顶层 key、字符串长度、列表长度等结构摘要。

不保存完整 prompt 和完整模型返回。

### MCP client 调用

`mcp_client.call_tool()` 使用：

- `kind="mcp.client"`
- `name=tool_name`
- `input_summary` 记录参数 key、短字符串参数摘要，例如 city、keywords、query，最长 80 字符。
- `output_summary` 记录返回顶层 key、列表长度和字段数量。

### MCP gateway 工具执行

`mcp_gateway.call_tool()` 内部包裹实际工具函数：

- `kind="tool.execute"`
- `name=tool_name`
- `metadata` 可记录 gateway 层工具来源，如 `amap`、`tavily`。
- HTTP 错误会形成 `error` span，并继续按现有 FastAPI 错误逻辑返回。

## 数据流

```text
请求进入 /api/trips/plan
  -> 创建 trace_id
  -> LangGraph 执行节点
  -> LLM / MCP / tool 边界调用 trace_call
  -> 每个 trace_call 写 DB + JSON log
  -> 响应返回 X-Trace-Id
```

结构化日志格式：

```json
{
  "event": "call_trace",
  "trace_id": "...",
  "span_id": "...",
  "parent_span_id": "...",
  "kind": "mcp.client",
  "name": "amap_weather",
  "status": "ok",
  "duration_ms": 183
}
```

## 查询接口

先提供一个只读接口：

- `GET /api/traces/{trace_id}`：返回该 trace 下 spans，按 `started_at` 升序排序。

权限策略：

- 开发环境可直接开放。
- 非开发环境默认禁用，或要求管理员 token。实现时以最少配置为准，避免在权限体系未稳定时暴露审计数据。

## 摘要与脱敏策略

默认只保存摘要。

### 输入摘要

- LLM：消息数量、角色列表、总字符数、JSON 输出标记。
- MCP / tool：工具名、参数 key、短字符串参数，字符串最长 80 字符。
- 嵌套对象只记录结构，不展开长内容。

### 输出摘要

- 顶层 key。
- 列表长度。
- 字符串长度或前缀摘要，最长 120 字符。
- 不保存完整正文、完整搜索结果或完整模型输出。

### 强制脱敏字段

字段名包含以下片段时，值替换为 `***REDACTED***`：

```text
key, token, secret, password, authorization, api_key, access_token, refresh_token
```

字段匹配大小写不敏感。

## 错误处理

- 业务函数异常：trace span 记录为 `error`，然后原异常继续抛出。
- DB 写入失败：记录 `trace_store_error` 日志，不影响主流程。
- 摘要生成失败：降级为 `{"summary_error": "..."}`，不影响业务调用。
- 日志写入失败：不额外处理，交给 Python logging。

## 配置

新增配置建议：

- `trace_enabled: bool = True`
- `trace_query_enabled: bool = app_env == "development"`
- `trace_retention_days: int = 30`
- `trace_summary_max_chars: int = 120`

保留天数先只作为配置记录和后续清理脚本依据，不在首版实现常驻清理进程。

## 测试策略

当前项目无正式测试 runner，后端已有 `demo()` 自检风格，先保持一致。

### `tracing.demo()`

覆盖：

1. 成功调用写出 `ok` span。
2. 异常调用写出 `error` span，且原异常继续抛出。
3. 敏感字段被脱敏。

### `graph/test_trip_planner.py`

在现有 monkeypatch 风格基础上扩展：

- 替换 LLM 和 MCP 调用后跑一次规划。
- 断言生成了同一个 `trace_id` 下的 LLM / MCP span。
- 不依赖真实 OpenAI、AMap、Tavily 或 MCP gateway。

### 语法检查

实现后运行：

```bash
python -m compileall backend/src
```

## 首批落地范围

预计只修改后端：

- `backend/src/app/core/config.py`
- `backend/src/app/core/tracing.py`
- `backend/src/app/services/trace_store.py`
- `backend/src/app/models/db.py` 或 `backend/src/app/models/trace.py`
- `backend/src/app/api/router.py`
- `backend/src/app/services/llm_service.py`
- `backend/src/app/services/mcp_client.py`
- `backend/src/app/mcp_gateway.py`
- `backend/src/app/graph/test_trip_planner.py`

## 后续可扩展点

等真实需要出现后再加：

- OpenTelemetry 导出。
- trace 可视化 UI。
- 后台定时清理旧 trace。
- 异步批量写入。
- 更细的租户 / 用户级查询权限。
- 完整 prompt / response 的受控采样存储。
