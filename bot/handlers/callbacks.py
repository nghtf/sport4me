from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery

from bot.constants import ACTIVITIES
from bot.services import ActivityService, LimitError, PendingNotFoundError
from bot.i18n import translate
from bot.ui import (
    apply_success_message,
    cancel_message,
    clean_cancelled_message,
    clean_success_message,
    cta_keyboard,
    detailed_message,
    enter_number_first_message,
    limit_error_message,
    unknown_activity_message,
    user_language,
)

router = Router()


async def _answer_callback_safely(callback: CallbackQuery) -> None:
    try:
        await callback.answer()
    except TelegramBadRequest as error:
        # Callback queries can expire or be acknowledged by Telegram already.
        if "query is too old" in str(error).lower() or "query id is invalid" in str(error).lower():
            return
        raise


async def _delete_prompt_message_safely(callback: CallbackQuery) -> None:
    if callback.message is None:
        return
    try:
        await callback.message.delete()
    except TelegramBadRequest as error:
        if "message to delete not found" in str(error).lower():
            return
        raise


@router.callback_query(F.data == "cancel")
async def cancel(callback: CallbackQuery, service: ActivityService) -> None:
    telegram_user = callback.from_user
    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name, language_code=telegram_user.language_code)
    lang = user_language(stored_user, telegram_user)
    amount = service.clear_pending_amount(telegram_user.id)
    await callback.message.answer(cancel_message(amount, lang))
    await _delete_prompt_message_safely(callback)
    await _answer_callback_safely(callback)


@router.callback_query(F.data == "clean:cancel")
async def cancel_clean(callback: CallbackQuery, service: ActivityService) -> None:
    telegram_user = callback.from_user
    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name, language_code=telegram_user.language_code)
    lang = user_language(stored_user, telegram_user)
    await callback.message.answer(clean_cancelled_message(lang))
    await _delete_prompt_message_safely(callback)
    await _answer_callback_safely(callback)


@router.callback_query(F.data == "clean:confirm")
async def confirm_clean(callback: CallbackQuery, service: ActivityService) -> None:
    telegram_user = callback.from_user
    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name, language_code=telegram_user.language_code)
    lang = user_language(stored_user, telegram_user)
    service.clear_all_stats(telegram_user.id, telegram_user.username)
    await callback.message.answer(clean_success_message(lang))
    await _delete_prompt_message_safely(callback)
    await _answer_callback_safely(callback)


@router.callback_query(F.data.startswith("join_group:"))
async def join_group(callback: CallbackQuery, service: ActivityService) -> None:
    telegram_user = callback.from_user
    chat_id = int(str(callback.data).split(":", 1)[1])
    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name, language_code=telegram_user.language_code)
    lang = user_language(stored_user, telegram_user)
    service.register_group_member(chat_id, None, telegram_user.id, telegram_user.username, first_name=telegram_user.first_name)
    await callback.answer(translate(lang, "message.join_group.success"), show_alert=False)


@router.callback_query(F.data.startswith("details:"))
async def details_period(callback: CallbackQuery, service: ActivityService) -> None:
    telegram_user = callback.from_user
    stored_user = service.ensure_user(
        telegram_user.id, telegram_user.username,
        first_name=telegram_user.first_name, language_code=telegram_user.language_code,
    )
    lang = user_language(stored_user, telegram_user)

    key = str(callback.data).split(":", 1)[1]  # "week", "last_week", "month", "last_month"
    last = key.startswith("last_")
    period = key[5:] if last else key

    daily_scores = service.get_detailed_stats(telegram_user.id, telegram_user.username, period, last)
    bot_username = (await callback.bot.me()).username
    await _delete_prompt_message_safely(callback)
    await callback.message.answer(detailed_message(period, last, daily_scores, lang, bot_username=bot_username), reply_markup=cta_keyboard(lang))
    await _answer_callback_safely(callback)


@router.callback_query(F.data.startswith("activity:"))
async def apply_activity(callback: CallbackQuery, service: ActivityService) -> None:
    telegram_user = callback.from_user
    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name, language_code=telegram_user.language_code)
    lang = user_language(stored_user, telegram_user)
    activity_key = str(callback.data).split(":", 1)[1]
    if activity_key not in ACTIVITIES:
        await callback.answer(unknown_activity_message(lang), show_alert=True)
        return

    amount = service.get_pending_amount(telegram_user.id)
    if amount is None:
        await callback.message.answer(enter_number_first_message(lang))
        await _answer_callback_safely(callback)
        return

    try:
        result = service.apply_pending_amount(telegram_user.id, telegram_user.username, activity_key)
    except PendingNotFoundError:
        await callback.message.answer(enter_number_first_message(lang))
    except LimitError as error:
        await callback.message.answer(limit_error_message(activity_key, amount, error, lang))
    else:
        await callback.message.answer(apply_success_message(result, lang))
        await _delete_prompt_message_safely(callback)
    finally:
        await _answer_callback_safely(callback)
