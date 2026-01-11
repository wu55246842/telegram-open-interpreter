from __future__ import annotations

from pywinauto import Desktop


def focus_window(title_substring: str) -> bool:
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        if title_substring.lower() in window.window_text().lower():
            window.set_focus()
            return True
    return False
