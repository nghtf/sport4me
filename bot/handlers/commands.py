from __future__ import annotations

import logging

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.services import ActivityService
from bot.ui import (
    cannot_identify_user_message,
    clean_confirm_message,
    clean_confirm_keyboard,
    cta_keyboard,
    detailed_message,
    details_keyboard,
    details_prompt,
    help_text,
    language_switched_to_english_message,
    language_switched_to_russian_message,
    period_message,
    start_text,
    stats_message,
    user_language,
    PERIOD_TO_FIELD,
)

logger = logging.getLogger(__name__)

router = Router()


@router.message(Command("start"))
async def start(message: Message, service: ActivityService) -> None:
    telegram_user = message.from_user
    logger.info("Handling /start for user_id=%s", telegram_user.id if telegram_user else "<unknown>")
    stored_user = None
    if telegram_user is not None:
        stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name, language_code=telegram_user.language_code)
    lang = user_language(stored_user, telegram_user)
    await message.answer(start_text(lang))


@router.message(Command("help"))
async def help_command(message: Message, service: ActivityService) -> None:
    telegram_user = message.from_user
    logger.info("Handling /help for user_id=%s", telegram_user.id if telegram_user else "<unknown>")
    stored_user = None
    if telegram_user is not None:
        stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name, language_code=telegram_user.language_code)
    lang = user_language(stored_user, telegram_user)
    await message.answer(help_text(lang))


@router.message(Command("stat"))
async def stat(message: Message, service: ActivityService) -> None:
    telegram_user = message.from_user
    logger.info("Handling /stat for user_id=%s", telegram_user.id if telegram_user else "<unknown>")
    if telegram_user is None:
        await message.answer(cannot_identify_user_message("en"))
        return

    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name, language_code=telegram_user.language_code)
    lang = user_language(stored_user, telegram_user)
    stats = service.get_period_stats(telegram_user.id, telegram_user.username)
    bot_username = (await message.bot.me()).username
    await message.answer(stats_message(stats, lang, bot_username=bot_username), reply_markup=cta_keyboard(lang))


@router.message(Command("en"))
async def english(message: Message, service: ActivityService) -> None:
    telegram_user = message.from_user
    logger.info("Handling /en for user_id=%s", telegram_user.id if telegram_user else "<unknown>")
    if telegram_user is None:
        await message.answer(cannot_identify_user_message("en"))
        return
    service.set_user_language(telegram_user.id, telegram_user.username, "en")
    await message.answer(language_switched_to_english_message())


@router.message(Command("ru"))
async def russian(message: Message, service: ActivityService) -> None:
    telegram_user = message.from_user
    logger.info("Handling /ru for user_id=%s", telegram_user.id if telegram_user else "<unknown>")
    if telegram_user is None:
        await message.answer(cannot_identify_user_message("en"))
        return
    service.set_user_language(telegram_user.id, telegram_user.username, "ru")
    await message.answer(language_switched_to_russian_message())


@router.message(Command("clean"))
async def clean(message: Message, service: ActivityService) -> None:
    telegram_user = message.from_user
    logger.info("Handling /clean for user_id=%s", telegram_user.id if telegram_user else "<unknown>")
    if telegram_user is None:
        await message.answer(cannot_identify_user_message("en"))
        return
    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name, language_code=telegram_user.language_code)
    lang = user_language(stored_user, telegram_user)
    await message.answer(clean_confirm_message(lang), reply_markup=clean_confirm_keyboard(lang))


@router.message(Command("today"))
async def today(message: Message, service: ActivityService) -> None:
    await _send_single_period_stats(message, service, "day")


@router.message(Command("yesterday"))
async def yesterday(message: Message, service: ActivityService) -> None:
    telegram_user = message.from_user
    logger.info("Handling /yesterday for user_id=%s", telegram_user.id if telegram_user else "<unknown>")
    if telegram_user is None:
        await message.answer(cannot_identify_user_message("en"))
        return
    stored_user = service.ensure_user(
        telegram_user.id, telegram_user.username,
        first_name=telegram_user.first_name, language_code=telegram_user.language_code,
    )
    lang = user_language(stored_user, telegram_user)
    totals = service.get_yesterday_totals(telegram_user.id, telegram_user.username)
    bot_username = (await message.bot.me()).username
    await message.answer(period_message("yesterday", totals, lang, bot_username=bot_username), reply_markup=cta_keyboard(lang))


@router.message(Command("week"))
async def week(message: Message, service: ActivityService) -> None:
    await _send_single_period_stats(message, service, "week")


@router.message(Command("month"))
async def month(message: Message, service: ActivityService) -> None:
    await _send_single_period_stats(message, service, "month")


@router.message(Command("details"))
async def details(message: Message, service: ActivityService) -> None:
    telegram_user = message.from_user
    logger.info("Handling /details for user_id=%s", telegram_user.id if telegram_user else "<unknown>")
    if telegram_user is None:
        await message.answer(cannot_identify_user_message("en"))
        return
    stored_user = service.ensure_user(
        telegram_user.id, telegram_user.username,
        first_name=telegram_user.first_name, language_code=telegram_user.language_code,
    )
    lang = user_language(stored_user, telegram_user)
    await message.answer(details_prompt(lang), reply_markup=details_keyboard(lang))


@router.message(Command("detailed"))
async def detailed(message: Message, command: CommandObject, service: ActivityService) -> None:
    telegram_user = message.from_user
    logger.info("Handling /detailed for user_id=%s", telegram_user.id if telegram_user else "<unknown>")
    if telegram_user is None:
        await message.answer(cannot_identify_user_message("en"))
        return

    stored_user = service.ensure_user(
        telegram_user.id, telegram_user.username,
        first_name=telegram_user.first_name, language_code=telegram_user.language_code,
    )
    lang = user_language(stored_user, telegram_user)

    args = (command.args or "").lower().split()
    last = "last" in args
    period = "month" if "month" in args else "week"

    daily_scores = service.get_detailed_stats(telegram_user.id, telegram_user.username, period, last)
    bot_username = (await message.bot.me()).username
    await message.answer(detailed_message(period, last, daily_scores, lang, bot_username=bot_username), reply_markup=cta_keyboard(lang))


async def _send_single_period_stats(message: Message, service: ActivityService, period: str) -> None:
    telegram_user = message.from_user
    logger.info("Handling /%s for user_id=%s", period, telegram_user.id if telegram_user else "<unknown>")
    if telegram_user is None:
        await message.answer(cannot_identify_user_message("en"))
        return

    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name, language_code=telegram_user.language_code)
    lang = user_language(stored_user, telegram_user)
    stats = service.get_period_stats(telegram_user.id, telegram_user.username)
    stats_field = PERIOD_TO_FIELD[period]
    totals = getattr(stats, stats_field)
    bot_username = (await message.bot.me()).username
    await message.answer(period_message(period, totals, lang, bot_username=bot_username), reply_markup=cta_keyboard(lang))
