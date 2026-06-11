# Video Engine

Local video editing automation for short-form educational content. Drop an MP4, get a fully edited vertical video with captions, motion graphics, and a Telegram delivery with posting caption and hashtags.

## Prerequisites

- **Python 3.9+** (3.11+ recommended)
- **Node.js 18+** (for Bun)
- **Bun** — [bun.sh](https://bun.sh)
- **ffmpeg** — `brew install ffmpeg` (macOS) or your system package manager
- **API keys optional** — default `ZERO_COST_MODE=true` uses deterministic shot planning, SVG B-roll, ffmpeg music, local Whisper
- **ANTHROPIC_API_KEY** — only if `USE_DESIGN_AGENT=true` for ad-lib videos (~$0.01/video)
- **PEXELS_API_KEY** / **PIXABAY_API_KEY** — optional stock B-roll (free tier)
- **Telegram bot** — optional, for delivery notifications

## Install (exact order)

### 1. ffmpeg

```bash
brew install ffmpeg
ffmpeg -version
```

### 2. Python dependencies (faster-whisper)

```bash
cd video-engine
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

First transcription run downloads the Whisper model (`small` by default in zero-cost mode) to `~/.cache/huggingface`.

### 3. Remotion agent skills (optional but recommended)

```bash
npx skills add remotion-dev/skills
```

### 4. Remotion project

```bash
cd remotion
bun install   # or: npm install
```

### 5. One-time SFX, music, and Lottie assets

```bash
cd video-engine
source .venv/bin/activate
python scripts/download_assets.py
```

Downloads CC0 SFX (whoosh, pop, tick, swoosh, impact), background music, and Lottie accent JSON files into `remotion/public/`.

## Configuration

Copy `.env.example` to `.env` in `video-engine/`:

```env
ZERO_COST_MODE=true
JUMP_CUTS=true
WHISPER_MODEL=small
BROLL_MODE=svg
USE_DESIGN_AGENT=false
SCRIPTS_ARCHIVE_URL=https://raw.githubusercontent.com/jugalsheth/script-engine/main/data/scripts_archive.json
```

### AI vs deterministic boundary

| Step | Type | When |
|------|------|------|
| Script matched | **Deterministic** `shot_planner.py` | Default — uses script metadata + transcript regex |
| Ad-lib video | **Deterministic** `shot_planner.py` | Default |
| Ad-lib + `USE_DESIGN_AGENT=true` | **AI** Claude Sonnet | Optional creative override |
| B-roll / fun / roles / beats | **Deterministic** keyword detectors | Always |
| Transcription | **Local** faster-whisper | Always ($0) |
| Jump cuts | **Deterministic** ffmpeg silencedetect | `JUMP_CUTS=true` |

The pipeline also loads `../.env` from the parent `CretorAuto/` folder if present.

**SCRIPTS_ARCHIVE_URL** must point to the raw GitHub URL for `data/scripts_archive.json` in your `script-engine` repo. Replace `jugalsheth` with your GitHub username if different. No git clone or manual copy-paste — the pipeline always fetches the latest committed archive.

## Usage

### Trial run (single file)

```bash
cd video-engine
source .venv/bin/activate
python watch.py --file raw_videos/your_video.mp4
```

### Watch folder (automatic)

```bash
python watch.py
```

Drop MP4 files into `raw_videos/`. Finished videos appear in `ready_to_post/`.

## Pipeline steps

1. Fetch latest scripts from GitHub (`scripts_archive.json`)
2. Transcribe with faster-whisper (word-level timestamps)
3. Optionally match transcript to a script (filename or fuzzy)
4. Claude Sonnet design agent builds animation shot list
5. Stage assets: ffmpeg color grade, stock B-roll fetch (Pexels → Pixabay), SFX
6. Remotion renders final 1080×1920 video with viral captions, stock cuts, and audio
7. Telegram notification with caption + hashtags

If the design agent fails, the pipeline still renders with captions only.

Staging log example:

```
Shots: 11 | B-roll: 4 stock clips (3 Pexels, 1 Pixabay) | SFX: on | Grade: on
```

## Customization

### Design rules

Edit `rules/design_rules.txt` — brand colors, caption style, stat callouts, step reveals, and constraints. The design agent reads this file on every run.

### Animation library

`rules/animation_library.txt` lists available shot types and their parameters.

### Stock B-roll

`src/broll_detector.py` detects keyword moments; `src/fetch_broll.py` downloads portrait clips from Pexels (primary) or Pixabay (fallback). Search queries are defined in `rules/broll_search_map.txt`. SVG diagrams are used when API keys are missing or fetch fails.

### Remotion Studio sliders

| Prop | Default | Effect |
|------|---------|--------|
| `captionStyle` | `viral` | 2-word Hormozi captions vs classic strip |
| `titleVerticalPosition` | 0.35 | Title card vertical placement |
| `captionVerticalPosition` | 0.75 | Caption vertical placement |
| `zoomIntensity` | 1.0 | Hook zoom strength multiplier |
| `statCalloutSide` | `right` | Stat callout alignment |

## Cost per video

| Step | Cost |
|------|------|
| faster-whisper transcription | Free (local CPU) |
| Pexels / Pixabay API | Free |
| SFX / music (CC0) | Free |
| Claude design agent | ~$0.01 |
| Remotion render | Free (local) |
| Telegram | Free |
| **Total** | **~$0.01/video** |

## Project structure

```
video-engine/
├── raw_videos/          # Drop MP4s here
├── ready_to_post/       # Final renders
├── rules/               # Design rules, broll search map, animations
├── scripts/             # download_assets.py (one-time SFX setup)
├── data/                # Cached scripts archive
├── remotion/            # Remotion render project
├── src/                 # Python pipeline modules
├── watch.py             # Entry point
└── pipeline.py          # Orchestrator
```

## Remotion studio (preview)

```bash
cd remotion
bun run start
```

Uses `input-props.json` generated by the pipeline after a run.
