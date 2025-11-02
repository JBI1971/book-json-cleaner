# Symlink Setup Instructions

## For Project Setup Scripts

This project requires a symlink to be created during project initialization.

### Symlink Details

**Name:** `translation_data`

**Target:** `/Users/jacki/project_files/translation_project`

**Location:** Project root directory

**Type:** Directory symlink

### Command to Create

From the project root directory:

```bash
ln -sf /Users/jacki/project_files/translation_project translation_data
```

### Verification

After creation, the symlink should exist:

```bash
ls -la | grep translation_data
# Should show: translation_data -> /Users/jacki/project_files/translation_project

# Test it works:
ls translation_data/
# Should show: works.csv, wuxia_catalog.db, wuxia_individual_files/
```

### For Automated Setup Scripts

If you're creating an automated project setup script, include this step:

```python
import os
from pathlib import Path

def create_symlinks(project_root):
    """Create required symlinks for the project."""

    # Define symlink
    symlink_name = "translation_data"
    symlink_target = "/Users/jacki/project_files/translation_project"
    symlink_path = project_root / symlink_name

    # Remove existing symlink if present
    if symlink_path.exists() or symlink_path.is_symlink():
        symlink_path.unlink()

    # Create symlink
    os.symlink(symlink_target, symlink_path)
    print(f"✓ Created symlink: {symlink_name} -> {symlink_target}")

# Usage in setup script:
project_root = Path(__file__).parent
create_symlinks(project_root)
```

### Why This Symlink?

All wuxia catalog scripts use this symlink to access:
- `wuxia_individual_files/` - JSON source files (640 directories)
- `works.csv` - Metadata CSV file
- `wuxia_catalog.db` - SQLite database

The scripts automatically resolve paths relative to the project root:

```python
# Scripts use this pattern:
PROJECT_ROOT = Path(__file__).parent.parent
DEFAULT_DATA_DIR = PROJECT_ROOT / 'translation_data'
```

This keeps the project git-portable while maintaining access to large data files outside the repository.

### Configuration in env.yml

The symlink is documented in `env.yml`:

```yaml
symlinks:
  - name: translation_data
    target: /Users/jacki/project_files/translation_project
    type: directory
    description: "Symlink to translation project data directory"
```

### Excluded from Git

The symlink is listed in `.gitignore`:

```gitignore
# Symlinks (created during setup, not in git)
translation_data
```

This ensures each developer/deployment creates their own symlink pointing to their local data directory.
