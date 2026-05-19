from __future__ import annotations

from datetime import datetime, timedelta


def today_range(now: datetime) -> tuple[datetime, datetime]:
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def week_range(now: datetime) -> tuple[datetime, datetime]:
    today_start, _ = today_range(now)
    start = today_start - timedelta(days=today_start.weekday())
    return start, start + timedelta(days=7)


def month_range(now: datetime) -> tuple[datetime, datetime]:
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def last_day_range(now: datetime) -> tuple[datetime, datetime]:
    today_start, _ = today_range(now)
    return today_start - timedelta(days=1), today_start


def last_week_range(now: datetime) -> tuple[datetime, datetime]:
    current_week_start, _ = week_range(now)
    return current_week_start - timedelta(days=7), current_week_start


def last_month_range(now: datetime) -> tuple[datetime, datetime]:
    current_month_start, _ = month_range(now)
    if current_month_start.month == 1:
        prev = current_month_start.replace(year=current_month_start.year - 1, month=12)
    else:
        prev = current_month_start.replace(month=current_month_start.month - 1)
    return prev, current_month_start
