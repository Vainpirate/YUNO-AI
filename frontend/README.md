# YUNO AI — Frontend

React + TypeScript web application for the YUNO AI Agent Orchestration Platform.

---

## Requirements

| Dependency | Version |
|-----------|---------|
| Node.js | 20+ |
| npm | 10+ |

---

## Local Setup

```bash
# From repo root
cd frontend

# Install dependencies
npm install

# Start the dev server (hot-reload on http://localhost:5173)
npm run dev
```

> **Backend must be running** at `http://localhost:8000` for API calls and WebSocket connections to work.

### Environment

The dev server proxies API calls automatically via Vite config.  
For Docker builds, set `VITE_API_URL` at build time (default: `http://localhost:8000`).

---

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start Vite dev server with HMR (port 5173) |
| `npm run build` | TypeScript compile + Vite production bundle → `dist/` |
| `npm run preview` | Serve the production build locally |
| `npm run lint` | ESLint check |

---

## Pages & Routing

| Path | Page | Description |
|------|------|-------------|
| `/` | Dashboard | Overview: agent count, recent executions, system health |
| `/agents` | Agent Manager | Create, edit, delete agents; assign tools and channels |
| `/workflows` | Workflow Studio | Visual DAG builder; execute workflows; view templates |
| `/monitor` | Monitoring | Real-time execution logs; WebSocket-streamed per workflow |

---

## Project Structure

```
frontend/src/
├── components/
│   ├── AgentForm.tsx          # Create / edit agent modal
│   ├── AgentList.tsx          # Agent table with status badges
│   ├── WorkflowBuilder.tsx    # ReactFlow DAG canvas + controls
│   ├── MessageHistory.tsx     # Timeline of inter-agent messages
│   ├── ExecutionMonitor.tsx   # Live log viewer (WebSocket)
│   └── shared/
│       ├── Header.tsx         # Top nav bar
│       ├── Sidebar.tsx        # Left nav (if used)
│       ├── Modal.tsx          # Reusable modal wrapper
│       └── ToastContainer.tsx # Error / success toasts
│
├── pages/
│   ├── Dashboard.tsx
│   ├── AgentManager.tsx
│   ├── WorkflowStudio.tsx
│   └── Monitoring.tsx
│
├── hooks/
│   └── useWebSocket.ts        # Auto-reconnecting WebSocket hook
│
├── services/
│   └── api.ts                 # Axios client + typed endpoint wrappers
│
├── store/
│   └── index.ts               # Zustand global state
│
├── types/
│   └── index.ts               # Shared TypeScript interfaces
│
├── App.tsx                    # BrowserRouter + route definitions
└── main.tsx                   # React 19 root mount
```

---

## Key Libraries

| Library | Version | Purpose |
|---------|---------|---------|
| React | 19 | UI framework |
| TypeScript | 6 | Type safety |
| Vite | 8 | Build tool + dev server |
| TailwindCSS | 3 | Utility-first styling |
| ReactFlow | 11 | Workflow DAG canvas |
| Zustand | 5 | Global state management |
| Axios | 1 | HTTP client (typed API wrappers) |
| lucide-react | latest | Icon set |

---

## API Integration

All HTTP calls go through `src/services/api.ts`:

```typescript
// Example: create an agent
import api from '../services/api';
const agent = await api.agents.create({
  name: 'Researcher',
  role: 'Web Researcher',
  system_prompt: '...',
  model: 'gpt-4o-mini',
  tools: ['calculator'],
  channels: ['telegram'],
});
```

The base URL defaults to `http://localhost:8000`. Override with `VITE_API_URL`.

---

## WebSocket Hook

`src/hooks/useWebSocket.ts` provides an auto-reconnecting WebSocket client:

```typescript
import { useWebSocket } from '../hooks/useWebSocket';

// Subscribe to a workflow's log stream
const { messages, status } = useWebSocket(`/ws/logs/${workflowId}`);
```

Events received from the backend:

| Event type | Payload fields | When fired |
|-----------|---------------|-----------|
| `workflow_started` | `workflow_id`, `agent_count` | Workflow begins |
| `step_completed` | `agent`, `response`, `tool_outputs` | Each agent node finishes |
| `workflow_completed` | `final_output`, `steps` | All nodes done |
| `agent_response` | `agent`, `response` | Single-agent execute |

---

## Docker

```bash
# Build production image
docker build -t yuno-frontend .

# Run (assumes backend at http://backend:8000)
docker run -p 3000:3000 \
  --build-arg VITE_API_URL=http://localhost:8000 \
  yuno-frontend

# Full stack (recommended)
cd ..
docker-compose up --build
```

The Dockerfile uses a two-stage build:
1. **Builder** — Node 20, `npm ci`, `npm run build` → `dist/`
2. **Runner** — Node 20 + `serve` — serves `dist/` on port 3000
