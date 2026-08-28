
# import requests

# from urllib.parse import urlparse, parse_qs, unquote

# from bs4 import BeautifulSoup

# from providers.base import SearchProvider


# class DuckDuckGoProvider(SearchProvider):

#     name = "duckduckgo"

#     BASE_URL = "https://html.duckduckgo.com/html/"

#     def __init__(self, timeout=15):

#         self.timeout = timeout

#         self.session = requests.Session()

#         self.session.headers.update({

#             "User-Agent":
#                 (
#                     "Mozilla/5.0 "
#                     "(X11; Linux x86_64) "
#                     "AppleWebKit/537.36 "
#                     "(KHTML, like Gecko) "
#                     "Chrome/131.0 Safari/537.36"
#                 ),

#             "Accept":
#                 "text/html,application/xhtml+xml,application/xml;q=0.9,"
#                 "image/avif,image/webp,*/*;q=0.8",

#             "Accept-Language":
#                 "fa,en;q=0.9",

#             "Connection":
#                 "keep-alive",

#         })

#     # ==========================================
#     # SEARCH
#     # ==========================================

#     def search(
#         self,
#         query,
#         page=1
#     ):

#         query = str(query).strip()

#         if not query:
#             return []

#         print(
#             f"[DDG] Query: {query} | Page: {page}"
#         )

#         params = {

#             "q":
#                 query,

#             "s":
#                 max(
#                     0,
#                     (page - 1) * 30
#                 ),

#             "kl":
#                 "ir-fa",

#         }

#         try:

#             response = self.session.get(

#                 self.BASE_URL,

#                 params=params,

#                 timeout=self.timeout

#             )

#             print(
#                 f"[DDG] Status: {response.status_code}"
#             )

#             response.raise_for_status()

#         except requests.RequestException as error:

#             print(
#                 f"[DDG ERROR] {error}"
#             )

#             return []

#         results = self.parse(
#             response.text
#         )

#         print(
#             f"[DDG] Parsed: {len(results)}"
#         )

#         return results

#     # ==========================================
#     # PARSER
#     # ==========================================

#     def parse(self, html):

#         if not html:
#             return []

#         soup = BeautifulSoup(
#             html,
#             "html.parser"
#         )

#         results = []

#         seen = set()

#         items = soup.select(
#             ".result"
#         )

#         for item in items:

#             # ----------------------------------
#             # TITLE / LINK
#             # ----------------------------------

#             link = item.select_one(
#                 ".result__a"
#             )

#             if not link:
#                 continue

#             title = link.get_text(
#                 " ",
#                 strip=True
#             )

#             raw_url = link.get(
#                 "href",
#                 ""
#             ).strip()

#             if not title or not raw_url:
#                 continue

#             # ----------------------------------
#             # REAL URL
#             # ----------------------------------

#             url = self.clean_url(
#                 raw_url
#             )

#             if not url:
#                 continue

#             # ----------------------------------
#             # DEDUPLICATION
#             # ----------------------------------

#             if url in seen:
#                 continue

#             seen.add(url)

#             # ----------------------------------
#             # SNIPPET
#             # ----------------------------------

#             snippet_node = item.select_one(
#                 ".result__snippet"
#             )

#             snippet = ""

#             if snippet_node:

#                 snippet = snippet_node.get_text(
#                     " ",
#                     strip=True
#                 )

#             # ----------------------------------
#             # NORMALIZED RESULT
#             # ----------------------------------

#             results.append({

#                 "title":
#                     title,

#                 "name":
#                     title,

#                 "address":
#                     "",

#                 "city":
#                     "",

#                 "province":
#                     "",

#                 "phone":
#                     "",

#                 "website":
#                     "",

#                 "latitude":
#                     None,

#                 "longitude":
#                     None,

#                 "distance_km":
#                     None,

#                 "url":
#                     url,

#                 "snippet":
#                     snippet,

#                 "source":
#                     self.name

#             })

#         return results

#     # ==========================================
#     # URL CLEANER
#     # ==========================================

#     def clean_url(self, url):

#         if not url:
#             return None

#         url = url.strip()

#         # --------------------------------------
#         # Protocol-relative URL
#         # --------------------------------------

#         if url.startswith("//"):

