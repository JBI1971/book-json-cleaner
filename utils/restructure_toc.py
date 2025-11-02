#!/usr/bin/env python3
"""
Restructure Table of Contents - Post-processing script

Converts TOC from blob text format to structured list of objects with
chapter references for EPUB navigation and link generation.

Before:
  "toc": [{"content": "目錄 第一回... 第二回... 第三回..."}]

After:
  "toc": [
    {
      "entries": [
        {
          "chapter_number": "第一回",
          "chapter_title": "杯酒論交甘淡薄　玉釵為聘結良緣",
          "full_title": "第一回　杯酒論交甘淡薄　玉釵為聘結良緣",
          "chapter_ref": "chapter_0001",
          "ordinal": 1
        },
        ...
      ]
    }
  ]

Benefits:
- Proper EPUB internal links
- Easy validation (TOC ↔ chapters)
- Better navigation structure
- Machine-readable chapter list
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional


class TOCRestructurer:
    """Restructure TOC from text blob to structured list"""

    # Patterns for chapter headings in TOC
    # Ordered by specificity (most specific first)
    TOC_PATTERNS = [
        # Chinese traditional formats (回 = hui/episode)
        r'(第[一二三四五六七八九十百千\d]+回)[　\s]+([^\n第章]+)',      # 第N回 Title
        r'(第[一二三四五六七八九十百千\d]+回)[　\s]*(?=\n|第|$)',     # 第N回 (no title)

        # Chinese modern formats (章 = zhang/chapter)
        r'(第[一二三四五六七八九十百千\d]+章)[　\s]+([^\n第章]+)',      # 第N章 Title
        r'(第[一二三四五六七八九十百千\d]+章)[　\s]*(?=\n|第|$)',     # 第N章 (no title)

        # Without 第 prefix
        r'([一二三四五六七八九十百千]+)　([^\n]+)',                   # N　Title (traditional)
        r'(\d+)　([^\n]+)',                                           # 1　Title (numeric)

        # English formats
        r'(Chapter\s+\d+)[:\s]*([^\n]+)',                             # Chapter N: Title
        r'(CHAPTER\s+\d+)[:\s]*([^\n]+)',                             # CHAPTER N: Title
    ]

    def __init__(self, dry_run: bool = False, strict: bool = False):
        self.dry_run = dry_run
        self.strict = strict  # Fail if TOC doesn't match chapters
        self.warnings = []
        self.fixes = []

    def restructure_file(self, input_path: str, output_path: str = None) -> Dict[str, Any]:
        """Restructure TOC in a cleaned JSON file"""

        # Load the file
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Check if already structured
        if self._is_already_structured(data):
            print(f"⚠️  TOC already structured - skipping")
            return data

        # Restructure TOC
        original_toc = data['structure']['front_matter']['toc']
        chapters = data['structure']['body']['chapters']

        # Try to extract TOC entries from source
        entries = []
        if original_toc and len(original_toc) > 0:
            toc_text = original_toc[0].get('content', '')
            if toc_text:
                entries = self._extract_toc_entries(toc_text)

        # If no TOC entries found, generate from chapters
        if not entries:
            print(f"⚠️  No TOC found - generating from chapters")
            entries = self._generate_toc_from_chapters(chapters)
            self.warnings.append("Generated TOC from chapter titles (no source TOC)")

        # Match TOC entries to actual chapters
        structured_entries = self._match_to_chapters(entries, chapters)

        # Create new structured TOC
        toc_id = original_toc[0].get('id', 'toc_0000') if original_toc else 'toc_0000'
        toc_title = original_toc[0].get('title', 'Table of Contents') if original_toc else 'Table of Contents'
        new_toc = [{
            'id': toc_id,
            'title': toc_title,
            'title_en': 'Table of Contents',
            'entries': structured_entries
        }]

        data['structure']['front_matter']['toc'] = new_toc

        # Report
        print(f"\n📊 TOC RESTRUCTURING SUMMARY")
        print(f"  TOC entries found: {len(entries)}")
        print(f"  Matched to chapters: {len(structured_entries)}")
        print(f"  Total chapters: {len(chapters)}")

        if self.warnings:
            print(f"\n⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings[:10]:
                print(f"  • {warning}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more")

        if len(structured_entries) != len(chapters):
            msg = f"TOC entries ({len(structured_entries)}) ≠ chapters ({len(chapters)})"
            if self.strict:
                raise ValueError(msg)
            else:
                self.warnings.append(msg)

        # Save if not dry run
        if not self.dry_run:
            if output_path is None:
                output_path = input_path

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            print(f"\n✓ Restructured TOC saved to: {output_path}")
        else:
            print(f"\n⚠️  DRY RUN - No files modified")

        return data

    def _is_already_structured(self, data: Dict) -> bool:
        """Check if TOC is already in structured format"""
        toc = data['structure']['front_matter'].get('toc', [])
        if not toc:
            return False
        return 'entries' in toc[0]

    def _generate_toc_from_chapters(self, chapters: List[Dict]) -> List[Dict[str, str]]:
        """Generate TOC entries from chapter titles when no source TOC exists

        Extracts chapter number and title from chapter titles using patterns.
        """
        entries = []

        for chapter in chapters:
            title = chapter.get('title', '')

            # Skip empty titles
            if not title or len(title.strip()) == 0:
                continue

            # Try to parse chapter number and title from chapter title
            chapter_num = None
            chapter_title = None

            # Try patterns to extract number and title
            # Include: 零〇 一二三四五六七八九 十百千 廿卅卌 壹貳參叁肆伍陸柒捌玖拾佰仟
            chinese_nums = r'[零〇一二三四五六七八九十百千廿卅卌壹貳參叁肆伍陸柒捌玖拾佰仟\d]'
            patterns = [
                rf'^(第{chinese_nums}+[回章節集])[　\s]+(.+)$',  # 第N回/章/節/集 Title
                rf'^(第{chinese_nums}+[回章節集])$',            # 第N回/章/節/集 (no title)
                r'^([一二三四五六七八九十百千廿卅]+)　(.+)$',   # N　Title
                r'^(\d+)　(.+)$',                               # 1　Title
            ]

            for pattern in patterns:
                match = re.match(pattern, title)
                if match:
                    chapter_num = match.group(1)
                    if match.lastindex >= 2:
                        chapter_title = match.group(2)
                    else:
                        chapter_title = ""
                    break

            # If no pattern matched, use full title as chapter title
            if not chapter_num:
                # Skip title pages, decorators, etc.
                skip_patterns = [
                    r'^[《〈].+[》〉]',  # 《Book Title》
                    r'^[\s　☆★\*─═-]+$',  # Decorators
                    r'^後記$',  # Standalone afterword
                ]
                if any(re.match(p, title) for p in skip_patterns):
                    continue

                # Use generic numbering
                chapter_num = f"Chapter {len(entries) + 1}"
                chapter_title = title

            full_title = f"{chapter_num}　{chapter_title}" if chapter_title else chapter_num

            entries.append({
                'chapter_number': chapter_num,
                'chapter_title': chapter_title,
                'full_title': full_title
            })

        return entries

    def _extract_toc_entries(self, toc_text: str) -> List[Dict[str, str]]:
        """Extract chapter entries from TOC text blob

        Handles both line-separated and space-separated TOC entries.
        """
        entries = []

        # Pre-process: Split on chapter patterns for blob TOCs (all on one line)
        # This handles cases like: "十一　藥酒 十二　兩塊銅牌 十三　舐犢之情"
        split_patterns = [
            r'(?=第[一二三四五六七八九十百千\d]+[回章])',              # Before 第N回 or 第N章
            r'(?:^|\s)(?=[一二三四五六七八九十百千]{1,4}　)',       # Before N　(at start or after space, 1-4 chars)
            r'(?:^|\s)(?=\d+　)',                                    # Before 1　(at start or after space)
        ]

        # Try to split the text into separate entries
        text_parts = [toc_text]
        for split_pattern in split_patterns:
            new_parts = []
            for part in text_parts:
                split_result = re.split(split_pattern, part)
                new_parts.extend([p.strip() for p in split_result if p.strip()])
            if len(new_parts) > len(text_parts):
                text_parts = new_parts
                break

        # Extract entries from each part
        for part in text_parts:
            # Try each pattern
            for pattern in self.TOC_PATTERNS:
                match = re.search(pattern, part)
                if match:
                    chapter_num = match.group(1).strip()
                    # Handle patterns with or without title capture group
                    if match.lastindex >= 2:
                        chapter_title = match.group(2).strip()
                    else:
                        chapter_title = ""

                    full_title = f"{chapter_num}　{chapter_title}" if chapter_title else chapter_num

                    entries.append({
                        'chapter_number': chapter_num,
                        'chapter_title': chapter_title,
                        'full_title': full_title
                    })
                    break  # Found match, don't try other patterns

        # Remove duplicates (keep first occurrence)
        seen = set()
        unique_entries = []
        for entry in entries:
            if entry['full_title'] not in seen:
                seen.add(entry['full_title'])
                unique_entries.append(entry)

        return unique_entries

    def _match_to_chapters(self, toc_entries: List[Dict], chapters: List[Dict]) -> List[Dict]:
        """Match TOC entries to actual chapters and add references

        Also adds any missing chapters to the TOC automatically.
        """
        structured = []

        for i, entry in enumerate(toc_entries):
            # Try to find matching chapter
            matched_chapter = self._find_matching_chapter(entry, chapters)

            if matched_chapter:
                structured_entry = {
                    'chapter_number': entry['chapter_number'],
                    'chapter_title': entry['chapter_title'],
                    'full_title': entry['full_title'],
                    'chapter_ref': matched_chapter['id'],
                    'ordinal': i + 1
                }
                structured.append(structured_entry)
            else:
                # No match found - still add entry but warn
                self.warnings.append(
                    f"TOC entry '{entry['full_title'][:50]}...' has no matching chapter"
                )
                structured_entry = {
                    'chapter_number': entry['chapter_number'],
                    'chapter_title': entry['chapter_title'],
                    'full_title': entry['full_title'],
                    'chapter_ref': None,  # No match
                    'ordinal': i + 1
                }
                structured.append(structured_entry)

        # Find chapters not in TOC and add them
        matched_chapter_ids = {e['chapter_ref'] for e in structured if e.get('chapter_ref')}
        missing_chapters = [ch for ch in chapters if ch['id'] not in matched_chapter_ids]

        if missing_chapters:
            # Filter out decorators and title pages (don't add these to TOC)
            decorator_patterns = [
                r'^[　\s☆★\*─═-]+$',  # Visual decorators
                r'^《.+》.+$',          # Title pages
            ]

            chapters_to_add = []
            for ch in missing_chapters:
                title = ch['title']
                if not any(re.match(p, title) for p in decorator_patterns):
                    chapters_to_add.append(ch)

            if chapters_to_add:
                print(f"  ℹ️  Adding {len(chapters_to_add)} missing chapters to TOC")

                for ch in chapters_to_add:
                    # Generate TOC entry from chapter title
                    entry = self._generate_toc_entry_from_chapter(ch)
                    if entry:
                        entry['chapter_ref'] = ch['id']
                        structured.append(entry)
                        print(f"    + {entry['full_title'][:60]}")

        # Re-sort by chapter order (not TOC order) to maintain proper sequence
        # Map chapter IDs to their index
        chapter_order = {ch['id']: idx for idx, ch in enumerate(chapters)}

        # Sort structured entries by chapter order
        structured.sort(key=lambda e: chapter_order.get(e.get('chapter_ref'), 999))

        # Renumber ordinals after sorting
        for i, entry in enumerate(structured):
            entry['ordinal'] = i + 1

        return structured

    def _generate_toc_entry_from_chapter(self, chapter: Dict) -> Optional[Dict]:
        """Generate a TOC entry from a chapter title

        Extracts chapter number and title from the chapter's title field.
        """
        title = chapter.get('title', '')
        if not title:
            return None

        # Try patterns to extract number and title
        # Include: 零〇 一二三四五六七八九 十百千 廿卅卌 壹貳參叁肆伍陸柒捌玖拾佰仟
        chinese_nums = r'[零〇一二三四五六七八九十百千廿卅卌壹貳參叁肆伍陸柒捌玖拾佰仟\d]'
        patterns = [
            rf'^(第{chinese_nums}+[回章節集])[　\s]+(.+)$',  # 第N回/章/節/集 Title
            rf'^(第{chinese_nums}+[回章節集])$',            # 第N回/章/節/集 (no title)
            r'^([一二三四五六七八九十百千廿卅]+)　(.+)$',   # N　Title
            r'^(\d+)　(.+)$',                               # 1　Title
        ]

        chapter_num = None
        chapter_title = None

        for pattern in patterns:
            match = re.match(pattern, title)
            if match:
                chapter_num = match.group(1)
                if match.lastindex >= 2:
                    chapter_title = match.group(2)
                else:
                    chapter_title = ""
                break

        # If no pattern matched, use the full title
        if not chapter_num:
            chapter_num = f"Chapter {chapter.get('ordinal', '?')}"
            chapter_title = title

        full_title = f"{chapter_num}　{chapter_title}" if chapter_title else chapter_num

        return {
            'chapter_number': chapter_num,
            'chapter_title': chapter_title,
            'full_title': full_title,
            'ordinal': 0  # Will be renumbered later
        }

    def _normalize_for_matching(self, text: str) -> str:
        """Normalize text for matching by removing bracket variations and whitespace

        Handles common formatting issues:
        - 【text】 vs text】 【 (corrupted brackets)
        - Whitespace variations
        - Leading/trailing brackets
        """
        if not text:
            return ""

        # Remove corrupted bracket patterns: 】 【
        text = re.sub(r'】\s*【', '', text)

        # Remove leading/trailing brackets
        text = re.sub(r'^【', '', text)
        text = re.sub(r'】$', '', text)

        # Normalize whitespace
        text = re.sub(r'\s+', '', text)

        return text.strip()

    def _find_matching_chapter(self, toc_entry: Dict, chapters: List[Dict]) -> Optional[Dict]:
        """Find chapter that matches a TOC entry"""
        full_title = toc_entry['full_title']
        chapter_num = toc_entry['chapter_number']

        # Try exact match first
        for chapter in chapters:
            if chapter['title'] == full_title:
                return chapter

        # Try matching just the chapter number
        for chapter in chapters:
            if chapter['title'].startswith(chapter_num):
                # Close enough - warn about mismatch
                if chapter['title'] != full_title:
                    self.warnings.append(
                        f"Partial match: TOC '{full_title}' → Chapter '{chapter['title']}'"
                    )
                return chapter

        # Try normalized matching (handles bracket corruption)
        normalized_toc = self._normalize_for_matching(full_title)
        for chapter in chapters:
            normalized_chapter = self._normalize_for_matching(chapter['title'])
            if normalized_toc == normalized_chapter:
                self.warnings.append(
                    f"Normalized match: TOC '{full_title}' → Chapter '{chapter['title']}'"
                )
                return chapter

        # Try fuzzy match on title content
        chapter_title = toc_entry['chapter_title']
        for chapter in chapters:
            if chapter_title in chapter['title']:
                self.warnings.append(
                    f"Fuzzy match: TOC '{full_title}' → Chapter '{chapter['title']}'"
                )
                return chapter

        return None

    def validate_structure(self, data: Dict) -> bool:
        """Validate that structured TOC properly represents all content

        Validates bidirectionally:
        1. All TOC entries point to valid content (chapters or other sections)
        2. All content sections are represented in TOC

        Note: Count mismatch is not necessarily an error. TOC may include
        afterwords, appendices, etc. that are legitimate content sections.
        """
        toc = data['structure']['front_matter'].get('toc', [])
        if not toc or 'entries' not in toc[0]:
            print("❌ TOC not in structured format")
            return False

        chapters = data['structure']['body']['chapters']
        entries = toc[0]['entries']

        print(f"\n✅ TOC VALIDATION")
        print(f"  TOC entries: {len(entries)}")
        print(f"  Content sections: {len(chapters)}")

        # 1. Check TOC entries point to valid content
        missing_refs = [e for e in entries if not e.get('chapter_ref')]
        if missing_refs:
            print(f"\n⚠️  {len(missing_refs)} TOC entries without content references")
            for entry in missing_refs[:5]:
                print(f"    • {entry['full_title']}")

        # 2. Check content sections are in TOC
        chapter_ids = {ch['id'] for ch in chapters}
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

        decorators = []
        afterwords = []
        other_content = []

        for ch_id in unreferenced:
            ch = next((c for c in chapters if c['id'] == ch_id), None)
            if ch:
                title = ch['title']
                if any(re.match(p, title) for p in decorator_patterns):
                    decorators.append(ch)
                elif any(re.match(p, title) for p in afterword_patterns):
                    afterwords.append(ch)
                else:
                    other_content.append(ch)

        # Report categorized results
        if decorators:
            print(f"\n📍 {len(decorators)} decorators not in TOC (expected):")
            for ch in decorators[:3]:
                print(f"    • {ch['title'][:50]}")

        if afterwords:
            print(f"\n📍 {len(afterwords)} afterwords not in TOC:")
            for ch in afterwords[:3]:
                print(f"    • {ch['title'][:50]}")

        if other_content:
            print(f"\n⚠️  {len(other_content)} content sections not in TOC:")
            for ch in other_content[:5]:
                print(f"    • {ch['title'][:50]}")

        # 3. Check for TOC entries that don't match any content
        invalid_refs = []
        for entry in entries:
            ref = entry.get('chapter_ref')
            if ref and ref not in chapter_ids:
                invalid_refs.append(entry)

        if invalid_refs:
            print(f"\n⚠️  {len(invalid_refs)} TOC entries point to non-existent content:")
            for entry in invalid_refs[:5]:
                print(f"    • {entry['full_title']} → {entry.get('chapter_ref')}")

        # Summary
        all_good = (len(missing_refs) == 0 and
                   len(other_content) == 0 and
                   len(invalid_refs) == 0)

        if all_good:
            print(f"\n✓ All TOC entries match content sections!")
            if decorators or afterwords:
                print(f"  Note: {len(decorators + afterwords)} sections not in TOC (decorators/afterwords)")
        else:
            print(f"\n⚠️  Validation completed with warnings")

        return all_good


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Restructure TOC from text blob to structured list with chapter references'
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input cleaned JSON file'
    )
    parser.add_argument(
        '--output', '-o',
        default=None,
        help='Output file (default: overwrite input)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be changed without modifying files'
    )
    parser.add_argument(
        '--strict',
        action='store_true',
        help='Fail if TOC entries do not match chapters exactly'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate existing structured TOC (do not restructure)'
    )

    args = parser.parse_args()

    # Validate input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_path}")
        return 1

    print(f"📑 Restructuring TOC in: {input_path}")
    if args.dry_run:
        print(f"   (DRY RUN - no changes will be saved)")
    print()

    # Process
    try:
        restructurer = TOCRestructurer(dry_run=args.dry_run, strict=args.strict)

        if args.validate:
            # Just validate, don't restructure
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            is_valid = restructurer.validate_structure(data)
            return 0 if is_valid else 1
        else:
            # Restructure
            restructurer.restructure_file(str(input_path), args.output)
            return 0

    except Exception as e:
        print(f"❌ Error restructuring TOC: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
