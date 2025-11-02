#!/usr/bin/env python3
"""
Batch Process Books - Test pipeline on entire dataset

Process multiple book files through the complete pipeline:
1. Topology analysis
2. Sanity check (metadata lookup, sequence validation)
3. JSON cleaning
4. Chapter alignment fix
5. TOC restructuring (intelligent matching fixes most issues)
6. TOC alignment validation (OpenAI - verify restructuring)
7. Structure validation (chapter classification)
8. Final validation check

Note: TOC restructuring includes intelligent fuzzy matching that fixes
most alignment issues automatically. Validation happens after to verify.

Logs all issues, warnings, and errors for pipeline adjustment.
"""

import json
import logging
import re
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Tuple
import subprocess
import traceback

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.topology_analyzer import TopologyAnalyzer
from utils.fix_chapter_alignment import ChapterAlignmentFixer
from utils.restructure_toc import TOCRestructurer
from utils.sanity_checker import BookSanityChecker
from utils.catalog_metadata import get_volume_label


class BatchProcessor:
    """Process multiple books through the pipeline with logging"""

    def __init__(self, output_dir: Path, log_dir: Path, catalog_path: str, dry_run: bool = False):
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        self.catalog_path = catalog_path
        self.dry_run = dry_run

        # Create directories
        if not dry_run:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize sanity checker
        try:
            self.sanity_checker = BookSanityChecker(catalog_path)
            logger.info(f"Sanity checker initialized with catalog: {catalog_path}")
        except Exception as e:
            logger.warning(f"Could not initialize sanity checker: {e}")
            self.sanity_checker = None

        # Results tracking
        self.results = {
            'total': 0,
            'succeeded': 0,
            'failed': 0,
            'skipped': 0,
            'stage_stats': {
                'topology': {'success': 0, 'failed': 0},
                'sanity_check': {'success': 0, 'failed': 0},
                'cleaning': {'success': 0, 'failed': 0},
                'alignment': {'success': 0, 'failed': 0},
                'toc': {'success': 0, 'failed': 0},
                'validation': {'success': 0, 'failed': 0}
            },
            'files': []
        }

        # Issue tracking
        self.issues = {
            'no_book_json': [],
            'multiple_book_jsons': [],
            'topology_errors': [],
            'sanity_check_errors': [],
            'sequence_gaps': [],
            'cleaning_errors': [],
            'alignment_errors': [],
            'toc_errors': [],
            'validation_errors': [],
            'toc_chapter_mismatch': [],
            'missing_toc': [],
            'unusual_structure': []
        }

    def find_book_files(self, source_dir: Path, limit_folders: int = None) -> List[Tuple[Path, Path]]:
        """Find all book JSON files in source directory

        Args:
            source_dir: Source directory containing wuxia_* folders
            limit_folders: Limit to first N folders (processes ALL files in each folder)

        Returns list of (folder_path, json_file_path) tuples
        """
        book_files = []
        folders_processed = 0

        # Find all directories starting with wuxia_
        for folder in sorted(source_dir.glob('wuxia_*')):
            if not folder.is_dir():
                continue

            # Apply folder limit if specified
            if limit_folders and folders_processed >= limit_folders:
                break

            # Look for book JSON files (not haodoo_page or summary files)
            json_files = sorted([
                f for f in folder.glob('*.json')
                if 'haodoo_page' not in f.name
                and 'summary' not in f.name
            ])

            if len(json_files) == 0:
                self.issues['no_book_json'].append(str(folder))
            elif len(json_files) > 1:
                self.issues['multiple_book_jsons'].append({
                    'folder': str(folder),
                    'files': [f.name for f in json_files]
                })
                # Process ALL files in the folder
                for json_file in json_files:
                    book_files.append((folder, json_file))
            else:
                book_files.append((folder, json_files[0]))

            folders_processed += 1

        return book_files

    def process_file(self, folder: Path, json_file: Path) -> Dict[str, Any]:
        """Process a single book file through the pipeline"""
        folder_name = folder.name
        result = {
            'folder': folder_name,
            'file': json_file.name,
            'stages': {},
            'issues': [],
            'warnings': [],
            'stats': {}
        }

        print(f"\n{'='*80}")
        print(f"Processing: {folder_name}/{json_file.name}")
        print(f"{'='*80}")

        try:
            # Stage 1: Topology Analysis
            print(f"\n[1/6] Topology Analysis...")
            topology_result = self._stage_topology(json_file)
            result['stages']['topology'] = topology_result
            result['stats']['tokens'] = topology_result.get('estimated_tokens', 0)
            result['stats']['max_depth'] = topology_result.get('max_depth', 0)

            if not topology_result['success']:
                self.results['stage_stats']['topology']['failed'] += 1

                # Check if this is a skip (non-book file) vs error
                if 'skip_reason' in topology_result:
                    result['status'] = 'SKIPPED'
                    result['skip_reason'] = topology_result['skip_reason']
                    self.results['skipped'] += 1
                    print(f"\n⊘ Skipped: {topology_result['error']}")
                    return result
                else:
                    # Real error
                    self.issues['topology_errors'].append({
                        'file': f"{folder_name}/{json_file.name}",
                        'error': topology_result['error']
                    })
                    result['status'] = 'FAILED'
                    print(f"\n✗ Failed: {topology_result['error']}")
                    return result

            self.results['stage_stats']['topology']['success'] += 1

            # Stage 1.5: Sanity Check
            print(f"[1.5/6] Sanity Check...")
            sanity_result = self._stage_sanity_check(json_file, folder_name)
            result['stages']['sanity_check'] = sanity_result

            if sanity_result['success']:
                self.results['stage_stats']['sanity_check']['success'] += 1
                # Store metadata for later use
                if sanity_result.get('metadata'):
                    result['metadata'] = sanity_result['metadata']
                # Track sequence issues
                if sanity_result.get('sequence_issues'):
                    for issue in sanity_result['sequence_issues']:
                        if issue['severity'] == 'error':
                            self.issues['sequence_gaps'].append({
                                'file': f"{folder_name}/{json_file.name}",
                                'issue': issue['message']
                            })
                        result['warnings'].append(issue['message'])
            else:
                self.results['stage_stats']['sanity_check']['failed'] += 1
                self.issues['sanity_check_errors'].append({
                    'file': f"{folder_name}/{json_file.name}",
                    'error': sanity_result.get('error', 'Unknown error')
                })
                # Continue anyway - sanity check failures are not fatal

            # Stage 2: JSON Cleaning
            print(f"[2/6] JSON Cleaning...")
            metadata = result.get('metadata')  # Get metadata from sanity check
            cleaning_result = self._stage_clean(json_file, folder_name, metadata)
            result['stages']['cleaning'] = cleaning_result

            if not cleaning_result['success']:
                self.results['stage_stats']['cleaning']['failed'] += 1
                self.issues['cleaning_errors'].append({
                    'file': f"{folder_name}/{json_file.name}",
                    'error': cleaning_result['error']
                })
                return result
            self.results['stage_stats']['cleaning']['success'] += 1

            cleaned_path = Path(cleaning_result['output_path'])
            result['stats']['chapters'] = cleaning_result.get('chapters', 0)
            result['stats']['blocks'] = cleaning_result.get('blocks', 0)

            # Stage 3: Chapter Alignment
            print(f"[3/6] Chapter Alignment...")
            alignment_result = self._stage_alignment(cleaned_path)
            result['stages']['alignment'] = alignment_result

            if not alignment_result['success']:
                self.results['stage_stats']['alignment']['failed'] += 1
                self.issues['alignment_errors'].append({
                    'file': f"{folder_name}/{json_file.name}",
                    'error': alignment_result['error']
                })
                # Continue anyway
            else:
                self.results['stage_stats']['alignment']['success'] += 1
                if alignment_result.get('fixes', 0) > 0:
                    result['warnings'].append(f"Fixed {alignment_result['fixes']} chapter alignments")

            # Stage 4: TOC Restructuring (includes intelligent fuzzy matching)
            print(f"[4/6] TOC Restructuring...")
            toc_result = self._stage_toc(cleaned_path)
            result['stages']['toc'] = toc_result

            if not toc_result['success']:
                self.results['stage_stats']['toc']['failed'] += 1
                self.issues['toc_errors'].append({
                    'file': f"{folder_name}/{json_file.name}",
                    'error': toc_result['error']
                })
                # Continue anyway
            else:
                self.results['stage_stats']['toc']['success'] += 1
                if toc_result.get('warnings'):
                    result['warnings'].extend(toc_result['warnings'])

            # Stage 5: Combined Validation (TOC alignment + Structure)
            print(f"[5/6] Validation (TOC + Structure)...")
            validation_result = self._stage_validate(cleaned_path)
            result['stages']['validation'] = validation_result

            if validation_result['success']:
                self.results['stage_stats']['validation']['success'] += 1
                result['status'] = 'SUCCESS'
                self.results['succeeded'] += 1
                if validation_result.get('warnings'):
                    result['warnings'].extend(validation_result['warnings'])
            else:
                self.results['stage_stats']['validation']['failed'] += 1
                result['status'] = 'COMPLETED_WITH_ISSUES'
                result['issues'].extend(validation_result.get('issues', []))
                if validation_result.get('warnings'):
                    result['warnings'].extend(validation_result['warnings'])

            print(f"\n✓ Completed: {result['status']}")

        except Exception as e:
            result['status'] = 'FAILED'
            result['error'] = str(e)
            result['traceback'] = traceback.format_exc()
            self.results['failed'] += 1
            print(f"\n✗ Failed: {e}")

        return result

    def _stage_topology(self, json_file: Path) -> Dict[str, Any]:
        """Run topology analysis"""
        try:
            # First check if it's a valid book file
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check for 'chapters' key - if missing, it's not a book file
            if 'chapters' not in data:
                return {
                    'success': False,
                    'error': 'Not a book file (no chapters key)',
                    'skip_reason': 'missing_chapters_key'
                }

            if len(data.get('chapters', [])) == 0:
                return {
                    'success': False,
                    'error': 'Empty chapters array',
                    'skip_reason': 'empty_chapters'
                }

            # Continue with normal topology analysis
            analyzer = TopologyAnalyzer()
            stats = analyzer.analyze_file(str(json_file))
            return {
                'success': True,
                'estimated_tokens': stats['estimated_tokens'],
                'max_depth': stats['max_depth'],
                'total_keys': len(stats['total_keys']),
                'content_locations': len(stats['content_locations'])
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _stage_sanity_check(self, json_file: Path, folder_name: str) -> Dict[str, Any]:
        """Run sanity checks (metadata lookup, sequence validation)"""
        try:
            if not self.sanity_checker:
                return {'success': False, 'error': 'Sanity checker not initialized'}

            # Run sanity check
            result = self.sanity_checker.check(json_file, folder_name, strict_sequence=False)

            # Convert to dict format
            return {
                'success': result.is_valid,
                'metadata': {
                    'work_number': result.metadata.work_number if result.metadata else None,
                    'title_chinese': result.metadata.title_chinese if result.metadata else None,
                    'author_chinese': result.metadata.author_chinese if result.metadata else None,
                    'volume': result.metadata.volume if result.metadata else None
                } if result.metadata else None,
                'sequence_issues': [
                    {
                        'severity': issue.severity,
                        'type': issue.issue_type,
                        'message': issue.message,
                        'chapter_index': issue.chapter_index
                    }
                    for issue in result.sequence_issues
                ],
                'has_errors': result.has_errors,
                'has_warnings': result.has_warnings
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _stage_clean(self, json_file: Path, folder_name: str, metadata: Dict = None) -> Dict[str, Any]:
        """Run JSON cleaning"""
        try:
            from processors.json_cleaner import clean_book_json

            # Clean
            cleaned_data = clean_book_json(str(json_file), 'zh-Hant')

            # Enrich with catalog metadata if available
            if metadata:
                if 'meta' not in cleaned_data:
                    cleaned_data['meta'] = {}

                # Work identification
                if metadata.get('work_number'):
                    cleaned_data['meta']['work_number'] = metadata['work_number']

                # Title (Chinese and English)
                if metadata.get('title_chinese'):
                    cleaned_data['meta']['title'] = metadata['title_chinese']
                    cleaned_data['meta']['title_chinese'] = metadata['title_chinese']
                if metadata.get('title_english'):
                    cleaned_data['meta']['title_english'] = metadata['title_english']

                # Author (Chinese and English)
                if metadata.get('author_chinese'):
                    cleaned_data['meta']['author'] = metadata['author_chinese']
                    cleaned_data['meta']['author_chinese'] = metadata['author_chinese']
                if metadata.get('author_english'):
                    cleaned_data['meta']['author_english'] = metadata['author_english']

                # Volume
                if metadata.get('volume'):
                    cleaned_data['meta']['volume'] = metadata['volume']
                    # Add volume to main title for display
                    volume_label = get_volume_label(metadata['volume'])
                    if metadata.get('title_chinese'):
                        cleaned_data['meta']['title'] = f"{metadata['title_chinese']} ({volume_label}卷)"

            # Save if not dry run
            output_path = self.output_dir / folder_name / f"cleaned_{json_file.name}"
            if not self.dry_run:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(cleaned_data, f, ensure_ascii=False, indent=2)

            # Extract stats
            chapters = cleaned_data['structure']['body']['chapters']
            total_blocks = sum(len(ch.get('content_blocks', [])) for ch in chapters)

            return {
                'success': True,
                'output_path': str(output_path),  # Convert Path to string
                'chapters': len(chapters),
                'blocks': total_blocks
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _stage_alignment(self, cleaned_path: Path) -> Dict[str, Any]:
        """Run chapter alignment fix"""
        try:
            if self.dry_run:
                return {'success': True, 'fixes': 0, 'skipped': 'dry_run'}

            fixer = ChapterAlignmentFixer(dry_run=False)
            fixer.fix_file(str(cleaned_path))

            return {
                'success': True,
                'fixes': len(fixer.fixes)
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _stage_toc(self, cleaned_path: Path) -> Dict[str, Any]:
        """Run TOC restructuring"""
        try:
            if self.dry_run:
                return {'success': True, 'skipped': 'dry_run'}

            restructurer = TOCRestructurer(dry_run=False, strict=False)
            restructurer.restructure_file(str(cleaned_path))

            return {
                'success': True,
                'warnings': restructurer.warnings
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _stage_validate(self, cleaned_path: Path) -> Dict[str, Any]:
        """Validate final output using AI-powered validators

        Uses multiple validators:
        1. StructureValidator - chapter classification and structure
        2. TOCAlignmentValidator - TOC/chapter title matching
        """
        try:
            from processors.structure_validator import StructureValidator
            from utils.toc_alignment_validator import TOCAlignmentValidator

            with open(cleaned_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Run structure validation
            struct_validator = StructureValidator()
            struct_result = struct_validator.validate(data)

            # Run TOC alignment validation
            toc_validator = TOCAlignmentValidator()
            toc_result = toc_validator.validate(data)

            # Merge results
            issues = [
                issue.message
                for issue in struct_result.issues
                if issue.severity == "error"
            ]
            issues.extend([
                issue.message
                for issue in toc_result.issues
                if issue.severity == "error"
            ])

            warnings = [
                issue.message
                for issue in struct_result.issues
                if issue.severity == "warning"
            ]
            warnings.extend([
                issue.message
                for issue in toc_result.issues
                if issue.severity == "warning"
            ])

            # Add info messages
            info_messages = [
                issue.message
                for issue in struct_result.issues
                if issue.severity == "info"
            ]
            info_messages.extend([
                issue.message
                for issue in toc_result.issues
                if issue.severity == "info"
            ])

            # Overall success if both validators pass
            overall_success = struct_result.is_valid and toc_result.is_valid

            return {
                'success': overall_success,
                'issues': issues,
                'warnings': warnings + info_messages,
                'toc_coverage': struct_result.toc_coverage,
                'toc_alignment': toc_result.confidence_score,
                'quality_score': struct_result.structure_quality,
                'classifications': len(struct_result.classifications)
            }

        except Exception as e:
            # Fallback to basic validation if AI validation fails
            logger.warning(f"AI validation failed, using basic validation: {e}")
            return self._stage_validate_basic(cleaned_path)

    def _stage_validate_basic(self, cleaned_path: Path) -> Dict[str, Any]:
        """Fallback basic validation (original logic)"""
        try:
            with open(cleaned_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            issues = []
            warnings = []

            # Check TOC structure
            toc = data['structure']['front_matter'].get('toc', [])
            if not toc:
                issues.append("Missing TOC")
                return {'success': False, 'issues': issues, 'warnings': warnings}
            elif 'entries' not in toc[0]:
                issues.append("TOC not restructured")
                return {'success': False, 'issues': issues, 'warnings': warnings}

            chapters = data['structure']['body']['chapters']
            entries = toc[0]['entries']

            # 1. Check TOC entries have valid references
            missing_refs = [e for e in entries if not e.get('chapter_ref')]
            if missing_refs:
                issues.append(f"{len(missing_refs)} TOC entries without content refs")

            # 2. Check for invalid references (TOC points to non-existent content)
            chapter_ids = {ch['id'] for ch in chapters}
            invalid_refs = [e for e in entries if e.get('chapter_ref') and e['chapter_ref'] not in chapter_ids]
            if invalid_refs:
                issues.append(f"{len(invalid_refs)} TOC entries point to non-existent content")

            # 3. Check content sections in TOC (categorize by type)
            toc_refs = {e['chapter_ref'] for e in entries if e.get('chapter_ref')}
            unreferenced = chapter_ids - toc_refs

            # Categorize unreferenced content
            decorator_patterns = [
                r'^[　\s☆★\*─═-]+$',  # Visual decorators
                r'^《.+》.+$',          # Title pages
            ]
            afterword_patterns = [
                r'^後記$',
                r'^附錄',
                r'^Afterword',
            ]

            decorators = 0
            afterwords = 0
            other_unreferenced = 0

            for ch_id in unreferenced:
                ch = next((c for c in chapters if c['id'] == ch_id), None)
                if ch:
                    title = ch['title']
                    if any(re.match(p, title) for p in decorator_patterns):
                        decorators += 1
                    elif any(re.match(p, title) for p in afterword_patterns):
                        afterwords += 1
                    else:
                        other_unreferenced += 1

            # Report unreferenced content as warnings or issues
            if decorators > 0:
                warnings.append(f"{decorators} decorators not in TOC (expected)")

            if afterwords > 0:
                warnings.append(f"{afterwords} afterwords not in TOC")

            if other_unreferenced > 0:
                issues.append(f"{other_unreferenced} content sections not in TOC")

            # Success if no critical issues
            # Warnings (decorators, afterwords) don't cause failure
            return {
                'success': len(issues) == 0,
                'issues': issues,
                'warnings': warnings
            }
        except Exception as e:
            return {'success': False, 'error': str(e), 'warnings': []}

    def _stage_validate_toc_only(self, cleaned_path: Path) -> Dict[str, Any]:
        """Validate TOC alignment only (before restructuring)"""
        try:
            from utils.toc_alignment_validator import TOCAlignmentValidator

            with open(cleaned_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Run TOC alignment validation
            toc_validator = TOCAlignmentValidator()
            toc_result = toc_validator.validate(data)

            issues = [
                issue.message
                for issue in toc_result.issues
                if issue.severity == "error"
            ]

            warnings = [
                issue.message
                for issue in toc_result.issues
                if issue.severity == "warning" or issue.severity == "info"
            ]

            return {
                'success': toc_result.is_valid,
                'issues': issues,
                'warnings': warnings,
                'toc_alignment': toc_result.confidence_score
            }

        except Exception as e:
            # Fallback if OpenAI fails
            logger.warning(f"TOC validation failed, skipping: {e}")
            return {
                'success': True,  # Don't fail pipeline if validation unavailable
                'issues': [],
                'warnings': [f"TOC validation skipped: {e}"]
            }

    def _stage_validate_structure(self, cleaned_path: Path) -> Dict[str, Any]:
        """Validate structure only (after restructuring)"""
        try:
            from processors.structure_validator import StructureValidator

            with open(cleaned_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Run structure validation
            struct_validator = StructureValidator()
            struct_result = struct_validator.validate(data)

            issues = [
                issue.message
                for issue in struct_result.issues
                if issue.severity == "error"
            ]

            warnings = [
                issue.message
                for issue in struct_result.issues
                if issue.severity == "warning" or issue.severity == "info"
            ]

            return {
                'success': struct_result.is_valid,
                'issues': issues,
                'warnings': warnings,
                'toc_coverage': struct_result.toc_coverage,
                'quality_score': struct_result.structure_quality,
                'classifications': len(struct_result.classifications)
            }

        except Exception as e:
            # Fallback if OpenAI fails
            logger.warning(f"Structure validation failed, using basic validation: {e}")
            return self._stage_validate_basic(cleaned_path)

    def _stage_fix_toc(self, cleaned_path: Path) -> Dict[str, Any]:
        """Run TOC alignment fixer"""
        try:
            fixer = TOCAlignmentFixer()
            result = fixer.fix_file(str(cleaned_path))

            if result.success:
                return {
                    'success': True,
                    'fixes_applied': result.fixes_applied,
                    'errors': result.errors
                }
            else:
                return {
                    'success': False,
                    'error': '; '.join(result.errors) if result.errors else 'Unknown error',
                    'fixes_applied': result.fixes_applied
                }
        except Exception as e:
            logger.warning(f"TOC fixing failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'fixes_applied': 0
            }

    def generate_report(self, output_file: Path):
        """Generate detailed processing report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': self.results,
            'issues': self.issues,
            'files': self.results['files']
        }

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # Also print summary
        print(f"\n{'='*80}")
        print(f"BATCH PROCESSING SUMMARY")
        print(f"{'='*80}\n")

        print(f"📊 Overall Results:")
        print(f"  Total files: {self.results['total']}")
        print(f"  ✓ Succeeded: {self.results['succeeded']}")
        print(f"  ✗ Failed: {self.results['failed']}")
        print(f"  ⊘ Skipped: {self.results['skipped']}")

        print(f"\n📈 Stage Statistics:")
        for stage, stats in self.results['stage_stats'].items():
            total = stats['success'] + stats['failed']
            if total > 0:
                pct = (stats['success'] / total) * 100
                print(f"  {stage:12} - {stats['success']:3}/{total:3} ({pct:5.1f}%) succeeded")

        print(f"\n⚠️  Issue Summary:")
        for issue_type, items in self.issues.items():
            if items:
                print(f"  {issue_type:25} - {len(items):3} files")

        print(f"\n📝 Full report saved to: {output_file}")


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Batch process multiple books through the complete pipeline'
    )
    parser.add_argument(
        '--source-dir',
        required=True,
        help='Source directory containing wuxia_NNNN folders'
    )
    parser.add_argument(
        '--output-dir',
        required=True,
        help='Output directory for cleaned files'
    )
    parser.add_argument(
        '--log-dir',
        default='./logs',
        help='Directory for log files (default: ./logs)'
    )
    parser.add_argument(
        '--catalog-path',
        required=True,
        help='Path to wuxia_catalog.db SQLite database'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='Limit number of files to process (for testing)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Analyze only, do not write files'
    )
    parser.add_argument(
        '--continue-on-error',
        action='store_true',
        default=True,
        help='Continue processing if a file fails'
    )

    args = parser.parse_args()

    # Setup
    source_dir = Path(args.source_dir)
    output_dir = Path(args.output_dir)
    log_dir = Path(args.log_dir)
    catalog_path = args.catalog_path

    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        return 1

    if not Path(catalog_path).exists():
        print(f"❌ Catalog database not found: {catalog_path}")
        return 1

    print(f"🚀 Batch Processing Pipeline")
    print(f"  Source: {source_dir}")
    print(f"  Output: {output_dir}")
    print(f"  Logs: {log_dir}")
    print(f"  Catalog: {catalog_path}")
    if args.dry_run:
        print(f"  Mode: DRY RUN")
    print()

    # Create processor
    processor = BatchProcessor(output_dir, log_dir, catalog_path, dry_run=args.dry_run)

    # Find files
    print(f"🔍 Finding book files...")
    if args.limit:
        print(f"  Limiting to first {args.limit} folders (all files per folder)")
    book_files = processor.find_book_files(source_dir, limit_folders=args.limit)

    print(f"  Found {len(book_files)} book files")
    if processor.issues['no_book_json']:
        print(f"  ⚠️  {len(processor.issues['no_book_json'])} folders with no book JSON")
    if processor.issues['multiple_book_jsons']:
        print(f"  ⚠️  {len(processor.issues['multiple_book_jsons'])} folders with multiple JSONs")
    print()

    # Process files
    processor.results['total'] = len(book_files)
    start_time = time.time()

    for i, (folder, json_file) in enumerate(book_files, 1):
        print(f"\n[{i}/{len(book_files)}]", end=' ')
        result = processor.process_file(folder, json_file)
        processor.results['files'].append(result)

    elapsed = time.time() - start_time

    # Generate report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = log_dir / f"batch_report_{timestamp}.json"
    if not args.dry_run:
        log_dir.mkdir(parents=True, exist_ok=True)

    processor.generate_report(report_file)

    if len(book_files) > 0:
        print(f"\n⏱️  Processing time: {elapsed:.1f}s ({elapsed/len(book_files):.1f}s per file)")
    else:
        print(f"\n⏱️  Processing time: {elapsed:.1f}s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
