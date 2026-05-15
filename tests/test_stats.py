from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from bot.repository import ActivityRepository
from bot.services import ActivityService, LimitError


@pytest.fixture()
def repository(tmp_path):
    repo = ActivityRepository(str(tmp_path / "activity.db"))
    repo.init_db()
    return repo


def test_stats_are_scoped_by_user_and_period(repository: ActivityRepository) -> None:
    service = ActivityService(repository)
    now = datetime(2026, 5, 13, 12, 0, 0)
    user = service.ensure_user(telegram_user_id=1, username="alice", now=now)
    other_user = service.ensure_user(telegram_user_id=2, username="bob", now=now)

    repository.add_activity_entry(user.id, "steps", 100, now)
    repository.add_activity_entry(user.id, "steps", -20, now + timedelta(hours=1))
    repository.add_activity_entry(user.id, "squats", 15, now - timedelta(days=1))
    repository.add_activity_entry(user.id, "pushups", 7, datetime(2026, 5, 4, 12, 0, 0))
    repository.add_activity_entry(user.id, "abs", 9, datetime(2026, 4, 30, 12, 0, 0))
    repository.add_activity_entry(other_user.id, "steps", 999, now)

    stats = service.get_period_stats(telegram_user_id=1, username="alice", now=now)

    assert stats.today["steps"] == 80
    assert stats.today["squats"] == 0
    assert stats.week["steps"] == 80
    assert stats.week["squats"] == 15
    assert stats.week["pushups"] == 0
    assert stats.month["steps"] == 80
    assert stats.month["squats"] == 15
    assert stats.month["pushups"] == 7
    assert stats.month["abs"] == 0


def test_apply_pending_saves_valid_entry_and_clears_pending(repository: ActivityRepository) -> None:
    service = ActivityService(repository)
    now = datetime(2026, 5, 13, 12, 0, 0)

    service.set_pending_amount(telegram_user_id=1, amount=20)
    result = service.apply_pending_amount(1, "alice", "pushups", now=now)

    assert result.today_total == 20
    assert result.amount == 20
    assert service.get_pending_amount(1) is None
    stats = service.get_period_stats(1, "alice", now=now)
    assert stats.today["pushups"] == 20


def test_apply_pending_rejects_below_zero_and_does_not_save(repository: ActivityRepository) -> None:
    service = ActivityService(repository)
    now = datetime(2026, 5, 13, 12, 0, 0)

    service.set_pending_amount(telegram_user_id=1, amount=20)
    service.apply_pending_amount(1, "alice", "pushups", now=now)
    service.set_pending_amount(telegram_user_id=1, amount=-21)

    with pytest.raises(LimitError) as error:
        service.apply_pending_amount(1, "alice", "pushups", now=now)

    assert error.value.current_total == 20
    assert error.value.attempted_total == -1
    assert service.get_pending_amount(1) is None
    stats = service.get_period_stats(1, "alice", now=now)
    assert stats.today["pushups"] == 20


def test_user_language_preference_is_persistent(repository: ActivityRepository) -> None:
    service = ActivityService(repository)
    now = datetime(2026, 5, 13, 12, 0, 0)

    created = service.ensure_user(telegram_user_id=1, username="alice", now=now)
    assert created.preferred_language is None

    updated = service.set_user_language(telegram_user_id=1, username="alice", language="en", now=now)
    assert updated.preferred_language == "en"

    loaded = service.ensure_user(telegram_user_id=1, username="alice", now=now)
    assert loaded.preferred_language == "en"


def test_language_code_fills_null_preferred_language_on_new_user(repository: ActivityRepository) -> None:
    service = ActivityService(repository)
    now = datetime(2026, 5, 13, 12, 0, 0)

    user = service.ensure_user(1, "alice", language_code="ru", now=now)
    assert user.preferred_language == "ru"


def test_language_code_fills_null_preferred_language_on_existing_user(repository: ActivityRepository) -> None:
    service = ActivityService(repository)
    now = datetime(2026, 5, 13, 12, 0, 0)

    # First interaction — no language_code known yet
    service.ensure_user(1, "alice", now=now)

    # Second interaction — Telegram language_code now available
    updated = service.ensure_user(1, "alice", language_code="ru", now=now)
    assert updated.preferred_language == "ru"


def test_language_code_does_not_override_explicit_language(repository: ActivityRepository) -> None:
    service = ActivityService(repository)
    now = datetime(2026, 5, 13, 12, 0, 0)

    service.ensure_user(1, "alice", now=now)
    service.set_user_language(1, "alice", "en", now=now)

    # Telegram says "ru" but user already chose "en" explicitly
    user = service.ensure_user(1, "alice", language_code="ru", now=now)
    assert user.preferred_language == "en"


def test_non_russian_language_code_resolves_to_english(repository: ActivityRepository) -> None:
    service = ActivityService(repository)
    now = datetime(2026, 5, 13, 12, 0, 0)

    user = service.ensure_user(1, "alice", language_code="de", now=now)
    assert user.preferred_language == "en"


def test_none_language_code_leaves_preferred_language_null(repository: ActivityRepository) -> None:
    service = ActivityService(repository)
    now = datetime(2026, 5, 13, 12, 0, 0)

    user = service.ensure_user(1, "alice", language_code=None, now=now)
    assert user.preferred_language is None


def test_clear_all_stats_removes_entries_but_keeps_user(repository: ActivityRepository) -> None:
    service = ActivityService(repository)
    now = datetime(2026, 5, 13, 12, 0, 0)

    user = service.ensure_user(telegram_user_id=1, username="alice", now=now)
    repository.add_activity_entry(user.id, "steps", 100, now)
    repository.add_activity_entry(user.id, "plank", 5, now)
    service.set_pending_amount(telegram_user_id=1, amount=10)

    cleared_user = service.clear_all_stats(telegram_user_id=1, username="alice", now=now)

    assert cleared_user.telegram_user_id == 1
    assert service.get_pending_amount(1) is None
    stats = service.get_period_stats(1, "alice", now=now)
    assert stats.today["steps"] == 0
    assert stats.today["plank"] == 0
    assert stats.week["steps"] == 0
    assert stats.month["plank"] == 0
