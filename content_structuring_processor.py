#!/usr/bin/env python3
"""
Content Structuring Processor for Chinese Novels
Processes raw Chinese text and identifies content blocks using the structuring assistant
"""

import os
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI
from translation_assistant_manager import TranslationAssistantManager

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    print("Install tqdm for progress bars: pip install tqdm")


# =============================================================================
# CONFIGURATION
# =============================================================================

# Processing Configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 2.0
DEFAULT_RATE_LIMIT_DELAY = 0.5
DEFAULT_TIMEOUT = 300
DEFAULT_MAX_WORKERS = 3
DEFAULT_CHECKPOINT_INTERVAL = 5

# Chunking Configuration
DEFAULT_MAX_CHUNK_SIZE = 4000  # characters per chunk
DEFAULT_CHUNK_OVERLAP = 200  # character overlap between chunks

# Output Configuration
OUTPUT_DIR = "output"
CHECKPOINT_SUFFIX = "_checkpoint.json"
ERROR_SUFFIX = "_error.json"
SUMMARY_SUFFIX = "_summary.json"

# Logging Configuration
LOG_LEVEL = "INFO"
LOG_FORMAT = '%(asctime)s - %(levelname)s - [%(threadName)s] - %(message)s'

# Schema path
SCHEMA_PATH = "assistant_configs/schemas/structuring_schema.json"

# Setup logging
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format=LOG_FORMAT)
logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class ProcessingMode(Enum):
    """Processing mode options"""
    STRICT = "strict"
    FLEXIBLE = "flexible"
    BEST_EFFORT = "best_effort"


@dataclass
class ProcessingConfig:
    """Configuration for content structuring processing"""
    max_retries: int = DEFAULT_MAX_RETRIES
    retry_delay: float = DEFAULT_RETRY_DELAY
    rate_limit_delay: float = DEFAULT_RATE_LIMIT_DELAY
    timeout: int = DEFAULT_TIMEOUT
    mode: ProcessingMode = ProcessingMode.FLEXIBLE
    save_partial_results: bool = True
    continue_on_error: bool = True
    validate_schema: bool = True


@dataclass
class TextChunk:
    """Text chunk for processing"""
    chunk_id: str
    text: str
    start_char: int
    end_char: int
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class StructuredResult:
    """Result from structuring a text chunk"""
    chunk_id: str
    content_blocks: List[Dict[str, Any]]
    status: str
    error: Optional[str] = None
    processing_time: float = 0.0


# =============================================================================
# VALIDATION
# =============================================================================

