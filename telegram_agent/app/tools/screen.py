from __future__ import annotations

import os
import time
from pathlib import Path

import mss
import mss.tools


def capture_screen(audit_dir: str, task_id: str, label: str) -> str:
    Path(audit_dir).mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{task_id}_{label}_{timestamp}.png"
    path = os.path.join(audit_dir, filename)

    with mss.mss() as sct:
        monitor = sct.monitors[0]
        screenshot = sct.grab(monitor)
        mss.tools.to_png(screenshot.rgb, screenshot.size, output=path)

    return path
