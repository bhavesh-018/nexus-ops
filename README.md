# NexusOps

AI-powered cloud operations and incident intelligence platform.
*Understand incidents. Find root causes. Prevent failures.*

Design: [docs/technical_blueprint.md](docs/technical_blueprint.md) · Agent rules: [AGENTS.md](AGENTS.md)

## Quick start (Phase 1)

### 1. Infrastructure & Backend
```powershell
copy .env.example .env          # set passwords + a 32+ char JWT_SECRET
docker compose up -d            # PostgreSQL+pgvector, Redis
cd backend
python -m venv .venv; .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
uvicorn app.main:app --reload   # http://localhost:8000/docs
```

### 2. Frontend
```powershell
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

### Tests & Linting
```powershell
# Backend (add $env:RUN_INTEGRATION="1" with Docker up for real DB/Redis tests)
cd backend; ruff check .; pytest -q

# Frontend
cd frontend; npm run build; npm test
```
