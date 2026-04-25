"""Simple in-memory job registry. Prototype-scale; not persistent."""

import threading
import uuid
from typing import Any


class Job:
    def __init__(self, mode: str) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.mode = mode
        self.status = "running"
        self.stage = "queued"
        self.progress = 0
        self.error: str | None = None
        self.video_path: str | None = None
        self.output_dir: str | None = None
        self.topic: dict | None = None
        self.reel: dict | None = None
        self.post: dict | None = None
        self.heygen_status: str | None = None
        self.scene_prompt: str | None = None
        self._lock = threading.Lock()

    def update(self, **fields: Any) -> None:
        with self._lock:
            for k, v in fields.items():
                setattr(self, k, v)

    def to_dict(self) -> dict:
        with self._lock:
            return {
                "id": self.id,
                "mode": self.mode,
                "status": self.status,
                "stage": self.stage,
                "progress": self.progress,
                "error": self.error,
                "video_path": self.video_path,
                "output_dir": self.output_dir,
                "topic": self.topic,
                "reel": self.reel,
                "post": self.post,
                "heygen_status": self.heygen_status,
                "scene_prompt": self.scene_prompt,
            }


class JobRegistry:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, mode: str) -> Job:
        job = Job(mode)
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)


jobs = JobRegistry()
