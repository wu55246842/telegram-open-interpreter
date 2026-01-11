from __future__ import annotations

from dataclasses import dataclass

from telegram_agent.app.auth import is_authorized
from telegram_agent.app.settings import Settings


@dataclass
class DummyUser:
    id: int


@dataclass
class DummyChat:
    id: int


@dataclass
class DummyUpdate:
    effective_user: DummyUser | None
    effective_chat: DummyChat | None


def test_authorized_user_and_chat() -> None:
    settings = Settings(
        BOT_TOKEN="token",
        ALLOWED_USER_IDS="1,2",
        ALLOWED_CHAT_IDS="10,20",
    )
    update = DummyUpdate(DummyUser(1), DummyChat(10))
    result = is_authorized(update, settings)
    assert result.ok


def test_rejects_unlisted_user() -> None:
    settings = Settings(
        BOT_TOKEN="token",
        ALLOWED_USER_IDS="1",
        ALLOWED_CHAT_IDS="10",
    )
    update = DummyUpdate(DummyUser(2), DummyChat(10))
    result = is_authorized(update, settings)
    assert not result.ok
