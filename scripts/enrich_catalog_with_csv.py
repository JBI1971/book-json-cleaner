#!/usr/bin/env python3
"""
Enrich Wuxia Catalog Database with CSV Data

Reads works.csv and adds English metadata to the database:
- Initial_Author_English
- Initial_Title_English
- Category_English
- Summary
"""

import csv
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


def add_columns_to_database(db_path: str):
    """Add new columns to works table if they don't exist."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get existing columns
    cursor.execute("PRAGMA table_info(works)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    # Add new columns if they don't exist
    new_columns = {
        'author_english': 'TEXT',
        'title_english': 'TEXT',
        'category_english': 'TEXT',
        'summary': 'TEXT',
        'author_chinese': 'TEXT',
        'title_chinese': 'TEXT',
        'work_link': 'TEXT'
    }

    for col_name, col_type in new_columns.items():
        if col_name not in existing_columns:
            cursor.execute(f'ALTER TABLE works ADD COLUMN {col_name} {col_type}')
            print(f"  ✓ Added column: {col_name}")

    conn.commit()
    conn.close()


def load_csv_data(csv_path: str):
    """Load CSV data into a dictionary keyed by work_key (directory name)."""
    csv_data = {}

    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            work_key = row['work_key']  # e.g., "wuxia_0001"
            # Extract directory number (e.g., "0001" from "wuxia_0001")
            dir_num = work_key.replace('wuxia_', '')
            csv_data[dir_num] = {
                'author_english': row.get('Initial_Author_English', ''),
                'title_english': row.get('Initial_Title_English', ''),
                'category_english': row.get('Category_English', ''),
                'summary': row.get('Summary', ''),
                'author_chinese': row.get('author_chinese', ''),
                'title_chinese': row.get('title_chinese', ''),
                'work_link': row.get('work_link', '')
            }

    print(f"✓ Loaded {len(csv_data)} entries from CSV")
    return csv_data


def enrich_database(csv_data, db_path: str):
    """Update database with CSV data based on directory_number."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get all works
    cursor.execute('SELECT work_id, directory_number FROM works')
    works = cursor.fetchall()

    updated_count = 0
    missing_count = 0

    for work_id, dir_number in works:
        if dir_number in csv_data:
            data = csv_data[dir_number]
            cursor.execute('''
                UPDATE works
                SET author_english = ?,
                    title_english = ?,
                    category_english = ?,
                    summary = ?,
                    author_chinese = ?,
                    title_chinese = ?,
                    work_link = ?
                WHERE work_id = ?
            ''', (
                data['author_english'],
                data['title_english'],
                data['category_english'],
                data['summary'],
                data['author_chinese'],
                data['title_chinese'],
                data['work_link'],
                work_id
            ))
            updated_count += 1
        else:
            missing_count += 1
            print(f"  ⚠ No CSV data for directory: wuxia_{dir_number}")

    conn.commit()
    conn.close()

    print(f"\n✅ Updated {updated_count} works")
    print(f"⚠  {missing_count} works missing CSV data")


def verify_enrichment(db_path: str):
    """Show sample enriched data."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    print("\n📊 Sample enriched works:")
    cursor.execute('''
        SELECT work_number, title_author, author_english, title_english, category_english
        FROM works
        WHERE author_english IS NOT NULL AND author_english != ''
        ORDER BY directory_number
        LIMIT 10
    ''')

    for row in cursor.fetchall():
        work_num, title_auth, auth_en, title_en, cat_en = row
        print(f"   Work {work_num}: {auth_en} - {title_en}")
        print(f"              原文: {title_auth}")
        if cat_en:
            print(f"              類別: {cat_en}")
        print()

    conn.close()


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Enrich wuxia catalog database with CSV metadata',
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

  # Specify paths explicitly
  %(prog)s --csv /path/to/works.csv --db /path/to/catalog.db
        '''
    )

    parser.add_argument(
        '--base-dir',
        default=DEFAULT_PROJECT_BASE,
        help='Base directory for translation project (default: env TRANSLATION_PROJECT_DIR or hardcoded path)'
    )
    parser.add_argument(
        '--csv',
        '--csv-path',
        dest='csv_path',
        help='Path to works.csv file (default: BASE_DIR/works.csv)'
    )
    parser.add_argument(
        '--db',
        '--db-path',
        dest='db_path',
        help='Path to SQLite database (default: BASE_DIR/wuxia_catalog.db)'
    )

    return parser.parse_args()


def main():
    args = parse_args()

    # Determine paths
    base_dir = args.base_dir
    csv_path = args.csv_path or os.path.join(base_dir, 'works.csv')
    db_path = args.db_path or os.path.join(base_dir, 'wuxia_catalog.db')

    print("=" * 70)
    print("Wuxia Catalog Database Enrichment")
    print("=" * 70)
    print()
    print(f"Base Directory: {base_dir}")
    print(f"CSV Path: {csv_path}")
    print(f"Database Path: {db_path}")
    print()

    # Check if CSV exists
    if not Path(csv_path).exists():
        print(f"❌ Error: CSV not found: {csv_path}")
        return 1

    # Check if database exists
    if not Path(db_path).exists():
        print(f"❌ Error: Database not found: {db_path}")
        return 1

    # Add columns
    print("📝 Adding new columns to database...")
    add_columns_to_database(db_path)
    print()

    # Load CSV data
    print("📂 Loading CSV data...")
    csv_data = load_csv_data(csv_path)
    print()

    # Enrich database
    print("💾 Enriching database with CSV data...")
    enrich_database(csv_data, db_path)

    # Verify
    verify_enrichment(db_path)

    return 0


if __name__ == "__main__":
    exit(main())
