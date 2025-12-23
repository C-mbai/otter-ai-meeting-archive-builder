#!/usr/bin/env python3
"""Extract failed URLs from download_report.json for retry."""

import json
import sys

def extract_failed_urls(report_file='downloads/download_report.json', output_file='retry_urls.txt'):
    """Extract failed URLs from download report."""

    with open(report_file, 'r') as f:
        report = json.load(f)

    # Get all failed URLs
    failed = [
        r['url'] for r in report['results']
        if r.get('status') in ['failed', 'error']
    ]

    if not failed:
        print("No failed downloads found!")
        return

    # Write to file
    with open(output_file, 'w') as f:
        f.write('\n'.join(failed) + '\n')

    print(f"Found {len(failed)} failed downloads:")
    for i, url in enumerate(failed, 1):
        print(f"  {i}. {url}")

    print(f"\nSaved to: {output_file}")
    print(f"\nTo retry, run:")
    print(f"  python download_loom_videos.py {output_file}")

if __name__ == '__main__':
    report_file = sys.argv[1] if len(sys.argv) > 1 else 'downloads/download_report.json'
    extract_failed_urls(report_file)