class SchemaValidator:
    """Validates assistant output against JSON schema"""

    def __init__(self, schema_path: str):
        """
        Initialize validator with schema file.

        Args:
            schema_path: Path to JSON schema file
        """
        self.schema = None
        if Path(schema_path).exists():
            with open(schema_path, 'r', encoding='utf-8') as f:
                self.schema = json.load(f)
            logger.info(f"Loaded validation schema from {schema_path}")
        else:
            logger.warning(f"Schema file not found: {schema_path}")

    def validate(self, data: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        Validate data against schema.

        Args:
            data: Data to validate

        Returns:
            tuple: (is_valid, list of error messages)
        """
        if not self.schema:
            return True, []

        errors = []

        # Check required fields
        if "content_blocks" not in data:
            errors.append("Missing required field: content_blocks")
            return False, errors

        if not isinstance(data["content_blocks"], list):
            errors.append("content_blocks must be an array")
            return False, errors

        if len(data["content_blocks"]) == 0:
            errors.append("content_blocks cannot be empty")
            return False, errors

        # Validate each block
        valid_types = ["chapter_title", "narrative", "dialogue", "verse",
                      "document", "thought", "descriptive"]

        for idx, block in enumerate(data["content_blocks"]):
            # Check required fields
            for field in ["id", "type", "content", "metadata"]:
                if field not in block:
                    errors.append(f"Block {idx}: Missing required field '{field}'")

            # Check block type
            if "type" in block and block["type"] not in valid_types:
                errors.append(f"Block {idx}: Invalid type '{block['type']}'")

            # Check content not empty
            if "content" in block and not block["content"].strip():
                errors.append(f"Block {idx}: Content cannot be empty")

            # Check ID format
            if "id" in block and not block["id"].startswith("block_"):
                errors.append(f"Block {idx}: ID must start with 'block_'")

        return len(errors) == 0, errors


# =============================================================================
# TEXT CHUNKING
# =============================================================================

class TextChunker:
    """Chunks large texts for processing"""

    def __init__(self, max_chunk_size: int = DEFAULT_MAX_CHUNK_SIZE,
                 overlap: int = DEFAULT_CHUNK_OVERLAP):
        """
        Initialize chunker.

        Args:
            max_chunk_size: Maximum characters per chunk
            overlap: Character overlap between chunks
        """
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def chunk_text(self, text: str, chunk_id_prefix: str = "chunk") -> List[TextChunk]:
        """
        Split text into chunks with overlap.

        Args:
            text: Text to chunk
            chunk_id_prefix: Prefix for chunk IDs

        Returns:
            List of TextChunk objects
        """
        if len(text) <= self.max_chunk_size:
            return [TextChunk(
                chunk_id=f"{chunk_id_prefix}_001",
                text=text,
                start_char=0,
                end_char=len(text)
            )]

        chunks = []
        start = 0
        chunk_num = 1

        while start < len(text):
            # Find end position
            end = min(start + self.max_chunk_size, len(text))

            # Try to break at sentence boundary if not at end
            if end < len(text):
                # Look for sentence endings (。！？\n)
                for i in range(end, max(start, end - 200), -1):
                    if text[i] in '。！？\n':
                        end = i + 1
                        break

            # Create chunk
            chunk_text = text[start:end]
            chunks.append(TextChunk(
                chunk_id=f"{chunk_id_prefix}_{chunk_num:03d}",
                text=chunk_text,
                start_char=start,
                end_char=end
            ))

            # Move to next chunk with overlap
            start = end - self.overlap if end < len(text) else end
            chunk_num += 1

        logger.info(f"Split text into {len(chunks)} chunks")
        return chunks


# =============================================================================
# CONTENT STRUCTURING PROCESSOR
# =============================================================================

class ContentStructuringProcessor:
    """
    Process Chinese text through the structuring assistant.
    Identifies content blocks with types (narrative, dialogue, verse, etc.)
    """

    def __init__(
        self,
        assistant_manager: Optional[TranslationAssistantManager] = None,
        config: Optional[ProcessingConfig] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize the processor.

        Args:
            assistant_manager: TranslationAssistantManager instance (creates if None)
            config: Processing configuration
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.assistant_manager = assistant_manager or TranslationAssistantManager()
        self.config = config or ProcessingConfig()
        self.client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

        # Get structuring assistant
        self.assistant_config = self.assistant_manager.get_assistant("structuring")
        if not self.assistant_config:
            raise ValueError(
                "Structuring assistant not found. "
                "Run setup_translation_assistants.py first."
            )

        self.assistant_id = self.assistant_config["assistant_id"]
        logger.info(f"Using structuring assistant: {self.assistant_id}")

        # Initialize validator
        self.validator = SchemaValidator(SCHEMA_PATH)

        # Initialize chunker
        self.chunker = TextChunker()

    def process_text(
        self,
        text: str,
        text_id: Optional[str] = None,
        retry_count: int = 0,
        on_progress: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Process Chinese text through structuring assistant.

        Args:
            text: Chinese text to structure
            text_id: Optional ID for tracking
            retry_count: Current retry attempt
            on_progress: Optional progress callback

        Returns:
            Structured output with content blocks
        """
        try:
            if on_progress:
                on_progress(f"Creating thread (attempt {retry_count + 1})")

            # Create thread
            thread = self.client.beta.threads.create()

            if on_progress:
                on_progress("Adding message to thread")

            # Add message
            self.client.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=text
            )

            if on_progress:
                on_progress("Running structuring assistant")

            # Run assistant
            run = self.client.beta.threads.runs.create(
                thread_id=thread.id,
                assistant_id=self.assistant_id
            )

            # Wait for completion
            start_time = time.time()
            while run.status in ['queued', 'in_progress', 'cancelling']:
                if time.time() - start_time > self.config.timeout:
                    raise TimeoutError(
                        f"Assistant run timed out after {self.config.timeout}s"
                    )

                time.sleep(1)
                run = self.client.beta.threads.runs.retrieve(
                    thread_id=thread.id,
                    run_id=run.id
                )

            if run.status == 'completed':
                if on_progress:
                    on_progress("Retrieving and validating response")

                # Get response
                messages = self.client.beta.threads.messages.list(thread_id=thread.id)

                for message in messages.data:
                    if message.role == 'assistant':
                        content = message.content[0].text.value
                        result = json.loads(content)

                        # Validate if enabled
                        if self.config.validate_schema:
                            is_valid, errors = self.validator.validate(result)
                            if not is_valid:
                                error_msg = f"Schema validation failed: {'; '.join(errors)}"
                                logger.warning(error_msg)

                                # Retry on validation failure
                                if retry_count < self.config.max_retries:
                                    if on_progress:
                                        on_progress(f"Validation failed, retrying...")
                                    time.sleep(self.config.retry_delay)
                                    return self.process_text(
                                        text, text_id, retry_count + 1, on_progress
                                    )

                                raise ValueError(error_msg)

                        if on_progress:
                            on_progress("Success!")

                        return result

                raise ValueError("No assistant response found")

            elif run.status == 'failed':
                error_msg = f"Assistant run failed: {run.last_error}"

                # Retry on failure
                if retry_count < self.config.max_retries and \
                   self.config.mode != ProcessingMode.STRICT:
                    if on_progress:
                        on_progress(
                            f"Failed, retrying in {self.config.retry_delay}s "
                            f"({retry_count + 1}/{self.config.max_retries})"
                        )
                    time.sleep(self.config.retry_delay)
                    return self.process_text(text, text_id, retry_count + 1, on_progress)

                raise RuntimeError(error_msg)

            else:
                raise RuntimeError(f"Unexpected run status: {run.status}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")

            # Retry on JSON errors
            if retry_count < self.config.max_retries and \
               self.config.mode == ProcessingMode.FLEXIBLE:
                if on_progress:
                    on_progress(f"JSON parse error, retrying...")
                time.sleep(self.config.retry_delay)
                return self.process_text(text, text_id, retry_count + 1, on_progress)

            raise

        except Exception as e:
            logger.error(f"Error processing text: {e}")

            # Retry on other errors
            if retry_count < self.config.max_retries and \
               self.config.mode == ProcessingMode.FLEXIBLE:
                if on_progress:
                    on_progress(f"Error, retrying...")
                time.sleep(self.config.retry_delay)
                return self.process_text(text, text_id, retry_count + 1, on_progress)

            raise

    def process_file(
        self,
        input_file: str,
        output_file: Optional[str] = None,
        chunk_large_files: bool = True
    ) -> Dict[str, Any]:
        """
        Process a Chinese text file.

        Args:
            input_file: Path to input text file
            output_file: Path to output JSON file (optional)
            chunk_large_files: Whether to chunk large files

        Returns:
            Structured output
        """
        logger.info(f"Processing file: {input_file}")

        # Read input file
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()

        logger.info(f"Read {len(text)} characters from {input_file}")

        # Check if chunking needed
        if chunk_large_files and len(text) > DEFAULT_MAX_CHUNK_SIZE:
            logger.info(f"Text is large, chunking into smaller pieces...")
            return self.process_chunked_text(text, output_file)

        # Process entire text
        start_time = time.time()
        result = self.process_text(text)
        processing_time = time.time() - start_time

        logger.info(
            f"Processed in {processing_time:.2f}s, "
            f"found {len(result['content_blocks'])} blocks"
        )

        # Save output if path provided
        if output_file:
            self._save_output(result, output_file)

        return result

    def process_chunked_text(
        self,
        text: str,
        output_file: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process large text by chunking.

        Args:
            text: Text to process
            output_file: Output file path (optional)

        Returns:
            Combined structured output
        """
        # Chunk text
        chunks = self.chunker.chunk_text(text)
        logger.info(f"Processing {len(chunks)} chunks...")

        all_blocks = []
        block_id_counter = 1

        # Process each chunk
        for chunk in chunks:
            logger.info(f"Processing {chunk.chunk_id}...")

            try:
                result = self.process_text(chunk.text, chunk.chunk_id)

                # Renumber block IDs to be sequential
                for block in result["content_blocks"]:
                    block["id"] = f"block_{block_id_counter:03d}"
                    block_id_counter += 1

                    # Add chunk info to metadata
                    if "metadata" not in block:
                        block["metadata"] = {}
                    block["metadata"]["source_chunk"] = chunk.chunk_id

                all_blocks.extend(result["content_blocks"])
                logger.info(
                    f"{chunk.chunk_id}: Found {len(result['content_blocks'])} blocks"
                )

            except Exception as e:
                logger.error(f"Failed to process {chunk.chunk_id}: {e}")

                if self.config.mode == ProcessingMode.STRICT:
                    raise
                else:
                    continue

        # Combine results
        combined_result = {"content_blocks": all_blocks}

        logger.info(f"Total blocks found: {len(all_blocks)}")

        # Save output if path provided
        if output_file:
            self._save_output(combined_result, output_file)

        return combined_result

    def process_batch(
        self,
        input_files: List[str],
        output_dir: str = OUTPUT_DIR,
        max_workers: int = DEFAULT_MAX_WORKERS,
        show_progress: bool = True
    ) -> Dict[str, Dict[str, Any]]:
        """
        Process multiple files in parallel.

        Args:
            input_files: List of input file paths
            output_dir: Output directory
            max_workers: Maximum concurrent workers
            show_progress: Show progress bar

        Returns:
            Dictionary mapping file names to results
        """
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        results = {}
        successful = 0
        failed = 0

        # Progress bar
        pbar = None
        if show_progress and TQDM_AVAILABLE:
            pbar = tqdm(total=len(input_files), desc="Processing files", unit="file")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_file = {}
            for input_file in input_files:
                file_name = Path(input_file).stem
                output_file = Path(output_dir) / f"{file_name}_structured.json"

                future = executor.submit(
                    self._process_with_rate_limit,
                    input_file,
                    str(output_file)
                )
                future_to_file[future] = input_file

            # Process results
            for future in as_completed(future_to_file):
                input_file = future_to_file[future]

                try:
                    result = future.result()
                    results[input_file] = {
                        "status": "success",
                        "result": result,
                        "blocks_count": len(result["content_blocks"])
                    }
                    successful += 1

                except Exception as e:
                    logger.error(f"Failed to process {input_file}: {e}")
                    results[input_file] = {
                        "status": "failed",
                        "error": str(e)
                    }
                    failed += 1

                if pbar:
                    pbar.update(1)
                    pbar.set_postfix({"success": successful, "failed": failed})

        if pbar:
            pbar.close()

        logger.info(
            f"Batch processing complete: {successful}/{len(input_files)} successful"
        )

        return results

    def _process_with_rate_limit(
        self,
        input_file: str,
        output_file: str
    ) -> Dict[str, Any]:
        """Process file with rate limiting"""
        if self.config.rate_limit_delay > 0:
            time.sleep(self.config.rate_limit_delay)

        return self.process_file(input_file, output_file)

    def _save_output(self, data: Dict[str, Any], output_file: str):
        """Save structured output to JSON file"""
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved structured output to {output_file}")


# =============================================================================
# CLI AND EXAMPLES
# =============================================================================

def main():
    """Example usage and CLI interface"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Content Structuring Processor for Chinese Novels"
    )

    # Input/output
    parser.add_argument(
        "--input",
        required=True,
        help="Input text file or directory"
    )
    parser.add_argument(
        "--output",
        help="Output file or directory (default: auto-generated)"
    )

    # Processing options
    parser.add_argument(
        "--mode",
        choices=["strict", "flexible", "best_effort"],
        default="flexible",
        help="Processing mode (default: flexible)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help=f"Max retries per chunk (default: {DEFAULT_MAX_RETRIES})"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout per request in seconds (default: {DEFAULT_TIMEOUT})"
    )
    parser.add_argument(
        "--no-chunking",
        action="store_true",
        help="Disable automatic chunking of large files"
    )
    parser.add_argument(
        "--no-validation",
        action="store_true",
        help="Disable schema validation"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f"Max concurrent workers for batch (default: {DEFAULT_MAX_WORKERS})"
    )

    args = parser.parse_args()

    # Create config
    config = ProcessingConfig(
        max_retries=args.max_retries,
        timeout=args.timeout,
        mode=ProcessingMode(args.mode),
        validate_schema=not args.no_validation
    )

    # Initialize processor
    try:
        processor = ContentStructuringProcessor(config=config)
    except ValueError as e:
        logger.error(f"Failed to initialize processor: {e}")
        return 1

    # Check if input is file or directory
    input_path = Path(args.input)

    if input_path.is_file():
        # Single file processing
        output_file = args.output
        if not output_file:
            output_file = f"{input_path.stem}_structured.json"

        try:
            result = processor.process_file(
                str(input_path),
                output_file,
                chunk_large_files=not args.no_chunking
            )
            logger.info(f"Success! Found {len(result['content_blocks'])} content blocks")
            return 0
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            return 1

    elif input_path.is_dir():
        # Batch processing
        input_files = list(input_path.glob("*.txt"))
        if not input_files:
            logger.error(f"No .txt files found in {input_path}")
            return 1

        output_dir = args.output or "output"

        try:
            results = processor.process_batch(
                [str(f) for f in input_files],
                output_dir,
                max_workers=args.max_workers
            )

            # Print summary
            successful = sum(1 for r in results.values() if r["status"] == "success")
            logger.info(f"Batch complete: {successful}/{len(results)} successful")
            return 0 if successful == len(results) else 1

        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return 1

    else:
        logger.error(f"Input not found: {input_path}")
        return 1


