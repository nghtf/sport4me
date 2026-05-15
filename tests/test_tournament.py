from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from bot.repository import ActivityRepository
from bot.services import (
    ActivityService,
    AlreadyJoinedError,
    GroupFullError,
    InvalidTournamentDaysError,
    NoActiveTournamentError,
    TournamentAlreadyActiveError,
)


@pytest.fixture()
def repository(tmp_path):
    repo = ActivityRepository(str(tmp_path / "activity.db"))
    repo.init_db()
    return repo


@pytest.fixture()
def service(repository):
    return ActivityService(repository)


NOW = datetime(2026, 5, 14, 10, 0, 0)
CHAT_ID = -100123456789


# ----------------------------------------------------------------- /run tests

def test_start_tournament_creates_correct_period(service: ActivityService) -> None:
    t = service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=7, now=NOW)
    assert t.start_date == datetime(2026, 5, 14, 0, 0, 0)
    assert t.end_date == datetime(2026, 5, 21, 0, 0, 0)
    assert t.finished_at is None
    assert t.is_active(NOW)


def test_tournament_expires_after_end_date(service: ActivityService) -> None:
    t = service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=3, now=NOW)
    assert not t.is_active(t.end_date + timedelta(seconds=1))


def test_creator_is_added_as_participant(service: ActivityService, repository: ActivityRepository) -> None:
    t = service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=7, now=NOW)
    alice = service.ensure_user(1, "alice")
    assert repository.is_tournament_participant(t.id, alice.id)


def test_cannot_start_two_active_tournaments(service: ActivityService) -> None:
    service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=7, now=NOW)
    with pytest.raises(TournamentAlreadyActiveError) as exc_info:
        service.start_tournament(CHAT_ID, "Test Group", 2, "bob", days=5, now=NOW)
    assert exc_info.value.tournament.telegram_chat_id == CHAT_ID


def test_can_start_after_expiry(service: ActivityService) -> None:
    service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=3, now=NOW)
    t2 = service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=5, now=NOW + timedelta(days=4))
    assert t2.is_active(NOW + timedelta(days=4))


def test_invalid_days_raises(service: ActivityService) -> None:
    with pytest.raises(InvalidTournamentDaysError):
        service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=0, now=NOW)
    with pytest.raises(InvalidTournamentDaysError):
        service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=366, now=NOW)


# ---------------------------------------------------------------- /join tests

def test_join_adds_participant(service: ActivityService, repository: ActivityRepository) -> None:
    t = service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=7, now=NOW)
    count = service.join_tournament(CHAT_ID, 2, "bob", now=NOW)
    bob = service.ensure_user(2, "bob")
    assert count == 2
    assert repository.is_tournament_participant(t.id, bob.id)


def test_join_no_active_tournament(service: ActivityService) -> None:
    with pytest.raises(NoActiveTournamentError):
        service.join_tournament(CHAT_ID, 1, "alice", now=NOW)


def test_join_already_joined(service: ActivityService) -> None:
    service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=7, now=NOW)
    with pytest.raises(AlreadyJoinedError):
        service.join_tournament(CHAT_ID, 1, "alice", now=NOW)


def test_join_group_full(service: ActivityService) -> None:
    from bot.constants import MAX_GROUP_MEMBERS
    service.start_tournament(CHAT_ID, "Test Group", 1, "user1", days=7, now=NOW)
    for i in range(2, MAX_GROUP_MEMBERS + 1):
        service.join_tournament(CHAT_ID, i, f"user{i}", now=NOW)
    with pytest.raises(GroupFullError):
        service.join_tournament(CHAT_ID, MAX_GROUP_MEMBERS + 1, "extra", now=NOW)


def test_join_after_tournament_ends(service: ActivityService) -> None:
    service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=3, now=NOW)
    with pytest.raises(NoActiveTournamentError):
        service.join_tournament(CHAT_ID, 2, "bob", now=NOW + timedelta(days=4))


# --------------------------------------------------------------- /finish tests

def test_finish_ends_tournament(service: ActivityService) -> None:
    service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=7, now=NOW)
    finished, _ = service.finish_tournament(CHAT_ID, now=NOW + timedelta(days=2))
    assert finished.finished_at is not None
    assert not finished.is_active(NOW + timedelta(days=2))


def test_finish_no_active_tournament(service: ActivityService) -> None:
    with pytest.raises(NoActiveTournamentError):
        service.finish_tournament(CHAT_ID, now=NOW)


