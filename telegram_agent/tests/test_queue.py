from __future__ import annotations

import tempfile

from telegram_agent.app.queue import TaskQueue


def test_task_lifecycle() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = f"{tmpdir}/tasks.sqlite"
        queue = TaskQueue(db_path)
        task_id = queue.create_task(1, 2, "do something", "{}", 10)
        task = queue.get_task(task_id)
        assert task is not None
        assert task.status == "pending_approval"

        assert queue.approve_task(task_id)
        task = queue.get_task(task_id)
        assert task.status == "queued"

        queued = queue.next_queued()
        assert queued is not None
        assert queued.task_id == task_id

        assert queue.mark_running(task_id)
        task = queue.get_task(task_id)
        assert task.status == "running"

        assert queue.cancel_task(task_id)
        task = queue.get_task(task_id)
        assert task.status == "cancelled"
