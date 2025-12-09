"""
Example: Aggregating news from offline sources
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.nosql_db import NoSQLDatabase
from src.pipeline.aggregator import NewsAggregator


def main():
    """Example of aggregating news from a directory."""
    
    # Initialize database
    print("Initializing database...")
    database = NoSQLDatabase()
    
    # Initialize aggregator
    print("Initializing aggregator...")
    aggregator = NewsAggregator(
        database=database,
        min_relevance=0.3
    )
    
    # Example 1: Aggregate from a single file
    print("\n=== Example 1: Aggregating from a single file ===")
    file_path = "path/to/your/news/document.pdf"  # Replace with actual path
    
    if os.path.exists(file_path):
        try:
            rectified = aggregator.aggregate_from_file(
                file_path=file_path,
                url="https://news.example.com/article1",
                filter_low_relevance=True
            )
            print(f"✓ Document indexed: {rectified['url']}")
            print(f"  Entities found:")
            for category, entities in rectified['entities'].items():
                if entities:
                    print(f"    {category}: {len(entities)} entities")
        except Exception as e:
            print(f"✗ Error: {e}")
    else:
        print(f"File not found: {file_path}")
        print("Please update the file_path variable with a valid path")
    
    # Example 2: Aggregate from a directory
    print("\n=== Example 2: Aggregating from a directory ===")
    directory_path = "path/to/your/news/documents"  # Replace with actual path
    
    if os.path.exists(directory_path):
        try:
            results = aggregator.aggregate_from_directory(
                directory_path=directory_path,
                url_prefix="https://news.example.com",
                filter_low_relevance=True
            )
            print(f"✓ Processed {len(results)} documents")
            print(f"  Total indexed: {database.count_documents()}")
        except Exception as e:
            print(f"✗ Error: {e}")
    else:
        print(f"Directory not found: {directory_path}")
        print("Please update the directory_path variable with a valid path")
    
    # Example 3: Aggregate from pre-extracted text
    print("\n=== Example 3: Aggregating from text ===")
    sample_text = """
    London, April 12, 2025 - John Matthews, CEO of TechCorp, announced today 
    at the Economic Summit in Times Square that the company will expand operations 
    to the United Kingdom. Elena Rodriguez, the company's CFO, was also present 
    at the press conference held at Grand Central Station.
    """
    
    try:
        rectified = aggregator.aggregate_from_text(
            text=sample_text,
            url="https://news.example.com/sample-article",
            filter_low_relevance=True
        )
        print(f"✓ Text indexed: {rectified['url']}")
        print(f"  Extracted entities:")
        for category, entities in rectified['entities'].items():
            if entities:
                print(f"    {category}:")
                for entity in entities[:3]:  # Show first 3
                    print(f"      - {entity['key']} (relevance: {entity['value']})")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Close database connection
    database.close()
    print("\n✓ Done!")


if __name__ == "__main__":
    main()

