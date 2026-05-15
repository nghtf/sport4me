from __future__ import annotations

from datetime import datetime, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.types import User as TelegramUser

from bot.constants import ACTIVITIES, ACTIVITY_KEYS, MAX_AMOUNT, MAX_GROUP_MEMBERS, MAX_TOTAL, MAX_TOURNAMENT_DAYS, MIN_TOTAL
from bot.i18n import Language, translate
from bot.models import LeaderboardEntry, PeriodStats, Tournament, User
from bot.scoring import calculate_score
from bot.services import ApplyResult, LimitError
from bot.validators import InputErrorCode

PERIOD_TO_FIELD = {"day": "today", "week": "week", "month": "month"}


def user_language(user: User | None, telegram_user: TelegramUser | None) -> Language:
    if user and user.preferred_language in {"en", "ru"}:
        return user.preferred_language
    if telegram_user and telegram_user.language_code == "ru":
        return "ru"
    return "en"


def format_number(value: int) -> str:
    return f"{value:,}".replace(",", " ")


def activity_keyboard(lang: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                _activity_button("steps", lang),
                _activity_button("squats", lang),
            ],
            [
                _activity_button("pushups", lang),
                _activity_button("plank", lang),
            ],
            [_activity_button("abs", lang)],
            [InlineKeyboardButton(text=translate(lang, "button.cancel"), callback_data="cancel")],
        ]
    )


def clean_confirm_keyboard(lang: Language) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=translate(lang, "button.confirm"),
                    callback_data="clean:confirm",
                ),
                InlineKeyboardButton(
                    text=translate(lang, "button.cancel"),
                    callback_data="clean:cancel",
                ),
            ]
        ]
    )


def start_text(lang: Language) -> str:
    return translate(lang, "message.start")


def help_text(lang: Language) -> str:
    return translate(lang, "message.help")


def pending_prompt(amount: int, lang: Language, replaced: bool = False) -> str:
    action = translate(lang, "term.action.adding" if amount > 0 else "term.action.subtracting")
    direction = translate(lang, "term.direction.add" if amount > 0 else "term.direction.subtract")
    formatted_amount = format_number(abs(amount))
    if replaced:
        return translate(lang, "message.pending.replaced", action=action, amount=formatted_amount, direction=direction)
    return translate(lang, "message.pending.prompt", amount=formatted_amount, direction=direction)


def cancel_message(amount: int | None, lang: Language) -> str:
    if amount is None:
        return translate(lang, "message.cancel.none")
    action = translate(lang, "term.action.not_adding" if amount > 0 else "term.action.not_subtracting")
    return translate(lang, "message.cancel.pending", action=action, amount=format_number(abs(amount)))


def apply_success_message(result: ApplyResult, lang: Language) -> str:
    amount_text = format_activity_amount(result.activity_key, result.amount, lang)
    total_text = format_activity_amount(result.activity_key, result.today_total, lang)
    action = translate(lang, "term.action.added" if result.amount > 0 else "term.action.subtracted")
    return translate(lang, "message.apply_success", action=action, amount_text=amount_text, total_text=total_text)


def limit_error_message(activity_key: str, amount: int, error: LimitError, lang: Language) -> str:
    amount_text = format_activity_amount(activity_key, amount, lang)
    current_text = format_activity_amount(activity_key, error.current_total, lang)
    bound_value = MIN_TOTAL if error.attempted_total < MIN_TOTAL else MAX_TOTAL
    action = translate(lang, "term.action.add" if amount > 0 else "term.action.subtract")
    bound_label = translate(lang, "term.bound.minimum" if error.attempted_total < MIN_TOTAL else "term.bound.maximum")
    return translate(
        lang,
        "message.limit_error",
        action=action,
        amount_text=amount_text,
        attempted_total=format_number(error.attempted_total),
        bound_label=bound_label,
        bound_value=format_number(bound_value),
        current_text=current_text,
    )


def input_error_message(code: InputErrorCode, lang: Language) -> str:
    if code == InputErrorCode.ZERO:
        return translate(lang, "message.input_error.zero", max_amount=format_number(MAX_AMOUNT))
    if code == InputErrorCode.TOO_LARGE:
        return translate(lang, "message.input_error.too_large", max_amount=format_number(MAX_AMOUNT))
    return translate(lang, "message.input_error.invalid")


def stats_message(stats: PeriodStats, lang: Language, bot_username: str | None = None) -> str:
    body = "\n\n".join(
        [
            period_message("day", stats.today, lang, bot_username=bot_username, include_cta=False),
            period_message("week", stats.week, lang, bot_username=bot_username, include_cta=False),
            period_message("month", stats.month, lang, bot_username=bot_username, include_cta=False),
        ]
    )
    return _append_cta(body, lang, "cta.stats", bot_username)


def period_message(
    period: str,
    totals: dict[str, int],
    lang: Language,
    bot_username: str | None = None,
    include_cta: bool = True,
) -> str:
    title = period_title(period, lang)
    score = calculate_score(totals)
    lines = [f"<b>{title} (🏅{format_number(score)})</b>", "-----"]
    for activity_key in ACTIVITY_KEYS:
        lines.append(stat_line(activity_key, totals.get(activity_key, 0), lang))
    message = "\n".join(lines)
    if not include_cta:
        return message
    return _append_cta(message, lang, "cta.stats", bot_username)


def stat_line(activity_key: str, value: int, lang: Language) -> str:
    activity = ACTIVITIES[activity_key]
    formatted = format_number(value)
    if activity_key == "plank":
        formatted = f"{formatted} {activity.unit(lang)}"
    return f"{activity.emoji} {activity.stat_label(lang)}: {formatted}"


