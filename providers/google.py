from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

from providers.base import SearchProvider


class GoogleProvider(SearchProvider):

    name = "google"

    BASE_URL = "https://www.google.com/search"

    def __init__(self, timeout=15):

        super().__init__(
            timeout=timeout
        )

        self.session = requests.Session()

        self.session.headers.update({

            "User-Agent": (
                "Mozilla/5.0 "
                "(X11; Linux x86_64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/131.0 Safari/537.36"
            ),

            "Accept-Language":
                "fa,en;q=0.9",

            "Accept":
                (
                    "text/html,"
                    "application/xhtml+xml,"
                    "application/xml;q=0.9,"
                    "*/*;q=0.8"
                ),

        })

    # ==========================================
    # SEARCH
    # ==========================================

    def search(
        self,
        query,
        page=1,
        **kwargs
    ):

        query = self._string(query)

        if not query:
            return []

        try:
            page = max(1, int(page))
        except (ValueError, TypeError):
            page = 1

        print(
            f"[GOOGLE] Query: {query} | Page: {page}"
        )

        params = {
            "q": query,
            "start": (page - 1) * 10,
            "hl": "fa",
            "filter": "0",
            "num": "10",
        }

        try:

            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout
            )

            print(
                f"[GOOGLE] Status: "
                f"{response.status_code}"
            )

            response.raise_for_status()

        except requests.RequestException as error:

            print(
                f"[GOOGLE ERROR] {error}"
            )

            return []

        results = self.parse(
            response.text
        )

        results = self.normalize_results(
            results
        )

        print(
            f"[GOOGLE] Parsed: "
            f"{len(results)}"
        )

        return results

    # ==========================================
    # PARSE
    # ==========================================

    def parse(self, html):

        if not html:
            return []

        soup = BeautifulSoup(
            html,
            "html.parser"
        )

        results = []
        seen = set()

        # --------------------------------------
        # Strategy 1
        # Current / known Google containers
        # --------------------------------------

        blocks = soup.select(
            "div.MjjYud"
        )

        # --------------------------------------
        # Strategy 2
        # Older Google layout
        # --------------------------------------

        if not blocks:
            blocks = soup.select(
                "div.g"
            )

        # --------------------------------------
        # Strategy 3
        # Generic containers containing h3
        # --------------------------------------

        if not blocks:
            blocks = []

            for h3 in soup.select("h3"):

                parent = h3

                for _ in range(5):

                    if parent.parent is None:
                        break

                    parent = parent.parent

                    if parent.name == "div":

                        if parent.find("a", href=True):
                            blocks.append(parent)
                            break

        # --------------------------------------
        # Parse blocks
        # --------------------------------------

        for block in blocks:

            title_node = block.select_one(
                "h3"
            )

            if not title_node:
                continue

            title = title_node.get_text(
                " ",
                strip=True
            )

            if not title:
                continue

            # ----------------------------------
            # Find result URL
            # ----------------------------------

            link = title_node.find_parent(
                "a",
                href=True
            )

            if not link:

                link = block.select_one(
                    "a[href]"
                )

            if not link:
                continue

            url = self.clean_url(
                link.get("href", "")
            )

            if not url:
                continue

            if url in seen:
                continue

            seen.add(url)

            snippet = self.extract_snippet(
                block
            )

            results.append({

                "title": title,

                "name": title,

                "url": url,

                "snippet": snippet,

                "source": self.name,

            })

        return results

    # ==========================================
    # SNIPPET
    # ==========================================

    def extract_snippet(self, block):

        selectors = (

            ".VwiC3b",

            ".yXK7lf",

            ".kb0PBd",

            "[data-sncf]",

            ".IsZvec",

            ".aCOpRe",

        )

        for selector in selectors:

            node = block.select_one(
                selector
            )

            if node:

                text = node.get_text(
                    " ",
                    strip=True
                )

                if text:
                    return text

        # --------------------------------------
        # Generic fallback
        # --------------------------------------

        text = block.get_text(
            " ",
            strip=True
        )

        if not text:
            return ""

        title = block.select_one("h3")

        if title:

            title_text = title.get_text(
                " ",
                strip=True
            )

            if title_text:

                text = text.replace(
                    title_text,
                    "",
                    1
                ).strip()

        return text[:1000]

    # ==========================================
    # URL CLEANER
    # ==========================================

    def clean_url(self, url):

        if not url:
            return None

        url = url.strip()

        if not url:
            return None

        # --------------------------------------
        # Google /url redirect
        # --------------------------------------

        if url.startswith("/url?"):

            try:

                parsed = urlparse(url)

                params = parse_qs(
                    parsed.query
                )

                target = (
                    params.get("q")
                    or
                    params.get("url")
                )

                if target:
                    url = unquote(
                        target[0]
                    )
                else:
                    return None

            except (
                ValueError,
                TypeError
            ):
                return None

        # --------------------------------------
        # Google encoded redirect
        # --------------------------------------

        if url.startswith(
            "https://www.google.com/url?"
        ):

            try:

                parsed = urlparse(url)

                params = parse_qs(
                    parsed.query
                )

                target = (
                    params.get("q")
                    or
                    params.get("url")
                )

                if target:
                    url = unquote(
                        target[0]
                    )
                else:
                    return None

            except (
                ValueError,
                TypeError
            ):
                return None

        # --------------------------------------
        # Protocol
        # --------------------------------------

        if not url.startswith(
            (
                "http://",
                "https://"
            )
        ):

            return None

        try:

            parsed = urlparse(url)

            hostname = (
                parsed.hostname
                or ""
            ).lower()

        except (
            ValueError,
            TypeError
        ):

            return None

        # --------------------------------------
        # Reject Google internal links
        # --------------------------------------

        if (
            "google." in hostname
            or
            hostname.startswith("webcache.")
        ):
            return None

        return url

    # ==========================================
    # HEALTH CHECK
    # ==========================================

    def health_check(self):

        try:

            response = self.session.get(
                self.BASE_URL,
                params={
                    "q": "test",
                    "hl": "fa",
                    "num": 1,
                },
                timeout=self.timeout
            )

            return (
                response.status_code < 500
                and
                bool(response.text)
            )

        except requests.RequestException:

            return False