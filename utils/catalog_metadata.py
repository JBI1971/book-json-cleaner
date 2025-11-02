#!/usr/bin/env python3
"""
Catalog Metadata Extractor
Extracts work metadata (title, author, volume) from the catalog SQLite database
"""

import sqlite3
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def convert_volume_to_numeric(volume_letter: Optional[str]) -> Optional[str]:
    """
    Convert volume letter (a, b, c...) to three-digit number (001, 002, 003...).

    Args:
        volume_letter: Letter like 'a', 'b', 'c', etc.

    Returns:
        Three-digit string like '001', '002', '003', or None if input is None/empty
    """
    if not volume_letter or len(volume_letter) == 0:
        return None

    # Map a=1, b=2, c=3, etc.
    volume_letter = volume_letter.lower().strip()
    if len(volume_letter) == 1 and 'a' <= volume_letter <= 'z':
        volume_number = ord(volume_letter) - ord('a') + 1
        return f"{volume_number:03d}"

    # If already numeric or unrecognized format, return as-is
    return volume_letter


def get_volume_label(volume_numeric: str) -> str:
    """
    Get Chinese label for numeric volume (001→上, 002→二, etc.).

    Args:
        volume_numeric: Three-digit volume like '001', '002', '003'

    Returns:
        Chinese label or the input if not in mapping
    """
    volume_labels = {
        '001': '上',
        '002': '二',
        '003': '三',
        '004': '四',
        '005': '五',
        '006': '六',
        '007': '七',
        '008': '八',
        '009': '九',
        '010': '十'
    }
    return volume_labels.get(volume_numeric, volume_numeric)


@dataclass
class WorkMetadata:
    """Metadata for a work from catalog"""
    work_number: str
    title_chinese: str
    author_chinese: str
    volume: Optional[str] = None
    title_english: Optional[str] = None
    author_english: Optional[str] = None
    category_english: Optional[str] = None
    summary: Optional[str] = None
    work_link: Optional[str] = None


