# ============================================================
# EYE SCRAPPER
# GENERIC OSM / NOMINATIM BUSINESS DISCOVERY PROVIDER
# ============================================================
#
# PROVIDER VERSION
# ============================================================
#
#     6.1.0
#
#
# PURPOSE
# ============================================================
#
# Generic place / business discovery provider based on
# OpenStreetMap Nominatim.
#
# IMPORTANT:
#
# This provider is intentionally discovery-oriented.
#
# Unlike a strict classifier, it does NOT discard a valid
# geographic result merely because OSM has incomplete
# classification/contact metadata.
#
# A valid result generally requires:
#
#     - valid name
#     - valid latitude
#     - valid longitude
#
# Classification, score and confidence are used primarily
# for categorization and ranking.
#
#
# PIPELINE
# ============================================================
#
#     Query
#       ↓
#     Query normalization
#       ↓
#     Query planning
#       ↓
#     Nominatim request
#       ↓
#     Raw result normalization
#       ↓
#     Geographic validation
#       ↓
#     Category resolution
#       ↓
#     Business / place classification
#       ↓
#     Quality scoring
#       ↓
#     Deduplication
#       ↓
#     Ranking
#       ↓
#     Stable dictionary output
#
#
# OUTPUT CONTRACT
# ============================================================
#
# search() returns:
#
# List[Dict[str, Any]]
#
# Every accepted result follows:
#
# {
#     "name": str,
#     "category": str,
#     "city": str,
#     "province": str,
#     "phone": str,
#     "website": str,
#     "address": str,
#     "latitude": float,
#     "longitude": float,
#     "distance_km": float | None,
#
#     "source": "osm",
#     "source_id": str,
#     "source_type": str,
#     "url": str,
#
#     "score": float,
#     "confidence": float,
#     "semantic_type": str,
#     "verification": bool,
#     "query": str,
#
#     "neighborhood": str,
#     "street": str,
#
#     "api_distance": float | None,
#
#     "osm_type": str,
#     "osm_class": str,
#     "osm_type_value": str,
# }
#
# ============================================================


from __future__ import annotations


# ============================================================
# STANDARD LIBRARY
# ============================================================

import math
import re
import time

from dataclasses import dataclass, field
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
)


# ============================================================
# THIRD PARTY
# ============================================================

import requests


# ============================================================
# PROJECT
# ============================================================

from providers.base import SearchProvider


# ============================================================
# PROVIDER METADATA
# ============================================================

PROVIDER_NAME = "osm"
PROVIDER_VERSION = "6.1.0"

BASE_URL = "https://www.openstreetmap.org"

SEARCH_ENDPOINT = (
    "https://nominatim.openstreetmap.org/search"
)

REVERSE_ENDPOINT = (
    "https://nominatim.openstreetmap.org/reverse"
)

DEFAULT_TIMEOUT = 15.0

# Nominatim public service should not be hammered.
DEFAULT_DELAY = 1.0

DEFAULT_MAX_RESULTS = 30

DEFAULT_REQUEST_LIMIT = 50

DEFAULT_MAX_QUERIES = 6

# These are ranking thresholds only.
DEFAULT_MIN_SCORE = 0.0
DEFAULT_MIN_CONFIDENCE = 0.0

EARTH_RADIUS_KM = 6371.0088

IRAN_COUNTRY_CODE = "ir"


# ============================================================
# CITY DATABASE
# ============================================================

