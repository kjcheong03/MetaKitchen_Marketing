"""
HeyGen API client.

Default flow (trained avatar):
  generate_video(avatar_id, script, scene_prompt, ...) -> video_id
  poll_until_done(video_id)                            -> data dict with video_url
  download_video(video_url, dest)                      -> local MP4

Legacy flow (talking_photo) is still available via upload_talking_photo().

Auth: X-Api-Key header.
"""

import asyncio
import hashlib
import json
from pathlib import Path
from typing import Callable, Optional

import httpx

from .config import (
    HEYGEN_API_KEY,
    HEYGEN_AVATAR_ID,
    HEYGEN_BASE,
    HEYGEN_HEIGHT,
    HEYGEN_SCENE_PROMPT,
    HEYGEN_UPLOAD_BASE,
    HEYGEN_VOICE_ID,
    HEYGEN_WIDTH,
    TALKING_PHOTO_CACHE,
)

_API_HEADERS = {
    "X-Api-Key": HEYGEN_API_KEY,
    "Content-Type": "application/json",
    "Accept": "application/json",
}


# ---------- legacy: talking-photo upload (kept for fallback) ----------

def _cache_key(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.resolve()}::{stat.st_mtime_ns}::{stat.st_size}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _read_cache() -> dict:
    if TALKING_PHOTO_CACHE.exists():
        try:
            return json.loads(TALKING_PHOTO_CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _write_cache(cache: dict) -> None:
    TALKING_PHOTO_CACHE.parent.mkdir(parents=True, exist_ok=True)
    TALKING_PHOTO_CACHE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def _content_type_for(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "image/jpeg"
    if ext == ".png":
        return "image/png"
    raise ValueError(f"Unsupported image type: {ext}. Use PNG or JPG.")


async def upload_talking_photo(path: Path) -> str:
    """[Legacy] Upload an image to HeyGen and return its talking_photo_id.
    Not used when HEYGEN_AVATAR_ID is set — the trained avatar is used instead."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Image not found: {path}")

    cache = _read_cache()
    key = _cache_key(path)
    if key in cache:
        return cache[key]

    content_type = _content_type_for(path)
    data = path.read_bytes()
    headers = {"X-Api-Key": HEYGEN_API_KEY, "Content-Type": content_type}
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            f"{HEYGEN_UPLOAD_BASE}/v1/talking_photo",
            headers=headers,
            content=data,
        )
        if r.status_code >= 400:
            raise RuntimeError(
                f"HeyGen talking_photo upload failed ({r.status_code}): {r.text[:2000]}"
            )
        body = r.json()

    tp_id = body.get("data", {}).get("talking_photo_id")
    if not tp_id:
        raise RuntimeError(f"No talking_photo_id in response: {body}")

    cache[key] = tp_id
    _write_cache(cache)
    return tp_id


# ---------- video generation (trained avatar) ----------

async def generate_video(
    script: str,
    avatar_id: Optional[str] = None,
    scene_prompt: Optional[str] = None,
    background: Optional[dict] = None,
    voice_id: Optional[str] = None,
    width: int = HEYGEN_WIDTH,
    height: int = HEYGEN_HEIGHT,
    title: str = "Dr Aara Reel",
) -> str:
    """Submit a video-generation job using a trained avatar. Returns video_id."""
    character: dict = {
        "type": "avatar",
        "avatar_id": avatar_id or HEYGEN_AVATAR_ID,
        "avatar_style": "normal",
        "scale": 1.0,
        # Lift head slightly above Instagram's bottom UI (caption bar, like button).
        "offset": {"x": 0.0, "y": -0.05},
        # NOTE: matting is off because this is a video-trained avatar — its baked-in
        # set should show through. Matting here would force per-frame alpha synthesis
        # over the trained background and introduce edge artifacts.
        "matting": False,
    }
    if scene_prompt:
        # HeyGen uses this only on Avatar IV / photo-avatar-groups; harmless otherwise.
        character["prompt"] = scene_prompt

    video_input: dict = {
        "character": character,
        "voice": {
            "type": "text",
            "voice_id": voice_id or HEYGEN_VOICE_ID,
            "input_text": script,
            "speed": 1.0,
            "emotion": "Friendly",
        },
    }
    if background is not None:
        video_input["background"] = background

    payload = {
        "title": title,
        "video_inputs": [video_input],
        "dimension": {"width": width, "height": height},
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{HEYGEN_BASE}/v2/video/generate",
            headers=_API_HEADERS,
            json=payload,
        )
        if r.status_code >= 400:
            raise RuntimeError(
                f"HeyGen generate failed ({r.status_code}): {r.text[:2000]}"
            )
        body = r.json()

    video_id = body.get("data", {}).get("video_id")
    if not video_id:
        raise RuntimeError(f"No video_id in response: {body}")
    return video_id


async def poll_until_done(
    video_id: str,
    on_update: Optional[Callable[[dict], None]] = None,
    interval_seconds: float = 5.0,
    timeout_seconds: float = 900.0,
) -> dict:
    terminal_ok = {"completed"}
    terminal_bad = {"failed"}

    elapsed = 0.0
    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            r = await client.get(
                f"{HEYGEN_BASE}/v1/video_status.get",
                headers={"X-Api-Key": HEYGEN_API_KEY},
                params={"video_id": video_id},
            )
            r.raise_for_status()
            body = r.json()
            data = body.get("data", {}) or {}
            status = (data.get("status") or "").lower()

            if on_update:
                try:
                    on_update(data)
                except Exception:
                    pass

            if status in terminal_ok:
                return data
            if status in terminal_bad:
                raise RuntimeError(
                    f"HeyGen video ended with status '{status}': {data}"
                )

            if elapsed >= timeout_seconds:
                raise TimeoutError(
                    f"HeyGen job timed out after {timeout_seconds}s (last status: {status})"
                )

            await asyncio.sleep(interval_seconds)
            elapsed += interval_seconds


async def download_video(video_url: str, dest: Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=180.0) as client:
        async with client.stream("GET", video_url) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                async for chunk in r.aiter_bytes():
                    f.write(chunk)
    return dest


# ---------- convenience: end-to-end ----------

async def render(
    script: str,
    output_path: Path,
    avatar_id: Optional[str] = None,
    scene_prompt: Optional[str] = None,
    background: Optional[dict] = None,
    voice_id: Optional[str] = None,
    width: int = HEYGEN_WIDTH,
    height: int = HEYGEN_HEIGHT,
    on_update: Optional[Callable[[dict], None]] = None,
    title: str = "Dr Aara Reel",
) -> Path:
    video_id = await generate_video(
        script=script,
        avatar_id=avatar_id,
        scene_prompt=scene_prompt or HEYGEN_SCENE_PROMPT,
        background=background,
        voice_id=voice_id,
        width=width,
        height=height,
        title=title,
    )
    final = await poll_until_done(video_id, on_update=on_update)
    video_url = final.get("video_url")
    if not video_url:
        raise RuntimeError(f"Completed but no video_url in payload: {final}")
    return await download_video(video_url, output_path)
