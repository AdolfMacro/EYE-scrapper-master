from urllib.parse import urlparse


# ==========================================================
# URL NORMALIZER
# ==========================================================

def normalize_url(url):

    if not url:
        return None

    url = url.strip()

    if not url.startswith(
        ("http://", "https://")
    ):
        return None

    parsed = urlparse(url)

    if not parsed.hostname:
        return None

    return url