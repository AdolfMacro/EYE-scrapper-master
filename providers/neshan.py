# ============================================================
# EYE SCRAPPER
# NESHAN BUSINESS / PLACE PROVIDER
# ============================================================
#
# FILE:
#     providers/neshan.py
#
# VERSION:
#     2.2.0
#
# STATUS:
#     CANONICAL / MASTER COMPATIBLE
#
# ROLE:
#     Generic Iranian business / place discovery provider
#     based on Neshan Location Search API.
#
# RESPONSIBILITY:
#     - Search Iranian businesses / places
#     - Resolve city / geographic context
#     - Normalize Neshan responses
#     - Classify business categories
#     - Reject obvious non-business locations
#     - Score and rank candidates
#     - Deduplicate results
#     - Expose stable structured output
#     - Provide provider statistics
#
# ============================================================

from __future__ import annotations

import math
import os
import re
import time

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

from providers.base import SearchProvider


# ============================================================
# PROVIDER METADATA
# ============================================================

PROVIDER_NAME = "neshan"
PROVIDER_VERSION = "2.2.0"

BASE_URL = "https://neshan.org"
SEARCH_ENDPOINT = "https://api.neshan.org/v1/search"

DEFAULT_TIMEOUT = 15.0
DEFAULT_DELAY = 0.25
DEFAULT_MAX_RESULTS = 30
DEFAULT_MIN_SCORE = 25.0
DEFAULT_MIN_CONFIDENCE = 0.20

EARTH_RADIUS_KM = 6371.0088


# ============================================================
# IRAN CITY DATABASE
# ============================================================

CITY_DATABASE: Dict[str, Dict[str, float]] = {
    "تهران": {"lat": 35.6892, "lng": 51.3890},
    "کرج": {"lat": 35.8400, "lng": 50.9391},
    "تبریز": {"lat": 38.0962, "lng": 46.2738},
    "مشهد": {"lat": 36.2605, "lng": 59.6168},
    "اصفهان": {"lat": 32.6546, "lng": 51.6680},
    "شیراز": {"lat": 29.5918, "lng": 52.5837},
    "اهواز": {"lat": 31.3183, "lng": 48.6706},
    "رشت": {"lat": 37.2808, "lng": 49.5832},
    "قم": {"lat": 34.6416, "lng": 50.8746},
    "کرمان": {"lat": 30.2839, "lng": 57.0834},
    "ارومیه": {"lat": 37.5527, "lng": 45.0761},
    "یزد": {"lat": 31.8974, "lng": 54.3569},
    "اردبیل": {"lat": 38.2498, "lng": 48.2933},
    "سنندج": {"lat": 35.3219, "lng": 46.9862},
    "کرمانشاه": {"lat": 34.3142, "lng": 47.0650},
    "همدان": {"lat": 34.7980, "lng": 48.5148},
    "قزوین": {"lat": 36.2688, "lng": 50.0041},
    "زنجان": {"lat": 36.6769, "lng": 48.4963},
    "ساری": {"lat": 36.5659, "lng": 53.0586},
    "بابل": {"lat": 36.5387, "lng": 52.6765},
    "گرگان": {"lat": 36.8456, "lng": 54.4393},
    "بندرعباس": {"lat": 27.1832, "lng": 56.2666},
    "بوشهر": {"lat": 28.9234, "lng": 50.8203},
    "خرم‌آباد": {"lat": 33.4878, "lng": 48.3558},
    "ایلام": {"lat": 33.6374, "lng": 46.4227},
    "اراک": {"lat": 34.0954, "lng": 49.7013},
    "کاشان": {"lat": 33.9850, "lng": 51.4090},
    "نیشابور": {"lat": 36.2140, "lng": 58.7967},
    "سبزوار": {"lat": 36.2090, "lng": 57.6810},
    "بیرجند": {"lat": 32.8663, "lng": 59.2211},
    "زاهدان": {"lat": 29.4963, "lng": 60.8629},
    "بجنورد": {"lat": 37.4750, "lng": 57.3327},
    "گرمسار": {"lat": 35.2183, "lng": 52.3406},
}


# ============================================================
# CITY ALIASES
# ============================================================

CITY_ALIASES: Dict[str, str] = {
    "تهران": "تهران",
    "کرج": "کرج",

    "تبریز": "تبریز",
    "تبريز": "تبریز",

    "مشهد": "مشهد",

    "اصفهان": "اصفهان",

    "شیراز": "شیراز",
    "شيراز": "شیراز",

    "اهواز": "اهواز",
    "رشت": "رشت",
    "قم": "قم",
    "کرمان": "کرمان",

    "ارومیه": "ارومیه",
    "اروميه": "ارومیه",

    "یزد": "یزد",
    "يزد": "یزد",

    "اردبیل": "اردبیل",
    "اردبيل": "اردبیل",

    "سنندج": "سنندج",
    "کرمانشاه": "کرمانشاه",
    "همدان": "همدان",

    "قزوین": "قزوین",
    "قزوين": "قزوین",

    "زنجان": "زنجان",
    "ساری": "ساری",
    "بابل": "بابل",
    "گرگان": "گرگان",

    "بندرعباس": "بندرعباس",
    "بندر عباس": "بندرعباس",

    "بوشهر": "بوشهر",

    "خرم آباد": "خرم‌آباد",
    "خرم‌اباد": "خرم‌آباد",
    "خرم‌آباد": "خرم‌آباد",

    "ایلام": "ایلام",
    "ايلام": "ایلام",

    "اراک": "اراک",
    "کاشان": "کاشان",

    "نیشابور": "نیشابور",
    "نيشابور": "نیشابور",

    "سبزوار": "سبزوار",

    "بیرجند": "بیرجند",
    "بيرجند": "بیرجند",

    "زاهدان": "زاهدان",
    "بجنورد": "بجنورد",
    "گرمسار": "گرمسار",
}


# ============================================================
# CATEGORY MAP
# ============================================================

