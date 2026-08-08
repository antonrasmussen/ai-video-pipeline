"""Assembles the final video from generated clips + narration audio via
ffmpeg. Pure network-free — everything it needs must already exist under
the output directory (from `cli.py`'s synth-narration + generate-video
steps, or a test's synthetic stand-ins).

Per shot: concatenate that shot's Runway clip(s) (video only, Runway's own
audio track is dropped — final audio comes from narration + SFX, not the
generated footage), trim to the shot's measured target duration, burn in the
on-screen text. Then concatenate all shots into one video track, concatenate
all narration clips into one audio track (these now match in length because
video was trimmed to the same measured durations narration produced), and mux.

Command-building is split into pure functions (`build_*`) that return argv
lists, so the logic is testable without actually invoking ffmpeg.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from . import manifest as manifest_mod
from . import text_overlay


def build_concat_trim_cmd(clip_paths: list[Path], target_seconds: float, dest: Path) -> list[str]:
    n = len(clip_paths)
    inputs: list[str] = []
    for p in clip_paths:
        inputs += ["-i", str(p)]
    streams = "".join(f"[{i}:v:0]" for i in range(n))
    filter_complex = f"{streams}concat=n={n}:v=1:a=0[catv];[catv]trim=0:{target_seconds}[outv]"
    return [
        "ffmpeg", "-y", *inputs,
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-an", str(dest),
    ]


def build_overlay_cmd(
    src: Path, text_png: Path, dest: Path, src_duration: float, fade_seconds: float = 0.6
) -> list[str]:
    """Composite a pre-rendered transparent text PNG onto `src`, fading the
    text in over `fade_seconds` from the start of this clip.

    The image input needs `-loop 1` — without it, ffmpeg's image2 demuxer
    supplies exactly one frame, and many ffmpeg builds' `overlay` filter does
    not repeat it, so the overlay silently vanishes after frame one. `-loop 1`
    alone loops the image forever, which then hangs the encode waiting for an
    EOF that never comes, so it needs an explicit `-t src_duration` to bound
    it — `-shortest` on the output does not reliably bound a
    filter_complex-produced stream the way it does a plain stream copy/mux.
    """
    filter_complex = (
        f"[1:v]fade=t=in:st=0:d={fade_seconds}:alpha=1[txt];"
        "[0:v][txt]overlay=0:0[outv]"
    )
    return [
        "ffmpeg", "-y", "-i", str(src),
        "-loop", "1", "-t", str(src_duration), "-i", str(text_png),
        "-filter_complex", filter_complex, "-map", "[outv]", "-an", str(dest),
    ]


def build_video_concat_cmd(shot_paths: list[Path], dest: Path) -> list[str]:
    n = len(shot_paths)
    inputs: list[str] = []
    for p in shot_paths:
        inputs += ["-i", str(p)]
    streams = "".join(f"[{i}:v:0]" for i in range(n))
    filter_complex = f"{streams}concat=n={n}:v=1:a=0[outv]"
    return ["ffmpeg", "-y", *inputs, "-filter_complex", filter_complex, "-map", "[outv]", str(dest)]


def build_audio_concat_cmd(audio_paths: list[Path], dest: Path) -> list[str]:
    n = len(audio_paths)
    inputs: list[str] = []
    for p in audio_paths:
        inputs += ["-i", str(p)]
    streams = "".join(f"[{i}:a:0]" for i in range(n))
    filter_complex = f"{streams}concat=n={n}:v=0:a=1[outa]"
    return ["ffmpeg", "-y", *inputs, "-filter_complex", filter_complex, "-map", "[outa]", str(dest)]


def build_mux_cmd(video_path: Path, audio_path: Path, dest: Path) -> list[str]:
    return [
        "ffmpeg", "-y", "-i", str(video_path), "-i", str(audio_path),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
        "-shortest", str(dest),
    ]


def run(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {' '.join(cmd)}\n{proc.stderr[-2000:]}")


def assemble(manifest_path: Path, output_dir: Path) -> Path:
    manifest = manifest_mod.load_manifest(manifest_path)
    timing = json.loads((output_dir / "timing.json").read_text())
    (output_dir / "shots").mkdir(parents=True, exist_ok=True)

    shot_final_paths = []
    for shot in manifest.shots:
        clip_dir = output_dir / "clips" / shot.id
        clip_paths = sorted(clip_dir.glob("clip_*.mp4"), key=lambda p: int(p.stem.split("_")[1]))
        if not clip_paths:
            raise FileNotFoundError(f"no clips found for {shot.id} under {clip_dir}")
        target = timing[shot.id]

        raw = output_dir / "shots" / f"{shot.id}_raw.mp4"
        run(build_concat_trim_cmd(clip_paths, target, raw))

        text_png = output_dir / "shots" / f"{shot.id}_text.png"
        text_overlay.render_text_png(shot.on_screen_text, text_png)

        final = output_dir / "shots" / f"{shot.id}_final.mp4"
        run(build_overlay_cmd(raw, text_png, final, src_duration=target))
        shot_final_paths.append(final)

    video_track = output_dir / "video_track.mp4"
    run(build_video_concat_cmd(shot_final_paths, video_track))

    narration_paths = [output_dir / "narration" / f"{shot.id}.mp3" for shot in manifest.shots]
    for p in narration_paths:
        if not p.exists():
            raise FileNotFoundError(f"missing narration audio: {p}")
    narration_track = output_dir / "narration_track.mp3"
    run(build_audio_concat_cmd(narration_paths, narration_track))

    final_video = output_dir / "final_video.mp4"
    run(build_mux_cmd(video_track, narration_track, final_video))
    return final_video
