from __future__ import annotations

from aiogram.client.session.aiohttp import AiohttpSession

from bot.config import PROXY_ENV_NAMES, load_settings, mask_url_credentials
from bot.session import create_telegram_session


def test_load_settings_ignores_generic_proxy_envs(monkeypatch) -> None:
    for env_name in PROXY_ENV_NAMES:
        monkeypatch.delenv(env_name, raising=False)
    for env_name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(env_name, raising=False)

    monkeypatch.setenv("BOT_TOKEN", "123:test")
    monkeypatch.setenv("HTTP_PROXY_URL", "")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:8118")

    settings = load_settings()

    assert settings.telegram_proxy_url is None


def test_telegram_proxy_url_has_priority(monkeypatch) -> None:
    for env_name in PROXY_ENV_NAMES:
        monkeypatch.delenv(env_name, raising=False)
    for env_name in ("HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"):
        monkeypatch.delenv(env_name, raising=False)

    monkeypatch.setenv("BOT_TOKEN", "123:test")
    monkeypatch.setenv("HTTP_PROXY_URL", "https://proxy.example:8443")
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:8118")

    settings = load_settings()

    assert settings.telegram_proxy_url == "https://proxy.example:8443"


def test_mask_url_credentials_hides_proxy_auth() -> None:
    assert (
        mask_url_credentials("https://user:secret@proxy.example:8443")
        == "https://***:***@proxy.example:8443"
    )


def test_mask_url_credentials_keeps_url_without_auth() -> None:
    assert mask_url_credentials("http://127.0.0.1:8118") == "http://127.0.0.1:8118"


def test_http_proxy_uses_aiogram_proxy_session() -> None:
    session = create_telegram_session("http://127.0.0.1:8118")

    assert isinstance(session, AiohttpSession)
    assert session._proxy == "http://127.0.0.1:8118"


def test_socks5_proxy_uses_aiogram_proxy_session() -> None:
    session = create_telegram_session("socks5://host.docker.internal:1081")

    assert isinstance(session, AiohttpSession)
    assert type(session).__name__ == "CurlSocksSession"