CATEGORY_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "education": (
        "مدرسه",
        "دبستان",
        "دبیرستان",
        "هنرستان",
        "دانشگاه",
        "دانشکده",
        "آموزشگاه",
        "مهد کودک",
        "مهدکودک",
        "کودکستان",
        "آموزش",
        "کلاس",
        "فرهنگسرا",
    ),

    "restaurant": (
        "رستوران",
        "چلوکباب",
        "کباب",
        "غذا",
        "سفره خانه",
        "سفره‌خانه",
    ),

    "cafe": (
        "کافه",
        "کافی شاپ",
        "کافی‌شاپ",
        "قهوه",
    ),

    "food": (
        "فست فود",
        "فست‌فود",
        "نانوایی",
        "قنادی",
        "شیرینی",
        "بستنی",
        "فروشگاه مواد غذایی",
    ),

    "retail": (
        "فروشگاه",
        "سوپرمارکت",
        "هایپرمارکت",
        "مغازه",
        "فروش",
        "بازار",
        "فروشندگی",
        "پاساژ",
        "مجتمع تجاری",
        "مرکز خرید",
    ),

    "fashion": (
        "پوشاک",
        "لباس",
        "کفش",
        "کیف",
        "طلا",
        "جواهر",
    ),

    "healthcare": (
        "بیمارستان",
        "کلینیک",
        "درمانگاه",
        "پزشک",
        "مطب",
        "دندانپزشکی",
        "داروخانه",
        "آزمایشگاه",
        "فیزیوتراپی",
        "دامپزشکی",
    ),

    "finance": (
        "بانک",
        "بیمه",
        "صرافی",
        "خدمات مالی",
    ),

    "automotive": (
        "تعمیرگاه",
        "مکانیکی",
        "خودرو",
        "قطعات خودرو",
        "نمایندگی خودرو",
        "لاستیک",
        "تعویض روغن",
        "کارواش",
    ),

    "hospitality": (
        "هتل",
        "مهمانپذیر",
        "مهمانسرا",
        "مهمانخانه",
        "هاستل",
        "اقامتگاه",
    ),

    "beauty": (
        "آرایشگاه",
        "سالن زیبایی",
        "زیبایی",
        "پیرایشگاه",
    ),

    "real_estate": (
        "املاک",
        "مسکن",
        "مشاور املاک",
    ),

    "professional_services": (
        "وکیل",
        "وکالت",
        "حسابداری",
        "مشاوره",
        "مشاور",
        "معماری",
        "دفتر مهندسی",
    ),

    "company": (
        "شرکت",
        "صنایع",
        "کارخانه",
        "بازرگانی",
        "تولیدی",
    ),

    "services": (
        "خدمات",
        "تعمیرات",
        "کارگاه",
        "دفتر",
        "مرکز خدمات",
    ),
}


# ============================================================
# NON-BUSINESS TERMS
#
# IMPORTANT:
# These terms are used against entity metadata/name,
# NOT against the full address.
#
# Otherwise a business located on:
#     "خیابان ولیعصر"
# would incorrectly become a "place".
# ============================================================

NON_BUSINESS_TERMS = (
    "خیابان",
    "بلوار",
    "کوچه",
    "میدان",
    "بزرگراه",
    "رودخانه",
    "کوه",
    "دریاچه",
    "جنگل",
    "پارک ملی",
)


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class CityContext:
    name: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    province: str = ""
    source: str = ""

    @property
    def has_coordinates(self) -> bool:
        return (
            self.latitude is not None
            and self.longitude is not None
        )


@dataclass
class Candidate:
    name: str
    latitude: float
    longitude: float

    city: str = ""
    province: str = ""

    phone: str = ""
    website: str = ""
    address: str = ""

    neighborhood: str = ""
    street: str = ""

    source_id: str = ""
    source_type: str = ""

    category: str = "unknown"

    neshan_type: str = ""
    neshan_category: str = ""

    distance_km: Optional[float] = None
    api_distance: Optional[float] = None

    score: float = 0.0
    confidence: float = 0.0

    semantic_type: str = "business"
    verification: bool = False

    source_query: str = ""

    raw: Dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================
# PROVIDER
# ============================================================

