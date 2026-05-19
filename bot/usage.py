from __future__ import annotations

import sqlite3
import subprocess
from datetime import datetime, timedelta

from bot.config import load_settings, sqlite_path_from_url


def main() -> int:
    settings = load_settings()
    db_path = sqlite_path_from_url(settings.database_url)

    try:
        conn = sqlite3.connect(db_path)
    except Exception as e:
        print(f"Cannot open database: {e}")
        return 1

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    today_str = today_start.isoformat()
    week_str = week_start.isoformat()

    with conn:
        total_users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        users_today = conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM activity_entries WHERE created_at >= ?", (today_str,)
        ).fetchone()[0]
        users_this_week = conn.execute(
            "SELECT COUNT(DISTINCT user_id) FROM activity_entries WHERE created_at >= ?", (week_str,)
        ).fetchone()[0]
        new_users_today = conn.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= ?", (today_str,)
        ).fetchone()[0]
        new_users_this_week = conn.execute(
            "SELECT COUNT(*) FROM users WHERE created_at >= ?", (week_str,)
        ).fetchone()[0]
        total_groups = conn.execute("SELECT COUNT(*) FROM group_chats").fetchone()[0]
        total_entries = conn.execute("SELECT COUNT(*) FROM activity_entries").fetchone()[0]
        entries_today = conn.execute(
            "SELECT COUNT(*) FROM activity_entries WHERE created_at >= ?", (today_str,)
        ).fetchone()[0]
        entries_this_week = conn.execute(
            "SELECT COUNT(*) FROM activity_entries WHERE created_at >= ?", (week_str,)
        ).fetchone()[0]
        activity_rows = conn.execute(
            "SELECT activity_type, COUNT(*) AS cnt FROM activity_entries GROUP BY activity_type ORDER BY cnt DESC"
        ).fetchall()

    try:
        version = subprocess.check_output(
            ["git", "describe", "--tags", "--always"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except Exception:
        version = "unknown"

    print(f"Version:  {version}")
    print(f"Database: {db_path}")
    print(f"Date:     {now.strftime('%Y-%m-%d %H:%M')}")
    print()
    print("Users")
    print(f"  Total:          {total_users}")
    print(f"  New today:      {new_users_today}")
    print(f"  New this week:  {new_users_this_week}")
    print(f"  Active today:   {users_today}")
    print(f"  Active week:    {users_this_week}")
    print()
    print("Groups")
    print(f"  Total:          {total_groups}")
    print()
    print("Activity entries")
    print(f"  Total:          {total_entries}")
    print(f"  Today:          {entries_today}")
    print(f"  This week:      {entries_this_week}")
    if activity_rows:
        print()
        print("  By type:")
        for activity_type, count in activity_rows:
            print(f"    {activity_type:<12} {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
