# Book JSON Cleaner

Transform raw book JSON files into clean, structured formats with discrete content blocks suitable for EPUB generation.

## Overview

This tool takes any book JSON file and transforms it into a standardized, discrete block structure. Each paragraph, heading, and content element becomes a separately-addressable block with unique IDs for internal linking and EPUB compatibility.

**No API required** - Pure JSON transformation with instant processing.

## Quick Start

```bash
python clean_input_json.py \
  --input /path/to/book.json \
  --output ./output/cleaned_book.json \
  --language zh-Hant
```

**Output**: Structured JSON with discrete blocks, EPUB IDs, and auto-detected TOC

## Features

✅ **Discrete Content Blocks** - Each paragraph/heading is a separate object
✅ **EPUB IDs** - Every block has unique ID for internal linking
✅ **TOC Auto-Detection** - Automatically identifies table of contents
✅ **Block Types** - heading_N, paragraph, text, list elements
✅ **Source References** - Maintains traceability to original
✅ **Fast Processing** - No API calls, processes instantly

## Main Tool

### `clean_input_json.py`

Transform raw JSON into discrete content blocks.

**Features:**
- No API or external dependencies required
- Instant processing (~1 second)
- Auto-detects table of contents
- Generates discrete blocks with EPUB IDs
- Supports multiple input formats

**Usage:**

```bash
# Basic usage
python clean_input_json.py --input book.json --output cleaned.json

# With language hint
python clean_input_json.py \
  --input book.json \
  --output cleaned.json \
  --language zh-Hant

# Quiet mode (no summary)
python clean_input_json.py \
  --input book.json \
  --output cleaned.json \
  --quiet
```

## Additional Tools

The project includes additional tools for advanced processing:

### `content_structuring_processor.py`
AI-powered content structuring using OpenAI assistants. Identifies content block types (narrative, dialogue, verse, etc.) for more sophisticated categorization.

Requires:
- OpenAI API key
- `translation_assistant_manager.py`

See [TRANSLATION_ASSISTANT_MANAGER_GUIDE.md](TRANSLATION_ASSISTANT_MANAGER_GUIDE.md) for details.

## Output Format

Both approaches produce the same structure:

```json
{
  "meta": {
    "title": "Book Title",
    "language": "zh-Hant"
  },
  "structure": {
    "front_matter": { "toc": [...] },
    "body": {
      "chapters": [
        {
          "id": "chapter_0001",
          "title": "Chapter Title",
          "content_blocks": [
            {
              "id": "block_0000",
              "type": "heading_3",
              "content": "...",
              "epub_id": "heading_0"
            }
          ]
        }
      ]
    },
    "back_matter": {}
  }
}
```

## Example Output

After cleaning:
```
✓ 14 chapters
✓ 677 discrete content blocks
✓ TOC auto-detected
✓ 462 KB cleaned_book.json
```

## Project Structure

```
agentic_test_project/
├── clean_input_json.py                      # Main tool: JSON cleaner
├── content_structuring_processor.py         # Optional: AI-powered structuring
├── translation_assistant_manager.py         # Helper for content_structuring
├── src/template_pkg/                        # Utilities library
│   ├── clients/
│   │   ├── openai_client.py                 # OpenAI API wrapper
│   │   └── anthropic_client.py              # Anthropic API wrapper
│   └── scraping/
│       ├── http.py                          # HTTP utilities
│       └── parse.py                         # HTML parsing
├── output/                                  # Default output directory
├── TRANSLATION_ASSISTANT_MANAGER_GUIDE.md   # Advanced tool guide
└── README.md                                # This file
```

## Requirements

### For basic JSON cleaning (clean_input_json.py):
```bash
# No dependencies required! Pure Python 3.10+
```

### For AI-powered structuring (content_structuring_processor.py):
```bash
pip install openai tqdm
```

## License

MIT
