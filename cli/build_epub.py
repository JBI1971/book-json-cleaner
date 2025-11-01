#!/usr/bin/env python3
"""
CLI for EPUB Builder (COMING SOON)

Build EPUB files from processed book JSON.
"""

import argparse

def main():
    parser = argparse.ArgumentParser(
        description='Build EPUB from processed JSON (COMING SOON)'
    )
    parser.add_argument('--input', required=True, help='Input processed JSON file')
    parser.add_argument('--output', required=True, help='Output EPUB file')
    parser.add_argument('--cover', help='Cover image file (optional)')
    parser.add_argument('--author', help='Author name (optional)')

    args = parser.parse_args()

    print("EPUB building feature coming soon!")
    print(f"Will build: {args.input} -> {args.output}")
    if args.cover:
        print(f"Cover image: {args.cover}")
    if args.author:
        print(f"Author: {args.author}")
    return 0

if __name__ == "__main__":
    exit(main())
