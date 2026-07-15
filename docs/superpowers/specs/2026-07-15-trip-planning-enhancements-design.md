# 旅游规划增强设计

## 目标

在不重构现有规划链路的前提下，完善三件事：

1. 行程可执行性校验。
2. 预算结构化为交通、住宿、餐饮、门票四项。
3. 用户偏好结构化为旅行节奏、同行人、必去地点、避开地点。

后端所有新增工作必须嵌入现有 LangGraph 图节点中，不在 API 层或独立旁路流程里处理。

## 非目标

- 不接酒店、票务、交通排班等新的实时供应商 API。
- 不做精确路线优化或地图级时间矩阵。
- 不重构主页布局。
- 不新增通用 service 抽象，除非实现时发现已有函数必须复用。

## 数据模型

### 请求字段

在 `TripPlanRequest` 上新增：

- `budget_breakdown`
  - `transport`: string
  - `hotel`: string
  - `food`: string
  - `tickets`: string
- `pace`: `relaxed | balanced | packed`
- `companions`: `solo | couple | friends | family | seniors`
- `must_see`: string
- `avoid`: string

保留旧的 `budget: string`，作为兼容字段。前端提交时可以继续带总预算，也会提交分项预算。后端 prompt 优先使用分项预算。

### 响应字段

暂不改 `TripPlanResponse` schema。预算和可执行性风险先追加到现有 `tips`，避免前端结果组件跟着大改。

## 前端设计

只改 `HomeView.vue` 和 `front/src/types/index.ts`：

- 预算区域从单个预算输入改为四个小输入：交通、住宿、餐饮、门票。
- 偏好区域新增：
  - 旅行节奏：慢游 / 适中 / 紧凑。
  - 同行人：独自 / 情侣 / 朋友 / 家庭 / 老人。
  - 必去地点。
  - 避开地点。
- 原 `notes` 保留，继续承接自由描述。
- 表单布局保持现有结构，只在 planner 表单内增加字段。

## 后端 LangGraph 设计

现有图：

```text
normalize_request
-> collect_map_context
-> collect_price_context
-> draft_plan
-> validate_plan
```

调整为：

```text
normalize_request
-> collect_map_context
-> collect_price_context
-> check_constraints
-> draft_plan
-> validate_plan
-> review_plan
```

### normalize_request

继续 trim 字符串，并清洗新增字段：

- 分项预算字段 trim。
- `must_see`、`avoid` trim。
- 枚举字段使用 Pydantic 保证合法。

### check_constraints

新增 LangGraph 节点，产出 `constraints`：

- 分项预算原文。
- 可解析出的数字预算。
- 总预算估算。
- 节奏规则：
  - `relaxed`: 每天 2-3 个活动，减少跨区。
  - `balanced`: 每天 3 个左右活动。
  - `packed`: 每天 3-4 个活动，但仍避免明显冲突。
- 同行人规则：
  - `family` / `seniors`: 降低步行强度，增加休息提示。
  - `solo`: 增加安全和夜间交通提醒。
  - `couple`: 可保留慢节奏体验。
  - `friends`: 可接受更灵活安排。
- 必去和避开地点作为硬约束文本传给 LLM。

### draft_plan

继续使用 `generate_json()`，但 user payload 增加 `constraints`。system prompt 增加要求：

- 优先满足必去地点。
- 不安排避开地点。
- 按节奏控制每天活动数量。
- 预算建议必须参考分项预算；不确定价格写区间或“需查询官方渠道”。

### validate_plan

继续负责 JSON shape 修复和天数校验。职责不扩大。

### review_plan

新增 LangGraph 节点，对已通过 schema 的计划做轻量本地检查，把发现的问题追加到 `plan.tips`：

- 每天活动数量是否符合节奏上限。
- 同一天是否出现重复时间。
- 必去地点是否没有出现在计划中。
- 避开地点是否出现在计划中。
- 如果能从 `estimated_cost` 中解析数字，粗略汇总后和分项/总预算比较；明显超出时追加预算提醒。

检查只追加提醒，不阻断返回。真正阻断仍只限 schema 无法修复或天数不匹配。

## 数据流

1. 用户在主页填写目的地、日期、旅行风格、分项预算和偏好。
2. 前端调用 `/api/trips/plan/stream`。
3. `stream_trip_with_graph()` 按节点流式输出状态。
4. LangGraph 收集上下文、整理约束、生成计划、校验计划、追加风险提醒。
5. API 保存最终计划并返回。

## 错误处理

- 分项预算为空：允许，视为未提供该分项。
- 分项预算不能解析为数字：保留原文给 LLM，不做预算超额判断。
- 必去/避开为空：跳过对应检查。
- 可执行性检查发现问题：追加到 `tips`，不返回 500。
- LLM 超时和 MCP 查询失败沿用现有处理方式。

## 测试与验证

最小验证：

1. `python3 -m compileall backend/src`。
2. `npm run build` from `front/`。
3. 用浏览器打开主页，确认新增字段可填写，生成请求 payload 包含新增字段。
4. 后端用一个手工 payload 调 `/api/trips/plan/stream`，确认流状态包含新增节点对应文案，返回计划的 `tips` 可能包含预算/可执行性提醒。

## 实施范围

预计修改文件：

- `backend/src/app/models/trip.py`
- `backend/src/app/graph/trip_planner.py`
- `front/src/types/index.ts`
- `front/src/views/HomeView.vue`

不新增依赖。