if __name__ == "__main__":
    # Example usage
    print("=" * 80)
    print("Content Structuring Processor for Chinese Novels")
    print("=" * 80)
    print()
    print("This processor identifies content blocks in raw Chinese text.")
    print()
    print("EXAMPLE USAGE:")
    print()
    print("1. Process a single file:")
    print("   python content_structuring_processor.py --input novel.txt")
    print()
    print("2. Process with custom output:")
    print("   python content_structuring_processor.py --input novel.txt --output structured.json")
    print()
    print("3. Process directory (batch mode):")
    print("   python content_structuring_processor.py --input ./novels/ --output ./output/")
    print()
    print("4. Strict mode (fail on first error):")
    print("   python content_structuring_processor.py --input novel.txt --mode strict")
    print()
    print("5. Disable chunking for large files:")
    print("   python content_structuring_processor.py --input novel.txt --no-chunking")
    print()
    print("PROGRAMMATIC USAGE:")
    print()
    print("```python")
    print("from content_structuring_processor import ContentStructuringProcessor")
    print()
    print("# Initialize processor")
    print("processor = ContentStructuringProcessor()")
    print()
    print("# Process a file")
    print("result = processor.process_file('novel.txt', 'output.json')")
    print()
    print("# Access content blocks")
    print("for block in result['content_blocks']:")
    print("    print(f\"{block['id']}: {block['type']} - {block['content'][:50]}...\")")
    print()
    print("# Process text directly")
    print("text = '第一回 靈帝御園問道\\n\\n話說帝乙游於御園...'")
    print("result = processor.process_text(text)")
    print()
    print("# Batch process multiple files")
    print("results = processor.process_batch(['file1.txt', 'file2.txt'])")
    print("```")
    print()
    print("=" * 80)
    print()

    # Run CLI if arguments provided
    import sys
    if len(sys.argv) > 1:
        exit(main())
