# lookup/phone_lookup.py

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ==========================================================
# RESULT MODEL
# ==========================================================

@dataclass
class LookupResult:

    phone: str

    normalized: str

    country: Optional[str] = None

    valid: bool = False

    services: Dict[str, str] = field(
        default_factory=dict
    )

    metadata: Dict[str, str] = field(
        default_factory=dict
    )

    errors: List[str] = field(
        default_factory=list
    )


# ==========================================================
# PHONE LOOKUP
# ==========================================================

class PhoneLookup:

    """
    Initial phone lookup engine.

    Responsibilities:
        - Normalize phone numbers
        - Validate basic phone format
        - Prepare structured lookup results
        - Provide a provider-oriented architecture
    """

    DEFAULT_COUNTRY = "IR"

    # ------------------------------------------------------
    # IRANIAN PHONE PATTERN
    # ------------------------------------------------------

    IRAN_MOBILE_PATTERN = re.compile(
        r"^09\d{9}$"
    )

    INTERNATIONAL_IRAN_PATTERN = re.compile(
        r"^\+989\d{9}$"
    )

    # ======================================================
    # INIT
    # ======================================================

    def __init__(
        self,
        country: str = DEFAULT_COUNTRY
    ):

        self.country = country.upper()

    # ======================================================
    # NORMALIZE
    # ======================================================

    @staticmethod
    def normalize(
        phone: str
    ) -> str:

        if phone is None:
            return ""

        phone = str(phone).strip()

        # Persian digits
        persian_digits = str.maketrans(
            "۰۱۲۳۴۵۶۷۸۹",
            "0123456789"
        )

        # Arabic digits
        arabic_digits = str.maketrans(
            "٠١٢٣٤٥٦٧٨٩",
            "0123456789"
        )

        phone = phone.translate(
            persian_digits
        )

        phone = phone.translate(
            arabic_digits
        )

        # Remove common separators
        phone = re.sub(
            r"[\s\-\(\)\.]",
            "",
            phone
        )

        # Iranian international format
        if phone.startswith(
            "0098"
        ):

            phone = "+" + phone[2:]

        elif phone.startswith(
            "98"
        ):

            phone = "+" + phone

        elif phone.startswith(
            "9"
        ):

            phone = "0" + phone

        return phone

    # ======================================================
    # VALIDATE
    # ======================================================

    def validate(
        self,
        phone: str
    ) -> bool:

        normalized = self.normalize(
            phone
        )

        if self.country == "IR":

            return bool(
                self.IRAN_MOBILE_PATTERN.match(
                    normalized
                )
                or
                self.INTERNATIONAL_IRAN_PATTERN.match(
                    normalized
                )
            )

        return bool(
            re.match(
                r"^\+?[0-9]{7,15}$",
                normalized
            )
        )

    # ======================================================
    # COUNTRY
    # ======================================================

    def detect_country(
        self,
        phone: str
    ) -> Optional[str]:

        normalized = self.normalize(
            phone
        )

        if (
            normalized.startswith("09")
            or
            normalized.startswith("+989")
        ):

            return "IR"

        return None

    # ======================================================
    # PREPARE PHONE
    # ======================================================

    def prepare(
        self,
        phone: str
    ) -> LookupResult:

        normalized = self.normalize(
            phone
        )

        result = LookupResult(
            phone=str(phone or ""),
            normalized=normalized,
            country=self.detect_country(
                normalized
            ),
            valid=self.validate(
                normalized
            )
        )

        if not normalized:

            result.errors.append(
                "EMPTY_PHONE"
            )

        elif not result.valid:

            result.errors.append(
                "INVALID_PHONE"
            )

        return result

    # ======================================================
    # LOOKUP
    # ======================================================

    def lookup(
        self,
        phone: str
    ) -> LookupResult:

        result = self.prepare(
            phone
        )

        if not result.valid:
            return result

        # --------------------------------------------------
        # Provider layer will be added here.
        #
        # Example:
        #
        # result.services["telegram"] = "unknown"
        # result.services["whatsapp"] = "unknown"
        #
        # IMPORTANT:
        # We do not mark an account as active merely because
        # a number is syntactically valid.
        # --------------------------------------------------

        result.metadata[
            "lookup_status"
        ] = "READY"

        return result

    # ======================================================
    # SERVICE STATUS
    # ======================================================

    @staticmethod
    def service_status(
        result: LookupResult,
        service: str
    ) -> str:

        return result.services.get(
            service.lower(),
            "unknown"
        )

    # ======================================================
    # EXPORT
    # ======================================================

    @staticmethod
    def to_dict(
        result: LookupResult
    ) -> dict:

        return {
            "phone": result.phone,
            "normalized": result.normalized,
            "country": result.country,
            "valid": result.valid,
            "services": dict(
                result.services
            ),
            "metadata": dict(
                result.metadata
            ),
            "errors": list(
                result.errors
            )
        }


# ==========================================================
# SIMPLE FUNCTION API
# ==========================================================

def lookup_phone(
    phone: str
) -> dict:

    engine = PhoneLookup()

    result = engine.lookup(
        phone
    )

    return PhoneLookup.to_dict(
        result
    )


# ==========================================================
# CLI TEST
# ==========================================================

if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:

        print(
            "Usage: python3 lookup/phone_lookup.py <phone>"
        )

        sys.exit(1)

    phone = sys.argv[1]

    result = lookup_phone(
        phone
    )

    print(
        result
    )