class CatalogMetadataExtractor:
    """Extract metadata from wuxia_catalog.db"""

    def __init__(self, catalog_path: str):
        """
        Initialize extractor.

        Args:
            catalog_path: Path to wuxia_catalog.db
        """
        self.catalog_path = Path(catalog_path)
        if not self.catalog_path.exists():
            raise FileNotFoundError(f"Catalog database not found: {catalog_path}")
        logger.info(f"Catalog loaded: {catalog_path}")

    def get_metadata_by_directory(self, directory_name: str) -> Optional[WorkMetadata]:
        """
        Get metadata for a work by directory name (e.g., 'wuxia_0008').

        Args:
            directory_name: Directory name like 'wuxia_0008'

        Returns:
            WorkMetadata or None if not found
        """
        try:
            conn = sqlite3.connect(self.catalog_path)
            cursor = conn.cursor()

            # Query joining works and work_files tables
            query = """
                SELECT
                    w.work_number,
                    w.title_chinese,
                    w.author_chinese,
                    w.title_english,
                    w.author_english,
                    w.category_english,
                    w.summary,
                    w.work_link,
                    wf.volume
                FROM works w
                JOIN work_files wf ON w.work_id = wf.work_id
                WHERE wf.directory_name = ?
                LIMIT 1
            """

            cursor.execute(query, (directory_name,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                logger.warning(f"No metadata found for directory: {directory_name}")
                return None

            metadata = WorkMetadata(
                work_number=row[0] or "",
                title_chinese=row[1] or "",
                author_chinese=row[2] or "",
                title_english=row[3],
                author_english=row[4],
                category_english=row[5],
                summary=row[6],
                work_link=row[7],
                volume=convert_volume_to_numeric(row[8]) if row[8] and len(row[8]) > 0 else None
            )

            logger.debug(f"Found metadata for {directory_name}: {metadata.title_chinese} by {metadata.author_chinese}")
            return metadata

        except Exception as e:
            logger.error(f"Error querying catalog for {directory_name}: {e}")
            return None

    def get_metadata_by_filename(self, filename: str) -> Optional[WorkMetadata]:
        """
        Get metadata by filename (e.g., 'D61a_飛狐外傳上_金庸.json').

        Args:
            filename: Filename

        Returns:
            WorkMetadata or None if not found
        """
        try:
            conn = sqlite3.connect(self.catalog_path)
            cursor = conn.cursor()

            query = """
                SELECT
                    w.work_number,
                    w.title_chinese,
                    w.author_chinese,
                    w.title_english,
                    w.author_english,
                    w.category_english,
                    w.summary,
                    w.work_link,
                    wf.volume
                FROM works w
                JOIN work_files wf ON w.work_id = wf.work_id
                WHERE wf.filename = ?
                LIMIT 1
            """

            cursor.execute(query, (filename,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                logger.warning(f"No metadata found for filename: {filename}")
                return None

            return WorkMetadata(
                work_number=row[0] or "",
                title_chinese=row[1] or "",
                author_chinese=row[2] or "",
                title_english=row[3],
                author_english=row[4],
                category_english=row[5],
                summary=row[6],
                work_link=row[7],
                volume=convert_volume_to_numeric(row[8]) if row[8] and len(row[8]) > 0 else None
            )

        except Exception as e:
            logger.error(f"Error querying catalog for {filename}: {e}")
            return None

    def enrich_json_metadata(self, json_data: Dict[str, Any], directory_name: str) -> Dict[str, Any]:
        """
        Enrich JSON data with catalog metadata.

        Args:
            json_data: Cleaned JSON book data
            directory_name: Directory name for lookup

        Returns:
            JSON data with enriched metadata
        """
        metadata = self.get_metadata_by_directory(directory_name)
        if not metadata:
            logger.warning(f"Could not enrich metadata for {directory_name}")
            return json_data

        # Update meta section
        if 'meta' not in json_data:
            json_data['meta'] = {}

        # Add catalog metadata
        json_data['meta']['work_number'] = metadata.work_number
        json_data['meta']['title_chinese'] = metadata.title_chinese
        json_data['meta']['author_chinese'] = metadata.author_chinese

        if metadata.volume:
            json_data['meta']['volume'] = metadata.volume

        if metadata.title_english:
            json_data['meta']['title_english'] = metadata.title_english

        if metadata.author_english:
            json_data['meta']['author_english'] = metadata.author_english

        if metadata.category_english:
            json_data['meta']['category'] = metadata.category_english

        if metadata.summary:
            json_data['meta']['summary'] = metadata.summary

        if metadata.work_link:
            json_data['meta']['work_link'] = metadata.work_link

        # Update title if needed
        if metadata.volume:
            volume_label = get_volume_label(metadata.volume)
            full_title = f"{metadata.title_chinese} ({volume_label}卷)"
            json_data['meta']['title'] = full_title
        else:
            json_data['meta']['title'] = metadata.title_chinese

        logger.info(f"Enriched metadata: {metadata.title_chinese} by {metadata.author_chinese}")
        return json_data


def main():
    """CLI testing"""
    import sys
    if len(sys.argv) < 3:
        print("Usage: python catalog_metadata.py <catalog_path> <directory_name>")
        return 1

    catalog_path = sys.argv[1]
    directory_name = sys.argv[2]

    extractor = CatalogMetadataExtractor(catalog_path)
    metadata = extractor.get_metadata_by_directory(directory_name)

    if metadata:
        print(f"\n✓ Metadata found:")
        print(f"  Work Number: {metadata.work_number}")
        print(f"  Title (中文): {metadata.title_chinese}")
        print(f"  Author (中文): {metadata.author_chinese}")
        if metadata.volume:
            print(f"  Volume: {metadata.volume}")
        if metadata.title_english:
            print(f"  Title (EN): {metadata.title_english}")
        if metadata.author_english:
            print(f"  Author (EN): {metadata.author_english}")
        return 0
    else:
        print(f"\n✗ No metadata found for {directory_name}")
        return 1


if __name__ == "__main__":
    exit(main())
