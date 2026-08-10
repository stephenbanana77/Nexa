# Nexa Development Guide

This guide covers local setup, validation, and the engineering conventions used in Nexa.

## Requirements

- Python 3.12+
- Node.js 24+
- Docker Desktop, optional
- An OpenAI-compatible LLM endpoint, optional for deterministic tests

## Backend Setup

```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

The backend starts at `http://localhost:8000`.

Useful environment variables:

```env
DATABASE_URL=sqlite:///./nexa.db
SECRET_KEY=change-me
STORAGE_PATH=./storage
LLM_API_KEY=your-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
```

## Frontend Setup

```powershell
cd frontend
npm install
npm run dev
```

The frontend starts at `http://localhost:5173`.

## Docker

```powershell
docker compose up --build
```

## Validation

Run from the repository root:

```powershell
.\backend\venv\Scripts\python.exe -m pytest backend/tests -q
npm run lint --prefix frontend
npm run build --prefix frontend
```

Do not run two backend pytest processes in parallel. The current test fixture uses a shared SQLite `test.db`, so parallel pytest commands can collide.

## Offline Evaluation

```powershell
Push-Location backend
.\venv\Scripts\python.exe -m evaluation.runner --format markdown
Pop-Location
```

The default suite is `backend/evaluation/cases/superstore_core.json`.

## Database Migrations

Alembic migrations live in `backend/alembic/versions`.

```powershell
cd backend
alembic revision --autogenerate -m "describe change"
alembic upgrade head
```

The local app still calls `Base.metadata.create_all()` on startup for development convenience, but migrations should be kept for schema changes.

## Architecture Notes

- `backend/agents/graph.py` owns the LangGraph pipeline and graph-level SQL retry events.
- `backend/agents/controller.py` owns run tracking, system retry, and lineage aggregation.
- `backend/services/sql_policy.py` is the single source of truth for SQL safety decisions.
- `backend/services/run_tracker.py` writes Run and RunStep observability data.
- `backend/evaluation/runner.py` runs deterministic offline evaluation.
- `frontend/src/pages/RunHistoryPage.tsx` displays evidence chain and agent step details.

## Git Conventions

Suggested branch prefixes:

```text
feat/<topic>
fix/<topic>
docs/<topic>
```

Suggested commit format:

```text
type(scope): message
```

Examples:

```text
feat(agent): record SQL policy lineage
fix(api): validate run ownership before detail lookup
docs(readme): describe trustworthy analysis architecture
```

## Known Gaps

- Evaluation should be expanded from 12 golden SQL cases to 30-50 real Agent cases.
- Token usage is estimated rather than read from provider usage metadata.
- Notebook Python execution still needs sandboxing.
- Workflow engine is useful but still an MVP.
