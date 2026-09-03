---
name: auto-transcribe
description: Transcribe a meeting recording into a speaker-labelled Markdown transcript with diarization, cross-session voice recognition, and a review → rename flow. Use when the user says "transcribe" or "litteroi", names a recording file (.mp3/.m4a/.wav), asks who said what, or wants to rename speakers in an existing transcript.
argument-hint: '[recording-file] [--attendees "A, B"] [--num-speakers N] [--user-channel left|right|none] [--language xx]'
---

# Auto-Transcribe Skill

Local (mlx-whisper + ECAPA) meeting transcription with speaker diarization, a global
voice store, and AI-assisted review. Optimized for Apple Silicon Macs.

## What Claude does when this skill is invoked

Paths: `PY=~/.claude/skills/auto-transcribe/.venv/bin/python`,
`M=~/.claude/skills/auto-transcribe/scripts/meeting.py`. Always use the skill's own venv.

0. **Environment (only when needed).** On a machine where the skill has not run
   before, or whenever a step fails with a missing venv / command / import, run
   `python3 ~/.claude/skills/auto-transcribe/scripts/doctor.py` (stdlib-only, no
   venv needed). It checks Apple Silicon, uv, ffmpeg, the venv, and dependencies,
   and prints the exact install commands — run them (or relay them to the user)
   in the printed order, then re-run the doctor until it reports ready.
