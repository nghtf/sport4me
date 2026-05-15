from __future__ import annotations

import logging

from aiogram import Router
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent

from bot.i18n import translate
from bot.services import ActivityService
from bot.ui import PERIOD_TO_FIELD, period_message, period_title, stats_message, user_language

logger = logging.getLogger(__name__)

router = Router()

_INLINE_PERIOD_ALIASES = {
    "": ("all", "day", "week", "month"),
    "all": ("all",),
    "stat": ("all",),
    "stats": ("all",),
    "today": ("day",),
    "day": ("day",),
    "week": ("week",),
    "month": ("month",),
    "сегодня": ("day",),
    "день": ("day",),
    "неделя": ("week",),
    "месяц": ("month",),
    "стат": ("all",),
    "статистика": ("all",),
}


@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery, service: ActivityService) -> None:
    telegram_user = inline_query.from_user
    logger.info("Handling inline query for user_id=%s query=%r", telegram_user.id, inline_query.query)

    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name)
    lang = user_language(stored_user, telegram_user)
    stats = service.get_period_stats(telegram_user.id, telegram_user.username)
    periods = _resolve_inline_periods(inline_query.query)
    bot_username = (await inline_query.bot.me()).username

    results = [
        _build_stats_result(
            period=period,
            stats=stats,
            lang=lang,
            bot_username=bot_username,
        )
        for period in periods
    ]

    await inline_query.answer(results=results, cache_time=0, is_personal=True)


def _resolve_inline_periods(query: str) -> tuple[str, ...]:
    normalized = query.strip().lower()
    return _INLINE_PERIOD_ALIASES.get(normalized, _INLINE_PERIOD_ALIASES[""])


def _build_stats_result(period: str, stats, lang: str, bot_username: str | None) -> InlineQueryResultArticle:
    if period == "all":
        title = translate(lang, "inline.all_stats.title")
        description = translate(lang, "inline.all_stats.description")
        text = stats_message(stats, lang, bot_username=bot_username)
    else:
        stats_field = PERIOD_TO_FIELD[period]
        title = period_title(period, lang)
        description = title
        text = period_message(period, getattr(stats, stats_field), lang, bot_username=bot_username)

    return InlineQueryResultArticle(
        id=period,
        title=title,
        description=description,
        input_message_content=InputTextMessageContent(
            message_text=text,
            parse_mode="HTML",
        ),
    )
