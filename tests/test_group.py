from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from bot.repository import ActivityRepository
from bot.services import (
    ActivityService,
    last_day_range,
    last_month_range,
    last_week_range,
    today_range,
    week_range,
    month_range,
)


@pytest.fixture()
def repository(tmp_path):
    repo = ActivityRepository(str(tmp_path / "activity.db"))
    repo.init_db()
    return repo


@pytest.fixture()
def service(repository):
    return ActivityService(repository)


NOW = datetime(2026, 5, 14, 10, 0, 0)  # Thursday
CHAT_ID = -100123456789


# --------------------------------------------------------- membership tests

def test_register_group_member_creates_membership(
    service: ActivityService, repository: ActivityRepository
) -> None:
    service.register_group_member(CHAT_ID, "Test Group", 1, "alice", now=NOW)
    group_chat_id = repository.get_or_create_group_chat_id(CHAT_ID, "Test Group", NOW)
    day_start, day_end = today_range(NOW)
    entries = repository.get_group_leaderboard(group_chat_id, day_start, day_end)
    assert len(entries) == 1
    assert entries[0].user.username == "alice"


def test_register_group_member_is_idempotent(
    service: ActivityService, repository: ActivityRepository
) -> None:
    service.register_group_member(CHAT_ID, "Test Group", 1, "alice", now=NOW)
    service.register_group_member(CHAT_ID, "Test Group", 1, "alice", now=NOW)
    group_chat_id = repository.get_or_create_group_chat_id(CHAT_ID, "Test Group", NOW)
    day_start, day_end = today_range(NOW)
    entries = repository.get_group_leaderboard(group_chat_id, day_start, day_end)
    assert len(entries) == 1


# ---------------------------------------------------- leaderboard ranking tests

def test_group_leaderboard_ranks_by_score(
    service: ActivityService, repository: ActivityRepository
) -> None:
    service.register_group_member(CHAT_ID, "Test Group", 1, "alice", now=NOW)
    service.register_group_member(CHAT_ID, "Test Group", 2, "bob", now=NOW)
    alice = service.ensure_user(1, "alice")
    bob = service.ensure_user(2, "bob")
    repository.add_activity_entry(alice.id, "steps", 1000, NOW)
    repository.add_activity_entry(bob.id, "steps", 500, NOW)

    group_chat_id = repository.get_or_create_group_chat_id(CHAT_ID, "Test Group", NOW)
    day_start, day_end = today_range(NOW)
    entries = repository.get_group_leaderboard(group_chat_id, day_start, day_end)

    assert entries[0].user.username == "alice"
    assert entries[0].score == 10
    assert entries[0].rank == 1
    assert entries[1].user.username == "bob"
    assert entries[1].score == 5
    assert entries[1].rank == 2


def test_group_leaderboard_excludes_non_members(
    service: ActivityService, repository: ActivityRepository
) -> None:
    service.register_group_member(CHAT_ID, "Test Group", 1, "alice", now=NOW)
    bob = service.ensure_user(2, "bob")
    repository.add_activity_entry(bob.id, "steps", 5000, NOW)

    group_chat_id = repository.get_or_create_group_chat_id(CHAT_ID, "Test Group", NOW)
    day_start, day_end = today_range(NOW)
    entries = repository.get_group_leaderboard(group_chat_id, day_start, day_end)

    assert all(e.user.username != "bob" for e in entries)


def test_group_leaderboard_top_10_limit(
    service: ActivityService, repository: ActivityRepository
) -> None:
    for i in range(1, 16):
        service.register_group_member(CHAT_ID, "Test Group", i, f"user{i}", now=NOW)
        user = service.ensure_user(i, f"user{i}")
        repository.add_activity_entry(user.id, "steps", i * 100, NOW)

    group_chat_id = repository.get_or_create_group_chat_id(CHAT_ID, "Test Group", NOW)
    day_start, day_end = today_range(NOW)
    entries = repository.get_group_leaderboard(group_chat_id, day_start, day_end, limit=10)

    assert len(entries) == 10
    assert entries[0].score >= entries[-1].score


