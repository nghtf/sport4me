from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramNetworkError

from bot.config import load_settings, mask_url_credentials, sqlite_path_from_url
from bot.handlers import callbacks, commands, errors, group, inline, input
from bot.repository import ActivityRepository
from bot.session import create_telegram_session
from bot.services import ActivityService

logger = logging.getLogger(__name__)


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        force=True,
    )

async def main() -> None:
    configure_logging()
    settings = load_settings()
    logger.info(
        "Starting activity bot with database=%s proxy=%s",
        sqlite_path_from_url(settings.database_url),
        mask_url_credentials(settings.telegram_proxy_url),
    )
    repository = ActivityRepository(sqlite_path_from_url(settings.database_url))
    repository.init_db()
    service = ActivityService(repository)

    session = create_telegram_session(settings.telegram_proxy_url)
    bot = Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dispatcher = Dispatcher(service=service)
    dispatcher.include_router(group.router)
    dispatcher.include_router(commands.router)
    dispatcher.include_router(callbacks.router)
    dispatcher.include_router(inline.router)
    dispatcher.include_router(input.router)
    dispatcher.include_router(errors.router)

    try:
        logger.info("Dropping pending Telegram updates before polling")
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("Starting Telegram polling")
        await dispatcher.start_polling(bot)
    except (TelegramNetworkError, OSError, TimeoutError) as error:
        logger.error(
            "Cannot connect to Telegram API. Proxy: %s. "
            "Check that the proxy is running, supports HTTPS CONNECT to api.telegram.org:443, "
            "and is reachable from this environment. Original error: %s",
            mask_url_credentials(settings.telegram_proxy_url),
            error,
        )
        raise SystemExit(1) from error
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