CITY_DATABASE: Dict[str, Dict[str, float]] = {

    "تبریز": {
        "center_lat": 38.0962,
        "center_lon": 46.2738,
        "min_lat": 37.80,
        "max_lat": 38.35,
        "min_lon": 45.90,
        "max_lon": 46.75,
    },

    "تهران": {
        "center_lat": 35.6892,
        "center_lon": 51.3890,
        "min_lat": 35.45,
        "max_lat": 35.90,
        "min_lon": 50.95,
        "max_lon": 51.80,
    },

    "کرج": {
        "center_lat": 35.8400,
        "center_lon": 50.9391,
        "min_lat": 35.60,
        "max_lat": 36.10,
        "min_lon": 50.70,
        "max_lon": 51.30,
    },

    "مشهد": {
        "center_lat": 36.2605,
        "center_lon": 59.6168,
        "min_lat": 35.95,
        "max_lat": 36.55,
        "min_lon": 59.30,
        "max_lon": 59.90,
    },

    "اصفهان": {
        "center_lat": 32.6546,
        "center_lon": 51.6680,
        "min_lat": 32.45,
        "max_lat": 32.85,
        "min_lon": 51.45,
        "max_lon": 51.90,
    },

    "شیراز": {
        "center_lat": 29.5918,
        "center_lon": 52.5837,
        "min_lat": 29.45,
        "max_lat": 29.90,
        "min_lon": 52.30,
        "max_lon": 52.75,
    },

    "اهواز": {
        "center_lat": 31.3183,
        "center_lon": 48.6706,
        "min_lat": 31.15,
        "max_lat": 31.55,
        "min_lon": 48.50,
        "max_lon": 48.90,
    },

    "رشت": {
        "center_lat": 37.2808,
        "center_lon": 49.5832,
        "min_lat": 37.10,
        "max_lat": 37.45,
        "min_lon": 49.40,
        "max_lon": 49.75,
    },

    "قم": {
        "center_lat": 34.6416,
        "center_lon": 50.8746,
        "min_lat": 34.45,
        "max_lat": 34.80,
        "min_lon": 50.60,
        "max_lon": 51.20,
    },

    "کرمان": {
        "center_lat": 30.2839,
        "center_lon": 57.0834,
        "min_lat": 29.80,
        "max_lat": 30.50,
        "min_lon": 56.70,
        "max_lon": 57.50,
    },

    "ارومیه": {
        "center_lat": 37.5527,
        "center_lon": 45.0761,
        "min_lat": 37.00,
        "max_lat": 38.00,
        "min_lon": 44.80,
        "max_lon": 45.50,
    },

    "یزد": {
        "center_lat": 31.8974,
        "center_lon": 54.3569,
        "min_lat": 31.70,
        "max_lat": 32.30,
        "min_lon": 53.70,
        "max_lon": 54.60,
    },

    "اردبیل": {
        "center_lat": 38.2498,
        "center_lon": 48.2933,
        "min_lat": 38.00,
        "max_lat": 38.50,
        "min_lon": 47.80,
        "max_lon": 48.60,
    },

    "سنندج": {
        "center_lat": 35.3219,
        "center_lon": 46.9862,
        "min_lat": 35.20,
        "max_lat": 35.80,
        "min_lon": 46.80,
        "max_lon": 47.30,
    },

    "کرمانشاه": {
        "center_lat": 34.3142,
        "center_lon": 47.0650,
        "min_lat": 34.00,
        "max_lat": 34.70,
        "min_lon": 46.50,
        "max_lon": 47.20,
    },

    "همدان": {
        "center_lat": 34.7980,
        "center_lon": 48.5148,
        "min_lat": 34.60,
        "max_lat": 35.20,
        "min_lon": 48.20,
        "max_lon": 48.80,
    },

    "قزوین": {
        "center_lat": 36.2688,
        "center_lon": 50.0041,
        "min_lat": 35.70,
        "max_lat": 36.60,
        "min_lon": 49.60,
        "max_lon": 50.40,
    },

    "زنجان": {
        "center_lat": 36.6769,
        "center_lon": 48.4963,
        "min_lat": 36.30,
        "max_lat": 37.00,
        "min_lon": 48.20,
        "max_lon": 49.40,
    },

    "ساری": {
        "center_lat": 36.5659,
        "center_lon": 53.0586,
        "min_lat": 36.20,
        "max_lat": 36.70,
        "min_lon": 52.70,
        "max_lon": 53.50,
    },

    "بابل": {
        "center_lat": 36.5387,
        "center_lon": 52.6765,
        "min_lat": 36.20,
        "max_lat": 36.60,
        "min_lon": 52.55,
        "max_lon": 53.20,
    },

    "گرگان": {
        "center_lat": 36.8456,
        "center_lon": 54.4393,
        "min_lat": 36.60,
        "max_lat": 37.00,
        "min_lon": 54.20,
        "max_lon": 54.70,
    },

    "بندرعباس": {
        "center_lat": 27.1832,
        "center_lon": 56.2666,
        "min_lat": 26.80,
        "max_lat": 27.50,
        "min_lon": 56.00,
        "max_lon": 56.70,
    },

    "بوشهر": {
        "center_lat": 28.9234,
        "center_lon": 50.8203,
        "min_lat": 28.70,
        "max_lat": 29.10,
        "min_lon": 50.60,
        "max_lon": 51.00,
    },

    "خرم‌آباد": {
        "center_lat": 33.4878,
        "center_lon": 48.3558,
        "min_lat": 32.90,
        "max_lat": 33.70,
        "min_lon": 47.70,
        "max_lon": 48.80,
    },

    "ایلام": {
        "center_lat": 33.6374,
        "center_lon": 46.4227,
        "min_lat": 32.50,
        "max_lat": 33.00,
        "min_lon": 46.10,
        "max_lon": 47.10,
    },

    "اراک": {
        "center_lat": 34.0954,
        "center_lon": 49.7013,
        "min_lat": 33.80,
        "max_lat": 34.50,
        "min_lon": 49.40,
        "max_lon": 50.20,
    },

    "کاشان": {
        "center_lat": 33.9850,
        "center_lon": 51.4090,
        "min_lat": 33.70,
        "max_lat": 34.20,
        "min_lon": 51.00,
        "max_lon": 51.70,
    },

    "نیشابور": {
        "center_lat": 36.2140,
        "center_lon": 58.7967,
        "min_lat": 35.80,
        "max_lat": 36.50,
        "min_lon": 58.50,
        "max_lon": 59.20,
    },

    "سبزوار": {
        "center_lat": 36.2090,
        "center_lon": 57.6810,
        "min_lat": 35.40,
        "max_lat": 36.20,
        "min_lon": 57.00,
        "max_lon": 58.00,
    },

    "بیرجند": {
        "center_lat": 32.8663,
        "center_lon": 59.2211,
        "min_lat": 32.50,
        "max_lat": 33.50,
        "min_lon": 58.80,
        "max_lon": 59.60,
    },

    "زاهدان": {
        "center_lat": 29.4963,
        "center_lon": 60.8629,
        "min_lat": 29.20,
        "max_lat": 30.00,
        "min_lon": 60.50,
        "max_lon": 61.00,
    },

    "بجنورد": {
        "center_lat": 37.4750,
        "center_lon": 57.3327,
        "min_lat": 37.20,
        "max_lat": 37.80,
        "min_lon": 57.00,
        "max_lon": 57.80,
    },

    "گرمسار": {
        "center_lat": 35.2183,
        "center_lon": 52.3406,
        "min_lat": 34.90,
        "max_lat": 35.50,
        "min_lon": 52.00,
        "max_lon": 53.00,
    },
}


# ============================================================
# CATEGORY MAP
# ============================================================

OSM_CATEGORY_MAP: Dict[str, str] = {

    "school": "education",
    "college": "education",
    "university": "education",
    "kindergarten": "education",
    "language_school": "education",
    "music_school": "education",
    "driving_school": "education",

    "shop": "retail",
    "supermarket": "retail",
    "convenience": "retail",
    "department_store": "retail",
    "mall": "retail",
    "market": "retail",
    "wholesale": "retail",
    "mobile_phone": "retail",
    "electronics": "retail",
    "computer": "retail",
    "hardware": "retail",
    "furniture": "retail",

    "clothes": "fashion",
    "shoes": "fashion",
    "bag": "fashion",
    "jewelry": "fashion",
    "fashion": "fashion",

    "bakery": "food",
    "confectionery": "food",
    "pastry": "food",
    "butcher": "food",
    "deli": "food",
    "greengrocer": "food",
    "beverages": "food",

    "restaurant": "restaurant",
    "fast_food": "food",
    "food_court": "food",
    "ice_cream": "food",

    "cafe": "cafe",
    "coffee_shop": "cafe",
    "bar": "food",

    "hotel": "hospitality",
    "motel": "hospitality",
    "guest_house": "hospitality",
    "hostel": "hospitality",

    "hospital": "healthcare",
    "clinic": "healthcare",
    "doctors": "healthcare",
    "dentist": "healthcare",
    "pharmacy": "healthcare",
    "laboratory": "healthcare",
    "optician": "healthcare",
    "veterinary": "healthcare",

    "bank": "finance",
    "insurance": "finance",
    "bureau_de_change": "finance",
    "money_transfer": "finance",
    "atm": "finance",

    "car_repair": "automotive",
    "car_parts": "automotive",
    "car_dealer": "automotive",
    "car_rental": "automotive",
    "motorcycle": "automotive",
    "tyres": "automotive",
    "fuel": "automotive",

    "hairdresser": "beauty",
    "beauty": "beauty",
    "cosmetics": "beauty",

    "real_estate": "real_estate",
    "estate_agent": "real_estate",

    "lawyer": "professional_services",
    "accountant": "professional_services",
    "consulting": "professional_services",
    "architect": "professional_services",

    "travel_agency": "travel",
    "tourism": "travel",

    "office": "office",
    "company": "company",

    "factory": "industrial",
    "industrial": "industrial",
    "warehouse": "industrial",

    "craft": "services",
    "carpenter": "services",
    "plumber": "services",
    "electrician": "services",
    "tailor": "services",
    "photographer": "services",
}


