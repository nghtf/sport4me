from __future__ import annotations

from bot.models import LeaderboardEntry, PeriodStats, User
from bot.scoring import calculate_score
from bot.ui import cta_keyboard, group_leaderboard_message, participate_keyboard, period_message, stats_message
from bot.handlers.inline import _resolve_inline_periods
from datetime import datetime


def test_stats_message_is_compact_and_aligned() -> None:
    message = stats_message(
        PeriodStats(
            yesterday={"steps": 0, "squats": 0, "pushups": 0, "plank": 0, "abs": 0},
            today={"steps": 3, "squats": 0, "pushups": 0, "plank": 0, "abs": 0},
            week={"steps": 1200, "squats": 40, "pushups": 0, "plank": 5, "abs": 0},
            month={"steps": 12345, "squats": 40, "pushups": 10, "plank": 5, "abs": 12},
        ),
        "ru",
        bot_username="sport4me_bot",
    )

    assert "<b>Сегодня (🏅0)</b>" in message
    assert "<b>Неделя (🏅57)</b>" in message
    assert "<b>Месяц (🏅184)</b>" in message
    assert "-----" in message
    assert "<pre>" not in message
    assert "👟 Шаги: 3" in message
    assert "⏱ Планка: 0 мин" in message
    assert "🔥 Пресс: 0" in message
    assert "👟 Шаги: 12 345" in message
    assert message.endswith('<a href="https://t.me/sport4me_bot">Атжумаца тут!</a>')


def test_stats_message_uses_english_for_non_russian_users() -> None:
    message = stats_message(
        PeriodStats(
            yesterday={"steps": 0, "squats": 0, "pushups": 0, "plank": 0, "abs": 0},
            today={"steps": 3, "squats": 0, "pushups": 0, "plank": 0, "abs": 0},
            week={"steps": 1200, "squats": 40, "pushups": 0, "plank": 5, "abs": 0},
            month={"steps": 12345, "squats": 40, "pushups": 10, "plank": 5, "abs": 12},
        ),
        "en",
        bot_username="sport4me_bot",
    )

    assert "<b>Today (🏅0)</b>" in message
    assert "<b>Week (🏅57)</b>" in message
    assert "<b>Month (🏅184)</b>" in message
    assert "-----" in message
    assert "👟 Steps: 3" in message
    assert "⏱ Plank: 0 min" in message
    assert "🔥 Abs: 0" in message
    assert message.endswith('<a href="https://t.me/sport4me_bot">Join here!</a>')


def test_calculate_score_uses_normalized_model() -> None:
    assert calculate_score({"steps": 1_000}) == 10
    assert calculate_score({"squats": 20}) == 10
    assert calculate_score({"pushups": 10}) == 10
    assert calculate_score({"plank": 2}) == 10
    assert calculate_score({"abs": 20}) == 10


def test_period_message_returns_single_period_block() -> None:
    message = period_message("day", {"steps": 42, "plank": 5}, "en", bot_username="sport4me_bot")

    assert message.startswith("<b>Today (🏅25)</b>")
    assert "-----" in message
    assert "👟 Steps: 42" in message
    assert "<b>Week</b>" not in message
    assert message.endswith('<a href="https://t.me/sport4me_bot">Join here!</a>')


def test_group_leaderboard_message_shows_medals() -> None:
    def _user(uid: int, username: str | None, first_name: str | None = None) -> User:
        return User(id=uid, telegram_user_id=uid, username=username, first_name=first_name,
                    preferred_language="en", created_at=datetime(2026, 1, 1))

    entries = [
        LeaderboardEntry(rank=1, user=_user(1, "alice"), score=120),
        LeaderboardEntry(rank=2, user=_user(2, "bob"), score=80),
        LeaderboardEntry(rank=3, user=_user(3, None, "Carol"), score=50),   # no username, has first_name
        LeaderboardEntry(rank=4, user=_user(4, None, None), score=10),      # no username, no first_name
    ]
    message = group_leaderboard_message("day", entries, "en", bot_username="sport4me_bot")

    assert "Top 10 · Today" in message
    assert "🥇 @alice: 120" in message
    assert "🥈 @bob: 80" in message
    assert "🥉 Carol: 50" in message
    assert "4. Member: 10" in message
    assert message.endswith('<a href="https://t.me/sport4me_bot">Join here!</a>')


def test_group_leaderboard_message_no_data() -> None:
    message = group_leaderboard_message("last_week", [], "ru", bot_username="sport4me_bot")
    assert "Прошлая неделя" in message
    assert "Нет данных" in message
    assert message.endswith('<a href="https://t.me/sport4me_bot">Атжумаца тут!</a>')


def test_participate_keyboard_label() -> None:
    kb = participate_keyboard("en", chat_id=-100123456789)
    btn = kb.inline_keyboard[0][0]
    assert btn.text == "Participate!"
    assert btn.callback_data == "join_group:-100123456789"

    kb_ru = participate_keyboard("ru", chat_id=-100123456789)
    assert kb_ru.inline_keyboard[0][0].text == "Участвовать!"


def test_cta_keyboard_label() -> None:
    kb = cta_keyboard("en")
    assert kb.inline_keyboard[0][0].text == "Get your result"
    kb_ru = cta_keyboard("ru")
    assert kb_ru.inline_keyboard[0][0].text == "Узнай свой результат"


def test_inline_query_aliases_resolve_expected_periods() -> None:
    assert _resolve_inline_periods("") == ("all", "yesterday", "day", "week", "month")
    assert _resolve_inline_periods("stat") == ("all",)
    assert _resolve_inline_periods("today") == ("day",)
    assert _resolve_inline_periods("неделя") == ("week",)
