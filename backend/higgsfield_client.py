"""
Higgsfield API client. Submits a Seedance image-to-video job, polls status,
and downloads the resulting MP4.

Auth format (per Higgsfield docs): Authorization: Key {api_key}:{api_secret}
Base URL: https://platform.higgsfield.ai
Async: POST returns request_id; poll status_url until status is completed.
"""

import asyncio
from pathlib import Path
from typing import Callable, Optional

import httpx

from .config import HIGGSFIELD_AUTH, HIGGSFIELD_BASE

SEEDANCE_ENDPOINT = "/bytedance/seedance/v1/pro/image-to-video"

_HEADERS = {
    "Authorization": HIGGSFIELD_AUTH,
    "Content-Type": "application/json",
    "Accept": "application/json",
}


async def submit_seedance(
    image_url: str,
    prompt: str,
    aspect_ratio: Optional[str] = None,
    resolution: Optional[str] = None,
    duration: Optional[int] = None,
) -> dict:
    payload: dict = {"image_url": image_url, "prompt": prompt}
    if aspect_ratio is not None:
        payload["aspect_ratio"] = aspect_ratio
    if resolution is not None:
        payload["resolution"] = resolution
    if duration is not None:
        payload["duration"] = duration

    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(
            f"{HIGGSFIELD_BASE}{SEEDANCE_ENDPOINT}",
            headers=_HEADERS,
            json=payload,
        )
        if r.status_code >= 400:
            body = r.text
            raise RuntimeError(
                f"Higgsfield submit failed ({r.status_code}). "
                f"Payload sent: {payload}. Response body: {body[:2000]}"
            )
        return r.json()


async def poll_until_done(
    status_url: str,
    on_update: Optional[Callable[[dict], None]] = None,
    interval_seconds: float = 5.0,
    timeout_seconds: float = 900.0,
) -> dict:
    """Poll the status URL until the job reaches a terminal state.
    Returns the final status payload (which contains video.url on success).
    Raises RuntimeError on failed / nsfw / cancelled."""
    terminal_ok = {"completed"}
    terminal_bad = {"failed", "nsfw", "cancelled"}

    elapsed = 0.0
    async with httpx.AsyncClient(timeout=60.0) as client:
        while True:
            r = await client.get(status_url, headers=_HEADERS)
            r.raise_for_status()
            data = r.json()
            status = (data.get("status") or "").lower()

            if on_update:
                try:
                    on_update(data)
                except Exception:
                    pass

            if status in terminal_ok:
                return data
            if status in terminal_bad:
                raise RuntimeError(f"Higgsfield job ended with status '{status}': {data}")

            if elapsed >= timeout_seconds:
                raise TimeoutError(f"Higgsfield job timed out after {timeout_seconds}s")

            await asyncio.sleep(interval_seconds)
            elapsed += interval_seconds


async def download_video(video_url: str, dest: Path) -> Path:
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream("GET", video_url) as r:
            r.raise_for_status()
            with open(dest, "wb") as f:
                async for chunk in r.aiter_bytes():
                    f.write(chunk)
    return dest


def _status_url_from_submit(submit_response: dict) -> str:
    """Submit response may include status_url directly, or just request_id."""
    if "status_url" in submit_response:
        return submit_response["status_url"]
    request_id = submit_response.get("request_id") or submit_response.get("id")
    if not request_id:
        raise ValueError(f"No status_url or request_id in response: {submit_response}")
    return f"{HIGGSFIELD_BASE}/requests/{request_id}/status"


def _video_url_from_status(status_payload: dict) -> str:
    """Final status payload contains the video URL. Supports a few shapes."""
    if "video" in status_payload and isinstance(status_payload["video"], dict):
        if "url" in status_payload["video"]:
            return status_payload["video"]["url"]
    if "result" in status_payload and isinstance(status_payload["result"], dict):
        res = status_payload["result"]
        if "video" in res and isinstance(res["video"], dict) and "url" in res["video"]:
            return res["video"]["url"]
        if "url" in res:
            return res["url"]
    if "url" in status_payload:
        return status_payload["url"]
    raise ValueError(f"Could not find video URL in status payload: {status_payload}")


async def generate_video(
    image_url: str,
    prompt: str,
    output_path: Path,
    aspect_ratio: Optional[str] = None,
    resolution: Optional[str] = None,
    duration: Optional[int] = None,
    on_update: Optional[Callable[[dict], None]] = None,
) -> Path:
    """End-to-end: submit → poll → download. Returns the local MP4 path."""
    submit = await submit_seedance(
        image_url=image_url,
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        resolution=resolution,
        duration=duration,
    )
    status_url = _status_url_from_submit(submit)
    final = await poll_until_done(status_url, on_update=on_update)
    video_url = _video_url_from_status(final)
    return await download_video(video_url, output_path)
