"""
Upload a local image to a public URL so Higgsfield can fetch it.
Uses tmpfiles.org (anonymous, no auth). Caches the result per-file
(keyed by absolute path + mtime) so we don't re-upload on every run.
"""

import hashlib
import json
from pathlib import Path

import httpx

from .config import IMAGE_URL_CACHE


def _cache_key(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.resolve()}::{stat.st_mtime_ns}::{stat.st_size}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _read_cache() -> dict:
    if IMAGE_URL_CACHE.exists():
        try:
            return json.loads(IMAGE_URL_CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _write_cache(cache: dict) -> None:
    IMAGE_URL_CACHE.parent.mkdir(parents=True, exist_ok=True)
    IMAGE_URL_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def upload_to_public_url(path: Path) -> str:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    cache = _read_cache()
    key = _cache_key(path)
    if key in cache:
        return cache[key]

    with open(path, "rb") as f:
        files = {"file": (path.name, f, "application/octet-stream")}
        r = httpx.post("https://tmpfiles.org/api/v1/upload", files=files, timeout=60.0)
    r.raise_for_status()
    data = r.json()
    display_url = data["data"]["url"]
    direct_url = display_url.replace("tmpfiles.org/", "tmpfiles.org/dl/")

    cache[key] = direct_url
    _write_cache(cache)
    return direct_url