#             url = "https:" + url

#         # --------------------------------------
#         # DDG redirect
#         #
#         # Example:
#         #
#         # https://duckduckgo.com/l/?uddg=https%3A...
#         # --------------------------------------

#         if (
#             "duckduckgo.com/l/" in url
#             or
#             url.startswith("/l/")
#         ):

#             if url.startswith("/l/"):

#                 url = (
#                     "https://duckduckgo.com"
#                     + url
#                 )

#             try:

#                 parsed = urlparse(
#                     url
#                 )

#                 params = parse_qs(
#                     parsed.query
#                 )

#                 target = (
#                     params.get("uddg")
#                     or
#                     params.get("u")
#                 )

#                 if target:

#                     url = unquote(
#                         target[0]
#                     )

#             except Exception as error:

#                 print(
#                     f"[DDG URL ERROR] {error}"
#                 )

#                 return None

#         # --------------------------------------
#         # Decode URL
#         # --------------------------------------

#         try:

#             url = unquote(
#                 url
#             ).strip()

#         except Exception:

#             return None

#         # --------------------------------------
#         # Only HTTP / HTTPS
#         # --------------------------------------

#         if not url.startswith(
#             (
#                 "http://",
#                 "https://"
#             )
#         ):

#             return None

#         # --------------------------------------
#         # Validate hostname
#         # --------------------------------------

#         try:

#             hostname = (
#                 urlparse(url)
#                 .hostname
#                 or ""
#             ).lower()

#         except Exception:

#             return None

#         if not hostname:
#             return None

#         # --------------------------------------
#         # Ignore DDG internal links
#         # --------------------------------------

#         if (
#             hostname == "duckduckgo.com"
#             or
#             hostname.endswith(
#                 ".duckduckgo.com"
#             )
#         ):

#             return None

#         return url

#     # ==========================================
#     # HEALTH CHECK
#     # ==========================================

#     def health_check(self):

#         try:

#             response = self.session.get(

#                 self.BASE_URL,

#                 params={
#                     "q": "test"
#                 },

#                 timeout=self.timeout

#             )

#             return (
#                 response.status_code == 200
#             )

#         except requests.RequestException:

#             return False

#     # ==========================================
#     # INFO
#     # ==========================================

#     def info(self):

#         return {

#             "name":
#                 self.name,

#             "timeout":
#                 self.timeout,

#             "base_url":
#                 self.BASE_URL,

#         }

#############################################################################
#############################################################################
#############################################################################
#############################################################################
#############################################################################





import threading
import time

import requests

from urllib.parse import (
    urlparse,
    parse_qs,
    unquote,
)

from collections import OrderedDict

from bs4 import BeautifulSoup

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from providers.base import SearchProvider


