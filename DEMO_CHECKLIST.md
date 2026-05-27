# DEMO_CHECKLIST — YUNO AI Phase 6 Sign-off

Use this checklist before any live demo or submission.

---

## System Startup

- [ ] `docker-compose up --build` completes without errors
- [ ] All 4 services healthy (postgres, redis, backend, frontend)
- [ ] `GET /api/health` returns `{"status": "ok"}`
- [ ] `GET /api/health/db` returns `{"status": "ok", "db": "connected"}`
- [ ] `GET /api/health/redis` returns `{"status": "ok", "redis": "connected"}` *(or "degraded" — acceptable without Redis in dev)*
- [ ] Frontend accessible at `http://localhost:3000`
- [ ] Swagger UI accessible at `http://localhost:8000/docs`

---

## Functionality

### Agent CRUD
- [ ] Create agent via UI — agent appears in dashboard
- [ ] Create agent via API (`POST /api/agents`) — 200 response, `id` returned
- [ ] Update agent (`PUT /api/agents/{id}`) — changes persist
- [ ] Patch tools (`PATCH /api/agents/{id}/tools`) — tool list updates
- [ ] Delete agent (`DELETE /api/agents/{id}`) — removed from list
- [ ] Duplicate name rejected (`409 Conflict`)

### Workflow Builder
- [ ] Workflow templates load (`GET /api/workflows/templates` → 3 templates)
- [ ] Create workflow via UI — canvas renders nodes and edges
- [ ] Save workflow — persisted in DB
- [ ] Update workflow (add/remove node) — graph JSON updates correctly

### Workflow Execution
- [ ] Execute 2-agent workflow — status returns `"completed"`
- [ ] Execute with custom input `{"input": "..."}` — first agent receives it
- [ ] Agent-to-agent message passing visible in `GET /api/messages/{wf_id}`
- [ ] Execution logs present in `GET /api/execution/{wf_id}/logs`
- [ ] Token counts are non-zero in execution logs
- [ ] Workflow status endpoint returns `"completed"` after execution

### Tools
- [ ] `calculator` tool returns numeric result for math input
- [ ] `datetime_now` tool returns current UTC time string
- [ ] `random_fact` tool returns a fact string
- [ ] `word_count` tool returns correct word count

### Real-Time Monitoring
- [ ] WebSocket connection to `/ws/logs/{workflow_id}` established
- [ ] `step_completed` events stream during execution
- [ ] `workflow_completed` event fires at end
- [ ] Frontend monitor page shows live log updates

### Telegram Integration *(skip if no token)*
- [ ] Bot starts polling without errors in backend logs
- [ ] `/start` command received and processed
- [ ] Free-text message routed to correct agent
- [ ] Response sent back to Telegram user
- [ ] Inbound/outbound stored in `message_history` table
- [ ] Telegram event broadcast to WebSocket subscribers

---

## Code Quality

- [ ] All 3 unit tests passing: `pytest tests/ -v` → `3 passed`
- [ ] No hardcoded API keys / secrets in source files
- [ ] No unhandled exceptions in `/api/health` or core CRUD routes
- [ ] `requirements.txt` lists all dependencies (no missing imports)
- [ ] `.env.example` covers all required environment variables
- [ ] No `TODO`s left in critical path files (executor, routes, models)

---

## Documentation

- [ ] `README.md` — quick start works as documented (docker-compose up)
- [ ] `ARCHITECTURE.md` — ASCII diagram accurate to implemented system
- [ ] `EXTENDING.md` — tool, channel, and template extension guides present
- [ ] `DEMO.md` — demo script written with seed data commands
- [ ] `openapi_spec.yaml` — reflects current endpoint set
- [ ] `backend/README.md` — setup instructions accurate
- [ ] `DECISION_LOG.md` — major tech choices documented with rationale

---

## UI / UX

- [ ] Dashboard loads without console errors
- [ ] Agent Manager: list, create, edit, delete all functional
- [ ] Workflow Studio: canvas renders, nodes draggable
- [ ] Monitoring page: connects to WebSocket, shows logs
- [ ] Loading states shown during API calls (spinner / skeleton)
- [ ] Error toast appears on API failure
- [ ] Responsive on 1920×1080 desktop viewport

---

## Demo Readiness

- [ ] Seed agents created (Researcher, Summarizer, Validator)
- [ ] Seed workflow created (`Research → Summarize`)
- [ ] Demo script rehearsed end-to-end (DEMO.md)
- [ ] Backup scenarios reviewed (offline fallbacks)
- [ ] Q&A answers prepared
- [ ] Screen recording setup (1920×1080 @ 60 fps, audio clear)
- [ ] Git history clean — no debug commits, no secrets in history

---

## Phase 6 Sign-off

| Criterion | Weight | Status |
|-----------|--------|--------|
| Working end-to-end demo | 40% | ☐ |
| Architecture + code quality | 30% | ☐ |
| UI/UX and configurability | 20% | ☐ |
| Documentation | 10% | ☐ |

**Overall: READY FOR DELIVERY** when all boxes above are checked.
