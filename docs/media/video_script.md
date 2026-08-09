# Video script: *This Video Made Itself*

Plan and unified A/V script for a short (~83s target) teaser covering
`ai-video-pipeline` at a very high level: what it is, the two APIs it wires
together, the one design decision that makes it work (audio drives timing,
not the manifest's guess), and the cost discipline that keeps it affordable.
Intended for a README media embed; produced *by the tool it describes*. This
script is a human-authored planning document, not a pipeline input: it was
compiled by hand into `shot_manifest.yaml`, and the CLI pipeline runs from
that manifest, the same script → manifest → CLI method used for another
project.

- Runtime target: ~83 seconds (constraint: 75–95s); the produced video
  measured ~79.8s once real narration audio came in — see "Calibration"
- Narration: ~244 words, paced for this video's narrator (ElevenLabs voice
  "River") — see "Calibration" below; word count is not a fixed constraint,
  wording is tuned against measured audio, not a wpm formula
- On-screen text: ≤ 5 words per shot, ≤ ~40 characters (the overlay renderer
  draws one line, unwrapped)
- No file paths, function names, flag names, or screenshots — this is a
  teaser, not documentation

## Calibration

The prior video produced with this pipeline (for a different project, a
different narrator) ran 228 words in 118.57 measured seconds: 115 wpm, 1.92
words/sec. That number does not transfer between voices: an initial draft of
this script, budgeted at 1.92 w/s for River, measured at **2.93 words/sec**
in practice — nearly 50% faster — landing at 52.9s instead of the ~81s
intended. This draft's word counts were rescaled against that measured rate.
Rule going forward: **never budget words from a formula: `synth-narration`
measures the real thing for a few cents, and that's what to tune against**,
per shot, for whichever voice is actually cast.

## A. One-sentence thesis

**This teaser was not edited by anyone — it was compiled from a text file by
the same two-API, one-file pipeline it explains.**

## B. Audience takeaway checklist

- **The whole pipeline runs from one shot manifest**: each shot's visual
  prompt, narration, on-screen text, and timing all live in one hand-authored
  YAML file — that's the only input.
- **Two unrelated APIs do the work**: Runway generates the picture, ElevenLabs
  generates the voice. Neither knows the other exists.
- **Audio drives timing, not the other way around.** The manifest's duration
  is a guess; the *measured* length of the synthesized narration becomes the
  real target the video is cut to.
- **Runway generations are capped at 10 seconds each**, so longer shots are
  tiled from multiple generations, chosen to waste the least paid footage.
- **Spending is deliberate, not uniform.** A free local rehearsal proves the
  assembly mechanically first. Narration synthesis is a small per-character
  cost that runs right away; video generation, the expensive step, refuses to
  run without explicit confirmation.
- **This video is proof, not just an example** — it is itself the pipeline's
  output.

## C. Omission list (deliberately not covered)

1. The manifest's YAML field names and schema
2. The CLI subcommands and their flags
3. ffmpeg filter graph details (concat, trim, overlay compositing)
4. Why Pillow renders text instead of ffmpeg's `drawtext`
5. Runway/ElevenLabs pricing figures or API version numbers
6. Retry/regeneration mechanics for a bad clip
7. Voice selection (`list-voices`) and voice settings (stability, similarity)
8. Aspect ratio / resolution configuration
9. Any comparison to other video-generation tools or workflows

## D. Unified A/V script

Palette used in every shot: near-black void, high contrast, minimal abstract
geometry, no humans, no UI, no legible glyphs. Four colors carry fixed
meaning throughout: **pale gold = authored text (the manifest)**,
**violet-magenta = the generated picture stream (Runway)**, **teal = the
voice stream (ElevenLabs)**, **cold steel/pale white = local assembly
(ffmpeg)**. Each visual cell is self-contained and ambient/slowly-evolving —
a generation model can read any cell in isolation, and a mid-shot cut between
two independent generations of the same prompt should read as a deliberate
cut, not a continuity error.

