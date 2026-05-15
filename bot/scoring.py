from __future__ import annotations

from fractions import Fraction

from bot.constants import ACTIVITY_KEYS

# Normalized score model:
# - 1,000 steps = 10 points
# - 20 squats = 10 points
# - 10 push-ups = 10 points
# - 2 plank minutes = 10 points
# - 20 abs reps = 10 points
#
# This keeps typical daily walking meaningful without letting raw step counts
# dominate bodyweight exercises, and gives plank extra weight as a time-based hold.
_POINTS_PER_UNIT: dict[str, Fraction] = {
    "steps": Fraction(1, 100),
    "squats": Fraction(1, 2),
    "pushups": Fraction(1, 1),
    "plank": Fraction(5, 1),
    "abs": Fraction(1, 2),
}


def calculate_score(totals: dict[str, int]) -> int:
    score = sum(Fraction(totals.get(activity_key, 0)) * _POINTS_PER_UNIT[activity_key] for activity_key in ACTIVITY_KEYS)
    return int(score + Fraction(1, 2))