def test_group_leaderboard_members_with_no_activity_appear(
    service: ActivityService, repository: ActivityRepository
) -> None:
    service.register_group_member(CHAT_ID, "Test Group", 1, "alice", now=NOW)
    service.register_group_member(CHAT_ID, "Test Group", 2, "bob", now=NOW)
    alice = service.ensure_user(1, "alice")
    repository.add_activity_entry(alice.id, "steps", 1000, NOW)

    group_chat_id = repository.get_or_create_group_chat_id(CHAT_ID, "Test Group", NOW)
    day_start, day_end = today_range(NOW)
    entries = repository.get_group_leaderboard(group_chat_id, day_start, day_end)

    usernames = [e.user.username for e in entries]
    assert "alice" in usernames
    assert "bob" in usernames
    assert entries[0].user.username == "alice"


# ------------------------------------------------------- period range tests

def test_last_day_range_covers_yesterday(
    service: ActivityService, repository: ActivityRepository
) -> None:
    service.register_group_member(CHAT_ID, "Test Group", 1, "alice", now=NOW)
    alice = service.ensure_user(1, "alice")
    yesterday = NOW - timedelta(days=1)
    repository.add_activity_entry(alice.id, "steps", 1000, yesterday)
    repository.add_activity_entry(alice.id, "steps", 500, NOW)  # today — should not count

    group_chat_id = repository.get_or_create_group_chat_id(CHAT_ID, "Test Group", NOW)
    start, end = last_day_range(NOW)
    entries = repository.get_group_leaderboard(group_chat_id, start, end)

    assert len(entries) == 1
    assert entries[0].score == 10


def test_last_week_range_excludes_current_week(
    service: ActivityService, repository: ActivityRepository
) -> None:
    # NOW = 2026-05-14 (Thursday); current week starts 2026-05-11 (Monday)
    # last week: 2026-05-04 to 2026-05-11
    service.register_group_member(CHAT_ID, "Test Group", 1, "alice", now=NOW)
    alice = service.ensure_user(1, "alice")
    last_week_day = datetime(2026, 5, 7, 10, 0, 0)  # Wednesday last week
    repository.add_activity_entry(alice.id, "steps", 1000, last_week_day)
    repository.add_activity_entry(alice.id, "steps", 500, NOW)  # this week — should not count

    group_chat_id = repository.get_or_create_group_chat_id(CHAT_ID, "Test Group", NOW)
    start, end = last_week_range(NOW)
    entries = repository.get_group_leaderboard(group_chat_id, start, end)

    assert len(entries) == 1
    assert entries[0].score == 10


def test_last_month_range_excludes_current_month(
    service: ActivityService, repository: ActivityRepository
) -> None:
    # NOW = 2026-05-14; last month = April 2026
    service.register_group_member(CHAT_ID, "Test Group", 1, "alice", now=NOW)
    alice = service.ensure_user(1, "alice")
    last_month_day = datetime(2026, 4, 15, 10, 0, 0)
    repository.add_activity_entry(alice.id, "steps", 1000, last_month_day)
    repository.add_activity_entry(alice.id, "steps", 500, NOW)  # this month — should not count

    group_chat_id = repository.get_or_create_group_chat_id(CHAT_ID, "Test Group", NOW)
    start, end = last_month_range(NOW)
    entries = repository.get_group_leaderboard(group_chat_id, start, end)

    assert len(entries) == 1
    assert entries[0].score == 10


def test_last_week_range_january_boundary() -> None:
    # Edge case: current week straddles Jan/Feb boundary
    # 2026-01-05 is Monday; last week would be 2025-12-29 to 2026-01-05
    now = datetime(2026, 1, 7, 10, 0, 0)
    start, end = last_week_range(now)
    assert start == datetime(2025, 12, 29, 0, 0, 0)
    assert end == datetime(2026, 1, 5, 0, 0, 0)


def test_last_month_range_january() -> None:
    # Edge case: current month is January → last month is December of prior year
    now = datetime(2026, 1, 15, 10, 0, 0)
    start, end = last_month_range(now)
    assert start == datetime(2025, 12, 1, 0, 0, 0)
    assert end == datetime(2026, 1, 1, 0, 0, 0)


# ------------------------------------------------ cross-group isolation tests

