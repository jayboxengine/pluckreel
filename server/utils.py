import re
import time
from collections import defaultdict, deque
from urllib.parse import urlparse

ALLOWED_HOSTS = {
    "youtube.com", "youtu.be",
    "linkedin.com",
    "facebook.com", "fb.watch",
    "instagram.com",
    "tiktok.com",
    "vimeo.com",
    "twitter.com", "x.com",
}


def is_allowed_url(url: str) -> bool:
    """True if url is http(s) on one of the supported platforms (any subdomain)."""
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    return any(host == h or host.endswith("." + h) for h in ALLOWED_HOSTS)


def safe_filename(name: str, ext: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\r\n\t]+', "", name).strip() or "video"
    ext = re.sub(r"[^\w]", "", ext) or "mp4"
    return f"{name[:120]}.{ext}"


class RateLimiter:
    """In-memory sliding-window limiter; fine for a single low-traffic process."""

    def __init__(self, limit: int, window: float):
        self.limit = limit
        self.window = window
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True
