# Wuxia Catalog Database Guide

## Quick Start

### Configuration (Git-Portable)

The scripts are now git-portable! Set your base directory using:

```bash
# Method 1: Environment variable (recommended)
export TRANSLATION_PROJECT_DIR="/path/to/your/translation_project"

# Method 2: Command-line argument
python scripts/catalog_wuxia_files.py --base-dir /path/to/translation_project

# Method 3: Use default (if on original machine)
python scripts/catalog_wuxia_files.py
```

See [SETUP_GUIDE.md](./SETUP_GUIDE.md) for detailed configuration options.

## Database Location

**Default:** `${TRANSLATION_PROJECT_DIR}/wuxia_catalog.db`

Example:
```
/Users/jacki/project_files/translation_project/wuxia_catalog.db
```

## Table Structure

### `works` Table
Main catalog of wuxia works with metadata

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `work_id` | INTEGER | Primary key | 1 |
| `work_number` | TEXT | Work code from filename | `D55`, `I1046`, `J081102` |
| `title_author` | TEXT | Original filename title_author | `射鵰英雄傳三_金庸` |
| `directory_number` | TEXT | Directory number (4 digits) | `0001` |
| `author_chinese` | TEXT | Chinese author name | `金庸` |
| `title_chinese` | TEXT | Chinese title | `射鵰英雄傳` |
| `author_english` | TEXT | English author name | `Jin Yong` |
| `title_english` | TEXT | English title | `Legend of the Condor Heroes` |
| `category_english` | TEXT | English category | `Wuxia` |
| `summary` | TEXT | Work summary (if available) | `...` |
| `work_link` | TEXT | Link to source | `https://...` |

### `work_files` Table
Individual file volumes for each work

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `file_id` | INTEGER | Primary key | 1 |
| `work_id` | INTEGER | Foreign key to works | 1 |
| `volume` | TEXT | Volume letter (a, b, c...) or empty | `a` |
| `filename` | TEXT | JSON filename | `D55a_射鵰英雄傳一_金庸.json` |
| `full_path` | TEXT | Absolute file path | `/Users/jacki/project_files/.../D55a_...json` |
| `directory_name` | TEXT | Directory name | `wuxia_0001` |

## How to Construct File Paths

### Method 1: Use the `full_path` column (Recommended)

The easiest way - the database stores the complete absolute path:

```python
import sqlite3

conn = sqlite3.connect('/Users/jacki/project_files/translation_project/wuxia_catalog.db')
cursor = conn.cursor()

# Get all file paths for work D55 (射鵰英雄傳)
cursor.execute('''
    SELECT wf.volume, wf.full_path
    FROM work_files wf
    JOIN works w ON wf.work_id = w.work_id
    WHERE w.work_number = 'D55'
    ORDER BY wf.volume
''')

for volume, path in cursor.fetchall():
    print(f"Volume {volume}: {path}")

conn.close()
```

**Output:**
```
Volume a: /Users/jacki/project_files/translation_project/wuxia_individual_files/wuxia_0001/D55a_射鵰英雄傳一_金庸.json
Volume b: /Users/jacki/project_files/translation_project/wuxia_individual_files/wuxia_0001/D55b_射鵰英雄傳二_金庸.json
Volume c: /Users/jacki/project_files/translation_project/wuxia_individual_files/wuxia_0001/D55c_射鵰英雄傳三_金庸.json
Volume d: /Users/jacki/project_files/translation_project/wuxia_individual_files/wuxia_0001/D55d_射鵰英雄傳四_金庸.json
```

### Method 2: Construct from components

If you need to construct paths manually:

```python
BASE_DIR = "/Users/jacki/project_files/translation_project/wuxia_individual_files"

# Path construction formula:
# {BASE_DIR}/wuxia_{directory_number}/{filename}

cursor.execute('''
    SELECT w.directory_number, wf.filename
    FROM works w
    JOIN work_files wf ON w.work_id = wf.work_id
    WHERE w.work_number = 'D55'
    ORDER BY wf.volume
''')

for dir_num, filename in cursor.fetchall():
    path = f"{BASE_DIR}/wuxia_{dir_num}/{filename}"
    print(path)
```

## Common Queries

### Get all volumes for a work by English title

```sql
SELECT
    w.work_number,
    w.title_english,
    w.author_english,
    wf.volume,
    wf.full_path
FROM works w
JOIN work_files wf ON w.work_id = wf.work_id
WHERE w.title_english LIKE '%Condor Heroes%'
ORDER BY w.work_number, wf.volume;
```

### Get all works by an author

```sql
SELECT
    w.work_number,
    w.title_chinese,
    w.title_english,
    COUNT(wf.file_id) as volume_count
FROM works w
LEFT JOIN work_files wf ON w.work_id = wf.work_id
WHERE w.author_english = 'Jin Yong'
GROUP BY w.work_id
ORDER BY w.work_number;
```

### Get file path for specific work and volume

