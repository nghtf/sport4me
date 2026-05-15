from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

PROXY_ENV_NAMES = ("HTTP_PROXY_URL",)


@dataclass(frozen=True)
class Settings:
    bot_token: str
    database_url: str
    telegram_proxy_url: str | None


def load_settings() -> Settings:
    load_dotenv()

    bot_token = os.getenv("BOT_TOKEN", "").strip()
    if not bot_token:
        raise RuntimeError("BOT_TOKEN is required")

    return Settings(
        bot_token=bot_token,
        database_url=os.getenv("DATABASE_URL", "sqlite:///data/activity_bot.db").strip(),
        telegram_proxy_url=_get_proxy_url(),
    )


def sqlite_path_from_url(database_url: str) -> str:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        raise ValueError("Only sqlite:/// DATABASE_URL is supported in v1.0")
    return database_url[len(prefix) :]


def _get_proxy_url() -> str | None:
    value = os.getenv("HTTP_PROXY_URL", "").strip()
    if value:
        return value
    return None


def mask_url_credentials(url: str | None) -> str:
    if not url:
        return "not set"

    parts = urlsplit(url)
    if not parts.username and not parts.password:
        return url

    host = parts.hostname or ""
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, f"***:***@{host}", parts.path, parts.query, parts.fragment))
