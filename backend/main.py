"""FastAPI app. Run from the project root:
    uvicorn backend.main:app --reload --port 8000
"""

import asyncio
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import ASSETS_DIR, OUT_DIR
from .jobs import jobs
from .pipeline import run_auto, run_manual

app = FastAPI(title="MetaKitchen Marketing Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static/out", StaticFiles(directory=str(OUT_DIR)), name="out")
app.mount("/static/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

UPLOAD_DIR = OUT_DIR / "_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/api/health")
async def health() -> dict:
    return {"ok": True}


@app.post("/api/generate/auto")
async def generate_auto(background: BackgroundTasks) -> dict:
    job = jobs.create(mode="auto")
    background.add_task(_runner_auto, job.id)
    return {"job_id": job.id}


@app.post("/api/generate/manual")
async def generate_manual(
    background: BackgroundTasks,
    script: str = Form(...),
    scene_prompt: str = Form(""),
) -> dict:
    job = jobs.create(mode="manual")
    background.add_task(_runner_manual, job.id, script, scene_prompt or None)
    return {"job_id": job.id}


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> dict:
    job = jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    data = job.to_dict()
    if data.get("video_path"):
        data["video_download_url"] = f"/api/jobs/{job_id}/video"
    return data


@app.get("/api/jobs/{job_id}/video")
async def download_video(job_id: str):
    job = jobs.get(job_id)
    if job is None or not job.video_path:
        raise HTTPException(status_code=404, detail="Video not ready")
    path = Path(job.video_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Video file missing")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=path.name,
    )


def _runner_auto(job_id: str) -> None:
    job = jobs.get(job_id)
    if job is None:
        return
    asyncio.run(run_auto(job))


def _runner_manual(
    job_id: str, script: str, scene_prompt: Optional[str]
) -> None:
    job = jobs.get(job_id)
    if job is None:
        return
    asyncio.run(
        run_manual(
            job,
            script=script,
            scene_prompt=scene_prompt,
        )
    )
