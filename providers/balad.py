# ==========================================================
# EYES MASTER — BALAD SEARCH PROVIDER
# ==========================================================
#
# FILE:
#     providers/balad.py
#
# STATUS:
#     CANONICAL / CORE
#
# ROLE:
#     Exhaustive Balad SearchProvider.
#
# CORE RULE:
#
#     Query -> Balad API -> Pagination -> Extraction
#          -> City Filtering -> Deduplication
#          -> Maximum Available Results
#
# IMPORTANT:
#
#     This provider is still DOMAIN AGNOSTIC.
#
#     It does NOT classify:
#         - school
#         - company
#         - restaurant
#         - hospital
#         - etc.
#
#     Its job is to retrieve the maximum amount of
#     geographically relevant Balad data.
#
# ==========================================================

from __future__ import annotations

import hashlib
import math
import re
import time
import uuid

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests

from .base import SearchProvider


# ==========================================================
# CONSTANTS
# ==========================================================

PROVIDER_NAME = "balad"

PROVIDER_VERSION = "14.0.0"

BASE_URL = "https://balad.ir"

SEARCH_ENDPOINT = (
    "https://search.raah.ir/v6/"
)

POI_WEB = (
    "https://poi.raah.ir/web/v4"
)

DEFAULT_TIMEOUT = 20.0

DEFAULT_DELAY = 0.20

# ----------------------------------------------------------
# IMPORTANT
#
# There is intentionally NO small result limit here.
#
# None means:
#     collect everything available from pagination.
# ----------------------------------------------------------

DEFAULT_MAX_RESULTS: Optional[int] = None

# Safety limit for pathological API behaviour.
#
# This is NOT a result limit.
#
# 1000 pages * 500 records would theoretically allow
# hundreds of thousands of records.
DEFAULT_MAX_PAGES = 1000

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 "
    "(X11; Linux x86_64) "
    "AppleWebKit/537.36 "
    "(KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36"
)


# ==========================================================
# DATACLASS
# ==========================================================


@dataclass
class SearchCandidate:
    """
    Internal normalized representation of one Balad result.
    """

    name: str = ""

    title: str = ""

    city: str = ""

    province: str = ""

    address: str = ""

    neighborhood: str = ""

    street: str = ""

    phone: str = ""

    website: str = ""

    url: str = ""

    source_id: str = ""

    source_type: str = ""

    latitude: Optional[float] = None

    longitude: Optional[float] = None

    distance_km: Optional[float] = None

    score: Optional[float] = None

    snippet: str = ""

    query: str = ""

    raw: Optional[Dict[str, Any]] = None


# ==========================================================
# PROVIDER
# ==========================================================


