from __future__ import annotations

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.services import (
    ActivityService,
    last_day_range,
    last_month_range,
    last_week_range,
    month_range,
    today_range,
    week_range,
)
from bot.ui import cannot_identify_user_message, group_leaderboard_message, participate_keyboard, user_language

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))

_PERIOD_RANGES = {
    "day": today_range,
    "week": week_range,
    "month": month_range,
    "last_day": last_day_range,
    "last_week": last_week_range,
    "last_month": last_month_range,
}


def _parse_top_period(args: str) -> str:
    parts = args.lower().split()
    last = "last" in parts
    if "month" in parts:
        base = "month"
    elif "week" in parts:
        base = "week"
    else:
        base = "day"
    return f"last_{base}" if last else base


@router.message(Command("top"))
async def top(message: Message, command: CommandObject, service: ActivityService) -> None:
    period = _parse_top_period(command.args or "")
    telegram_user = message.from_user
    chat = message.chat
    logger.info(
        "Handling /top %s for user_id=%s in chat_id=%s",
        period,
        telegram_user.id if telegram_user else "<unknown>",
        chat.id,
    )
    if telegram_user is None:
        await message.reply(cannot_identify_user_message("en"))
        return

    now = datetime.now()
    stored_user = service.ensure_user(
        telegram_user.id, telegram_user.username,
        first_name=telegram_user.first_name, language_code=telegram_user.language_code, now=now,
    )
    lang = user_language(stored_user, telegram_user)

    service.register_group_member(
        chat.id, chat.title, telegram_user.id, telegram_user.username,
        first_name=telegram_user.first_name, language_code=telegram_user.language_code, now=now,
    )

    start, end = _PERIOD_RANGES[period](now)
    entries = service.get_group_top(chat.id, chat.title, start, end, now=now)
    bot_username = (await message.bot.me()).username

    await message.reply(
        group_leaderboard_message(period, entries, lang, bot_username=bot_username),
        reply_markup=participate_keyboard(lang, chat.id),
    )
