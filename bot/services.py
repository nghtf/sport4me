from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from bot.constants import ACTIVITIES, ACTIVITY_KEYS, MAX_TOTAL, MIN_TOTAL
from bot.models import LeaderboardEntry, PeriodStats, User
from bot.repository import ActivityRepository
from bot.time_ranges import (
    last_day_range,
    last_month_range,
    last_week_range,
    month_range,
    today_range,
    week_range,
)


class PendingNotFoundError(RuntimeError):
    pass


@dataclass(frozen=True)
class LimitError(RuntimeError):
    current_total: int
    attempted_total: int


@dataclass(frozen=True)
class ApplyResult:
    activity_key: str
    amount: int
    today_total: int


class ActivityService:
    def __init__(self, repository: ActivityRepository):
        self.repository = repository
        self._pending_amounts: dict[int, int] = {}

    def ensure_user(
        self,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None = None,
        language_code: str | None = None,
        now: datetime | None = None,
    ) -> User:
        return self.repository.get_or_create_user(
            telegram_user_id, username,
            first_name=first_name, language_code=language_code, now=now,
        )

    def set_pending_amount(self, telegram_user_id: int, amount: int) -> None:
        self._pending_amounts[telegram_user_id] = amount

    def set_user_language(
        self,
        telegram_user_id: int,
        username: str | None,
        language: str,
        now: datetime | None = None,
    ) -> User:
        self.ensure_user(telegram_user_id, username, now=now)
        return self.repository.set_user_language(telegram_user_id, language)

    def get_pending_amount(self, telegram_user_id: int) -> int | None:
        return self._pending_amounts.get(telegram_user_id)

    def clear_pending_amount(self, telegram_user_id: int) -> int | None:
        return self._pending_amounts.pop(telegram_user_id, None)

    def clear_all_stats(
        self,
        telegram_user_id: int,
        username: str | None,
        now: datetime | None = None,
    ) -> User:
        user = self.ensure_user(telegram_user_id, username, now=now)
        self.repository.delete_activity_entries(user.id)
        self.clear_pending_amount(telegram_user_id)
        return user

    def apply_pending_amount(
        self,
        telegram_user_id: int,
        username: str | None,
        activity_key: str,
        now: datetime | None = None,
    ) -> ApplyResult:
        if activity_key not in ACTIVITIES:
            raise ValueError(f"Unknown activity type: {activity_key}")

        amount = self._pending_amounts.get(telegram_user_id)
        if amount is None:
            raise PendingNotFoundError("No pending amount for user")

        current_time = now or datetime.now()
        user = self.ensure_user(telegram_user_id, username, now=current_time)
        day_start, day_end = today_range(current_time)
        current_total = self.repository.get_activity_total(user.id, activity_key, day_start, day_end)
        attempted_total = current_total + amount

        if not MIN_TOTAL <= attempted_total <= MAX_TOTAL:
            self.clear_pending_amount(telegram_user_id)
            raise LimitError(current_total=current_total, attempted_total=attempted_total)

        self.repository.add_activity_entry(user.id, activity_key, amount, current_time)
        self.clear_pending_amount(telegram_user_id)
        return ApplyResult(activity_key, amount, attempted_total)

    def get_period_stats(
        self,
        telegram_user_id: int,
        username: str | None,
        now: datetime | None = None,
    ) -> PeriodStats:
        current_time = now or datetime.now()
        user = self.ensure_user(telegram_user_id, username, now=current_time)
        today_start, today_end = today_range(current_time)
        week_start, week_end = week_range(current_time)
        month_start, month_end = month_range(current_time)

        yesterday_start, yesterday_end = last_day_range(current_time)
        return PeriodStats(
            yesterday=self.repository.get_totals_by_activity(user.id, yesterday_start, yesterday_end),
            today=self.repository.get_totals_by_activity(user.id, today_start, today_end),
            week=self.repository.get_totals_by_activity(user.id, week_start, week_end),
            month=self.repository.get_totals_by_activity(user.id, month_start, month_end),
        )

    def get_detailed_stats(
        self,
        telegram_user_id: int,
        username: str | None,
        period: str,
        last: bool = False,
        now: datetime | None = None,
    ) -> list[tuple[date, int]]:
        current_time = now or datetime.now()
        user = self.ensure_user(telegram_user_id, username, now=current_time)

        if period == "month":
            start, end = last_month_range(current_time) if last else month_range(current_time)
        else:
            start, end = last_week_range(current_time) if last else week_range(current_time)

        if not last:
            _, tomorrow = today_range(current_time)
            end = min(end, tomorrow)

        return self.repository.get_daily_scores(user.id, start, end)

    def register_group_member(
        self,
        telegram_chat_id: int,
        chat_title: str | None,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None = None,
        language_code: str | None = None,
        now: datetime | None = None,
    ) -> None:
        current_time = now or datetime.now()
        user = self.ensure_user(
            telegram_user_id, username,
            first_name=first_name, language_code=language_code, now=current_time,
        )
        group_chat_id = self.repository.get_or_create_group_chat_id(telegram_chat_id, chat_title, current_time)
        self.repository.add_group_member(group_chat_id, user.id, current_time)

    def get_group_top(
        self,
        telegram_chat_id: int,
        chat_title: str | None,
        start: datetime,
        end: datetime,
        now: datetime | None = None,
        limit: int = 10,
    ) -> list[LeaderboardEntry]:
        current_time = now or datetime.now()
        group_chat_id = self.repository.get_or_create_group_chat_id(telegram_chat_id, chat_title, current_time)
        return self.repository.get_group_leaderboard(group_chat_id, start, end, limit=limit)


def validate_daily_total(current_total: int, amount: int) -> int:
    new_total = current_total + amount
    if not MIN_TOTAL <= new_total <= MAX_TOTAL:
        raise LimitError(current_total=current_total, attempted_total=new_total)
    return new_total
