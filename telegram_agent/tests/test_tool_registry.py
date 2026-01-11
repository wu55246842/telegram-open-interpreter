from __future__ import annotations

from telegram_agent.app.executor import ToolRegistry


def test_tool_registry_allows_registered_tool() -> None:
    registry = ToolRegistry()

    def dummy() -> str:
        return "ok"

    registry.register("dummy", dummy)
    assert registry.get("dummy") is dummy
    assert registry.get("missing") is None
