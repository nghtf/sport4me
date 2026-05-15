from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

from bot.constants import MAX_AMOUNT

INTEGER_RE = re.compile(r"^[+-]?\d+$")


class InputErrorCode(StrEnum):
    ZERO = "zero"
    TOO_LARGE = "too_large"
    INVALID = "invalid"


@dataclass(frozen=True)
class InputValidationError(ValueError):
    code: InputErrorCode


def parse_signed_amount(text: str) -> int:
    value = text.strip()

    if not INTEGER_RE.fullmatch(value):
        raise InputValidationError(InputErrorCode.INVALID)

    amount = int(value)
    if amount == 0:
        raise InputValidationError(InputErrorCode.ZERO)

    if abs(amount) > MAX_AMOUNT:
        raise InputValidationError(InputErrorCode.TOO_LARGE)

    return amount
