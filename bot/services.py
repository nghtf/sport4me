from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from bot.constants import ACTIVITIES, ACTIVITY_KEYS, MAX_GROUP_MEMBERS, MAX_TOURNAMENT_DAYS, MAX_TOTAL, MIN_TOTAL
from bot.models import LeaderboardEntry, PeriodStats, Tournament, User
from bot.repository import ActivityRepository


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


class GroupFullError(RuntimeError):
    pass


class AlreadyJoinedError(RuntimeError):
    pass


class NoActiveTournamentError(RuntimeError):
    pass


class TournamentAlreadyActiveError(RuntimeError):
    def __init__(self, tournament: Tournament) -> None:
        self.tournament = tournament
        super().__init__("A tournament is already active")


class InvalidTournamentDaysError(ValueError):
    pass


class ActivityService:
    def __init__(self, repository: ActivityRepository):
        self.repository = repository
        self._pending_amounts: dict[int, int] = {}

    def ensure_user(
        self,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None = None,
        now: datetime | None = None,
    ) -> User:
        return self.repository.get_or_create_user(telegram_user_id, username, first_name=first_name, now=now)

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

        return PeriodStats(
            today=self.repository.get_totals_by_activity(user.id, today_start, today_end),
            week=self.repository.get_totals_by_activity(user.id, week_start, week_end),
            month=self.repository.get_totals_by_activity(user.id, month_start, month_end),
        )

    def start_tournament(
        self,
        telegram_chat_id: int,
        chat_title: str | None,
        telegram_user_id: int,
        username: str | None,
        days: int,
        first_name: str | None = None,
        now: datetime | None = None,
    ) -> Tournament:
        if days < 1 or days > MAX_TOURNAMENT_DAYS:
            raise InvalidTournamentDaysError(f"Days must be between 1 and {MAX_TOURNAMENT_DAYS}")
        current_time = now or datetime.now()
        active = self.repository.get_active_tournament(telegram_chat_id, current_time)
        if active is not None:
            raise TournamentAlreadyActiveError(active)
        user = self.ensure_user(telegram_user_id, username, first_name=first_name, now=current_time)
        group_chat_id = self.repository.get_or_create_group_chat_id(telegram_chat_id, chat_title, current_time)
        start_date = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=days)
        tournament = self.repository.create_tournament(group_chat_id, user.id, start_date, end_date, current_time)
        self.repository.add_tournament_participant(tournament.id, user.id, current_time)
        return tournament

    def join_tournament(
        self,
        telegram_chat_id: int,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None = None,
        now: datetime | None = None,
    ) -> int:
        """Add user as a tournament participant. Returns total participant count."""
        current_time = now or datetime.now()
        tournament = self.repository.get_active_tournament(telegram_chat_id, current_time)
        if tournament is None:
            raise NoActiveTournamentError()
        user = self.ensure_user(telegram_user_id, username, first_name=first_name, now=current_time)
        if self.repository.is_tournament_participant(tournament.id, user.id):
            raise AlreadyJoinedError()
        count = self.repository.get_tournament_participant_count(tournament.id)
        if count >= MAX_GROUP_MEMBERS:
            raise GroupFullError()
        self.repository.add_tournament_participant(tournament.id, user.id, current_time)
        return count + 1

    def finish_tournament(
        self,
        telegram_chat_id: int,
        now: datetime | None = None,
    ) -> tuple[Tournament, list[LeaderboardEntry]]:
        current_time = now or datetime.now()
        tournament = self.repository.get_active_tournament(telegram_chat_id, current_time)
        if tournament is None:
            raise NoActiveTournamentError()
        finished = self.repository.finish_tournament(tournament.id, current_time)
        entries = self.repository.get_tournament_leaderboard(
            finished.id, finished.start_date, finished.end_date
        )
        return finished, entries

    def get_tournament_results(
        self,
        telegram_chat_id: int,
        now: datetime | None = None,
    ) -> tuple[Tournament | None, list[LeaderboardEntry]]:
        current_time = now or datetime.now()
        # Prefer the active tournament so /results and /finish always agree;
        # fall back to the most recent past tournament when nothing is running.
        tournament = (
            self.repository.get_active_tournament(telegram_chat_id, current_time)
            or self.repository.get_latest_tournament(telegram_chat_id)
        )
        if tournament is None:
            return None, []
        entries = self.repository.get_tournament_leaderboard(
            tournament.id, tournament.start_date, tournament.end_date
        )
        return tournament, entries


def validate_daily_total(current_total: int, amount: int) -> int:
    new_total = current_total + amount
    if not MIN_TOTAL <= new_total <= MAX_TOTAL:
        raise LimitError(current_total=current_total, attempted_total=new_total)
    return new_total


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
