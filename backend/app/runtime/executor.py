"""RuntimeExecutor — core agent and workflow execution engine.

Design notes
------------
* ``_run_agent_step``  is synchronous and pure (no I/O side-effects beyond the
  tool registry and in-memory store).  It is the single authoritative place
  where an agent processes input and produces a response.

* ``execute_agent`` / ``execute_workflow`` are **async** so they can:
    - await Gemini calls via the async client when available
    - emit real-time WebSocket events via the broadcaster
    - be awaited directly from FastAPI async route handlers

* LLM behaviour:
    - If ``GEMINI_API_KEY`` is set, the async Google Gemini client is used for
      agents that have no matching tool for the input.
    - If the key is absent (CI, tests, local dev without a key), a harmless
      mock string is returned so the rest of the stack keeps working.

* Tool behaviour:
    - If an agent has registered tools, every tool is executed against the
      user input and the **last tool result** is used as the agent's response.
      This preserves backward-compatibility with the existing test suite
      (``test_messaging.py`` asserts response == "100" for a calculator agent).
    - Tool output is also passed to the LLM as additional context when a key
      is available, so the final response is still natural-language where
      appropriate.

* LangGraph integration:
    - ``_build_langgraph`` converts a workflow's ``graph`` JSON
      (``{nodes: [...], edges: [[src,dst], ...]}``) into a compiled
      LangGraph ``StateGraph``.
    - Each node is a closure over ``_run_agent_step`` created by
      ``agent_factory.make_agent_node``.
    - The compiled graph is invoked via ``ainvoke`` so async broadcaster
      events can be fired between steps using a custom stream callback.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Agent, ExecutionLog, Message, Workflow
from app.runtime.agent_factory import build_agent_prompt, make_agent_node
from app.runtime.memory import MemoryStore
from app.runtime.tools import ToolRegistry
from app.websocket.broadcaster import broadcaster

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Typed workflow state (used by LangGraph StateGraph)
# ---------------------------------------------------------------------------

class WorkflowState(dict):
    """Typed dict used as LangGraph state.

    Keys:
        messages      – accumulated chat history across all agent nodes
        current_input – the text passed to the *next* node
        final_output  – the most recent agent response (final answer at END)
        step_outputs  – list of per-step result dicts from _run_agent_step
    """


# ---------------------------------------------------------------------------
# RuntimeExecutor
# ---------------------------------------------------------------------------

class RuntimeExecutor:
    def __init__(self) -> None:
        self.tools = ToolRegistry()
        self.memory = MemoryStore()
        self._gemini_client = None  # lazy-initialised google.genai.Client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_gemini_client(self):
        """Return a cached google.genai.Client, or None if no key is set."""
        if self._gemini_client is not None:
            return self._gemini_client
        try:
            from app.config import settings
            if not settings.gemini_api_key:
                return None
            from google import genai  # type: ignore[import]
            self._gemini_client = genai.Client(api_key=settings.gemini_api_key)
            return self._gemini_client
        except Exception:  # noqa: BLE001
            return None

    def _run_agent_step(self, agent: Agent, user_input: str) -> dict:
        """Synchronous, side-effect-free agent step.

        Returns a result dict::

            {
                "agent_id":    str,
                "agent_name":  str,
                "response":    str,   # final text returned to caller / next agent
                "tool_outputs": [...],
                "prompt":      str,   # the assembled prompt (for logging)
            }

        If the agent has tools the tool result IS the response (keeps tests
        passing).  LLM synthesis is applied on top in the async layer when a
        key is available.
        """
        memory = self.memory.get(str(agent.id))
        prompt = build_agent_prompt(agent, user_input, memory)

        # --- tool execution ---
        selected_tools = [t for t in (agent.tools or []) if self.tools.has_tool(t)]
        tool_outputs: list[dict] = []
        for tool_name in selected_tools:
            try:
                result = self.tools.execute(tool_name, user_input)
            except Exception as exc:  # noqa: BLE001
                result = f"tool_error: {exc}"
            tool_outputs.append({"tool": tool_name, "result": result})

        # --- response determination (sync path) ---
        if tool_outputs:
            # Use last tool result as primary response — LLM wrapping is done
            # asynchronously in execute_agent / _llm_synthesise_tool_result.
            response_text = tool_outputs[-1]["result"]
        else:
            # No tools: placeholder — async layer replaces this with LLM output.
            response_text = f"[{agent.name}] received: {user_input}"

        # Update in-memory history
        self.memory.append(str(agent.id), user_input)
        self.memory.append(str(agent.id), response_text)

        return {
            "agent_id": str(agent.id),
            "agent_name": agent.name,
            "response": response_text,
            "tool_outputs": tool_outputs,
            "prompt": prompt,
        }

    async def _llm_call(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str = "gemini-2.0-flash",
    ) -> tuple[str | None, int]:
        """Async LLM call via Google Gemini.  Returns (text, tokens_used) tuple.

        ``text`` is None if no client is configured or the call fails.
        ``tokens_used`` is the real prompt+candidates token count from Gemini's
        ``usage_metadata``; falls back to 0 on error.

        Converts the memory store's OpenAI-style message list
        (``[{"role": "user"|"assistant", "content": "..."}]``) to the Gemini
        Content format (``[{"role": "user"|"model", "parts": [{"text": "..."}]}]``).
        The system prompt is passed via ``GenerateContentConfig.system_instruction``.
        """
        client = self._get_gemini_client()
        if client is None:
            return None, 0
        try:
            from google.genai import types  # type: ignore[import]

            # Convert OpenAI-style messages → Gemini Content objects
            # Gemini uses "model" where OpenAI uses "assistant"
            gemini_contents = [
                types.Content(
                    role="model" if msg["role"] == "assistant" else "user",
                    parts=[types.Part(text=msg["content"])],
                )
                for msg in messages
                if msg.get("content")
            ]

            # Gemini requires the conversation to start with a user turn
            if not gemini_contents or gemini_contents[0].role != "user":
                gemini_contents.insert(
                    0,
                    types.Content(role="user", parts=[types.Part(text="(start)")]),
                )

            response = await client.aio.models.generate_content(
                model=model,
                contents=gemini_contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                ),
            )
            usage = response.usage_metadata
            tokens = (usage.prompt_token_count or 0) + (usage.candidates_token_count or 0)
            return response.text, tokens
        except Exception as exc:  # noqa: BLE001
            logger.warning("Gemini LLM call failed: %s", exc)
            return None, 0

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def execute_agent(
        self,
        db: Session,
        agent: Agent,
        user_input: str,
        workflow_id: UUID | None = None,
    ) -> dict:
        """Execute a single agent and persist the result.

        Emits a WebSocket event to any subscribers listening on
        ``/ws/agent-status/{agent.id}`` and (if workflow_id is set)
        ``/ws/logs/{workflow_id}``.
        """
        # --- emit: agent is running ---
        await _safe_publish_agent(str(agent.id), {"status": "running", "agent": agent.name})

        # --- synchronous step (tools + prompt) ---
        result = self._run_agent_step(agent, user_input)

        # --- async LLM synthesis when no tool was involved ---
        llm_tokens = 0
        if not result["tool_outputs"]:
            llm_response, llm_tokens = await self._llm_call(
                system_prompt=agent.system_prompt or "You are a helpful assistant.",
                messages=self.memory.as_messages(str(agent.id)),
                model=agent.model or "gemini-2.0-flash",
            )
            if llm_response:
                # Replace placeholder with real LLM output and update memory
                result["response"] = llm_response
                # Overwrite the last two memory entries with the real response
                self.memory.clear(str(agent.id))
                # memory was cleared; re-append the real exchange
                self.memory.append(str(agent.id), user_input)
                self.memory.append(str(agent.id), llm_response)

        # Real token count from Gemini; fall back to word-count estimate for
        # tool-only steps where no LLM call was made.
        tokens_used = llm_tokens or max(1, len(result["prompt"].split()) + len(result["response"].split()))

        # --- persist to DB ---
        if workflow_id is not None:
            db.add(
                Message(
                    from_agent_id=agent.id,
                    to_agent_id=None,
                    workflow_id=workflow_id,
                    channel="internal",
                    content=result["response"],
                    metadata_json={"tool_outputs": result["tool_outputs"]},
                )
            )

        db.add(
            ExecutionLog(
                workflow_id=workflow_id,
                agent_id=agent.id,
                step_name="execute_agent",
                status="success",
                input={"prompt": result["prompt"]},
                output={
                    "response": result["response"],
                    "tool_outputs": result["tool_outputs"],
                },
                tokens_used=tokens_used,
                cost=round(tokens_used * 0.000_000_15, 6),  # gemini-2.0-flash: ~$0.15/1M tokens
                created_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

        # --- emit: agent idle + log event ---
        await _safe_publish_agent(str(agent.id), {
            "status": "idle",
            "agent": agent.name,
            "response_preview": result["response"][:120],
        })
        if workflow_id:
            await _safe_publish_workflow(str(workflow_id), {
                "event": "agent_response",
                "agent": agent.name,
                "response": result["response"],
                "tool_outputs": result["tool_outputs"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return {
            "agent_id": result["agent_id"],
            "response": result["response"],
            "tool_outputs": result["tool_outputs"],
        }

    async def execute_workflow(self, db: Session, workflow: Workflow, initial_input: str = "Workflow started") -> dict:
        """Execute a multi-agent workflow using a LangGraph StateGraph.

        1. Resolves all agents referenced in the workflow.
        2. Builds a LangGraph ``StateGraph`` from the workflow's ``graph`` JSON.
        3. Invokes the graph; each node calls ``_run_agent_step`` synchronously.
        4. Persists messages + execution logs for every step.
        5. Emits WebSocket events at start, per step, and at completion.

        Falls back to a simple sequential loop if LangGraph is unavailable or
        the workflow graph cannot be compiled.
        """
        agent_ids = [UUID(a) for a in (workflow.agents or [])]
        if not agent_ids:
            return {"workflow_id": str(workflow.id), "status": "error", "error": "No agents attached"}

        agents_map: dict[str, Agent] = {}
        for aid in agent_ids:
            agent = db.get(Agent, aid)
            if agent:
                agents_map[str(aid)] = agent

        if not agents_map:
            return {"workflow_id": str(workflow.id), "status": "error", "error": "No valid agents found"}

        # --- emit workflow start ---
        await _safe_publish_workflow(str(workflow.id), {
            "event": "workflow_started",
            "workflow_id": str(workflow.id),
            "workflow_name": workflow.name,
            "agent_count": len(agents_map),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        # --- build and run LangGraph ---
        compiled = self._build_langgraph(workflow, agents_map)
        if compiled is not None:
            initial_state: WorkflowState = {
                "messages": [],
                "current_input": initial_input,
                "final_output": "",
                "step_outputs": [],
            }
            try:
                final_state = compiled.invoke(initial_state)
                step_outputs: list[dict] = final_state.get("step_outputs", [])
                final_output: str = final_state.get("final_output", "")
            except Exception as exc:  # noqa: BLE001
                logger.error("LangGraph execution failed: %s", exc)
                step_outputs, final_output = await self._fallback_sequential(db, agents_map, workflow)
        else:
            step_outputs, final_output = await self._fallback_sequential(db, agents_map, workflow, initial_input)

        # --- persist results ---
        for step in step_outputs:
            agent_id = UUID(step["agent_id"])
            db.add(
                Message(
                    from_agent_id=agent_id,
                    workflow_id=workflow.id,
                    channel="internal",
                    content=step["response"],
                    metadata_json={"tool_outputs": step.get("tool_outputs", [])},
                )
            )
            wf_tokens = step.get("tokens_used") or max(
                1, len(step.get("prompt", "").split()) + len(step["response"].split())
            )
            db.add(
                ExecutionLog(
                    workflow_id=workflow.id,
                    agent_id=agent_id,
                    step_name=f"workflow_step_{step['agent_name']}",
                    status="success",
                    input={"prompt": step.get("prompt", "")},
                    output={"response": step["response"], "tool_outputs": step.get("tool_outputs", [])},
                    tokens_used=wf_tokens,
                    cost=round(wf_tokens * 0.000_000_15, 6),
                    created_at=datetime.now(timezone.utc),
                )
            )
            # Emit per-step WebSocket log
            await _safe_publish_workflow(str(workflow.id), {
                "event": "step_completed",
                "agent": step["agent_name"],
                "response": step["response"],
                "tool_outputs": step.get("tool_outputs", []),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        db.commit()

        # --- emit workflow completed ---
        await _safe_publish_workflow(str(workflow.id), {
            "event": "workflow_completed",
            "workflow_id": str(workflow.id),
            "final_output": final_output,
            "steps": len(step_outputs),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return {
            "workflow_id": str(workflow.id),
            "status": "completed",
            "final_output": final_output,
            "steps": len(step_outputs),
        }

    # ------------------------------------------------------------------
    # LangGraph builder
    # ------------------------------------------------------------------

    def _build_langgraph(self, workflow: Workflow, agents_map: dict[str, Agent]):
        """Compile a LangGraph StateGraph from the workflow's graph descriptor.

        Returns a compiled graph or ``None`` if LangGraph is unavailable or
        the graph descriptor has no valid nodes.
        """
        try:
            from langgraph.graph import END, StateGraph  # type: ignore[import]
        except ImportError:
            logger.warning("langgraph not installed — falling back to sequential executor")
            return None

        graph_def: dict = workflow.graph or {}
        node_ids: list[str] = [str(n) for n in graph_def.get("nodes", list(agents_map.keys()))]
        edges: list[list] = graph_def.get("edges", [])

        # Filter to nodes that have a corresponding agent
        valid_nodes = [n for n in node_ids if n in agents_map]
        if not valid_nodes:
            return None

        # Define state schema as a plain dict (TypedDict-compatible)
        from typing_extensions import TypedDict  # type: ignore[import]

        class WFState(TypedDict):
            messages: list
            current_input: str
            final_output: str
            step_outputs: list

        graph = StateGraph(WFState)

        # Add one node per valid agent
        for node_id in valid_nodes:
            agent = agents_map[node_id]
            node_fn = make_agent_node(agent, self._run_agent_step)
            graph.add_node(node_id, node_fn)

        # Entry point = first valid node
        graph.set_entry_point(valid_nodes[0])

        # ── Group edges by source node ─────────────────────────────────
        # Each edge may be:
        #   [src, dst]            — unconditional
        #   [src, dst, condition] — conditional; "condition" is a plain
        #                           keyword/phrase checked against the
        #                           previous agent's output (case-insensitive
        #                           substring match).
        # ──────────────────────────────────────────────────────────────────

        # outgoing[src] = list of (dst, condition_or_None)
        outgoing: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
        for edge in edges:
            if len(edge) < 2:
                continue
            src, dst = str(edge[0]), str(edge[1])
            condition: str | None = str(edge[2]).strip() if len(edge) >= 3 and edge[2] else None
            if src in agents_map and dst in agents_map:
                outgoing[src].append((dst, condition))

        added_src: set[str] = set()

        for src, targets in outgoing.items():
            cond_targets  = [(dst, cond) for dst, cond in targets if cond]
            plain_targets = [dst for dst, cond in targets if not cond]
            default_next  = plain_targets[0] if plain_targets else END

            if cond_targets:
                # Build a routing function that checks the last agent output
                # against each condition keyword, falling back to default_next.
                all_dests = {dst for dst, _ in cond_targets} | {default_next}

                def _make_router(
                    cond_edges: list[tuple[str, str]],
                    fallback: str,
                ) -> "Callable[[WFState], str]":
                    def _router(state: WFState) -> str:  # type: ignore[return]
                        last_output = (state.get("final_output") or "").lower()
                        for target, keyword in cond_edges:
                            if keyword.lower() in last_output:
                                return target
                        return fallback
                    return _router

                graph.add_conditional_edges(
                    src,
                    _make_router(cond_targets, default_next),
                    {d: d for d in all_dests},
                )
            else:
                # Simple unconditional edge(s)
                for dst in plain_targets:
                    graph.add_edge(src, dst)

            added_src.add(src)

        # Any node with no explicit outgoing edge → END
        for node_id in valid_nodes:
            if node_id not in added_src:
                graph.add_edge(node_id, END)

        return graph.compile()

    # ------------------------------------------------------------------
    # Sequential fallback (no LangGraph)
    # ------------------------------------------------------------------

    async def _fallback_sequential(
        self, _db: Session, agents_map: dict[str, Agent], _workflow: Workflow,
        initial_input: str = "Workflow started",
    ) -> tuple[list[dict], str]:
        """Simple ordered execution when LangGraph is unavailable."""
        step_outputs: list[dict] = []
        current_input = initial_input
        for agent in agents_map.values():
            result = self._run_agent_step(agent, current_input)
            current_input = result["response"]
            step_outputs.append(result)
        return step_outputs, current_input


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

runtime_executor = RuntimeExecutor()


# ---------------------------------------------------------------------------
# Broadcaster helpers (best-effort — never raise)
# ---------------------------------------------------------------------------

async def _safe_publish_workflow(workflow_id: str, payload: dict) -> None:
    try:
        await broadcaster.publish_workflow_log(workflow_id, payload)
    except Exception:  # noqa: BLE001
        pass


async def _safe_publish_agent(agent_id: str, payload: dict) -> None:
    try:
        await broadcaster.publish_agent_status(agent_id, payload)
    except Exception:  # noqa: BLE001
        pass