def test_different_groups_are_isolated(
    service: ActivityService, repository: ActivityRepository
) -> None:
    chat_id_2 = -100987654321
    service.register_group_member(CHAT_ID, "Group 1", 1, "alice", now=NOW)
    service.register_group_member(chat_id_2, "Group 2", 2, "bob", now=NOW)
    alice = service.ensure_user(1, "alice")
    bob = service.ensure_user(2, "bob")
    repository.add_activity_entry(alice.id, "steps", 1000, NOW)
    repository.add_activity_entry(bob.id, "steps", 2000, NOW)

    group_chat_id_1 = repository.get_or_create_group_chat_id(CHAT_ID, "Group 1", NOW)
    day_start, day_end = today_range(NOW)
    entries = repository.get_group_leaderboard(group_chat_id_1, day_start, day_end)

    assert len(entries) == 1
    assert entries[0].user.username == "alice"


def test_member_in_multiple_groups(
    service: ActivityService, repository: ActivityRepository
) -> None:
    chat_id_2 = -100987654321
    service.register_group_member(CHAT_ID, "Group 1", 1, "alice", now=NOW)
    service.register_group_member(chat_id_2, "Group 2", 1, "alice", now=NOW)

    group_chat_id_1 = repository.get_or_create_group_chat_id(CHAT_ID, "Group 1", NOW)
    group_chat_id_2 = repository.get_or_create_group_chat_id(chat_id_2, "Group 2", NOW)
    day_start, day_end = today_range(NOW)

    entries_1 = repository.get_group_leaderboard(group_chat_id_1, day_start, day_end)
    entries_2 = repository.get_group_leaderboard(group_chat_id_2, day_start, day_end)

    assert len(entries_1) == 1
    assert len(entries_2) == 1
    assert entries_1[0].user.username == "alice"
    assert entries_2[0].user.username == "alice"


# --------------------------------------------------------- migration test

def test_init_db_migration_partial_tournaments_already_dropped(tmp_path) -> None:
    """tournament_participants exists but tournaments was already dropped — must not crash."""
    import sqlite3
    db_path = str(tmp_path / "partial.db")
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL UNIQUE,
            username TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE group_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_chat_id INTEGER NOT NULL UNIQUE,
            title TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE tournament_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TEXT NOT NULL
        );
    """)
    conn.close()

    repo = ActivityRepository(db_path)
    repo.init_db()  # must not raise

    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()

    assert "tournament_participants" not in tables
    assert "group_members" in tables


def test_init_db_migration_drops_tournament_tables(tmp_path) -> None:
    import sqlite3
    db_path = str(tmp_path / "legacy.db")
    # Create a database that looks like the old schema
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_user_id INTEGER NOT NULL UNIQUE,
            username TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE group_chats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_chat_id INTEGER NOT NULL UNIQUE,
            title TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE tournaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_chat_id INTEGER NOT NULL,
            started_by_user_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            finished_at TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE tournament_participants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tournament_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            joined_at TEXT NOT NULL,
            UNIQUE(tournament_id, user_id)
        );
        INSERT INTO users (telegram_user_id, username, created_at) VALUES (1, 'alice', '2026-01-01T00:00:00');
        INSERT INTO group_chats (telegram_chat_id, title, created_at) VALUES (-100123, 'Test', '2026-01-01T00:00:00');
        INSERT INTO tournaments (group_chat_id, started_by_user_id, start_date, end_date, created_at)
            VALUES (1, 1, '2026-01-01T00:00:00', '2026-01-08T00:00:00', '2026-01-01T00:00:00');
        INSERT INTO tournament_participants (tournament_id, user_id, joined_at) VALUES (1, 1, '2026-01-01T00:00:00');
    """)
    conn.close()

    repo = ActivityRepository(db_path)
    repo.init_db()

    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()

    assert "tournaments" not in tables
    assert "tournament_participants" not in tables
    assert "group_members" in tables

    # The former tournament participant should have been migrated to group_members
    conn = sqlite3.connect(db_path)
    count = conn.execute("SELECT COUNT(*) FROM group_members").fetchone()[0]
    conn.close()
    assert count == 1
