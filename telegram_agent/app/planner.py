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


def _parse_click_text(task: str) -> tuple[str, str | None] | None:
    match = re.search(r"click_text\s+(.+?)(?:\s+then\b|$)", task, re.IGNORECASE)
    if not match:
        return None
    text = match.group(1).strip()
    control_match = re.search(r"\bcontrol_type\s*=\s*([\\w ]+)$", text, re.IGNORECASE)
    control_type = None
    if control_match:
        control_type = control_match.group(1).strip()
        text = re.sub(r"\bcontrol_type\s*=\s*[\\w ]+$", "", text, flags=re.IGNORECASE).strip()
    return text, control_type


def _parse_click_uia(task: str) -> str | None:
    match = re.search(r"click_uia\s+(.+?)(?:\s+then\b|$)", task, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def _parse_click_path(task: str) -> str | None:
    match = re.search(r"click_path\s+(.+?)(?:\s+then\b|$)", task, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


def create_plan(task: str, observation: dict[str, Any] | None = None) -> Plan:
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
    if observation:
        steps.append(
            {
                "id": len(steps) + 1,
                "action": "log.note",
                "args": {"message": f"Observation summary: {json.dumps(observation, ensure_ascii=False)}"},
            }
        )

    click_text = _parse_click_text(task)
    if click_text:
        args = {"text": click_text[0]}
        if click_text[1]:
            args["control_type"] = click_text[1]
        steps.append(
            {
                "id": len(steps) + 1,
                "action": "uia.click_text",
                "args": args,
            }
        )
    else:
        click_uia = _parse_click_uia(task)
        if click_uia:
            steps.append(
                {
                    "id": len(steps) + 1,
                    "action": "uia.click_automation_id",
                    "args": {"automation_id": click_uia},
                }
            )
        else:
            click_path = _parse_click_path(task)
            if click_path:
                steps.append(
                    {
                        "id": len(steps) + 1,
                        "action": "uia.click_path",
                        "args": {"path": click_path},
                    }
                )
            else:
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
