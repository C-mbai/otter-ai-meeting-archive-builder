# Loom Video Downloader

Download all your Loom videos locally for safe archival. Uses yt-dlp to download videos with metadata, thumbnails, and subtitles.

## Features

- Downloads videos with original quality
- Preserves metadata (title, description, upload date)
- Downloads thumbnails and subtitles (if available)
- Automatic authentication using browser cookies
- Progress tracking and error reporting
- Resume capability (skip already downloaded videos)
- Dry-run mode to preview what will be downloaded

## Prerequisites

- Python 3.6 or higher
- A browser with an active Loom session (Chrome, Firefox, Safari, Edge, or Brave)

## Quick Start

### 1. Install Dependencies

```bash
cd loom-downloader
pip install -r requirements.txt
```

This installs `yt-dlp`, the video downloader that supports Loom.

### 2. Get Your Video URLs

You've already done this! You should have 212 video URLs in your clipboard.

Create a file called `video_urls.txt` and paste all your URLs into it (one per line):

```bash
# Paste your URLs from clipboard into video_urls.txt
nano video_urls.txt
# Or use any text editor you prefer
```

Your `video_urls.txt` should look like:
```
https://www.loom.com/share/fdaa0e7196404544bae49921e7d9126f
https://www.loom.com/share/e942737e754f420891ef806ab4d8f5b4
https://www.loom.com/share/a8d114deb4dc49b395fc0afb27e24876
...
```

### 3. Download Your Videos

**Basic usage (using Chrome cookies for authentication):**
```bash
python download_loom_videos.py video_urls.txt
```

**Using a different browser:**
```bash
# Firefox
python download_loom_videos.py video_urls.txt --browser firefox

# Safari
python download_loom_videos.py video_urls.txt --browser safari

# Edge
python download_loom_videos.py video_urls.txt --browser edge

# Brave
python download_loom_videos.py video_urls.txt --browser brave
```

**Dry run (preview without downloading):**
```bash
python download_loom_videos.py video_urls.txt --dry-run
```

**Custom output directory:**
```bash
python download_loom_videos.py video_urls.txt -o /path/to/my/loom/archive
```

### 4. Find Your Videos

Downloaded videos will be in the `downloads/` folder (or your custom directory) with filenames like:
```
2024-03-15 - Team Meeting Q1 Planning [fdaa0e7196404544bae49921e7d9126f].mp4
```

Each video includes:
- `.mp4` - The video file
- `.info.json` - Full metadata (title, description, uploader, date, etc.)
- `.jpg` - Thumbnail image
- `.srt` - Subtitles (if available)
- `.description` - Video description text

## Authentication

The script uses **browser cookies** to authenticate with Loom. This means:

1. **You must be logged into Loom in your browser**
2. The script extracts your session cookies from the browser
3. No need to manually handle authentication

**Important:** If videos fail to download with authentication errors:
- Make sure you're logged into Loom in the specified browser
- Try a different browser with `--browser firefox` etc.
- Close and reopen your browser, then log into Loom again

## Advanced Usage

### Resume After Interruption

If downloads are interrupted, just run the same command again. `yt-dlp` automatically skips already-downloaded videos.

### Start from Specific Video

If you want to skip the first N videos:
```bash
python download_loom_videos.py video_urls.txt --start-at 50
```
This starts downloading from video #50.

### Public Videos Only (No Authentication)

If all your videos are public and don't require authentication:
```bash
python download_loom_videos.py video_urls.txt --no-cookies
```

### Download Report

After downloading, check `downloads/download_report.json` for:
- Which videos succeeded/failed
- Error messages for failed downloads
- Timestamp and summary statistics

## Troubleshooting

### "Error: yt-dlp is not installed"
```bash
pip install yt-dlp
```

### "Failed to download" errors

**Authentication issues:**
- Make sure you're logged into Loom in your browser
- Try `--browser firefox` or another browser
- Check that the browser you specified is installed

**Network issues:**
- Check your internet connection
- Some videos might be private/deleted
- Try downloading a single video first to test

### Videos downloading slowly

This is normal. Loom videos can be large, and yt-dlp downloads one at a time to avoid rate limiting.

For 212 videos, expect the process to take several hours depending on:
- Video file sizes
- Your internet speed
- Loom's rate limits

**Pro tip:** Run in a `screen` or `tmux` session so you can disconnect and let it run:
```bash
# Start a screen session
screen -S loom-download

# Run the download
python download_loom_videos.py video_urls.txt

# Detach with Ctrl+A, then D
# Reattach later with: screen -r loom-download
```

## File Organization

By default, videos are saved as:
```
downloads/
├── 2024-03-15 - Team Meeting [video_id].mp4
├── 2024-03-15 - Team Meeting [video_id].info.json
├── 2024-03-15 - Team Meeting [video_id].jpg
├── 2024-03-14 - Product Demo [video_id].mp4
├── ...
└── download_report.json
```

The date prefix helps sort videos chronologically, and the video ID prevents filename collisions.

## Privacy & Security

- All downloads happen **locally** on your machine
- Your browser cookies are used **only** for authenticating with Loom
- No data is sent to any third-party services
- Downloads are direct from Loom's servers via yt-dlp

## What Gets Downloaded

For each video:
- **Video file** (MP4, highest quality available)
- **Metadata JSON** (title, description, uploader, upload date, duration, view count, etc.)
- **Thumbnail** (JPG image)
- **Subtitles** (SRT format, if available)
- **Description** (Plain text file)

## Command Reference

```
usage: download_loom_videos.py [-h] [-o OUTPUT_DIR]
                              [-b {chrome,firefox,safari,edge,brave}]
                              [--no-cookies] [--dry-run] [--start-at START_AT]
                              urls_file

Options:
  urls_file              Text file with Loom URLs (one per line)
  -o, --output-dir       Output directory (default: downloads)
  -b, --browser          Browser for cookies (default: chrome)
  --no-cookies           Don't use browser cookies
  --dry-run              Preview without downloading
  --start-at N           Start from video number N
```

## Tips

1. **Do a dry-run first** to make sure everything is configured correctly:
   ```bash
   python download_loom_videos.py video_urls.txt --dry-run
   ```

2. **Test with one video** before downloading all 212:
   ```bash
   # Create a test file with just one URL
   head -1 video_urls.txt > test.txt
   python download_loom_videos.py test.txt
   ```

3. **Check the download report** to see which videos failed and why

4. **Keep the metadata JSON files** - they contain valuable information about each video

## License

This tool uses yt-dlp, which is unlicensed/public domain software.
