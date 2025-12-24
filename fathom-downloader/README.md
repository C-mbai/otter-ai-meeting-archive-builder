# Fathom Video Downloader

Download all your Fathom.video recordings locally using the Fathom API. Includes videos, transcripts, summaries, and action items.

## Features

- **Fully automated** - Uses Fathom API to list and download all recordings
- **Rich metadata** - Downloads transcripts, summaries, action items, and participant info
- **Resume capability** - Skips already-downloaded videos
- **Progress tracking** - Shows download progress and generates detailed reports
- **Privacy-first** - All downloads run locally on your machine

## Prerequisites

- Python 3.6 or higher
- ffmpeg installed
- Fathom API key

## Quick Start

### 1. Install Dependencies

```bash
cd fathom-downloader
pip install -r requirements.txt
```

### 2. Install ffmpeg

**Mac:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html)

### 3. Set Up API Key

Create a `.env` file:

```bash
cp .env.example .env
nano .env
```

Add your API key:
```
FATHOM_API_KEY=your_api_key_here
```

Or export it as an environment variable:
```bash
export FATHOM_API_KEY=your_api_key_here
```

### 4. Download Your Videos

**Test with dry run first:**
```bash
python download_fathom_videos.py --dry-run
```

**Download all videos:**
```bash
python download_fathom_videos.py
```

**Test with just 5 videos:**
```bash
python download_fathom_videos.py --limit 5
```

## What Gets Downloaded

For each meeting, the tool downloads:

- **Video file** (`.mp4`) - Full recording in highest quality
- **Metadata** (`.json`) - Complete meeting data including:
  - Title, date, duration
  - Participants
  - Share URL
  - Full transcript with timestamps
  - Summary
  - Action items
- **Transcript** (`_transcript.txt`) - Formatted transcript with speaker names and timestamps
- **Summary** (`_summary.txt`) - Meeting summary

## File Organization

Downloaded files are saved as:
```
downloads/
├── 2024-03-15 - Team Standup.mp4
├── 2024-03-15 - Team Standup.json
├── 2024-03-15 - Team Standup_transcript.txt
├── 2024-03-15 - Team Standup_summary.txt
├── 2024-03-14 - Client Call.mp4
├── 2024-03-14 - Client Call.json
├── ...
└── download_report.json
```

## Usage Examples

### Basic Usage

```bash
# Download everything (recommended)
python download_fathom_videos.py

# Dry run (see what would be downloaded)
python download_fathom_videos.py --dry-run

# Custom output directory
python download_fathom_videos.py -o /path/to/my/fathom/archive

# Use specific API key
python download_fathom_videos.py --api-key YOUR_API_KEY

# Test with first 3 videos
python download_fathom_videos.py --limit 3
```

### Resume After Interruption

If downloads are interrupted, just run the same command again. The script automatically skips already-downloaded videos.

```bash
python download_fathom_videos.py
```

## API Key Setup

### Getting Your API Key

1. Log into Fathom.video
2. Go to Settings → Integrations → API
3. Create a new API key
4. Copy the key

### Using the API Key

**Option 1: .env file (recommended)**
```bash
echo "FATHOM_API_KEY=your_key_here" > .env
```

**Option 2: Environment variable**
```bash
export FATHOM_API_KEY=your_key_here
python download_fathom_videos.py
```

**Option 3: Command line argument**
```bash
python download_fathom_videos.py --api-key your_key_here
```

## Download Report

After downloading, check `downloads/download_report.json` for:
- Total number of meetings
- Success/failure counts
- Details of each download
- Error messages for failed downloads

Example report:
```json
{
  "timestamp": "2024-03-15T10:30:00",
  "total": 50,
  "successful": 48,
  "skipped": 0,
  "failed": 2,
  "results": [...]
}
```

## Troubleshooting

### "Error: ffmpeg is not installed"

Install ffmpeg using the instructions in step 2 above.

### "Error: Fathom API key required"

Make sure you've set up your API key using one of the three methods above.

### "Video download failed"

**Possible causes:**
- Network timeout (video might be very large)
- Video URL not accessible (permissions issue)
- ffmpeg error

**Solutions:**
- Check your internet connection
- Verify you have access to the meeting in Fathom
- Run again - the script will retry failed downloads
- Check the error message in the download report

### API Rate Limiting

Fathom allows 60 API calls per minute. The script automatically handles pagination and should stay within limits. If you hit rate limits, the script will show errors and you can resume later.

### Videos Taking Too Long

Large videos can take time to download. The script has a 1-hour timeout per video. For very large libraries:

1. Use `--limit` to download in batches
2. Run in a `screen` or `tmux` session
3. Let it run overnight

## Privacy & Security

- All downloads happen **locally** on your machine
- Your API key is stored **only** in your local `.env` file
- No data is sent to any third-party services
- Downloads are direct from Fathom's servers

## Command Reference

```
usage: download_fathom_videos.py [-h] [--api-key API_KEY] [-o OUTPUT_DIR]
                                [--dry-run] [--limit LIMIT]

Options:
  --api-key API_KEY    Fathom API key (or set FATHOM_API_KEY env var)
  -o OUTPUT_DIR        Output directory (default: downloads)
  --dry-run            Preview without downloading
  --limit LIMIT        Download only first N videos
```

## How It Works

1. **Authenticate** - Uses your API key to access Fathom's API
2. **List meetings** - Fetches all meetings with automatic pagination
3. **Extract metadata** - Saves transcripts, summaries, and meeting info
4. **Download videos** - Uses ffmpeg to download m3u8 streams
5. **Generate report** - Creates a summary of all downloads

## Tips

1. **Start with a dry run** to verify everything is set up:
   ```bash
   python download_fathom_videos.py --dry-run
   ```

2. **Test with a small batch** before downloading everything:
   ```bash
   python download_fathom_videos.py --limit 5
   ```

3. **Check the download report** after completion to see if anything failed

4. **Keep your metadata** - The JSON files contain valuable information about each meeting

## What's Next?

After downloading, you can:
- Build a searchable archive viewer (coming soon)
- Process transcripts for insights
- Archive to external storage
- Share specific videos while keeping others private

## License

MIT License - feel free to use and modify for your own archiving needs.
