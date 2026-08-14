"""Attempt persistence. Pure stdlib JSON on disk so `down`/`up` resumes work."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path


def attempt_path(state_root: Path, attempt_id: str) -> Path:
    return state_root / f"{attempt_id}.json"


def new_attempt_id() -> str:
    return f"att-{uuid.uuid4().hex[:12]}"


def save(state_root: Path, attempt: dict) -> None:
    state_root.mkdir(parents=True, exist_ok=True)
    path = attempt_path(state_root, attempt["id"])
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as fh:
        json.dump(attempt, fh, indent=2, sort_keys=True)
    os.replace(tmp, path)


def load(state_root: Path, attempt_id: str) -> dict | None:
    path = attempt_path(state_root, attempt_id)
    if not path.is_file():
        return None
    with path.open() as fh:
        return json.load(fh)


def list_attempts(state_root: Path) -> list[dict]:
    if not state_root.is_dir():
        return []
    out = []
    for f in state_root.glob("att-*.json"):
        try:
            with f.open() as fh:
                out.append(json.load(fh))
        except (OSError, json.JSONDecodeError):
            continue
    out.sort(key=lambda a: a.get("started_at", 0), reverse=True)
    return out


def seconds_remaining(attempt: dict, now: float | None = None) -> int:
    now = now or time.time()
    if attempt.get("mode") == "training" or not attempt.get("duration_seconds"):
        return -1  # untimed
    deadline = attempt.get("started_at", now) + attempt["duration_seconds"]
    return max(0, int(deadline - now))
