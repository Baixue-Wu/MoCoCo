"""Background stage runs. One thread per job, log captured, status polled by the UI."""

from __future__ import annotations

import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field


@dataclass
class Job:
    id: str
    project: str
    stage: str
    status: str = "running"  # running | done | failed
    started: float = field(default_factory=time.time)
    finished: float | None = None
    error: str | None = None
    result: object = None


class Jobs:
    def __init__(self):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def start(self, project: str, stage: str, fn) -> Job:
        with self._lock:
            for j in self._jobs.values():
                if j.project == project and j.status == "running":
                    raise RuntimeError(f"project {project} already has {j.stage} running (job {j.id})")
            job = Job(id=uuid.uuid4().hex[:12], project=project, stage=stage)
            self._jobs[job.id] = job

        def run():
            try:
                job.result = fn()
                job.status = "done"
            except Exception as e:  # noqa: BLE001
                job.status = "failed"
                job.error = f"{e}\n\n{traceback.format_exc()[-3000:]}"
            finally:
                job.finished = time.time()

        threading.Thread(target=run, daemon=True, name=f"job-{job.id}").start()
        return job

    def get(self, job_id: str) -> Job:
        if job_id not in self._jobs:
            raise KeyError(f"no job {job_id}")
        return self._jobs[job_id]

    def for_project(self, project: str) -> list[Job]:
        return sorted((j for j in self._jobs.values() if j.project == project), key=lambda j: -j.started)
