from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

from bot.config import load_settings, mask_url_credentials


def main() -> int:
    settings = load_settings()
    proxy_url = settings.telegram_proxy_url
    print(f"Telegram proxy: {mask_url_credentials(proxy_url)}")

    opener = urllib.request.build_opener()
    if os.getenv("HTTP_PROXY_URL"):
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler(
                {
                    "http": os.environ["HTTP_PROXY_URL"],
                    "https": os.environ["HTTP_PROXY_URL"],
                }
            )
        )

    url = f"https://api.telegram.org/bot{settings.bot_token}/getMe"
    request = urllib.request.Request(url, headers={"User-Agent": "activity-bot-check"})

    try:
        with opener.open(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        print(f"Telegram API returned HTTP {error.code}. Check BOT_TOKEN.")
        return 1
    except OSError as error:
        print(f"Cannot reach Telegram API through the configured proxy: {error}")
        return 1

    if not payload.get("ok"):
        print(f"Telegram API returned error: {payload}")
        return 1

    bot = payload.get("result", {})
    print(f"Telegram API ok: @{bot.get('username', '<unknown>')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
