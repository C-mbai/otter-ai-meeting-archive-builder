# Build Instructions: Otter.ai Meeting Archive

**For Humans:** This document describes a searchable web archive of Otter.ai meetings. Skim this to understand what you're asking an AI to build, then share it with the AI.

**For AI:** This is a complete build specification. Read this and create an implementation plan, then execute it.

---

## What This Creates

A fully static, offline-capable web archive with:
- **Main page** listing all meetings with search (summaries or transcripts) and filters (recorded/all)
- **Individual meeting pages** with synchronized audio-transcript playback (click transcript lines to jump to audio, auto-highlight current line during playback)
- **Dark mode** toggle that persists preference
- **Responsive design** for mobile and desktop
- **No server required** - works offline

---

## Input Requirements

User provides:
1. **`Otter Main Page/` folder** with `Otter Voice Meeting Notes.html` (complete saved page, ALL summaries expanded)
2. **`Otter Meeting Notes [Date]/` folder** with all `.mp3` and `.txt` files (keep original Otter.ai filenames)

---

## Step 1: Extract and Match Meetings (`extract_meetings.py`)

**Goal:** Parse HTML to get meeting metadata, then match meetings to audio/transcript files.

### Extract from HTML

Parse conversation cards using `data-testid="conversation-card"`. Extract:
- **Title:** from `data-testid="conversation-title-link"` (fallback: any `<a>` in card)
- **Time/duration/attendee:** from `data-testid="subtitle-text"` (fallback: divs containing "•")
- **Summary:** from `<div class="text-sm">` (fallback: similar class names)
- **Date:** from `<div class="font-semibold">` headers (if year missing, append user's year)

**Robustness:** Add `--debug` flag that prints warnings like `"Warning: Couldn't find {field} for card {index}"` when extraction fails. Missing fields become `None`.

### Build File Index

Scan notes directory for all `.mp3` and `.txt` files. Group by base name, handling numbered duplicates like `Meeting Name (1)`, `Meeting Name (2)`. Match MP3/TXT pairs by matching stem names.

### Match Meetings to Files

**Normalize names:** Remove "Re:" prefix (case-insensitive), collapse multiple spaces, handle HTML entities, normalize Unicode punctuation (`:` vs `-`, smart quotes), remove trailing punctuation differences.

**Matching strategy:**
1. Try exact normalized name match first
2. Use fuzzy matching (difflib.SequenceMatcher) with 0.8 threshold
3. **For meetings with summaries:** Validate by comparing summary to transcript:
   - Extract meaningful words (>3 chars, exclude common words) from first 300 chars
   - Create 2-word phrases
   - Score: 40% word matches + 60% phrase matches
   - Bonus +0.2 if summary start appears in transcript
   - Accept matches with score > 0.05
4. **Log ambiguous matches:** When multiple candidates score >0.3, log top 3 with scores

**Prioritize:** Meetings with summaries MUST have recordings. Match sequentially (base file, then (1), (2), etc.).

### Output Files

1. **`meetings_data.json`:** Array of meeting objects with `id`, `name`, `time`, `duration`, `attendee`, `summary`, `date`, `has_recording`, `file` (dict with `mp3`/`txt` paths), `transcript_search` (first 5000 chars)

2. **`match_report.csv`:** Debug report with columns: `meeting_title`, `matched_mp3`, `matched_txt`, `fuzzy_ratio`, `validation_score`, `has_recording`, `match_method`. Helps spot incorrect matches quickly.

---

## Step 2: Generate HTML Pages (`generate_html.py`)

**Goal:** Create main page and individual meeting pages with all interactive features.

### Main Page (`meetings.html`)

**Structure:** Header with title (user's name), subtitle showing meeting counts in clear format: "Total: {total} meetings ({with_recordings} with recordings)" (e.g., "Total: 459 meetings (401 with recordings)"). 

**Controls layout:** Group controls logically in header:
- **Search section:** Create a grouped container with:
  - Search mode toggle buttons ("Summaries"/"Transcripts") positioned directly above the search input, visually connected
  - Search input box below the toggle
- **Filter section:** Create a grouped container with:
  - Label text "Show:" before the segmented control
  - Segmented control ("Recorded"/"All" buttons, default to "Recorded")
- **Theme toggle:** Dark mode button (separate)

**HTML structure example:**
```html
<div class="header-controls">
    <div class="search-control">
        <div class="search-mode-toggle">...</div>
        <input type="text" id="search-input" class="search-input" ...>
    </div>
    <div class="filter-control">
        <span class="filter-label">Show:</span>
        <div class="segmented-control">...</div>
    </div>
    <button class="theme-toggle">...</button>
</div>
```

Grid of meeting cards below.

**Meeting cards:** Show title (truncate to 80 chars), microphone icon (filled=recording, slashed=no recording), metadata (date/time/duration/attendee), truncated summary (300 chars). Add `data-transcript-search` attribute with first 5000 chars of transcript. Click card navigates to meeting detail page.

**JavaScript:**
- **Theme toggle:** Toggle `data-theme` on `<html>` ("light"/"dark"), save to localStorage, swap sun/moon icons
- **Search mode:** Toggle between searching title/metadata/summary vs `data-transcript-search` attribute
- **Filter:** Show/hide cards based on `has-recording` class
- **Search:** Filter cards in real-time as user types, respect current search mode

### Individual Meeting Pages (`Meetings Web Data/meeting-{id}.html`)

**Structure:** Header with back button, meeting title, metadata, full summary (if available), transcript search input, dark mode toggle. Audio player container. Transcript container with formatted transcript.

**Transcript formatting:** Parse transcript file. Lines matching `"Speaker Name MM:SS"` or `"Speaker Name H:MM:SS"` are speaker lines. Format as:
```html
<div class="speaker-line" data-time="{seconds}" data-time-display="{time}">
  <span class="speaker">Name</span> <span class="time">MM:SS</span>
</div>
```
Following lines until next speaker are transcript text:
```html
<div class="transcript-line" data-time="{seconds}" data-time-display="{time}">text</div>
```
Convert timestamps to seconds for `data-time` attribute (handle both MM:SS and H:MM:SS).

**JavaScript:**
- **Theme toggle:** Same as main page
- **Transcript search:** Filter lines by search term (case-insensitive), highlight matches with `<mark>`, hide non-matching lines (keep speaker lines visible if their transcript matches)
- **Audio-transcript sync (CRITICAL):**
  - On `timeupdate` event: Find line with highest `data-time` <= current audio time, add `.playing` class, scroll into view smoothly
  - Track `isUserSeeking` flag to prevent sync during manual seeking
  - On `seeking`/`seeked`: Update flag and sync position
- **Clickable transcript lines:** All lines with `data-time` are clickable. On click: seek audio to `data-time - 3 seconds` (min 0), start playback, highlight line, temporarily set `isUserSeeking`

---

## Step 3: Create Styles (`Meetings Web Data/styles.css`)

**Design system:** Modern, clean interface with light/dark themes. Light theme uses white cards (#ffffff) on light gray background (#fafafa), dark text (#1a1a1a). Dark theme uses dark cards (#111827) on black background (#000000), light text (#e5e7eb). Use `[data-theme="dark"]` selector for dark mode overrides.

**Key visual elements:**
- **Cards:** White/dark background, 12px border-radius, subtle shadows, hover lift effect (translateY -2px)
- **Search inputs:** Rounded (8px), blue focus ring (#3b82f6), placeholder gray (#9ca3af)
- **Segmented controls:** Pill-shaped toggle buttons, active state has white/dark background with shadow
- **Microphone icons:** SVG icons, green background (#d1fae5) for recording, red (#fee2e2) for no recording
- **Transcript:** Light gray background (#f9fafb), max-height 600px with scroll, thin custom scrollbar
- **Speaker lines:** Blue color (#3b82f6), bold, larger font
- **Playing highlight:** Blue background (rgba(59, 130, 246, 0.2)) on current line during playback
- **Clickable lines:** Pointer cursor, hover shows light blue background, smooth transitions (0.2s ease)

**Responsive:** Mobile (<768px): single column grid, stacked header controls, full-width search inputs.

**Font:** System font stack: `-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif`

---

## Step 4: Execution

1. **Identify user's folder structure** (check folder names)
2. **Update scripts:** Set `current_year` and `notes_dir` path in `extract_meetings.py`, replace company name and `notes_dir` in `generate_html.py`
3. **Run:** `python3 extract_meetings.py` (optionally with `--debug`), then `python3 generate_html.py`
4. **Review:** Check `match_report.csv` for any incorrect matches (low fuzzy_ratio or validation_score)
5. **Deliver:** `meetings.html`, `Meetings Web Data/` folder, `meetings_data.json`, `match_report.csv`

---

## Key Technical Details

**Transcript parsing:** Handle `MM:SS` and `H:MM:SS` formats. Speaker names may include letters, numbers, spaces, `&`, `.`, `-`, `'`. If format doesn't match, treat as regular transcript text.

**Audio sync:** `timeupdate` fires ~4x/second. Find best matching line (highest time <= current time), add `.playing` class for visual highlight, scroll smoothly to center. Prevent sync during user seeking with flag.

**File matching:** Fuzzy match threshold 0.8, validation score threshold 0.05 (intentionally low). Log ambiguous matches (score 0.3-0.6) for review.

**Performance:** Limit transcript search index to first 5000 chars per meeting to keep HTML size reasonable.

**Paths:** Use relative paths for all assets (audio files, CSS, navigation between pages).

---

## Edge Cases

- **HTML structure changes:** Fallback selectors catch most variations, debug mode shows warnings
- **Missing fields:** Set to `None`, don't fail script
- **Malformed timestamps:** Display as regular transcript text
- **Short summaries:** May have low validation scores (expected), rely on fuzzy matching
- **Identical meeting names:** Match sequentially to numbered files

---

## Feature Checklist

- ✅ Modern UI with clean design
- ✅ Dark mode toggle (persists in localStorage)
- ✅ Filter: Recorded/All (defaults to Recorded)
- ✅ Search mode toggle: Summaries vs Transcripts
- ✅ Search meetings by title, summary, metadata (Summaries mode)
- ✅ Search meetings by transcript content (Transcripts mode)
- ✅ Search within transcripts on detail pages with highlighting
- ✅ Click transcript lines to jump to audio playback
- ✅ Audio-transcript synchronization (highlights current line during playback)
- ✅ Microphone status icons
- ✅ Responsive mobile design
- ✅ Audio players with HTML5 controls
- ✅ Meeting summaries & metadata
- ✅ Fully static - works offline, no server required

---

**End of Instructions**