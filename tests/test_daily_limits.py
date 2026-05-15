from __future__ import annotations

import pytest

from bot.services import LimitError, validate_daily_total


def test_daily_total_can_reach_zero() -> None:
    assert validate_daily_total(current_total=20, amount=-20) == 0


def test_daily_total_cannot_go_below_zero() -> None:
    with pytest.raises(LimitError) as error:
        validate_daily_total(current_total=20, amount=-21)

    assert error.value.current_total == 20
    assert error.value.attempted_total == -1


def test_daily_total_can_reach_upper_limit() -> None:
    assert validate_daily_total(current_total=999_990, amount=10) == 1_000_000


def test_daily_total_cannot_exceed_upper_limit() -> None:
    with pytest.raises(LimitError) as error:
        validate_daily_total(current_total=999_990, amount=11)

    assert error.value.current_total == 999_990
    assert error.value.attempted_total == 1_000_001