class NeshanProvider(SearchProvider):

    name = PROVIDER_NAME

    def __init__(
        self,
        *,
        api_key: str = "",
        delay: float = DEFAULT_DELAY,
        timeout: float = DEFAULT_TIMEOUT,
        max_results: int = DEFAULT_MAX_RESULTS,
        min_score: float = DEFAULT_MIN_SCORE,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        session: Optional[requests.Session] = None,
        debug: bool = True,
    ) -> None:

        self.api_key = (
            str(api_key).strip()
            if api_key
            else self._environment_api_key()
        )

        self.delay = max(
            0.0,
            float(delay),
        )

        self.timeout = max(
            1.0,
            float(timeout),
        )

        self.max_results = max(
            1,
            min(
                DEFAULT_MAX_RESULTS,
                int(max_results),
            ),
        )

        self.min_score = max(
            0.0,
            min(
                100.0,
                float(min_score),
            ),
        )

        self.min_confidence = max(
            0.0,
            min(
                1.0,
                float(min_confidence),
            ),
        )

        self.session = (
            session
            if session is not None
            else requests.Session()
        )

        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": (
                    f"EYE-Scrapper/{PROVIDER_VERSION}"
                ),
            }
        )

        self.debug = bool(debug)

        self._last_request_at = 0.0

        self.stats = self._new_stats()

    # ========================================================
    # API KEY
    # ========================================================

    @staticmethod
    def _environment_api_key() -> str:

        for key_name in (
            "NESHAN_API_KEY",
            "NESHAN_APIKEY",
            "NESHAN_KEY",
        ):

            value = os.getenv(
                key_name,
                "",
            ).strip()

            if value:
                return value

        return ""

    def _resolve_api_key(
        self,
        kwargs: Dict[str, Any],
    ) -> str:

        explicit = kwargs.get("api_key")

        if explicit:

            value = str(
                explicit
            ).strip()

            if value:
                return value

        config = kwargs.get("config")

        if isinstance(
            config,
            Mapping,
        ):

            provider_config = config.get(
                PROVIDER_NAME
            )

            if isinstance(
                provider_config,
                Mapping,
            ):

                value = str(
                    provider_config.get(
                        "api_key",
                        "",
                    )
                    or ""
                ).strip()

                if value:
                    return value

            value = str(
                config.get(
                    "neshan_api_key",
                    "",
                )
                or ""
            ).strip()

            if value:
                return value

            providers = config.get(
                "providers"
            )

            if isinstance(
                providers,
                Mapping,
            ):

                provider_config = providers.get(
                    PROVIDER_NAME
                )

                if isinstance(
                    provider_config,
                    Mapping,
                ):

                    value = str(
                        provider_config.get(
                            "api_key",
                            "",
                        )
                        or ""
                    ).strip()

                    if value:
                        return value

        if config is not None:

            for attr in (
                "neshan_api_key",
                "api_key",
            ):

                try:
                    value = getattr(
                        config,
                        attr,
                        "",
                    )
                except Exception:
                    value = ""

                if value:

                    value = str(
                        value
                    ).strip()

                    if value:
                        return value

        if self.api_key:
            return self.api_key

        return self._environment_api_key()

    # ========================================================
    # INFO
    # ========================================================

    def info(self) -> Dict[str, Any]:

        return {
            "name": PROVIDER_NAME,
            "version": PROVIDER_VERSION,
            "type": "business_search",
            "base_url": BASE_URL,
            "endpoint": SEARCH_ENDPOINT,
            "method": "GET",
            "format": "json",
            "country": "Iran",
            "timeout": self.timeout,
            "delay": self.delay,
            "max_results": self.max_results,
            "min_score": self.min_score,
            "min_confidence": self.min_confidence,
            "api_key_configured": bool(
                self.api_key
                or self._environment_api_key()
            ),
            "module": __name__,
        }

    # ========================================================
    # HEALTH
    # ========================================================

    def health_check(self) -> bool:

        api_key = (
            self.api_key
            or self._environment_api_key()
        )

        if not api_key:

            self._log(
                "[NESHAN][HEALTH] "
                "API key is not configured"
            )

            return False

        context = self._city_context(
            "تهران"
        )

        if not context.has_coordinates:

            self._log(
                "[NESHAN][HEALTH] "
                "Default geographic context unavailable"
            )

            return False

        try:

            data = self._request(
                query="رستوران",
                latitude=context.latitude,
                longitude=context.longitude,
                api_key=api_key,
            )

            return isinstance(
                data.get("items"),
                list,
            )

        except Exception as exc:

            self._log(
                f"[NESHAN][HEALTH] FAILED: {exc}"
            )

            return False

    # ========================================================
    # SEARCH
    # ========================================================

    def search(
        self,
        query: str,
        page: int = 1,
        city: str = "",
        province: str = "",
        radius: float = 0,
        max_results: Optional[int] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:

        self.stats = self._new_stats()

        clean_query = self._normalize_text(
            query
        )

        if not clean_query:
            return []

        api_key = self._resolve_api_key(
            kwargs
        )

        limit = self._resolve_limit(
            max_results
        )

        context = self._resolve_city_context(
            query=clean_query,
            city=city,
            province=province,
        )

        center = self._resolve_center(
            context=context,
            latitude=latitude,
            longitude=longitude,
        )

        try:
            page_number = max(
                1,
                int(page),
            )
        except (
            TypeError,
            ValueError,
        ):
            page_number = 1

        self._log(
            "[NESHAN] SEARCH "
            f"query={clean_query!r} "
            f"page={page_number} "
            f"city={context.name or '-'} "
            f"geo={'yes' if center else 'no'}"
        )

        if not api_key:

            self.stats[
                "configuration_errors"
            ] += 1

            self._log(
                "[NESHAN][ERROR] "
                "Neshan API key is not configured"
            )

            return []

        if center is None:

            self.stats[
                "geographic_errors"
            ] += 1

            self._log(
                "[NESHAN][ERROR] "
                "No geographic reference for query"
            )

            return []

        try:

            raw_data = self._request(
                query=clean_query,
                latitude=center[0],
                longitude=center[1],
                api_key=api_key,
            )

        except requests.HTTPError as exc:

            self.stats[
                "http_errors"
            ] += 1

            self._log(
                f"[NESHAN][HTTP] {exc}"
            )

            return []

        except requests.RequestException as exc:

            self.stats[
                "request_errors"
            ] += 1

            self._log(
                f"[NESHAN][REQUEST] {exc}"
            )

            return []

        except ValueError as exc:

            self.stats[
                "parse_errors"
            ] += 1

            self._log(
                f"[NESHAN][JSON] {exc}"
            )

            return []

        except Exception as exc:

            self.stats[
                "errors"
            ] += 1

            self._log(
                f"[NESHAN][ERROR] {exc}"
            )

            return []

        raw_items = self._extract_items(
            raw_data
        )

        self.stats[
            "raw_results"
        ] = len(raw_items)

        self._log(
            f"[NESHAN] RAW={len(raw_items)}"
        )

        candidates: List[Candidate] = []

        for raw in raw_items:

            candidate = self._parse_candidate(
                raw=raw,
                context=context,
                center=center,
                radius=radius,
                source_query=clean_query,
            )

            if candidate is not None:
                candidates.append(candidate)

        self.stats[
            "candidates"
        ] = len(candidates)

        unique = self._deduplicate(
            candidates
        )

        accepted: List[Candidate] = []

        for candidate in unique:

            if self._is_acceptable(
                candidate
            ):
                accepted.append(candidate)
            else:
                self.stats[
                    "rejected"
                ] += 1

        accepted.sort(
            key=self._ranking_key,
            reverse=True,
        )

        accepted = accepted[:limit]

        self.stats[
            "accepted"
        ] = len(accepted)

        self._log(
            "[NESHAN] COMPLETE "
            f"raw={len(raw_items)} "
            f"candidates={len(candidates)} "
            f"unique={len(unique)} "
            f"accepted={len(accepted)}"
        )

        return [
            self._to_dict(candidate)
            for candidate in accepted
        ]

    # ========================================================
    # REQUEST
    # ========================================================

    def _request(
        self,
        *,
        query: str,
        latitude: float,
        longitude: float,
        api_key: str,
    ) -> Dict[str, Any]:

        if not api_key:
            raise RuntimeError(
                "Neshan API key is not configured"
            )

        self._respect_rate_limit()

        params = {
            "term": query,
            "lat": latitude,
            "lng": longitude,
        }

        headers = {
            "Api-Key": api_key,
            "Accept": "application/json",
        }

        self._log(
            "[NESHAN] GET "
            f"{SEARCH_ENDPOINT} "
            f"lat={latitude:.6f} "
            f"lng={longitude:.6f}"
        )

        response = self.session.get(
            SEARCH_ENDPOINT,
            params=params,
            headers=headers,
            timeout=self.timeout,
        )

        self.stats[
            "requests"
        ] += 1

        response.raise_for_status()

        data = response.json()

        if not isinstance(
            data,
            dict,
        ):
            raise ValueError(
                "Neshan response must be a JSON object"
            )

        return data

    # ========================================================
    # RATE LIMIT
    # ========================================================

    def _respect_rate_limit(self) -> None:

        if self.delay <= 0:

            self._last_request_at = (
                time.monotonic()
            )

            return

        now = time.monotonic()

        elapsed = (
            now
            - self._last_request_at
        )

        remaining = (
            self.delay
            - elapsed
        )

        if remaining > 0:
            time.sleep(remaining)

        self._last_request_at = (
            time.monotonic()
        )

    # ========================================================
    # CITY RESOLUTION
    # ========================================================

    def _resolve_city_context(
        self,
        *,
        query: str,
        city: str,
        province: str,
    ) -> CityContext:

        explicit = self._city_context(
            city
        )

        if explicit.has_coordinates:

            explicit.province = (
                self._normalize_text(
                    province
                )
            )

            explicit.source = "argument"

            return explicit

        detected = (
            self._detect_city_from_query(
                query
            )
        )

        if detected:

            context = self._city_context(
                detected
            )

            context.province = (
                self._normalize_text(
                    province
                )
            )

            context.source = "query"

            return context

        return CityContext(
            name=self._canonical_city(city),
            province=self._normalize_text(
                province
            ),
            source="none",
        )

    def _city_context(
        self,
        city: str,
    ) -> CityContext:

        normalized = self._normalize_text(
            city
        )

        canonical = self._canonical_city(
            normalized
        )

        data = CITY_DATABASE.get(
            canonical
        )

        if data is None:
            return CityContext(
                name=canonical
            )

        return CityContext(
            name=canonical,
            latitude=float(
                data["lat"]
            ),
            longitude=float(
                data["lng"]
            ),
        )

    def _detect_city_from_query(
        self,
        query: str,
    ) -> str:

        normalized_query = (
            self._normalize_text(query)
        )

        aliases = sorted(
            CITY_ALIASES.keys(),
            key=len,
            reverse=True,
        )

        for alias in aliases:

            normalized_alias = (
                self._normalize_text(alias)
            )

            if (
                normalized_alias
                and normalized_alias
                in normalized_query
            ):
                return CITY_ALIASES[
                    alias
                ]

        return ""

    def _canonical_city(
        self,
        city: str,
    ) -> str:

        normalized = self._normalize_text(
            city
        )

        return CITY_ALIASES.get(
            normalized,
            normalized,
        )

    # ========================================================
    # CENTER
    # ========================================================

    def _resolve_center(
        self,
        *,
        context: CityContext,
        latitude: Optional[float],
        longitude: Optional[float],
    ) -> Optional[Tuple[float, float]]:

        if (
            latitude is not None
            and longitude is not None
            and self._valid_coordinate(
                latitude,
                longitude,
            )
        ):

            return (
                float(latitude),
                float(longitude),
            )

        if context.has_coordinates:

            return (
                float(context.latitude),
                float(context.longitude),
            )

        return None

    # ========================================================
    # ITEMS
    # ========================================================

    def _extract_items(
        self,
        data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        items = data.get(
            "items"
        )

        if not isinstance(
            items,
            list,
        ):
            return []

        return [
            item
            for item in items
            if isinstance(
                item,
                dict,
            )
        ]

    # ========================================================
    # PARSE
    # ========================================================

    def _parse_candidate(
        self,
        *,
        raw: Dict[str, Any],
        context: CityContext,
        center: Tuple[float, float],
        radius: float,
        source_query: str,
    ) -> Optional[Candidate]:

        name = self._extract_name(
            raw
        )

        if not name:
            return None

        latitude, longitude = (
            self._extract_coordinates(
                raw
            )
        )

        if (
            latitude is None
            or longitude is None
        ):
            return None

        address = self._extract_address(
            raw
        )

        neighborhood = (
            self._extract_neighborhood(
                raw
            )
        )

        street = self._extract_street(
            raw
        )

        phone = self._extract_phone(
            raw
        )

        website = self._extract_website(
            raw
        )

        neshan_type = self._extract_type(
            raw
        )

        neshan_category = (
            self._extract_category(
                raw
            )
        )

        searchable_text = (
            self._build_searchable_text(
                raw=raw,
                name=name,
                address=address,
                source_query=source_query,
            )
        )

        category = self._resolve_category(
            text=searchable_text,
            neshan_type=neshan_type,
            neshan_category=neshan_category,
        )

        semantic = self._classify_business(
            name=name,
            neshan_type=neshan_type,
            neshan_category=neshan_category,
            category=category,
        )

        distance_km = self._distance_km(
            center[0],
            center[1],
            latitude,
            longitude,
        )

        if (
            radius > 0
            and distance_km > radius
        ):

            self.stats[
                "radius_filtered"
            ] += 1

            return None

        api_distance = (
            self._extract_distance(
                raw
            )
        )

        result_city = (
            self._extract_city(raw)
            or context.name
        )

        result_province = (
            self._extract_province(raw)
            or context.province
        )

        score = self._calculate_score(
            name=name,
            category=category,
            address=address,
            phone=phone,
            website=website,
            neshan_type=neshan_type,
            neshan_category=neshan_category,
            source_query=source_query,
            distance_km=distance_km,
            semantic=semantic,
        )

        confidence = (
            self._calculate_confidence(
                score=score,
                category=category,
                semantic=semantic,
                address=address,
                phone=phone,
                website=website,
            )
        )

        source_id = (
            self._extract_source_id(
                raw
            )
        )

        source_type = (
            self._build_source_type(
                raw
            )
        )

        verification = (
            self._calculate_verification(
                raw=raw,
                score=score,
                confidence=confidence,
            )
        )

        return Candidate(
            name=name,
            latitude=latitude,
            longitude=longitude,
            city=result_city,
            province=result_province,
            phone=phone,
            website=website,
            address=address,
            neighborhood=neighborhood,
            street=street,
            source_id=source_id,
            source_type=source_type,
            category=category,
            neshan_type=neshan_type,
            neshan_category=neshan_category,
            distance_km=distance_km,
            api_distance=api_distance,
            score=score,
            confidence=confidence,
            semantic_type=semantic[
                "semantic_type"
            ],
            verification=verification,
            source_query=source_query,
            raw=raw,
        )

    # ========================================================
    # NAME
    # ========================================================

    def _extract_name(
        self,
        raw: Dict[str, Any],
    ) -> str:

        for key in (
            "title",
            "name",
            "name_fa",
            "nameFa",
        ):

            value = self._normalize_text(
                raw.get(key)
                or ""
            )

            if value:
                return value

        return ""

    # ========================================================
    # COORDINATES
    # ========================================================

    def _extract_coordinates(
        self,
        raw: Dict[str, Any],
    ) -> Tuple[
        Optional[float],
        Optional[float],
    ]:

        location = raw.get(
            "location"
        )

        if isinstance(
            location,
            dict,
        ):

            x = location.get(
                "x"
            )

            y = location.get(
                "y"
            )

            try:

                longitude = float(x)
                latitude = float(y)

                if self._valid_coordinate(
                    latitude,
                    longitude,
                ):

                    return (
                        latitude,
                        longitude,
                    )

            except (
                TypeError,
                ValueError,
            ):
                pass

            lat = (
                location.get(
                    "latitude"
                )
                if location.get(
                    "latitude"
                ) is not None
                else location.get(
                    "lat"
                )
            )

            lng = (
                location.get(
                    "longitude"
                )
                if location.get(
                    "longitude"
                ) is not None
                else location.get(
                    "lng"
                )
            )

            if lng is None:
                lng = location.get(
                    "lon"
                )

            try:

                latitude = float(
                    lat
                )

                longitude = float(
                    lng
                )

                if self._valid_coordinate(
                    latitude,
                    longitude,
                ):

                    return (
                        latitude,
                        longitude,
                    )

            except (
                TypeError,
                ValueError,
            ):
                pass

        for source in (
            raw.get("geometry"),
            raw.get("point"),
            raw,
        ):

            if not isinstance(
                source,
                dict,
            ):
                continue

            lat = source.get(
                "latitude"
            )

            if lat is None:
                lat = source.get(
                    "lat"
                )

            lng = source.get(
                "longitude"
            )

            if lng is None:
                lng = source.get(
                    "lng"
                )

            if lng is None:
                lng = source.get(
                    "lon"
                )

            try:

                latitude = float(
                    lat
                )

                longitude = float(
                    lng
                )

            except (
                TypeError,
                ValueError,
            ):
                continue

            if self._valid_coordinate(
                latitude,
                longitude,
            ):

                return (
                    latitude,
                    longitude,
                )

        return None, None

    # ========================================================
    # ADDRESS
    # ========================================================

    def _extract_address(
        self,
        raw: Dict[str, Any],
    ) -> str:

        for key in (
            "address",
            "formatted_address",
            "formattedAddress",
            "address_text",
        ):

            value = self._normalize_text(
                raw.get(key)
                or ""
            )

            if value:
                return value

        return ""

    def _extract_neighborhood(
        self,
        raw: Dict[str, Any],
    ) -> str:

        for key in (
            "neighbourhood",
            "neighborhood",
            "district",
        ):

            value = self._normalize_text(
                raw.get(key)
                or ""
            )

            if value:
                return value

        return ""

    def _extract_street(
        self,
        raw: Dict[str, Any],
    ) -> str:

        for key in (
            "route_name",
            "route",
            "street",
            "street_name",
        ):

            value = self._normalize_text(
                raw.get(key)
                or ""
            )

            if value:
                return value

        return ""

    def _extract_city(
        self,
        raw: Dict[str, Any],
    ) -> str:

        for key in (
            "city",
            "town",
            "municipality",
        ):

            value = self._normalize_text(
                raw.get(key)
                or ""
            )

            if value:
                return value

        region = self._normalize_text(
            raw.get("region")
            or ""
        )

        if region:

            parts = [
                part.strip()
                for part in region.split(",")
                if part.strip()
            ]

            if parts:
                return parts[0]

        return ""

    def _extract_province(
        self,
        raw: Dict[str, Any],
    ) -> str:

        for key in (
            "state",
            "province",
        ):

            value = self._normalize_text(
                raw.get(key)
                or ""
            )

            if value:
                return value

        region = self._normalize_text(
            raw.get("region")
            or ""
        )

        if region:

            parts = [
                part.strip()
                for part in region.split(",")
                if part.strip()
            ]

            if len(parts) >= 2:
                return parts[-1]

        return ""

    # ========================================================
    # PHONE
    # ========================================================

    def _extract_phone(
        self,
        raw: Dict[str, Any],
    ) -> str:

        for key in (
            "phone",
            "telephone",
            "mobile",
            "contact_phone",
            "contact:phone",
        ):

            value = raw.get(
                key
            )

            if value:
                return self._normalize_phone(
                    value
                )

        contact = raw.get(
            "contact"
        )

        if isinstance(
            contact,
            dict,
        ):

            for key in (
                "phone",
                "telephone",
                "mobile",
            ):

                value = contact.get(
                    key
                )

                if value:
                    return self._normalize_phone(
                        value
                    )

        return ""

    def _normalize_phone(
        self,
        value: Any,
    ) -> str:

        text = str(
            value or ""
        ).strip()

        text = self._normalize_digits(
            text
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text

    # ========================================================
    # WEBSITE
    # ========================================================

    def _extract_website(
        self,
        raw: Dict[str, Any],
    ) -> str:

        for key in (
            "website",
            "url",
            "website_url",
            "websiteUrl",
        ):

            value = self._normalize_text(
                raw.get(key)
                or ""
            )

            if value:
                return self._normalize_url(
                    value
                )

        return ""

    def _normalize_url(
        self,
        value: str,
    ) -> str:

        value = value.strip()

        if not value:
            return ""

        if value.startswith(
            (
                "http://",
                "https://",
            )
        ):

            return value

        if re.match(
            r"^(?:www\.)?[\w.-]+\.[A-Za-z]{2,}(?:/.*)?$",
            value,
        ):

            return (
                "https://"
                + value
            )

        return ""

    # ========================================================
    # TYPE / CATEGORY
    # ========================================================

    def _extract_type(
        self,
        raw: Dict[str, Any],
    ) -> str:

        for key in (
            "type",
            "place_type",
            "placeType",
        ):

            value = self._normalize_text(
                raw.get(key)
                or ""
            )

            if value:
                return value

        return ""

    def _extract_category(
        self,
        raw: Dict[str, Any],
    ) -> str:

        for key in (
            "category",
            "category_name",
            "categoryName",
        ):

            value = self._normalize_text(
                raw.get(key)
                or ""
            )

            if value:
                return value

        return ""

    def _resolve_category(
        self,
        *,
        text: str,
        neshan_type: str,
        neshan_category: str,
    ) -> str:

        metadata = self._normalize_text(
            f"{neshan_type} "
            f"{neshan_category}"
        )

        for category, terms in (
            CATEGORY_KEYWORDS.items()
        ):

            if self._contains_any(
                metadata,
                terms,
            ):

                return category

        for category, terms in (
            CATEGORY_KEYWORDS.items()
        ):

            if self._contains_any(
                text,
                terms,
            ):

                return category

        return "unknown"

    # ========================================================
    # BUSINESS CLASSIFICATION
    # ========================================================

    def _classify_business(
        self,
        *,
        name: str,
        neshan_type: str,
        neshan_category: str,
        category: str,
    ) -> Dict[str, Any]:

        if category != "unknown":

            return {
                "semantic_type": "business",
                "confidence": 0.90,
            }

        metadata = self._normalize_text(
            f"{name} "
            f"{neshan_type} "
            f"{neshan_category}"
        )

        metadata_lower = metadata.lower()

        if metadata_lower in {
            "municipal",
            "region",
        }:

            return {
                "semantic_type": "place",
                "confidence": 0.05,
            }

        if self._contains_any(
            metadata,
            NON_BUSINESS_TERMS,
        ):

            return {
                "semantic_type": "place",
                "confidence": 0.10,
            }

        return {
            "semantic_type": "business",
            "confidence": 0.50,
        }

    # ========================================================
    # SCORE
    # ========================================================

    def _calculate_score(
        self,
        *,
        name: str,
        category: str,
        address: str,
        phone: str,
        website: str,
        neshan_type: str,
        neshan_category: str,
        source_query: str,
        distance_km: Optional[float],
        semantic: Dict[str, Any],
    ) -> float:

        score = 0.0

        if name:
            score += 25.0

        if category != "unknown":
            score += 20.0

        if neshan_type:
            score += 8.0

        if neshan_category:
            score += 8.0

        if address:
            score += 12.0

        if phone:
            score += 7.0

        if website:
            score += 5.0

        if self._query_matches_name(
            source_query,
            name,
        ):
            score += 5.0

        semantic_confidence = float(
            semantic.get(
                "confidence",
                0.0,
            )
        )

        score += (
            semantic_confidence
            * 10.0
        )

        if distance_km is not None:

            if distance_km <= 1:
                score += 5.0

            elif distance_km <= 3:
                score += 4.0

            elif distance_km <= 5:
                score += 3.0

            elif distance_km <= 10:
                score += 1.0

        return round(
            min(
                100.0,
                score,
            ),
            2,
        )

    # ========================================================
    # CONFIDENCE
    # ========================================================

    def _calculate_confidence(
        self,
        *,
        score: float,
        category: str,
        semantic: Dict[str, Any],
        address: str,
        phone: str,
        website: str,
    ) -> float:

        confidence = (
            score / 100.0
        )

        semantic_confidence = float(
            semantic.get(
                "confidence",
                0.0,
            )
        )

        confidence = (
            confidence * 0.70
            + semantic_confidence * 0.30
        )

        if category == "unknown":
            confidence -= 0.03

        if not address:
            confidence -= 0.01

        if not phone and not website:
            confidence -= 0.01

        return round(
            max(
                0.0,
                min(
                    1.0,
                    confidence,
                ),
            ),
            4,
        )

    # ========================================================
    # VERIFICATION
    # ========================================================

    def _calculate_verification(
        self,
        *,
        raw: Dict[str, Any],
        score: float,
        confidence: float,
    ) -> bool:

        source_id = (
            self._extract_source_id(
                raw
            )
        )

        return bool(
            source_id
            and score >= 70.0
            and confidence >= 0.70
        )

    # ========================================================
    # ACCEPTANCE
    # ========================================================

    def _is_acceptable(
        self,
        candidate: Candidate,
    ) -> bool:

        if not candidate.name:
            return False

        if not self._valid_coordinate(
            candidate.latitude,
            candidate.longitude,
        ):
            return False

        if (
            candidate.semantic_type
            == "place"
        ):
            return False

        if (
            candidate.score
            < self.min_score
        ):
            return False

        if (
            candidate.confidence
            < self.min_confidence
        ):
            return False

        return True

    # ========================================================
    # DISTANCE
    # ========================================================

    def _extract_distance(
        self,
        raw: Dict[str, Any],
    ) -> Optional[float]:

        for key in (
            "distance",
            "distance_km",
            "distanceKm",
        ):

            value = raw.get(
                key
            )

            if value is None:
                continue

            try:

                result = float(
                    value
                )

                if math.isfinite(
                    result
                ):
                    return result

            except (
                TypeError,
                ValueError,
            ):
                continue

        return None

    def _distance_km(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:

        phi1 = math.radians(
            lat1
        )

        phi2 = math.radians(
            lat2
        )

        delta_phi = math.radians(
            lat2 - lat1
        )

        delta_lambda = math.radians(
            lon2 - lon1
        )

        a = (
            math.sin(
                delta_phi / 2.0
            ) ** 2
            +
            math.cos(phi1)
            * math.cos(phi2)
            * math.sin(
                delta_lambda / 2.0
            ) ** 2
        )

        a = max(
            0.0,
            min(
                1.0,
                a,
            ),
        )

        return (
            EARTH_RADIUS_KM
            * 2.0
            * math.atan2(
                math.sqrt(a),
                math.sqrt(
                    1.0 - a
                ),
            )
        )

    # ========================================================
    # SOURCE
    # ========================================================

    def _extract_source_id(
        self,
        raw: Dict[str, Any],
    ) -> str:

        for key in (
            "place_id",
            "placeId",
            "id",
            "uid",
            "object_id",
            "objectId",
        ):

            value = raw.get(
                key
            )

            if value is not None:

                text = str(
                    value
                ).strip()

                if text:
                    return text

        return ""

    def _build_source_type(
        self,
        raw: Dict[str, Any],
    ) -> str:

        values: List[str] = []

        for key in (
            "type",
            "place_type",
            "category",
        ):

            value = self._normalize_text(
                raw.get(key)
                or ""
            )

            if value:
                values.append(
                    value
                )

        return ":".join(
            values
        )

    # ========================================================
    # DEDUPLICATION
    # ========================================================

    def _deduplicate(
        self,
        candidates: Sequence[Candidate],
    ) -> List[Candidate]:

        result: List[Candidate] = []

        seen_ids = set()
        seen_geo = set()
        seen_names = set()

        for candidate in candidates:

            source_id = (
                candidate.source_id
            )

            if (
                source_id
                and source_id in seen_ids
            ):

                self.stats[
                    "duplicates"
                ] += 1

                continue

            geo_key = self._geo_key(
                candidate
            )

            if geo_key in seen_geo:

                self.stats[
                    "duplicates"
                ] += 1

                continue

            name_key = (
                self._dedupe_name(
                    candidate.name
                )
            )

            if (
                name_key
                and name_key in seen_names
            ):

                if self._nearby_candidate_exists(
                    candidate,
                    result,
                ):

                    self.stats[
                        "duplicates"
                    ] += 1

                    continue

            if source_id:
                seen_ids.add(
                    source_id
                )

            seen_geo.add(
                geo_key
            )

            if name_key:
                seen_names.add(
                    name_key
                )

            result.append(
                candidate
            )

        return result

    def _geo_key(
        self,
        candidate: Candidate,
    ) -> str:

        name = self._dedupe_name(
            candidate.name
        )

        return (
            f"{name}|"
            f"{round(candidate.latitude, 4)}|"
            f"{round(candidate.longitude, 4)}"
        )

    def _dedupe_name(
        self,
        value: str,
    ) -> str:

        text = self._normalize_text(
            value
        ).lower()

        text = re.sub(
            r"[^\w\u0600-\u06ff]+",
            "",
            text,
        )

        return text

    def _nearby_candidate_exists(
        self,
        candidate: Candidate,
        existing: Sequence[Candidate],
    ) -> bool:

        for item in existing:

            if (
                self._dedupe_name(
                    item.name
                )
                != self._dedupe_name(
                    candidate.name
                )
            ):
                continue

            distance = self._distance_km(
                item.latitude,
                item.longitude,
                candidate.latitude,
                candidate.longitude,
            )

            if distance <= 0.05:
                return True

        return False

    # ========================================================
    # RANKING
    # ========================================================

    def _ranking_key(
        self,
        candidate: Candidate,
    ) -> Tuple[
        float,
        float,
        float,
        float,
    ]:

        distance_score = 0.0

        if (
            candidate.distance_km
            is not None
        ):

            distance_score = (
                1.0
                / (
                    1.0
                    + candidate.distance_km
                )
            )

        return (
            candidate.score,
            candidate.confidence,
            distance_score,
            (
                1.0
                if candidate.verification
                else 0.0
            ),
        )

    # ========================================================
    # OUTPUT
    # ========================================================

    def _to_dict(
        self,
        candidate: Candidate,
    ) -> Dict[str, Any]:

        return {
            "name": candidate.name,
            "category": candidate.category,

            "city": candidate.city,
            "province": candidate.province,

            "phone": candidate.phone,
            "website": candidate.website,
            "address": candidate.address,

            "latitude": float(
                candidate.latitude
            ),

            "longitude": float(
                candidate.longitude
            ),

            "distance_km": (
                float(
                    candidate.distance_km
                )
                if candidate.distance_km
                is not None
                else None
            ),

            "source": PROVIDER_NAME,
            "source_id": candidate.source_id,
            "source_type": candidate.source_type,

            "url": candidate.website,

            "score": float(
                candidate.score
            ),

            "confidence": float(
                candidate.confidence
            ),

            "semantic_type": (
                candidate.semantic_type
            ),

            "verification": bool(
                candidate.verification
            ),

            "query": candidate.source_query,

            "neighborhood": (
                candidate.neighborhood
            ),

            "street": candidate.street,

            "api_distance": (
                float(
                    candidate.api_distance
                )
                if candidate.api_distance
                is not None
                else None
            ),

            "neshan_type": (
                candidate.neshan_type
            ),

            "neshan_category": (
                candidate.neshan_category
            ),
        }

    # ========================================================
    # SEARCHABLE TEXT
    # ========================================================

    def _build_searchable_text(
        self,
        *,
        raw: Dict[str, Any],
        name: str,
        address: str,
        source_query: str,
    ) -> str:

        values = [
            name,
            address,
            source_query,

            self._string_value(
                raw.get("type")
            ),

            self._string_value(
                raw.get("category")
            ),

            self._string_value(
                raw.get("category_name")
            ),

            self._string_value(
                raw.get("description")
            ),
        ]

        return self._normalize_text(
            " ".join(
                value
                for value in values
                if value
            )
        )

    # ========================================================
    # QUERY MATCH
    # ========================================================

    def _query_matches_name(
        self,
        query: str,
        name: str,
    ) -> bool:

        query_tokens = {
            token
            for token in self._normalize_text(
                query
            ).split()
            if len(token) >= 2
        }

        name_tokens = {
            token
            for token in self._normalize_text(
                name
            ).split()
            if len(token) >= 2
        }

        return bool(
            query_tokens
            & name_tokens
        )

    # ========================================================
    # TEXT
    # ========================================================

    def _contains_any(
        self,
        text: str,
        terms: Sequence[str],
    ) -> bool:

        normalized = self._normalize_text(
            text
        )

        for term in terms:

            normalized_term = (
                self._normalize_text(
                    term
                )
            )

            if (
                normalized_term
                and normalized_term
                in normalized
            ):

                return True

        return False

    def _string_value(
        self,
        value: Any,
    ) -> str:

        if value is None:
            return ""

        if isinstance(
            value,
            Mapping,
        ):

            return " ".join(
                self._string_value(
                    item
                )
                for item in value.values()
            )

        if isinstance(
            value,
            (list, tuple, set),
        ):

            return " ".join(
                self._string_value(
                    item
                )
                for item in value
            )

        return str(value)

    def _normalize_text(
        self,
        value: Any,
    ) -> str:

        if value is None:
            return ""

        text = str(
            value
        ).strip()

        if not text:
            return ""

        replacements = {
            "ي": "ی",
            "ى": "ی",
            "ك": "ک",
            "ۀ": "ه",
            "ة": "ه",
            "ؤ": "و",
            "إ": "ا",
            "أ": "ا",

            "\u200c": " ",
            "\u200f": " ",
            "\u200e": " ",
        }

        for old, new in (
            replacements.items()
        ):

            text = text.replace(
                old,
                new,
            )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    def _normalize_digits(
        self,
        value: str,
    ) -> str:

        replacements = str.maketrans(
            {
                "۰": "0",
                "۱": "1",
                "۲": "2",
                "۳": "3",
                "۴": "4",
                "۵": "5",
                "۶": "6",
                "۷": "7",
                "۸": "8",
                "۹": "9",

                "٠": "0",
                "١": "1",
                "٢": "2",
                "٣": "3",
                "٤": "4",
                "٥": "5",
                "٦": "6",
                "٧": "7",
                "٨": "8",
                "٩": "9",
            }
        )

        return value.translate(
            replacements
        )

    # ========================================================
    # COORDINATE VALIDATION
    # ========================================================

    def _valid_coordinate(
        self,
        latitude: Any,
        longitude: Any,
    ) -> bool:

        try:

            lat = float(
                latitude
            )

            lng = float(
                longitude
            )

        except (
            TypeError,
            ValueError,
        ):

            return False

        if not (
            math.isfinite(lat)
            and math.isfinite(lng)
        ):

            return False

        return (
            -90.0 <= lat <= 90.0
            and -180.0 <= lng <= 180.0
        )

    # ========================================================
    # LIMIT
    # ========================================================

    def _resolve_limit(
        self,
        max_results: Optional[int],
    ) -> int:

        if max_results is None:
            return self.max_results

        try:

            value = int(
                max_results
            )

        except (
            TypeError,
            ValueError,
        ):

            value = self.max_results

        return max(
            1,
            min(
                DEFAULT_MAX_RESULTS,
                value,
            ),
        )

    # ========================================================
    # STATS
    # ========================================================

    @staticmethod
    def _new_stats() -> Dict[str, int]:

        return {
            "requests": 0,
            "raw_results": 0,
            "candidates": 0,
            "accepted": 0,
            "rejected": 0,
            "duplicates": 0,
            "radius_filtered": 0,
            "http_errors": 0,
            "request_errors": 0,
            "parse_errors": 0,
            "configuration_errors": 0,
            "geographic_errors": 0,
            "errors": 0,
        }

    # ========================================================
    # LOG
    # ========================================================

    def _log(
        self,
        message: str,
    ) -> None:

        if not self.debug:
            return

        print(message)

    # ========================================================
    # CLOSE
    # ========================================================

    def close(self) -> None:

        if self.session is None:
            return

        try:
            self.session.close()
        except Exception:
            pass


# ============================================================
# END OF FILE
# ============================================================