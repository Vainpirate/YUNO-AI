from __future__ import annotations

import ast
import operator
from typing import Any, Callable

import httpx


class ToolRegistry:
    """Registry of callable tools available to agents.

    Tools are keyed by name and exposed as simple string-in / string-out
    functions so they can be called uniformly by the executor regardless of
    the underlying implementation.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Callable[[str], str]] = {
            "calculator": self._calculator,
            "web_search": self._web_search,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def has_tool(self, name: str) -> bool:
        return name in self._tools

    def execute(self, name: str, payload: str) -> str:
        if name not in self._tools:
            raise ValueError(f"Unknown tool: {name}")
        return self._tools[name](payload)

    def list_tools(self) -> list[str]:
        return sorted(self._tools.keys())

    # ------------------------------------------------------------------
    # Tool implementations
    # ------------------------------------------------------------------

    def _web_search(self, query: str) -> str:
        """Query DuckDuckGo Instant Answers API (no key required).

        Falls back gracefully on network errors so agents are never blocked.
        """
        try:
            with httpx.Client(timeout=10, follow_redirects=True) as client:
                resp = client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": "1",
                        "skip_disambig": "1",
                    },
                    headers={"User-Agent": "Mozilla/5.0 (compatible; YunoAgentBot/1.0)"},
                )
                resp.raise_for_status()
                data = resp.json()

            parts: list[str] = []
            if data.get("AbstractText"):
                parts.append(data["AbstractText"])
            for topic in data.get("RelatedTopics", [])[:4]:
                if isinstance(topic, dict) and topic.get("Text"):
                    parts.append(topic["Text"])

            return "\n".join(parts) if parts else f"[web_search] No instant results found for: {query}"
        except Exception as exc:  # noqa: BLE001
            return f"[web_search] Error reaching search API: {exc}"

    def _calculator(self, expression: str) -> str:
        """Safely evaluate a mathematical expression using Python AST."""
        try:
            node = ast.parse(expression.strip(), mode="eval").body
            result = self._eval_ast(node)
            # Return int-like floats without decimal point for cleaner output
            if isinstance(result, float) and result.is_integer():
                return str(int(result))
            return str(result)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Cannot evaluate '{expression}': {exc}") from exc

    def _eval_ast(self, node: ast.AST) -> Any:
        _ops: dict[type, Any] = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.FloorDiv: operator.floordiv,
            ast.USub: operator.neg,
            ast.UAdd: operator.pos,
        }
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _ops:
            return _ops[type(node.op)](self._eval_ast(node.left), self._eval_ast(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _ops:
            return _ops[type(node.op)](self._eval_ast(node.operand))
        raise ValueError(f"Unsupported AST node: {type(node).__name__}")
