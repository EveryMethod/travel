# 用户个人工作台设计

日期：2026-07-15

## 目标

补齐旅行规划产品的最小闭环：登录用户可以生成行程，系统自动保存，用户之后能在独立工作台里回看和操作已保存行程。

本设计只做 **行程管理 MVP**，不做完整个人中心。

## 范围

### 做

- 登录用户生成行程后自动保存。
- 新增独立工作台页面 `/workspace`。
- 工作台展示“我的行程”列表。
- 新增行程详情页 `/trips/:id`。
- 支持查看详情、复制 Markdown、重新生成、删除。
- 所有行程数据按当前登录用户隔离。

### 不做

- 分享链接。
- PDF 导出。
- 标题 / 备注编辑。
- 局部编辑每天行程。
- 匿名行程。
- 复杂个人设置。
- `trip_days` / `trip_items` 结构化表。

## 用户流程

1. 用户登录后进入 `/home`。
2. 用户填写旅行规划表单并生成行程。
3. 生成成功后，后端自动保存行程。
4. `/home` 显示“已保存到工作台”，并提供“查看工作台”和“查看本次行程详情”。
5. 用户进入 `/workspace` 查看已保存行程列表。
6. 用户点击某条行程进入 `/trips/:id`。
7. 详情页支持复制 Markdown、重新生成和删除。
8. 删除成功后回到工作台列表。

## 页面设计

### `/home`：新建规划页

职责保持单一：新建旅行规划和展示本次生成结果。

生成成功后显示：

- 保存成功提示。
- 当前行程详情入口。
- 工作台入口。

不在 `/home` 混入完整历史列表，避免页面膨胀。

### `/workspace`：个人工作台

职责：展示当前用户的已保存行程。

列表字段：

- 目的地。
- 天数。
- 创建时间。
- 状态。

列表操作：

- 查看详情。
- 删除。
- 新建规划入口，跳转 `/home`。

### `/trips/:id`：行程详情页

展示完整行程结果和基础信息：

- 目的地。
- 天数。
- 创建时间。
- 行程内容。

详情操作：

- 复制 Markdown。
- 重新生成。
- 删除。

重新生成使用当前行程的 `request_json` 重新调用规划接口，成功后创建一条新行程，不覆盖旧行程。

## 数据设计

只新增一张表：

```text
trips
- id
- user_id
- trace_id nullable
- destination
- days
- status
- request_json
- plan_json
- created_at
- updated_at
```

字段说明：

- `user_id` 必填。MVP 只支持登录用户。
- `trace_id` 可空，用于排查生成问题。
- `destination`、`days` 是列表页直接展示字段。
- `status` 初始只需要 `completed`。如果实现时决定记录失败行程，可增加 `failed`。
- `request_json` 保存原始规划请求，用于重新生成。
- `plan_json` 保存完整生成结果。

暂不拆结构化行程表。JSON 已足够支持列表、详情、复制和重新生成；等需要搜索、统计或局部编辑时再拆表。

## API 设计

```text
POST   /api/trips/plan
GET    /api/trips
GET    /api/trips/{trip_id}
DELETE /api/trips/{trip_id}
```

### `POST /api/trips/plan`

替代或包住当前规划接口。

行为：

1. 校验当前登录用户。
2. 调用现有旅行规划流程。
3. 生成成功后保存 `trips` 记录。
4. 返回规划结果和 `trip_id`。

生成失败不保存行程。

### `GET /api/trips`

返回当前用户的行程列表。

返回字段：

```text
id
destination
days
status
created_at
```

按 `created_at desc` 排序。

### `GET /api/trips/{trip_id}`

返回当前用户自己的行程详情。

包含：

- 基础字段。
- `request_json`。
- `plan_json`。

如果行程不存在或不属于当前用户，返回 404。

### `DELETE /api/trips/{trip_id}`

删除当前用户自己的行程。

如果行程不存在或不属于当前用户，返回 404。

## 前端组件

最少新增 / 调整这些组件：

```text
TripPlannerForm.vue
TripList.vue
TripPlanResult.vue
WorkspaceView.vue
TripDetailView.vue
```

说明：

- `TripPlannerForm.vue` 负责表单。
- `TripPlanResult.vue` 负责展示生成结果，也用于详情页复用。
- `TripList.vue` 负责工作台列表。
- `WorkspaceView.vue` 组合工作台页面。
- `TripDetailView.vue` 展示单条行程详情。

不新增复杂 workspace layout 或导航框架。

## 鉴权

前端路由要求登录：

- `/home`
- `/workspace`
- `/trips/:id`

后端 trip API 全部依赖当前登录用户。

资源隔离规则：

- 用户只能看到自己的行程。
- 用户只能删除自己的行程。
- 不存在和无权限统一返回 404，避免暴露资源是否存在。

## 错误处理

- 生成失败：不保存行程，前端显示错误。
- 如果错误中有 `trace_id`，前端显示“问题编号：xxx”。
- 工作台列表加载失败：显示错误和重试按钮。
- 详情加载失败：显示错误，提供返回工作台入口。
- 删除失败：保留当前页面，显示错误。
- 复制失败：提示用户手动复制。

## 复制 Markdown

复制功能放在前端实现。

前端根据 `plan_json` 生成 Markdown 文本并写入剪贴板。

不新增后端导出接口；PDF、Word、分享链接都不在 MVP 范围内。

## 重新生成

详情页点击重新生成时：

1. 读取当前行程详情中的 `request_json`。
2. 调用 `POST /api/trips/plan`。
3. 成功后跳转到新行程的 `/trips/:id`。

旧行程不修改。

## 验证

后端检查：

```bash
python -m compileall backend/src
```

前端检查：

```bash
corepack pnpm --dir front build
```

手动验收：

1. 登录后从 `/home` 生成行程。
2. 看到“已保存到工作台”。
3. 进入 `/workspace` 看到行程卡片。
4. 打开 `/trips/:id` 能看到详情。
5. 复制 Markdown 成功。
6. 重新生成后产生新行程。
7. 删除后列表消失。
8. 退出登录后不能访问工作台和详情页。

## 后续再做

- 行程标题 / 备注。
- 分享链接。
- PDF 导出。
- 局部编辑每天行程。
- `trip_days` / `trip_items` 结构化存储。
- 工作台统计或筛选。
