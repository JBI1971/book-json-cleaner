# Book Processing Toolkit

Complete toolkit for processing books through the entire pipeline: JSON cleaning, AI-powered structuring, translation, footnote generation, and EPUB building.

## Vision: Full Book Processing Pipeline

```
Raw JSON → Clean → Structure → Translate → Footnotes → EPUB
```

### Current Status

✅ **JSON Cleaner** - Transform raw book JSON into discrete content blocks
✅ **Content Structurer** - AI-powered semantic analysis (narrative, dialogue, etc.)
🚧 **Translator** - Coming soon
🚧 **Footnote Generator** - Coming soon
🚧 **EPUB Builder** - Coming soon

## Quick Start

### Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# For development
pip install -r requirements-dev.txt
```

### Usage

#### 1. Clean JSON (No API Required)
```bash
python cli/clean.py --input book.json --output cleaned.json --language zh-Hant
```

#### 2. AI-Powered Structuring (Requires OPENAI_API_KEY)
```bash
export OPENAI_API_KEY=your-key-here
python cli/structure.py --input cleaned.json --output structured.json
```

#### 3. Translation (Coming Soon)
```bash
python cli/translate.py --input structured.json --output translated.json --target-lang en
```

#### 4. Footnotes (Coming Soon)
```bash
python cli/footnotes.py --input translated.json --output with_footnotes.json
```

#### 5. Build EPUB (Coming Soon)
```bash
python cli/build_epub.py --input with_footnotes.json --output book.epub
```

## Project Structure

```
book-processing-toolkit/
├── processors/              # Pipeline processors
│   ├── json_cleaner.py         ✅ Clean raw JSON
│   ├── content_structurer.py   ✅ AI semantic analysis
│   ├── translator.py           🚧 Translation (placeholder)
│   ├── footnote_generator.py   🚧 Footnotes (placeholder)
│   └── epub_builder.py         🚧 EPUB (placeholder)
│
├── ai/                      # AI assistant management
│   ├── assistant_manager.py    OpenAI assistant lifecycle
│   └── assistants/             Stored assistant configs
│
├── utils/                   # Reusable utilities
│   ├── clients/                API client wrappers
│   │   ├── openai_client.py
│   │   └── anthropic_client.py
│   └── http/                   HTTP & web utilities
│       ├── http.py             Retry logic
│       └── parse.py            HTML parsing
│
├── cli/                     # Command-line interfaces
│   ├── clean.py                JSON cleaning CLI
│   ├── structure.py            Structuring CLI
│   ├── translate.py            Translation CLI (placeholder)
│   ├── footnotes.py            Footnotes CLI (placeholder)
│   └── build_epub.py           EPUB CLI (placeholder)
│
├── schemas/                 # JSON schemas
├── docs/                    # Documentation
├── tests/                   # Test suite
│
├── requirements.txt         # Core dependencies
├── requirements-dev.txt     # Dev dependencies
└── README.md               # This file
```

## Features

### JSON Cleaner (Implemented)

✅ **Discrete Content Blocks** - Each paragraph/heading is a separate object
✅ **EPUB IDs** - Every block has unique ID for internal linking
✅ **TOC Auto-Detection** - Identifies table of contents
✅ **Block Types** - heading_1-6, paragraph, text, list elements
✅ **Source References** - Maintains traceability
✅ **Fast Processing** - No API calls, instant results

### Content Structurer (Implemented)

✅ **Semantic Analysis** - Identifies narrative, dialogue, verse, etc.
✅ **OpenAI Assistants** - Uses AI for content classification
✅ **Batch Processing** - Multi-threaded with progress tracking
✅ **Retry Logic** - Robust error handling
✅ **Schema Validation** - Ensures output quality
✅ **Chunking** - Handles large texts (>4000 chars)

### Translator (Planned)

🚧 AI-powered translation
🚧 Multi-language support
🚧 Glossary integration
🚧 Format preservation

### Footnote Generator (Planned)

🚧 Cultural/historical notes
🚧 Pronunciation guides (pinyin)
🚧 Multiple citation styles
🚧 Global deduplication

### EPUB Builder (Planned)

🚧 EPUB 3.0 generation
🚧 Custom CSS styling
🚧 Cover image support
🚧 Navigation documents
🚧 Internal linking via block IDs

## Output Format

All processors maintain a consistent JSON structure:

```json
{
  "meta": {
    "title": "Book Title",
    "language": "zh-Hant",
    "schema_version": "2.0.0"
  },
  "structure": {
    "front_matter": {
      "toc": [...]
    },
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

## Environment Variables

```bash
# Required for AI-powered features
export OPENAI_API_KEY=your-openai-key

# Optional: Alternative AI provider
export ANTHROPIC_API_KEY=your-anthropic-key
```

## Development

### Run Tests
```bash
make test
# or
pytest
```

### Code Formatting
```bash
black processors ai utils cli
```

### Linting
```bash
flake8 processors ai utils cli
```

## Documentation

- **[CLAUDE.md](CLAUDE.md)** - Architecture guide for Claude Code
- **[docs/AI_ASSISTANT_GUIDE.md](docs/AI_ASSISTANT_GUIDE.md)** - OpenAI assistant management

## Roadmap

### v0.2.0 (Current)
- ✅ Restructured as toolkit
- ✅ Created placeholders for future processors
- ✅ Proper package structure
- ✅ CLI entry points

### v0.3.0 (Next)
- 🚧 Implement translator processor
- 🚧 Add language detection improvements
- 🚧 Glossary/terminology support

### v0.4.0 (Future)
- 🚧 Implement footnote generator
- 🚧 Citation style support (Chicago, MLA, APA)
- 🚧 Cultural/historical annotations

### v0.5.0 (Future)
- 🚧 Implement EPUB builder
- 🚧 Custom CSS themes
- 🚧 Cover image integration

## Contributing

This project is under active development. Contributions welcome!

## License

MIT