def test_can_start_after_finish(service: ActivityService) -> None:
    service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=7, now=NOW)
    service.finish_tournament(CHAT_ID, now=NOW + timedelta(days=1))
    t2 = service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=5, now=NOW + timedelta(days=1))
    assert t2.is_active(NOW + timedelta(days=1))


def test_finish_returns_leaderboard(service: ActivityService, repository: ActivityRepository) -> None:
    service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=7, now=NOW)
    service.join_tournament(CHAT_ID, 2, "bob", now=NOW)
    alice = service.ensure_user(1, "alice")
    repository.add_activity_entry(alice.id, "steps", 500, NOW + timedelta(hours=1))
    _, entries = service.finish_tournament(CHAT_ID, now=NOW + timedelta(days=2))
    assert len(entries) == 2
    assert entries[0].user.username == "alice"
    assert entries[0].score == 5


# ------------------------------------------------------------- /results tests

def test_results_no_tournament(service: ActivityService) -> None:
    tournament, entries = service.get_tournament_results(CHAT_ID)
    assert tournament is None
    assert entries == []


def test_results_show_last_tournament_after_expiry(service: ActivityService) -> None:
    service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=3, now=NOW)
    after_end = NOW + timedelta(days=5)
    tournament, entries = service.get_tournament_results(CHAT_ID, now=after_end)
    assert tournament is not None
    assert not tournament.is_active(after_end)


def test_leaderboard_uses_normalized_score(service: ActivityService, repository: ActivityRepository) -> None:
    service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=7, now=NOW)
    service.join_tournament(CHAT_ID, 2, "bob", now=NOW)
    alice = service.ensure_user(1, "alice")
    bob = service.ensure_user(2, "bob")
    repository.add_activity_entry(alice.id, "steps", 100, NOW + timedelta(days=1))
    repository.add_activity_entry(alice.id, "squats", 20, NOW + timedelta(days=2))
    repository.add_activity_entry(bob.id, "steps", 200, NOW + timedelta(days=1))
    # Entry before tournament — should NOT count
    repository.add_activity_entry(alice.id, "steps", 50, NOW - timedelta(days=1))

    _, entries = service.get_tournament_results(CHAT_ID)
    assert entries[0].user.username == "alice"
    assert entries[0].score == 11
    assert entries[1].user.username == "bob"
    assert entries[1].score == 2


def test_leaderboard_excludes_entries_after_end_date(service: ActivityService, repository: ActivityRepository) -> None:
    service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=3, now=NOW)
    alice = service.ensure_user(1, "alice")
    repository.add_activity_entry(alice.id, "steps", 100, NOW + timedelta(days=2))
    # After end_date (exclusive) — should NOT count
    repository.add_activity_entry(alice.id, "steps", 999, NOW + timedelta(days=3))
    _, entries = service.get_tournament_results(CHAT_ID)
    assert entries[0].score == 1


def test_results_and_finish_use_same_tournament(service: ActivityService, repository: ActivityRepository) -> None:
    # Regression: /results used get_latest_tournament while /finish used get_active_tournament,
    # which can return different records if a newer expired tournament coexists with an older
    # active one. Both should always agree on the active tournament when one exists.
    service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=7, now=NOW)
    service.join_tournament(CHAT_ID, 2, "bob", now=NOW)
    alice = service.ensure_user(1, "alice")
    repository.add_activity_entry(alice.id, "steps", 100, NOW + timedelta(days=1))

    mid = NOW + timedelta(days=2)
    t_results, entries_before = service.get_tournament_results(CHAT_ID, now=mid)
    t_finish, entries_after = service.finish_tournament(CHAT_ID, now=mid)

    assert t_results is not None
    assert t_results.id == t_finish.id
    assert len(entries_before) == len(entries_after)


def test_non_participant_not_in_leaderboard(service: ActivityService, repository: ActivityRepository) -> None:
    service.start_tournament(CHAT_ID, "Test Group", 1, "alice", days=7, now=NOW)
    # Bob logs activity but never calls /join
    bob = service.ensure_user(2, "bob")
    repository.add_activity_entry(bob.id, "steps", 5000, NOW + timedelta(days=1))
    _, entries = service.get_tournament_results(CHAT_ID)
    usernames = [e.user.username for e in entries]
    assert "bob" not in usernames
