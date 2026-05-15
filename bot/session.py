from __future__ import annotations

import asyncio
import contextlib
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.exceptions import TelegramNetworkError
from aiogram.methods.base import TelegramType

if False:  # pragma: no cover
    from aiogram.client.bot import Bot
    from aiogram.methods import TelegramMethod


def create_telegram_session(proxy_url: str | None) -> AiohttpSession:
    session_kwargs: dict[str, object] = {}

    if proxy_url:
        scheme = urlsplit(proxy_url).scheme.lower()
        if scheme not in {"http", "https", "socks5", "socks5h"}:
            raise RuntimeError(
                "Supported proxy URL schemes are http, https, socks5, and socks5h. "
                "Use HTTP_PROXY_URL=http://host:port, https://host:port, or socks5://host:port."
            )
        if scheme in {"socks5", "socks5h"}:
            return CurlSocksSession(proxy_url)
        session_kwargs["proxy"] = proxy_url

    session = AiohttpSession(**session_kwargs)
    session.timeout = 120
    return session


class CurlSocksSession(AiohttpSession):
    def __init__(self, proxy_url: str, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.proxy_url = proxy_url
        self.timeout = 120

    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[TelegramType],
        timeout: int | None = None,
    ) -> TelegramType:
        url = self.api.api_url(token=bot.token, method=method.__api_method__)
        files: dict[str, object] = {}
        data: dict[str, str] = {}

        for key, value in method.model_dump(warnings=False).items():
            prepared = self.prepare_value(value, bot=bot, files=files)
            if prepared is not None:
                data[key] = prepared

        if files:
            raise RuntimeError("File uploads through SOCKS proxy are not supported in this runtime")

        try:
            status_code, body = await _curl_request(
                proxy_url=self.proxy_url,
                url=url,
                data=data or None,
                timeout=self.timeout if timeout is None else timeout,
            )
        except RuntimeError as error:
            raise TelegramNetworkError(method=method, message=str(error)) from error
        response = self.check_response(
            bot=bot,
            method=method,
            status_code=status_code,
            content=body,
        )
        return response.result


async def _curl_request(
    *,
    proxy_url: str,
    url: str,
    data: dict[str, str] | None,
    timeout: int,
) -> tuple[int, str]:
    scheme = urlsplit(proxy_url).scheme.lower()
    marker = "__CURL_HTTP_STATUS__:"
    with tempfile.NamedTemporaryFile(delete=False) as output_file:
        output_path = Path(output_file.name)

    command = [
        "curl",
        "--silent",
        "--show-error",
        "--max-time",
        str(timeout),
        "--output",
        str(output_path),
        "--write-out",
        marker + "%{http_code}",
    ]

    if scheme == "socks5h":
        command.extend(["--socks5-hostname", proxy_url[len("socks5h://") :]])
    else:
        command.extend(["--socks5", proxy_url[len("socks5://") :]])

    if data:
        for key, value in data.items():
            command.extend(["--data-urlencode", f"{key}={value}"])

    command.append(url)

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        if process.returncode != 0:
            raise RuntimeError(stderr.decode("utf-8", errors="replace").strip() or "curl failed")

        status_output = stdout.decode("utf-8", errors="replace").strip()
        if not status_output.startswith(marker):
            raise RuntimeError(f"Unexpected curl status output: {status_output}")
        status_code = int(status_output[len(marker) :])
        body = output_path.read_text(encoding="utf-8", errors="replace")
        return status_code, body
    finally:
        with contextlib.suppress(FileNotFoundError):
            output_path.unlink()
