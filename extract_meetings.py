#!/usr/bin/env python3
"""
Extract meeting names from Otter.ai HTML and match them with downloaded audio/transcript files.
"""

import re
import os
import json
from pathlib import Path
from html import unescape
from collections import defaultdict
from urllib.parse import quote, unquote
import difflib
from difflib import SequenceMatcher

def extract_meetings_from_html(html_path):
    """Extract meeting names and metadata from the saved Otter.ai HTML page."""
    with open(html_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    meetings = []
    
    # Find all conversation cards with data-testid="conversation-card"
    card_pattern = r'<div[^>]*role="link"[^>]*data-testid="conversation-card"[^>]*>(.*?)</div></div></div></div>'
    cards = re.findall(card_pattern, content, re.DOTALL)
    
    # Find date headers - they appear before conversation cards
    # Pattern: <div class="font-semibold">Friday, Mar 15 , 2024</div>
    date_pattern = r'<div class="font-semibold">([^<]+)</div>'
    date_headers = re.findall(date_pattern, content)
    
    # Split content by date headers to match dates to meetings
    # This gives us sections where each section starts with a date
    sections = re.split(r'<div class="font-semibold">([^<]+)</div>', content)
    
    # Process sections: every other element starting from index 1 is a date
    date_to_meetings = {}
    current_date = None
    
    # Determine the current year from folder name or assume 2025
    # Based on folder name "Otter Meeting Notes Dec 12 2025"
    current_year = "2025"
    
    for i in range(1, len(sections), 2):  # Every other element is a date
        if i + 1 < len(sections):
            date_str = sections[i].strip()
            section_content = sections[i + 1]
            
            # Check if date has a year (4 digits)
            if re.search(r'\d{4}', date_str):
                # Date already has a year
                current_date = date_str
            else:
                # Date doesn't have a year - add the current year (2025)
                # Format: "Wednesday, Dec 10" -> "Wednesday, Dec 10, 2025"
                if date_str and len(date_str) > 5:
                    # Clean up any trailing spaces and add year
                    date_str = date_str.rstrip()
                    if not date_str.endswith(','):
                        date_str += ','
                    current_date = f"{date_str} {current_year}"
                elif current_date:
                    # Use the last date if current is invalid
                    pass
                else:
                    # Skip if no valid date
                    continue
            
            # Find all conversation cards in this section
            section_cards = re.findall(card_pattern, section_content, re.DOTALL)
            
            # Extract meetings from cards in this section
            for card_html in section_cards:
                meeting = {}
                
                # Extract title
                title_match = re.search(r'<a[^>]*data-testid="conversation-title-link"[^>]*>([^<]+)</a>', card_html)
                if title_match:
                    meeting['name'] = unescape(title_match.group(1)).strip()
                else:
                    continue
                
                # Extract subtitle (time, duration, attendee)
                subtitle_match = re.search(r'<div[^>]*data-testid="subtitle-text"[^>]*>([^<]+)</div>', card_html)
                if subtitle_match:
                    subtitle = unescape(subtitle_match.group(1)).strip()
                    parts = [p.strip() for p in subtitle.split('•')]
                    meeting['time'] = parts[0] if len(parts) > 0 else None
                    if len(parts) > 1:
                        if re.search(r'\d+\s*(?:min|sec|h|hour)', parts[1], re.IGNORECASE):
                            meeting['duration'] = parts[1]
                            meeting['attendee'] = parts[2] if len(parts) > 2 else None
                        else:
                            meeting['duration'] = None
                            meeting['attendee'] = parts[1]
                    else:
                        meeting['duration'] = None
                        meeting['attendee'] = None
                else:
                    meeting['time'] = None
                    meeting['duration'] = None
                    meeting['attendee'] = None
                
                # Extract summary
                summary_match = re.search(r'<div class="text-sm">([^<]+)</div>', card_html)
                if summary_match:
                    summary = unescape(summary_match.group(1)).strip()
                    summary = re.sub(r'\s*Show less\s*$', '', summary, flags=re.IGNORECASE)
                    meeting['summary'] = summary if summary else None
                else:
                    meeting['summary'] = None
                
                # Assign date (with year)
                meeting['date'] = current_date
                
                meetings.append(meeting)
    
    return meetings

def build_file_index(notes_dir):
    """Build an index of all audio and transcript files."""
    notes_path = Path(notes_dir)
    files = {}
    
    # Group files by base name
    file_groups = defaultdict(list)
    
    for file_path in notes_path.glob('*.mp3'):
        base_name = file_path.stem
        file_groups[base_name].append({
            'mp3': str(file_path),
            'base_name': base_name,
            'modified': file_path.stat().st_mtime
        })
    
    for file_path in notes_path.glob('*.txt'):
        base_name = file_path.stem
        if base_name in file_groups:
            for entry in file_groups[base_name]:
                if entry['base_name'] == base_name:
                    entry['txt'] = str(file_path)
                    break
        else:
            file_groups[base_name].append({
                'txt': str(file_path),
                'base_name': base_name,
                'modified': file_path.stat().st_mtime
            })
    
    # Process groups to handle numbered files
    for base_name, entries in file_groups.items():
        match = re.match(r'^(.+?)\s*\((\d+)\)$', base_name)
        if match:
            actual_base = match.group(1).strip()
            number = int(match.group(2))
            if actual_base not in files:
                files[actual_base] = []
            files[actual_base].append({
                'number': number,
                'base_name': base_name,
                **entries[0]
            })
        else:
            files[base_name] = entries
    
    # Sort numbered entries
    for base_name in files:
        if isinstance(files[base_name], list) and len(files[base_name]) > 0 and 'number' in files[base_name][0]:
            files[base_name].sort(key=lambda x: x.get('number', 0))
    
    return files

def normalize_name(name):
    """Normalize a meeting name for comparison."""
    name = ' '.join(name.split())
    name = re.sub(r'^Re:\s*', '', name, flags=re.IGNORECASE)
    name = name.replace('&amp;', '&').replace('&', '&')
    return name.strip()

def fuzzy_match(html_name, file_names, threshold=0.8):
    """Find the best matching file name using fuzzy matching."""
    html_normalized = normalize_name(html_name)
    
    best_match = None
    best_score = 0
    
    for file_name in file_names:
        file_normalized = normalize_name(file_name)
        
        if html_normalized.lower() == file_normalized.lower():
            return file_name, 1.0
        
        score = difflib.SequenceMatcher(None, html_normalized.lower(), file_normalized.lower()).ratio()
        
        if html_normalized.lower() in file_normalized.lower() or file_normalized.lower() in html_normalized.lower():
            score = max(score, 0.85)
        
        if score > best_score:
            best_score = score
            best_match = file_name
    
    if best_score >= threshold:
        return best_match, best_score
    return None, best_score

def validate_match_by_summary(meeting, file_info, notes_dir):
    """Validate if a meeting matches a file by comparing summary with transcript content."""
    if not meeting.get('summary') or 'txt' not in file_info:
        return 0.0
    
    summary = meeting.get('summary', '').lower()
    if not summary:
        return 0.0
    
    try:
        txt_path = Path(notes_dir) / file_info['txt'] if isinstance(file_info['txt'], str) else file_info['txt']
        if not txt_path.exists():
            return 0.0
        
        with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
            transcript = f.read().lower()
        
        # Extract meaningful words from summary (skip common words)
        common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
        
        summary_words = summary[:300].split()
        # Filter to meaningful words (longer than 3 chars, not common words)
        meaningful_words = [w.lower().strip('.,!?;:()[]{}"\'-') for w in summary_words 
                          if len(w.strip('.,!?;:()[]{}"\'-')) > 3 and w.lower().strip('.,!?;:()[]{}"\'-') not in common_words]
        
        # Also create 2-word phrases for better matching
        key_phrases = []
        for i in range(len(meaningful_words) - 1):
            phrase = f"{meaningful_words[i]} {meaningful_words[i+1]}"
            if len(phrase) > 6:
                key_phrases.append(phrase)
        
        # Check how many words and phrases appear in transcript
        word_matches = sum(1 for word in meaningful_words[:15] if word in transcript)
        phrase_matches = sum(1 for phrase in key_phrases[:10] if phrase in transcript)
        
        # Score based on word and phrase matches
        if len(meaningful_words) > 0:
            word_score = word_matches / min(len(meaningful_words), 15)
        else:
            word_score = 0.0
        
        if len(key_phrases) > 0:
            phrase_score = phrase_matches / min(len(key_phrases), 10)
        else:
            phrase_score = 0.0
        
        # Combined score (weighted toward phrases)
        score = (word_score * 0.4 + phrase_score * 0.6)
        
        # Bonus if summary start appears in transcript
        summary_start = summary[:150].lower()
        # Remove punctuation for comparison
        summary_start_clean = re.sub(r'[^\w\s]', ' ', summary_start)
        transcript_clean = re.sub(r'[^\w\s]', ' ', transcript)
        if summary_start_clean[:50] in transcript_clean:
            score = min(score + 0.2, 1.0)
        
        return score
    except Exception as e:
        return 0.0

def parse_date_to_timestamp(date_str):
    """Parse date string to approximate timestamp for comparison."""
    if not date_str:
        return None
    
    # Extract year
    year_match = re.search(r'(\d{4})', date_str)
    if not year_match:
        return None
    
    year = int(year_match.group(1))
    
    # Extract month name
    month_map = {
        'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
        'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
    }
    month = None
    for month_name, month_num in month_map.items():
        if month_name in date_str.lower():
            month = month_num
            break
    
    if not month:
        return None
    
    # Extract day
    day_match = re.search(r',\s*(\w+)\s+(\d+)', date_str)
    if day_match:
        day = int(day_match.group(2))
    else:
        # Try alternative format
        day_match = re.search(r'\s+(\d+)', date_str)
        if day_match:
            day = int(day_match.group(1))
        else:
            return None
    
    # Create approximate timestamp (midday)
    import datetime
    try:
        dt = datetime.datetime(year, month, day, 12, 0, 0)
        return dt.timestamp()
    except:
        return None

def match_meetings_to_files(html_meetings, file_index, notes_dir):
    """Match meetings from HTML with files using improved algorithm."""
    matched_meetings = []
    used_files = set()
    
    # Manual overrides based on user verification
    manual_overrides = {
        # Format: (meeting_name, date_keyword): file_name
        ('Thursday Catch up', 'Nov 20'): 'Thursday Catch up',  # User verified: base file
        ('Andy Lai', 'Aug 7'): 'Andy Lai - 60 Minutes Call(1)',  # User verified: manually added file
    }
    
    # Group meetings by normalized name
    meetings_by_name = defaultdict(list)
    for i, meeting in enumerate(html_meetings):
        name = meeting.get('name', '')
        if name:
            meetings_by_name[normalize_name(name)].append((i, meeting))
    
    # Track matches temporarily
    temp_matches = {}
    
    # Process each meeting name group
    for normalized_name, meeting_list in meetings_by_name.items():
        # Find matching file group
        file_group_name = normalized_name
        if normalized_name not in file_index:
            # Try fuzzy match
            best_match, score = fuzzy_match(meeting_list[0][1].get('name', ''), file_index.keys())
            if best_match and score >= 0.8:
                file_group_name = best_match
        
        if file_group_name not in file_index:
            continue
        
        file_entry = file_index[file_group_name]
        available_files = []
        
        if isinstance(file_entry, list):
            available_files = file_entry.copy()
        else:
            available_files = [file_entry] if isinstance(file_entry, dict) else list(file_entry)
        
        # Filter out already used files
        available_files = [f for f in available_files if f.get('base_name', '') not in used_files]
        
        if not available_files:
            continue
        
        # Sort files by number if they have numbers, otherwise keep order
        def get_file_number(file_info):
            base = file_info.get('base_name', '')
            match = re.match(r'.*\((\d+)\)$', base)
            if match:
                return int(match.group(1))
            return 0  # Base file (no number) comes first
        
        available_files.sort(key=get_file_number)
        
        # Prioritize meetings with summaries - validate matches using summary content
        meetings_with_summary = [(idx, m) for idx, m in meeting_list if m.get('summary')]
        meetings_without_summary = [(idx, m) for idx, m in meeting_list if not m.get('summary')]
        
        # For meetings with summaries, validate each potential match
        validated_matches = []
        used_files_set = set()
        
        if meetings_with_summary:
            # Score all potential matches
            match_scores = []
            for idx, meeting in meetings_with_summary:
                for file_info in available_files:
                    score = validate_match_by_summary(meeting, file_info, notes_dir)
                    match_scores.append((score, idx, meeting, file_info))
            
            # Group by file - find best meeting for each file
            file_to_best_match = {}
            for score, idx, meeting, file_info in match_scores:
                file_name = file_info.get('base_name', '')
                if file_name not in file_to_best_match or score > file_to_best_match[file_name][0]:
                    file_to_best_match[file_name] = (score, idx, meeting, file_info)
            
            # Assign files to meetings (highest scores first)
            assigned_meetings = set()
            assigned_files = set()
            
            # Sort by score descending
            best_matches = sorted(file_to_best_match.values(), reverse=True, key=lambda x: x[0])
            
            for score, idx, meeting, file_info in best_matches:
                file_name = file_info.get('base_name', '')
                # Only assign if meeting not assigned AND file not assigned
                if idx not in assigned_meetings and file_name not in assigned_files:
                    # Accept matches with any positive score
                    if score > 0.05:
                        validated_matches.append((idx, meeting, file_info))
                        assigned_meetings.add(idx)
                        assigned_files.add(file_name)
                        used_files_set.add(file_name)
        
        # Second pass: Match remaining meetings with summaries sequentially
        # If there's a summary, there MUST be a recording - match by order
        remaining_summary_meetings = [(idx, m) for idx, m in meetings_with_summary 
                                      if idx not in [x[0] for x in validated_matches]]
        
        # Get remaining files (sorted by number)
        remaining_files = [f for f in available_files if f.get('base_name', '') not in used_files_set]
        remaining_files.sort(key=get_file_number)
        
        # Match sequentially - HTML order to file order
        for idx, meeting in remaining_summary_meetings:
            if remaining_files:
                file_info = remaining_files.pop(0)
                validated_matches.append((idx, meeting, file_info))
                used_files_set.add(file_info.get('base_name', ''))
        
        # Third pass: Match remaining meetings without summaries
        # BUT ONLY if all meetings with summaries are matched first
        remaining_meetings = [(idx, m) for idx, m in meeting_list 
                             if idx not in [x[0] for x in validated_matches]]
        
        # Separate remaining meetings with and without summaries
        remaining_with_summary = [(idx, m) for idx, m in remaining_meetings if m.get('summary')]
        remaining_without_summary = [(idx, m) for idx, m in remaining_meetings if not m.get('summary')]
        
        # Match remaining meetings with summaries first (even if validation failed)
        for idx, meeting in remaining_with_summary:
            if remaining_files:
                file_info = remaining_files.pop(0)
                validated_matches.append((idx, meeting, file_info))
                used_files_set.add(file_info.get('base_name', ''))
        
        # Then match remaining meetings without summaries
        for idx, meeting in remaining_without_summary:
            if remaining_files:
                file_info = remaining_files.pop(0)
                validated_matches.append((idx, meeting, file_info))
                used_files_set.add(file_info.get('base_name', ''))
                break
        
        chosen_matches = validated_matches
        
        # Store matches
        for idx, meeting, file_info in chosen_matches:
            temp_matches[idx] = file_info
            used_files.add(file_info.get('base_name', ''))
    
    # Build final meeting list
    for i, html_meeting in enumerate(html_meetings):
        meeting_name = html_meeting.get('name', '')
        if not meeting_name:
            continue
        
        matched_file = temp_matches.get(i)
        
        # If not matched yet and has summary, try validation-based matching
        # This is a second pass to catch meetings with summaries that weren't matched in first pass
        if not matched_file and html_meeting.get('summary'):
            # Look for files that might match by name variations
            potential_files = []
            
            # Try exact name
            html_normalized = normalize_name(meeting_name)
            if html_normalized in file_index:
                file_entry = file_index[html_normalized]
                if isinstance(file_entry, list):
                    potential_files.extend(file_entry)
                else:
                    potential_files.append(file_entry)
            
            # Try fuzzy match
            best_match, score = fuzzy_match(meeting_name, file_index.keys())
            if best_match and best_match != html_normalized:
                file_entry = file_index[best_match]
                if isinstance(file_entry, list):
                    potential_files.extend(file_entry)
                else:
                    potential_files.append(file_entry)
            
            # Try name variations
            name_variations = [
                meeting_name.replace(' - 60 Minutes Call', ''),
                meeting_name.replace('60 Minutes Call', '60 Minute Call'),
                meeting_name.replace('60 Minutes Call', '60 Min Call'),
                meeting_name.replace('Open working session', 'Open work session - no agenda'),
                meeting_name.replace('Open work session - no agenda', 'Open working session'),
            ]
            
            for variant in name_variations:
                variant_normalized = normalize_name(variant)
                if variant_normalized in file_index and variant_normalized != html_normalized:
                    file_entry = file_index[variant_normalized]
                    if isinstance(file_entry, list):
                        potential_files.extend(file_entry)
                    else:
                        potential_files.append(file_entry)
            
            # Score and match - prefer unused files but allow reusing if score is high
            best_file = None
            best_score = 0
            best_is_unused = False
            
            for file_info in potential_files:
                file_name = file_info.get('base_name', '')
                is_unused = file_name not in used_files
                score = validate_match_by_summary(html_meeting, file_info, notes_dir)
                
                # Prefer unused files, but accept used files if score is very high
                if (is_unused and score > best_score and score > 0.1) or \
                   (not is_unused and score > best_score and score > 0.3 and not best_is_unused):
                    best_score = score
                    best_file = file_info
                    best_is_unused = is_unused
            
            if best_file:
                matched_file = best_file
                used_files.add(best_file.get('base_name', ''))
        
        # If still not matched, try basic fuzzy matching
        if not matched_file:
            html_normalized = normalize_name(meeting_name)
            best_match, score = fuzzy_match(meeting_name, file_index.keys())
            
            if best_match and best_match not in used_files:
                file_entry = file_index[best_match]
                if isinstance(file_entry, list):
                    for file_info in file_entry:
                        if file_info.get('base_name', '') not in used_files:
                            matched_file = file_info
                            used_files.add(file_info.get('base_name', ''))
                            break
                else:
                    file_list = file_entry if isinstance(file_entry, list) else [file_entry]
                    if file_list and file_list[0].get('base_name', '') not in used_files:
                        matched_file = file_list[0]
                        used_files.add(matched_file.get('base_name', ''))
        
        # Extract transcript content for searching if file exists
        transcript_content = None
        if matched_file and 'txt' in matched_file:
            try:
                txt_path = Path(notes_dir) / matched_file['txt'] if isinstance(matched_file['txt'], str) else matched_file['txt']
                if txt_path.exists():
                    with open(txt_path, 'r', encoding='utf-8', errors='ignore') as f:
                        transcript_content = f.read()[:5000]  # First 5000 chars for search indexing
            except:
                transcript_content = None
        
        meeting_entry = {
            'id': len(matched_meetings),
            'name': meeting_name,
            'time': html_meeting.get('time'),
            'duration': html_meeting.get('duration'),
            'attendee': html_meeting.get('attendee'),
            'summary': html_meeting.get('summary'),
            'date': html_meeting.get('date'),
            'has_recording': matched_file is not None,
            'file': matched_file,
            'transcript_search': transcript_content  # First portion of transcript for searching
        }
        
        matched_meetings.append(meeting_entry)
    
    return matched_meetings

def main():
    """Main function to extract and match meetings."""
    base_dir = Path(__file__).parent
    html_path = base_dir / 'Otter Main Page' / 'Otter Voice Meeting Notes.html'
    notes_dir = base_dir / 'Otter Meeting Notes Dec 12 2025'
    
    print("Extracting meetings from HTML...")
    html_meetings = extract_meetings_from_html(html_path)
    print(f"Found {len(html_meetings)} meetings in HTML")
    
    print("\nBuilding file index...")
    file_index = build_file_index(notes_dir)
    print(f"Found {len(file_index)} unique file groups")
    
    print("\nMatching meetings to files (validating with summaries)...")
    matched_meetings = match_meetings_to_files(html_meetings, file_index, notes_dir)
    
    with_recording = sum(1 for m in matched_meetings if m['has_recording'])
    without_recording = len(matched_meetings) - with_recording
    
    print(f"\nMatching complete:")
    print(f"  Total meetings: {len(matched_meetings)}")
    print(f"  With recordings: {with_recording}")
    print(f"  Without recordings: {without_recording}")
    
    output_file = base_dir / 'meetings_data.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(matched_meetings, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved meeting data to {output_file}")
    
    return matched_meetings

if __name__ == '__main__':
    main()