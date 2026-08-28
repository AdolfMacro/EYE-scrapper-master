from __future__ import annotations

import re
from typing import Any


# ==========================================================
# DIGITS
# ==========================================================

PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"

ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"

ENGLISH_DIGITS = "0123456789"


_DIGIT_TRANSLATION_TABLE = str.maketrans(
    PERSIAN_DIGITS + ARABIC_DIGITS,
    ENGLISH_DIGITS + ENGLISH_DIGITS,
)


# ==========================================================
# TEXT NORMALIZATION
# ==========================================================

def normalize_digits(
    value: Any,
) -> str:
    """
    Convert Persian and Arabic digits to English digits.

    Examples
    --------
    ۰۹۱۲۳۴۵۶۷۸۹
        ↓
    09123456789
    """

    if value is None:
        return ""

    return str(
        value
    ).translate(
        _DIGIT_TRANSLATION_TABLE
    )


def normalize_text(
    value: Any,
) -> str:
    """
    Normalize general text.

    Operations
    ----------
    - Convert Persian/Arabic digits
    - Normalize Persian Arabic-character variants
    - Replace zero-width spaces
    - Collapse repeated whitespace
    - Strip surrounding whitespace
    """

    if value is None:
        return ""

    text = normalize_digits(
        value
    )

    # ------------------------------------------------------
    # Persian character normalization
    # ------------------------------------------------------

    text = text.replace(
        "ي",
        "ی",
    )

    text = text.replace(
        "ى",
        "ی",
    )

    text = text.replace(
        "ك",
        "ک",
    )

    # ------------------------------------------------------
    # Zero-width characters
    # ------------------------------------------------------

    text = text.replace(
        "\u200c",
        " ",
    )

    text = text.replace(
        "\u200b",
        "",
    )

    text = text.replace(
        "\ufeff",
        "",
    )

    # ------------------------------------------------------
    # Whitespace
    # ------------------------------------------------------

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


# ==========================================================
# PHONE NORMALIZATION
# ==========================================================

def normalize_phone(
    phone: Any,
) -> str:
    """
    Normalize a phone number while preserving the basic
    phone representation.

    This function is responsible for normalization only.

    Use phone_digits() when a digits-only identity is required.
    """

    if phone is None:
        return ""

    value = normalize_digits(
        phone
    )

    value = value.strip()

    if not value:
        return ""

    # ------------------------------------------------------
    # Remove common visual separators
    # ------------------------------------------------------

    value = re.sub(
        r"[\s().\[\]]+",
        "",
        value,
    )

    value = value.replace(
        "−",
        "-",
    )

    value = value.replace(
        "–",
        "-",
    )

    value = value.replace(
        "—",
        "-",
    )

    return value.strip()


def phone_digits(
    phone: Any,
) -> str:
    """
    Return digits-only representation of a phone number.

    This is the canonical representation used for
    phone-based identity and deduplication.
    """

    normalized = normalize_phone(
        phone
    )

    if not normalized:
        return ""

    return re.sub(
        r"\D",
        "",
        normalized,
    )


# ==========================================================
# NAME
# ==========================================================

def normalize_name(
    name: Any,
) -> str:
    """
    Normalize a name for comparison and deduplication.
    """

    return normalize_text(
        name
    ).casefold()


# ==========================================================
# CITY
# ==========================================================

def normalize_city(
    city: Any,
) -> str:
    """
    Normalize a city name for comparison and deduplication.
    """

    return normalize_text(
        city
    ).casefold()


# ==========================================================
# PROVINCE
# ==========================================================

def normalize_province(
    province: Any,
) -> str:
    """
    Normalize a province name for comparison and deduplication.
    """

    return normalize_text(
        province
    ).casefold()


# ==========================================================
# ADDRESS
# ==========================================================

def normalize_address(
    address: Any,
) -> str:
    """
    Normalize an address for comparison and deduplication.
    """

    return normalize_text(
        address
    ).casefold()