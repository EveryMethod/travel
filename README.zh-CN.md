# AI 智能旅行规划器

[English](README.md) | **简体中文**

一个 AI 辅助旅行规划应用，可根据结构化旅行偏好生成逐日行程，并提供包含去程和返程的城际交通建议。

## 核心功能

- 根据目的地、日期、预算、旅行风格、节奏和旅客人数生成结构化行程。
- 规划航班、中国大陆铁路或自驾的去程与返程方案。
- 通过供应商 API 查询地点、路线、天气和参考票价。
- 将行程保存到个人工作台，并查看完整行程详情。
- 使用自然语言调整已保存行程，同时保留原始版本。
- 独立刷新交通结果，不覆盖目的地逐日安排。
- 向前端流式返回规划进度，并保留 Trace ID 便于诊断。
- 使用访问令牌和刷新令牌完成用户鉴权。

> 航班和铁路票价均为参考数据，最终价格、余票和预订条件请以承运方或订票平台为准。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Pinia、Vue Router、Tailwind CSS |
| 后端 | Python 3.12、FastAPI、Pydantic、LangGraph、SQLAlchemy |
| 存储 | MySQL、Redis |
| 旅行数据 | 高德地图、聚合数据航班与铁路 API、Amadeus 备用、Tavily 备用 |
| 工具链 | pnpm、uv、Alembic |

## 项目结构

```text
travel/
├── front/                     # Vue 前端
│   └── src/
│       ├── components/        # 通用界面组件
│       ├── composables/       # 行程生成与流式状态管理
│       ├── services/          # API 客户端和 Markdown 导出
│       ├── types/             # 前端领域类型
│       └── views/             # 登录、规划、工作台和行程详情页面
├── backend/
│   ├── alembic/               # 数据库迁移
│   └── src/app/
│       ├── api/               # FastAPI 路由和鉴权
│       ├── core/              # 配置、数据库、Redis 和调用追踪
│       ├── graph/             # 行程、交通和修改 LangGraph 工作流
│       ├── models/            # Pydantic 与 SQLAlchemy 模型
│       ├── services/          # 大模型、供应商客户端、追踪和持久化
│       ├── main.py            # 主 API 应用
│       └── mcp_gateway.py     # 旅行供应商网关
└── docs/                      # 项目文档
```

## 环境要求

- Python 3.12.6 或更高版本
- [uv](https://docs.astral.sh/uv/)
- Node.js 20 LTS 或更高版本
- 通过 Corepack 使用 pnpm 11
- MySQL 8+
- Redis 7+

## 快速开始

### 1. 克隆并安装依赖

```bash
git clone https://github.com/EveryMethod/travel.git
cd travel

python -m uv sync --project backend
corepack pnpm --dir front install
```

### 2. 配置后端

```bash
cp backend/.env.example backend/.env
```

编辑 `backend/.env`，填写当前环境使用的服务配置。不要提交该文件。

| 变量组 | 用途 |
| --- | --- |
| `MYSQL_*` | MySQL 数据库连接 |
| `REDIS_URL` | 会话与运行时 Redis 连接 |
| `OPENAI_BASE_URL`、`OPENAI_API_KEY`、`LLM_NAME` | OpenAI 兼容的大模型服务 |
| `AMAP_API_KEY` | 地点、地理编码、路线和天气 |
| `JUHE_FLIGHT_API_KEY` | 实时航班班次和参考票价 |
| `JUHE_TRAIN_API_KEY` | 中国大陆铁路班次和票价 |
| `AMADEUS_API_KEY`、`AMADEUS_API_SECRET` | 可选航班备用数据源 |
| `TAVILY_API_KEY` | 可选搜索估价备用数据源 |

缺少可选供应商凭证时，应用会尝试使用可用的备用数据源。核心规划仍需要可用的大模型、数据库和 Redis。

### 3. 执行数据库迁移

```bash
cd backend
python -m uv run alembic upgrade head
cd ..
```

### 4. 启动服务

请在不同终端分别运行以下命令。

```bash
# 主 API：http://127.0.0.1:8000
cd backend
python -m uv run uvicorn src.app.main:app --reload --port 8000
```

```bash
# 供应商网关：http://127.0.0.1:8100
cd backend
python -m uv run uvicorn src.app.mcp_gateway:app --reload --port 8100
```

```bash
# 前端：http://127.0.0.1:5173
corepack pnpm --dir front dev
```

FastAPI 文档地址为 `http://127.0.0.1:8000/docs` 和 `http://127.0.0.1:8100/docs`。

## 验证命令

```bash
python -m compileall backend/src
corepack pnpm --dir front build
```

## 安全说明

- 将 API Key、数据库密码和 OAuth 凭证保存在 `backend/.env` 或密钥管理服务中。
- 只提交凭证值为空的 `backend/.env.example`。
- 如果凭证曾出现在源码、日志、截图或聊天记录中，请立即轮换。
- 非开发环境应限制调用追踪查询接口。
