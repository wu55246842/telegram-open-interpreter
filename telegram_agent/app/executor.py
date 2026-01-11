from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from loguru import logger

from telegram_agent.app.tools import input as input_tools
from telegram_agent.app.tools import screen as screen_tools
from telegram_agent.app.tools import uia as uia_tools


ToolFunc = Callable[..., Any]


@dataclass
class ToolRegistry:
    tools: dict[str, ToolFunc] = field(default_factory=dict)

    def register(self, name: str, func: ToolFunc) -> None:
        self.tools[name] = func

    def get(self, name: str) -> ToolFunc | None:
        return self.tools.get(name)


@dataclass
class ExecutionStep:
    step_id: int
    action: str
    args: dict[str, Any]


class TaskExecutor:
    def __init__(self, audit_dir: str, tool_registry: ToolRegistry) -> None:
        self.audit_dir = audit_dir
        self.tool_registry = tool_registry

    def execute_plan(
        self,
        task_id: str,
        plan_json: str,
        send_update: Callable[[str], None],
        send_photo: Callable[[str], None],
        cancel_check: Callable[[], bool],
        timeout_seconds: int,
    ) -> dict[str, Any]:
        log_id = logger.add(f"{self.audit_dir}/{task_id}.log", rotation="1 MB")
        payload = json.loads(plan_json)
        steps = [ExecutionStep(step["id"], step["action"], step.get("args", {})) for step in payload["steps"]]
        started_at = time.monotonic()
        results: list[dict[str, Any]] = []

        try:
            for step in steps:
                if cancel_check():
                    raise RuntimeError("Task cancelled")

                if time.monotonic() - started_at > timeout_seconds:
                    raise RuntimeError("Task timeout reached")

                tool = self.tool_registry.get(step.action)
                if tool is None:
                    raise RuntimeError(f"Tool not allowed: {step.action}")

                send_update(f"Executing step {step.step_id}: {step.action}")
                logger.info("Executing step {} with args {}", step.action, step.args)

                result: dict[str, Any] = {"step": step.step_id, "action": step.action}
                if step.action == "screen.capture":
                    path = tool(self.audit_dir, task_id, step.args.get("label", "step"))
                    result["screenshot"] = path
                    send_photo(path)
                elif step.action == "input.click":
                    tool(step.args["x"], step.args["y"])
                elif step.action == "input.type":
                    tool(step.args["text"])
                elif step.action == "uia.focus_window":
                    result["focused"] = tool(step.args["title_substring"])
                elif step.action in {"uia.click_text", "uia.click_automation_id", "uia.click_path"}:
                    self._execute_with_error_screenshot(step.action, tool, step.args, task_id, send_photo)
                elif step.action == "log.note":
                    logger.info("NOTE: {}", step.args.get("message", ""))
                else:
                    tool(**step.args)

                results.append(result)
        finally:
            logger.remove(log_id)

        return {"task": payload["task"], "steps": results}

    def _execute_with_error_screenshot(
        self,
        action: str,
        func: ToolFunc,
        args: dict[str, Any],
        task_id: str,
        send_photo: Callable[[str], None],
    ) -> None:
        try:
            func(**args)
        except Exception as exc:  # noqa: BLE001
            path = screen_tools.capture_screen(self.audit_dir, task_id, "error")
            send_photo(path)
            raise RuntimeError(f"{action} failed: {exc}") from exc


def default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register("screen.capture", screen_tools.capture_screen)
    registry.register("input.click", input_tools.click)
    registry.register("input.type", input_tools.type_text)
    registry.register("uia.focus_window", uia_tools.focus_window)
    registry.register("uia.dump", uia_tools.dump)
    registry.register("uia.click_text", uia_tools.click_text)
    registry.register("uia.click_automation_id", uia_tools.click_automation_id)
    registry.register("uia.click_path", uia_tools.click_path)
    registry.register("log.note", lambda message: logger.info("NOTE: {}", message))
    return registry