```sql
SELECT wf.full_path
FROM works w
JOIN work_files wf ON w.work_id = wf.work_id
WHERE w.work_number = 'D55' AND wf.volume = 'a';
```

Result: `/Users/jacki/project_files/translation_project/wuxia_individual_files/wuxia_0001/D55a_射鵰英雄傳一_金庸.json`

### List all multi-volume works

```sql
SELECT
    w.work_number,
    w.author_chinese,
    w.title_chinese,
    w.title_english,
    COUNT(wf.file_id) as volumes
FROM works w
JOIN work_files wf ON w.work_id = wf.work_id
GROUP BY w.work_id
HAVING COUNT(wf.file_id) > 1
ORDER BY volumes DESC, w.work_number;
```

## File Path Examples

### Single-volume work
```
Work Number: D60
Directory: wuxia_0007
Filename: D60_雪山飛狐_金庸.json
Full Path: /Users/jacki/project_files/translation_project/wuxia_individual_files/wuxia_0007/D60_雪山飛狐_金庸.json
```

### Multi-volume work
```
Work Number: D70
Directory: wuxia_0225
Volumes: 7 (a, b, c, d, e, f, g)

Full Paths:
/Users/jacki/project_files/translation_project/wuxia_individual_files/wuxia_0225/D70a_覆雨翻雲一_黃易.json
/Users/jacki/project_files/translation_project/wuxia_individual_files/wuxia_0225/D70b_覆雨翻雲二_黃易.json
/Users/jacki/project_files/translation_project/wuxia_individual_files/wuxia_0225/D70c_覆雨翻雲三_黃易.json
...
/Users/jacki/project_files/translation_project/wuxia_0225/D70g_覆雨翻雲七_黃易.json
```

### Work with non-D prefix
```
Work Number: I1046
Directory: wuxia_0125
Filename: I1046_飛鳳潛龍_梁羽生.json
Full Path: /Users/jacki/project_files/translation_project/wuxia_individual_files/wuxia_0125/I1046_飛鳳潛龍_梁羽生.json
```

## Python Helper Function

```python
import sqlite3
from pathlib import Path
from typing import List, Optional

class WuxiaCatalog:
    def __init__(self, db_path: str = '/Users/jacki/project_files/translation_project/wuxia_catalog.db'):
        self.db_path = db_path

    def get_work_files(self, work_number: str) -> List[dict]:
        """
        Get all file paths for a work.

        Args:
            work_number: Work code (e.g., 'D55', 'I1046')

        Returns:
            List of dicts with volume, filename, and full_path
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                wf.volume,
                wf.filename,
                wf.full_path
            FROM work_files wf
            JOIN works w ON wf.work_id = w.work_id
            WHERE w.work_number = ?
            ORDER BY wf.volume
        ''', (work_number,))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

    def search_by_english_title(self, title_search: str) -> List[dict]:
        """
        Search works by English title.

        Args:
            title_search: Search term

        Returns:
            List of matching works with metadata
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute('''
            SELECT
                w.work_number,
                w.author_chinese,
                w.author_english,
                w.title_chinese,
                w.title_english,
                w.directory_number,
                COUNT(wf.file_id) as volume_count
            FROM works w
            LEFT JOIN work_files wf ON w.work_id = wf.work_id
            WHERE w.title_english LIKE ?
            GROUP BY w.work_id
            ORDER BY w.work_number
        ''', (f'%{title_search}%',))

        results = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return results

# Usage example:
catalog = WuxiaCatalog()

# Get all files for a work
files = catalog.get_work_files('D55')
for f in files:
    print(f"Volume {f['volume']}: {f['full_path']}")

# Search by English title
results = catalog.search_by_english_title('Condor')
for work in results:
    print(f"{work['work_number']}: {work['title_english']} ({work['volume_count']} volumes)")
```

## Database Statistics

- **Total Works**: 639
- **Total Files**: 702
- **Unique Directories**: 630
- **Works with English Metadata**: 639
- **Multi-volume Works**: ~100+ works

## Regenerating the Catalog

To rebuild the database from scratch:

```bash
# Set your base directory (if not already set)
export TRANSLATION_PROJECT_DIR="/path/to/translation_project"

# Or use command-line arguments
python scripts/catalog_wuxia_files.py --base-dir /path/to/translation_project
python scripts/enrich_catalog_with_csv.py --base-dir /path/to/translation_project

# Or if using environment variable or defaults
python scripts/catalog_wuxia_files.py
python scripts/enrich_catalog_with_csv.py
```

This will create a fresh database at `${TRANSLATION_PROJECT_DIR}/wuxia_catalog.db`.

### Testing Your Setup

```bash
# Run tests to verify everything works
python scripts/test_file_paths.py

# Or with custom path
python scripts/test_file_paths.py --base-dir /path/to/translation_project
```

### Command-Line Help

All scripts support `--help`:

```bash
python scripts/catalog_wuxia_files.py --help
python scripts/enrich_catalog_with_csv.py --help
python scripts/test_file_paths.py --help
```
