from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

Language = Literal["en", "ru"]

_LOCALES_DIR = Path(__file__).with_name("locales")


@lru_cache(maxsize=None)
def _load_locale(lang: Language) -> dict[str, str]:
    locale_path = _LOCALES_DIR / f"{lang}.json"
    with locale_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def translate(lang: Language, key: str, **kwargs: object) -> str:
    try:
        template = _load_locale(lang)[key]
    except KeyError as error:
        raise KeyError(f"Missing translation for {lang}:{key}") from error
    return template.format(**kwargs)
