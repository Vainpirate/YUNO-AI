# Backend (Phase 2)

## Setup

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
```

## Run API

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI: `http://localhost:8000/docs`

## Database Migrations

```bash
alembic upgrade head
```

## Run Tests

```bash
pytest
```

## Implemented Endpoints

- `POST/GET/PUT/DELETE /api/agents`
- `PATCH /api/agents/{id}/tools`
- `PATCH /api/agents/{id}/channels`
- `POST /api/agents/{id}/execute`
- `POST/GET/PUT /api/workflows`
- `GET /api/workflows/templates`
- `POST /api/workflows/{id}/execute`
- `GET /api/workflows/{id}/status`
- `GET /api/messages/{workflow_id}`
- `GET /api/execution/{workflow_id}/logs`
- `WS /ws/logs/{workflow_id}`
- `WS /ws/agent-status/{agent_id}`
