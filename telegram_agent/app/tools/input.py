from __future__ import annotations

import time

import pyautogui


def click(x: int, y: int) -> None:
    pyautogui.click(x=x, y=y)
    time.sleep(0.2)


def type_text(text: str) -> None:
    pyautogui.typewrite(text, interval=0.02)
    time.sleep(0.2)
