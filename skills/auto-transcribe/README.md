# Auto-Transcribe

High-quality audio transcription skill for Claude Code, optimized for Apple Silicon Macs.

## Features

- **MLX-Whisper Transcription**: Local transcription using Apple Silicon GPU acceleration
- **Confidence Scoring**: Word-level confidence with automatic annotation of uncertain sections
- **Meeting pipeline (`meeting.py`)**: configurable channel layout (your own mic on one stereo channel, or a plain multi-speaker mix), per-channel Whisper, ECAPA speaker diarization, global speaker profiles with context/attendee bias, review sheet + rename/enrol flow
- **Speaker Diarization (legacy)**: Stereo channel splitting or multi-speaker clustering
- **Audio Enhancement**: Noise reduction and loudness normalization
- **Live Monitoring**: Watch timestamped transcript output or growing audio files
- **Template Filling**: AI-powered extraction of meeting notes/action items
- **Multiple Export Formats**: Markdown, SRT, VTT, JSON

## Installation

The skill is automatically available in Claude Code. Dependencies install on first use via uv.

To check the environment and get exact install commands for anything missing
(runs with the bare system python3, no setup required):

```bash
python3 ~/.claude/skills/auto-transcribe/scripts/doctor.py
```

### Manual Dependency Installation

```bash
cd ~/.claude/skills/auto-transcribe
uv sync
```

### Optional: High-Quality Noise Reduction

```bash
uv sync --extra full
```

This installs DeepFilterNet for superior noise reduction (requires more resources).

## Quick Start

### Basic Transcription (meeting pipeline)

```
/transcribe meeting.mp3
# → meeting.md, meeting.transcript.json, meeting.speakers.yaml next to the file
# identify speakers from the review sheet, then:
~/.claude/skills/auto-transcribe/.venv/bin/python ~/.claude/skills/auto-transcribe/scripts/meeting.py \
  rename meeting.mp3 "Speaker 1=Etunimi Sukunimi, Speaker 2=Toinen Nimi"
```

Named speakers are enrolled into `~/.auto-transcribe/config/speakers/` and guessed
automatically in later recordings. See `skill.md` for the full command reference.

### Enhanced Workflow

```
# 1. Enhance noisy audio
/enhance noisy_call.mp3

# 2. Transcribe with speaker labels
/transcribe noisy_call_enhanced.wav
/diarize noisy_call_enhanced.wav --transcript noisy_call_enhanced.json

# 3. AI refinement of uncertain sections
# (handled via refine_transcript.py)
```

### Live Meeting Notes

```
# Start your recording app with transcript output to file
/transcribe-live ~/transcripts/current_meeting.txt --template meeting_template.md
```

## Commands Reference

| Command | Description |
|---------|-------------|
| `/transcribe <file>` | Transcribe audio file |
| `/transcribe-live <source>` | Monitor live transcript/audio |
| `/enhance <file>` | Preprocess audio quality |
| `/diarize <file>` | Add speaker labels |
| `/fill-template <transcript> <template>` | Extract into template |
| `/add-speaker <name> <audio>` | Learn speaker voice |
| `/add-vocabulary <terms>` | Add domain terms |
| `/export <transcript> <format>` | Convert format |

## Configuration

Settings: `~/.auto-transcribe/config/settings.yaml`

```yaml
transcription:
  model: "mlx-community/whisper-large-v3-mlx"
  fallback_api: "openai"
  confidence_thresholds:
    high: 0.7
    low: 0.4
  language: "auto"

enhancement:
  enabled: true
  normalize: true
  noise_reduction: "noisereduce"

diarization:
  default_mode: "stereo"
  user_channel: "left"

live_monitoring:
  poll_interval: 20
  buffer_lag: 10

output:
  default_format: "markdown"
  timestamp_format: "hh:mm:ss"
```

## Recording Setup

For optimal results, if your recording app supports multi-source capture:

1. **Stereo Recording**: Set up two capture sources
   - One channel: Your microphone (set it as `diarization.user_channel`)
   - Other channel: System audio (remote participants)

2. **Transcript Output**: Add a "Transcribe" block
   - Format: `[00:00:00.02] Speaker: text`
   - Output to file for live monitoring

3. **Audio Quality**: Use "Denoise" block for cleaner input

## Template Format

Create templates with these placeholder formats:

```markdown
# Meeting Notes

## Attendees
{{ATTENDEES}}

## Discussion

Q: What were the main topics discussed?

Q: Were there any decisions made?

## Action Items
- Action Items:

## Next Steps
{{NEXT_STEPS}}
```

## Confidence Annotations

The transcription uses these markers:

- **Normal text**: High confidence (≥70%)
- **[word?]**: Medium confidence (40-70%)
- **[inaudible]**: Low confidence (<40%)

These can be resolved by Claude using context from surrounding text.

## Speaker Profiles

Learn voices for automatic recognition:

```
/add-speaker "Alice Chen" alice_meeting_sample.wav
/add-speaker "Bob Smith" bob_interview.wav
```

Profiles are saved to `~/.auto-transcribe/config/speakers/` and automatically matched in future transcriptions.

## Vocabulary

Add domain terms to improve accuracy:

```
/add-vocabulary Kubernetes,PostgreSQL,microservices
```

Terms are saved to `~/.auto-transcribe/config/vocabulary.yaml`.

## File Structure

```
~/.claude/skills/auto-transcribe/
├── skill.md              # Skill definition
├── pyproject.toml        # Dependencies
├── README.md             # This file
└── scripts/
    ├── transcribe.py     # Core transcription
    ├── enhance.py        # Audio preprocessing
    ├── diarize.py        # Speaker diarization
    ├── refine_transcript.py  # AI refinement
    ├── template_fill.py  # Template extraction
    ├── live_monitor.py   # Live monitoring
    ├── export.py         # Format conversion
    └── utils/
        ├── audio.py      # Audio utilities
        ├── config.py     # Configuration
        ├── formats.py    # Output formats
        └── speakers.py   # Speaker profiles

~/.auto-transcribe/
├── config/
│   ├── settings.yaml     # Main settings
│   ├── vocabulary.yaml   # Domain terms
│   └── speakers/         # Voice profiles
├── models/               # Downloaded models
└── transcripts/          # Archived transcripts
```

## API Fallback

Set `OPENAI_API_KEY` environment variable for automatic fallback when local transcription fails or for faster processing of long files.

## Troubleshooting

### First Run is Slow
Model downloads (~3GB for whisper-large-v3) happen on first use.

### Out of Memory
For very long recordings:
- Use `--api` flag for OpenAI processing
- Process in chunks using the scripts directly

### Poor Quality Results
- Run `/enhance` first for noisy audio
- Add domain vocabulary for technical terms
- Check audio is mono 16kHz (automatic conversion happens)

### Speaker Detection Issues
- Ensure stereo recording has clear channel separation
- For mono, try specifying `--num-speakers`
- Add speaker profiles for better matching

## License

Part of Claude Code skills ecosystem.
