# YUNO AI — Demo Script

> **Duration:** ~6 minutes  
> **Format:** Screen recording + voiceover  
> **Resolution:** 1920 × 1080, 60 fps  
> **Prerequisites:** System running via `docker-compose up --build`

---

## Pre-Demo Setup Checklist

Before hitting record:

- [ ] `docker-compose up --build` is healthy (all 4 services green)
- [ ] Browser open at `http://localhost:3000`
- [ ] API docs open in second tab: `http://localhost:8000/docs`
- [ ] Telegram app open on phone / in browser (if demonstrating Telegram)
- [ ] 3 seed agents already created (see [Seed Data](#seed-data) below)
- [ ] 1 seed workflow already created (Research → Summarize)
- [ ] `backend/.env` has `GEMINI_API_KEY` set for real LLM responses

---

## Seed Data (run before recording)

```bash
# Create agents
curl -s -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Researcher",
    "role": "Web Researcher",
    "system_prompt": "You are an expert researcher. Find and synthesize information clearly.",
    "model": "gemini-2.0-flash",
    "tools": ["calculator", "datetime_now"],
    "channels": ["telegram"],
    "memory_config": {},
    "guardrails": {}
  }' | python -m json.tool

curl -s -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Summarizer",
    "role": "Content Summarizer",
    "system_prompt": "You condense information into clear, concise bullet-point summaries.",
    "model": "gemini-2.0-flash",
    "tools": ["word_count"],
    "channels": [],
    "memory_config": {},
    "guardrails": {}
  }' | python -m json.tool

curl -s -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Validator",
    "role": "Quality Checker",
    "system_prompt": "You review outputs and flag inconsistencies or low-quality responses.",
    "model": "gemini-2.0-flash",
    "tools": [],
    "channels": [],
    "memory_config": {},
    "guardrails": {}
  }' | python -m json.tool
```

---

## Demo Script

### Scene 1 — Dashboard Overview (0:00 – 0:30)

**[Show]** `http://localhost:3000` (Dashboard page)

**Narrate:**
> "This is YUNO AI — a full-stack agent orchestration platform.
> On the dashboard you can see your active agents, recent workflow executions,
> and system health at a glance. Everything here is live — backed by a FastAPI
> backend, LangGraph runtime, and real-time WebSocket streaming."

**[Click]** through the nav: Agents → Workflows → Monitor → back to Dashboard.

---

### Scene 2 — Agent Manager (0:30 – 1:30)

**[Navigate to]** `/agents`

**Narrate:**
> "Agents are the building blocks. Each agent has a role, a system prompt that
> defines its personality, a model selection, and a set of tools it can call."

**[Show]** the existing agent list (Researcher, Summarizer, Validator).

**[Click]** **"+ New Agent"**

**Fill in the form:**
- Name: `Calculator Bot`
- Role: `Math Assistant`
- System Prompt: `You are a precise math assistant. Use the calculator tool for all computations.`
- Model: `gemini-2.0-flash`
- Tools: ✅ `calculator`
- Channels: `(none)`

**[Click Save]**

**Narrate:**
> "The agent is now registered in the database and immediately available for
> use in any workflow. Notice the calculator tool — when this agent runs,
> it will call the tool and return the result rather than guessing."

**[Click]** the new agent to show its detail view. Then delete it (to keep the demo clean).

---

### Scene 3 — Workflow Builder (1:30 – 3:00)

**[Navigate to]** `/workflows`

**Narrate:**
> "Workflows connect agents into pipelines. The visual builder uses a DAG
> canvas — drag agents from the sidebar, draw edges between them, and the
> platform compiles it into a LangGraph StateGraph at execution time."

**[Show]** the existing `Research → Summarize` workflow on the canvas.

**Narrate:**
> "Here we have a two-agent chain: the Researcher runs first, its output
> becomes the Summarizer's input. Let me add the Validator to make it a
> three-stage pipeline."

**[Drag]** Validator node onto canvas.  
**[Draw edge]** from Summarizer → Validator.  
**[Click Save]**

**Narrate:**
> "Now I'll execute the workflow with a real prompt."

**[Click Execute]** — enter input: `"What are the latest breakthroughs in AI in 2024?"`

**[Switch to Monitor tab]** — show the real-time log stream:
> "Watch the logs stream in. Researcher runs, calls its tools, passes output
> to Summarizer, which hands off to Validator. Each step's token count and
> latency is tracked."

---

### Scene 4 — Live Telegram Interaction (3:00 – 4:30)

**[Show Telegram]** side-by-side with the UI Monitor screen.

**Narrate:**
> "YUNO AI also integrates with Telegram. I've configured a bot that routes
> messages to the Researcher agent."

**[Send Telegram message]:** `"What's the time right now?"`

**[Watch]** the agent respond (it uses the `datetime_now` tool).

**Narrate:**
> "The bot received my message, the Researcher agent used the datetime tool,
> and the response came back in under a second. Every message is persisted —
> let's confirm that in the UI."

**[Navigate to Message History]** for the Researcher agent or Monitor page.

**Narrate:**
> "Here it is — inbound from Telegram, outbound response, full metadata
> including tokens used. The entire conversation is visible in the platform."

---

### Scene 5 — Execution Monitor & Logs (4:30 – 5:30)

**[Navigate to]** `/monitor` — select the workflow execution from Scene 3.

**Narrate:**
> "The monitoring dashboard shows a live-updated log stream for any workflow
> execution. Each entry shows the agent name, step, input/output snippets,
> and token cost. The WebSocket connection stays open — if you re-run the
> workflow, new events appear instantly without a page refresh."

**[Show]** the execution log detail: expand one log entry to show the full
input, output, and tool calls.

**[Show]** the API docs at `http://localhost:8000/docs` briefly:
> "And everything you see in the UI is powered by a fully documented REST API.
> Any CI pipeline, script, or external tool can trigger workflows, inspect
> logs, or create agents programmatically."

---

### Scene 6 — Architecture Walkthrough (5:30 – 6:00)

**[Show]** `ARCHITECTURE.md` or an architecture diagram.

**Narrate:**
> "Under the hood: React frontend talks to FastAPI over REST and WebSocket.
> The runtime layer uses LangGraph — each agent is a StateGraph node, edges
> represent the workflow DAG. Execution logs and messages persist to
> SQLite in dev or PostgreSQL in production. The Telegram bot runs as a
> background asyncio task, routing messages through the same executor.
> The whole stack starts with a single `docker-compose up --build`."

**[Show]** terminal with `docker-compose up` output / healthy services.

**Narrate:**
> "That's YUNO AI — multi-agent orchestration, real-time monitoring,
> external channel integration, all in one platform. Thank you."

---

## Backup Scenarios (if live demo fails)

| Failure | Backup |
|---------|--------|
| Gemini key not set | Agents return deterministic tool output — still demonstrates the pipeline |
| Telegram bot offline | Skip Scene 4; show message history from a pre-seeded DB |
| WebSocket not streaming | Manually refresh `/monitor` to show persisted logs |
| Docker compose fails | Fall back to `uvicorn app.main:app --reload` + `npm run dev` |

---

## Q&A Prep

**"Why LangGraph over CrewAI?"**
> Graph-based composition maps 1:1 to the visual DAG builder. TypedDict state
> makes inter-node data flow explicit. CrewAI is higher-abstraction but less
> transparent about orchestration internals.

**"How does state sync between agents?"**
> `WorkflowState` is a TypedDict passed through the LangGraph `StateGraph`.
> Each node's output updates `current_input` so the next node receives the
> previous agent's response as its user input.

**"What happens if an agent fails mid-workflow?"**
> The executor catches exceptions per step, logs them to `execution_logs`
> with `status="error"`, and the WebSocket broadcasts the error event. The
> workflow terminates with `status="error"` rather than silently hanging.

**"How would you scale to 100 concurrent agents?"**
> Replace the in-process `WebSocketBroadcaster` with a Redis pub/sub adapter,
> run multiple uvicorn workers, and point all workers at the same Redis.
> The database layer is already async-capable via SQLAlchemy 2.

**"How do you add a new tool?"**
> Drop a `_tool_<name>(self, input: str) -> str` method on `ToolRegistry`.
> It's auto-discovered at registry construction time. Zero config.
