#!/usr/bin/env python3
"""
CLI wrapper for structure_validator.py
"""
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.structure_validator import main

if __name__ == "__main__":
    sys.exit(main())
