from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from bot.constants import ACTIVITY_KEYS
from bot.models import LeaderboardEntry, Tournament, User
from bot.scoring import calculate_score


class ActivityRepository:
    def __init__(self, database_path: str):
        self.database_path = database_path

    def init_db(self) -> None:
        db_path = Path(self.database_path)
        if db_path.parent != Path("."):
            db_path.parent.mkdir(parents=True, exist_ok=True)

        with self._connect() as conn:
            conn.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL UNIQUE,
                    username TEXT,
                    preferred_language TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activity_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    activity_type TEXT NOT NULL,
                    amount INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE INDEX IF NOT EXISTS idx_entries_user_activity_created
                ON activity_entries(user_id, activity_type, created_at);

                CREATE TABLE IF NOT EXISTS group_chats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_chat_id INTEGER NOT NULL UNIQUE,
                    title TEXT,
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS tournaments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_chat_id INTEGER NOT NULL,
                    started_by_user_id INTEGER NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    finished_at TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (group_chat_id) REFERENCES group_chats(id),
                    FOREIGN KEY (started_by_user_id) REFERENCES users(id)
                );

                CREATE TABLE IF NOT EXISTS tournament_participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tournament_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    joined_at TEXT NOT NULL,
                    FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(tournament_id, user_id)
                );
                """
            )
            # Column migrations for existing databases
            user_columns = {
                str(r["name"])
                for r in conn.execute("PRAGMA table_info(users)").fetchall()
            }
            if "preferred_language" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN preferred_language TEXT")
            if "first_name" not in user_columns:
                conn.execute("ALTER TABLE users ADD COLUMN first_name TEXT")

            tournament_columns = {
                str(r["name"])
                for r in conn.execute("PRAGMA table_info(tournaments)").fetchall()
            }
            if "finished_at" not in tournament_columns:
                conn.execute("ALTER TABLE tournaments ADD COLUMN finished_at TEXT")

    # ------------------------------------------------------------------ users

    def get_or_create_user(
        self,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None = None,
        now: datetime | None = None,
    ) -> User:
        current_time = now or datetime.now()
        with self._connect() as conn:
            row = _get_user_row_by_telegram_id(conn, telegram_user_id)

            if row is None:
                cursor = conn.execute(
                    """
                    INSERT INTO users (telegram_user_id, username, first_name, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (telegram_user_id, username, first_name, _to_db_datetime(current_time)),
                )
                user_id = int(cursor.lastrowid)
            else:
                user_id = int(row["id"])
                if username != row["username"] or first_name != row["first_name"]:
                    conn.execute(
                        "UPDATE users SET username = ?, first_name = ? WHERE id = ?",
                        (username, first_name, user_id),
                    )

            row = _get_user_row_by_id(conn, user_id)
            return _user_from_row(row)

    def set_user_language(self, telegram_user_id: int, language: str) -> User:
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET preferred_language = ? WHERE telegram_user_id = ?",
                (language, telegram_user_id),
            )
            row = _get_user_row_by_telegram_id(conn, telegram_user_id)
            if row is None:
                raise RuntimeError(f"User not found for telegram_user_id={telegram_user_id}")
            return _user_from_row(row)

    # --------------------------------------------------------- activity entries

    def add_activity_entry(
        self,
        user_id: int,
        activity_type: str,
        amount: int,
        created_at: datetime,
    ) -> None:
        _ensure_activity_type(activity_type)
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO activity_entries (user_id, activity_type, amount, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, activity_type, amount, _to_db_datetime(created_at)),
            )

    def delete_activity_entries(self, user_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM activity_entries WHERE user_id = ?",
                (user_id,),
            )

    def get_activity_total(
        self,
        user_id: int,
        activity_type: str,
        start: datetime,
        end: datetime,
    ) -> int:
        _ensure_activity_type(activity_type)
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS total
                FROM activity_entries
                WHERE user_id = ?
                  AND activity_type = ?
                  AND created_at >= ?
                  AND created_at < ?
                """,
                (user_id, activity_type, _to_db_datetime(start), _to_db_datetime(end)),
            ).fetchone()
            return int(row["total"])

    def get_totals_by_activity(
        self,
        user_id: int,
        start: datetime,
        end: datetime,
    ) -> dict[str, int]:
        totals = {key: 0 for key in ACTIVITY_KEYS}
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT activity_type, COALESCE(SUM(amount), 0) AS total
                FROM activity_entries
                WHERE user_id = ?
                  AND created_at >= ?
                  AND created_at < ?
                GROUP BY activity_type
                """,
                (user_id, _to_db_datetime(start), _to_db_datetime(end)),
            ).fetchall()

        for row in rows:
            totals[str(row["activity_type"])] = int(row["total"])
        return totals

    # ------------------------------------------------------------ group chats

    def get_or_create_group_chat_id(
        self,
        telegram_chat_id: int,
        title: str | None,
        now: datetime | None = None,
    ) -> int:
        current_time = now or datetime.now()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, title FROM group_chats WHERE telegram_chat_id = ?",
                (telegram_chat_id,),
            ).fetchone()
            if row is None:
                cursor = conn.execute(
                    "INSERT INTO group_chats (telegram_chat_id, title, created_at) VALUES (?, ?, ?)",
                    (telegram_chat_id, title, _to_db_datetime(current_time)),
                )
                return int(cursor.lastrowid)
            group_chat_id = int(row["id"])
            if title and title != row["title"]:
                conn.execute(
                    "UPDATE group_chats SET title = ? WHERE id = ?",
                    (title, group_chat_id),
                )
            return group_chat_id

    # ------------------------------------------------------------ tournaments

    def create_tournament(
        self,
        group_chat_id: int,
        started_by_user_id: int,
        start_date: datetime,
        end_date: datetime,
        now: datetime | None = None,
    ) -> Tournament:
        current_time = now or datetime.now()
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO tournaments (group_chat_id, started_by_user_id, start_date, end_date, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    group_chat_id,
                    started_by_user_id,
                    _to_db_datetime(start_date),
                    _to_db_datetime(end_date),
                    _to_db_datetime(current_time),
                ),
            )
            tournament_id = int(cursor.lastrowid)
            row = conn.execute(
                """
                SELECT t.*, gc.telegram_chat_id
                FROM tournaments t
                JOIN group_chats gc ON gc.id = t.group_chat_id
                WHERE t.id = ?
                """,
                (tournament_id,),
            ).fetchone()
            return _tournament_from_row(row)

    def get_active_tournament(
        self,
        telegram_chat_id: int,
        now: datetime | None = None,
    ) -> Tournament | None:
        current_time = now or datetime.now()
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT t.*, gc.telegram_chat_id
                FROM tournaments t
                JOIN group_chats gc ON gc.id = t.group_chat_id
                WHERE gc.telegram_chat_id = ?
                  AND t.end_date > ?
                  AND t.finished_at IS NULL
                ORDER BY t.created_at DESC
                LIMIT 1
                """,
                (telegram_chat_id, _to_db_datetime(current_time)),
            ).fetchone()
            return _tournament_from_row(row) if row else None

    def get_latest_tournament(self, telegram_chat_id: int) -> Tournament | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT t.*, gc.telegram_chat_id
                FROM tournaments t
                JOIN group_chats gc ON gc.id = t.group_chat_id
                WHERE gc.telegram_chat_id = ?
                ORDER BY t.created_at DESC
                LIMIT 1
                """,
                (telegram_chat_id,),
            ).fetchone()
            return _tournament_from_row(row) if row else None

    def finish_tournament(self, tournament_id: int, now: datetime | None = None) -> Tournament:
        current_time = now or datetime.now()
        with self._connect() as conn:
            conn.execute(
                "UPDATE tournaments SET finished_at = ? WHERE id = ?",
                (_to_db_datetime(current_time), tournament_id),
            )
            row = conn.execute(
                """
                SELECT t.*, gc.telegram_chat_id
                FROM tournaments t
                JOIN group_chats gc ON gc.id = t.group_chat_id
                WHERE t.id = ?
                """,
                (tournament_id,),
            ).fetchone()
            return _tournament_from_row(row)

    # ------------------------------------------------- tournament participants

    def add_tournament_participant(
        self,
        tournament_id: int,
        user_id: int,
        now: datetime | None = None,
    ) -> None:
        current_time = now or datetime.now()
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO tournament_participants (tournament_id, user_id, joined_at) VALUES (?, ?, ?)",
                (tournament_id, user_id, _to_db_datetime(current_time)),
            )

    def get_tournament_participant_count(self, tournament_id: int) -> int:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS cnt FROM tournament_participants WHERE tournament_id = ?",
                (tournament_id,),
            ).fetchone()
            return int(row["cnt"])

    def is_tournament_participant(self, tournament_id: int, user_id: int) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM tournament_participants WHERE tournament_id = ? AND user_id = ?",
                (tournament_id, user_id),
            ).fetchone()
            return row is not None

    def get_tournament_leaderboard(
        self,
        tournament_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> list[LeaderboardEntry]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT u.id, u.telegram_user_id, u.username, u.first_name, u.preferred_language, u.created_at,
                       ae.activity_type,
                       COALESCE(SUM(ae.amount), 0) AS total
                FROM tournament_participants tp
                JOIN users u ON u.id = tp.user_id
                LEFT JOIN activity_entries ae
                    ON ae.user_id = u.id
                    AND ae.created_at >= ?
                    AND ae.created_at < ?
                WHERE tp.tournament_id = ?
                GROUP BY u.id, ae.activity_type
                """,
                (_to_db_datetime(start_date), _to_db_datetime(end_date), tournament_id),
            ).fetchall()
        grouped: dict[int, dict[str, object]] = {}
        for row in rows:
            user_id = int(row["id"])
            if user_id not in grouped:
                grouped[user_id] = {
                    "user": _user_from_row(row),
                    "totals": {key: 0 for key in ACTIVITY_KEYS},
                }
            activity_type = row["activity_type"]
            if activity_type is not None:
                grouped[user_id]["totals"][str(activity_type)] = int(row["total"])

        ranked = sorted(
            (
                (data["user"], calculate_score(data["totals"]))
                for data in grouped.values()
            ),
            key=lambda item: (
                -item[1],
                item[0].username or "",
                item[0].first_name or "",
                item[0].telegram_user_id,
            ),
        )
        return [
            LeaderboardEntry(rank=rank, user=user, score=score)
            for rank, (user, score) in enumerate(ranked, start=1)
        ]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn


def _ensure_activity_type(activity_type: str) -> None:
    if activity_type not in ACTIVITY_KEYS:
        raise ValueError(f"Unknown activity type: {activity_type}")


def _get_user_row_by_id(conn: sqlite3.Connection, user_id: int) -> Any:
    return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def _get_user_row_by_telegram_id(conn: sqlite3.Connection, telegram_user_id: int) -> Any:
    return conn.execute(
        "SELECT * FROM users WHERE telegram_user_id = ?",
        (telegram_user_id,),
    ).fetchone()


def _to_db_datetime(value: datetime) -> str:
    return value.replace(microsecond=0).isoformat()


def _tournament_from_row(row: Any) -> Tournament:
    return Tournament(
        id=int(row["id"]),
        group_chat_id=int(row["group_chat_id"]),
        telegram_chat_id=int(row["telegram_chat_id"]),
        started_by_user_id=int(row["started_by_user_id"]),
        start_date=datetime.fromisoformat(row["start_date"]),
        end_date=datetime.fromisoformat(row["end_date"]),
        finished_at=datetime.fromisoformat(row["finished_at"]) if row["finished_at"] else None,
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def _user_from_row(row: Any) -> User:
    return User(
        id=int(row["id"]),
        telegram_user_id=int(row["telegram_user_id"]),
        username=row["username"],
        first_name=row["first_name"],
        preferred_language=row["preferred_language"],
        created_at=datetime.fromisoformat(row["created_at"]),
    )
