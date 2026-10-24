"""Cached, streaming downloads with retries.

Every source here is a bulk file (frequency lists, Wiktionary dumps, Tatoeba
exports), some of them hundreds of MB, so downloads stream to disk instead of
going through memory. Files are cached by URL in ``data_cache/`` and reused
while fresher than ``max_age``; an interrupted download leaves only a
``.part`` file behind, never a truncated cache entry.
"""

from __future__ import annotations

import atexit
import hashlib
import os
import sys
import threading
import time
from datetime import timedelta
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
CACHE_DIR = Path(os.environ.get("WWL_CACHE_DIR", ROOT / "data_cache"))
USER_AGENT = "words-worth-learning/0.1 (build-time data loader; python-httpx)"

# Status codes worth retrying: rate limiting and transient server errors.
RETRY_STATUS = {429, 500, 502, 503, 504}


class NotFound(Exception):
    """The file does not exist."""


def log(*args: object) -> None:
    """Loaders write data to stdout, so all diagnostics must go to stderr."""
    print(*args, file=sys.stderr, flush=True)


def cache_path(url: str) -> Path:
    """Cache file for ``url``: a short hash plus the URL's own file name, so the
    cache directory stays readable (``3f2a…-spa_sentences.tsv.bz2``)."""
    digest = hashlib.sha256(url.encode()).hexdigest()[:12]
    name = url.rstrip("/").rsplit("/", 1)[-1][-80:]
    return CACHE_DIR / "raw" / f"{digest}-{name}"


def cached_path(url: str) -> Path | None:
    """Where ``download`` stored this URL, or None if it was never downloaded."""
    path = cache_path(url)
    return path if path.exists() else None


_client: httpx.Client | None = None
_client_lock = threading.Lock()


def _get_client() -> httpx.Client:
    """One client per process, so downloads from the same host reuse connections."""
    global _client
    with _client_lock:
        if _client is None:
            _client = httpx.Client(follow_redirects=True, headers={"User-Agent": USER_AGENT})
            atexit.register(_client.close)
    return _client


def download(url: str, *, max_age: timedelta | None = timedelta(days=30), retries: int = 5, timeout: float = 120.0) -> Path:
    """Download ``url`` to the cache (unless a fresh copy exists) and return its path.

    ``max_age=None`` caches forever.
    """
    path = cache_path(url)
    if path.exists() and (max_age is None or time.time() - path.stat().st_mtime < max_age.total_seconds()):
        return path

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{threading.get_ident()}.part")
    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            t0 = time.time()
            with _get_client().stream("GET", url, timeout=timeout) as resp:
                if resp.status_code == 404:
                    raise NotFound(f"404 for {url}")
                if resp.status_code in RETRY_STATUS:
                    raise httpx.HTTPStatusError(f"{resp.status_code}", request=resp.request, response=resp)
                resp.raise_for_status()
                size = int(resp.headers.get("Content-Length") or 0)
                log(f"downloading {url}" + (f" ({size / 1e6:,.0f} MB)" if size else ""))
                done, next_report = 0, 100e6
                with tmp.open("wb") as fh:
                    for chunk in resp.iter_bytes(1 << 20):
                        fh.write(chunk)
                        done += len(chunk)
                        if done >= next_report:
                            log(f"  {done / 1e6:,.0f} MB ({time.time() - t0:.0f}s)")
                            next_report += 100e6
            break
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            tmp.unlink(missing_ok=True)
            if attempt == retries:
                raise
            log(f"  retry {attempt}/{retries} for {url} in {delay:.0f}s ({exc})")
            time.sleep(delay)
            delay *= 2

    tmp.replace(path)
    return path
