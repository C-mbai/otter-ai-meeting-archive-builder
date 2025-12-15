# Otter.ai Meeting Archive Builder

Build a beautiful, searchable web archive of your Otter.ai meetings from backup data. Fully static, works offline, no server required.

## Features

- 🔍 **Dual search modes**: Search by summaries/metadata OR full transcript content
- 🎯 **Clickable transcripts**: Click any transcript line to jump to that audio segment
- 🎵 **Synchronized playback**: Audio automatically highlights the current transcript line
- 🌙 **Dark mode**: Toggle with persistent preference
- 📱 **Responsive design**: Works beautifully on mobile and desktop
- 🔒 **Privacy-first**: Everything runs locally, no data sent anywhere

## Quick Start

1. **Get your Otter.ai backup data:**
   - Save your Otter.ai main page as HTML (with ALL summaries expanded)
   - Download all meeting audio (.mp3) and transcript (.txt) files

2. **Follow the instructions:**
   - Read `INSTRUCTIONS_CONCISE.md` - it's designed to be shared with an AI assistant
   - Or use the included Python scripts directly (see below)

3. **Run the scripts:**
   ```bash
   python3 extract_meetings.py
   python3 generate_html.py
   ```

4. **Open `meetings.html` in your browser** - that's it!

## Repository Contents

- **`INSTRUCTIONS_CONCISE.md`** - Complete build instructions (share with AI or use as reference)
- **`extract_meetings.py`** - Extracts meeting metadata from HTML and matches with audio/transcript files
- **`generate_html.py`** - Generates the web archive HTML pages
- **`styles.css`** - Modern, responsive styling with dark mode support

## Example Output

The generated archive includes:
- Main page (`meetings.html`) with searchable meeting list
- Individual meeting pages with synchronized audio-transcript playback
- Match report (`match_report.csv`) for debugging file matching

## Requirements

- Python 3.6+
- Your Otter.ai backup data (HTML + MP3/TXT files)

## How It Works

1. **Extract**: Parses the saved Otter.ai HTML page to extract meeting metadata
2. **Match**: Intelligently matches meetings to audio/transcript files using fuzzy matching and content validation
3. **Generate**: Creates a fully static web archive with search, filters, and synchronized playback

## Privacy & Data

- All processing happens locally on your machine
- No data is sent to any server
- The generated archive works completely offline
- Your meeting data stays private

## Contributing

Found a bug or have an improvement? Pull requests welcome!

## License

MIT License - feel free to use this for your own Otter.ai archives.

---

**Note**: This tool requires you to have already exported your data from Otter.ai. It doesn't connect to Otter.ai's API or services.