1. **Resolve the file.** If the user gives a name without a path, look in the
   configured `recordings_dir` (`~/.auto-transcribe/config/settings.yaml`; typically
   the recording app's output folder) for the newest matching file. If the setting
   is unset, ask where recordings live and offer to save it there. If
   `<stem>.transcript.json` already exists next to the audio, skip to step 4 (or use
   `rediarize`/`rename`) unless asked to redo.
2. **Check the channel layout.** The default comes from `diarization.user_channel`
   in settings: "left"/"right" = the user's own mic has that stereo channel to
   itself, unset = no dedicated user channel (mono or plain mix). On first use, or
   when the user says a recording differs from their usual setup, ask which layout
   applies; save their usual one to settings and pass one-off deviations as
   `--user-channel left|right|none`.
3. **Run** `$PY $M run "<file>"` **in the background** (≈ 10 min per hour of audio) and
   wait for it — don't poll. Pass `--attendees "A, B"` if the user named participants,
   `--num-speakers N` if they gave a count, `-l en` for non-Finnish meetings.
4. **Present the speaker review** from the printed `=== speakers ===` block /
   `<stem>.speakers.yaml`: for each "Speaker N" give talk time, the store's guess with
   score (and why), and 2–3 representative utterances — summarise *what each speaker
   talked about* so the user can recognise them. Mark `[minor]` speakers as probably
   fragments. Heed the printed warnings: a "may merge two speakers" tie means the
   cluster likely fuses two people (the pipeline tries to auto-split; if it could
   not, rediarize with a higher `-n`); "attendees not matched to any cluster" means
   an unidentified cluster is probably that person — check its samples against them
   first. To identify a voice with no stored print, compare the cluster's segment
   `emb`s in `<stem>.transcript.json` against the named `speakers` centroids of a
   previous meeting's `.transcript.json` (cosine; ≥ ~0.5 on a 15 s+ turn is strong).
   Then ask the user for the names (they may instead edit the yaml).
5. **Apply names:** `$PY $M rename "<file>" "Speaker 1=Name, Speaker 2=Other"` (the
   yaml is read too; `-` clears a name; several Speaker Ns may map to one person —
   only the largest cluster is enrolled). This re-renders the `.md`, updates the
   yaml/json, and enrols voices. Report which names were applied and which were
   enrolled (20 s+ = full voiceprint, 8–20 s = weak hint-only print, under 8 s none).
6. If the clustering still looks wrong (one person split in two, two merged), use
   `$PY $M rediarize "<file>" --num-speakers N` or `--threshold 0.5/0.6` — it re-clusters
   from stored embeddings in seconds. Names already confirmed survive re-clustering.
7. **Fix misheard domain terms:** `$PY $M normalize "<file>"` prints what it would
   change; add `--apply` to write. Run it whenever the meeting has product, system
   or status names — Whisper mangles them and, worse, grows *confident* in the
   mangle, so a confidence threshold will not find them. Present the preview table
   before applying, and add anything it missed to the matching pack in `~/.auto-transcribe/config/domain/`.
8. The deliverable is `<stem>.md` next to the recording. Offer a summary / action items
   from it only if asked.

When the layout has a dedicated user channel, never downmix to mono or run the
legacy `transcribe.py` — that channel must stay separate. Without one, the whole
recording is processed as a single multi-speaker channel and everyone (including
the user) is diarized and named through the same review flow.

## Commands

### /transcribe <file>  (meeting pipeline — the default)
Transcribe a meeting recording end-to-end: optional stereo split (your own mic
channel vs. everyone else, per the configured layout), Whisper per channel
(Finnish forced by default), ECAPA speaker diarization of the multi-speaker
channel, speaker identification against the global profile store, and a review
sheet for naming.

**Usage:**
```
/transcribe "~/Recordings/20260819 1130 Acme - CustomerX - ProjectY - dev daily.mp3"
/transcribe recording.mp3 --attendees "Alex Example, Bella Sample" --num-speakers 3
/transcribe recording.mp3 --language en
```

**Script:** `meeting.py run <audio>` — options `-l/--language`, `-n/--num-speakers`,
`-a/--attendees "A,B"`, `-t/--threshold` (cluster cosine distance, default 0.55),
`-u/--user-channel left|right|none` (layout override), `--mono` (alias for
`--user-channel none`), `--force`.

**Outputs, written next to the audio file:**
- `<stem>.md` — speaker-labelled transcript (turns coalesced, timestamps)
- `<stem>.transcript.json` — everything: segments, words, per-unit embeddings, speakers, guesses
- `<stem>.speakers.yaml` — review sheet: per speaker the talk time, turn count,
  best guesses from the profile store (with score), first and longest utterances

**Naming flow (how the user assigns real names):**
1. Read the review sheet (or the `=== speakers ===` block printed at the end) and
   identify who "Speaker 1..N" are from the samples. Claude should summarise what
   each speaker said when asked, to help the user recognise them.
2. Apply names either way — both work and can be combined:
   - edit the names in `<stem>.speakers.yaml`, then `meeting.py rename "<audio>"`
   - or `meeting.py rename "<audio>" "Speaker 1=Alex Example, Speaker 2=Bella Sample"`
   The user's own mic channel can be renamed the same way (`"You=Alex Example"`):
   until the user's name is known it is labelled with the placeholder "You";
   naming it stores the name in settings (`diarization.user_name`) and enrols
   their voice, and later runs label it automatically.
3. `rename` re-renders the `.md` and **enrols** each named speaker's session centroid
   into the global store (`~/.auto-transcribe/config/speakers/*.json`, one centroid
   per session, max 24 kept; per person only their largest cluster). Speech of
   20 s+ makes a full voiceprint; 8–20 s a *weak* one (shown as "(weak)" in guesses,
   never auto-applied); under 8 s none. `--no-enrol` skips enrolment. Re-running on
   the same file replaces, not duplicates.
4. Next time the same person appears, `run` shows them as a guess
   (`guess: Alex Example 0.78`) and auto-applies the name when the raw score
   ≥ `diarization.auto_label_threshold` (0.70), the match is not weak, no other
   cluster claims the same name, and no second enrolled voice ties the cluster
   (a tie marks the cluster as a suspected merge instead — the pipeline then tries
   finer clusterings automatically and warns if it cannot separate the voices).
   Auto-applied names are marked `auto` in the yaml — still confirm with `rename`
   so the store gets the new session.

**Matching bias:** `--attendees` (+0.08 to listed names) and the filename context
(`Acme - CustomerX - ProjectY - dev daily` → tokens `customerx projecty`; +0.05 ×
overlap with the contexts a profile was seen in). The raw cosine score is always
shown; the bias only reorders near-ties. When the layout has a dedicated user
channel it always belongs to the user: with `diarization.user_name` set it is
labelled and auto-enrolled under that name; otherwise it is labelled "You"
(no profile is created for the placeholder).

**Re-cluster without re-running Whisper:** `meeting.py rediarize "<audio>" -n 3` or
`-t 0.5` (uses the embeddings stored in the JSON; seconds, not minutes).

**Profiles:** `meeting.py speakers` lists the store; `meeting.py speakers forget "Name"`.

### /normalize <file>  (domain-term correction)
`meeting.py normalize "<audio>" [--apply] [--fuzzy 0.82]`

Rewrites domain names Whisper misheard, then re-renders the `.md`. Preview by
default; `--apply` writes both the `.md` and the `.transcript.json`.

**Why it is confidence-blind.** Whisper mishears a name two different ways. The
first mention is a genuine guess and scores low — in one 33-minute meeting
`Verteks` came out at p=0.33 against a corpus median of 0.986. But
`condition_on_previous_text` then feeds that guess forward, and the same word
later scores **0.99**. A confidence gate repairs the first occurrence and leaves
every repeat, so matching here ignores confidence entirely.

**Terms are layered packs in `~/.auto-transcribe/config/domain/`:**
- `_shared.yaml` loads for **every** recording — cross-project conventions
  (Finnish→English loanwords, tool names, employer).
- `<project>.yaml` loads when its filename matches a token in the recording's
  filename context — the same signal that biases speaker matching. So
  `… Acme - CustomerX - ProjectY …` loads `customerx.yaml`, and a CustomerZ
  recording never sees CustomerX's terms or vice versa.
- Project packs load **first**, so a project term wins any conflict with
  `_shared`. Override detection with `--domain customerx,customerz`.
- With no matching pack you get `_shared` only. Both `run` and `normalize`
  print which packs they used.

**Per term:**
- `variants` — mis-transcribed **stems**, lowercase and *uninflected*. Finnish
  endings are re-attached automatically (`Verteksin` → `Vertexin`). An inflected
  variant swallows the ending and yields `Vertexn`.
- `map` — whole-token fixes, checked first. Use where a stem swap breaks vowel
  harmony (`räpintöjä` would become *`rajapintöjä`, not `rajapintoja`).
- `proper: false` — follow the source token's casing (common nouns).
- `fuzzy: false` — **set this whenever the canonical is an ordinary word.** One
  letter separates `fallback` from `callback` (ratio 0.875), so near-miss
  matching will happily corrupt correct text.

Hyphens are handled specially: a stem never reaches across one, so
`Vertex-toimittaja` keeps its compound dash, while `ver-texin` (a spurious
Whisper hyphen) is repaired to `Vertexin` via an exact-only retry.

Domain canonicals are also fed to Whisper's `initial_prompt` ahead of the
generic `vocabulary.yaml`, since that prompt is capped and silently truncated.
That biasing only helps the *first* hearing — `normalize` is what fixes the
confident repeats.

**Filename convention parsed:** `<yyyymmdd> <hhmm> <employer> - <entity> - <project> - <purpose>.mp3`
(loose hyphenation is fine; the remainder after the employer marker is the context).
A leading `<Word> - ` is treated as the employer automatically; to also strip an
employer written without a dash, set `filename.org_marker` in settings.

### /transcribe-legacy <file>
The old single-pass `transcribe.py` (mono downmix, confidence annotations, `--api`
OpenAI fallback, srt/vtt). Use only when the meeting pipeline doesn't fit.

**Options:** `--format/-f` (markdown, srt, vtt, json), `--language/-l`, `--api`, `--output/-o`

### /transcribe-live <source>
Monitor a live transcript or audio file for continuous transcription.

**Usage:**
```
/transcribe-live ~/Documents/meeting_transcript.txt
/transcribe-live recording.wav --mode audio --template notes.md
```

**Options:**
- `--mode` / `-m`: 'text' for transcript files, 'audio' for audio files
- `--template` / `-t`: Template file to fill continuously
- `--interval` / `-i`: Poll interval in seconds (default: 20)
- `--output` / `-o`: Output file path

### /enhance <file>
Preprocess audio for better transcription quality.

**Usage:**
```
/enhance noisy_recording.mp3
/enhance call.wav --noise-reduction deepfilternet --voice-isolation
```

**Options:**
- `--no-normalize`: Skip loudness normalization
- `--noise-reduction`: Method - noisereduce, deepfilternet, or none
- `--voice-isolation`: Isolate voice from background (slow)
- `--force`: Enhance even if quality is already good
- `--output` / `-o`: Output file path

### /diarize <file>
Add speaker labels to a transcript or audio file.

**Usage:**
```
/diarize meeting.wav
/diarize audio.mp3 --transcript transcript.json --mode stereo
```

**Options:**
- `--transcript` / `-t`: Existing transcript JSON to enhance
- `--mode` / `-m`: stereo, mono, or auto (default: auto)
- `--left-speaker`: Name for left channel (default: User)
- `--right-speaker`: Name for right channel (default: Remote)
- `--num-speakers` / `-n`: Number of speakers (mono mode)
- `--output` / `-o`: Output file path

### /fill-template <transcript> <template>
Extract answers from transcript into a template.

**Usage:**
```
/fill-template meeting.json meeting_notes_template.md
```

**Template formats supported:**
- `Q: Question here?` - Question format
- `{{PLACEHOLDER}}` - Mustache-style placeholders
- `- Topic:` - Bullet point topics
- `## Section` - Section headers

### /add-speaker <name> <audio>
Learn a speaker's voice from an audio sample.

**Usage:**
```
/add-speaker "John Smith" john_sample.wav
```

### /add-vocabulary <terms>
Add domain-specific terms to improve transcription accuracy.

**Usage:**
```
/add-vocabulary Kubernetes,PostgreSQL,GraphQL
/add-vocabulary --category meeting standup,retro,backlog
```

### /export <transcript> <format>
Convert transcript to different formats.

**Usage:**
```
/export transcript.json srt
/export meeting.json vtt --output subtitles.vtt
```

## Script Paths

All scripts are located at `~/.claude/skills/auto-transcribe/scripts/`:

- `doctor.py` - **Environment check**: stdlib-only, runs with system python3; prints exact install commands for anything missing
- `meeting.py` - **Meeting pipeline**: channel split per configured layout, per-channel Whisper, ECAPA diarization, speaker ID, review sheet, rename/enrol
- `transcribe.py` - Legacy single-pass transcription with confidence scoring
- `enhance.py` - Audio preprocessing pipeline
- `diarize.py` - Speaker diarization
- `refine_transcript.py` - Context-aware AI refinement
- `template_fill.py` - Template extraction
- `live_monitor.py` - Live monitoring
- `export.py` - Format conversion

Run via the skill venv: `~/.claude/skills/auto-transcribe/.venv/bin/python ~/.claude/skills/auto-transcribe/scripts/meeting.py run <audio>` (or `uv run --directory ~/.claude/skills/auto-transcribe python scripts/meeting.py ...`). Whisper for a 1 h stereo meeting takes ~10 min on an M3 Max; run it in the background and wait.

## Configuration

Settings are stored in `~/.auto-transcribe/config/`:

- `settings.yaml` - Main configuration
- `vocabulary.yaml` - Domain terms
- `speakers/` - Voice profiles

### Key Settings

```yaml
transcription:
  model: "mlx-community/whisper-large-v3-mlx"
  confidence_thresholds:
    high: 0.7      # Normal output
    low: 0.4       # [inaudible] threshold

enhancement:
  noise_reduction: "noisereduce"  # or deepfilternet

diarization:
  default_mode: "stereo"
  user_channel: null               # your own mic's channel: "left", "right", or
                                   # null = no dedicated user channel (mono / mix)
  user_name: "Your Name"           # label + auto-enrolled profile for your own channel;
                                   # unset -> placeholder "You", learned on first rename
  cluster_threshold: 0.55          # agglomerative cosine-distance cut (lower = more speakers)
  auto_label_threshold: 0.70       # min raw cosine to auto-apply a stored name

filename:
  org_marker: null                 # employer name to strip from filename context, e.g. "Acme"

recordings_dir: null               # where recordings land (e.g. the recording app's
                                   # output folder); used to resolve bare filenames

live_monitoring:
  poll_interval: 20  # seconds
```

## Workflow Examples

### Basic Meeting Transcription
1. Enhance audio if needed: `/enhance meeting.mp3`
2. Transcribe: `/transcribe meeting_enhanced.wav`
3. Review and fix uncertain sections manually or with `/refine`

### Stereo call recording with your mic on its own channel
1. Record with stereo output (your mic on one channel, everyone else on the other;
   configure the side as `diarization.user_channel`)
2. `/transcribe call.mp3` → `.md`, `.transcript.json`, `.speakers.yaml` next to the file
3. Identify "Speaker N" from the review sheet; `meeting.py rename call.mp3 "Speaker 1=Name, …"`
4. Known voices are guessed automatically next time (global store, biased by attendees/context)

### Live Meeting Notes
1. Start your recording app with timestamped transcript output
2. Create template with questions/topics
3. Run: `/transcribe-live transcript.txt --template notes.md`
4. Template updates as meeting progresses

### Learning Team Voices
Voices are learned as a side effect of naming speakers with `meeting.py rename`
(one ECAPA centroid per session per person). `/add-speaker` (legacy, resemblyzer)
profiles are ignored by the meeting pipeline.

## Confidence Annotations

The transcription marks uncertain words:
- `word` - High confidence (>= 0.7)
- `[word?]` - Medium confidence (0.4 - 0.7)
- `[inaudible]` - Low confidence (< 0.4)

Use `/refine transcript.json` to have Claude resolve these using context.

## Best Practices

1. **Audio Quality**: Better input = better output. Use enhance for noisy recordings.

2. **Stereo for Calls**: If your recording app can put your own mic on its own stereo channel, configure that (and set `diarization.user_channel`) for automatic speaker separation.

3. **Domain Vocabulary**: Add technical terms your team uses to improve accuracy.

4. **Templates**: Create standard meeting templates with your typical questions/sections.

5. **Archive**: Transcripts are saved to `~/.auto-transcribe/transcripts/` for searchability.

## Dependencies

Check the environment and get install commands for anything missing (works with
the bare system python3, before anything is set up):

```bash
python3 ~/.claude/skills/auto-transcribe/scripts/doctor.py
```

It verifies: Apple Silicon Mac (required by mlx-whisper), uv, ffmpeg/ffprobe,
the skill venv, and the Python dependencies; models (~3 GB) and personal
settings are noted but download/get created automatically on first run.

Manual dependency install:
```bash
cd ~/.claude/skills/auto-transcribe
uv sync
```

For DeepFilterNet (optional, higher quality noise reduction):
```bash
uv sync --extra full
```

## Troubleshooting

**Model download slow?**
Models (~3GB) download to `~/.auto-transcribe/models/` on first use.

**API fallback:**
Set `OPENAI_API_KEY` for automatic fallback when local transcription fails.

**Memory issues:**
For very long recordings, use chunked processing or the API fallback.
