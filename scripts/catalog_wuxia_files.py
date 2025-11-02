#!/usr/bin/env python3
"""
Catalog Wuxia Files - Scan directories and create database mapping

Scans wuxia_individual_files directories to find book JSON files
and creates a database table mapping works to their file paths.

FILE PATH CONSTRUCTION:
-----------------------
The database stores complete file paths in work_files.full_path column.

To get file paths for a work:
    SELECT wf.full_path
    FROM work_files wf
    JOIN works w ON wf.work_id = w.work_id
    WHERE w.work_number = 'D55'
    ORDER BY wf.volume

Path pattern:
    {BASE_DIR}/wuxia_{directory_number}/{filename}

Example:
    /Users/jacki/project_files/translation_project/wuxia_individual_files/wuxia_0001/D55a_射鵰英雄傳一_金庸.json
    └─────────────────── BASE_DIR ────────────────────┘└─ dir ──┘└──────────── filename ──────────────┘

See README_WUXIA_CATALOG.md for detailed usage examples.
"""

import os
import re
import sqlite3
import argparse
from pathlib import Path
from typing import List, Dict, Tuple

# Default configuration - Use symlink relative to script location
# The project root has a symlink: translation_data -> /Users/jacki/project_files/translation_project
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DEFAULT_PROJECT_BASE = os.getenv(
    'TRANSLATION_PROJECT_DIR',
    str(PROJECT_ROOT / 'translation_data')
)

# Files to ignore
IGNORE_PATTERNS = [
    r"^summary_translated_",
    r"^wuxia_\d+_haodoo_page\.json$",
    r"^wuxia_work_summary_",
]


def should_ignore_file(filename: str) -> bool:
    """Check if file matches ignore patterns"""
    for pattern in IGNORE_PATTERNS:
        if re.match(pattern, filename):
            return True
    return False


def parse_filename(filename: str) -> Tuple[str, str, str]:
    """
    Parse filename to extract work code and volume.

    Examples:
        D55a_射鵰英雄傳一_金庸.json -> ('D55', 'a', '射鵰英雄傳一_金庸')
        D1568_劍氣珠光_王度廬.json -> ('D1568', '', '劍氣珠光_王度廬')
        D10U4_越女劍_金庸.json -> ('D10U4', '', '越女劍_金庸')
        I1046_飛鳳潛龍_梁羽生.json -> ('I1046', '', '飛鳳潛龍_梁羽生')
        J081102a_大劍師傳奇一_黃易.json -> ('J081102', 'a', '大劍師傳奇一_黃易')

    Returns:
        (work_code, volume_letter, title_author)
    """
    # Pattern 1: <letter><number><lowercase_letter>_<title>_<author>.json (e.g., D55a_, J081102a_)
    match = re.match(r'([A-Z])(\d+)([a-z])_(.+)\.json$', filename, re.IGNORECASE)
    if match:
        prefix = match.group(1).upper()
        work_num = match.group(2)
        volume = match.group(3)
        title_author = match.group(4)
        return (f'{prefix}{work_num}', volume, title_author)

    # Pattern 2: <letter><alphanumeric>_<title>_<author>.json (e.g., D10U4_, I1046_, H10O6_)
    match = re.match(r'([A-Z][A-Z0-9]+)_(.+)\.json$', filename, re.IGNORECASE)
    if match:
        work_code = match.group(1).upper()
        title_author = match.group(2)
        return (work_code, '', title_author)

    return (None, None, None)


def scan_directories(wuxia_dir: str) -> List[Dict]:
    """
    Scan all wuxia_XXXX directories and catalog JSON files.

    Args:
        wuxia_dir: Base directory containing wuxia_XXXX subdirectories

    Returns:
        List of file info dictionaries
    """
    files_info = []

    # Get all wuxia_XXXX directories
    wuxia_dirs = sorted([
        d for d in Path(wuxia_dir).iterdir()
        if d.is_dir() and d.name.startswith('wuxia_')
    ])

    print(f"Found {len(wuxia_dirs)} wuxia directories")

    for wuxia_subdir in wuxia_dirs:
        dir_number = wuxia_subdir.name.replace('wuxia_', '')

        # Find all JSON files in this directory
        for json_file in wuxia_subdir.glob('*.json'):
            filename = json_file.name

            # Skip ignored files
            if should_ignore_file(filename):
                continue

            # Parse filename
            work_num, volume, title_author = parse_filename(filename)

            if work_num is None:
                print(f"  ⚠ Could not parse: {filename}")
                continue

            file_info = {
                'directory': wuxia_subdir.name,
                'directory_number': dir_number,
                'filename': filename,
                'full_path': str(json_file),
                'work_number': work_num,
                'volume': volume,
                'title_author': title_author,
            }

            files_info.append(file_info)
            print(f"  ✓ {wuxia_subdir.name}/{filename} -> Work {work_num}{volume}")

    return files_info


