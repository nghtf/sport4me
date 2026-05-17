from __future__ import annotations

from aiogram import F, Router
from aiogram.types import Message

from bot.services import ActivityService
from bot.ui import (
    activity_keyboard,
    input_error_message,
    pending_prompt,
    user_language,
)
from bot.validators import InputValidationError, parse_signed_amount

router = Router()


@router.message(F.text, F.chat.type == "private", F.via_bot.is_(None))
async def handle_text(message: Message, service: ActivityService) -> None:
    telegram_user = message.from_user
    if telegram_user is None:
        return
    stored_user = service.ensure_user(telegram_user.id, telegram_user.username, first_name=telegram_user.first_name, language_code=telegram_user.language_code)
    lang = user_language(stored_user, telegram_user)

    try:
        amount = parse_signed_amount(message.text)
    except InputValidationError as error:
        await message.answer(input_error_message(error.code, lang))
        return

    replaced = service.get_pending_amount(telegram_user.id) is not None
    service.set_pending_amount(telegram_user.id, amount)
    await message.answer(pending_prompt(amount, lang, replaced), reply_markup=activity_keyboard(lang))
