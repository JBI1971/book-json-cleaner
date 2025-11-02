#!/usr/bin/env python3
"""
Topology Analyzer - Analyze JSON file structure without processing

This tool performs deterministic analysis of JSON files to understand:
- Overall structure and nesting depth
- Field types and patterns
- Content size and token estimates
- Data organization topology
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple
from collections import Counter


class TopologyAnalyzer:
    """Analyze JSON file topology and structure"""

    def __init__(self):
        self.stats = {
            'total_keys': Counter(),
            'max_depth': 0,
            'content_locations': [],
            'html_content_size': 0,
            'json_structure': {},
            'estimated_tokens': 0
        }

    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """Analyze a JSON file and return topology information"""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.stats = {
            'total_keys': Counter(),
            'max_depth': 0,
            'content_locations': [],
            'html_content_size': 0,
            'json_structure': {},
            'estimated_tokens': 0
        }

        # Analyze the structure
        structure = self._analyze_structure(data, path='root', depth=0)
        self.stats['json_structure'] = structure

        # Calculate token estimate (rough: 1 token ≈ 4 chars for Chinese)
        if self.stats['html_content_size'] > 0:
            self.stats['estimated_tokens'] = self.stats['html_content_size'] // 4

        return self.stats

    def _analyze_structure(self, obj: Any, path: str = 'root', depth: int = 0) -> Dict[str, Any]:
        """Recursively analyze object structure"""
        self.stats['max_depth'] = max(self.stats['max_depth'], depth)

        if isinstance(obj, dict):
            result = {'type': 'dict', 'keys': {}}
            for key, value in obj.items():
                self.stats['total_keys'][key] += 1

                # Check for HTML/content fields
                if isinstance(value, str) and len(value) > 1000:
                    if 'html' in key.lower() or 'content' in key.lower():
                        self.stats['html_content_size'] += len(value)
                        self.stats['content_locations'].append({
                            'path': f"{path}.{key}",
                            'size': len(value),
                            'type': 'html_string' if '<' in value[:100] else 'large_string'
                        })

                result['keys'][key] = self._analyze_structure(
                    value,
                    path=f"{path}.{key}",
                    depth=depth + 1
                )
            return result

        elif isinstance(obj, list):
            if not obj:
                return {'type': 'list', 'length': 0, 'sample': None}

            # Analyze first few items to understand list contents
            sample = self._analyze_structure(obj[0], path=f"{path}[0]", depth=depth + 1)

            return {
                'type': 'list',
                'length': len(obj),
                'sample': sample
            }

        elif isinstance(obj, str):
            return {
                'type': 'string',
                'length': len(obj),
                'preview': obj[:100] if len(obj) > 100 else obj
            }

        elif isinstance(obj, (int, float)):
            return {'type': type(obj).__name__, 'value': obj}

        elif obj is None:
            return {'type': 'null'}

        else:
            return {'type': str(type(obj).__name__)}

    def print_summary(self, stats: Dict[str, Any]) -> None:
        """Print a human-readable summary of the topology"""
        print("=" * 80)
        print("JSON TOPOLOGY ANALYSIS")
        print("=" * 80)

        print(f"\n📊 STRUCTURE OVERVIEW")
        print(f"  Max nesting depth: {stats['max_depth']}")
        print(f"  Unique keys found: {len(stats['total_keys'])}")
        print(f"  Total content size: {stats['html_content_size']:,} chars")
        print(f"  Estimated tokens: {stats['estimated_tokens']:,} (for AI processing)")

        print(f"\n🔑 TOP-LEVEL KEYS")
        for key, count in stats['total_keys'].most_common(20):
            print(f"  • {key}: appears {count} time(s)")

        print(f"\n📍 CONTENT LOCATIONS ({len(stats['content_locations'])} found)")
        for loc in stats['content_locations'][:10]:
            size_mb = loc['size'] / (1024 * 1024)
            print(f"  • {loc['path']}")
            print(f"    Type: {loc['type']}, Size: {loc['size']:,} chars ({size_mb:.2f} MB)")

        if len(stats['content_locations']) > 10:
            print(f"  ... and {len(stats['content_locations']) - 10} more locations")

        print(f"\n🌲 STRUCTURE TREE (first 2 levels):")
        self._print_tree(stats['json_structure'], indent=0, max_depth=2)

        print("\n" + "=" * 80)

        # Provide recommendations
        print("\n💡 RECOMMENDATIONS")
        if stats['estimated_tokens'] > 100000:
            print(f"  ⚠️  Large file ({stats['estimated_tokens']:,} tokens)")
            print(f"     Consider chunking before OpenAI processing")
            print(f"     Recommended chunk size: ~30,000 tokens")
            chunks_needed = (stats['estimated_tokens'] // 30000) + 1
            print(f"     Estimated chunks needed: {chunks_needed}")
        elif stats['estimated_tokens'] > 50000:
            print(f"  ⚠️  Medium file ({stats['estimated_tokens']:,} tokens)")
            print(f"     May need chunking for OpenAI assistant")
        else:
            print(f"  ✅ Manageable size ({stats['estimated_tokens']:,} tokens)")
            print(f"     Can likely process in single request")

        print("\n")

    def _print_tree(self, structure: Dict[str, Any], indent: int = 0, max_depth: int = 3) -> None:
        """Print structure tree recursively"""
        if indent >= max_depth:
            return

        prefix = "  " * indent

        if structure['type'] == 'dict':
            for key, value in list(structure['keys'].items())[:10]:
                if value['type'] == 'dict':
                    print(f"{prefix}├─ {key}: {{dict}} with {len(value['keys'])} keys")
                    self._print_tree(value, indent + 1, max_depth)
                elif value['type'] == 'list':
                    print(f"{prefix}├─ {key}: [list] length {value['length']}")
                    if value['sample']:
                        self._print_tree(value['sample'], indent + 1, max_depth)
                elif value['type'] == 'string':
                    length = value.get('length', 0)
                    if length > 100:
                        print(f"{prefix}├─ {key}: (string) {length:,} chars")
                    else:
                        preview = value.get('preview', '')[:50]
                        print(f"{prefix}├─ {key}: \"{preview}...\"")
                else:
                    print(f"{prefix}├─ {key}: {value['type']}")

            if len(structure['keys']) > 10:
                print(f"{prefix}└─ ... and {len(structure['keys']) - 10} more keys")


def main():
    """CLI entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Analyze JSON file topology before processing'
    )
    parser.add_argument(
        '--input', '-i',
        required=True,
        help='Input JSON file path'
    )
    parser.add_argument(
        '--output', '-o',
        help='Save analysis to JSON file (optional)'
    )

    args = parser.parse_args()

    # Validate input
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Error: File not found: {input_path}")
        return 1

    # Analyze
    analyzer = TopologyAnalyzer()
    print(f"\n🔍 Analyzing: {input_path}")
    print(f"   Size: {input_path.stat().st_size / (1024*1024):.2f} MB\n")

    try:
        stats = analyzer.analyze_file(str(input_path))
        analyzer.print_summary(stats)

        # Save if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            print(f"💾 Analysis saved to: {output_path}")

        return 0

    except Exception as e:
        print(f"❌ Error analyzing file: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
