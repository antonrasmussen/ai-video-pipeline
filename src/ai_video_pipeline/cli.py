"""ai-video-pipeline: generate a narrated video from a shot manifest via
Runway (video) and ElevenLabs (narration), assembled locally with ffmpeg.

Four steps; two of them (synth-narration, generate-video) talk to a paid API
and are separately gated:

  plan               no network. Print the Runway clip-tiling plan using the
                      manifest's nominal duration estimates.
  synth-narration     ElevenLabs only (cheap). Synthesizes narration audio per
                      shot, measures actual duration via ffprobe, writes
                      <output>/timing.json with real per-shot target durations.
  generate-video      Runway only (real cost). Requires <output>/timing.json
                      from synth-narration. Prints the cost-relevant plan and
                      REQUIRES --confirm (or --confirm-cost) before spending.
  assemble            ffmpeg only, local and free. Produces
                      <output>/final_video.mp4.

Run in this order. `plan` and `synth-narration` involve no real spend beyond
ElevenLabs' per-character TTS cost. `generate-video` is the one step that
costs real money per clip — check your Runway dashboard's current rate
before confirming; this tool does not know your account's pricing.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from . import assemble as assemble_mod
from . import elevenlabs_client, runway_client
from . import manifest as manifest_mod


def ffprobe_duration(path: Path) -> float:
    try:
        proc = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, check=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            "ffprobe not found on PATH. Install ffmpeg (e.g. `brew install ffmpeg`) "
            "— it provides ffprobe too."
        ) from e
    return float(proc.stdout.strip())


def cmd_plan(args: argparse.Namespace) -> int:
    manifest = manifest_mod.load_manifest(args.manifest)
    rows = manifest_mod.generation_plan(manifest)
    print(f"Plan for '{manifest.title}' (nominal durations from the manifest — not yet measured):\n")
    print(manifest_mod.format_plan_summary(rows))
    print(
        "\nThese are estimates. Run `synth-narration` to measure real narration "
        "length per shot before generating video, since TTS pacing will not "
        "exactly match the manifest's guessed timing."
    )
    return 0


def cmd_synth_narration(args: argparse.Namespace) -> int:
    manifest = manifest_mod.load_manifest(args.manifest)
    voice_id = args.voice_id or os.environ.get("ELEVENLABS_VOICE_ID")
    if not voice_id:
        print("No voice id given: pass --voice-id or set ELEVENLABS_VOICE_ID in the "
              "environment. Run `list-voices` to pick one.", file=sys.stderr)
        return 1
    output_dir: Path = args.output_dir
    audio_dir = output_dir / "narration"
    timing: dict[str, float] = {}
    for shot in manifest.shots:
        dest = audio_dir / f"{shot.id}.mp3"
        print(f"  synthesizing {shot.id}...", end=" ", flush=True)
        elevenlabs_client.synthesize(shot.narration, voice_id, dest)
        duration = ffprobe_duration(dest)
        timing[shot.id] = duration
        drift = duration - shot.nominal_duration
        print(f"{duration:.2f}s (manifest estimate {shot.nominal_duration:.1f}s, drift {drift:+.2f}s)")
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "timing.json").write_text(json.dumps(timing, indent=2))
    print(f"\nWrote {output_dir / 'timing.json'}")
    rows = manifest_mod.generation_plan(manifest, use_measured=timing)
    print("\nRunway generation plan using MEASURED narration durations:\n")
    print(manifest_mod.format_plan_summary(rows))
    return 0


def cmd_generate_video(args: argparse.Namespace) -> int:
    output_dir: Path = args.output_dir
    timing_path = output_dir / "timing.json"
    if not timing_path.exists():
        print(f"No {timing_path} found. Run `synth-narration` first.", file=sys.stderr)
        return 1
    timing = json.loads(timing_path.read_text())
    manifest = manifest_mod.load_manifest(args.manifest)
    rows = manifest_mod.generation_plan(manifest, use_measured=timing)

    print("Runway generation plan (measured durations):\n")
    print(manifest_mod.format_plan_summary(rows))
    print(
        f"\nThis will submit {len(rows)} paid Runway generations. Check your "
        "Runway dashboard for current per-second/per-generation pricing before "
        "confirming — this tool does not know your account's rate."
    )
    if not args.confirm:
        print("\nDry run only. Re-run with --confirm to actually generate video.")
        return 0

    clip_dir = output_dir / "clips"
    for row in rows:
        dest = clip_dir / row["shot_id"] / f"clip_{row['clip_index']}.mp4"
        if dest.exists() and not args.overwrite:
            print(f"  {dest} already exists, skipping (use --overwrite to regenerate)")
            continue
        print(f"  generating {row['shot_id']} clip {row['clip_index']} "
              f"({row['duration']}s)...", end=" ", flush=True)
        runway_client.generate_clip(
            row["prompt"], row["duration"], dest,
            ratio=manifest.aspect_ratio, model=manifest.video_model,
        )
        print(f"-> {dest}")
    print("\nAll clips generated. Run `assemble` next.")
    return 0


def cmd_assemble(args: argparse.Namespace) -> int:
    final = assemble_mod.assemble(args.manifest, args.output_dir)
    print(f"Assembled: {final}")
    return 0


def cmd_list_voices(args: argparse.Namespace) -> int:
    for v in elevenlabs_client.list_voices():
        print(f"  {v.get('voice_id')}  {v.get('name')}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="ai-video-pipeline", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--manifest", type=Path, default=Path("shot_manifest.yaml"),
                       help="path to the shot manifest YAML (default: ./shot_manifest.yaml)")
        p.add_argument("--output-dir", type=Path, default=Path("output"),
                       help="directory for generated assets (default: ./output)")

    p_plan = sub.add_parser("plan", help="no network; print the estimated generation plan")
    add_common(p_plan)

    p_synth = sub.add_parser("synth-narration", help="ElevenLabs only; measures real timing")
    add_common(p_synth)
    p_synth.add_argument("--voice-id", default=None,
                         help="ElevenLabs voice id (see list-voices); falls back to "
                              "ELEVENLABS_VOICE_ID env var if omitted")

    p_gen = sub.add_parser("generate-video", help="Runway only; costs money")
    add_common(p_gen)
    p_gen.add_argument("--confirm", "--confirm-cost", dest="confirm", action="store_true",
                       help="required to actually spend (--confirm-cost is an accepted alias)")
    p_gen.add_argument("--overwrite", action="store_true", help="regenerate clips that already exist")

    p_asm = sub.add_parser("assemble", help="ffmpeg only; free and local")
    add_common(p_asm)

    sub.add_parser("list-voices", help="ElevenLabs only; list available voice ids")

    args = parser.parse_args()
    return {
        "plan": cmd_plan,
        "synth-narration": cmd_synth_narration,
        "generate-video": cmd_generate_video,
        "assemble": cmd_assemble,
        "list-voices": cmd_list_voices,
    }[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
