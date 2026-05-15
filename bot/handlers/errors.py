from __future__ import annotations

import logging

from aiogram import Router
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import ErrorEvent

logger = logging.getLogger(__name__)

router = Router()


@router.errors()
async def log_error(event: ErrorEvent) -> bool:
    update_id = getattr(event.update, "update_id", "<unknown>")
    if isinstance(event.exception, TelegramNetworkError):
        logger.warning(
            "Telegram network error for update_id=%s: %s",
            update_id,
            event.exception,
        )
        return True
    logger.exception("Unhandled Telegram update error for update_id=%s", update_id, exc_info=event.exception)
    return True
