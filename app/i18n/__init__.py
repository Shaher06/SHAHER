"""Tiny translation system. All user-visible text lives in strings_ar.py / strings_en.py.

    from app.i18n import t
    t("home.add")                 -> "إضافة التزام"  (or English, per current language)
    t("home.today_count", n=3)    -> text with {n} filled in

Missing keys fall back to English, then to the key itself (so nothing ever crashes).
"""
from app.i18n.strings_ar import STRINGS as _AR
from app.i18n.strings_en import STRINGS as _EN

LANGUAGES = {"ar": "العربية", "en": "English"}
_STRINGS = {"ar": _AR, "en": _EN}
_lang = "ar"
_arabic_digits = False
_AR_DIGITS = str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩")


def set_language(lang: str) -> None:
    global _lang
    _lang = lang if lang in _STRINGS else "ar"


def language() -> str:
    return _lang


def is_rtl() -> bool:
    return _lang == "ar"


def set_arabic_digits(on: bool) -> None:
    global _arabic_digits
    _arabic_digits = bool(on)


def localize_digits(text: str) -> str:
    """Display-only: 0-9 -> ٠-٩ when the user chose Arabic digits (Arabic UI only)."""
    return text.translate(_AR_DIGITS) if (_arabic_digits and _lang == "ar") else text


def t(key: str, **params) -> str:
    text = _STRINGS[_lang].get(key)
    if text is None:
        text = _EN.get(key, key)
    if params:
        try:
            return text.format(**params)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def all_keys():
    return set(_AR) | set(_EN)


def missing(lang: str):
    return sorted(all_keys() - set(_STRINGS[lang]))
