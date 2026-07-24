# AI Travel Planner

**English** | [简体中文](README.zh-CN.md)

An AI-assisted travel planning application that turns structured preferences into a day-by-day itinerary and combines it with round-trip intercity transport suggestions.

## Features

- Generate structured itineraries from destination, dates, budget, travel style, pace, and traveler counts.
- Plan outbound and return transport by flight, China railway, or self-driving.
- Query maps, places, routes, weather, and reference ticket prices through supplier APIs.
- Save trips in a personal workspace and view complete trip details.
- Revise a saved itinerary with natural-language instructions while preserving the original version.
- Refresh transport results independently without replacing destination-day content.
- Stream planning progress to the frontend and retain trace IDs for diagnostics.
- Authenticate users with access and refresh tokens.

> Flight and railway fares are reference data. Final prices, availability, and booking conditions must be confirmed with the carrier or booking platform.

## Tech Stack

| Layer | Technologies |
| --- | --- |
| Frontend | Vue 3, TypeScript, Vite, Pinia, Vue Router, Tailwind CSS |
| Backend | Python 3.12, FastAPI, Pydantic, LangGraph, SQLAlchemy |
| Storage | MySQL, Redis |
| Travel data | AMap, Juhe flight and railway APIs, Amadeus fallback, Tavily fallback |
| Tooling | pnpm, uv, Alembic |

## Project Structure

```text
travel/
├── front/                     # Vue frontend
│   └── src/
│       ├── components/        # Shared UI components
│       ├── composables/       # Trip generation state and streaming
│       ├── services/          # API client and Markdown export
│       ├── types/             # Frontend domain types
│       └── views/             # Login, planner, workspace, and trip detail views
├── backend/
│   ├── alembic/               # Database migrations
│   └── src/app/
│       ├── api/               # FastAPI routes and authentication
│       ├── core/              # Configuration, database, Redis, and tracing
│       ├── graph/             # Trip, transport, and revision LangGraph workflows
│       ├── models/            # Pydantic and SQLAlchemy models
│       ├── services/          # LLM, supplier client, tracing, and persistence
│       ├── main.py            # Main API application
│       └── mcp_gateway.py     # Travel supplier gateway
└── docs/                      # Project documentation
```

## Prerequisites

- Python 3.12.6 or newer
- [uv](https://docs.astral.sh/uv/)
- Node.js 20 LTS or newer
- pnpm 11 through Corepack
- MySQL 8+
- Redis 7+

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/EveryMethod/travel.git
cd travel

python -m uv sync --project backend
corepack pnpm --dir front install
```

### 2. Configure the backend

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and provide the services used by your environment. Never commit this file.

| Variable group | Purpose |
| --- | --- |
| `MYSQL_*` | MySQL connection |
| `REDIS_URL` | Session and runtime Redis connection |
| `OPENAI_BASE_URL`, `OPENAI_API_KEY`, `LLM_NAME` | OpenAI-compatible language model |
| `AMAP_API_KEY` | Places, geocoding, routes, and weather |
| `JUHE_FLIGHT_API_KEY` | Live flight schedule and reference fares |
| `JUHE_TRAIN_API_KEY` | Mainland China railway schedules and fares |
| `AMADEUS_API_KEY`, `AMADEUS_API_SECRET` | Optional flight fallback |
| `TAVILY_API_KEY` | Optional search-based price fallback |

The application degrades to available fallback providers when optional supplier credentials are missing. Core planning still requires a working language model, database, and Redis instance.

### 3. Apply database migrations

```bash
cd backend
python -m uv run alembic upgrade head
cd ..
```

### 4. Start the services

Run each command in a separate terminal.

```bash
# Main API: http://127.0.0.1:8000
cd backend
python -m uv run uvicorn src.app.main:app --reload --port 8000
```

```bash
# Supplier gateway: http://127.0.0.1:8100
cd backend
python -m uv run uvicorn src.app.mcp_gateway:app --reload --port 8100
```

```bash
# Frontend: http://127.0.0.1:5173
corepack pnpm --dir front dev
```

FastAPI documentation is available at `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8100/docs`.

## Verification

```bash
python -m compileall backend/src
corepack pnpm --dir front build
```

## Security

- Keep API keys, database passwords, and OAuth credentials in `backend/.env` or a secret manager.
- Commit only `backend/.env.example`, with empty credential values.
- Rotate any credential that has been exposed in source code, logs, screenshots, or chat history.
- Restrict trace-query endpoints outside development environments.
