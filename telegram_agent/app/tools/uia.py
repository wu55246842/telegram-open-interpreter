from __future__ import annotations

from difflib import SequenceMatcher

from pywinauto import Desktop
from pywinauto.base_wrapper import BaseWrapper

MAX_DUMP_NODES = 200


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


def _node_payload(wrapper: BaseWrapper, path: str) -> dict[str, object]:
    return {
        "name": wrapper.window_text(),
        "control_type": wrapper.element_info.control_type,
        "automation_id": wrapper.element_info.automation_id,
        "rect": _rect_payload(wrapper),
        "path": path,
        "is_enabled": wrapper.is_enabled(),
        "is_visible": wrapper.is_visible(),
    }


def dump() -> list[dict[str, object]]:
    desktop = Desktop(backend="uia")
    window = desktop.get_active()
    results: list[dict[str, object]] = []

    def walk(wrapper: BaseWrapper, path: str) -> None:
        if len(results) >= MAX_DUMP_NODES:
            return
        results.append(_node_payload(wrapper, path))
        for index, child in enumerate(wrapper.children()):
            walk(child, f"{path}/{index}")
            if len(results) >= MAX_DUMP_NODES:
                return

    walk(window, "root")
    return results


def focus_window(title_substring: str) -> bool:
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        if title_substring.lower() in window.window_text().lower():
            window.set_focus()
            return True
    return False


def _find_candidates(control_type: str | None = None) -> list[BaseWrapper]:
    window = Desktop(backend="uia").get_active()
    if control_type:
        return window.descendants(control_type=control_type)
    return window.descendants()


def _best_text_match(text: str, control_type: str | None) -> BaseWrapper | None:
    text_lower = text.lower()
    best_score = 0.0
    best = None

    for candidate in _find_candidates(control_type):
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


def click_text(text: str, control_type: str | None = None) -> None:
    candidate = _best_text_match(text, control_type)
    if candidate is None:
        message = f"Unable to find UIA element matching text '{text}'"
        if control_type:
            message += f" with control_type '{control_type}'"
        raise RuntimeError(message)
    candidate.click_input()


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