class DuckDuckGoProvider(SearchProvider):

    name = "duckduckgo"

    BASE_URL = "https://html.duckduckgo.com/html/"

    # ======================================================
    # LIMITS
    # ======================================================

    MAX_PAGES = 50

    PAGE_OFFSET = 30

    MAX_DORK_QUERIES = 10

    # ======================================================
    # GLOBAL RATE CONTROL
    # ======================================================
    #
    # این متغیرها بین تمام instanceهای Provider
    # داخل همان Process مشترک هستند.
    #
    # Thread Manager پروژه همچنان مسئول Threadهاست.
    # Provider هیچ Thread جدیدی ایجاد نمی‌کند.
    # ======================================================

    _rate_lock = threading.RLock()

    _next_allowed_time = 0.0

    _cooldown_until = 0.0

    _consecutive_rate_limits = 0

    # حداقل فاصله بین درخواست‌ها
    #
    # این مقدار عمداً محافظه‌کارانه است.
    # عدد «امن رسمی» از طرف DDG اعلام نشده است.
    MIN_REQUEST_INTERVAL = 1.0

    # حداکثر cooldown داخلی
    MAX_COOLDOWN = 300.0

    # ======================================================
    # SHARED CACHE
    # ======================================================

    _cache_lock = threading.RLock()

    _cache = OrderedDict()

    CACHE_MAX_ITEMS = 5000

    CACHE_TTL = 900.0

    # ======================================================
    # ADAPTIVE PAGINATION
    # ======================================================

    # اگر چند صفحه متوالی نتیجه جدیدی ندهند،
    # pagination متوقف می‌شود.
    MAX_EMPTY_PAGES = 2

    # ======================================================
    # INIT
    # ======================================================

    def __init__(
        self,
        timeout=15,
        region="ir-fa",
    ):

        self.timeout = timeout

        self.region = (
            str(region).strip()
            if region
            else "ir-fa"
        )

        # --------------------------------------------------
        # Original Session
        #
        # برای compatibility حفظ شده است.
        # --------------------------------------------------

        self.session = requests.Session()

        self.session.headers.update({

            "User-Agent":
                (
                    "Mozilla/5.0 "
                    "(X11; Linux x86_64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/131.0 Safari/537.36"
                ),

            "Accept":
                (
                    "text/html,application/xhtml+xml,"
                    "application/xml;q=0.9,"
                    "image/avif,image/webp,*/*;q=0.8"
                ),

            "Accept-Language":
                "fa,en;q=0.9",

            "Connection":
                "keep-alive",
        })

        self._configure_session(
            self.session
        )

        # --------------------------------------------------
        # Thread Local
        # --------------------------------------------------

        self._thread_local = (
            threading.local()
        )

        # --------------------------------------------------
        # Session Registry
        # --------------------------------------------------

        self._sessions = {}

        self._sessions_lock = (
            threading.RLock()
        )

        self._closed = False

    # ======================================================
    # SESSION CONFIGURATION
    # ======================================================

    def _configure_session(
        self,
        session,
    ):

        retry = Retry(

            total=3,

            connect=3,

            read=3,

            status=3,

            backoff_factor=0.8,

            # 429 عمداً اینجا نیست.
            #
            # Rate Limit باید توسط Global Controller
            # مدیریت شود.
            status_forcelist=[
                500,
                502,
                503,
                504,
            ],

            allowed_methods=frozenset([
                "GET",
            ]),

            respect_retry_after_header=True,

            raise_on_status=False,
        )

        adapter = HTTPAdapter(

            max_retries=retry,

            pool_connections=4,

            pool_maxsize=4,

            pool_block=False,
        )

        session.mount(
            "http://",
            adapter,
        )

        session.mount(
            "https://",
            adapter,
        )

    # ======================================================
    # THREAD LOCAL SESSION
    # ======================================================

    def _get_session(self):

        if self._closed:

            raise RuntimeError(
                "DuckDuckGoProvider is closed"
            )

        session = getattr(
            self._thread_local,
            "session",
            None,
        )

        if session is not None:

            return session

        session = requests.Session()

        session.headers.update(
            self.session.headers
        )

        self._configure_session(
            session
        )

        self._thread_local.session = (
            session
        )

        current_thread = (
            threading.current_thread()
        )

        with self._sessions_lock:

            self._sessions[
                current_thread
            ] = session

        return session

    # ======================================================
    # GLOBAL RATE CONTROLLER
    # ======================================================

    @classmethod
    def _wait_for_rate_limit(
        cls,
    ):

        while True:

            with cls._rate_lock:

                now = time.monotonic()

                # ------------------------------------------
                # Global cooldown
                # ------------------------------------------

                if now < cls._cooldown_until:

                    wait_time = (
                        cls._cooldown_until
                        - now
                    )

                else:

                    # --------------------------------------
                    # Minimum interval
                    # --------------------------------------

                    wait_time = max(
                        0.0,
                        cls._next_allowed_time
                        - now,
                    )

                    if wait_time <= 0:

                        cls._next_allowed_time = (
                            now
                            + cls.MIN_REQUEST_INTERVAL
                        )

                        return

            if wait_time > 0:

                time.sleep(
                    wait_time
                )

    # ======================================================
    # RATE LIMIT RESPONSE
    # ======================================================

    @classmethod
    def _handle_rate_limit(
        cls,
        response,
    ):

        retry_after = None

        try:

            header = response.headers.get(
                "Retry-After"
            )

            if header:

                retry_after = float(
                    header
                )

        except (
            TypeError,
            ValueError,
        ):

            retry_after = None

        with cls._rate_lock:

            cls._consecutive_rate_limits += 1

            # ------------------------------------------
            # اگر Retry-After وجود دارد همان را ترجیح بده.
            # در غیر این صورت exponential backoff.
            # ------------------------------------------

            if retry_after is not None:

                cooldown = max(
                    1.0,
                    retry_after,
                )

            else:

                level = min(
                    cls._consecutive_rate_limits,
                    8,
                )

                cooldown = min(
                    cls.MAX_COOLDOWN,
                    2 ** level,
                )

            now = time.monotonic()

            cls._cooldown_until = max(
                cls._cooldown_until,
                now + cooldown,
            )

            cls._next_allowed_time = (
                cls._cooldown_until
            )

        print(
            "[DDG RATE LIMIT] "
            f"Cooldown: {cooldown:.1f}s"
        )

    # ======================================================
    # SUCCESSFUL REQUEST
    # ======================================================

    @classmethod
    def _handle_success(
        cls,
    ):

        with cls._rate_lock:

            cls._consecutive_rate_limits = 0

    # ======================================================
    # HARD BLOCK / ACCESS DENIED
    # ======================================================

    @classmethod
    def _handle_access_denied(
        cls,
    ):

        with cls._rate_lock:

            now = time.monotonic()

            # 403 را شدیدتر از 429 مدیریت می‌کنیم.
            cooldown = 60.0

            cls._cooldown_until = max(
                cls._cooldown_until,
                now + cooldown,
            )

            cls._next_allowed_time = (
                cls._cooldown_until
            )

        print(
            "[DDG ACCESS DENIED] "
            f"Cooldown: {cooldown:.1f}s"
        )

    # ======================================================
    # CACHE KEY
    # ======================================================

    def _cache_key(
        self,
        query,
        page,
    ):

        return (
            self.name,
            self.region,
            str(query).strip().casefold(),
            int(page),
        )

    # ======================================================
    # CACHE GET
    # ======================================================

    def _cache_get(
        self,
        key,
    ):

        now = time.monotonic()

        with self._cache_lock:

            entry = self._cache.get(
                key
            )

            if entry is None:

                return None

            timestamp, value = entry

            # ------------------------------------------
            # Expired
            # ------------------------------------------

            if (
                now - timestamp
                > self.CACHE_TTL
            ):

                try:

                    del self._cache[key]

                except KeyError:

                    pass

                return None

            # ------------------------------------------
            # LRU update
            # ------------------------------------------

            self._cache.move_to_end(
                key
            )

            # جلوگیری از تغییر داده cache توسط caller
            return list(value)

    # ======================================================
    # CACHE SET
    # ======================================================

    def _cache_set(
        self,
        key,
        value,
    ):

        now = time.monotonic()

        value = list(
            value or []
        )

        with self._cache_lock:

            self._cache[key] = (
                now,
                value,
            )

            self._cache.move_to_end(
                key
            )

            while (
                len(self._cache)
                > self.CACHE_MAX_ITEMS
            ):

                self._cache.popitem(
                    last=False
                )

    # ======================================================
    # CLEAR CACHE
    # ======================================================

    @classmethod
    def clear_cache(
        cls,
    ):

        with cls._cache_lock:

            cls._cache.clear()

    # ======================================================
    # SEARCH
    #
    # API قبلی حفظ شده
    # ======================================================

    def search(
        self,
        query,
        page=1,
    ):

        query = str(
            query
        ).strip()

        if not query:

            return []

        # --------------------------------------------------
        # Page validation
        # --------------------------------------------------

        try:

            page = int(
                page
            )

        except (
            TypeError,
            ValueError,
        ):

            page = 1

        page = max(
            1,
            page,
        )

        if page > self.MAX_PAGES:

            print(
                f"[DDG] Page {page} exceeds "
                f"maximum page {self.MAX_PAGES}"
            )

            return []

        # --------------------------------------------------
        # Thread-local status
        # --------------------------------------------------

        self._thread_local.last_status = (
            None
        )

        self._thread_local.last_retry_after = (
            None
        )

        # --------------------------------------------------
        # Cache
        # --------------------------------------------------

        cache_key = self._cache_key(
            query,
            page,
        )

        cached = self._cache_get(
            cache_key
        )

        if cached is not None:

            self._thread_local.last_status = (
                "cache"
            )

            print(
                f"[DDG CACHE HIT] "
                f"{query} | Page: {page}"
            )

            return cached

        print(
            f"[DDG] Query: {query} | Page: {page}"
        )

        # --------------------------------------------------
        # Global Rate Controller
        # --------------------------------------------------

        self._wait_for_rate_limit()

        params = {

            "q":
                query,

            "s":
                (page - 1)
                * self.PAGE_OFFSET,

            "kl":
                self.region,
        }

        try:

            session = self._get_session()

            response = session.get(

                self.BASE_URL,

                params=params,

                timeout=self.timeout,
            )

            status = (
                response.status_code
            )

            self._thread_local.last_status = (
                status
            )

            print(
                f"[DDG] Status: {status}"
            )

            # --------------------------------------------------
            # 429
            # --------------------------------------------------

            if status == 429:

                self._handle_rate_limit(
                    response
                )

                return []

            # --------------------------------------------------
            # 403
            # --------------------------------------------------

            if status == 403:

                self._handle_access_denied()

                return []

            # --------------------------------------------------
            # Other HTTP errors
            # --------------------------------------------------

            response.raise_for_status()

            # --------------------------------------------------
            # Success
            # --------------------------------------------------

            self._handle_success()

            if not response.text:

                self._cache_set(
                    cache_key,
                    [],
                )

                return []

        except requests.RequestException as error:

            self._thread_local.last_status = (
                "request_error"
            )

            print(
                f"[DDG ERROR] {error}"
            )

            return []

        except RuntimeError as error:

            self._thread_local.last_status = (
                "provider_closed"
            )

            print(
                f"[DDG ERROR] {error}"
            )

            return []

        # --------------------------------------------------
        # Parse
        # --------------------------------------------------

        results = self.parse(
            response.text
        )

        print(
            f"[DDG] Parsed: {len(results)}"
        )

        # --------------------------------------------------
        # Cache
        # --------------------------------------------------

        self._cache_set(
            cache_key,
            results,
        )

        return list(
            results
        )

    # ======================================================
    # SEARCH PAGES
    # ======================================================

    def search_pages(
        self,
        query,
        start_page=1,
        max_pages=50,
    ):

        query = str(
            query
        ).strip()

        if not query:

            return []

        try:

            start_page = int(
                start_page
            )

        except (
            TypeError,
            ValueError,
        ):

            start_page = 1

        try:

            max_pages = int(
                max_pages
            )

        except (
            TypeError,
            ValueError,
        ):

            max_pages = self.MAX_PAGES

        start_page = max(
            1,
            start_page,
        )

        max_pages = max(
            1,
            min(
                max_pages,
                self.MAX_PAGES,
            ),
        )

        end_page = min(
            start_page
            + max_pages
            - 1,
            self.MAX_PAGES,
        )

        results = []

        seen = set()

        empty_pages = 0

        for current_page in range(
            start_page,
            end_page + 1,
        ):

            page_results = self.search(
                query,
                current_page,
            )

            status = getattr(
                self._thread_local,
                "last_status",
                None,
            )

            # ------------------------------------------
            # Rate limited / blocked
            # ------------------------------------------

            if status in (
                429,
                403,
            ):

                print(
                    "[DDG PAGINATION] "
                    "Stopping because of "
                    f"HTTP {status}"
                )

                break

            # ------------------------------------------
            # No result
            # ------------------------------------------

            if not page_results:

                empty_pages += 1

                if (
                    empty_pages
                    >= self.MAX_EMPTY_PAGES
                ):

                    print(
                        "[DDG PAGINATION] "
                        "Stopping after consecutive "
                        "empty pages."
                    )

                    break

                continue

            empty_pages = 0

            new_count = 0

            for result in page_results:

                url = result.get(
                    "url"
                )

                if not url:
                    continue

                if url in seen:
                    continue

                seen.add(
                    url
                )

                results.append(
                    result
                )

                new_count += 1

            # ------------------------------------------
            # Adaptive stopping
            # ------------------------------------------

            if new_count == 0:

                empty_pages += 1

                if (
                    empty_pages
                    >= self.MAX_EMPTY_PAGES
                ):

                    print(
                        "[DDG PAGINATION] "
                        "Stopping because pages "
                        "produce no new URLs."
                    )

                    break

        return results

    # ======================================================
    # DORK BUILDER
    # ======================================================

    def build_dork_queries(
        self,
        query,
        city=None,
        country=None,
        category=None,
        extra_terms=None,
    ):

        query = self._clean_text(
            query
        )

        city = self._clean_text(
            city
        )

        country = self._clean_text(
            country
        )

        category = self._clean_text(
            category
        )

        if extra_terms is None:

            extra_terms = []

        elif isinstance(
            extra_terms,
            str,
        ):

            extra_terms = [
                extra_terms
            ]

        cleaned_extra_terms = []

        for term in extra_terms:

            term = self._clean_text(
                term
            )

            if not term:
                continue

            if term not in cleaned_extra_terms:

                cleaned_extra_terms.append(
                    term
                )

        if not query:

            return []

        queries = []

        # ==================================================
        # Base Query
        # ==================================================

        self._add_query(
            queries,
            query,
        )

        # ==================================================
        # Query + City
        # ==================================================

        if city:

            self._add_query(
                queries,
                f"{query} {city}",
            )

            self._add_query(
                queries,
                f'"{query}" "{city}"',
            )

        # ==================================================
        # Query + City + Country
        # ==================================================

        if city and country:

            self._add_query(
                queries,
                f"{query} {city} {country}",
            )

            self._add_query(
                queries,
                f'"{query}" "{city}" "{country}"',
            )

        # ==================================================
        # Category + City
        # ==================================================

        if category and city:

            category_exact = (
                self._quote_if_needed(
                    category
                )
            )

            self._add_query(
                queries,
                f"{category_exact} {city}",
            )

            self._add_query(
                queries,
                f'"{category}" "{city}"',
            )

        # ==================================================
        # Query + Category + City
        # ==================================================

        if (
            query
            and category
            and city
        ):

            category_exact = (
                self._quote_if_needed(
                    category
                )
            )

            self._add_query(
                queries,
                f"{query} "
                f"{category_exact} "
                f"{city}",
            )

        # ==================================================
        # intitle
        # ==================================================

        if category and city:

            title_value = (
                self._quote_if_needed(
                    category
                )
            )

            self._add_query(
                queries,
                f'intitle:{title_value} "{city}"',
            )

        # ==================================================
        # inurl
        # ==================================================

        if city:

            city_url_value = (
                self._normalize_operator_value(
                    city
                )
            )

            self._add_query(
                queries,
                f"{query} "
                f"inurl:{city_url_value}",
            )

        # ==================================================
        # Extra Terms
        # ==================================================

        for term in cleaned_extra_terms:

            if city:

                self._add_query(
                    queries,
                    f"{query} "
                    f"{term} "
                    f"{city}",
                )

            else:

                self._add_query(
                    queries,
                    f"{query} {term}",
                )

        # ==================================================
        # Final Cleanup
        # ==================================================

        return self._clean_query_list(
            queries
        )[:self.MAX_DORK_QUERIES]

    # ======================================================
    # LOCATION SEARCH
    # ======================================================

    def search_location(
        self,
        query,
        city,
        country=None,
        category=None,
        pages=1,
        extra_terms=None,
    ):

        query = self._clean_text(
            query
        )

        city = self._clean_text(
            city
        )

        if not query:
            return []

        if not city:
            return []

        try:

            pages = int(
                pages
            )

        except (
            TypeError,
            ValueError,
        ):

            pages = 1

        pages = max(
            1,
            min(
                pages,
                self.MAX_PAGES,
            ),
        )

        dork_queries = (
            self.build_dork_queries(

                query=query,

                city=city,

                country=country,

                category=category,

                extra_terms=extra_terms,
            )
        )

        if not dork_queries:

            return []

        print(
            "[DDG LOCATION] "
            f"Query={query} "
            f"City={city} "
            f"Dorks={len(dork_queries)} "
            f"MaxPages={pages}"
        )

        all_results = []

        # --------------------------------------------------
        # Dorks are sequential INSIDE this call.
        #
        # External Thread Manager can execute multiple
        # scraper jobs concurrently.
        # --------------------------------------------------

        for dork_query in dork_queries:

            print(
                f"[DDG DORK] {dork_query}"
            )

            dork_results = (
                self.search_pages(

                    dork_query,

                    start_page=1,

                    max_pages=pages,
                )
            )

            all_results.extend(
                dork_results
            )

            # ----------------------------------------------
            # اگر Rate Limit یا Block اتفاق افتاده،
            # Dorkهای بعدی را هم متوقف می‌کنیم.
            # ----------------------------------------------

            status = getattr(
                self._thread_local,
                "last_status",
                None,
            )

            if status in (
                429,
                403,
            ):

                print(
                    "[DDG LOCATION] "
                    "Stopping remaining dorks "
                    f"because of HTTP {status}"
                )

                break

        results = self._deduplicate(
            all_results
        )

        print(
            "[DDG LOCATION] "
            f"Final results={len(results)}"
        )

        return results

    # ======================================================
    # LOCATION PAGES
    # ======================================================

    def search_location_pages(
        self,
        query,
        city,
        country=None,
        category=None,
        pages=50,
        extra_terms=None,
    ):

        try:

            pages = int(
                pages
            )

        except (
            TypeError,
            ValueError,
        ):

            pages = self.MAX_PAGES

        pages = max(
            1,
            min(
                pages,
                self.MAX_PAGES,
            ),
        )

        return self.search_location(

            query=query,

            city=city,

            country=country,

            category=category,

            pages=pages,

            extra_terms=extra_terms,
        )

    # ======================================================
    # PARSER
    # ======================================================

    def parse(
        self,
        html,
    ):

        if not html:

            return []

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        results = []

        seen = set()

        items = soup.select(
            ".result"
        )

        for item in items:

            # --------------------------------------------------
            # Link
            # --------------------------------------------------

            link = item.select_one(
                ".result__a"
            )

            if not link:
                continue

            title = link.get_text(
                " ",
                strip=True,
            )

            raw_url = link.get(
                "href",
                "",
            ).strip()

            if (
                not title
                or not raw_url
            ):

                continue

            # --------------------------------------------------
            # Clean URL
            # --------------------------------------------------

            url = self.clean_url(
                raw_url
            )

            if not url:
                continue

            if url in seen:
                continue

            seen.add(
                url
            )

            # --------------------------------------------------
            # Snippet
            # --------------------------------------------------

            snippet_node = (
                item.select_one(
                    ".result__snippet"
                )
            )

            snippet = ""

            if snippet_node:

                snippet = (
                    snippet_node.get_text(
                        " ",
                        strip=True,
                    )
                )

            # --------------------------------------------------
            # Original normalized output
            # --------------------------------------------------

            results.append({

                "title":
                    title,

                "name":
                    title,

                "address":
                    "",

                "city":
                    "",

                "province":
                    "",

                "phone":
                    "",

                "website":
                    "",

                "latitude":
                    None,

                "longitude":
                    None,

                "distance_km":
                    None,

                "url":
                    url,

                "snippet":
                    snippet,

                "source":
                    self.name,
            })

        return results

    # ======================================================
    # URL CLEANER
    # ======================================================

    def clean_url(
        self,
        url,
    ):

        if not url:

            return None

        url = url.strip()

        # --------------------------------------------------
        # Protocol relative
        # --------------------------------------------------

        if url.startswith("//"):

            url = (
                "https:"
                + url
            )

        # --------------------------------------------------
        # DDG redirect
        # --------------------------------------------------

        if (
            "duckduckgo.com/l/" in url
            or
            url.startswith("/l/")
        ):

            if url.startswith("/l/"):

                url = (
                    "https://duckduckgo.com"
                    + url
                )

            try:

                parsed = urlparse(
                    url
                )

                params = parse_qs(
                    parsed.query
                )

                target = (
                    params.get("uddg")
                    or
                    params.get("u")
                )

                if target:

                    url = target[0]

            except Exception as error:

                print(
                    f"[DDG URL ERROR] {error}"
                )

                return None

        # --------------------------------------------------
        # Decode
        # --------------------------------------------------

        try:

            url = unquote(
                url
            ).strip()

        except Exception:

            return None

        # --------------------------------------------------
        # HTTP only
        # --------------------------------------------------

        if not url.startswith(
            (
                "http://",
                "https://",
            )
        ):

            return None

        # --------------------------------------------------
        # Hostname
        # --------------------------------------------------

        try:

            hostname = (
                urlparse(url)
                .hostname
                or ""
            ).lower()

        except Exception:

            return None

        if not hostname:

            return None

        # --------------------------------------------------
        # Ignore DDG URLs
        # --------------------------------------------------

        if (
            hostname == "duckduckgo.com"
            or
            hostname.endswith(
                ".duckduckgo.com"
            )
        ):

            return None

        return url

    # ======================================================
    # DEDUPLICATION
    # ======================================================

    def _deduplicate(
        self,
        results,
    ):

        if not results:

            return []

        output = []

        seen = set()

        for result in results:

            if not isinstance(
                result,
                dict,
            ):

                continue

            url = result.get(
                "url"
            )

            if not url:

                continue

            if url in seen:

                continue

            seen.add(
                url
            )

            output.append(
                result
            )

        return output

    # ======================================================
    # TEXT CLEANER
    # ======================================================

    def _clean_text(
        self,
        value,
    ):

        if value is None:

            return ""

        return " ".join(
            str(value)
            .strip()
            .split()
        )

    # ======================================================
    # ADD QUERY
    # ======================================================

    def _add_query(
        self,
        queries,
        query,
    ):

        query = self._clean_text(
            query
        )

        if not query:

            return

        if query in queries:

            return

        queries.append(
            query
        )

    # ======================================================
    # QUERY CLEANUP
    # ======================================================

    def _clean_query_list(
        self,
        queries,
    ):

        output = []

        seen = set()

        for query in queries:

            query = self._clean_text(
                query
            )

            if not query:

                continue

            normalized = (
                query.casefold()
            )

            if normalized in seen:

                continue

            seen.add(
                normalized
            )

            output.append(
                query
            )

        return output

    # ======================================================
    # QUOTE IF NEEDED
    # ======================================================

    def _quote_if_needed(
        self,
        value,
    ):

        value = self._clean_text(
            value
        )

        if not value:

            return ""

        if (
            " " in value
            and
            not (
                value.startswith('"')
                and
                value.endswith('"')
            )
        ):

            return (
                f'"{value}"'
            )

        return value

    # ======================================================
    # OPERATOR VALUE
    # ======================================================

    def _normalize_operator_value(
        self,
        value,
    ):

        value = self._clean_text(
            value
        )

        if not value:

            return ""

        return value.replace(
            " ",
            "-",
        )

    # ======================================================
    # HEALTH CHECK
    # ======================================================

    def health_check(
        self,
    ):

        try:

            session = self._get_session()

            self._wait_for_rate_limit()

            response = session.get(

                self.BASE_URL,

                params={

                    "q":
                        "test",

                    "kl":
                        self.region,
                },

                timeout=self.timeout,
            )

            if response.status_code == 429:

                self._handle_rate_limit(
                    response
                )

                return False

            if response.status_code == 403:

                self._handle_access_denied()

                return False

            if response.status_code != 200:

                return False

            if not response.text:

                return False

            self._handle_success()

            return True

        except requests.RequestException:

            return False

        except Exception:

            return False

    # ======================================================
    # INFO
    # ======================================================

    def info(
        self,
    ):

        return {

            "name":
                self.name,

            "timeout":
                self.timeout,

            "base_url":
                self.BASE_URL,

        }

    # ======================================================
    # CLOSE
    # ======================================================

    def close(
        self,
    ):

        with self._sessions_lock:

            if self._closed:

                return

            self._closed = True

            sessions = list(
                self._sessions.values()
            )

            self._sessions.clear()

        closed_ids = set()

        for session in sessions:

            try:

                session_id = id(
                    session
                )

                if session_id in closed_ids:

                    continue

                session.close()

                closed_ids.add(
                    session_id
                )

            except Exception:

                pass

        try:

            self.session.close()

        except Exception:

            pass

        try:

            self._thread_local.session = None

        except Exception:

            pass

    # ======================================================
    # CONTEXT MANAGER
    # ======================================================

    def __enter__(
        self,
    ):

        return self

    def __exit__(
        self,
        exc_type,
        exc_value,
        traceback,
    ):

        self.close()