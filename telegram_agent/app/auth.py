from __future__ import annotations

from dataclasses import dataclass

from telegram import Update

from telegram_agent.app.settings import Settings


@dataclass(frozen=True)
class AuthResult:
    ok: bool
    reason: str


def is_authorized(update: Update, settings: Settings) -> AuthResult:
    if update.effective_user is None or update.effective_chat is None:
        return AuthResult(False, "missing user or chat")

    user_id = update.effective_user.id
    chat_id = update.effective_chat.id

    if user_id not in settings.allowed_users():
        return AuthResult(False, "user not allowed")

    if chat_id not in settings.allowed_chats():
        return AuthResult(False, "chat not allowed")

    return AuthResult(True, "ok")