| VISUAL & ON-SCREEN TEXT | AUDIO / NARRATION |
|---|---|
| **S1 · 0:00–0:07.2.** Near-black void. A single luminous pale-gold filament of light writes itself horizontally across the frame, unhurried, tracing like handwriting with no hand. It reaches the right edge and folds inward on itself, collapsing into one small, dense, glowing seed of light at center frame. Nothing else in frame: no tools, no cursor, no interface. ON-SCREEN TEXT: "Nobody edited this." | *(0:00)* Nobody edited this. No timeline. No cuts by hand. It came from one text file, and two APIs did the rest. |
| **S2 · 0:07.2–0:19.8.** Near-black void. The gold seed from S1 unfolds into a receding vertical ladder of glowing horizontal rules, evenly spaced, like a document made entirely of light — no readable glyphs, just structure. One by one, each rule splits lengthwise into two thin parallel strands: one drifting toward violet, one drifting toward teal. The ladder continues receding into the dark as more rules split. ON-SCREEN TEXT: "One entry per shot." | *(0:07.2)* It starts as a shot manifest: one entry per shot, holding a picture to be generated, a line to be spoken, and a bit of timing — nothing about how any of it actually gets made. |
| **S3 · 0:19.8–0:33.5.** Near-black void split by an unmarked vertical midline. On the left, a violet-magenta volumetric bloom slowly gathers and resolves into a rotating, translucent abstract form, folding and unfolding. On the right, a teal ribbon of light unspools from a point and oscillates like a slow waveform, never repeating exactly. The two sides brighten and drift toward the center at the same unhurried pace, but never touch or merge. ON-SCREEN TEXT: "Two APIs. One file." | *(0:19.8)* Two unrelated services do the making. One turns each description into a moving picture. The other turns each line of text into a spoken voice. Neither service knows the other exists, and neither one is ever trusted with the timing. |
| **S4 · 0:33.5–0:45.4.** Near-black void. A teal ribbon of light lies flat and still at center frame. A pair of cold steel, caliper-like arms of pale light close in from either side and hold it at a fixed span, precise ticks marking the measurement. Beside it, a violet ribbon of equal starting length shears cleanly at exactly that same span; the excess past the cut dissolves into fine drifting dust. ON-SCREEN TEXT: "The voice sets the length." | *(0:33.5)* The voice is generated first, and measured. Whatever it actually takes to say a line becomes that shot's real length — not the guess written in the manifest — and the picture gets trimmed to match exactly. |
| **S5 · 0:45.4–0:58.7.** Near-black void. A gap of light-marked space sits at center frame, wider than any single piece could span. Short violet segments of varying length slide in from off-frame and test themselves against the gap, one combination at a time, each attempt fading if it doesn't fit flush. The best-fitting combination locks into place, flush at both ends; a small overhang shears cleanly away into drifting dust. ON-SCREEN TEXT: "Least wasted footage." | *(0:45.4)* Runway caps a single generation at ten seconds, so a longer shot has to be built from several. Whichever combination of five, eight, and ten-second clips wastes the least footage gets picked — because wasted footage is still paid for. |
| **S6 · 0:58.7–1:13.4.** Near-black void. A precise steel aperture, ring-like and exact, spans the center of frame. A colorless, ghost-grey braid of light approaches from the left and passes through the aperture freely, unimpeded, continuing into the dark. A second braid — this one solid violet and teal — arrives at the same aperture, which has now closed to a thin bright seam, and it holds at the threshold, waiting. ON-SCREEN TEXT: "Nothing spends by accident." | *(0:58.7)* A free rehearsal proves the whole assembly locally, with no network calls at all. Voice costs pennies, so it runs right away — but the expensive step, generating video, refuses to run until someone confirms it, on purpose. |
| **S7 · 1:13.4–1:23.3.** Near-black void. The violet and teal ribbons from earlier shots twist together into one continuous braided strand, spiraling inward, then snap taut into a single clean horizontal line of light at center frame. The line holds, steady and still, fading only slightly at the very end. Empty darkness surrounds it, unchanging. ON-SCREEN TEXT: "It built itself." | *(1:13.4)* Which is how this video exists. A person wrote the narration and what each shot should show. The pipeline made the pictures, spoke the lines, and built the rest. |

