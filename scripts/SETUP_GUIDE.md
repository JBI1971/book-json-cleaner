# Wuxia Catalog Scripts - Setup Guide

## Overview

The wuxia catalog scripts are now **git-portable** and can work with any base directory location. They support three methods for configuration:

1. **Environment variables** (recommended for git repos)
2. **Command-line arguments**
3. **Default paths** (fallback)

## Configuration Methods

### Method 1: Environment Variable (Recommended for Git)

Set the `TRANSLATION_PROJECT_DIR` environment variable to point to your data directory:

```bash
# In your shell profile (~/.bashrc, ~/.zshrc, etc.)
export TRANSLATION_PROJECT_DIR="/path/to/your/translation_project"

# Or set it temporarily for a session
export TRANSLATION_PROJECT_DIR="/Users/jacki/project_files/translation_project"
```

Then run scripts normally:

```bash
python scripts/catalog_wuxia_files.py
python scripts/enrich_catalog_with_csv.py
python scripts/test_file_paths.py
```

### Method 2: Command-Line Arguments

Pass paths directly when running scripts:

```bash
# Using --base-dir
python scripts/catalog_wuxia_files.py --base-dir /path/to/translation_project

# Or specify each path individually
python scripts/catalog_wuxia_files.py \
  --wuxia-dir /path/to/wuxia_individual_files \
  --db-path /path/to/wuxia_catalog.db

python scripts/enrich_catalog_with_csv.py \
  --csv /path/to/works.csv \
  --db /path/to/wuxia_catalog.db
```

### Method 3: Default Paths (Fallback)

If no environment variable or argument is provided, scripts use the hardcoded default:
```
/Users/jacki/project_files/translation_project
```

## Expected Directory Structure

Your translation project directory should have this structure:

```
translation_project/
├── wuxia_individual_files/
│   ├── wuxia_0001/
│   │   ├── D55a_射鵰英雄傳一_金庸.json
│   │   ├── D55b_射鵰英雄傳二_金庸.json
│   │   └── ...
│   ├── wuxia_0002/
│   └── ...
├── works.csv
└── wuxia_catalog.db (created by scripts)
```

## Script Usage

### 1. catalog_wuxia_files.py

Scans directories and creates the SQLite database.

```bash
# Basic usage (uses env var or default)
python scripts/catalog_wuxia_files.py

# With custom base directory
python scripts/catalog_wuxia_files.py --base-dir /custom/path

# With specific paths
python scripts/catalog_wuxia_files.py \
  --wuxia-dir /data/wuxia_files \
  --db-path /output/catalog.db

# View help
python scripts/catalog_wuxia_files.py --help
```

**Output:**
- Creates `wuxia_catalog.db` with `works` and `work_files` tables
- Catalogs all valid JSON files from wuxia_XXXX directories

### 2. enrich_catalog_with_csv.py

Enriches the database with English metadata from CSV.

```bash
# Basic usage
python scripts/enrich_catalog_with_csv.py

# With custom paths
python scripts/enrich_catalog_with_csv.py \
  --csv /path/to/works.csv \
  --db /path/to/wuxia_catalog.db

# View help
python scripts/enrich_catalog_with_csv.py --help
```

**Output:**
- Adds English columns to `works` table
- Populates with data from works.csv

### 3. test_file_paths.py

Tests database functionality and path construction.

```bash
# Basic usage
python scripts/test_file_paths.py

# With custom base directory
python scripts/test_file_paths.py --base-dir /custom/path

# View help
python scripts/test_file_paths.py --help
```

**Output:**
- Runs 4 test suites
- Verifies file paths exist
- Tests path construction

## Git Repository Setup

### For Contributors

When cloning the repository, set up your environment:

```bash
# Clone the repository
git clone <repo-url>
cd <repo-directory>

# Set your local data directory
export TRANSLATION_PROJECT_DIR="/your/local/path/to/translation_project"

# Add to your shell profile for persistence
echo 'export TRANSLATION_PROJECT_DIR="/your/local/path"' >> ~/.bashrc
```

### .gitignore

The repository should ignore data files:

```gitignore
# Data directories (not in git)
/Users/jacki/project_files/

# Database files
*.db
*.db-journal

# CSV data files
works.csv
```

### Environment Variable Template

Create a `.env.template` file in the repository:

```bash
# Copy this to .env and set your local paths
TRANSLATION_PROJECT_DIR=/path/to/your/translation_project
```

Users can then copy and customize:
```bash
cp .env.template .env
# Edit .env with your paths
source .env
```

## Complete Workflow

### Initial Setup (First Time)

```bash
# 1. Set environment variable
export TRANSLATION_PROJECT_DIR="/path/to/translation_project"

# 2. Catalog all files
python scripts/catalog_wuxia_files.py

# 3. Enrich with CSV data
python scripts/enrich_catalog_with_csv.py

# 4. Test everything works
python scripts/test_file_paths.py
```

### Updating After New Files Added

```bash
# Re-run catalog (will recreate database)
rm $TRANSLATION_PROJECT_DIR/wuxia_catalog.db
python scripts/catalog_wuxia_files.py

# Re-enrich
python scripts/enrich_catalog_with_csv.py
```

## Troubleshooting

### Error: "Directory not found"

**Problem:** Scripts can't find your data directory.

**Solution:**
```bash
# Check your environment variable
echo $TRANSLATION_PROJECT_DIR

# If not set, set it
export TRANSLATION_PROJECT_DIR="/correct/path"

# Or use command-line argument
python scripts/catalog_wuxia_files.py --base-dir /correct/path
```

### Error: "CSV not found" or "Database not found"

**Problem:** Files aren't in expected locations.

**Solution:**
```bash
# Check your directory structure
ls -la $TRANSLATION_PROJECT_DIR/

# Should see:
# - wuxia_individual_files/
# - works.csv
# - wuxia_catalog.db (if already created)

# Or specify paths explicitly
python scripts/enrich_catalog_with_csv.py \
  --csv /actual/path/to/works.csv \
  --db /actual/path/to/wuxia_catalog.db
```

### Verifying Setup

```bash
# Show what paths scripts will use
python scripts/catalog_wuxia_files.py --help
python scripts/enrich_catalog_with_csv.py --help

# Test with environment variable
echo "TRANSLATION_PROJECT_DIR=$TRANSLATION_PROJECT_DIR"
python scripts/test_file_paths.py
```

## Examples for Different Setups

### Development Machine (macOS)
```bash
export TRANSLATION_PROJECT_DIR="/Users/yourname/Documents/translation_project"
python scripts/catalog_wuxia_files.py
```

### Linux Server
```bash
export TRANSLATION_PROJECT_DIR="/home/user/data/translation_project"
python scripts/catalog_wuxia_files.py
```

### Windows (PowerShell)
```powershell
$env:TRANSLATION_PROJECT_DIR="C:\Users\YourName\translation_project"
python scripts\catalog_wuxia_files.py
```

### Docker Container
```bash
docker run -it \
  -v /host/data:/data \
  -e TRANSLATION_PROJECT_DIR=/data/translation_project \
  python-image \
  python scripts/catalog_wuxia_files.py
```

## Script Portability Summary

✅ **Git-friendly:** No hardcoded absolute paths in repository
✅ **Flexible:** Three configuration methods
✅ **Cross-platform:** Works on macOS, Linux, Windows
✅ **Docker-ready:** Environment variable based
✅ **Team-friendly:** Each developer can use their own paths

All scripts now support:
- `--help` flag for usage information
- Environment variable configuration
- Command-line path overrides
- Sensible defaults
