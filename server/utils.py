import os
import re
import secrets
import threading
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


class Blocklist:
    """Links blocked after a copyright/abuse report. One entry per line in a text file: a video ID
    (e.g. dQw4w9WgXcQ) or any other piece of the URL; a link is blocked if it contains an entry.
    Lines starting with # are comments. The file is re-read whenever it changes, no restart needed."""

    def __init__(self, path):
        self.path = path
        self.mtime = None
        self.entries: list[str] = []
        self.lock = threading.Lock()

    def _load(self):
        try:
            mtime = os.path.getmtime(self.path)
        except OSError:
            self.mtime, self.entries = None, []
            return
        if mtime != self.mtime:
            with open(self.path, encoding="utf-8") as f:
                lines = (line.split("#", 1)[0].strip() for line in f)
                self.entries = [line for line in lines if len(line) >= 4]
            self.mtime = mtime

    def is_blocked(self, url: str) -> bool:
        with self.lock:
            self._load()
            return any(e in url for e in self.entries)


class RateLimiter:
    """In-memory sliding-window limiter for a single process. Thread-safe, and forgets idle IPs."""

    def __init__(self, limit: int, window: float):
        self.limit = limit
        self.window = window
        self.hits: dict[str, deque] = defaultdict(deque)
        self.lock = threading.Lock()
        self.last_sweep = time.monotonic()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self.lock:
            if now - self.last_sweep > self.window:
                for k in [k for k, q in self.hits.items() if not q or now - q[-1] > self.window]:
                    del self.hits[k]
                self.last_sweep = now
            q = self.hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True


class DownloadSlots:
    """Caps concurrent downloads, overall and per IP.

    A slot is reserved when the page asks for a download ticket, so "server busy" can be shown
    as a normal error instead of a failed browser download. The ticket is single-use; the slot
    becomes active when the stream starts and is freed when it ends. Reservations whose stream
    never starts (ticket unused, or client gone before the first byte) expire after `ttl`.
    """

    def __init__(self, total: int, per_ip: int, ttl: float = 60):
        self.total = total
        self.per_ip = per_ip
        self.ttl = ttl
        self.lock = threading.Lock()
        self.slots: dict[str, dict] = {}  # token -> {ip, job, state, at}

    def _purge(self, now: float):
        for t in [t for t, s in self.slots.items() if s["state"] != "active" and now - s["at"] > self.ttl]:
            del self.slots[t]

    def reserve(self, ip: str, job: dict) -> tuple[str | None, str | None]:
        """Returns (token, None) or (None, reason) where reason is 'busy' or 'per_ip'."""
        now = time.monotonic()
        with self.lock:
            self._purge(now)
            if sum(s["ip"] == ip for s in self.slots.values()) >= self.per_ip:
                return None, "per_ip"
            if len(self.slots) >= self.total:
                return None, "busy"
            token = secrets.token_urlsafe(18)
            self.slots[token] = {"ip": ip, "job": job, "state": "reserved", "at": now}
            return token, None

    def claim(self, token: str) -> dict | None:
        """Single-use: returns the job for a fresh ticket, else None."""
        with self.lock:
            self._purge(time.monotonic())
            s = self.slots.get(token)
            if not s or s["state"] != "reserved":
                return None
            s["state"] = "claimed"
            return s["job"]

    def start(self, token: str):
        with self.lock:
            if token in self.slots:
                self.slots[token]["state"] = "active"

    def release(self, token: str):
        with self.lock:
            self.slots.pop(token, None)
