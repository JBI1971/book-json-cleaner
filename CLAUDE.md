# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Book Processing Toolkit** - Complete pipeline for processing books from raw JSON through cleaning, AI structuring, translation, footnotes, to final EPUB generation.

**Vision**: `Raw JSON → Clean → Structure → Translate → Footnotes → EPUB`

**Current Status**:
- ✅ JSON Cleaner (implemented)
- ✅ Content Structurer (implemented)
- 🚧 Translator (placeholder)
- 🚧 Footnote Generator (placeholder)
- 🚧 EPUB Builder (placeholder)

## Development Commands

### Environment Setup
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

### Running Processors

```bash
# JSON cleaning (no API needed)
python cli/clean.py --input book.json --output cleaned.json --language zh-Hant

# AI-powered structuring (requires OPENAI_API_KEY)
python cli/structure.py --input cleaned.json --output structured.json --max-workers 3

# Future processors (placeholders)
python cli/translate.py --input structured.json --output translated.json --target-lang en
python cli/footnotes.py --input translated.json --output with_footnotes.json --style chicago
python cli/build_epub.py --input with_footnotes.json --output book.epub
```

### Testing
```bash
pytest                          # Run all tests
pytest tests/test_specific.py   # Run specific test
pytest -v                       # Verbose output
pytest --cov                    # Coverage report
```

### Code Quality
```bash
black processors ai utils cli   # Format code
flake8 processors ai utils cli  # Lint code
mypy processors ai utils cli    # Type checking
```

### Package Scripts (npm)
```bash
npm run clean      # Run JSON cleaner
npm run structure  # Run content structurer
npm run test       # Run pytest
npm run lint       # Run flake8
npm run format     # Run black
```

## Architecture

### Pipeline Structure

```
processors/
├── json_cleaner.py          [IMPLEMENTED] Raw JSON → Discrete blocks
├── content_structurer.py    [IMPLEMENTED] Blocks → Semantic types
├── translator.py            [PLACEHOLDER] Translate content
├── footnote_generator.py    [PLACEHOLDER] Add scholarly notes
└── epub_builder.py          [PLACEHOLDER] Generate EPUB file

ai/
└── assistant_manager.py     [IMPLEMENTED] Manage OpenAI assistants

utils/
├── clients/                 [IMPLEMENTED] API wrappers (OpenAI, Anthropic)
└── http/                    [IMPLEMENTED] HTTP with retry logic

cli/
├── clean.py                 [IMPLEMENTED] CLI for json_cleaner
├── structure.py             [IMPLEMENTED] CLI for content_structurer
├── translate.py             [PLACEHOLDER] CLI for translator
├── footnotes.py             [PLACEHOLDER] CLI for footnote_generator
└── build_epub.py            [PLACEHOLDER] CLI for epub_builder
```

### Data Flow

```
RAW INPUT
   ↓
processors/json_cleaner.py
   → Recursive extraction from nested structures
   → TOC auto-detection
   → Block ID generation (block_0000, block_0001...)
   → EPUB ID generation (heading_0, para_1...)
   ↓
CLEANED JSON (discrete blocks)
   ↓
processors/content_structurer.py (optional)
   → Chunk text if >4000 chars (200-char overlap)
   → OpenAI Assistant API via threads
   → Semantic classification (narrative, dialogue, verse...)
   → Schema validation
   → Retry logic (3 attempts, 2s delay, 300s timeout)
   ↓
STRUCTURED JSON (semantic types)
   ↓
processors/translator.py [TODO]
   → AI-powered translation
   → Preserve structure
   ↓
TRANSLATED JSON
   ↓
processors/footnote_generator.py [TODO]
   → Cultural/historical notes
   → Pronunciation guides
   → Citation formatting
   ↓
ANNOTATED JSON
   ↓
processors/epub_builder.py [TODO]
   → EPUB 3.0 generation
   → Internal linking via block IDs
   ↓
FINAL EPUB FILE
```

## Key Implementation Details

### JSON Cleaner (processors/json_cleaner.py)

**Input Formats Supported**:
- `{chapters: [{title, content}]}` - Standard format
- `{sections: [{title, content}]}` - Alternative field names
- Content as string, HTML-like objects, or nested structures

