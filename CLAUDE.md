# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Environment and setup

- Python dependencies are managed from the repo root with Poetry: `poetry install`
- Frontend dependencies live in `app/frontend`: `cd app/frontend && npm install`
- Copy env vars on first setup: `cp .env.example .env`
- The app expects at least one LLM API key (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GROQ_API_KEY`, etc.) plus `FINANCIAL_DATASETS_API_KEY`
- For the web app, there is a convenience launcher: `cd app && ./run.sh`

## Common commands

### CLI hedge fund
- `poetry run python src/main.py --tickers AAPL,MSFT,NVDA`
- `poetry run python src/main.py --tickers AAPL --show-reasoning`
- `poetry run python src/main.py --tickers AAPL --analysts-all`
- `poetry run python src/main.py --tickers AAPL --ollama`

### CLI backtester
- `poetry run python src/backtester.py --tickers AAPL,MSFT,NVDA`
- `poetry run python src/backtester.py --tickers AAPL --start-date 2024-01-01 --end-date 2024-03-01`

### Web app
- Full stack helper: `cd app && ./run.sh`
- Backend only (run from repo root): `poetry run uvicorn app.backend.main:app --reload --host 127.0.0.1 --port 8000`
- Frontend only: `cd app/frontend && npm run dev`
- Frontend build: `cd app/frontend && npm run build`
- Frontend lint: `cd app/frontend && npm run lint`

### Tests
- All Python tests: `poetry run pytest`
- Single file: `poetry run pytest tests/test_cache.py`
- Single test: `poetry run pytest tests/backtesting/test_portfolio.py::test_apply_long_buy_basic`

### Formatting / linting
- `poetry run black .`
- `poetry run isort .`
- `poetry run flake8`

## Architecture overview

### Core trading engine (`src/`)
- `src/main.py` is the CLI entrypoint and builds the fixed LangGraph workflow used by the CLI: selected analysts -> `risk_management_agent` -> `portfolio_manager`.
- Shared graph state lives in `src/graph/state.py` as `messages`, `data`, and `metadata`. Agents communicate by mutating `data["analyst_signals"]` and by writing the final JSON decision into the last message.
- `src/utils/analysts.py` is the single source of truth for available analysts, display names, ordering, and agent functions. Both the CLI selector and the web backend depend on it.
- `src/agents/` contains the analyst, risk, and portfolio manager nodes.
- `src/tools/api.py` is the market/fundamental/news data access layer. It calls the Financial Datasets API and uses a process-local in-memory cache from `src/data/cache.py`. Cache state is not persistent across runs.

### Backtesting
- The CLI backtester entrypoint is `src/backtester.py`.
- Most CLI backtesting logic is in `src/backtesting/engine.py` plus portfolio/execution/metrics helpers under `src/backtesting/`.
- The web backend has a separate async backtesting path in `app/backend/services/backtest_service.py`; it reuses the compiled graph and streams per-day updates over SSE. Do not assume CLI and web backtesting share the same service implementation.

### Web backend (`app/backend`)
- `app/backend/main.py` boots FastAPI, creates DB tables on startup, enables CORS for the local Vite dev server, and checks Ollama availability.
- `app/backend/routes/hedge_fund.py` exposes `/hedge-fund/run`, `/hedge-fund/backtest`, and `/hedge-fund/agents`. The run and backtest endpoints stream `start`, `progress`, `complete`, and `error` events.
- `app/backend/services/graph.py` is the key bridge between the React Flow UI and LangGraph. The frontend sends arbitrary graph node IDs; the backend strips the unique suffix to map each node back to a base analyst key from `ANALYST_CONFIG`.
- Portfolio manager nodes are special in the web graph: the backend automatically creates a paired risk manager node for each portfolio manager, even if the frontend graph connects analysts directly to portfolio managers.
- Flow/run persistence and API key storage live in SQLite via SQLAlchemy models in `app/backend/database/models.py`; the DB file is configured in `app/backend/database/connection.py` as `app/backend/hedge_fund.db`.

### Web frontend (`app/frontend`)
- The frontend is React + Vite + TypeScript with `@xyflow/react` for the graph editor.
- `app/frontend/src/contexts/node-context.tsx` stores per-flow runtime node state, messages, output data, and per-node model selections. The state is flow-aware via composite keys of `flowId:nodeId`.
- `app/frontend/src/services/api.ts` consumes backend streaming responses with `fetch(...).body.getReader()` rather than `EventSource`, because the backend endpoints are POST-based SSE streams.
- The frontend and backend share the agent catalog indirectly through the backend `/hedge-fund/agents` endpoint and `src/utils/analysts.py`.

## Testing layout

- `tests/test_cache.py` covers the in-memory cache behavior.
- `tests/test_api_rate_limiting.py` covers API retry/backoff logic.
- `tests/backtesting/` covers the refactored backtesting components such as portfolio math, execution, controller logic, and metrics.

## Repository quirks

- The CLI flag is `--tickers` (plural). Some README examples still show `--ticker`.
- Use the root Poetry environment. The repo has one top-level `pyproject.toml`; backend code imports both `app.*` and `src.*`, so backend commands are safest when run from the repo root.
- `app/run.sh` is the easiest full-stack local runner for humans, but for debugging it is often clearer to start `uvicorn` and the frontend dev server separately.
