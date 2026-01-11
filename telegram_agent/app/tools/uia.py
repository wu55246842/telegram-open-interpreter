from __future__ import annotations

import time
from difflib import SequenceMatcher

from pywinauto import Desktop
from pywinauto.base_wrapper import BaseWrapper

DEFAULT_MAX_DUMP_NODES = 200


def _rect_payload(wrapper: BaseWrapper) -> dict[str, int]:
    rect = wrapper.rectangle()
    return {
        "left": rect.left,
        "top": rect.top,
        "right": rect.right,
        "bottom": rect.bottom,
        "width": rect.width(),
        "height": rect.height(),
    }


def _node_payload(wrapper: BaseWrapper) -> dict[str, object]:
    return {
        "name": wrapper.window_text(),
        "control_type": wrapper.element_info.control_type,
        "automation_id": wrapper.element_info.automation_id,
        "rect": _rect_payload(wrapper),
        "enabled": wrapper.is_enabled(),
        "visible": wrapper.is_visible(),
    }


def _resolve_window(window_title_substring: str | None) -> BaseWrapper:
    desktop = Desktop(backend="uia")
    if window_title_substring:
        target = window_title_substring.lower()
        for window in desktop.windows():
            if target in window.window_text().lower():
                return window
        raise RuntimeError(f"Unable to find window with title containing '{window_title_substring}'")
    return desktop.get_active()


def dump(window_title_substring: str | None = None, max_items: int = DEFAULT_MAX_DUMP_NODES) -> list[dict[str, object]]:
    window = _resolve_window(window_title_substring)
    results: list[dict[str, object]] = []

    def walk(wrapper: BaseWrapper) -> None:
        if len(results) >= max_items:
            return
        results.append(_node_payload(wrapper))
        for child in wrapper.children():
            walk(child)
            if len(results) >= max_items:
                return

    walk(window)
    return results


def focus_window(title_substring: str) -> bool:
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        if title_substring.lower() in window.window_text().lower():
            window.set_focus()
            return True
    return False


def _find_candidates(window: BaseWrapper, control_type: str | None = None) -> list[BaseWrapper]:
    if control_type:
        return window.descendants(control_type=control_type)
    return window.descendants()


def _best_text_match(window: BaseWrapper, text: str, control_type: str | None) -> BaseWrapper | None:
    text_lower = text.lower()
    best_score = 0.0
    best = None

    for candidate in _find_candidates(window, control_type):
        name = candidate.window_text() or ""
        if not name:
            continue
        name_lower = name.lower()
        score = 0.0
        if text_lower in name_lower:
            score = 1.0
        else:
            score = SequenceMatcher(None, text_lower, name_lower).ratio()
        if score > best_score:
            best_score = score
            best = candidate

    if best_score < 0.4:
        return None
    return best


def click_text(
    text: str,
    window_title_substring: str | None = None,
    control_type: str | None = None,
    timeout_seconds: int = 5,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout_seconds
    candidate = None
    while time.monotonic() <= deadline:
        try:
            window = _resolve_window(window_title_substring)
        except RuntimeError:
            time.sleep(0.2)
            continue
        candidate = _best_text_match(window, text, control_type)
        if candidate is not None:
            break
        time.sleep(0.2)

    if candidate is None:
        message = f"Unable to find UIA element matching text '{text}'"
        if control_type:
            message += f" with control_type '{control_type}'"
        if window_title_substring:
            message += f" in window containing '{window_title_substring}'"
        raise RuntimeError(message)
    candidate.click_input()
    return _node_payload(candidate)


def click_automation_id(automation_id: str) -> None:
    window = Desktop(backend="uia").get_active()
    matches = window.descendants(automation_id=automation_id)
    if not matches:
        raise RuntimeError(f"Unable to find UIA element with automation_id '{automation_id}'")
    matches[0].click_input()


def click_path(path: str) -> None:
    window = Desktop(backend="uia").get_active()
    parts = [part for part in path.split("/") if part and part.lower() != "root"]
    node: BaseWrapper = window
    for part in parts:
        try:
            index = int(part)
        except ValueError as exc:
            raise RuntimeError(f"Invalid UIA path segment '{part}'") from exc
        children = node.children()
        if index < 0 or index >= len(children):
            raise RuntimeError(f"UIA path '{path}' is out of range at segment '{part}'")
        node = children[index]
    node.click_input()
