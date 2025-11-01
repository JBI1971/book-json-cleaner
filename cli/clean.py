#!/usr/bin/env python3
"""
CLI for JSON Cleaner

Clean raw book JSON into structured format with discrete content blocks.
"""

import sys
from pathlib import Path

# Add parent directory to path to import processors
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.json_cleaner import main

if __name__ == "__main__":
    sys.exit(main())
