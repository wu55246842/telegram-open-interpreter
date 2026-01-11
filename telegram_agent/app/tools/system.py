from __future__ import annotations

import ctypes
from typing import Any

import mss
import psutil
from pywinauto import Desktop


def active_window() -> dict[str, Any]:
    try:
        window = Desktop(backend="uia").get_active()
    except Exception:
        return {"title": "", "process": {}, "rect": {}}

    title = window.window_text()
    pid = window.process_id()
    process_name = ""
    try:
        process_name = psutil.Process(pid).name()
    except Exception:
        process_name = ""

    rect = window.rectangle()
    rect_payload = {
        "left": rect.left,
        "top": rect.top,
        "right": rect.right,
        "bottom": rect.bottom,
        "width": rect.width(),
        "height": rect.height(),
    }

    return {"title": title, "process": {"pid": pid, "name": process_name}, "rect": rect_payload}


def _system_dpi_scale() -> float:
    dpi = 96
    try:
        dpi = ctypes.windll.user32.GetDpiForSystem()  # type: ignore[attr-defined]
    except Exception:
        dpi = 96
    return round(dpi / 96, 2)


def display_info() -> dict[str, Any]:
    with mss.mss() as sct:
        monitors = sct.monitors

    monitor_payloads = []
    for monitor in monitors[1:]:
        monitor_payloads.append(
            {
                "left": monitor["left"],
                "top": monitor["top"],
                "width": monitor["width"],
                "height": monitor["height"],
            }
        )

    virtual = monitors[0]
    virtual_screen_rect = {
        "left": virtual["left"],
        "top": virtual["top"],
        "width": virtual["width"],
        "height": virtual["height"],
    }

    return {
        "monitors": monitor_payloads,
        "virtual_screen_rect": virtual_screen_rect,
        "dpi_scale": _system_dpi_scale(),
    }
