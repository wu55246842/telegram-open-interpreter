from __future__ import annotations

import json
import time
import traceback
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

                send_update(f"Executing step {step.step_id}: {step.action}")
                logger.info("Executing step {} with args {}", step.action, step.args)

                result: dict[str, Any] = {
                    "step": step.step_id,
                    "action": step.action,
                    "args": step.args,
                    "ok": False,
                }
                try:
                    tool = self.tool_registry.get(step.action)
                    if tool is None:
                        raise RuntimeError(f"Tool not allowed: {step.action}")

                    if step.action == "screen.capture":
                        label = step.args.get("label", "step")
                        path = screen_tools.capture_screen(self.audit_dir, task_id, label=label)
                        send_photo(path)
                        result["output"] = path
                    else:
                        output = tool(**step.args)
                        if output is not None:
                            result["output"] = output
                    result["ok"] = True
                except Exception as exc:  # noqa: BLE001
                    result["error"] = {
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "traceback": traceback.format_exc(),
                    }
                    self._capture_error_screenshot(task_id, step.step_id, send_photo)
                    results.append(result)
                    raise RuntimeError(f"{step.action} failed: {exc}") from exc

                results.append(result)
        finally:
            logger.remove(log_id)

        return {"task": payload["task"], "steps": results}

    def _capture_error_screenshot(
        self,
        task_id: str,
        step_id: int,
        send_photo: Callable[[str], None],
    ) -> None:
        label = f"error_step_{step_id}"
        try:
            path = screen_tools.capture_screen(self.audit_dir, task_id, label=label)
        except Exception:  # noqa: BLE001
            logger.exception("Failed to capture error screenshot for step {}", step_id)
            return
        send_photo(path)


def log_note(message: str) -> None:
    logger.info("NOTE: {}", message)


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
    registry.register("log.note", log_note)
    return registry
