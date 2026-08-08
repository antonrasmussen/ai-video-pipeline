#!/usr/bin/env python
"""Minimal Runway ML REST client: submit text-to-video tasks, poll, download.

Talks directly to the documented REST endpoints (no SDK dependency, one
fewer thing to pin). Requires RUNWAY_API_KEY in the environment.

Endpoints (Runway API, version 2024-11-06):
  POST /v1/text_to_video   -> {"id": "..."}
  GET  /v1/tasks/{id}      -> {"status": "...", "output": ["<url>", ...]}

Valid `duration` values are 5, 8, or 10 seconds — there is no larger single
generation. Covering a longer shot means tiling multiple generations and
concatenating them in assembly (see planning.plan_durations).
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import requests

BASE_URL = os.environ.get("RUNWAY_API_BASE", "https://api.dev.runwayml.com")
API_VERSION = "2024-11-06"
VALID_DURATIONS = (5, 8, 10)


class RunwayError(RuntimeError):
    pass


def _headers() -> dict:
    key = os.environ.get("RUNWAY_API_KEY")
    if not key:
        raise RunwayError("RUNWAY_API_KEY is not set")
    return {
        "Authorization": f"Bearer {key}",
        "X-Runway-Version": API_VERSION,
        "Content-Type": "application/json",
    }


def submit_text_to_video(
    prompt: str,
    duration: int,
    ratio: str = "1280:720",
    model: str = "gen4.5",
    seed: int | None = None,
) -> str:
    """Submit a generation task; returns the task id."""
    if duration not in VALID_DURATIONS:
        raise RunwayError(f"duration must be one of {VALID_DURATIONS}, got {duration}")
    body: dict = {"model": model, "promptText": prompt, "ratio": ratio, "duration": duration}
    if seed is not None:
        body["seed"] = seed
    resp = requests.post(f"{BASE_URL}/v1/text_to_video", headers=_headers(), json=body, timeout=30)
    if resp.status_code >= 400:
        raise RunwayError(f"submit failed ({resp.status_code}): {resp.text[:500]}")
    task_id = resp.json().get("id")
    if not task_id:
        raise RunwayError(f"no task id in response: {resp.text[:500]}")
    return task_id


def poll_task(task_id: str, timeout_seconds: int = 600, interval_seconds: int = 5) -> str:
    """Block until the task succeeds; return the output video URL."""
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        resp = requests.get(f"{BASE_URL}/v1/tasks/{task_id}", headers=_headers(), timeout=30)
        if resp.status_code >= 400:
            raise RunwayError(f"poll failed ({resp.status_code}): {resp.text[:500]}")
        data = resp.json()
        status = data.get("status")
        if status == "SUCCEEDED":
            output = data.get("output") or []
            if not output:
                raise RunwayError(f"task {task_id} succeeded with no output field")
            return output[0]
        if status in ("FAILED", "CANCELLED"):
            raise RunwayError(f"task {task_id} ended with status {status}: {data.get('failure')}")
        time.sleep(interval_seconds)
    raise RunwayError(f"task {task_id} did not finish within {timeout_seconds}s")


def download(url: str, dest: Path) -> Path:
    """Stream to disk rather than buffering the whole clip in memory —
    Runway clips are small individually but this pipeline downloads many."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, timeout=180, stream=True) as resp:
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                if chunk:
                    f.write(chunk)
    return dest


def generate_clip(prompt: str, duration: int, dest: Path, **kwargs) -> Path:
    """Submit, poll, and download one clip. Convenience wrapper for the
    common case; callers needing to submit many clips before polling any
    should call the pieces directly for better throughput."""
    task_id = submit_text_to_video(prompt, duration, **kwargs)
    url = poll_task(task_id)
    return download(url, dest)
