#!/usr/bin/env python3
"""
Fathom Video Downloader
Downloads all videos from Fathom.video using their API.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import requests
from dotenv import load_dotenv


class FathomDownloader:
    """Downloads videos and metadata from Fathom.video using their API."""

    API_BASE = "https://api.fathom.video/api/v1"

    def __init__(self, api_key, output_dir='downloads'):
        self.api_key = api_key
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

    def check_ffmpeg(self):
        """Check if ffmpeg is installed."""
        try:
            subprocess.run(['ffmpeg', '-version'],
                          capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def sanitize_filename(self, filename):
        """Sanitize filename by removing invalid characters."""
        # Remove invalid characters
        filename = re.sub(r'[<>:"/\\|?*]', '', filename)
        # Replace multiple spaces with single space
        filename = re.sub(r'\s+', ' ', filename)
        # Trim and limit length
        filename = filename.strip()[:200]
        return filename

    def list_meetings(self, limit=100):
        """
        List all meetings from Fathom API with pagination.

        Args:
            limit: Number of meetings per page (max 100)

        Returns:
            List of meeting objects
        """
        all_meetings = []
        next_cursor = None

        print("Fetching meetings from Fathom API...")

        while True:
            params = {
                'limit': limit,
                'include_transcript': 'true'
            }

            if next_cursor:
                params['next_cursor'] = next_cursor

            try:
                response = requests.get(
                    f'{self.API_BASE}/meetings',
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                data = response.json()

                meetings = data.get('items', [])
                all_meetings.extend(meetings)

                print(f"  Fetched {len(meetings)} meetings (total: {len(all_meetings)})")

                # Check for next page
                next_cursor = data.get('next_cursor')
                if not next_cursor:
                    break

            except requests.exceptions.RequestException as e:
                print(f"Error fetching meetings: {e}")
                break

        print(f"\nTotal meetings found: {len(all_meetings)}")
        return all_meetings

    def download_video(self, share_url, output_path):
        """
        Download video from Fathom using ffmpeg.

        Args:
            share_url: Fathom share URL (e.g., https://fathom.video/share/xxxxx)
            output_path: Path to save the video

        Returns:
            True if successful, False otherwise
        """
        # Construct m3u8 URL
        video_url = f"{share_url}/video.m3u8"

        # Build ffmpeg command
        cmd = [
            'ffmpeg',
            '-i', video_url,
            '-c', 'copy',  # Copy without re-encoding
            '-y',  # Overwrite output file
            str(output_path)
        ]

        try:
            print(f"  Downloading video...")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            if result.returncode == 0:
                return True
            else:
                print(f"  ffmpeg error: {result.stderr[:200]}")
                return False

        except subprocess.TimeoutExpired:
            print(f"  Download timeout (>1 hour)")
            return False
        except Exception as e:
            print(f"  Download error: {e}")
            return False

    def save_metadata(self, meeting, base_path):
        """
        Save meeting metadata to JSON file.

        Args:
            meeting: Meeting object from API
            base_path: Base path for output files (without extension)
        """
        metadata = {
            'id': meeting.get('id'),
            'title': meeting.get('title') or meeting.get('meeting_title', 'Untitled'),
            'created_at': meeting.get('created_at'),
            'scheduled_start_time': meeting.get('scheduled_start_time'),
            'duration_minutes': meeting.get('duration_minutes'),
            'share_url': meeting.get('share_url'),
            'url': meeting.get('url'),
            'participants': meeting.get('participants', []),
            'default_summary': meeting.get('default_summary'),
            'action_items': meeting.get('action_items', []),
            'transcript': meeting.get('transcript', [])
        }

        with open(f"{base_path}.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        # Save transcript separately as text
        if metadata.get('transcript'):
            with open(f"{base_path}_transcript.txt", 'w', encoding='utf-8') as f:
                for entry in metadata['transcript']:
                    speaker = entry.get('speaker', 'Unknown')
                    text = entry.get('text', '')
                    timestamp = entry.get('start', 0)
                    f.write(f"[{timestamp:.1f}s] {speaker}: {text}\n\n")

        # Save summary separately
        if metadata.get('default_summary'):
            with open(f"{base_path}_summary.txt", 'w', encoding='utf-8') as f:
                f.write(metadata['default_summary'])

    def download_all(self, dry_run=False, limit=None):
        """
        Download all videos and metadata.

        Args:
            dry_run: If True, only list what would be downloaded
            limit: Maximum number of videos to download (for testing)

        Returns:
            Download report dict
        """
        # Check ffmpeg
        if not dry_run and not self.check_ffmpeg():
            print("Error: ffmpeg is not installed or not in PATH")
            print("\nInstall ffmpeg:")
            print("  Mac: brew install ffmpeg")
            print("  Ubuntu: sudo apt install ffmpeg")
            sys.exit(1)

        # Fetch all meetings
        meetings = self.list_meetings()

        if not meetings:
            print("No meetings found")
            return {'total': 0, 'successful': 0, 'failed': 0, 'results': []}

        if limit:
            meetings = meetings[:limit]
            print(f"\nLimiting to first {limit} meetings")

        print(f"\n{'='*60}")
        print(f"Starting downloads...")
        print(f"{'='*60}\n")

        results = []

        for i, meeting in enumerate(meetings, 1):
            title = meeting.get('title') or meeting.get('meeting_title', 'Untitled')
            share_url = meeting.get('share_url')
            created_at = meeting.get('created_at', '')

            # Extract date for filename
            date_str = 'unknown-date'
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    date_str = dt.strftime('%Y-%m-%d')
                except:
                    pass

            # Create filename
            safe_title = self.sanitize_filename(title)
            filename_base = f"{date_str} - {safe_title}"
            output_base = self.output_dir / filename_base
            output_video = f"{output_base}.mp4"

            print(f"[{i}/{len(meetings)}] {title}")
            print(f"  Date: {date_str}")
            print(f"  Share URL: {share_url}")

            if dry_run:
                print(f"  [DRY RUN] Would download to: {output_video}")
                results.append({
                    'title': title,
                    'share_url': share_url,
                    'status': 'dry_run'
                })
                continue

            # Check if already downloaded
            if os.path.exists(output_video):
                print(f"  ✓ Already exists, skipping video download")
                # Still save/update metadata
                self.save_metadata(meeting, str(output_base))
                results.append({
                    'title': title,
                    'share_url': share_url,
                    'status': 'skipped'
                })
                print()
                continue

            # Save metadata
            self.save_metadata(meeting, str(output_base))
            print(f"  ✓ Metadata saved")

            # Download video
            if share_url:
                success = self.download_video(share_url, output_video)

                if success:
                    print(f"  ✓ Video downloaded")
                    results.append({
                        'title': title,
                        'share_url': share_url,
                        'status': 'success'
                    })
                else:
                    print(f"  ✗ Video download failed")
                    results.append({
                        'title': title,
                        'share_url': share_url,
                        'status': 'failed',
                        'error': 'Video download failed'
                    })
            else:
                print(f"  ✗ No share URL available")
                results.append({
                    'title': title,
                    'share_url': None,
                    'status': 'failed',
                    'error': 'No share URL'
                })

            print()

        # Generate report
        report = {
            'timestamp': datetime.now().isoformat(),
            'total': len(results),
            'successful': sum(1 for r in results if r['status'] == 'success'),
            'skipped': sum(1 for r in results if r['status'] == 'skipped'),
            'failed': sum(1 for r in results if r['status'] == 'failed'),
            'results': results
        }

        if not dry_run:
            report_path = self.output_dir / 'download_report.json'
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)

            print(f"{'='*60}")
            print(f"Download Summary:")
            print(f"  Total: {report['total']}")
            print(f"  Successful: {report['successful']}")
            print(f"  Skipped (already downloaded): {report['skipped']}")
            print(f"  Failed: {report['failed']}")
            print(f"\nReport saved to: {report_path}")

        return report


def main():
    parser = argparse.ArgumentParser(
        description='Download Fathom videos using the API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all videos
  python download_fathom_videos.py

  # Dry run to see what would be downloaded
  python download_fathom_videos.py --dry-run

  # Download only first 5 videos (for testing)
  python download_fathom_videos.py --limit 5

  # Use custom API key
  python download_fathom_videos.py --api-key YOUR_API_KEY

  # Custom output directory
  python download_fathom_videos.py -o /path/to/downloads
        """
    )

    parser.add_argument('--api-key',
                       help='Fathom API key (or set FATHOM_API_KEY env var)')
    parser.add_argument('-o', '--output-dir',
                       default='downloads',
                       help='Output directory for downloads (default: downloads)')
    parser.add_argument('--dry-run',
                       action='store_true',
                       help='Show what would be downloaded without downloading')
    parser.add_argument('--limit',
                       type=int,
                       help='Limit number of videos to download (for testing)')

    args = parser.parse_args()

    # Load .env file
    load_dotenv()

    # Get API key
    api_key = args.api_key or os.getenv('FATHOM_API_KEY')

    if not api_key:
        print("Error: Fathom API key required")
        print("\nProvide it via:")
        print("  1. --api-key argument")
        print("  2. FATHOM_API_KEY environment variable")
        print("  3. Create .env file with FATHOM_API_KEY=your_key")
        sys.exit(1)

    # Create downloader and run
    downloader = FathomDownloader(api_key, args.output_dir)
    downloader.download_all(dry_run=args.dry_run, limit=args.limit)


if __name__ == '__main__':
    main()