class BaladProvider(SearchProvider):
    """
    Exhaustive Balad SearchProvider.

    Main responsibilities
    ---------------------

    1. Query Balad.
    2. Walk through available pages.
    3. Extract direct POIs.
    4. Extract bundle POIs.
    5. Normalize fields.
    6. Enforce requested-city filtering.
    7. Deduplicate.
    8. Return maximum available results.

    This provider does NOT perform semantic classification.
    """

    name = PROVIDER_NAME

    version = PROVIDER_VERSION

    # ======================================================
    # INIT
    # ======================================================

    def __init__(
        self,
        timeout: int | float = DEFAULT_TIMEOUT,
        delay: int | float = DEFAULT_DELAY,
        max_results: Optional[int] = DEFAULT_MAX_RESULTS,
        max_pages: int = DEFAULT_MAX_PAGES,
        session: Optional[requests.Session] = None,
        debug: bool = True,
        **kwargs: Any,
    ) -> None:

        super().__init__(
            timeout=max(
                1,
                int(float(timeout)),
            )
        )

        self.timeout = max(
            1.0,
            float(timeout),
        )

        self.delay = max(
            0.0,
            float(delay),
        )

        # None / 0 means unlimited.
        if max_results is None:
            self.max_results = None
        else:
            try:
                parsed_limit = int(max_results)

                self.max_results = (
                    None
                    if parsed_limit <= 0
                    else parsed_limit
                )

            except (
                TypeError,
                ValueError,
            ):
                self.max_results = None

        try:
            self.max_pages = max(
                1,
                int(max_pages),
            )
        except (
            TypeError,
            ValueError,
        ):
            self.max_pages = DEFAULT_MAX_PAGES

        self.debug = bool(
            debug
        )

        self.session = (
            session
            if session is not None
            else requests.Session()
        )

        self.search_session = str(
            uuid.uuid4()
        )

        self._last_request = 0.0

        self.stats: Dict[str, int] = {
            "requests": 0,
            "pages": 0,
            "raw_results": 0,
            "results": 0,
            "poi_results": 0,
            "bundle_results": 0,
            "features": 0,
            "normalized": 0,
            "duplicates": 0,
            "city_rejected": 0,
            "empty_pages": 0,
            "repeated_pages": 0,
            "errors": 0,
        }

    # ======================================================
    # INFO
    # ======================================================

    def info(
        self,
    ) -> Dict[str, Any]:

        base = super().info()

        base.update(
            {
                "type": "search",
                "base_url": BASE_URL,
                "endpoint": SEARCH_ENDPOINT,
                "method": "GET",
                "format": "json",
                "delay": self.delay,
                "max_results": self.max_results,
                "max_pages": self.max_pages,
                "exhaustive": True,
                "search_session": self.search_session,
            }
        )

        return base

    # ======================================================
    # HEALTH
    # ======================================================

    def health_check(
        self,
    ) -> bool:

        try:

            data = self._request(
                "مدرسه",
                page=1,
            )

            return isinstance(
                data,
                dict,
            )

        except Exception as exc:

            self._log(
                f"[BALAD HEALTH ERROR] {exc}"
            )

            return False

    # ======================================================
    # SEARCH
    # ======================================================

    def search(
        self,
        query: str,
        page: int = 1,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        """
        Exhaustive Balad search.

        IMPORTANT:

        Unlike the old implementation, this method does NOT
        stop at the first page.

        It walks through Balad pagination until:

            - no results remain
            - Balad returns a repeated page
            - no new unique results are found
            - API explicitly reports the last page
            - max_pages safety boundary is reached
            - requested max_results has been reached

        Examples
        --------

        search("رشت")

        search("مدرسه رشت")

        search(
            "مدرسه",
            city="رشت",
        )

        search(
            "مدرسه",
            city="رشت",
            max_results=None,
        )
        """

        clean_query = self._normalize_text(
            query
        )

        if not clean_query:
            return []

        start_page = max(
            1,
            self._safe_int(
                page,
                1,
            ),
        )

        # --------------------------------------------------
        # RESULT LIMIT
        # --------------------------------------------------

        requested_limit = kwargs.pop(
            "max_results",
            self.max_results,
        )

        if requested_limit is None:
            requested_limit = None
        else:

            try:

                requested_limit = int(
                    requested_limit
                )

                if requested_limit <= 0:
                    requested_limit = None

            except (
                TypeError,
                ValueError,
            ):

                requested_limit = None

        # --------------------------------------------------
        # MAX PAGES
        # --------------------------------------------------

        max_pages = kwargs.pop(
            "max_pages",
            self.max_pages,
        )

        try:

            max_pages = max(
                1,
                int(max_pages),
            )

        except (
            TypeError,
            ValueError,
        ):

            max_pages = self.max_pages

        # --------------------------------------------------
        # CITY
        # --------------------------------------------------

        requested_city = self._first_text(
            kwargs.pop(
                "city",
                None,
            ),
            kwargs.pop(
                "location",
                None,
            ),
        )

        if not requested_city:

            requested_city = (
                self._infer_city_from_query(
                    clean_query
                )
            )

        requested_city = (
            self._normalize_city(
                requested_city
            )
        )

        self._log(
            "=" * 70
        )

        self._log(
            "[BALAD] EXHAUSTIVE SEARCH"
        )

        self._log(
            f"[BALAD] QUERY={clean_query!r}"
        )

        self._log(
            f"[BALAD] CITY="
            f"{requested_city or 'AUTO/NONE'}"
        )

        self._log(
            f"[BALAD] MAX_RESULTS="
            f"{requested_limit or 'UNLIMITED'}"
        )

        self._log(
            f"[BALAD] MAX_PAGES="
            f"{max_pages}"
        )

        # --------------------------------------------------
        # COLLECTION
        # --------------------------------------------------

        candidates: List[
            SearchCandidate
        ] = []

        seen_page_hashes: set[str] = set()

        # Used to detect a page that technically contains
        # records but contributes nothing new.
        previous_total_unique = 0

        current_page = start_page

        pages_without_growth = 0

        # --------------------------------------------------
        # PAGINATION LOOP
        # --------------------------------------------------

        while current_page <= max_pages:

            self._log(
                f"[BALAD] PAGE={current_page}"
            )

            try:

                data = self._request(
                    clean_query,
                    page=current_page,
                    **kwargs,
                )

            except Exception as exc:

                self.stats["errors"] += 1

                self._log(
                    f"[BALAD ERROR] "
                    f"page={current_page} "
                    f"{exc}"
                )

                # Do not silently destroy already collected
                # data because one later page failed.
                break

            self.stats["pages"] += 1

            # --------------------------------------------------
            # RAW ITEMS
            # --------------------------------------------------

            raw_items = (
                self._extract_raw_items(
                    data
                )
            )

            self.stats["raw_results"] += len(
                raw_items
            )

            self._log(
                f"[BALAD] PAGE={current_page} "
                f"RAW={len(raw_items)}"
            )

            # --------------------------------------------------
            # EMPTY PAGE
            # --------------------------------------------------

            if not raw_items:

                self.stats[
                    "empty_pages"
                ] += 1

                self._log(
                    f"[BALAD] PAGE={current_page} "
                    f"EMPTY -> END"
                )

                break

            # --------------------------------------------------
            # PAGE FINGERPRINT
            # --------------------------------------------------

            page_hash = (
                self._page_fingerprint(
                    raw_items
                )
            )

            if page_hash in seen_page_hashes:

                self.stats[
                    "repeated_pages"
                ] += 1

                self._log(
                    f"[BALAD] PAGE={current_page} "
                    f"REPEATED -> END"
                )

                break

            seen_page_hashes.add(
                page_hash
            )

            # --------------------------------------------------
            # PARSE
            # --------------------------------------------------

            page_candidates: List[
                SearchCandidate
            ] = []

            for raw in raw_items:

                candidate = (
                    self._parse_candidate(
                        raw,
                        query=clean_query,
                    )
                )

                if candidate is None:
                    continue

                # ----------------------------------------------
                # CITY FILTER
                # ----------------------------------------------

                if requested_city:

                    if not self._candidate_matches_city(
                        candidate,
                        requested_city,
                    ):

                        self.stats[
                            "city_rejected"
                        ] += 1

                        continue

                page_candidates.append(
                    candidate
                )

            self.stats["normalized"] += len(
                page_candidates
            )

            # --------------------------------------------------
            # APPEND
            # --------------------------------------------------

            candidates.extend(
                page_candidates
            )

            # --------------------------------------------------
            # EARLY LIMIT
            # --------------------------------------------------

            if (
                requested_limit is not None
                and len(candidates)
                >= requested_limit
            ):
                self._log(
                    "[BALAD] RESULT LIMIT "
                    "REACHED"
                )

                break

            # --------------------------------------------------
            # GROWTH DETECTION
            #
            # We cannot stop simply because a page had fewer
            # records. Balad can return different page sizes.
            # --------------------------------------------------

            unique_estimate = (
                self._quick_unique_count(
                    candidates
                )
            )

            if (
                unique_estimate
                <= previous_total_unique
            ):

                pages_without_growth += 1

            else:

                pages_without_growth = 0

            previous_total_unique = (
                unique_estimate
            )

            # If Balad keeps returning pages which add
            # absolutely nothing, pagination is effectively
            # exhausted.
            if pages_without_growth >= 2:

                self._log(
                    "[BALAD] NO NEW UNIQUE "
                    "DATA -> END"
                )

                break

            # --------------------------------------------------
            # EXPLICIT PAGINATION METADATA
            # --------------------------------------------------

            if self._is_last_page(
                data,
                current_page,
            ):

                self._log(
                    f"[BALAD] PAGE={current_page} "
                    f"MARKED LAST -> END"
                )

                break

            current_page += 1

        # --------------------------------------------------
        # FINAL DEDUPLICATION
        # --------------------------------------------------

        self._log(
            f"[BALAD] COLLECTED BEFORE DEDUP="
            f"{len(candidates)}"
        )

        candidates = self._deduplicate(
            candidates
        )

        # --------------------------------------------------
        # RANK
        # --------------------------------------------------

        candidates.sort(
            key=self._ranking_key,
            reverse=True,
        )

        # --------------------------------------------------
        # FINAL LIMIT
        # --------------------------------------------------

        if requested_limit is not None:

            candidates = candidates[
                :requested_limit
            ]

        self.stats["results"] = len(
            candidates
        )

        self._log(
            f"[BALAD] FINAL="
            f"{len(candidates)}"
        )

        self._log(
            f"[BALAD] STATS="
            f"{self.stats}"
        )

        self._log(
            "=" * 70
        )

        return [
            self._candidate_to_dict(
                candidate
            )
            for candidate in candidates
        ]

    # ======================================================
    # REQUEST
    # ======================================================

    def _request(
        self,
        query: str,
        *,
        page: int = 1,
        **kwargs: Any,
    ) -> Dict[str, Any]:

        self._respect_delay()

        params: Dict[str, Any] = {
            "text": query,
        }

        # --------------------------------------------------
        # PAGINATION
        # --------------------------------------------------

        if page > 1:

            params["page"] = page

        # --------------------------------------------------
        # EXTRA PARAMETERS
        # --------------------------------------------------

        for key, value in kwargs.items():

            if value is None:
                continue

            if key in {
                "text",
                "query",
                "page",
            }:
                continue

            params[key] = value

        headers = {
            "Accept": "application/json",
            "User-Agent": DEFAULT_USER_AGENT,
            "search-session": self.search_session,
        }

        self._log(
            f"[BALAD REQUEST] "
            f"page={page} "
            f"url={SEARCH_ENDPOINT}"
        )

        response = self.session.get(
            SEARCH_ENDPOINT,
            params=params,
            headers=headers,
            timeout=self.timeout,
        )

        self.stats["requests"] += 1

        response.raise_for_status()

        data = response.json()

        if not isinstance(
            data,
            dict,
        ):

            raise ValueError(
                "Balad response is not a JSON object."
            )

        return data

    # ======================================================
    # DELAY
    # ======================================================

    def _respect_delay(
        self,
    ) -> None:

        if self.delay <= 0:

            self._last_request = (
                time.monotonic()
            )

            return

        now = time.monotonic()

        elapsed = (
            now - self._last_request
        )

        remaining = (
            self.delay - elapsed
        )

        if remaining <= 0:

            self._last_request = (
                time.monotonic()
            )

            return

        while remaining > 0:

            time.sleep(
                min(
                    remaining,
                    0.10,
                )
            )

            remaining = (
                self.delay
                - (
                    time.monotonic()
                    - self._last_request
                )
            )

        self._last_request = (
            time.monotonic()
        )

    # ======================================================
    # RAW RESPONSE EXTRACTION
    # ======================================================

    def _extract_raw_items(
        self,
        data: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        results = data.get(
            "results"
        )

        if not isinstance(
            results,
            list,
        ):
            return []

        output: List[
            Dict[str, Any]
        ] = []

        for item in results:

            if not isinstance(
                item,
                dict,
            ):
                continue

            item_type = (
                self._normalize_text(
                    item.get("type")
                ).casefold()
            )

            if item_type == "poi":

                self.stats[
                    "poi_results"
                ] += 1

                output.append(
                    item
                )

                continue

            if item_type == "bundle-poi":

                self.stats[
                    "bundle_results"
                ] += 1

                output.extend(
                    self._extract_bundle_features(
                        item
                    )
                )

        return output

    # ======================================================
    # BUNDLE EXTRACTION
    # ======================================================

    def _extract_bundle_features(
        self,
        bundle: Dict[str, Any],
    ) -> List[Dict[str, Any]]:

        geojson = bundle.get(
            "geojson"
        )

        if not isinstance(
            geojson,
            dict,
        ):
            return []

        features = geojson.get(
            "features"
        )

        if not isinstance(
            features,
            list,
        ):
            return []

        output: List[
            Dict[str, Any]
        ] = []

        for feature in features:

            if not isinstance(
                feature,
                dict,
            ):
                continue

            geometry = feature.get(
                "geometry"
            )

            properties = feature.get(
                "properties"
            )

            if not isinstance(
                geometry,
                dict,
            ):
                continue

            if not isinstance(
                properties,
                dict,
            ):
                properties = {}

            coordinates = (
                geometry.get(
                    "coordinates"
                )
            )

            point = self._extract_point(
                coordinates
            )

            if point is None:
                continue

            lon, lat = point

            if not self._valid_coordinate(
                lat,
                lon,
            ):
                continue

            name = self._first_text(
                properties.get("name"),
                properties.get("title"),
                properties.get("maintext"),
            )

            synthetic = {
                "type": "poi",

                "view_type": "poi",

                "maintext": name,

                "formatted_maintext": name,

                "subtext1": self._first_text(
                    properties.get("address"),
                    properties.get("subtext1"),
                    properties.get("formatted_address"),
                ),

                "subtext2": self._first_text(
                    properties.get("subtext2"),
                    properties.get("description"),
                ),

                "id": self._first_text(
                    properties.get("id"),
                    properties.get("poi_id"),
                ),

                "center_point": [
                    lon,
                    lat,
                ],

                "geometry": {
                    "type": "Point",
                    "coordinates": [
                        lon,
                        lat,
                    ],
                },

                "score": self._safe_float(
                    (
                        bundle.get(
                            "bundle_paging_meta",
                            {},
                        )
                        or {}
                    ).get(
                        "score",
                        0,
                    ),
                    0.0,
                ),

                "phone": self._first_text(
                    properties.get("phone"),
                    properties.get("telephone"),
                    properties.get("tel"),
                ),

                "website": self._first_text(
                    properties.get("website"),
                    properties.get("web"),
                    properties.get("site"),
                ),

                "city": self._first_text(
                    properties.get("city"),
                    properties.get("city_name"),
                ),

                "province": self._first_text(
                    properties.get("province"),
                    properties.get("province_name"),
                ),

                "neighborhood": self._first_text(
                    properties.get("neighborhood"),
                    properties.get("neighborhood_name"),
                ),

                "street": self._first_text(
                    properties.get("street"),
                    properties.get("street_name"),
                ),

                "source_bundle": True,

                "bundle_id": bundle.get(
                    "bundle_id"
                ),

                "bundle_slug": bundle.get(
                    "bundle_slug"
                ),

                "_bundle_parent": bundle,
            }

            output.append(
                synthetic
            )

            self.stats[
                "features"
            ] += 1

        return output

    # ======================================================
    # CANDIDATE PARSER
    # ======================================================

    def _parse_candidate(
        self,
        raw: Dict[str, Any],
        *,
        query: str,
    ) -> Optional[SearchCandidate]:

        if not isinstance(
            raw,
            dict,
        ):
            return None

        name = self._first_text(
            raw.get("maintext"),
            raw.get("formatted_maintext"),
            raw.get("name"),
            raw.get("title"),
        )

        if not name:
            return None

        address = self._first_text(
            raw.get("subtext1"),
            raw.get("address"),
            raw.get("formatted_address"),
        )

        neighborhood = self._first_text(
            raw.get("neighborhood_name"),
            raw.get("neighborhood"),
        )

        street = self._first_text(
            raw.get("street_name"),
            raw.get("street"),
        )

        phone = self._extract_phone(
            raw
        )

        website = self._extract_website(
            raw
        )

        source_id = self._first_text(
            raw.get("id"),
            raw.get("poi_id"),
        )

        point = (
            self._extract_candidate_point(
                raw
            )
        )

        latitude: Optional[float] = None

        longitude: Optional[float] = None

        if point is not None:

            longitude, latitude = point

            if not self._valid_coordinate(
                latitude,
                longitude,
            ):

                latitude = None
                longitude = None

        city = self._first_text(
            raw.get("city"),
            raw.get("city_name"),
        )

        province = self._first_text(
            raw.get("province"),
            raw.get("province_name"),
        )

        if not city or not province:

            city_value, province_value = (
                self._extract_location_fields(
                    raw
                )
            )

            if not city:
                city = city_value

            if not province:
                province = province_value

        url = self._build_poi_url(
            source_id
        )

        distance = self._parse_distance(
            raw.get("distance")
        )

        score = self._safe_optional_float(
            raw.get("score")
        )

        snippet = self._first_text(
            raw.get("snippet"),
            raw.get("description"),
            raw.get("subtext2"),
        )

        return SearchCandidate(
            name=name,
            title=name,
            city=city,
            province=province,
            address=address,
            neighborhood=neighborhood,
            street=street,
            phone=phone,
            website=website,
            url=url,
            source_id=source_id,
            source_type=(
                "bundle-poi"
                if raw.get(
                    "source_bundle"
                )
                else "poi"
            ),
            latitude=latitude,
            longitude=longitude,
            distance_km=distance,
            score=score,
            snippet=snippet,
            query=query,
            raw=raw,
        )

    # ======================================================
    # CITY INFERENCE
    # ======================================================

    def _infer_city_from_query(
        self,
        query: str,
    ) -> str:
        """
        Best-effort city extraction.

        Examples:

            رشت
            مدرسه رشت
            مدرسه در رشت
            مدارس شهر رشت

        The explicit city= argument remains preferred.
        """

        text = self._normalize_text(
            query
        )

        if not text:
            return ""

        # --------------------------------------------------
        # Explicit forms
        # --------------------------------------------------

        patterns = (
            r"(?:در|شهر|شهرستان)\s+([آ-یA-Za-z]+)",
            r"(?:city|town)\s+([A-Za-z]+)",
        )

        for pattern in patterns:

            match = re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            if match:

                value = self._normalize_city(
                    match.group(1)
                )

                if value:
                    return value

        # --------------------------------------------------
        # Known Iranian city names.
        #
        # This prevents words such as:
        #
        #     مدرسه
        #     بیمارستان
        #     شرکت
        #
        # from accidentally becoming a city.
        # --------------------------------------------------

        words = [
            part
            for part in re.split(
                r"\s+",
                text,
            )
            if part
        ]

        known = self._known_city_names()

        for word in reversed(words):

            normalized = (
                self._normalize_city(
                    word
                )
            )

            if normalized in known:

                return normalized

        # --------------------------------------------------
        # Single-token query
        # --------------------------------------------------

        if len(words) == 1:

            return self._normalize_city(
                words[0]
            )

        return ""

    # ======================================================
    # CITY NORMALIZATION
    # ======================================================

    def _normalize_city(
        self,
        value: Any,
    ) -> str:

        text = self._normalize_text(
            value
        ).casefold()

        text = re.sub(
            r"\b(شهر|city|town)\b",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        return text

    # ======================================================
    # KNOWN CITIES
    # ======================================================

    @staticmethod
    def _known_city_names() -> set[str]:
        """
        Common Iranian city names.

        This list is used only for query-location inference.
        It does NOT restrict Balad results to these cities.
        """

        return {
            "تهران",
            "رشت",
            "انزلی",
            "لاهیجان",
            "رودسر",
            "آستانه",
            "قزوین",
            "زنجان",
            "تبریز",
            "ارومیه",
            "اردبیل",
            "خوی",
            "مراغه",
            "میانه",
            "اصفهان",
            "شیراز",
            "یزد",
            "کرمان",
            "اهواز",
            "دزفول",
            "آبادان",
            "خرمشهر",
            "بندرعباس",
            "بوشهر",
            "سنندج",
            "کرمانشاه",
            "همدان",
            "ملایر",
            "اراک",
            "قم",
            "ساری",
            "بابل",
            "آمل",
            "نوشهر",
            "گرگان",
            "مشهد",
            "نیشابور",
            "سبزوار",
            "بجنورد",
            "بیرجند",
            "زاهدان",
            "کرج",
            "شهریار",
            "اسلامشهر",
            "پاکدشت",
            "ورامین",
            "کاشان",
            "خمینی‌شهر",
            "نجف‌آباد",
            "شاهین‌شهر",
            "شهرکرد",
            "یاسوج",
            "خرم‌آباد",
            "بروجرد",
            "ایلام",
            "سمنان",
            "شاهرود",
            "دامغان",
            "گرمسار",
            "بیرجند",
            "رفسنجان",
            "سیرجان",
            "جیرفت",
            "بم",
            "مرودشت",
            "جهرم",
            "لار",
            "فسا",
            "کازرون",
            "بندرلنگه",
            "میناب",
            "چابهار",
            "ایرانشهر",
            "گنبدکاووس",
            "تربت‌حیدریه",
            "تربت جام",
            "قائمشهر",
            "بابلسر",
            "فومن",
            "صومعه‌سرا",
            "تالش",
            "آستارا",
        }

    # ======================================================
    # CITY MATCHING
    # ======================================================

    def _candidate_matches_city(
        self,
        candidate: SearchCandidate,
        requested_city: str,
    ) -> bool:
        """
        Strict geographic relevance check.

        Priority:

            1. explicit candidate.city
            2. province/location metadata
            3. address
            4. neighborhood/street/snippet
            5. raw nested location fields

        We intentionally reject an explicit different city.

        Example:

            requested = رشت

            candidate.city = تهران

        => reject
        """

        target = self._normalize_city(
            requested_city
        )

        if not target:
            return True

        candidate_city = self._normalize_city(
            candidate.city
        )

        # --------------------------------------------------
        # Direct city field
        # --------------------------------------------------

        if candidate_city:

            return (
                candidate_city == target
                or target in candidate_city
                or candidate_city in target
            )

        # --------------------------------------------------
        # Build searchable location text.
        # --------------------------------------------------

        location_parts = [
            candidate.address,
            candidate.neighborhood,
            candidate.street,
            candidate.snippet,
            candidate.province,
        ]

        raw = candidate.raw or {}

        for key in (
            "city",
            "city_name",
            "address",
            "formatted_address",
            "subtext1",
            "subtext2",
        ):

            value = raw.get(
                key
            )

            if value:

                location_parts.append(
                    str(value)
                )

        location_text = self._normalize_text(
            " ".join(
                location_parts
            )
        ).casefold()

        if not location_text:
            return False

        # --------------------------------------------------
        # Explicit different Iranian city detection.
        # --------------------------------------------------

        known_cities = (
            self._known_city_names()
        )

        detected_other_cities = []

        for city in known_cities:

            if city == target:
                continue

            if city in location_text:

                detected_other_cities.append(
                    city
                )

        if target in location_text:

            return True

        # If the location clearly names another city,
        # reject it.
        if detected_other_cities:

            return False

        # --------------------------------------------------
        # Unknown city information.
        #
        # We prefer false-negative over contaminating a
        # city-specific scrape with another city.
        # --------------------------------------------------

        return False

    # ======================================================
    # LOCATION FIELDS
    # ======================================================

    def _extract_location_fields(
        self,
        raw: Dict[str, Any],
    ) -> Tuple[str, str]:

        city = ""

        province = ""

        location = raw.get(
            "location"
        )

        if isinstance(
            location,
            dict,
        ):

            city = self._first_text(
                location.get("city"),
                location.get("city_name"),
            )

            province = self._first_text(
                location.get("province"),
                location.get("province_name"),
            )

        address_components = raw.get(
            "address_components"
        )

        if isinstance(
            address_components,
            list,
        ):

            for component in (
                address_components
            ):

                if not isinstance(
                    component,
                    dict,
                ):
                    continue

                component_type = (
                    self._normalize_text(
                        component.get(
                            "type"
                        )
                    ).casefold()
                )

                value = self._first_text(
                    component.get("name"),
                    component.get("title"),
                    component.get("text"),
                )

                if not value:
                    continue

                if component_type in {
                    "city",
                    "municipality",
                }:

                    city = city or value

                elif component_type in {
                    "province",
                    "state",
                }:

                    province = (
                        province
                        or value
                    )

        return (
            city,
            province,
        )

    # ======================================================
    # COORDINATES
    # ======================================================

    def _extract_candidate_point(
        self,
        raw: Dict[str, Any],
    ) -> Optional[
        Tuple[float, float]
    ]:

        center = raw.get(
            "center_point"
        )

        point = self._extract_point(
            center
        )

        if point is not None:
            return point

        geometry = raw.get(
            "geometry"
        )

        if isinstance(
            geometry,
            dict,
        ):

            point = (
                self._extract_point(
                    geometry.get(
                        "coordinates"
                    )
                )
            )

            if point is not None:
                return point

        location = raw.get(
            "location"
        )

        if isinstance(
            location,
            dict,
        ):

            point = (
                self._extract_point(
                    location.get(
                        "coordinates"
                    )
                )
            )

            if point is not None:
                return point

        return None

    def _extract_point(
        self,
        coordinates: Any,
    ) -> Optional[
        Tuple[float, float]
    ]:

        if not isinstance(
            coordinates,
            (list, tuple),
        ):
            return None

        if len(coordinates) < 2:
            return None

        first = coordinates[0]

        second = coordinates[1]

        if isinstance(
            first,
            (list, tuple),
        ):

            return self._extract_point(
                first
            )

        try:

            lon = float(
                first
            )

            lat = float(
                second
            )

        except (
            TypeError,
            ValueError,
        ):

            return None

        return (
            lon,
            lat,
        )

    @staticmethod
    def _valid_coordinate(
        lat: float,
        lon: float,
    ) -> bool:

        if not (
            math.isfinite(lat)
            and math.isfinite(lon)
        ):
            return False

        if lat == 0 and lon == 0:
            return False

        if not (
            -90 <= lat <= 90
        ):
            return False

        if not (
            -180 <= lon <= 180
        ):
            return False

        return True

    # ======================================================
    # PHONE
    # ======================================================

    def _extract_phone(
        self,
        raw: Dict[str, Any],
    ) -> str:

        direct = self._first_text(
            raw.get("phone"),
            raw.get("telephone"),
            raw.get("tel"),
        )

        if direct:

            return self._normalize_phone(
                direct
            )

        extra_info = raw.get(
            "extra_info"
        )

        if isinstance(
            extra_info,
            list,
        ):

            for item in extra_info:

                if not isinstance(
                    item,
                    dict,
                ):
                    continue

                value = self._first_text(
                    item.get("phone"),
                    item.get("telephone"),
                    item.get("tel"),
                )

                if value:

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
        value: str,
    ) -> str:

        value = self._normalize_text(
            value
        )

        value = value.replace(
            " ",
            "",
        )

        value = value.replace(
            "-",
            "",
        )

        value = value.replace(
            "(",
            "",
        )

        value = value.replace(
            ")",
            "",
        )

        if value.startswith(
            "+98"
        ):

            value = (
                "0"
                + value[3:]
            )

        elif (
            value.startswith("98")
            and len(value) >= 10
        ):

            value = (
                "0"
                + value[2:]
            )

        value = re.sub(
            r"[^0-9+]",
            "",
            value,
        )

        return value

    # ======================================================
    # WEBSITE
    # ======================================================

    def _extract_website(
        self,
        raw: Dict[str, Any],
    ) -> str:

        value = self._first_text(
            raw.get("website"),
            raw.get("web"),
            raw.get("site"),
        )

        if value:
            return value

        # Do NOT blindly use raw["url"] as website.
        # Balad POI URLs are source URLs, not business
        # websites.
        return ""

    # ======================================================
    # URL
    # ======================================================

    @staticmethod
    def _build_poi_url(
        source_id: str,
    ) -> str:

        if not source_id:
            return ""

        return (
            f"{POI_WEB}/{source_id}"
        )

    # ======================================================
    # DISTANCE
    # ======================================================

    def _parse_distance(
        self,
        value: Any,
    ) -> Optional[float]:

        if value is None:
            return None

        if isinstance(
            value,
            (int, float),
        ):

            result = float(
                value
            )

            return (
                result
                if math.isfinite(
                    result
                )
                else None
            )

        text = self._normalize_text(
            value
        )

        if not text:
            return None

        match = re.search(
            r"([0-9]+(?:[.,][0-9]+)?)",
            text,
        )

        if not match:
            return None

        try:

            result = float(
                match.group(1).replace(
                    ",",
                    ".",
                )
            )

        except ValueError:

            return None

        return (
            result
            if math.isfinite(
                result
            )
            else None
        )

    # ======================================================
    # PAGE FINGERPRINT
    # ======================================================

    def _page_fingerprint(
        self,
        raw_items: Sequence[
            Dict[str, Any]
        ],
    ) -> str:
        """
        Generate a stable fingerprint for a page.

        Used to detect Balad returning the exact same page
        repeatedly.
        """

        values: List[str] = []

        for item in raw_items:

            source_id = self._first_text(
                item.get("id"),
                item.get("poi_id"),
            )

            name = self._first_text(
                item.get("maintext"),
                item.get("name"),
                item.get("title"),
            )

            point = (
                self._extract_candidate_point(
                    item
                )
            )

            if point:

                lon, lat = point

                coordinate = (
                    f"{lat:.6f}:{lon:.6f}"
                )

            else:

                coordinate = ""

            values.append(
                "|".join(
                    (
                        source_id,
                        name,
                        coordinate,
                    )
                )
            )

        payload = "\n".join(
            values
        )

        return hashlib.sha1(
            payload.encode(
                "utf-8",
                errors="ignore",
            )
        ).hexdigest()

    # ======================================================
    # PAGINATION METADATA
    # ======================================================

    def _is_last_page(
        self,
        data: Dict[str, Any],
        current_page: int,
    ) -> bool:
        """
        Best-effort detection of explicit Balad pagination
        metadata.

        Because Balad response versions can differ, this
        method is deliberately conservative.
        """

        candidates = [
            data.get("pagination"),
            data.get("paging"),
            data.get("meta"),
            data.get("page_info"),
            data.get("paging_meta"),
        ]

        for metadata in candidates:

            if not isinstance(
                metadata,
                dict,
            ):
                continue

            # --------------------------------------------------
            # has_next
            # --------------------------------------------------

            for key in (
                "has_next",
                "hasNext",
                "has_next_page",
                "hasNextPage",
            ):

                if key in metadata:

                    value = metadata.get(
                        key
                    )

                    if value is False:
                        return True

                    if value is True:
                        return False

            # --------------------------------------------------
            # is_last
            # --------------------------------------------------

            for key in (
                "is_last",
                "isLast",
                "last_page",
                "lastPage",
            ):

                if key in metadata:

                    value = metadata.get(
                        key
                    )

                    if value is True:
                        return True

            # --------------------------------------------------
            # total pages
            # --------------------------------------------------

            for key in (
                "total_pages",
                "totalPages",
                "page_count",
                "pageCount",
            ):

                value = metadata.get(
                    key
                )

                try:

                    if (
                        value is not None
                        and current_page
                        >= int(value)
                    ):
                        return True

                except (
                    TypeError,
                    ValueError,
                ):
                    pass

        return False

    # ======================================================
    # QUICK UNIQUE COUNT
    # ======================================================

    def _quick_unique_count(
        self,
        candidates: Sequence[
            SearchCandidate
        ],
    ) -> int:

        keys: set[str] = set()

        for candidate in candidates:

            key = self._candidate_key(
                candidate
            )

            if key:
                keys.add(key)

        return len(keys)

    # ======================================================
    # DEDUPLICATION
    # ======================================================

    def _deduplicate(
        self,
        candidates: Sequence[
            SearchCandidate
        ],
    ) -> List[
        SearchCandidate
    ]:

        result: List[
            SearchCandidate
        ] = []

        by_id: Dict[
            str,
            SearchCandidate,
        ] = {}

        by_coordinate: Dict[
            Tuple[int, int],
            SearchCandidate,
        ] = {}

        by_name_location: Dict[
            str,
            SearchCandidate,
        ] = {}

        for candidate in candidates:

            # --------------------------------------------------
            # ID
            # --------------------------------------------------

            if candidate.source_id:

                existing = by_id.get(
                    candidate.source_id
                )

                if existing:

                    self.stats[
                        "duplicates"
                    ] += 1

                    self._merge_candidate(
                        existing,
                        candidate,
                    )

                    continue

            # --------------------------------------------------
            # COORDINATE
            # --------------------------------------------------

            coordinate_key = None

            if (
                candidate.latitude
                is not None
                and candidate.longitude
                is not None
            ):

                coordinate_key = (
                    round(
                        candidate.latitude,
                        5,
                    ),
                    round(
                        candidate.longitude,
                        5,
                    ),
                )

                existing = (
                    by_coordinate.get(
                        coordinate_key
                    )
                )

                if existing:

                    self.stats[
                        "duplicates"
                    ] += 1

                    self._merge_candidate(
                        existing,
                        candidate,
                    )

                    if candidate.source_id:

                        by_id[
                            candidate.source_id
                        ] = existing

                    continue

            # --------------------------------------------------
            # NAME + LOCATION
            # --------------------------------------------------

            name_key = (
                self._name_key(
                    candidate.name
                )
            )

            location_key = (
                self._name_key(
                    candidate.city
                    or candidate.address
                )
            )

            combined_key = (
                f"{name_key}|{location_key}"
            )

            if name_key:

                existing = (
                    by_name_location.get(
                        combined_key
                    )
                )

                if existing:

                    if self._same_location(
                        existing,
                        candidate,
                    ):

                        self.stats[
                            "duplicates"
                        ] += 1

                        self._merge_candidate(
                            existing,
                            candidate,
                        )

                        if candidate.source_id:

                            by_id[
                                candidate.source_id
                            ] = existing

                        continue

            # --------------------------------------------------
            # STORE
            # --------------------------------------------------

            if candidate.source_id:

                by_id[
                    candidate.source_id
                ] = candidate

            if coordinate_key:

                by_coordinate[
                    coordinate_key
                ] = candidate

            if name_key:

                by_name_location[
                    combined_key
                ] = candidate

            result.append(
                candidate
            )

        return result

    # ======================================================
    # CANDIDATE KEY
    # ======================================================

    def _candidate_key(
        self,
        candidate: SearchCandidate,
    ) -> str:

        if candidate.source_id:

            return (
                f"id:{candidate.source_id}"
            )

        if (
            candidate.latitude
            is not None
            and candidate.longitude
            is not None
        ):

            return (
                "geo:"
                f"{candidate.latitude:.5f}:"
                f"{candidate.longitude:.5f}:"
                f"{self._name_key(candidate.name)}"
            )

        return (
            "name:"
            f"{self._name_key(candidate.name)}:"
            f"{self._name_key(candidate.address)}"
        )

    # ======================================================
    # MERGE
    # ======================================================

    def _merge_candidate(
        self,
        target: SearchCandidate,
        source: SearchCandidate,
    ) -> None:

        if (
            not target.title
            and source.title
        ):
            target.title = source.title

        if (
            not target.city
            and source.city
        ):
            target.city = source.city

        if (
            not target.province
            and source.province
        ):
            target.province = source.province

        if (
            not target.address
            and source.address
        ):
            target.address = source.address

        if (
            not target.neighborhood
            and source.neighborhood
        ):
            target.neighborhood = (
                source.neighborhood
            )

        if (
            not target.street
            and source.street
        ):
            target.street = source.street

        if (
            not target.phone
            and source.phone
        ):
            target.phone = source.phone

        if (
            not target.website
            and source.website
        ):
            target.website = source.website

        if (
            not target.url
            and source.url
        ):
            target.url = source.url

        if (
            target.latitude is None
            and source.latitude is not None
        ):
            target.latitude = (
                source.latitude
            )

        if (
            target.longitude is None
            and source.longitude is not None
        ):
            target.longitude = (
                source.longitude
            )

        if (
            target.distance_km is None
            and source.distance_km is not None
        ):
            target.distance_km = (
                source.distance_km
            )

        if (
            target.score is None
            and source.score is not None
        ):
            target.score = source.score

        if (
            not target.snippet
            and source.snippet
        ):
            target.snippet = source.snippet

        if (
            target.source_type
            == "bundle-poi"
            and source.source_type
            == "poi"
        ):
            target.source_type = "poi"

        if (
            not target.raw
            and source.raw
        ):
            target.raw = source.raw

    # ======================================================
    # SAME LOCATION
    # ======================================================

    def _same_location(
        self,
        first: SearchCandidate,
        second: SearchCandidate,
    ) -> bool:

        if (
            first.latitude is None
            or first.longitude is None
            or second.latitude is None
            or second.longitude is None
        ):
            return False

        distance = self._haversine(
            first.latitude,
            first.longitude,
            second.latitude,
            second.longitude,
        )

        return distance <= 0.15

    @staticmethod
    def _haversine(
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
                delta_phi / 2
            ) ** 2
            +
            math.cos(phi1)
            * math.cos(phi2)
            * math.sin(
                delta_lambda / 2
            ) ** 2
        )

        a = max(
            0.0,
            min(
                1.0,
                a,
            ),
        )

        c = (
            2
            * math.atan2(
                math.sqrt(a),
                math.sqrt(1 - a),
            )
        )

        return (
            6371.0088 * c
        )

    # ======================================================
    # RANKING
    # ======================================================

    @staticmethod
    def _ranking_key(
        candidate: SearchCandidate,
    ) -> Tuple:

        return (
            1
            if candidate.source_type
            == "poi"
            else 0,

            1
            if candidate.phone
            else 0,

            1
            if candidate.website
            else 0,

            1
            if candidate.city
            else 0,

            candidate.score
            if candidate.score is not None
            else 0.0,

            -(
                candidate.distance_km
                if candidate.distance_km is not None
                else 999999.0
            ),

            candidate.name,
        )

    # ======================================================
    # TEXT NORMALIZATION
    # ======================================================

    def _normalize_text(
        self,
        value: Any,
    ) -> str:

        if value is None:
            return ""

        text = str(
            value
        )

        replacements = {
            "ي": "ی",
            "ى": "ی",
            "ك": "ک",
            "ۀ": "ه",
            "ة": "ه",
            "ؤ": "و",
            "إ": "ا",
            "أ": "ا",
            "ٱ": "ا",
        }

        for old, new in (
            replacements.items()
        ):

            text = text.replace(
                old,
                new,
            )

        digit_map = str.maketrans(
            "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
            "01234567890123456789",
        )

        text = text.translate(
            digit_map
        )

        text = re.sub(
            r"[\u200b\u200c\u200d\u200e\u200f\ufeff]",
            " ",
            text,
        )

        text = text.replace(
            "ـ",
            "",
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # ======================================================
    # NAME KEY
    # ======================================================

    def _name_key(
        self,
        name: str,
    ) -> str:

        value = self._normalize_text(
            name
        ).casefold()

        value = re.sub(
            r"[^\w\u0600-\u06ff]+",
            "",
            value,
        )

        return value

    # ======================================================
    # HELPERS
    # ======================================================

    def _first_text(
        self,
        *values: Any,
    ) -> str:

        for value in values:

            normalized = (
                self._normalize_text(
                    value
                )
            )

            if normalized:
                return normalized

        return ""

    @staticmethod
    def _safe_int(
        value: Any,
        default: int,
    ) -> int:

        try:

            return int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            return default

    @staticmethod
    def _safe_float(
        value: Any,
        default: float,
    ) -> float:

        try:

            result = float(
                value
            )

            if not math.isfinite(
                result
            ):
                return default

            return result

        except (
            TypeError,
            ValueError,
        ):

            return default

    @staticmethod
    def _safe_optional_float(
        value: Any,
    ) -> Optional[float]:

        try:

            result = float(
                value
            )

            if not math.isfinite(
                result
            ):
                return None

            return result

        except (
            TypeError,
            ValueError,
        ):

            return None

    # ======================================================
    # OUTPUT
    # ======================================================

    def _candidate_to_dict(
        self,
        candidate: SearchCandidate,
    ) -> Dict[str, Any]:

        return {
            # --------------------------------------------------
            # IDENTITY
            # --------------------------------------------------

            "title": candidate.title,

            "name": candidate.name,

            # --------------------------------------------------
            # LOCATION
            # --------------------------------------------------

            "province": candidate.province,

            "city": candidate.city,

            "address": candidate.address,

            "neighborhood": candidate.neighborhood,

            "street": candidate.street,

            # --------------------------------------------------
            # CONTACT
            # --------------------------------------------------

            "phone": candidate.phone,

            "website": candidate.website,

            # --------------------------------------------------
            # GEO
            # --------------------------------------------------

            "latitude": candidate.latitude,

            "longitude": candidate.longitude,

            "distance_km": (
                round(
                    candidate.distance_km,
                    3,
                )
                if candidate.distance_km
                is not None
                else None
            ),

            # --------------------------------------------------
            # SOURCE
            # --------------------------------------------------

            "url": candidate.url,

            "source_url": candidate.url,

            "source_id": (
                candidate.source_id
                or None
            ),

            "source": PROVIDER_NAME,

            "source_type": (
                candidate.source_type
            ),

            # --------------------------------------------------
            # SEARCH CONTEXT
            # --------------------------------------------------

            "snippet": candidate.snippet,

            "query": candidate.query,

            # --------------------------------------------------
            # PROVIDER DATA
            # --------------------------------------------------

            "score": (
                round(
                    candidate.score,
                    3,
                )
                if candidate.score
                is not None
                else None
            ),

            "provider": PROVIDER_NAME,
        }

    # ======================================================
    # LOGGING
    # ======================================================

    def _log(
        self,
        message: str,
    ) -> None:

        if self.debug:

            print(
                message
            )

    # ======================================================
    # CLOSE
    # ======================================================

    def close(
        self,
    ) -> None:

        if self.session is None:
            return

        try:

            self.session.close()

        except Exception:

            pass

        finally:

            self.session = None


# ==========================================================
# FACTORY
# ==========================================================


def create_provider(
    **kwargs: Any,
) -> BaladProvider:

    return BaladProvider(
        **kwargs
    )


# ==========================================================
# MANUAL TEST
# ==========================================================


if __name__ == "__main__":

    provider = BaladProvider(
        delay=0.2,
        timeout=20,
        max_results=None,
        max_pages=1000,
        debug=True,
    )

    try:

        print(
            "=" * 70
        )

        print(
            "EYES — BALAD EXHAUSTIVE PROVIDER"
        )

        print(
            "=" * 70
        )

        print()

        print(
            "INFO:"
        )

        print(
            provider.info()
        )

        print()

        print(
            "SEARCH: مدارس رشت"
        )

        results = provider.search(
            "مدارس رشت",
            city="رشت",
            max_results=None,
        )

        print()

        print(
            f"RESULTS: {len(results)}"
        )

        for index, result in enumerate(
            results,
            1,
        ):

            print(
                f"[{index:05d}] "
                f"{result.get('name')} | "
                f"{result.get('city')} | "
                f"{result.get('address')} | "
                f"{result.get('phone')} | "
                f"{result.get('latitude')} | "
                f"{result.get('longitude')}"
            )

        print()

        print(
            "STATS:"
        )

        print(
            provider.stats
        )

    finally:

        provider.close()