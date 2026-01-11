from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bot_token: str = Field(alias="BOT_TOKEN")
    allowed_user_ids: str = Field(alias="ALLOWED_USER_IDS")
    allowed_chat_ids: str = Field(alias="ALLOWED_CHAT_IDS")
    sqlite_path: str = Field(default="telegram_agent/app/agent.sqlite", alias="SQLITE_PATH")
    audit_dir: str = Field(default="telegram_agent/app/audit", alias="AUDIT_DIR")
    task_timeout_seconds: int = Field(default=300, alias="TASK_TIMEOUT_SECONDS")
    poll_interval_seconds: float = Field(default=2.0, alias="POLL_INTERVAL_SECONDS")

    def allowed_users(self) -> set[int]:
        return {int(value.strip()) for value in self.allowed_user_ids.split(",") if value.strip()}

    def allowed_chats(self) -> set[int]:
        return {int(value.strip()) for value in self.allowed_chat_ids.split(",") if value.strip()}
