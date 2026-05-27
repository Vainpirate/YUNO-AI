from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from app.models import Agent

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_agent_prompt(agent: Agent, user_input: str, memory: list[str]) -> str:
    """Assemble the full text prompt shown to an LLM for this agent turn.

    The prompt includes the agent's system instructions, recent conversation
    history (last 10 messages) and the current user input.
    """
    system_prompt = (agent.system_prompt or "").strip()
    recent = "\n".join(memory[-10:])
    parts = [system_prompt]
    if recent:
        parts.append(f"Conversation history:\n{recent}")
    parts.append(f"Input:\n{user_input}")
    return "\n\n".join(p for p in parts if p)


# ---------------------------------------------------------------------------
# LangGraph node factory
# ---------------------------------------------------------------------------

def make_agent_node(agent: Agent, run_step: Callable[[Agent, str], dict]) -> Callable[[dict[str, Any]], dict[str, Any]]:
    """Return a synchronous LangGraph node function for *agent*.

    The node reads ``state["current_input"]``, executes the agent via
    *run_step*, then returns updated state slices consumed by downstream nodes.

    Parameters
    ----------
    agent:
        The ORM Agent instance whose config drives this node.
    run_step:
        A callable ``(agent, user_input) -> result_dict`` — typically
        ``RuntimeExecutor._run_agent_step``.  Kept as a parameter so the
        factory itself has no dependency on the executor module, avoiding
        circular imports.
    """

    def node_fn(state: dict[str, Any]) -> dict[str, Any]:
        current_input: str = state.get("current_input", "")
        result = run_step(agent, current_input)

        updated_messages = list(state.get("messages", [])) + [
            {
                "role": "assistant",
                "name": agent.name,
                "content": result["response"],
            }
        ]
        updated_steps = list(state.get("step_outputs", [])) + [result]

        return {
            "messages": updated_messages,
            "current_input": result["response"],
            "final_output": result["response"],
            "step_outputs": updated_steps,
        }

    # Attach metadata for debugging / log enrichment
    node_fn.__name__ = f"node_{agent.name.replace(' ', '_').lower()}"
    return node_fn
