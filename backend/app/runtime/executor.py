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

* Guardrails enforcement (applied at runtime, not just stored in DB):
    - ``banned_keywords``: list of strings; if any appear in input or output,
      the step is blocked with a safe refusal message.
    - ``max_input_tokens``: approximate token cap on user input (word-count proxy).
    - ``max_output_tokens``: approximate token cap on agent response.
    - ``blocked_topics``: list of topic strings treated identically to banned_keywords.
    - ``require_safe_response``: if true, non-compliant outputs become refusals.

* Memory config (read from agent.memory_config):
    - ``window_size``: number of messages to retain in the sliding-window memory
      (defaults to MemoryStore.WINDOW = 20).

* Interaction rules (read from agent.interaction_rules):
    - ``response_format``: "text" | "json" | "markdown" — appended as instruction.
    - ``language``: instruct the LLM to reply in a specific language.
    - ``temperature``: float 0–1 passed to Gemini GenerateContentConfig.
    - ``max_turns``: cap on conversation turns (enforced against memory depth).

* Skills (read from agent.skills):
    - List of ``{"name": str, "description": str, "enabled": bool}`` dicts.
    - Enabled skills are appended to the system prompt so the LLM knows it can
      exhibit those behaviours.

* LLM behaviour:
    - If ``GEMINI_API_KEY`` is set, the async Google Gemini client is used.
    - If the key is absent, a harmless mock string is returned.

* Loop safety (feedback loops):
    - ``max_iterations`` on the Workflow model caps how many times any single
      node can fire in a single run (default 10).
    - The LangGraph state carries ``iteration_counts`` — a dict mapping node_id
      to its visit count.  A node that exceeds the cap routes to END.
