"""
Orchestrates the end-to-end pipeline:
  auto mode:   topic -> script -> HeyGen video
  manual mode: image + user prompt (becomes spoken script) -> HeyGen video
"""

import asyncio
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import OUT_DIR, pick_background, pick_scene_prompt
from .gemini_client import generate_reel, pick_trending_topic
from .heygen_client import render
from .jobs import Job


def _slugify(text: str, max_words: int = 6) -> str:
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text).strip().lower()
    words = text.split()[:max_words]
    return "-".join(words) or "reel"


def _make_output_dir(slug: str) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    base = OUT_DIR / f"{today}_{slug}"
    if base.exists():
        base = OUT_DIR / f"{today}_{slug}_{uuid.uuid4().hex[:6]}"
    base.mkdir(parents=True, exist_ok=True)
    return base


async def run_auto(job: Job, seed_themes: Optional[list[str]] = None) -> None:
    try:
        job.update(stage="picking_topic", progress=5)
        topic_data = await asyncio.to_thread(pick_trending_topic, seed_themes)
        job.update(topic=topic_data, progress=15)

        job.update(stage="writing_script", progress=25)
        reel = await asyncio.to_thread(
            generate_reel,
            topic_data["topic"],
            topic_data.get("search_notes", ""),
        )
        job.update(reel=reel, progress=45)

        slug = reel.get("title_slug") or _slugify(reel["topic"])
        out_dir = _make_output_dir(slug)
        video_path = out_dir / "video.mp4"

        scene = pick_scene_prompt()
        bg = pick_background()
        job.update(
            stage="generating_video",
            progress=60,
            output_dir=str(out_dir),
            scene_prompt=scene,
        )
        await render(
            script=reel["script"],
            scene_prompt=scene,
            background=bg,
            output_path=video_path,
            title=f"Dr Aara — {reel.get('topic', 'Reel')[:60]}",
            on_update=lambda s: job.update(heygen_status=s.get("status")),
        )

        post = {
            "topic": reel["topic"],
            "hook_pattern": reel.get("hook_pattern", ""),
            "hook": reel["hook"],
            "script": reel["script"],
            "caption": reel["caption"],
            "hashtags": reel["hashtags"],
            "compliance_check": reel["compliance_check"],
            "source_topic_notes": topic_data.get("search_notes", ""),
        }
        (out_dir / "post.json").write_text(json.dumps(post, indent=2), encoding="utf-8")
        (out_dir / "script.txt").write_text(reel["script"], encoding="utf-8")

        job.update(
            stage="done",
            progress=100,
            status="succeeded",
            video_path=str(video_path),
            post=post,
        )
    except Exception as e:
        job.update(stage="error", status="failed", error=str(e))
        raise


async def run_manual(
    job: Job,
    script: str,
    scene_prompt: Optional[str] = None,
    image_path: Optional[Path] = None,  # accepted for API compat; ignored now
    aspect_ratio: Optional[str] = None,
    resolution: Optional[str] = None,
) -> None:
    """Manual mode: user-provided script (and optional scene prompt).
    The trained Dr Aara avatar speaks the script verbatim."""
    try:
        slug = _slugify(script)
        out_dir = _make_output_dir(slug or "manual")
        video_path = out_dir / "video.mp4"

        scene = scene_prompt or pick_scene_prompt()
        bg = pick_background()
        job.update(
            stage="generating_video",
            progress=30,
            output_dir=str(out_dir),
            scene_prompt=scene,
        )
        await render(
            script=script,
            scene_prompt=scene,
            background=bg,
            output_path=video_path,
            title="Dr Aara — Manual",
            on_update=lambda s: job.update(heygen_status=s.get("status")),
        )

        post = {"mode": "manual", "script": script, "scene_prompt": scene}
        (out_dir / "post.json").write_text(json.dumps(post, indent=2), encoding="utf-8")

        job.update(
            stage="done",
            progress=100,
            status="succeeded",
            video_path=str(video_path),
            post=post,
        )
    except Exception as e:
        job.update(stage="error", status="failed", error=str(e))
        raise
