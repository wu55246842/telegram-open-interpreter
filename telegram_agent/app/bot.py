from __future__ import annotations

import asyncio
import json
from pathlib import Path

from loguru import logger
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from telegram_agent.app.auth import is_authorized
from telegram_agent.app.executor import TaskExecutor, default_tool_registry
from telegram_agent.app.planner import create_plan
from telegram_agent.app.queue import TaskQueue
from telegram_agent.app.settings import Settings


async def _reject(update: Update, reason: str) -> None:
    if update.effective_chat:
        await update.effective_chat.send_message(text=f"Unauthorized: {reason}")


def _ensure_audit_dir(settings: Settings) -> None:
    Path(settings.audit_dir).mkdir(parents=True, exist_ok=True)


def _format_plan(plan_json: str) -> str:
    payload = json.loads(plan_json)
    lines = [f"Task: {payload['task']}"]
    for step in payload["steps"]:
        lines.append(f"{step['id']}. {step['action']} {step.get('args', {})}")
    return "\n".join(lines)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    auth = is_authorized(update, settings)
    if not auth.ok:
        await _reject(update, auth.reason)
        return

    message = (
        "/help - show this message\n"
        "/status - list recent tasks\n"
        "/shot - capture a screenshot\n"
        "/do <task> - plan a task\n"
        "/approve <task_id> - approve a planned task\n"
        "/cancel <task_id> - cancel a task"
    )
    await update.effective_chat.send_message(text=message)


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    auth = is_authorized(update, settings)
    if not auth.ok:
        await _reject(update, auth.reason)
        return

    queue: TaskQueue = context.bot_data["queue"]
    tasks = queue.list_recent()
    if not tasks:
        await update.effective_chat.send_message(text="No tasks yet.")
        return

    lines = [f"{task.task_id} - {task.status} - {task.command}" for task in tasks]
    await update.effective_chat.send_message(text="\n".join(lines))


async def shot_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    auth = is_authorized(update, settings)
    if not auth.ok:
        await _reject(update, auth.reason)
        return

    executor: TaskExecutor = context.bot_data["executor"]
    path = executor.tool_registry.get("screen.capture")(settings.audit_dir, "manual", "shot")
    with open(path, "rb") as photo:
        await update.effective_chat.send_photo(photo=photo, caption="Screenshot")


async def do_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    auth = is_authorized(update, settings)
    if not auth.ok:
        await _reject(update, auth.reason)
        return

    if not context.args:
        await update.effective_chat.send_message(text="Usage: /do <task>")
        return

    task_text = " ".join(context.args)
    plan = create_plan(task_text)
    queue: TaskQueue = context.bot_data["queue"]
    task_id = queue.create_task(
        chat_id=update.effective_chat.id,
        user_id=update.effective_user.id,
        command=task_text,
        plan_json=plan.to_json(),
        timeout_seconds=settings.task_timeout_seconds,
    )

    await update.effective_chat.send_message(
        text=f"Plan created for task_id={task_id}. Use /approve {task_id} to execute.\n{_format_plan(plan.to_json())}"
    )


async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    auth = is_authorized(update, settings)
    if not auth.ok:
        await _reject(update, auth.reason)
        return

    if not context.args:
        await update.effective_chat.send_message(text="Usage: /approve <task_id>")
        return

    task_id = context.args[0]
    queue: TaskQueue = context.bot_data["queue"]
    if queue.approve_task(task_id):
        await update.effective_chat.send_message(text=f"Task {task_id} approved and queued.")
    else:
        await update.effective_chat.send_message(text=f"Task {task_id} not found or not pending approval.")


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    auth = is_authorized(update, settings)
    if not auth.ok:
        await _reject(update, auth.reason)
        return

    if not context.args:
        await update.effective_chat.send_message(text="Usage: /cancel <task_id>")
        return

    task_id = context.args[0]
    queue: TaskQueue = context.bot_data["queue"]
    if queue.cancel_task(task_id):
        await update.effective_chat.send_message(text=f"Task {task_id} cancelled.")
    else:
        await update.effective_chat.send_message(text=f"Task {task_id} not found.")


async def _run_next_task(context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    queue: TaskQueue = context.bot_data["queue"]
    executor: TaskExecutor = context.bot_data["executor"]

    task = queue.next_queued()
    if task is None:
        return

    if not queue.mark_running(task.task_id):
        return

    bot = context.bot
    def cancel_check() -> bool:
        current = queue.get_task(task.task_id)
        return current is not None and current.status == "cancelled"

    def send_update(message: str) -> None:
        asyncio.run_coroutine_threadsafe(bot.send_message(chat_id=task.chat_id, text=message), context.application.loop)

    def send_photo(path: str) -> None:
        with open(path, "rb") as photo:
            asyncio.run_coroutine_threadsafe(bot.send_photo(chat_id=task.chat_id, photo=photo), context.application.loop)

    try:
        result = await asyncio.to_thread(
            executor.execute_plan,
            task.task_id,
            task.plan_json,
            send_update,
            send_photo,
            cancel_check,
            task.timeout_seconds,
        )
        queue.mark_done(task.task_id, result)
        await bot.send_message(chat_id=task.chat_id, text=f"Task {task.task_id} completed.")
    except Exception as exc:  # noqa: BLE001
        logger.exception("Task failed")
        queue.mark_failed(task.task_id, str(exc))
        await bot.send_message(chat_id=task.chat_id, text=f"Task {task.task_id} failed: {exc}")


async def main() -> None:
    settings = Settings()
    _ensure_audit_dir(settings)

    queue = TaskQueue(settings.sqlite_path)
    registry = default_tool_registry()
    executor = TaskExecutor(settings.audit_dir, registry)

    application = ApplicationBuilder().token(settings.bot_token).build()
    application.bot_data["settings"] = settings
    application.bot_data["queue"] = queue
    application.bot_data["executor"] = executor

    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("shot", shot_command))
    application.add_handler(CommandHandler("do", do_command))
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(CommandHandler("cancel", cancel_command))

    application.job_queue.run_repeating(_run_next_task, interval=settings.poll_interval_seconds, first=2)

    await application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
