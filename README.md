# NexusOps

AI-powered cloud operations and incident intelligence platform.
*Understand incidents. Find root causes. Prevent failures.*

Design: [docs/technical_blueprint.md](docs/technical_blueprint.md) · Agent rules: [AGENTS.md](AGENTS.md)

## Quick start (Milestone 1)

```powershell
copy .env.example .env          # then edit passwords
docker compose up -d            # PostgreSQL+pgvector, Redis
cd backend
python -m venv .venv; .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload   # http://localhost:8000/docs
pytest; ruff check .
```

Endpoints: `GET /health` (liveness), `GET /ready` (checks Postgres + Redis).
