# ai-video-pipeline

Generate a narrated video from a shot manifest: [Runway](https://runwayml.com)
for the visuals (text-to-video), [ElevenLabs](https://elevenlabs.io) for the
narration, [ffmpeg](https://ffmpeg.org) to assemble the result locally. No
manual editing, no UI work in either service — the whole thing is a CLI.

## ~81-second teaser, made by the pipeline itself

https://github.com/user-attachments/assets/ced4827e-8dec-4de3-a4e3-7ab0e4a0b66a

Produced end to end by this tool: a script
([docs/media/video_script.md](docs/media/video_script.md)) compiled into a
shot manifest ([docs/media/shot_manifest.yaml](docs/media/shot_manifest.yaml)),
run through `plan` → `synth-narration` → `generate-video` → `assemble` with
no manual editing.

Originally built to produce an explainer video for a different research
prototype (private while that work is in development); extracted here since
the pipeline itself has nothing to do with that project's content.

## Install

```bash
pip install -e ".[dev]"
brew install ffmpeg        # or your platform's equivalent; provides ffprobe too
```

Set in `.env` (never committed — already gitignored):

```
RUNWAY_API_KEY=...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...    # run `ai-video-pipeline list-voices` to pick one
```

## Before spending anything: prove the pipeline works

```bash
python tests/smoke_test.py
```

Generates synthetic placeholder clips and narration locally (ffmpeg lavfi
color/tone sources — no network, no API keys) against the bundled
`examples/example_manifest.yaml`, then runs the *actual* assembly code
against them. If this fails, the bug is in the ffmpeg pipeline, not in
Runway or ElevenLabs — fix it here before spending real money. Pass
`--manifest path/to/yours.yaml` to smoke-test against your own manifest.

## Real run: four steps

Steps 2 and 3 talk to a paid API and are separately cost-gated; 1 and 4 are
free and local. All four accept `--manifest` (default `./shot_manifest.yaml`)
and `--output-dir` (default `./output`).

**1. Plan (no network)** — sanity-check the shot breakdown and Runway
clip-tiling using the manifest's nominal duration estimates:

```bash
ai-video-pipeline plan --manifest shot_manifest.yaml
```

**2. Synthesize narration (ElevenLabs; cheap)** — generates real narration
audio per shot and measures its actual duration. TTS pacing won't exactly
match the manifest's guessed timing, so this becomes the real target
duration for that shot's video:

```bash
ai-video-pipeline list-voices
ai-video-pipeline synth-narration --manifest shot_manifest.yaml --voice-id <id>
```

`--voice-id` falls back to `ELEVENLABS_VOICE_ID` if omitted. Writes
`<output>/narration/{shot}.mp3` and `<output>/timing.json`.

**3. Generate video (Runway; real cost per generation)** — dry-run by
default; prints the exact generation plan (clip count, seconds, per shot)
and requires `--confirm` (or `--confirm-cost`) to actually spend:

```bash
ai-video-pipeline generate-video --manifest shot_manifest.yaml            # dry run
ai-video-pipeline generate-video --manifest shot_manifest.yaml --confirm  # real spend
```

Runway's single-generation duration cap is 5/8/10 seconds — shots longer
than that get tiled across multiple generations and concatenated + trimmed
in assembly. `manifest.plan_durations()` picks the tiling that wastes the
least generated footage. Check your Runway dashboard for current pricing
before confirming; this tool doesn't know your account's rate.

**4. Assemble (ffmpeg; free, local)**:

```bash
ai-video-pipeline assemble --manifest shot_manifest.yaml
```

Produces `<output>/final_video.mp4`: per-shot clips concatenated and
trimmed to the measured narration length, on-screen text composited, all
shots concatenated, narration muxed on top.

## Manifest schema

See `examples/example_manifest.yaml` for a working two-shot example.

```yaml
title: string
target_runtime_seconds: number       # informational; real timing comes from measured narration
aspect_ratio: "1280:720"             # Runway ratio string
video_model: "gen4.5"
shots:
  - id: string                       # unique, used for output filenames
    start: number                    # seconds, informational (for your own planning)
    end: number
    nominal_duration: number         # seconds; planning estimate before narration is measured
    visual_prompt: string            # sent to Runway as promptText
    on_screen_text: string           # composited over the clip via Pillow, not sent to Runway
    narration: string                # sent to ElevenLabs; keep free of stage directions like "[chime]"
    sfx_cues: [string]                # notes only; not auto-generated
```

## Design notes

- **Audio drives timing, not the manifest's guesses.** `nominal_duration` is
  a planning estimate; the real per-shot duration used for video generation
  and trimming comes from *measuring* the synthesized narration clip via
  `ffprobe`, so the final video's pacing matches the actual spoken audio
  rather than an assumption made before any audio existed.
- **On-screen text is rendered with Pillow and composited via ffmpeg's
  `overlay` filter, not ffmpeg's `drawtext`.** Plain ffmpeg builds (e.g. the
  default Homebrew formula) often lack the libfreetype/fontconfig `drawtext`
  needs; Pillow bundles its own text rendering, sidestepping that entirely.
  Text-to-video models are unreliable at rendering legible text either way,
  so `visual_prompt` never asks Runway to draw words.
- **Every Runway clip has its own audio track stripped** — final audio is
  narration + optional SFX only, never whatever ambient sound the video
  model generated.
- The image-overlay step needs `-loop 1 -t <duration>` on the still-image
  input: without `-loop 1`, ffmpeg's image2 demuxer supplies exactly one
  frame and many `overlay` filter builds don't repeat it (the overlay
  silently vanishes after frame one); `-loop 1` alone then loops forever and
  hangs the encode without an explicit `-t` bound, since `-shortest` doesn't
  reliably bound a filter_complex-produced stream the way it bounds a plain
  stream copy.

## License

MIT — see [LICENSE](LICENSE).
