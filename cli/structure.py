#!/usr/bin/env python3
"""
CLI for Content Structurer

AI-powered content structuring using OpenAI assistants.
"""

import sys
from pathlib import Path

# Add parent directory to path to import processors
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.content_structurer import main

if __name__ == "__main__":
    sys.exit(main())
