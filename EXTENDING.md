# Extending YUNO AI

This guide covers the three most common extension points:
1. [Adding a new tool](#1-adding-a-new-tool)
2. [Adding a new messaging channel](#2-adding-a-new-messaging-channel)
3. [Adding a new workflow template](#3-adding-a-new-workflow-template)

---

## 1. Adding a New Tool

Tools are registered in `backend/app/runtime/tools.py` and optionally in
`backend/app/integrations/external_tools.py` (for tools that need external
API calls).

### Step 1 — Write the tool function

```python
# backend/app/runtime/tools.py

class ToolRegistry:
    ...

    def _tool_my_custom_tool(self, input_text: str) -> str:
        """
        A tool that reverses the input string.
        Convention: method name must start with `_tool_`.
        """
        return input_text[::-1]
```

That's it. The `ToolRegistry` auto-discovers every method whose name starts
with `_tool_` and registers it under `<method_name[6:]>` (i.e. `my_custom_tool`).

### Step 2 — Verify registration

```python
from app.runtime.tools import ToolRegistry
registry = ToolRegistry()
print(registry.list_tools())  # → [..., "my_custom_tool"]
```

### Step 3 — Assign to an agent

Via the UI (Agent Manager → Tools checklist) or directly via the API:

```bash
curl -X PATCH http://localhost:8000/api/agents/<id>/tools \
  -H "Content-Type: application/json" \
  -d '{"tools": ["calculator", "my_custom_tool"]}'
```

### External tools (HTTP calls)

For tools that hit external APIs, add them in
`backend/app/integrations/external_tools.py` and register them inside
`register_external_tools(registry)` which is called during app startup:

```python
# backend/app/integrations/external_tools.py

def register_external_tools(registry: ToolRegistry) -> None:
    ...

    def weather(input_text: str) -> str:
        """Return current weather for a city extracted from input_text."""
        import httpx
        city = input_text.strip().split()[-1]   # naive extraction
        r = httpx.get(f"https://wttr.in/{city}?format=3", timeout=5)
        return r.text

    registry.register("weather", weather)
```

---

## 2. Adding a New Messaging Channel

The Telegram integration in `backend/app/integrations/telegram_bot.py` is the
reference implementation. Follow the same pattern for any new channel.

### Minimum contract

A channel integration must:

1. **Receive** an inbound message (webhook or polling).
2. **Route** it to an agent via `runtime_executor.execute_agent(...)`.
3. **Send back** the agent's response through the channel.
4. **Persist** to `message_history` (for UI visibility).
5. **Broadcast** a WebSocket event (for live monitor).

### Example — Slack

```python
# backend/app/integrations/slack_bot.py

from fastapi import APIRouter, Request
from app.database import get_db
from app.runtime.executor import runtime_executor
from app.models import Agent, MessageHistory
from app.websocket.broadcaster import broadcaster
from sqlalchemy.orm import Session
import httpx, json

router = APIRouter(prefix="/webhooks/slack", tags=["slack"])

SLACK_BOT_TOKEN = "xoxb-..."

@router.post("")
async def slack_webhook(request: Request):
    body = await request.json()

    # Slack sends a url_verification challenge on first setup
    if body.get("type") == "url_verification":
        return {"challenge": body["challenge"]}

    event = body.get("event", {})
    if event.get("type") != "message" or event.get("bot_id"):
        return {}           # ignore bot messages / non-message events

    user_id  = event["user"]
    text     = event["text"]
    channel  = event["channel"]

    # --- find agent for this Slack user ---
    db: Session = next(get_db())
    agent = db.query(Agent).first()          # replace with proper user→agent mapping

    # --- execute ---
    result = await runtime_executor.execute_agent(db, agent, text)

    # --- reply via Slack API ---
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://slack.com/api/chat.postMessage",
            headers={"Authorization": f"Bearer {SLACK_BOT_TOKEN}"},
            json={"channel": channel, "text": result["response"]},
        )

    # --- persist ---
    db.add(MessageHistory(
        channel_user_id=user_id,
        agent_id=agent.id,
        direction="inbound",
        content=text,
    ))
    db.add(MessageHistory(
        channel_user_id=user_id,
        agent_id=agent.id,
        direction="outbound",
        content=result["response"],
    ))
    db.commit()

    # --- broadcast to UI ---
    await broadcaster.broadcast_telegram_event({   # reuse fan-out method
        "event": "slack_message",
        "user": user_id,
        "agent": agent.name,
        "response": result["response"],
    })

    return {}
```

**Register the router** in `backend/app/main.py`:

```python
from app.integrations.slack_bot import router as slack_router
app.include_router(slack_router)
```

**Point Slack to your endpoint** in the Slack app's Event Subscriptions:
`https://your-domain/webhooks/slack`

---

## 3. Adding a New Workflow Template

Templates are static descriptors returned by `GET /api/workflows/templates`.
Each template is a plain Python dict; the frontend uses it to pre-populate the
workflow builder.

```python
# backend/app/routes/workflows.py  →  list_workflow_templates()

@router.get("/templates")
def list_workflow_templates():
    return [
        # ... existing templates ...

        {
            "name": "fact_check",
            "description": "Three-agent pipeline: claim extraction → web search → verdict.",
            "graph": {
                "nodes": ["extractor", "searcher", "verifier"],
                "edges": [
                    ["extractor", "searcher"],
                    ["searcher",  "verifier"],
                ],
            },
        },
    ]
```

The frontend will display the new template in the Workflow Studio template
picker. Users can then instantiate it, assign real agent IDs to each node,
and execute.

### Conditional edges (future)

The current schema stores `edges` as a list of `[src, dst]` pairs. To add
conditional routing, extend the edge format:

```json
{
  "nodes": ["a", "b", "c"],
  "edges": [
    ["a", "b"],
    ["a", "c", {"condition": "score > 0.7"}]
  ]
}
```

Then update `_build_langgraph()` in `executor.py` to call
`graph.add_conditional_edges(src, routing_fn)` instead of `graph.add_edge()`
when a condition field is present.

---

## 4. Adding a New LLM Provider

The LLM call lives in `RuntimeExecutor._llm_call()` in
`backend/app/runtime/executor.py`. The platform currently uses **Google Gemini**
(`google-genai` SDK) as its default provider. The patterns below show how to
add OpenAI or Anthropic as alternatives.

### Add OpenAI as an alternative provider

```python
# backend/app/runtime/executor.py — inside RuntimeExecutor

def _get_openai_client(self):
    from app.config import settings
    if not getattr(settings, "openai_api_key", ""):
        return None
    from openai import AsyncOpenAI  # pip install openai
    return AsyncOpenAI(api_key=settings.openai_api_key)

async def _llm_call(self, system_prompt, messages, model="gemini-2.0-flash"):
    # Route gpt-* models to OpenAI
    if model.startswith("gpt-"):
        client = self._get_openai_client()
        if client is None:
            return None
        try:
            completion = await client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": system_prompt}] + messages,
            )
            return completion.choices[0].message.content
        except Exception as exc:
            logger.warning("OpenAI LLM call failed: %s", exc)
            return None

    # ... existing Gemini path below
```

Add `openai_api_key: str = ""` to `config.py` and `OPENAI_API_KEY=` to `.env.example`.
Agents that set `model: "gpt-4o-mini"` will route through OpenAI.

### Add Anthropic Claude as an alternative provider

```python
def _get_anthropic_client(self):
    from app.config import settings
    if not getattr(settings, "anthropic_api_key", ""):
        return None
    from anthropic import AsyncAnthropic  # pip install anthropic
    return AsyncAnthropic(api_key=settings.anthropic_api_key)

async def _llm_call(self, system_prompt, messages, model="gemini-2.0-flash"):
    if model.startswith("claude"):
        client = self._get_anthropic_client()
        if client is None:
            return None
        try:
            response = await client.messages.create(
                model=model,
                max_tokens=1024,
                system=system_prompt,
                messages=messages,  # role/content format matches Anthropic
            )
            return response.content[0].text
        except Exception as exc:
            logger.warning("Anthropic LLM call failed: %s", exc)
            return None

    # ... existing Gemini path below
```

Add `anthropic_api_key: str = ""` to `config.py` and `ANTHROPIC_API_KEY=` to
`.env.example`. Agents that set `model: "claude-sonnet-4-6"` will route through
the Anthropic client.
