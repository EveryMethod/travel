# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is a two-part AI travel planning project scaffold:

- `front/` contains the Vue frontend application.
- `backend/` contains the FastAPI backend application.

The current codebase is intentionally a pure skeleton. Avoid adding business logic unless explicitly requested.

## Frontend

The frontend is a Vite + Vue 3 + TypeScript application using Pinia, Vue Router, Tailwind CSS, and shadcn-vue configuration.

Common commands from `front/`:

```bash
corepack pnpm install
corepack pnpm dev
corepack pnpm build
corepack pnpm preview
```

Equivalent commands from the repository root:

```bash
corepack pnpm --dir front install
corepack pnpm --dir front dev
corepack pnpm --dir front build
corepack pnpm --dir front preview
```

There is no frontend test script configured yet.

Key frontend structure:

- `front/src/main.ts` creates the Vue app, installs Pinia and Vue Router, and mounts `App.vue`.
- `front/src/App.vue` renders the active route via `RouterView`.
- `front/src/router/index.ts` defines an empty Vue Router route table.
- `front/src/stores/`, `front/src/composables/`, `front/src/services/`, and `front/src/types/` are placeholder module areas.
- `front/vite.config.ts` defines the `@/` alias to `front/src` and proxies `/api` to `http://localhost:8000`.
- `front/components.json`, `front/tailwind.config.ts`, and `front/src/assets/main.css` provide the shadcn-vue and Tailwind CSS baseline.

## Backend

The backend is a Python 3.12.6+ uv project with FastAPI, LangChain 1.2.x, LangGraph, Pydantic v2, Pydantic Settings, and Supabase dependencies.

Common commands from `backend/`:

```bash
python -m uv sync
python -m uv run uvicorn src.app.main:app --reload
python -m compileall src
```

Equivalent commands from the repository root:

```bash
python -m uv sync --project backend
cd backend && python -m uv run uvicorn src.app.main:app --reload
python -m compileall backend/src
```

There is no backend test runner configured yet.

Key backend structure:

- `backend/src/app/main.py` creates the FastAPI app, installs CORS middleware, and registers the placeholder API router at `/api`.
- `backend/src/app/core/config.py` defines environment-backed settings using `pydantic-settings` and reads from `.env`.
- `backend/src/app/api/router.py` defines an empty `APIRouter` for future API modules.
- `backend/src/app/graph/` is reserved for future LangGraph definitions.
- `backend/src/app/models/` is reserved for future Pydantic request/response models.
- `backend/.env.example` documents the current environment variable names.

## Development Notes

- Run frontend commands from `front/`; run backend commands from `backend/` unless using the root equivalents above.
- The frontend dev server proxies `/api` to backend port `8000`.
- `front/node_modules/`, `front/dist/`, `backend/.venv/`, Python cache files, and local `.env` files are ignored.
