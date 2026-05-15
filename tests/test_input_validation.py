from __future__ import annotations

import pytest

from bot.validators import InputErrorCode, InputValidationError, parse_signed_amount


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("+1", 1),
        ("-1", -1),
        ("+20", 20),
        ("-20", -20),
        ("20", 20),
        ("+1000000", 1_000_000),
        ("-1000000", -1_000_000),
        ("1000000", 1_000_000),
    ],
)
def test_parse_signed_amount_accepts_valid_values(text: str, expected: int) -> None:
    assert parse_signed_amount(text) == expected


@pytest.mark.parametrize(
    ("text", "code"),
    [
        ("0", InputErrorCode.ZERO),
        ("+0", InputErrorCode.ZERO),
        ("-0", InputErrorCode.ZERO),
        ("abc", InputErrorCode.INVALID),
        ("+abc", InputErrorCode.INVALID),
        ("++", InputErrorCode.INVALID),
        ("--", InputErrorCode.INVALID),
        ("+1000001", InputErrorCode.TOO_LARGE),
        ("-1000001", InputErrorCode.TOO_LARGE),
        ("1000001", InputErrorCode.TOO_LARGE),
    ],
)
def test_parse_signed_amount_rejects_invalid_values(text: str, code: InputErrorCode) -> None:
    with pytest.raises(InputValidationError) as error:
        parse_signed_amount(text)

    assert error.value.code == code
