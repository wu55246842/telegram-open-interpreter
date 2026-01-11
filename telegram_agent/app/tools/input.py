from __future__ import annotations

import time

import pyautogui


def _ensure_in_bounds(x: int, y: int, bounds: list[int]) -> None:
    if len(bounds) != 4:
        raise ValueError("bounds must be [left, top, right, bottom]")
    left, top, right, bottom = bounds
    if not (left <= x <= right and top <= y <= bottom):
        raise ValueError(f"click ({x}, {y}) outside bounds {bounds}")


def click(x: int, y: int, bounds: list[int] | None = None) -> None:
    if bounds is not None:
        _ensure_in_bounds(x, y, bounds)
    pyautogui.click(x=x, y=y)
    time.sleep(0.2)


def type_text(text: str) -> None:
    pyautogui.typewrite(text, interval=0.02)
    time.sleep(0.2)


def hotkey(keys: str) -> None:
    parts = [part.strip().lower() for part in keys.split("+") if part.strip()]
    if not parts:
        raise ValueError("keys must not be empty")
    pyautogui.hotkey(*parts)
    time.sleep(0.2)


def sleep(seconds: float) -> None:
    if seconds < 0:
        raise ValueError("seconds must be non-negative")
    if seconds > 30:
        raise ValueError("seconds must be <= 30")
    time.sleep(seconds)