def create_database_table(files_info: List[Dict], db_path: str):
    """
    Create database table and populate with file information.

    Args:
        files_info: List of file information dictionaries
        db_path: Path to SQLite database file
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create works table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS works (
            work_id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_number TEXT NOT NULL,
            title_author TEXT,
            directory_number TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create work_files table (one-to-many relationship for volumes)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS work_files (
            file_id INTEGER PRIMARY KEY AUTOINCREMENT,
            work_id INTEGER,
            volume TEXT,
            filename TEXT NOT NULL,
            full_path TEXT NOT NULL,
            directory_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (work_id) REFERENCES works(work_id)
        )
    ''')

    # Group files by work_number
    works_dict = {}
    for file_info in files_info:
        work_num = file_info['work_number']
        if work_num not in works_dict:
            works_dict[work_num] = {
                'work_number': work_num,
                'title_author': file_info['title_author'],
                'directory_number': file_info['directory_number'],
                'files': []
            }
        works_dict[work_num]['files'].append(file_info)

    # Insert works and files
    for work_num, work_data in sorted(works_dict.items()):
        # Insert work
        cursor.execute('''
            INSERT INTO works (work_number, title_author, directory_number)
            VALUES (?, ?, ?)
        ''', (work_data['work_number'], work_data['title_author'], work_data['directory_number']))

        work_id = cursor.lastrowid

        # Insert all file volumes for this work
        for file_info in sorted(work_data['files'], key=lambda x: x['volume']):
            cursor.execute('''
                INSERT INTO work_files (work_id, volume, filename, full_path, directory_name)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                work_id,
                file_info['volume'],
                file_info['filename'],
                file_info['full_path'],
                file_info['directory']
            ))

    conn.commit()

    # Print summary
    cursor.execute('SELECT COUNT(*) FROM works')
    works_count = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM work_files')
    files_count = cursor.fetchone()[0]

    print(f"\n✅ Database created successfully!")
    print(f"   Works: {works_count}")
    print(f"   Files: {files_count}")

    # Show sample data
    print(f"\n📊 Sample works:")
    cursor.execute('''
        SELECT w.work_number, w.title_author, w.directory_number, COUNT(wf.file_id) as file_count
        FROM works w
        LEFT JOIN work_files wf ON w.work_id = wf.work_id
        GROUP BY w.work_id
        ORDER BY w.work_number
        LIMIT 10
    ''')

    for row in cursor.fetchall():
        print(f"   Work {row[0]}: {row[1]} (dir: wuxia_{row[2]}, files: {row[3]})")

    conn.close()


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Catalog wuxia JSON files into a SQLite database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Environment Variables:
  TRANSLATION_PROJECT_DIR    Base directory for translation project
                             (default: /Users/jacki/project_files/translation_project)

Examples:
  # Use default paths
  %(prog)s

  # Specify custom base directory
  %(prog)s --base-dir /path/to/translation_project

  # Use environment variable
  export TRANSLATION_PROJECT_DIR=/path/to/translation_project
  %(prog)s

  # Specify all paths explicitly
  %(prog)s --wuxia-dir /path/to/wuxia_files --db-path /path/to/catalog.db
        '''
    )

    parser.add_argument(
        '--base-dir',
        default=DEFAULT_PROJECT_BASE,
        help='Base directory for translation project (default: env TRANSLATION_PROJECT_DIR or hardcoded path)'
    )
    parser.add_argument(
        '--wuxia-dir',
        help='Directory containing wuxia_XXXX subdirectories (default: BASE_DIR/wuxia_individual_files)'
    )
    parser.add_argument(
        '--db-path',
        help='Path to output SQLite database (default: BASE_DIR/wuxia_catalog.db)'
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # Determine paths
    base_dir = args.base_dir
    wuxia_dir = args.wuxia_dir or os.path.join(base_dir, 'wuxia_individual_files')
    db_path = args.db_path or os.path.join(base_dir, 'wuxia_catalog.db')

    print("=" * 70)
    print("Wuxia Files Cataloger")
    print("=" * 70)
    print()
    print(f"Base Directory: {base_dir}")
    print(f"Wuxia Directory: {wuxia_dir}")
    print(f"Database Path: {db_path}")
    print()

    # Check if directory exists
    if not Path(wuxia_dir).exists():
        print(f"❌ Error: Directory not found: {wuxia_dir}")
        return 1

    # Scan directories
    print(f"📂 Scanning: {wuxia_dir}")
    print()
    files_info = scan_directories(wuxia_dir)

    if not files_info:
        print("❌ No files found!")
        return 1

    print()
    print(f"📝 Found {len(files_info)} JSON files")
    print()

    # Create database
    print(f"💾 Creating database: {db_path}")
    create_database_table(files_info, db_path)

    return 0


if __name__ == "__main__":
    exit(main())
