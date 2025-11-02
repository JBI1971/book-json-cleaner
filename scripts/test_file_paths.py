#!/usr/bin/env python3
"""
Test File Path Construction

Demonstrates how to retrieve file paths from the wuxia catalog database.
"""

import sqlite3
import argparse
import os
from pathlib import Path

# Default configuration - Use symlink relative to script location
# The project root has a symlink: translation_data -> /Users/jacki/project_files/translation_project
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_PROJECT_BASE = os.getenv(
    'TRANSLATION_PROJECT_DIR',
    str(PROJECT_ROOT / 'translation_data')
)


def test_single_volume_work(db_path: str):
    """Test retrieving a single-volume work."""
    print("=" * 70)
    print("Test 1: Single-volume work (D60 - Snow Mountain Flying Fox)")
    print("=" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            w.work_number,
            w.title_english,
            w.author_english,
            wf.full_path
        FROM works w
        JOIN work_files wf ON w.work_id = wf.work_id
        WHERE w.work_number = 'D60'
    ''')

    row = cursor.fetchone()
    if row:
        work_num, title, author, path = row
        print(f"\nWork: {work_num}")
        print(f"Title: {title}")
        print(f"Author: {author}")
        print(f"File Path: {path}")
        print(f"File Exists: {Path(path).exists()}")

    conn.close()
    print()


def test_multi_volume_work(db_path: str):
    """Test retrieving a multi-volume work."""
    print("=" * 70)
    print("Test 2: Multi-volume work (D55 - Legend of the Condor Heroes)")
    print("=" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            w.work_number,
            w.title_english,
            w.author_english,
            wf.volume,
            wf.full_path
        FROM works w
        JOIN work_files wf ON w.work_id = wf.work_id
        WHERE w.work_number = 'D55'
        ORDER BY wf.volume
    ''')

    rows = cursor.fetchall()
    if rows:
        work_num, title, author, _, _ = rows[0]
        print(f"\nWork: {work_num}")
        print(f"Title: {title}")
        print(f"Author: {author}")
        print(f"Volumes: {len(rows)}\n")

        for work_num, title, author, volume, path in rows:
            exists = "✓" if Path(path).exists() else "✗"
            print(f"  Volume {volume}: {exists} {path}")

    conn.close()
    print()


def test_search_by_author(db_path: str):
    """Test searching works by author."""
    print("=" * 70)
    print("Test 3: Search by author (Huang Yi / 黃易)")
    print("=" * 70)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            w.work_number,
            w.title_chinese,
            w.title_english,
            COUNT(wf.file_id) as volume_count
        FROM works w
        LEFT JOIN work_files wf ON w.work_id = wf.work_id
        WHERE w.author_english = 'Huang Yi'
        GROUP BY w.work_id
        ORDER BY w.work_number
        LIMIT 5
    ''')

    print(f"\nFound works by Huang Yi:\n")
    for work_num, title_cn, title_en, vol_count in cursor.fetchall():
        print(f"  {work_num}: {title_en}")
        print(f"           {title_cn} ({vol_count} volumes)")

    conn.close()
    print()


def test_path_construction(db_path: str, base_dir: str):
    """Test manual path construction."""
    print("=" * 70)
    print("Test 4: Manual path construction")
    print("=" * 70)

    wuxia_dir = os.path.join(base_dir, 'wuxia_individual_files')

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            w.directory_number,
            wf.filename,
            wf.full_path
        FROM works w
        JOIN work_files wf ON w.work_id = wf.work_id
        WHERE w.work_number = 'D69' AND wf.volume = 'a'
    ''')

    row = cursor.fetchone()
    if row:
        dir_num, filename, stored_path = row

        # Construct path manually
        constructed_path = f"{wuxia_dir}/wuxia_{dir_num}/{filename}"

        print(f"\nDirectory Number: {dir_num}")
        print(f"Filename: {filename}")
        print(f"\nConstructed Path:")
        print(f"  {constructed_path}")
        print(f"\nStored Path:")
        print(f"  {stored_path}")
        print(f"\nPaths Match: {constructed_path == stored_path}")
        print(f"File Exists: {Path(stored_path).exists()}")

    conn.close()
    print()


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Test wuxia catalog database file path functionality',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Environment Variables:
  TRANSLATION_PROJECT_DIR    Base directory for translation project

Examples:
  # Use default paths
  %(prog)s

  # Specify custom base directory
  %(prog)s --base-dir /path/to/translation_project

  # Use environment variable
  export TRANSLATION_PROJECT_DIR=/path/to/translation_project
  %(prog)s
        '''
    )

    parser.add_argument(
        '--base-dir',
        default=DEFAULT_PROJECT_BASE,
        help='Base directory for translation project'
    )
    parser.add_argument(
        '--db-path',
        help='Path to SQLite database (default: BASE_DIR/wuxia_catalog.db)'
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # Determine paths
    base_dir = args.base_dir
    db_path = args.db_path or os.path.join(base_dir, 'wuxia_catalog.db')

    print("\n")
    print("*" * 70)
    print(" Wuxia Catalog Database - File Path Test Suite")
    print("*" * 70)
    print()
    print(f"Base Directory: {base_dir}")
    print(f"Database Path: {db_path}")
    print()

    if not Path(db_path).exists():
        print(f"❌ Error: Database not found at {db_path}")
        return 1

    test_single_volume_work(db_path)
    test_multi_volume_work(db_path)
    test_search_by_author(db_path)
    test_path_construction(db_path, base_dir)

    print("=" * 70)
    print("✅ All tests completed!")
    print("=" * 70)
    print()
    print("For more examples, see: README_WUXIA_CATALOG.md")
    print()

    return 0


if __name__ == "__main__":
    exit(main())
