#!/usr/bin/env python
"""Proves the assembly pipeline works mechanically, with zero API keys and
zero network access. Generates synthetic placeholder clips (ffmpeg lavfi
color/tone sources) matching a manifest's shot structure and Runway's real
duration-tiling constraints, fabricates a timing.json as if narration had
been measured, then runs the real ai_video_pipeline.assemble.assemble()
against them.

Run this before spending anything on Runway/ElevenLabs — if this fails, the
bug is in the ffmpeg pipeline, not in either paid API. Defaults to the
bundled example manifest; pass --manifest to test against your own.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ai_video_pipeline import assemble as assemble_mod
from ai_video_pipeline import manifest as manifest_mod

DEFAULT_MANIFEST = Path(__file__).parent.parent / "examples" / "example_manifest.yaml"
SMOKE_DIR = Path(__file__).parent / "output_smoke"


def make_silent_clip(dest: Path, duration: int, color: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"color=c={color}:s=1280x720:d={duration}:r=24",
         "-pix_fmt", "yuv420p", str(dest)],
        check=True, capture_output=True,
    )


def make_tone_clip(dest: Path, duration: float, freq: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi",
         "-i", f"sine=frequency={freq}:duration={duration}",
         "-c:a", "libmp3lame", str(dest)],
        check=True, capture_output=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args()

    missing = [tool for tool in ("ffmpeg", "ffprobe") if shutil.which(tool) is None]
    if missing:
        print(f"{', '.join(missing)} not found on PATH. Install ffmpeg "
              "(e.g. `brew install ffmpeg`) — it provides both.", file=sys.stderr)
        return 1

    if SMOKE_DIR.exists():
        shutil.rmtree(SMOKE_DIR)
    SMOKE_DIR.mkdir(parents=True)

    manifest = manifest_mod.load_manifest(args.manifest)
    colors = ["0x2a1a00", "0x001a2a", "0x00301a", "0x1a0030", "0x2a2a00",
              "0x00302a", "0x301a00", "0x0a0a0a"]

    timing = {}
    print(f"Fabricating synthetic clips + narration stand-ins for '{manifest.title}' "
          "(no network, no API keys)...")
    for i, shot in enumerate(manifest.shots):
        # Real narration would drift slightly from the manifest's estimate;
        # simulate that so the pipeline is exercised the same way it will be
        # for real, not just on round numbers.
        measured = shot.nominal_duration + (0.4 if i % 2 == 0 else -0.3)
        timing[shot.id] = measured

        durations = manifest_mod.plan_durations(measured)
        for clip_idx, d in enumerate(durations):
            dest = SMOKE_DIR / "clips" / shot.id / f"clip_{clip_idx}.mp4"
            make_silent_clip(dest, d, colors[i % len(colors)])

        narration_dest = SMOKE_DIR / "narration" / f"{shot.id}.mp3"
        make_tone_clip(narration_dest, measured, freq=220 + i * 40)
        print(f"  {shot.id}: {len(durations)} clip(s) {durations} -> measured {measured:.2f}s")

    (SMOKE_DIR / "timing.json").write_text(json.dumps(timing, indent=2))

    print("\nRunning the real assembly pipeline against the synthetic assets...")
    final = assemble_mod.assemble(args.manifest, SMOKE_DIR)

    proc = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(final)],
        capture_output=True, text=True, check=True,
    )
    actual_duration = float(proc.stdout.strip())
    expected_duration = sum(timing.values())
    drift = abs(actual_duration - expected_duration)

    print(f"\nAssembled: {final}")
    print(f"Expected duration (sum of measured shot durations): {expected_duration:.2f}s")
    print(f"Actual final video duration: {actual_duration:.2f}s")

    if drift > 0.5:
        print(f"FAIL: duration drift {drift:.2f}s exceeds 0.5s tolerance", file=sys.stderr)
        return 1
    if final.stat().st_size < 10_000:
        print(f"FAIL: output suspiciously small ({final.stat().st_size} bytes)", file=sys.stderr)
        return 1
    print("PASS: pipeline is mechanically correct end to end.")
    print(f"\n(Synthetic test assets left at {SMOKE_DIR} for inspection; safe to delete.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
