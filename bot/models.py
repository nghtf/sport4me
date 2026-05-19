from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class Activity:
    key: str
    label_ru: str
    label_en: str
    stat_label_ru: str
    stat_label_en: str
    unit_ru: str
    unit_en: str
    genitive_plural_ru: str
    genitive_plural_en: str
    emoji: str = ""

    def label(self, lang: Literal["en", "ru"]) -> str:
        return self.label_ru if lang == "ru" else self.label_en

    def stat_label(self, lang: Literal["en", "ru"]) -> str:
        return self.stat_label_ru if lang == "ru" else self.stat_label_en

    def unit(self, lang: Literal["en", "ru"]) -> str:
        return self.unit_ru if lang == "ru" else self.unit_en

    def amount_label(self, lang: Literal["en", "ru"]) -> str:
        return self.genitive_plural_ru if lang == "ru" else self.genitive_plural_en


@dataclass(frozen=True)
class User:
    id: int
    telegram_user_id: int
    username: str | None
    first_name: str | None
    preferred_language: str | None
    created_at: datetime


@dataclass(frozen=True)
class PeriodStats:
    yesterday: dict[str, int]
    today: dict[str, int]
    week: dict[str, int]
    month: dict[str, int]



@dataclass(frozen=True)
class LeaderboardEntry:
    rank: int
    user: User
    score: int
