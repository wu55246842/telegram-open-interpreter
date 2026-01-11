from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class Plan:
    task: str
    steps: list[dict[str, Any]]

    def to_json(self) -> str:
        return json.dumps({"task": self.task, "steps": self.steps}, ensure_ascii=False)


def _parse_click(task: str) -> tuple[int, int] | None:
    match = re.search(r"click\s+(\d+)\s+(\d+)", task, re.IGNORECASE)
    if match:
        return int(match.group(1)), int(match.group(2))
    return None


def _parse_type(task: str) -> str | None:
    match = re.search(r"type\s+(.+)", task, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def create_plan(task: str) -> Plan:
    steps: list[dict[str, Any]] = [
        {
            "id": 1,
            "action": "screen.capture",
            "args": {"label": "before"},
        },
        {
            "id": 2,
            "action": "log.note",
            "args": {"message": f"Requested task: {task}"},
        },
    ]

    click = _parse_click(task)
    if click:
        steps.append(
            {
                "id": len(steps) + 1,
                "action": "input.click",
                "args": {"x": click[0], "y": click[1]},
            }
        )

    text = _parse_type(task)
    if text:
        steps.append(
            {
                "id": len(steps) + 1,
                "action": "input.type",
                "args": {"text": text},
            }
        )

    steps.append(
        {
            "id": len(steps) + 1,
            "action": "screen.capture",
            "args": {"label": "after"},
        }
    )

    return Plan(task=task, steps=steps)
