from __future__ import annotations

from bot.models import Activity

MAX_AMOUNT = 1_000_000
MIN_TOTAL = 0
MAX_TOTAL = 1_000_000


ACTIVITIES: dict[str, Activity] = {
    "steps": Activity("steps", "Шаги", "Steps", "Шаги", "Steps", "шт", "pcs", "шагов", "steps", "👟"),
    "squats": Activity(
        "squats", "Приседания", "Squats", "Приседания", "Squats", "шт", "pcs", "приседаний", "squats", "🦵"
    ),
    "pushups": Activity(
        "pushups", "Отжимания", "Push-ups", "Отжимания", "Push-ups", "шт", "pcs", "отжиманий", "push-ups", "💪"
    ),
    "plank": Activity("plank", "Планка", "Plank", "Планка", "Plank", "мин", "min", "мин планки", "min plank", "⏱"),
    "abs": Activity("abs", "Пресс", "Abs", "Пресс", "Abs", "шт", "pcs", "повторений пресса", "abs reps", "🔥"),
}

ACTIVITY_KEYS = tuple(ACTIVITIES.keys())
