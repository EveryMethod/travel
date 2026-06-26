# Repository Guidelines

## Project Structure & Module Organization

This repository contains an AI travel planner with separate frontend and backend projects.

- `front/` is a Vite + Vue 3 + TypeScript app. Source lives in `front/src/`, with routes in `router/`, state in `stores/`, shared API/client logic in `services/`, types in `types/`, views in `views/`, and styles/assets in `assets/`.
- `backend/` is a Python 3.12+ FastAPI project managed by `uv`. Application code lives in `backend/src/app/`, with API routing in `api/`, settings in `core/`, LangGraph planning code in `graph/`, and Pydantic models in `models/`.
- `docs/` stores project documentation. Generated outputs such as `front/dist/`, `front/node_modules/`, `backend/.venv/`, caches, and local `.env` files should stay untracked.

## Build, Test, and Development Commands

Frontend commands:

- `corepack pnpm --dir front install` installs frontend dependencies.
- `corepack pnpm --dir front dev` starts the Vite dev server and proxies `/api` to `localhost:8000`.
- `corepack pnpm --dir front build` runs TypeScript checks and creates `front/dist/`.
- `corepack pnpm --dir front preview` serves the production build locally.

Backend commands:

- `python -m uv sync --project backend` installs Python dependencies.
- From `backend/`, `python -m uv run uvicorn src.app.main:app --reload` starts the API server.
- `python -m compileall backend/src` performs a quick syntax check.

## Coding Style & Naming Conventions

Use TypeScript for frontend code and Python for backend code. Prefer small, typed modules that match the existing directory boundaries. Vue single-file components should use PascalCase names, such as `HomeView.vue`; composables should use `useThing` naming. Python modules should use `snake_case`, and Pydantic models should use PascalCase classes. Keep configuration in `.env` files based on `backend/.env.example`; do not commit secrets.

## Testing Guidelines

No formal test runner is configured yet. When adding behavior, include tests alongside the affected project and add the matching script to `front/package.json` or `backend/pyproject.toml`. Use clear names such as `tripPlanner.test.ts` for frontend tests or `test_trip_planner.py` for backend tests. Until test runners exist, run `corepack pnpm --dir front build` and `python -m compileall backend/src` before opening a PR.

## Commit & Pull Request Guidelines

Recent history uses concise Conventional Commit-style messages, for example `feat: add Chinese trip planning flow` and `docs: add Claude Code guidance`. Keep commits focused and imperative. Pull requests should describe the change, list verification commands, link related issues when available, and include screenshots for UI changes.
