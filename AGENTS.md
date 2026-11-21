# AGENTS.md — NexusOps

Instructions for AI coding agents working in this repo. Keep this file short; details live in [docs/technical_blueprint.md](docs/technical_blueprint.md).

## Project
NexusOps is an AI-powered cloud operations and incident intelligence platform ("Understand incidents. Find root causes. Prevent failures.").
Architecture: **modular monolith FastAPI API + 2 async workers** (`telemetry-worker`, `ai-worker`), React frontend, PostgreSQL + pgvector, Redis, Kafka, OpenTelemetry/Prometheus/Grafana.
Exactly **one** AI agent (LangGraph) lives in `ai-worker`. Do not add more agents.

## Hard Constraints
- **No Kubernetes.** Docker + Docker Compose locally; EC2 + RDS + S3 + Lambda on AWS via Terraform.
- **Never commit secrets** (API keys, AWS credentials, `.env`). Only `.env.example` with placeholders.
- **No autonomous infrastructure execution.** Remediation requires explicit human approval and is recorded in `audit_logs`.
- **No fake AI.** The `MockRuleBasedProvider` must run the same LangGraph tool loop on real platform data.
- **Never present a hypothesis as a confirmed root cause** without tool-retrieved evidence.
- Keep the LLM provider configurable (`LLMProvider` interface); no provider-specific code outside it.
- Don't assume API keys or cloud credentials exist; use mocks. Clearly label simulated vs. real AWS integrations.
- Don't add technologies or abstractions without a concrete problem they solve.

## Layout
```
backend/app/{api,core,db,models,schemas,services,ai}  backend/workers  backend/tests
frontend/src/{api,components,pages,hooks,types}
sample-services/  infra/{observability,nginx,terraform}  docs/
```

## Commands (update as milestones add them)
- Start infra: `docker compose up -d`
- Backend tests: `cd backend && pytest` (add `RUN_INTEGRATION=1` with Docker infra up to include real Postgres/Redis tests; CI always does)
- Lint: `cd backend && ruff check .`
- Migrations: `cd backend && alembic upgrade head` (new migration: `alembic revision --autogenerate -m "..."`, then review it; `alembic check` must pass)
- Frontend (from Milestone 3): `cd frontend && npm run build && npm test`

## Conventions
- Python 3.12, FastAPI, Pydantic v2, async SQLAlchemy 2.0, Alembic for all schema changes.
- Routers stay thin; business logic goes in `services/`.
- Config only via environment variables (pydantic-settings). No hardcoded data.
- Structured JSON logging; proper error handling; type hints everywhere.
- TypeScript strict mode on the frontend; dark-theme Tailwind UI.
- Small, meaningful commits (e.g. `feat: add service registry API`).

## Workflow
0. **Git: never commit directly to `main`.** Every change happens on a branch (`feat/...`, `fix/...`, `chore/...`). `main` only receives merges, and only after CI (`.github/workflows/ci.yml`) is green. Never push or merge unless the owner asks.
1. Work in small, verifiable milestones; **run tests after every milestone** and fix failures before moving on.
2. For each major piece, explain: what we're building, why, how it works, which engineering concepts it shows, how components communicate, and the trade-offs. The owner is learning.
3. Update docs (this file, README, blueprint) when decisions or commands change.
4. Every new feature ships with tests, and CI must run them. When a new part is added (frontend, workers), add its job to the CI workflow.
5. Current status: **Phase 1, Milestone 2 done** (schema, JWT auth, RBAC, service registry, audit logs); next is Milestone 3 (React frontend).