def format_activity_amount(activity_key: str, amount: int, lang: Language) -> str:
    activity = ACTIVITIES[activity_key]
    return f"{format_number(abs(amount))} {activity.amount_label(lang)}"


def cannot_identify_user_message(lang: Language) -> str:
    return translate(lang, "message.cannot_identify_user")


def enter_number_first_message(lang: Language) -> str:
    return translate(lang, "message.enter_number_first")


def unknown_activity_message(lang: Language) -> str:
    return translate(lang, "message.unknown_activity")


def language_switched_to_english_message() -> str:
    return translate("en", "language.switched.en")


def language_switched_to_russian_message() -> str:
    return translate("ru", "language.switched.ru")


def clean_confirm_message(lang: Language) -> str:
    return translate(lang, "message.clean.confirm")


def clean_success_message(lang: Language) -> str:
    return translate(lang, "message.clean.success")


def clean_cancelled_message(lang: Language) -> str:
    return translate(lang, "message.clean.cancelled")


def _activity_button(activity_key: str, lang: Language) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=ACTIVITIES[activity_key].label(lang),
        callback_data=f"activity:{activity_key}",
    )


def tournament_started_message(tournament: Tournament, lang: Language) -> str:
    start = tournament.start_date.strftime("%b %d, %Y")
    last_day = (tournament.end_date - timedelta(days=1)).strftime("%b %d, %Y")
    days = (tournament.end_date - tournament.start_date).days
    return translate(lang, "message.tournament.started", start=start, last_day=last_day, days=days)


def tournament_already_active_message(tournament: Tournament, lang: Language) -> str:
    start = tournament.start_date.strftime("%b %d, %Y")
    last_day = (tournament.end_date - timedelta(days=1)).strftime("%b %d, %Y")
    return translate(lang, "message.tournament.already_active", start=start, last_day=last_day)


def tournament_results_message(
    tournament: Tournament | None,
    entries: list[LeaderboardEntry],
    lang: Language,
    bot_username: str | None = None,
    now: datetime | None = None,
) -> str:
    if tournament is None:
        return translate(lang, "message.tournament.results.none")

    current_time = now or datetime.now()
    is_active = tournament.is_active(current_time)
    start = tournament.start_date.strftime("%b %d")
    last_day = (tournament.end_date - timedelta(days=1)).strftime("%b %d, %Y")
    status = translate(lang, "term.tournament.status.active" if is_active else "term.tournament.status.ended")
    header = translate(lang, "message.tournament.results.header", start=start, last_day=last_day, status=status)

    if not entries:
        return _append_cta(
            f"{header}\n\n{translate(lang, 'message.tournament.results.no_participants')}",
            lang,
            "cta.tournament",
            bot_username,
        )

    _MEDALS = ["🥇", "🥈", "🥉"]
    lines = [header, "-----"]
    for entry in entries:
        medal = _MEDALS[entry.rank - 1] if entry.rank <= 3 else f"{entry.rank}."
        name = (
            f"@{entry.user.username}"
            if entry.user.username
            else (entry.user.first_name or f"#{entry.user.telegram_user_id}")
        )
        lines.append(f"{medal} {name}: {format_number(entry.score)}")
    return _append_cta("\n".join(lines), lang, "cta.tournament", bot_username)


def tournament_join_success_message(participant_count: int, lang: Language) -> str:
    return translate(lang, "message.tournament.join_success", participant_count=participant_count)


def already_joined_message(lang: Language) -> str:
    return translate(lang, "message.already_joined")


def no_active_tournament_message(lang: Language) -> str:
    return translate(lang, "message.no_active_tournament")


def tournament_finished_message(
    tournament: Tournament,
    entries: list[LeaderboardEntry],
    lang: Language,
    bot_username: str | None = None,
) -> str:
    start = tournament.start_date.strftime("%b %d")
    end = (tournament.end_date - timedelta(days=1)).strftime("%b %d, %Y")
    header = translate(lang, "message.tournament.finished.header", start=start, end=end)
    if not entries:
        return _append_cta(
            f"{header}\n\n{translate(lang, 'message.tournament.finished.no_participants')}",
            lang,
            "cta.tournament",
            bot_username,
        )
    _MEDALS = ["🥇", "🥈", "🥉"]
    lines = [header, "-----"]
    for entry in entries:
        medal = _MEDALS[entry.rank - 1] if entry.rank <= 3 else f"{entry.rank}."
        name = (
            f"@{entry.user.username}"
            if entry.user.username
            else (entry.user.first_name or f"#{entry.user.telegram_user_id}")
        )
        lines.append(f"{medal} {name}: {format_number(entry.score)}")
    return _append_cta("\n".join(lines), lang, "cta.tournament", bot_username)


def group_full_message(lang: Language) -> str:
    return translate(lang, "message.group_full", max_group_members=MAX_GROUP_MEMBERS)


def invalid_tournament_days_message(lang: Language) -> str:
    return translate(lang, "message.invalid_tournament_days", max_tournament_days=MAX_TOURNAMENT_DAYS)


def period_title(period: str, lang: Language) -> str:
    return translate(lang, f"period.{period}")


def _append_cta(message: str, lang: Language, label_key: str, bot_username: str | None) -> str:
    if not bot_username:
        return message
    return f'{message}\n\n<a href="{_bot_chat_url(bot_username)}">{translate(lang, label_key)}</a>'


def _bot_chat_url(bot_username: str) -> str:
    return f"https://t.me/{bot_username.lstrip('@')}"
