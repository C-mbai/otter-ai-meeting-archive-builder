#!/usr/bin/env python3
"""
Loom Video Downloader
Downloads all videos from a list of Loom URLs using yt-dlp.
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def check_ytdlp_installed():
    """Check if yt-dlp is installed."""
    try:
        subprocess.run(['yt-dlp', '--version'],
                      capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def get_browser_cookies(browser='chrome'):
    """Get the cookie argument for yt-dlp."""
    browsers = ['chrome', 'firefox', 'safari', 'edge', 'brave']
    if browser.lower() in browsers:
        return f'--cookies-from-browser {browser.lower()}'
    return ''


def download_video(url, output_dir, cookies_arg='', dry_run=False):
    """
    Download a single Loom video with metadata.

    Args:
        url: Loom video URL
        output_dir: Directory to save the video
        cookies_arg: Browser cookie argument for authentication
        dry_run: If True, just print what would be downloaded

    Returns:
        Tuple of (success: bool, video_info: dict)
    """
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Output template: "YYYY-MM-DD - Title [video_id].ext"
    output_template = os.path.join(
        output_dir,
        '%(upload_date>%Y-%m-%d)s - %(title)s [%(id)s].%(ext)s'
    )

    # Build yt-dlp command
    cmd = [
        'yt-dlp',
        '--write-info-json',  # Save metadata
        '--write-description',  # Save description
        '--write-thumbnail',  # Save thumbnail
        '--write-subs',  # Download subtitles if available
        '--sub-format', 'srt',
        '--convert-subs', 'srt',
        '-o', output_template,
    ]

    # Add cookies if specified
    if cookies_arg:
        cmd.extend(cookies_arg.split())

    # Add URL
    cmd.append(url)

    if dry_run:
        print(f"[DRY RUN] Would execute: {' '.join(cmd)}")
        return True, {'url': url, 'dry_run': True}

    try:
        print(f"\nDownloading: {url}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"✓ Success: {url}")
            return True, {'url': url, 'status': 'success'}
        else:
            print(f"✗ Failed: {url}")
            print(f"  Error: {result.stderr}")
            return False, {'url': url, 'status': 'failed', 'error': result.stderr}

    except Exception as e:
        print(f"✗ Exception downloading {url}: {e}")
        return False, {'url': url, 'status': 'error', 'error': str(e)}


def read_urls_from_file(filepath):
    """Read video URLs from a text file (one per line)."""
    urls = []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if line and not line.startswith('#'):
                urls.append(line)
    return urls


def save_download_report(results, output_file='download_report.json'):
    """Save download results to a JSON report."""
    report = {
        'timestamp': datetime.now().isoformat(),
        'total': len(results),
        'successful': sum(1 for r in results if r.get('status') == 'success'),
        'failed': sum(1 for r in results if r.get('status') in ['failed', 'error']),
        'results': results
    }

    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)

    return report


def main():
    parser = argparse.ArgumentParser(
        description='Download Loom videos from a list of URLs',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download all videos (using Chrome cookies for auth)
  python download_loom_videos.py video_urls.txt

  # Use Firefox cookies instead
  python download_loom_videos.py video_urls.txt --browser firefox

  # Dry run to see what would be downloaded
  python download_loom_videos.py video_urls.txt --dry-run

  # Custom output directory
  python download_loom_videos.py video_urls.txt -o /path/to/downloads

  # Download without authentication (public videos only)
  python download_loom_videos.py video_urls.txt --no-cookies
        """
    )

    parser.add_argument('urls_file',
                       help='Text file containing Loom video URLs (one per line)')
    parser.add_argument('-o', '--output-dir',
                       default='downloads',
                       help='Output directory for downloaded videos (default: downloads)')
    parser.add_argument('-b', '--browser',
                       default='chrome',
                       choices=['chrome', 'firefox', 'safari', 'edge', 'brave'],
                       help='Browser to extract cookies from (default: chrome)')
    parser.add_argument('--no-cookies',
                       action='store_true',
                       help='Do not use browser cookies (only works for public videos)')
    parser.add_argument('--dry-run',
                       action='store_true',
                       help='Show what would be downloaded without actually downloading')
    parser.add_argument('--start-at',
                       type=int,
                       default=1,
                       help='Start downloading from this video number (default: 1)')

    args = parser.parse_args()

    # Check if yt-dlp is installed
    if not check_ytdlp_installed():
        print("Error: yt-dlp is not installed or not in PATH")
        print("\nInstall it with:")
        print("  pip install yt-dlp")
        print("  or: pip install -r requirements.txt")
        sys.exit(1)

    # Read URLs from file
    if not os.path.exists(args.urls_file):
        print(f"Error: File not found: {args.urls_file}")
        sys.exit(1)

    print(f"Reading URLs from: {args.urls_file}")
    urls = read_urls_from_file(args.urls_file)
    print(f"Found {len(urls)} video URLs")

    if not urls:
        print("No URLs found in file")
        sys.exit(1)

    # Prepare cookies argument
    cookies_arg = '' if args.no_cookies else get_browser_cookies(args.browser)

    if not args.no_cookies:
        print(f"Using {args.browser} browser cookies for authentication")
    else:
        print("Not using browser cookies (public videos only)")

    print(f"Output directory: {args.output_dir}")
    print(f"\nStarting downloads...\n{'='*60}")

    # Download all videos
    results = []
    start_idx = args.start_at - 1  # Convert to 0-based index

    for i, url in enumerate(urls[start_idx:], start=start_idx + 1):
        print(f"\n[{i}/{len(urls)}] Processing: {url}")
        success, info = download_video(
            url,
            args.output_dir,
            cookies_arg,
            dry_run=args.dry_run
        )
        results.append(info)

    # Save report
    if not args.dry_run:
        report_file = os.path.join(args.output_dir, 'download_report.json')
        report = save_download_report(results, report_file)

        print(f"\n{'='*60}")
        print(f"Download Summary:")
        print(f"  Total: {report['total']}")
        print(f"  Successful: {report['successful']}")
        print(f"  Failed: {report['failed']}")
        print(f"\nReport saved to: {report_file}")
    else:
        print(f"\n{'='*60}")
        print(f"[DRY RUN] Would process {len(urls)} videos")

    # Show failed URLs if any
    failed = [r for r in results if r.get('status') in ['failed', 'error']]
    if failed and not args.dry_run:
        print(f"\n⚠ Failed downloads ({len(failed)}):")
        for r in failed:
            print(f"  - {r['url']}")
            if 'error' in r:
                print(f"    Error: {r['error'][:100]}...")


if __name__ == '__main__':
    main()
