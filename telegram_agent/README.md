# Telegram Windows Desktop Agent (MVP)

This project adds a Windows desktop automation agent controlled via Telegram. It **only** accepts messages from configured user/chat IDs, and runs allow-listed tools with full audit screenshots + logs.

## Features (MVP)
- `/help`, `/status`, `/shot`
- `/do <task>`: generates a JSON plan, requires `/approve <task_id>` before execution
- `/cancel <task_id>`
- Serial task queue backed by SQLite
- UI automation via `pywinauto` (UIA backend)
- Coordinate fallback via `pyautogui` only when explicitly requested in a step
- Auditing: before/after screenshots and log lines per step

## Safety & Scope
- Only configured `ALLOWED_USER_IDS` and `ALLOWED_CHAT_IDS` can use the bot.
- Actions must be registered in the allow-list tool registry. Unknown tools are rejected.
- No stealth monitoring, keylogging, persistence, or bypassing system security.

## BotFather setup
1. Create a bot with BotFather.
2. Copy the API token and set `BOT_TOKEN` in `.env`.
3. Find your Telegram user ID and chat ID (e.g., via `@userinfobot`) and set them in `.env`.

## Configuration
Copy `.env.example` to `.env` and edit values.

```
BOT_TOKEN=123456:ABCDEF
ALLOWED_USER_IDS=123456789
ALLOWED_CHAT_IDS=123456789
SQLITE_PATH=telegram_agent/app/agent.sqlite
AUDIT_DIR=telegram_agent/app/audit
TASK_TIMEOUT_SECONDS=300
POLL_INTERVAL_SECONDS=2
```

## Install (Windows)
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r telegram_agent/requirements.txt
```

## Run
```bash
python -m telegram_agent.app.bot
```

## Windows DPI / multi-monitor notes
- Ensure Windows display scaling is consistent; mismatched DPI scaling can skew click coordinates.
- Multi-monitor setups may require additional handling; this MVP uses the virtual screen (`mss` monitor 0).

## Task planning notes
The current MVP planner supports simple patterns:
- `click_text <text>` (UIA-first, fuzzy match)
- `click_uia <automation_id>`
- `click_path <path>`
- `click <x> <y>` (coordinate fallback)
- `type <text>`

Example:
```
/do click_text 地址栏 then type hello
```

Example with hotkey:
```
/do click_text 地址栏 then type hello then hotkey enter
```

The bot will always include screenshots before and after execution. UIA actions (click_text/uia tools) are preferred; coordinate clicks are only a fallback.
