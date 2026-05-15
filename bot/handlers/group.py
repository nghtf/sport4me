from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from bot.services import (
    ActivityService,
    AlreadyJoinedError,
    GroupFullError,
    InvalidTournamentDaysError,
    NoActiveTournamentError,
    TournamentAlreadyActiveError,
)
from bot.ui import (
    already_joined_message,
    cannot_identify_user_message,
    group_full_message,
    invalid_tournament_days_message,
    no_active_tournament_message,
    tournament_already_active_message,
    tournament_finished_message,
    tournament_join_success_message,
    tournament_results_message,
    tournament_started_message,
    user_language,
)

logger = logging.getLogger(__name__)

router = Router()
router.message.filter(F.chat.type.in_({"group", "supergroup"}))


@router.message(Command("run"))
async def run_tournament(message: Message, command: CommandObject, service: ActivityService) -> None:
    telegram_user = message.from_user
    chat = message.chat
    logger.info("Handling /run for user_id=%s in chat_id=%s",
                telegram_user.id if telegram_user else "<unknown>", chat.id)
    if telegram_user is None:
        await message.reply(cannot_identify_user_message("en"))
        return

    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name)
    lang = user_language(stored_user, telegram_user)

    args = (command.args or "").split()
    numeric_args = [a for a in args if a.isdigit()]
    if not numeric_args:
        await message.reply(invalid_tournament_days_message(lang))
        return

    try:
        tournament = service.start_tournament(
            chat.id,
            chat.title,
            telegram_user.id,
            telegram_user.username,
            int(numeric_args[0]),
            first_name=telegram_user.first_name,
        )
    except InvalidTournamentDaysError:
        await message.reply(invalid_tournament_days_message(lang))
    except TournamentAlreadyActiveError as exc:
        await message.reply(tournament_already_active_message(exc.tournament, lang))
    else:
        await message.reply(tournament_started_message(tournament, lang))


@router.message(Command("join"))
async def join_tournament(message: Message, service: ActivityService) -> None:
    telegram_user = message.from_user
    chat = message.chat
    logger.info("Handling /join for user_id=%s in chat_id=%s",
                telegram_user.id if telegram_user else "<unknown>", chat.id)
    if telegram_user is None:
        await message.reply(cannot_identify_user_message("en"))
        return

    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name)
    lang = user_language(stored_user, telegram_user)

    try:
        count = service.join_tournament(
            chat.id,
            telegram_user.id,
            telegram_user.username,
            first_name=telegram_user.first_name,
        )
    except NoActiveTournamentError:
        await message.reply(no_active_tournament_message(lang))
    except AlreadyJoinedError:
        await message.reply(already_joined_message(lang))
    except GroupFullError:
        await message.reply(group_full_message(lang))
    else:
        await message.reply(tournament_join_success_message(count, lang))


@router.message(Command("results"))
async def results(message: Message, service: ActivityService) -> None:
    telegram_user = message.from_user
    chat = message.chat
    logger.info("Handling /results for user_id=%s in chat_id=%s",
                telegram_user.id if telegram_user else "<unknown>", chat.id)
    if telegram_user is None:
        await message.reply(cannot_identify_user_message("en"))
        return

    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name)
    lang = user_language(stored_user, telegram_user)
    tournament, entries = service.get_tournament_results(chat.id)
    await message.reply(tournament_results_message(tournament, entries, lang, bot_username=(await message.bot.me()).username))


@router.message(Command("finish"))
async def finish_tournament(message: Message, service: ActivityService) -> None:
    telegram_user = message.from_user
    chat = message.chat
    logger.info("Handling /finish for user_id=%s in chat_id=%s",
                telegram_user.id if telegram_user else "<unknown>", chat.id)
    if telegram_user is None:
        await message.reply(cannot_identify_user_message("en"))
        return

    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name)
    lang = user_language(stored_user, telegram_user)

    try:
        tournament, entries = service.finish_tournament(chat.id)
    except NoActiveTournamentError:
        await message.reply(no_active_tournament_message(lang))
    else:
        await message.reply(tournament_finished_message(tournament, entries, lang, bot_username=(await message.bot.me()).username))