## E. Title + README embed line

**Title:** *This Video Made Itself*

**Description:** An ~80-second teaser for `ai-video-pipeline`, generated by
the pipeline itself: one shot manifest, two APIs, and ffmpeg — no manual
editing, no UI work in either service.

## F. Self-critique

1. **Risk of reading as a gimmick rather than a demonstration.** "The video
   made itself" could land as a novelty stunt instead of evidence the tool
   works. Corrected: S2–S6 spend the bulk of runtime walking the actual
   mechanism (manifest structure, two independent APIs, audio-driven timing,
   clip tiling, spend gating) — the self-reference in S1/S7 is the frame, not
   the content.
2. **Overclaiming "nobody edited this."** Strictly true of the assembly (no
   manual cutting, no NLE), but the script itself and the manifest *were*
   authored by a person. Corrected: narration says "no timeline, no cuts by
   hand," which is accurate, rather than implying the words were also
   machine-authored.
3. **Duration-tiling (S5) is the most abstract beat and risks confusing
   rather than clarifying.** Corrected: the visual is grounded in a concrete,
   literal action (pieces sliding to test a fit, an overhang shearing away)
   rather than an abstract diagram, and the on-screen text ("Least wasted
   footage") names the concrete stake — cost — rather than the mechanism name
   ("clip tiling").
4. **Four color-coded threads (gold/violet/teal/steel) is more grammar than
   an 85-second video can comfortably teach.** Corrected: gold appears only
   in S1–S2 (authoring, then it's done), steel only in S4 and S6 (measurement
   and gating), so no shot ever needs to hold more than two colors' meaning
   in the viewer's head at once.
5. **Ending on "it built itself" repeats S1's claim without adding
   information.** Corrected: S7's narration names what a person actually did
   ("a person wrote the narration and what each shot should show") against
   what the pipeline did ("made the pictures, spoke the lines, and built the
   rest"), turning the closing line into an honest accounting of the split,
   not a bare repetition of the cold open — and reinforcing self-critique #2
   rather than repeating its mistake.
6. **First-draft word budget assumed the wrong speaking rate.** An early
   draft scaled every narration line to the 1.92 words/sec measured from a
   *different narrator* on a *different project*. Measured against River,
   the actual voice cast for this video, that draft ran 52.9s — 35% short of
   target. Corrected: rescaled word counts to River's measured 2.93 w/s, and
   made re-measuring per narrator (not assuming a formula) the standing rule
   — see "Calibration."
7. **S7 originally claimed the pipeline "described the pictures."** It
   doesn't: `visual_prompt` is authored by hand in the manifest, the same as
   the narration text — the pipeline generates footage from that
   description, it doesn't compose the description. Corrected: S7 now
   credits the person with writing "the narration and what each shot should
   show," and says the pipeline "made the pictures" (generated them from a
   given description) rather than "described" them (composed the
   description itself) — a distinction this video, of all videos, cannot
   afford to blur.
8. **S6 originally claimed "every paid step is gated" behind confirmation.**
   Not true: `synth-narration` calls the paid ElevenLabs API immediately,
   with no confirmation flag — only `generate-video`, the expensive step,
   requires `--confirm`. Corrected: S6 now names the actual asymmetry (cheap
   step runs right away, expensive step waits for confirmation) instead of a
   blanket claim that doesn't hold up against the tool's own source.
9. **S2 originally claimed the manifest has "nothing about resolution,
   nothing about pacing."** Not true: `aspect_ratio` and each shot's
   `start`/`end`/`nominal_duration` are manifest fields — this video's own
   manifest sets them. The B-checklist repeated the same overclaim ("nothing
   else is hand-authored," "the paid step" singular). Corrected both: S2 now
   says the manifest holds "a bit of timing" rather than denying timing
   fields exist, and the checklist names on-screen text and timing as
   hand-authored too, and separates narration's ungated cost from video
   generation's gated one — the same asymmetry fixed in #8, this time in the
   summary bullets rather than just the narration.
