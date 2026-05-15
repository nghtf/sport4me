from __future__ import annotations

from datetime import datetime

from bot.models import PeriodStats
from bot.models import Tournament, User, LeaderboardEntry
from bot.scoring import calculate_score
from bot.ui import period_message, stats_message, tournament_results_message
from bot.handlers.inline import _resolve_inline_periods


def test_stats_message_is_compact_and_aligned() -> None:
    message = stats_message(
        PeriodStats(
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
    assert message.endswith('<a href="https://t.me/sport4me_bot">Занимайся!</a>')


def test_stats_message_uses_english_for_non_russian_users() -> None:
    message = stats_message(
        PeriodStats(
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
    assert message.endswith('<a href="https://t.me/sport4me_bot">Sport now!</a>')


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
    assert message.endswith('<a href="https://t.me/sport4me_bot">Sport now!</a>')


def test_tournament_results_message_adds_tournament_cta() -> None:
    tournament = Tournament(
        id=1,
        group_chat_id=1,
        telegram_chat_id=1,
        started_by_user_id=1,
        start_date=datetime(2026, 5, 14, 0, 0, 0),
        end_date=datetime(2026, 5, 21, 0, 0, 0),
        finished_at=None,
        created_at=datetime(2026, 5, 14, 0, 0, 0),
    )
    user = User(
        id=1,
        telegram_user_id=1,
        username="alice",
        first_name="Alice",
        preferred_language="en",
        created_at=datetime(2026, 5, 14, 0, 0, 0),
    )
    message = tournament_results_message(
        tournament,
        [LeaderboardEntry(rank=1, user=user, score=1200)],
        "en",
        bot_username="sport4me_bot",
        now=datetime(2026, 5, 15, 0, 0, 0),
    )

    assert "🥇 @alice: 1 200" in message
    assert message.endswith('<a href="https://t.me/sport4me_bot">Engage!</a>')


def test_inline_query_aliases_resolve_expected_periods() -> None:
    assert _resolve_inline_periods("") == ("all", "day", "week", "month")
    assert _resolve_inline_periods("stat") == ("all",)
    assert _resolve_inline_periods("today") == ("day",)
    assert _resolve_inline_periods("неделя") == ("week",)