**Block Extraction**:
- Recursive `extract_blocks_from_nodes()` handles arbitrary nesting
- Recognizes tags: h1-h6, p, div, section, article, body, ul, ol, li
- Generates sequential IDs: `block_0000`, `block_0001`...
- Creates EPUB IDs: `heading_0`, `para_1`, `text_2`, `list_3`

**TOC Detection**:
- Title keywords: "目錄", "目录", "contents", "table of contents", "toc"
- Structure heuristic (first chapter only): ≥5 lines with 70%+ having ≤15 chars

**Output Structure**:
```json
{
  "meta": {"title", "language", "schema_version", "source", "original_file"},
  "structure": {
    "front_matter": {"toc": [...]},
    "body": {"chapters": [{"id", "title", "ordinal", "content_blocks": [...]}]},
    "back_matter": {}
  }
}
```

### Content Structurer (processors/content_structurer.py)

**Classes**:
- `ProcessingConfig` - Configuration dataclass (max_retries, timeout, mode)
- `SchemaValidator` - Validates against JSON schema
- `TextChunker` - Splits large texts (max 4000 chars, 200 overlap)
- `ContentStructuringProcessor` - Main processor with retry/batch support

**Processing Modes**:
- STRICT - Fail on first error
- FLEXIBLE (default) - Retry most errors
- BEST_EFFORT - Continue despite errors

**Semantic Block Types**:
- `narrative`, `dialogue`, `verse`, `document`, `thought`, `descriptive`, `chapter_title`

**OpenAI Assistant Pattern**:
```python
thread = client.beta.threads.create()
client.beta.threads.messages.create(thread_id, role="user", content=text)
run = client.beta.threads.runs.create(thread_id, assistant_id)
# Poll until completed (max 300s)
messages = client.beta.threads.messages.list(thread_id)
# Parse JSON response
```

**Batch Processing**:
- ThreadPoolExecutor with configurable workers (default: 3)
- Rate limiting: 0.5s delay between requests
- Progress tracking with tqdm (optional)

### Assistant Manager (ai/assistant_manager.py)

**Purpose**: Centralized OpenAI assistant lifecycle management with versioning

**Storage**: `.assistants/` directory (JSON files)

**Key Methods**:
- `create_assistant(name, instructions, schema, model, temperature)`
- `get_assistant(name, version)` - version can be "v1", "v2", "latest"
- `list_assistants()` - All stored configs
- `update_assistant(name, updates)` - Modify existing
- `delete_assistant(name, version, remote=False)` - Remove with optional API deletion
- `export_assistant(name, version)` - Export config
- `import_assistant(file_path)` - Import config
- `compare_versions(name, v1, v2)` - Show differences

**Versioning**: Supports semantic versions, tracks changes, "latest" keyword

## Configuration & Environment

### Required Environment Variables
```bash
export OPENAI_API_KEY=your-key-here        # For AI features
export ANTHROPIC_API_KEY=your-key-here     # Optional alternative
```

### Default Paths
- Input: `./input/book.json`
- Output: `./output/cleaned_book.json`
- Assistants: `.assistants/` (AI configs)
- Schemas: `schemas/` (JSON schemas)

### Processing Defaults

**json_cleaner.py**:
- DEFAULT_INPUT_PATH: `./input/book.json`
- DEFAULT_OUTPUT_PATH: `./output/cleaned_book.json`
- DEFAULT_LANGUAGE: `zh-Hant`

**content_structurer.py**:
- max_retries: 3
- retry_delay: 2.0s
- rate_limit_delay: 0.5s
- timeout: 300s (5 min)
- max_workers: 3
- max_chunk_size: 4000 chars
- chunk_overlap: 200 chars

## Dependencies

From `requirements.txt`:
- `openai>=1.0.0` - OpenAI API client
- `anthropic>=0.18.0` - Anthropic API client
- `httpx>=0.24.0` - Async HTTP
- `beautifulsoup4>=4.12.0` + `lxml>=4.9.0` - HTML parsing
- `tenacity>=8.2.0` - Retry logic
- `tqdm>=4.65.0` - Progress bars
- `pytest>=7.4.0` - Testing