# ============================================================
# OSM CLASSIFICATION
# ============================================================

BUSINESS_OSM_CLASSES = {
    "shop",
    "amenity",
    "office",
    "craft",
    "tourism",
    "healthcare",
    "commercial",
    "industrial",
    "leisure",
}

NON_BUSINESS_CLASSES = {
    "natural",
    "boundary",
    "highway",
    "waterway",
    "landuse",
    "aeroway",
    "railway",
}


# ============================================================
# TEXT TERMS
# ============================================================

BUSINESS_TERMS = (
    "شرکت",
    "فروشگاه",
    "مغازه",
    "مرکز",
    "دفتر",
    "نمایندگی",
    "کارخانه",
    "کارگاه",
    "رستوران",
    "کافه",
    "هتل",
    "مهمانپذیر",
    "کلینیک",
    "بیمارستان",
    "داروخانه",
    "آزمایشگاه",
    "مطب",
    "دندانپزشکی",
    "آرایشگاه",
    "فروش",
    "بازرگانی",
    "تجاری",
    "خدمات",
    "موسسه",
    "مؤسسه",
    "آژانس",
    "بانک",
    "بیمه",
    "صرافی",
    "املاک",
    "آموزشگاه",
    "مدرسه",
    "دانشگاه",
    "دبیرستان",
    "دبستان",
    "هنرستان",
    "کتابفروشی",
    "نانوایی",
    "قنادی",
    "شیرینی",
    "سوپرمارکت",
    "هایپرمارکت",
    "پوشاک",
    "موبایل",
    "کامپیوتر",
    "تعمیرگاه",
)


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
    "مرز",
)


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class CityContext:

    name: str

    normalized_name: str

    center_lat: Optional[float] = None
    center_lon: Optional[float] = None

    min_lat: Optional[float] = None
    max_lat: Optional[float] = None

    min_lon: Optional[float] = None
    max_lon: Optional[float] = None

    province: str = ""

    @property
    def has_center(self) -> bool:
        return (
            self.center_lat is not None
            and self.center_lon is not None
        )

    @property
    def has_bounds(self) -> bool:
        return all(
            value is not None
            for value in (
                self.min_lat,
                self.max_lat,
                self.min_lon,
                self.max_lon,
            )
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

    osm_type: str = ""
    osm_class: str = ""
    osm_type_value: str = ""

    score: float = 0.0
    confidence: float = 0.0

    distance_km: Optional[float] = None

    semantic_type: str = "place"

    verification: bool = False

    source_query: str = ""

    raw: Dict[str, Any] = field(
        default_factory=dict
    )


# ============================================================
# PROVIDER
# ============================================================

class OSMProvider(SearchProvider):

    name = PROVIDER_NAME

    def __init__(
        self,
        *,
        delay: float = DEFAULT_DELAY,
        timeout: float = DEFAULT_TIMEOUT,
        max_results: int = DEFAULT_MAX_RESULTS,
        max_queries: int = DEFAULT_MAX_QUERIES,
        min_score: float = DEFAULT_MIN_SCORE,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
        user_agent: str = (
            "EYE-Scrapper/6.1 "
            "(Business Discovery Project)"
        ),
        session: Optional[
            requests.Session
        ] = None,
        debug: bool = True,
    ) -> None:

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
            int(max_results),
        )

        self.max_queries = max(
            1,
            int(max_queries),
        )

        self.min_score = max(
            0.0,
            min(100.0, float(min_score)),
        )

        self.min_confidence = max(
            0.0,
            min(1.0, float(min_confidence)),
        )

        self.user_agent = (
            str(user_agent).strip()
            or "EYE-Scrapper/6.1"
        )

        self.session = (
            session
            if session is not None
            else requests.Session()
        )

        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Accept-Language": "fa,en;q=0.8",
            }
        )

        self.debug = bool(debug)

        self._last_request_at = 0.0

        self._city_cache: Dict[
            str,
            Optional[Tuple[float, float]]
        ] = {}

        self.stats = self._new_stats()

    # ========================================================
    # PUBLIC API
    # ========================================================

    def info(self) -> Dict[str, Any]:

        return {
            "name": PROVIDER_NAME,
            "version": PROVIDER_VERSION,
            "type": "business_search",
            "base_url": BASE_URL,
            "endpoint": SEARCH_ENDPOINT,
            "reverse_endpoint": REVERSE_ENDPOINT,
            "method": "GET",
            "format": "jsonv2",
            "country": "Iran",
            "timeout": self.timeout,
            "delay": self.delay,
            "max_results": self.max_results,
            "max_queries": self.max_queries,
            "min_score": self.min_score,
            "min_confidence": self.min_confidence,
            "user_agent": self.user_agent,
            "module": __name__,
        }

    def health_check(self) -> bool:

        try:

            data = self._request(
                "Iran",
                limit=1,
                use_viewbox=False,
            )

            return isinstance(
                data,
                list,
            )

        except Exception as exc:

            self._log(
                f"[OSM][HEALTH] FAILED: {exc}"
            )

            return False

    def search(
        self,
        query: str,
        page: int = 1,
        city: str = "",
        province: str = "",
        radius: float = 0,
        max_results: Optional[int] = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:

        self.stats = self._new_stats()

        limit = self._resolve_limit(
            max_results
        )

        clean_query = (
            self._normalize_text(query)
        )

        if not clean_query:
            return []

        city_context = (
            self._build_city_context(city)
        )

        radius = max(
            0.0,
            self._safe_float(radius),
        )

        center = self._resolve_center(
            city_context,
            radius,
        )

        query_plan = (
            self._build_query_plan(
                query=clean_query,
                city=city_context,
                province=province,
            )
        )

        query_plan = query_plan[
            :self.max_queries
        ]

        if not query_plan:
            return []

        self._log(
            f"[OSM] SEARCH "
            f"query={clean_query!r} "
            f"city={city or '-'} "
            f"province={province or '-'} "
            f"radius={radius or '-'}"
        )

        self._log(
            f"[OSM] QUERY PLAN: "
            f"{query_plan}"
        )

        candidates: List[Candidate] = []

        seen_queries = set()

        for current_query in query_plan:

            query_key = (
                self._normalize_text(
                    current_query
                )
            )

            if (
                not query_key
                or query_key in seen_queries
            ):
                continue

            seen_queries.add(query_key)

            self.stats["queries"] += 1

            self._log(
                f"[OSM] REQUEST "
                f"{self.stats['queries']}/"
                f"{len(query_plan)}: "
                f"{current_query}"
            )

            try:

                raw_results = self._request(
                    current_query,
                    limit=DEFAULT_REQUEST_LIMIT,
                    city_context=city_context,
                    **kwargs,
                )

            except requests.HTTPError as exc:

                self.stats[
                    "http_errors"
                ] += 1

                self._log(
                    f"[OSM][HTTP] {exc}"
                )

                continue

            except requests.RequestException as exc:

                self.stats[
                    "request_errors"
                ] += 1

                self._log(
                    f"[OSM][REQUEST] {exc}"
                )

                continue

            except ValueError as exc:

                self.stats[
                    "parse_errors"
                ] += 1

                self._log(
                    f"[OSM][JSON] {exc}"
                )

                continue

            except Exception as exc:

                self.stats[
                    "errors"
                ] += 1

                self._log(
                    f"[OSM][ERROR] {exc}"
                )

                continue

            self.stats[
                "raw_results"
            ] += len(raw_results)

            for raw in raw_results:

                candidate = (
                    self._parse_candidate(
                        raw=raw,
                        city=city_context,
                        center=center,
                        radius=radius,
                        source_query=current_query,
                    )
                )

                if candidate is not None:

                    candidates.append(
                        candidate
                    )

            unique = self._deduplicate(
                candidates
            )

            self._log(
                f"[OSM] "
                f"RAW={len(raw_results)} "
                f"UNIQUE={len(unique)} "
                f"CANDIDATES={len(candidates)}"
            )

            if len(unique) >= limit:
                break

        final = self._finalize(
            candidates,
            city=city_context,
            center=center,
            radius=radius,
        )

        final = final[:limit]

        self.stats["accepted"] = len(final)

        self._log(
            f"[OSM] FINAL={len(final)}"
        )

        return [
            self._to_dict(candidate)
            for candidate in final
        ]

    def close(self) -> None:

        if self.session is None:
            return

        try:
            self.session.close()
        except Exception:
            pass

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
            value = int(max_results)
        except (
            TypeError,
            ValueError,
        ):
            value = self.max_results

        return max(
            1,
            min(100, value),
        )

    # ========================================================
    # STATS
    # ========================================================

    @staticmethod
    def _new_stats() -> Dict[str, int]:

        return {
            "requests": 0,
            "queries": 0,
            "raw_results": 0,
            "candidates": 0,
            "accepted": 0,
            "rejected": 0,
            "duplicates": 0,
            "city_filtered": 0,
            "radius_filtered": 0,
            "invalid_coordinates": 0,
            "invalid_names": 0,
            "http_errors": 0,
            "request_errors": 0,
            "parse_errors": 0,
            "errors": 0,
            "city_geocodes": 0,
        }

    # ========================================================
    # REQUEST
    # ========================================================

    def _request(
        self,
        query: str,
        *,
        limit: int = DEFAULT_REQUEST_LIMIT,
        city_context: Optional[CityContext] = None,
        use_viewbox: bool = True,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:

        self._respect_rate_limit()

        params: Dict[str, Any] = {
            "q": query,
            "format": "jsonv2",
            "addressdetails": 1,
            "namedetails": 1,
            "extratags": 1,
            "dedupe": 1,
            "limit": max(
                1,
                min(50, int(limit)),
            ),
            "accept-language": "fa,en",
            "countrycodes": IRAN_COUNTRY_CODE,
        }

        #
        # IMPORTANT:
        #
        # We intentionally DO NOT use:
        #
        #     bounded=1
        #
        # because that causes Nominatim itself to discard
        # results before our provider can inspect them.
        #
        if use_viewbox:

            viewbox = self._build_viewbox(
                city_context
            )

            if viewbox:

                params["viewbox"] = viewbox

        for key, value in kwargs.items():

            if key in {
                "q",
                "query",
                "format",
                "page",
                "offset",
                "limit",
                "bounded",
            }:
                continue

            if value is None:
                continue

            params[key] = value

        self._log(
            f"[OSM] GET {SEARCH_ENDPOINT}"
        )

        response = self.session.get(
            SEARCH_ENDPOINT,
            params=params,
            timeout=self.timeout,
        )

        self.stats["requests"] += 1

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, list):

            raise ValueError(
                "Nominatim response is not a list"
            )

        return [
            item
            for item in data
            if isinstance(item, dict)
        ]

    def _respect_rate_limit(self) -> None:

        if self.delay <= 0:

            self._last_request_at = (
                time.monotonic()
            )

            return

        now = time.monotonic()

        elapsed = (
            now - self._last_request_at
        )

        remaining = (
            self.delay - elapsed
        )

        if remaining > 0:
            time.sleep(remaining)

        self._last_request_at = (
            time.monotonic()
        )

    # ========================================================
    # QUERY PLAN
    # ========================================================

    def _build_query_plan(
        self,
        *,
        query: str,
        city: Optional[CityContext],
        province: str,
    ) -> List[str]:

        query = self._normalize_text(
            query
        )

        if not query:
            return []

        queries: List[str] = []

        city_name = (
            city.name
            if city
            else ""
        )

        province_name = (
            self._normalize_text(
                province
            )
        )

        if city_name:

            queries.append(
                f"{query}, {city_name}"
            )

            if not self._contains_location(
                query,
                city_name,
            ):

                queries.append(
                    f"{query} {city_name}"
                )

        elif province_name:

            queries.extend(
                [
                    f"{query}, {province_name}",
                    f"{query} {province_name}",
                ]
            )

        else:

            queries.append(query)

        return self._unique_strings(
            queries
        )

    def _contains_location(
        self,
        query: str,
        location: str,
    ) -> bool:

        query_norm = (
            self._normalize_text(query)
        )

        location_norm = (
            self._normalize_text(location)
        )

        return bool(
            location_norm
            and location_norm in query_norm
        )

    # ========================================================
    # VIEWBOX
    # ========================================================

    def _build_viewbox(
        self,
        city: Optional[CityContext],
    ) -> str:

        if city is None:
            return ""

        if not city.has_bounds:
            return ""

        return (
            f"{city.min_lon},"
            f"{city.max_lat},"
            f"{city.max_lon},"
            f"{city.min_lat}"
        )

    # ========================================================
    # CITY CONTEXT
    # ========================================================

    def _build_city_context(
        self,
        city: Optional[str],
    ) -> Optional[CityContext]:

        if not city:
            return None

        normalized = (
            self._normalize_text(city)
        )

        if not normalized:
            return None

        canonical = (
            self._canonical_city(
                normalized
            )
        )

        data = CITY_DATABASE.get(
            canonical
        )

        if data is None:

            return CityContext(
                name=city.strip(),
                normalized_name=normalized,
            )

        return CityContext(
            name=canonical,
            normalized_name=(
                self._normalize_text(
                    canonical
                )
            ),
            center_lat=data.get(
                "center_lat"
            ),
            center_lon=data.get(
                "center_lon"
            ),
            min_lat=data.get(
                "min_lat"
            ),
            max_lat=data.get(
                "max_lat"
            ),
            min_lon=data.get(
                "min_lon"
            ),
            max_lon=data.get(
                "max_lon"
            ),
        )

    def _canonical_city(
        self,
        city: str,
    ) -> str:

        aliases = {

            "تبريز": "تبریز",
            "كرج": "کرج",
            "شيراز": "شیراز",
            "اروميه": "ارومیه",
            "يزد": "یزد",
            "اردبيل": "اردبیل",
            "قزوين": "قزوین",
            "زنجان": "زنجان",
            "ايلام": "ایلام",
            "نيشابور": "نیشابور",
            "بيرجند": "بیرجند",

            "خرم آباد": "خرم‌آباد",
            "خرم‌اباد": "خرم‌آباد",

            "بندر عباس": "بندرعباس",
            "کرمان شاه": "کرمانشاه",
        }

        return aliases.get(
            city,
            city,
        )

    # ========================================================
    # CENTER
    # ========================================================

    def _resolve_center(
        self,
        city: Optional[CityContext],
        radius: float,
    ) -> Optional[Tuple[float, float]]:

        if city is None:
            return None

        if city.has_center:

            return (
                float(city.center_lat),
                float(city.center_lon),
            )

        if radius <= 0:
            return None

        return self._geocode_city(
            city
        )

    def _geocode_city(
        self,
        city: CityContext,
    ) -> Optional[Tuple[float, float]]:

        key = city.normalized_name

        if key in self._city_cache:
            return self._city_cache[key]

        self._respect_rate_limit()

        params = {
            "q": f"{city.name}, Iran",
            "format": "jsonv2",
            "limit": 1,
            "addressdetails": 1,
            "countrycodes": IRAN_COUNTRY_CODE,
            "accept-language": "fa,en",
        }

        try:

            response = self.session.get(
                SEARCH_ENDPOINT,
                params=params,
                timeout=self.timeout,
            )

            self.stats["requests"] += 1
            self.stats["city_geocodes"] += 1

            response.raise_for_status()

            data = response.json()

        except (
            requests.RequestException,
            ValueError,
        ):

            self._city_cache[key] = None

            return None

        if (
            not isinstance(data, list)
            or not data
        ):

            self._city_cache[key] = None

            return None

        first = data[0]

        try:

            latitude = float(
                first["lat"]
            )

            longitude = float(
                first["lon"]
            )

        except (
            KeyError,
            TypeError,
            ValueError,
        ):

            self._city_cache[key] = None

            return None

        if not self._valid_coordinate(
            latitude,
            longitude,
        ):

            self._city_cache[key] = None

            return None

        result = (
            latitude,
            longitude,
        )

        self._city_cache[key] = result

        return result

    # ========================================================
    # GEOGRAPHIC VALIDATION
    # ========================================================

    def _validate_city(
        self,
        *,
        text: str,
        latitude: float,
        longitude: float,
        city: CityContext,
    ) -> bool:

        #
        # If no official/local boundary information exists,
        # don't reject based on missing text.
        #
        if not city.has_bounds:

            city_name = (
                city.normalized_name
            )

            if not city_name:
                return True

            #
            # Coordinates are already returned by Nominatim
            # with an Iranian country restriction.
            #
            # Without a local boundary, textual evidence is
            # useful but should not become a hard blocker.
            #
            if city_name in text:
                return True

            return True

        return (
            float(city.min_lat)
            <= latitude
            <= float(city.max_lat)
            and
            float(city.min_lon)
            <= longitude
            <= float(city.max_lon)
        )

    def _distance_km(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float,
    ) -> float:

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)

        delta_phi = math.radians(
            lat2 - lat1
        )

        delta_lambda = math.radians(
            lon2 - lon1
        )

        a = (
            math.sin(delta_phi / 2) ** 2
            +
            math.cos(phi1)
            * math.cos(phi2)
            * math.sin(delta_lambda / 2) ** 2
        )

        a = min(
            1.0,
            max(0.0, a),
        )

        return (
            EARTH_RADIUS_KM
            * 2
            * math.atan2(
                math.sqrt(a),
                math.sqrt(1.0 - a),
            )
        )

    # ========================================================
    # PARSING
    # ========================================================

    def _parse_candidate(
        self,
        *,
        raw: Dict[str, Any],
        city: Optional[CityContext],
        center: Optional[Tuple[float, float]],
        radius: float,
        source_query: str,
    ) -> Optional[Candidate]:

        name = self._normalize_text(
            raw.get("name") or ""
        )

        if not name:

            name = (
                self._extract_name_from_display(
                    raw.get("display_name")
                )
            )

        if not name:

            self.stats[
                "invalid_names"
            ] += 1

            self._reject(
                "<unknown>",
                "missing_name",
            )

            return None

        try:

            latitude = float(
                raw.get("lat")
            )

            longitude = float(
                raw.get("lon")
            )

        except (
            TypeError,
            ValueError,
        ):

            self.stats[
                "invalid_coordinates"
            ] += 1

            self._reject(
                name,
                "invalid_coordinates",
            )

            return None

        if not self._valid_coordinate(
            latitude,
            longitude,
        ):

            self.stats[
                "invalid_coordinates"
            ] += 1

            self._reject(
                name,
                "invalid_coordinates",
            )

            return None

        address_data = raw.get(
            "address"
        )

        if not isinstance(
            address_data,
            dict,
        ):
            address_data = {}

        address = self._extract_address(
            raw,
            address_data,
        )

        neighborhood = self._first_text(
            address_data,
            (
                "neighbourhood",
                "neighborhood",
                "suburb",
                "quarter",
            ),
        )

        street = self._first_text(
            address_data,
            (
                "road",
                "street",
            ),
        )

        searchable_text = (
            self._build_searchable_text(
                raw=raw,
                name=name,
                address=address,
                neighborhood=neighborhood,
                street=street,
                source_query=source_query,
            )
        )

        if city:

            if not self._validate_city(
                text=searchable_text,
                latitude=latitude,
                longitude=longitude,
                city=city,
            ):

                self.stats[
                    "city_filtered"
                ] += 1

                self._reject(
                    name,
                    "outside_city",
                )

                return None

            city_name = city.name

            province_name = (
                city.province
            )

        else:

            city_name = (
                self._extract_city_from_address(
                    address_data
                )
                or
                self._extract_city_from_text(
                    searchable_text
                )
            )

            province_name = (
                self._extract_province(
                    address_data
                )
            )

        osm_class = self._normalize_text(
            raw.get("class") or ""
        )

        osm_type_value = (
            self._normalize_text(
                raw.get("type") or ""
            )
        )

        osm_type = self._normalize_text(
            raw.get("osm_type") or ""
        )

        semantic = (
            self._classify_semantics(
                text=searchable_text,
                raw=raw,
            )
        )

        #
        # IMPORTANT:
        #
        # No semantic hard rejection here.
        #
        # A result with a valid name + coordinates remains
        # useful for discovery and Map View.
        #

        category = semantic[
            "category"
        ]

        phone = self._extract_phone(
            raw
        )

        website = self._extract_website(
            raw
        )

        source_id = (
            self._build_source_id(
                raw
            )
        )

        source_type = (
            self._build_source_type(
                raw
            )
        )

        distance_km = None

        if center is not None:

            distance_km = (
                self._distance_km(
                    center[0],
                    center[1],
                    latitude,
                    longitude,
                )
            )

            if (
                radius > 0
                and distance_km > radius
            ):

                self.stats[
                    "radius_filtered"
                ] += 1

                self._reject(
                    name,
                    "outside_radius",
                )

                return None

        score = (
            self._calculate_score(
                name=name,
                category=category,
                osm_class=osm_class,
                osm_type=osm_type_value,
                address=address,
                phone=phone,
                website=website,
                city=city_name,
                city_context=city,
                source_query=source_query,
                distance_km=distance_km,
                semantic=semantic,
            )
        )

        confidence = (
            self._calculate_confidence(
                score=score,
                semantic=semantic,
                name=name,
                category=category,
                address=address,
                phone=phone,
                website=website,
            )
        )

        verification = (
            self._calculate_verification(
                raw=raw,
                score=score,
                confidence=confidence,
            )
        )

        candidate = Candidate(
            name=name,
            latitude=latitude,
            longitude=longitude,
            city=city_name,
            province=province_name,
            phone=phone,
            website=website,
            address=address,
            neighborhood=neighborhood,
            street=street,
            source_id=source_id,
            source_type=source_type,
            category=category,
            osm_type=osm_type,
            osm_class=osm_class,
            osm_type_value=osm_type_value,
            score=score,
            confidence=confidence,
            distance_km=distance_km,
            semantic_type=semantic[
                "semantic_type"
            ],
            verification=verification,
            source_query=source_query,
            raw=raw,
        )

        self.stats[
            "candidates"
        ] += 1

        return candidate

    # ========================================================
    # SEARCHABLE TEXT
    # ========================================================

    def _build_searchable_text(
        self,
        *,
        raw: Dict[str, Any],
        name: str,
        address: str,
        neighborhood: str,
        street: str,
        source_query: str,
    ) -> str:

        values: List[str] = [
            name,
            address,
            neighborhood,
            street,
            source_query,
            str(
                raw.get("display_name")
                or ""
            ),
            str(
                raw.get("class")
                or ""
            ),
            str(
                raw.get("type")
                or ""
            ),
        ]

        namedetails = raw.get(
            "namedetails"
        )

        if isinstance(
            namedetails,
            dict,
        ):

            values.extend(
                str(value)
                for value in namedetails.values()
                if value
            )

        extratags = raw.get(
            "extratags"
        )

        if isinstance(
            extratags,
            dict,
        ):

            values.extend(
                str(value)
                for value in extratags.values()
                if value
            )

        return self._normalize_text(
            " ".join(values)
        )

    # ========================================================
    # SEMANTIC CLASSIFICATION
    # ========================================================

    def _classify_semantics(
        self,
        *,
        text: str,
        raw: Dict[str, Any],
    ) -> Dict[str, Any]:

        normalized = (
            self._normalize_text(text)
        )

        osm_class = (
            self._normalize_text(
                raw.get("class") or ""
            )
        )

        osm_type = (
            self._normalize_text(
                raw.get("type") or ""
            )
        )

        category = (
            self._resolve_category(
                osm_class=osm_class,
                osm_type=osm_type,
                text=normalized,
            )
        )

        confidence = 0.15

        if osm_class in BUSINESS_OSM_CLASSES:
            confidence += 0.35

        if osm_type in OSM_CATEGORY_MAP:
            confidence += 0.30

        if category != "unknown":
            confidence += 0.10

        if self._contains_any(
            normalized,
            BUSINESS_TERMS,
        ):
            confidence += 0.20

        confidence = min(
            1.0,
            confidence,
        )

        #
        # Discovery semantics:
        #
        # business:
        #     clearly business-like
        #
        # place:
        #     valid OSM place with insufficient business
        #     metadata
        #
        # unknown:
        #     very weak classification
        #

        if (
            osm_class in BUSINESS_OSM_CLASSES
            or category != "unknown"
            or self._contains_any(
                normalized,
                BUSINESS_TERMS,
            )
        ):

            semantic_type = "business"

        elif osm_class in NON_BUSINESS_CLASSES:

            semantic_type = "place"

        else:

            semantic_type = "place"

        return {
            "semantic_type": semantic_type,
            "category": category,
            "confidence": round(
                confidence,
                4,
            ),
            "hard_reject": False,
            "reason": "",
        }

    # ========================================================
    # CATEGORY RESOLUTION
    # ========================================================

    def _resolve_category(
        self,
        *,
        osm_class: str,
        osm_type: str,
        text: str,
    ) -> str:

        if osm_type in OSM_CATEGORY_MAP:

            return OSM_CATEGORY_MAP[
                osm_type
            ]

        if osm_class == "shop":
            return "retail"

        if osm_class == "office":
            return "office"

        if osm_class == "healthcare":
            return "healthcare"

        if osm_class == "tourism":
            return "hospitality"

        if osm_class == "craft":
            return "services"

        if osm_class == "industrial":
            return "industrial"

        if osm_class == "commercial":
            return "commercial"

        text_category = (
            self._resolve_text_category(
                text
            )
        )

        if text_category:
            return text_category

        return "unknown"

    def _resolve_text_category(
        self,
        text: str,
    ) -> str:

        category_terms = {

            "education": (
                "مدرسه",
                "دبستان",
                "دبیرستان",
                "هنرستان",
                "دانشگاه",
                "آموزشگاه",
                "کلاس",
            ),

            "restaurant": (
                "رستوران",
                "غذا",
                "چلوکباب",
            ),

            "cafe": (
                "کافه",
                "کافی شاپ",
                "کافی‌شاپ",
                "قهوه",
            ),

            "retail": (
                "فروشگاه",
                "مغازه",
                "فروش",
                "سوپرمارکت",
                "هایپرمارکت",
            ),

            "food": (
                "نانوایی",
                "قنادی",
                "شیرینی",
                "فست فود",
                "فست‌فود",
            ),

            "healthcare": (
                "کلینیک",
                "بیمارستان",
                "داروخانه",
                "پزشک",
                "دندانپزشکی",
                "آزمایشگاه",
            ),

            "finance": (
                "بانک",
                "بیمه",
                "صرافی",
            ),

            "automotive": (
                "تعمیرگاه",
                "مکانیکی",
                "قطعات خودرو",
                "نمایندگی خودرو",
            ),

            "real_estate": (
                "املاک",
                "مسکن",
            ),

            "hospitality": (
                "هتل",
                "مهمانپذیر",
                "مهمانخانه",
            ),

            "beauty": (
                "آرایشگاه",
                "زیبایی",
                "کاسمتیک",
            ),

            "company": (
                "شرکت",
                "کارخانه",
                "صنایع",
            ),

            "professional_services": (
                "وکیل",
                "حسابداری",
                "مشاوره",
                "معماری",
            ),
        }

        for category, terms in (
            category_terms.items()
        ):

            if self._contains_any(
                text,
                terms,
            ):
                return category

        return ""

    # ========================================================
    # SCORE
    # ========================================================

    def _calculate_score(
        self,
        *,
        name: str,
        category: str,
        osm_class: str,
        osm_type: str,
        address: str,
        phone: str,
        website: str,
        city: str,
        city_context: Optional[CityContext],
        source_query: str,
        distance_km: Optional[float],
        semantic: Dict[str, Any],
    ) -> float:

        score = 0.0

        if name:
            score += 20.0

        if category != "unknown":
            score += 20.0

        if osm_class:
            score += 10.0

        if osm_type:
            score += 10.0

        if address:
            score += 10.0

        if phone:
            score += 5.0

        if website:
            score += 5.0

        if city:
            score += 5.0

        semantic_confidence = (
            self._safe_float(
                semantic.get(
                    "confidence"
                )
            )
        )

        score += (
            semantic_confidence
            * 10.0
        )

        if self._query_matches_name(
            source_query,
            name,
        ):
            score += 5.0

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
            min(100.0, score),
            2,
        )

    # ========================================================
    # CONFIDENCE
    # ========================================================

    def _calculate_confidence(
        self,
        *,
        score: float,
        semantic: Dict[str, Any],
        name: str,
        category: str,
        address: str,
        phone: str,
        website: str,
    ) -> float:

        confidence = (
            score / 100.0
        )

        semantic_confidence = (
            self._safe_float(
                semantic.get(
                    "confidence"
                )
            )
        )

        confidence = (
            confidence * 0.70
            +
            semantic_confidence * 0.30
        )

        if not name:
            confidence -= 0.10

        if category == "unknown":
            confidence -= 0.05

        if not address:
            confidence -= 0.02

        return round(
            max(
                0.0,
                min(1.0, confidence),
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

        osm_id = raw.get(
            "osm_id"
        )

        return bool(
            osm_id
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

        #
        # Discovery mode:
        #
        # Only hard requirements are:
        #
        #     name
        #     valid coordinates
        #
        # Score/confidence are NOT used as hard gates.
        #

        if not candidate.name:
            return False

        if not self._valid_coordinate(
            candidate.latitude,
            candidate.longitude,
        ):
            return False

        return True

    # ========================================================
    # DEDUPLICATION
    # ========================================================

    def _deduplicate(
        self,
        candidates: Sequence[Candidate],
    ) -> List[Candidate]:

        result: List[Candidate] = []

        seen_source_ids = set()

        seen_geo_names = set()

        for candidate in candidates:

            source_key = (
                candidate.source_id
            )

            if (
                source_key
                and source_key
                in seen_source_ids
            ):

                self.stats[
                    "duplicates"
                ] += 1

                continue

            geo_key = (
                self._build_geo_name_key(
                    candidate
                )
            )

            if geo_key in seen_geo_names:

                self.stats[
                    "duplicates"
                ] += 1

                continue

            if source_key:
                seen_source_ids.add(
                    source_key
                )

            seen_geo_names.add(
                geo_key
            )

            result.append(
                candidate
            )

        return result

    def _build_geo_name_key(
        self,
        candidate: Candidate,
    ) -> str:

        normalized_name = (
            self._normalize_text(
                candidate.name
            )
        )

        lat = round(
            candidate.latitude,
            4,
        )

        lon = round(
            candidate.longitude,
            4,
        )

        return (
            f"{normalized_name}|"
            f"{lat}|"
            f"{lon}"
        )

    # ========================================================
    # FINALIZE / RANK
    # ========================================================

    def _finalize(
        self,
        candidates: Sequence[Candidate],
        *,
        city: Optional[CityContext],
        center: Optional[Tuple[float, float]],
        radius: float,
    ) -> List[Candidate]:

        unique = self._deduplicate(
            candidates
        )

        accepted: List[Candidate] = []

        for candidate in unique:

            if self._is_acceptable(
                candidate
            ):

                accepted.append(
                    candidate
                )

            else:

                self.stats[
                    "rejected"
                ] += 1

        accepted.sort(
            key=self._ranking_key,
            reverse=True,
        )

        return accepted

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

        if candidate.distance_km is not None:

            distance_score = (
                1.0
                /
                (
                    1.0
                    +
                    candidate.distance_km
                )
            )

        return (
            candidate.score,
            candidate.confidence,
            distance_score,
            1.0
            if candidate.verification
            else 0.0,
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

            "source_id": (
                candidate.source_id
            ),

            "source_type": (
                candidate.source_type
            ),

            "url": self._build_candidate_url(
                candidate
            ),

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

            "query": (
                candidate.source_query
            ),

            "neighborhood": (
                candidate.neighborhood
            ),

            "street": (
                candidate.street
            ),

            "api_distance": None,

            "osm_type": (
                candidate.osm_type
            ),

            "osm_class": (
                candidate.osm_class
            ),

            "osm_type_value": (
                candidate.osm_type_value
            ),
        }

    def _build_candidate_url(
        self,
        candidate: Candidate,
    ) -> str:

        if candidate.source_id:

            return self._build_source_url(
                candidate.raw
            )

        return ""

    # ========================================================
    # ADDRESS
    # ========================================================

    def _extract_address(
        self,
        raw: Dict[str, Any],
        address_data: Dict[str, Any],
    ) -> str:

        display_name = (
            self._normalize_text(
                raw.get(
                    "display_name"
                )
                or ""
            )
        )

        if display_name:
            return display_name

        preferred_keys = (
            "road",
            "street",
            "house_number",
            "neighbourhood",
            "neighborhood",
            "suburb",
            "quarter",
            "city",
            "town",
            "village",
            "county",
            "state",
            "province",
            "country",
        )

        parts: List[str] = []

        for key in preferred_keys:

            value = (
                self._normalize_text(
                    address_data.get(
                        key
                    )
                    or ""
                )
            )

            if (
                value
                and value not in parts
            ):

                parts.append(value)

        return ", ".join(parts)

    def _extract_city_from_address(
        self,
        address_data: Dict[str, Any],
    ) -> str:

        return self._first_text(
            address_data,
            (
                "city",
                "town",
                "municipality",
                "village",
                "city_district",
            ),
        )

    def _extract_city_from_text(
        self,
        text: str,
    ) -> str:

        for city_name in CITY_DATABASE:

            normalized_city = (
                self._normalize_text(
                    city_name
                )
            )

            if normalized_city in text:

                return city_name

        return ""

    def _extract_province(
        self,
        address_data: Dict[str, Any],
    ) -> str:

        return self._first_text(
            address_data,
            (
                "state",
                "province",
                "state_district",
            ),
        )

    # ========================================================
    # CONTACT
    # ========================================================

    def _extract_phone(
        self,
        raw: Dict[str, Any],
    ) -> str:

        candidates: List[Any] = []

        for key in (
            "phone",
            "contact:phone",
            "contact:mobile",
            "mobile",
            "telephone",
        ):

            if key in raw:
                candidates.append(
                    raw.get(key)
                )

        extratags = raw.get(
            "extratags"
        )

        if isinstance(
            extratags,
            dict,
        ):

            for key in (
                "phone",
                "contact:phone",
                "contact:mobile",
                "mobile",
                "telephone",
            ):

                if key in extratags:

                    candidates.append(
                        extratags.get(key)
                    )

        for value in candidates:

            normalized = (
                self._normalize_phone(
                    value
                )
            )

            if normalized:
                return normalized

        return ""

    def _normalize_phone(
        self,
        value: Any,
    ) -> str:

        if value is None:
            return ""

        text = str(value).strip()

        if not text:
            return ""

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text

    def _extract_website(
        self,
        raw: Dict[str, Any],
    ) -> str:

        candidates: List[Any] = []

        for key in (
            "website",
            "contact:website",
            "url",
        ):

            if key in raw:
                candidates.append(
                    raw.get(key)
                )

        extratags = raw.get(
            "extratags"
        )

        if isinstance(
            extratags,
            dict,
        ):

            for key in (
                "website",
                "contact:website",
                "url",
            ):

                if key in extratags:

                    candidates.append(
                        extratags.get(key)
                    )

        for value in candidates:

            normalized = (
                self._normalize_url(
                    value
                )
            )

            if normalized:
                return normalized

        return ""

    def _normalize_url(
        self,
        value: Any,
    ) -> str:

        if value is None:
            return ""

        text = str(value).strip()

        if not text:
            return ""

        if text.startswith(
            (
                "http://",
                "https://",
            )
        ):
            return text

        if re.match(
            r"^[\w.-]+\.[A-Za-z]{2,}",
            text,
        ):
            return (
                "https://"
                + text
            )

        return text

    # ========================================================
    # SOURCE
    # ========================================================

    def _build_source_id(
        self,
        raw: Dict[str, Any],
    ) -> str:

        osm_type = (
            self._normalize_text(
                raw.get("osm_type")
                or ""
            )
        )

        osm_id = raw.get(
            "osm_id"
        )

        if (
            osm_type
            and osm_id is not None
        ):

            return (
                f"{osm_type}/"
                f"{osm_id}"
            )

        place_id = raw.get(
            "place_id"
        )

        if place_id is not None:

            return str(place_id)

        return ""

    def _build_source_type(
        self,
        raw: Dict[str, Any],
    ) -> str:

        osm_type = (
            self._normalize_text(
                raw.get("osm_type")
                or ""
            )
        )

        osm_class = (
            self._normalize_text(
                raw.get("class")
                or ""
            )
        )

        osm_value = (
            self._normalize_text(
                raw.get("type")
                or ""
            )
        )

        parts = [
            value
            for value in (
                osm_type,
                osm_class,
                osm_value,
            )
            if value
        ]

        return ":".join(parts)

    def _build_source_url(
        self,
        raw: Dict[str, Any],
    ) -> str:

        osm_type = (
            self._normalize_text(
                raw.get("osm_type")
                or ""
            )
        )

        osm_id = raw.get(
            "osm_id"
        )

        if (
            not osm_type
            or osm_id is None
        ):
            return ""

        return (
            f"{BASE_URL}/"
            f"{osm_type}/"
            f"{osm_id}"
        )

    # ========================================================
    # NAME
    # ========================================================

    def _extract_name_from_display(
        self,
        display_name: Any,
    ) -> str:

        if not display_name:
            return ""

        text = self._normalize_text(
            display_name
        )

        if not text:
            return ""

        return text.split(
            ",",
            1,
        )[0].strip()

    # ========================================================
    # GENERIC HELPERS
    # ========================================================

    def _first_text(
        self,
        data: Dict[str, Any],
        keys: Sequence[str],
    ) -> str:

        for key in keys:

            value = (
                self._normalize_text(
                    data.get(key)
                    or ""
                )
            )

            if value:
                return value

        return ""

    def _contains_any(
        self,
        text: str,
        terms: Sequence[str],
    ) -> bool:

        normalized = (
            self._normalize_text(text)
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

    def _query_matches_name(
        self,
        query: str,
        name: str,
    ) -> bool:

        query_norm = (
            self._normalize_text(
                query
            )
        )

        name_norm = (
            self._normalize_text(
                name
            )
        )

        if not query_norm or not name_norm:
            return False

        query_tokens = {
            token
            for token in query_norm.split()
            if len(token) >= 2
        }

        name_tokens = {
            token
            for token in name_norm.split()
            if len(token) >= 2
        }

        if not query_tokens or not name_tokens:
            return False

        return bool(
            query_tokens
            & name_tokens
        )

    def _valid_coordinate(
        self,
        latitude: Any,
        longitude: Any,
    ) -> bool:

        try:

            lat = float(latitude)
            lon = float(longitude)

        except (
            TypeError,
            ValueError,
        ):
            return False

        if not (
            math.isfinite(lat)
            and math.isfinite(lon)
        ):
            return False

        return (
            -90.0
            <= lat
            <= 90.0
            and
            -180.0
            <= lon
            <= 180.0
        )

    def _normalize_text(
        self,
        value: Any,
    ) -> str:

        if value is None:
            return ""

        text = str(value).strip()

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
            "‌": " ",
            "\u200c": " ",
        }

        for old, new in replacements.items():

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

    def _safe_float(
        self,
        value: Any,
    ) -> float:

        try:

            result = float(value)

            if math.isfinite(result):
                return result

        except (
            TypeError,
            ValueError,
        ):
            pass

        return 0.0

    def _unique_strings(
        self,
        values: Sequence[str],
    ) -> List[str]:

        result: List[str] = []

        seen = set()

        for value in values:

            normalized = (
                self._normalize_text(
                    value
                )
            )

            if not normalized:
                continue

            key = normalized.casefold()

            if key in seen:
                continue

            seen.add(key)

            result.append(
                normalized
            )

        return result

    # ========================================================
    # LOGGING
    # ========================================================

    def _log(
        self,
        message: str,
    ) -> None:

        if not self.debug:
            return

        print(message)

    def _reject(
        self,
        name: str,
        reason: str,
    ) -> None:

        self.stats["rejected"] += 1

        self._log(
            f"[OSM][REJECT] "
            f"{name} -> {reason}"
        )


# ============================================================
# END OF FILE
# ============================================================