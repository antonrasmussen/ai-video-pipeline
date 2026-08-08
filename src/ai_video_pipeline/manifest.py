"""Pure, network-free manifest loading and Runway clip-tiling logic. Kept
separate from the API clients so it can be unit-tested without hitting any
network.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import product
from pathlib import Path

import yaml

VALID_DURATIONS = (5, 8, 10)


@dataclass
class Shot:
    id: str
    start: float
    end: float
    nominal_duration: float
    visual_prompt: str
    on_screen_text: str
    narration: str
    sfx_cues: list[str]


@dataclass
class Manifest:
    title: str
    target_runtime_seconds: float
    aspect_ratio: str
    video_model: str
    shots: list[Shot]


def load_manifest(path: Path) -> Manifest:
    doc = yaml.safe_load(Path(path).read_text())
    shots = [
        Shot(
            id=s["id"], start=s["start"], end=s["end"], nominal_duration=s["nominal_duration"],
            visual_prompt=" ".join(s["visual_prompt"].split()),
            on_screen_text=s["on_screen_text"],
            narration=" ".join(s["narration"].split()),
            sfx_cues=s.get("sfx_cues", []),
        )
        for s in doc["shots"]
    ]
    return Manifest(
        title=doc["title"], target_runtime_seconds=doc["target_runtime_seconds"],
        aspect_ratio=doc["aspect_ratio"], video_model=doc["video_model"], shots=shots,
    )


def plan_durations(target_seconds: float, max_clips: int = 4) -> list[int]:
    """Return a list of Runway-valid durations (each in {5, 8, 10}) whose sum
    covers `target_seconds` with the least wasted (trimmed) footage, breaking
    ties toward fewer clips. Brute force over a small combination space —
    correct and cheap for the clip counts a typical shot needs."""
    target = math.ceil(target_seconds)
    best: tuple[tuple[int, int], list[int]] | None = None
    for n in range(1, max_clips + 1):
        for combo in product(VALID_DURATIONS, repeat=n):
            total = sum(combo)
            if total >= target:
                key = (total - target, n)
                if best is None or key < best[0]:
                    best = (key, list(combo))
        if best is not None and best[0][0] == 0:
            break  # exact cover found at this clip count; more clips can't beat it
    if best is None:
        raise ValueError(f"cannot cover {target}s within {max_clips} clips of {VALID_DURATIONS}")
    return best[1]


def generation_plan(manifest: Manifest, use_measured: dict[str, float] | None = None) -> list[dict]:
    """One row per Runway clip to generate, across all shots. `use_measured`
    maps shot id -> measured narration seconds (from synth-narration output);
    falls back to the manifest's nominal_duration estimate when absent."""
    use_measured = use_measured or {}
    rows = []
    for shot in manifest.shots:
        target = use_measured.get(shot.id, shot.nominal_duration)
        durations = plan_durations(target)
        for i, d in enumerate(durations):
            rows.append({
                "shot_id": shot.id, "clip_index": i, "n_clips": len(durations),
                "duration": d, "target_seconds": target, "prompt": shot.visual_prompt,
            })
    return rows


def format_plan_summary(rows: list[dict]) -> str:
    lines = []
    total_generated = 0
    by_shot: dict[str, list[dict]] = {}
    for row in rows:
        by_shot.setdefault(row["shot_id"], []).append(row)
    for shot_id, shot_rows in by_shot.items():
        durations = [r["duration"] for r in shot_rows]
        target = shot_rows[0]["target_seconds"]
        total_generated += sum(durations)
        lines.append(
            f"  {shot_id}: target {target:.1f}s -> {len(durations)} clip(s) "
            f"{durations} = {sum(durations)}s generated, trimmed to {target:.1f}s"
        )
    lines.append(f"\nTotal clips: {len(rows)}   Total generated seconds: {total_generated}")
    return "\n".join(lines)