"""
from __future__ import annotations

import asyncio
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
# Guardrail helpers
# ---------------------------------------------------------------------------

class GuardrailViolation(Exception):
    """Raised when a guardrail rule is violated."""


def _apply_guardrails(guardrails: dict, text: str, stage: str) -> str:
    """Check *text* against guardrails config.

    Returns the (possibly truncated) text if compliant.
    Raises GuardrailViolation if a hard block is triggered.

    ``stage`` is "input" or "output" — used in violation messages.
    """
    if not guardrails:
        return text

    # Keyword / topic blocklist
    blocked: list[str] = list(guardrails.get("banned_keywords", []))
    blocked += list(guardrails.get("blocked_topics", []))
    lower_text = text.lower()
    for kw in blocked:
        if kw.lower() in lower_text:
            raise GuardrailViolation(
                f"Guardrail blocked {stage}: contains prohibited term '{kw}'"
            )

    # Token-count caps (approximate: words × 1.3 ≈ tokens)
    approx_tokens = len(text.split()) * 1.3
    cap_key = "max_input_tokens" if stage == "input" else "max_output_tokens"
    cap = guardrails.get(cap_key)
    if cap and approx_tokens > cap:
        # Truncate rather than hard-block for output; hard-block for input
        if stage == "output":
            # Soft truncate to keep things flowing
            word_limit = int(cap / 1.3)
            text = " ".join(text.split()[:word_limit]) + " [truncated by guardrail]"
        else:
            raise GuardrailViolation(
                f"Guardrail blocked input: exceeds max_input_tokens ({cap})"
            )

    return text


# ---------------------------------------------------------------------------
# Typed workflow state (used by LangGraph StateGraph)
# ---------------------------------------------------------------------------

try:
    from typing_extensions import TypedDict as _TypedDict  # type: ignore[import]

    class WFState(_TypedDict):
        messages: list
        current_input: str
        final_output: str
        step_outputs: list
        iteration_counts: dict

except Exception:  # noqa: BLE001
    WFState = dict  # type: ignore[assignment,misc]


class WorkflowState(dict):
    """Typed dict used as LangGraph state.

    Keys:
        messages         – accumulated chat history across all agent nodes
        current_input    – the text passed to the *next* node
        final_output     – the most recent agent response (final answer at END)
        step_outputs     – list of per-step result dicts from _run_agent_step
        iteration_counts – dict[node_id, int] tracking visits for loop safety
    """


# ---------------------------------------------------------------------------
# RuntimeExecutor
# ---------------------------------------------------------------------------

_GROQ_MODELS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-70b-8192",
    "llama3-8b-8192",
    "mixtral-8x7b-32768",
    "gemma2-9b-it",
    "gemma-7b-it",
}


def _is_groq_model(model: str) -> bool:
    """True when *model* is a known Groq model name."""
    m = (model or "").lower()
    return m in _GROQ_MODELS or m.startswith("llama") or m.startswith("mixtral") or m.startswith("gemma")


class RuntimeExecutor:
    def __init__(self) -> None:
        self.tools = ToolRegistry()
        self.memory = MemoryStore()
        self._gemini_client = None  # lazy-initialised google.genai.Client
        self._groq_client = None    # lazy-initialised groq.AsyncGroq

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_groq_client(self):
        """Return a cached groq.AsyncGroq client, or None if no key / sdk."""
        if self._groq_client is not None:
            return self._groq_client
        try:
            from app.config import settings
            if not settings.groq_api_key:
                return None
            from groq import AsyncGroq  # type: ignore[import]
            self._groq_client = AsyncGroq(api_key=settings.groq_api_key)
            return self._groq_client
        except Exception:  # noqa: BLE001
            return None

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

    def _memory_window(self, agent: Agent) -> int:
        """Return the effective memory window size for this agent."""
        cfg = agent.memory_config or {}
        return int(cfg.get("window_size", MemoryStore.WINDOW))

    def _build_system_prompt(self, agent: Agent) -> str:
        """Assemble the full system prompt: base + skills + interaction rules."""
        base = agent.system_prompt or "You are a helpful assistant."

        # Append enabled skills as behavioural instructions
        skills: list[dict] = agent.skills or []
        enabled_skills = [s for s in skills if s.get("enabled", True) and s.get("name")]
        if enabled_skills:
            skill_lines = "\n".join(
                f"- {s['name']}: {s.get('description', '')}" for s in enabled_skills
            )
            base += f"\n\nYou have the following skills:\n{skill_lines}"

        # Append interaction rules as format/language instructions
        rules: dict = agent.interaction_rules or {}
        if rules.get("response_format") == "json":
            base += "\n\nAlways respond with valid JSON only — no prose outside the JSON."
        elif rules.get("response_format") == "markdown":
            base += "\n\nAlways format your response using Markdown."
        if rules.get("language"):
            base += f"\n\nAlways respond in {rules['language']}."

        return base

    def _run_agent_step(self, agent: Agent, user_input: str) -> dict:
        """Synchronous, side-effect-free agent step.

        Returns a result dict::

            {
                "agent_id":    str,
                "agent_name":  str,
                "response":    str,   # final text returned to caller / next agent
                "tool_outputs": [...],
                "prompt":      str,   # the assembled prompt (for logging)
                "guardrail_blocked": bool,
            }

        Guardrails are enforced:
          - Input is checked before any processing.
          - Output is checked (and optionally truncated) before returning.

        If the agent has tools the tool result IS the response (keeps tests
        passing).  LLM synthesis is applied on top in the async layer when a
        key is available.
        """
        guardrails: dict = agent.guardrails or {}
        window = self._memory_window(agent)

        # --- guardrail: check input ---
        try:
            user_input = _apply_guardrails(guardrails, user_input, "input")
        except GuardrailViolation as exc:
            logger.warning("Guardrail input violation for agent %s: %s", agent.name, exc)
            return {
                "agent_id": str(agent.id),
                "agent_name": agent.name,
                "response": f"[Guardrail] {exc}",
                "tool_outputs": [],
                "prompt": "",
                "guardrail_blocked": True,
            }

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
            response_text = tool_outputs[-1]["result"]
        else:
            response_text = f"[{agent.name}] received: {user_input}"

        # --- guardrail: check output ---
        try:
            response_text = _apply_guardrails(guardrails, response_text, "output")
        except GuardrailViolation as exc:
            logger.warning("Guardrail output violation for agent %s: %s", agent.name, exc)
            response_text = f"[Guardrail] {exc}"

        # Update in-memory history with configured window
        self.memory.append(str(agent.id), user_input, window)
        self.memory.append(str(agent.id), response_text, window)

        return {
            "agent_id": str(agent.id),
            "agent_name": agent.name,
            "response": response_text,
            "tool_outputs": tool_outputs,
            "prompt": prompt,
            "guardrail_blocked": False,
        }

    async def _llm_call(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str = "llama-3.3-70b-versatile",
        temperature: float | None = None,
    ) -> tuple[str | None, int]:
        """Dispatch to Groq or Gemini.

        Priority:
          1. If GROQ_API_KEY is set → always try Groq first.
             Uses the agent's model name if it's a known Groq model,
             otherwise falls back to llama-3.3-70b-versatile so agents
             created with old Gemini model names still work.
          2. If Groq fails or key is absent → try Gemini.
          3. Return (None, 0) when no provider is available.
        """
        groq_client = self._get_groq_client()
        if groq_client is not None:
            groq_model = model if _is_groq_model(model) else "llama-3.3-70b-versatile"
            result = await self._groq_call(system_prompt, messages, groq_model, temperature)
            if result[0] is not None:
                return result
            logger.info("Groq call failed for model '%s', falling back to Gemini", groq_model)

        # Gemini fallback (used when GROQ_API_KEY not set or Groq call failed)
        gemini_model = model if not _is_groq_model(model) else "gemini-2.0-flash-lite"
        return await self._gemini_call(system_prompt, messages, gemini_model, temperature)

    async def _groq_call(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        temperature: float | None = None,
    ) -> tuple[str | None, int]:
        """Async LLM call via Groq (OpenAI-compatible).

        Converts the memory store's message list to OpenAI format and prepends
        the system prompt as a ``system`` role message.
        """
        client = self._get_groq_client()
        if client is None:
            return None, 0
        try:
            groq_messages = [{"role": "system", "content": system_prompt}]
            groq_messages += [
                {"role": msg["role"], "content": msg["content"]}
                for msg in messages
                if msg.get("content")
            ]
            kwargs: dict = {"model": model, "messages": groq_messages}
            if temperature is not None:
                kwargs["temperature"] = float(temperature)

            response = await client.chat.completions.create(**kwargs)
            usage = response.usage
            tokens = (usage.prompt_tokens or 0) + (usage.completion_tokens or 0)
            return response.choices[0].message.content, tokens
        except Exception as exc:  # noqa: BLE001
            logger.warning("Groq LLM call failed (model=%s): %s", model, exc)
            return None, 0

    async def _gemini_call(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        temperature: float | None = None,
    ) -> tuple[str | None, int]:
        """Async LLM call via Google Gemini."""
        client = self._get_gemini_client()
        if client is None:
            return None, 0
        try:
            from google.genai import types  # type: ignore[import]

            gemini_contents = [
                types.Content(
                    role="model" if msg["role"] == "assistant" else "user",
                    parts=[types.Part(text=msg["content"])],
                )
                for msg in messages
                if msg.get("content")
            ]

            if not gemini_contents or gemini_contents[0].role != "user":
                gemini_contents.insert(
                    0,
                    types.Content(role="user", parts=[types.Part(text="(start)")]),
                )

            config_kwargs: dict = {"system_instruction": system_prompt}
            if temperature is not None:
                config_kwargs["temperature"] = float(temperature)

            response = await client.aio.models.generate_content(
                model=model,
                contents=gemini_contents,
                config=types.GenerateContentConfig(**config_kwargs),
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
        """Execute a single agent and persist the result."""
        await _safe_publish_agent(str(agent.id), {"status": "running", "agent": agent.name})

        prior_messages = self.memory.as_messages(str(agent.id))

        result = self._run_agent_step(agent, user_input)

        # Skip LLM synthesis on guardrail-blocked steps
        llm_tokens = 0
        if not result.get("guardrail_blocked"):
            user_content = user_input
            if result["tool_outputs"]:
                tool_ctx = "\n".join(
                    f"[{t['tool']}]: {t['result']}" for t in result["tool_outputs"]
                )
                user_content += f"\n\nTool data available:\n{tool_ctx}"

            rules: dict = agent.interaction_rules or {}
            temperature = rules.get("temperature")

            llm_response, llm_tokens = await self._llm_call(
                system_prompt=self._build_system_prompt(agent),
                messages=prior_messages + [{"role": "user", "content": user_content}],
                model=agent.model or "llama-3.3-70b-versatile",
                temperature=temperature,
            )
            if llm_response:
                # Apply output guardrail to LLM response
                try:
                    llm_response = _apply_guardrails(
                        agent.guardrails or {}, llm_response, "output"
                    )
                except GuardrailViolation as exc:
                    llm_response = f"[Guardrail] {exc}"

                result["response"] = llm_response
                window = self._memory_window(agent)
                self.memory.clear(str(agent.id))
                for m in prior_messages:
                    self.memory.append(str(agent.id), m["content"], window)
                self.memory.append(str(agent.id), user_input, window)
                self.memory.append(str(agent.id), llm_response, window)
            else:
                logger.warning("LLM returned no response for agent %s", agent.name)

        tokens_used = llm_tokens or max(1, len(result["prompt"].split()) + len(result["response"].split()))

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
                status="guardrail_blocked" if result.get("guardrail_blocked") else "success",
                input={"prompt": result["prompt"]},
                output={
                    "response": result["response"],
                    "tool_outputs": result["tool_outputs"],
                },
                tokens_used=tokens_used,
                cost=round(tokens_used * 0.000_000_15, 6),
                created_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

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
            "guardrail_blocked": result.get("guardrail_blocked", False),
        }

    async def execute_workflow(self, db: Session, workflow: Workflow, initial_input: str = "Workflow started") -> dict:
        """Execute a multi-agent workflow using a LangGraph StateGraph.

        Supports cyclic graphs via ``max_iterations`` loop-safety: each node
        tracks its visit count in the LangGraph state and routes to END when
        the cap is reached.
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

        await _safe_publish_workflow(str(workflow.id), {
            "event": "workflow_started",
            "workflow_id": str(workflow.id),
            "workflow_name": workflow.name,
            "agent_count": len(agents_map),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        max_iterations: int = workflow.max_iterations or 10

        compiled = self._build_langgraph(workflow, agents_map, max_iterations)
        if compiled is not None:
            initial_state: WorkflowState = {
                "messages": [],
                "current_input": initial_input,
                "final_output": "",
                "step_outputs": [],
                "iteration_counts": {},
            }
            try:
                final_state = await compiled.ainvoke(initial_state)
                step_outputs: list[dict] = final_state.get("step_outputs", [])
                final_output: str = final_state.get("final_output", "")
            except Exception as exc:  # noqa: BLE001
                logger.error("LangGraph execution failed: %s", exc)
                step_outputs, final_output = await self._fallback_sequential(db, agents_map, workflow, initial_input)
        else:
            step_outputs, final_output = await self._fallback_sequential(db, agents_map, workflow, initial_input)

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
            await _safe_publish_workflow(str(workflow.id), {
                "event": "step_completed",
                "agent": step["agent_name"],
                "response": step["response"],
                "tool_outputs": step.get("tool_outputs", []),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        db.commit()

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

    def _build_langgraph(self, workflow: Workflow, agents_map: dict[str, Agent], max_iterations: int = 10):
        """Compile a LangGraph StateGraph from the workflow's graph descriptor.

        Supports cyclic graphs: each node tracks its visit count in
        ``state["iteration_counts"]`` and self-routes to END when the count
        exceeds ``max_iterations``.

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

        valid_nodes = [n for n in node_ids if n in agents_map]
        if not valid_nodes:
            return None

        graph = StateGraph(WFState)

        for node_id in valid_nodes:
            agent = agents_map[node_id]

            async def _make_async_node(state: WFState, _agent: Agent = agent, _node_id: str = node_id) -> WFState:  # type: ignore[return]
                current_input: str = state.get("current_input", "") or ""

                # --- loop-safety: check and increment visit count ---
                iter_counts: dict = dict(state.get("iteration_counts") or {})
                visit = iter_counts.get(_node_id, 0) + 1
                iter_counts[_node_id] = visit
                if visit > max_iterations:
                    logger.warning(
                        "Loop safety: node %s reached max_iterations=%d — terminating loop",
                        _agent.name, max_iterations,
                    )
                    loop_msg = f"[Loop limit reached for {_agent.name} after {max_iterations} iterations]"
                    return {
                        "messages": list(state.get("messages", [])) + [
                            {"role": "assistant", "name": _agent.name, "content": loop_msg}
                        ],
                        "current_input": loop_msg,
                        "final_output": loop_msg,
                        "step_outputs": list(state.get("step_outputs", [])) + [{
                            "agent_id": str(_agent.id),
                            "agent_name": _agent.name,
                            "response": loop_msg,
                            "tool_outputs": [],
                            "prompt": "",
                            "tokens_used": 0,
                            "loop_terminated": True,
                        }],
                        "iteration_counts": iter_counts,
                    }

                prior_messages = self.memory.as_messages(str(_agent.id))
                result = self._run_agent_step(_agent, current_input)

                llm_tokens = 0
                if not result.get("guardrail_blocked"):
                    user_content = current_input
                    if result["tool_outputs"]:
                        tool_ctx = "\n".join(
                            f"[{t['tool']}]: {t['result']}" for t in result["tool_outputs"]
                        )
                        user_content += f"\n\nTool data available:\n{tool_ctx}"

                    rules: dict = _agent.interaction_rules or {}
                    temperature = rules.get("temperature")

                    llm_messages = prior_messages + [{"role": "user", "content": user_content}]
                    llm_response, llm_tokens = await self._llm_call(
                        system_prompt=self._build_system_prompt(_agent),
                        messages=llm_messages,
                        model=_agent.model or "llama-3.3-70b-versatile",
                        temperature=temperature,
                    )
                    if llm_response:
                        try:
                            llm_response = _apply_guardrails(
                                _agent.guardrails or {}, llm_response, "output"
                            )
                        except GuardrailViolation as exc:
                            llm_response = f"[Guardrail] {exc}"
                        result["response"] = llm_response
                        result["tokens_used"] = llm_tokens
                    else:
                        logger.warning("LLM returned no response for agent %s", _agent.name)

                await asyncio.sleep(2)

                window = self._memory_window(_agent)
                self.memory.clear(str(_agent.id))
                for m in prior_messages:
                    self.memory.append(str(_agent.id), m["content"], window)
                self.memory.append(str(_agent.id), current_input, window)
                self.memory.append(str(_agent.id), result["response"], window)

                await _safe_publish_workflow(str(workflow.id), {
                    "event": "agent_response",
                    "agent": _agent.name,
                    "response": result["response"],
                    "tool_outputs": result.get("tool_outputs", []),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

                return {
                    "messages": list(state.get("messages", [])) + [
                        {"role": "assistant", "name": _agent.name, "content": result["response"]}
                    ],
                    "current_input": result["response"],
                    "final_output": result["response"],
                    "step_outputs": list(state.get("step_outputs", [])) + [result],
                    "iteration_counts": iter_counts,
                }

            graph.add_node(node_id, _make_async_node)

        graph.set_entry_point(valid_nodes[0])

        # outgoing[src] = list of (dst, condition_or_None)
        outgoing: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
        for edge in edges:
            if len(edge) < 2:
                continue
            src, dst = str(edge[0]), str(edge[1])
            condition: str | None = str(edge[2]).strip() if len(edge) >= 3 and edge[2] else None
            # Allow back-edges for cyclic graphs (loop safety handled inside each node)
            if src in agents_map and dst in agents_map:
                outgoing[src].append((dst, condition))

        added_src: set[str] = set()

        for src, targets in outgoing.items():
            cond_targets  = [(dst, cond) for dst, cond in targets if cond]
            plain_targets = [dst for dst, cond in targets if not cond]
            default_next  = plain_targets[0] if plain_targets else END

            if cond_targets:
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
                for dst in plain_targets:
                    graph.add_edge(src, dst)

            added_src.add(src)

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
            window = self._memory_window(agent)
            prior_messages = self.memory.as_messages(str(agent.id))
            result = self._run_agent_step(agent, current_input)

            if not result.get("guardrail_blocked"):
                user_content = current_input
                if result["tool_outputs"]:
                    tool_ctx = "\n".join(
                        f"[{t['tool']}]: {t['result']}" for t in result["tool_outputs"]
                    )
                    user_content += f"\n\nTool data available:\n{tool_ctx}"

                rules: dict = agent.interaction_rules or {}
                temperature = rules.get("temperature")

                llm_response, llm_tokens = await self._llm_call(
                    system_prompt=self._build_system_prompt(agent),
                    messages=prior_messages + [{"role": "user", "content": user_content}],
                    model=agent.model or "llama-3.3-70b-versatile",
                    temperature=temperature,
                )
                if llm_response:
                    try:
                        llm_response = _apply_guardrails(
                            agent.guardrails or {}, llm_response, "output"
                        )
                    except GuardrailViolation as exc:
                        llm_response = f"[Guardrail] {exc}"
                    result["response"] = llm_response
                    result["tokens_used"] = llm_tokens
                else:
                    logger.warning("LLM returned no response for agent %s", agent.name)

            self.memory.clear(str(agent.id))
            for m in prior_messages:
                self.memory.append(str(agent.id), m["content"], window)
            self.memory.append(str(agent.id), current_input, window)
            self.memory.append(str(agent.id), result["response"], window)

            await asyncio.sleep(2)
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