## Common Workflows

### Add New Block Type

1. Update `SchemaValidator.validate()` in content_structurer.py:
   ```python
   valid_types = [..., "new_type"]
   ```
2. Update assistant instructions to recognize new type
3. Update schema file if using validation

### Process Large Book

```bash
# Automatic chunking for >4000 chars
python cli/structure.py --input large_novel.txt --output result.json

# Disable chunking (may hit token limits)
python cli/structure.py --input novel.txt --no-chunking
```

### Debug AI Assistant

```bash
# List all assistants
python ai/assistant_manager.py list

# View specific config
python ai/assistant_manager.py export --name structuring --version latest

# Compare versions
python ai/assistant_manager.py compare --name structuring --version1 v1 --version2 v2
```

### Batch Processing

```bash
# Process directory of files
python cli/structure.py --input ./books/ --output ./results/ --max-workers 5
```

### Implement New Processor

1. Create file in `processors/` (e.g., `translator.py`)
2. Implement processor class with `process()` method
3. Update `processors/__init__.py` to export it
4. Create CLI in `cli/` (e.g., `translate.py`)
5. Add entry point in `pyproject.toml` [project.scripts]
6. Add npm script in `package.json`
7. Update README.md roadmap

## File Organization

### Processors Module Structure
Each processor should follow this pattern:
```python
class ProcessorName:
    def __init__(self, **config):
        """Initialize with configuration"""

    def process(self, data: Dict) -> Dict:
        """Main processing method"""

    def process_file(self, input_path: str, output_path: str):
        """File-based processing"""

def main():
    """CLI entry point with argparse"""

if __name__ == "__main__":
    exit(main())
```

### CLI Module Structure
Each CLI should wrap a processor:
```python
#!/usr/bin/env python3
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from processors.module_name import main

if __name__ == "__main__":
    sys.exit(main())
```

## Testing Notes

Current test coverage is minimal (`tests/test_sanity.py` only).

When adding tests:
- Test each processor independently
- Mock AI API calls (don't hit real APIs in tests)
- Test edge cases: empty input, malformed JSON, large files
- Test chunking boundary conditions
- Test batch processing concurrency
- Validate output schema compliance

## Error Handling Patterns

### Retry Strategy (content_structurer.py)
- 3 attempts with 2s delay
- 300s timeout per request
- Mode-dependent: FLEXIBLE retries, STRICT fails fast
- Handles: JSON parse errors, validation failures, API failures

### Schema Validation
Checks:
- `content_blocks` array exists and non-empty
- Each block has: `id`, `type`, `content`, `metadata`
- Valid block types from predefined list
- IDs start with `block_`
- Non-empty content

### Batch Processing
- ThreadPoolExecutor catches individual failures
- Continues processing remaining files (unless STRICT mode)
- Returns: `{file: {status: "success|failed", result|error}}`

## Migration Notes

### v0.1.0 → v0.2.0 (Current Refactoring)

**File Moves**:
- `clean_input_json.py` → `processors/json_cleaner.py`
- `content_structuring_processor.py` → `processors/content_structurer.py`
- `translation_assistant_manager.py` → `ai/assistant_manager.py`
- `src/template_pkg/clients/*` → `utils/clients/`
- `src/template_pkg/scraping/*` → `utils/http/`
- `TRANSLATION_ASSISTANT_MANAGER_GUIDE.md` → `docs/AI_ASSISTANT_GUIDE.md`

**CLI Changes**:
- Old: `python clean_input_json.py --input book.json`
- New: `python cli/clean.py --input book.json`

**Import Changes**:
- Old: `from clean_input_json import clean_book_json`
- New: `from processors.json_cleaner import clean_book_json`

## Roadmap Awareness

When implementing features, reference the roadmap in README.md:

- **v0.3.0**: Translator processor (language detection, glossaries)
- **v0.4.0**: Footnote generator (citation styles, cultural notes)
- **v0.5.0**: EPUB builder (EPUB 3.0, CSS themes, cover images)

Placeholders exist for all future processors with TODO comments indicating planned features.
