"""
Example: Searching indexed news articles
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.nosql_db import NoSQLDatabase
from src.search.engine import SearchEngine
from src.vector_db.cache import VectorCache
from src.llm.query_improver import LLMQueryImprover


def main():
    """Example of searching news articles."""
    
    # Initialize components
    print("Initializing components...")
    database = NoSQLDatabase()
    search_engine = SearchEngine(database=database)
    vector_cache = VectorCache()
    
    # Check if we have indexed documents
    doc_count = database.count_documents()
    print(f"Indexed documents: {doc_count}")
    
    if doc_count == 0:
        print("\n⚠ No documents indexed. Please run aggregate_example.py first.")
        return
    
    # Example 1: Basic search
    print("\n=== Example 1: Basic search ===")
    query = "John Matthews London"
    print(f"Query: '{query}'")
    
    try:
        results = search_engine.search(query, limit=5)
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n  {i}. {result.get('url')}")
            print(f"     Relevance: {result.get('_relevance_score', 0.0)}")
            # Show top entities
            entities = result.get('entities', {})
            for category, entity_list in entities.items():
                if entity_list:
                    top_entity = entity_list[0]
                    print(f"     {category}: {top_entity['key']} ({top_entity['value']})")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Example 2: Search with LLM improvement
    print("\n=== Example 2: Search with LLM improvement ===")
    vague_query = "economic news in UK"
    print(f"Vague query: '{vague_query}'")
    
    try:
        # Try LLM improvement (requires OpenAI API key)
        if os.getenv("OPENAI_API_KEY"):
            llm_improver = LLMQueryImprover(vector_cache=vector_cache)
            improvement = llm_improver.improve_query(vague_query)
            
            print(f"Improved query: '{improvement.get('improved_query')}'")
            print(f"Confidence: {improvement.get('confidence', 0.0)}")
            print(f"Extracted entities: {improvement.get('entities')}")
            
            # Search with improved query
            query_entities = improvement.get('entities', {})
            if query_entities:
                results = search_engine.search_with_entities(
                    query_entities=query_entities,
                    limit=5
                )
                print(f"\nFound {len(results)} results with improved query")
        else:
            print("⚠ OPENAI_API_KEY not set. Skipping LLM improvement.")
            # Fall back to regular search
            results = search_engine.search(vague_query, limit=5)
            print(f"Found {len(results)} results with regular search")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Example 3: Search with specific entity categories
    print("\n=== Example 3: Search with specific entities ===")
    query_entities = {
        "people": ["John Matthews"],
        "locations": ["London"],
        "events": ["Economic Summit"]
    }
    print(f"Query entities: {query_entities}")
    
    try:
        results = search_engine.search_with_entities(
            query_entities=query_entities,
            relevance_thresholds={
                "people": 0.5,
                "locations": 0.4,
                "events": 0.6
            },
            limit=5
        )
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result.get('url')} (score: {result.get('_relevance_score', 0.0)})")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Example 4: Check cache
    print("\n=== Example 4: Query caching ===")
    # Search same query again
    query = "John Matthews London"
    print(f"Query: '{query}' (second time)")
    
    try:
        cached_result = vector_cache.find_similar_query(query, similarity_threshold=0.8)
        if cached_result:
            print(f"✓ Found cached result (similarity: {cached_result.get('similarity', 0.0)})")
            print(f"  Cached query: '{cached_result.get('query')}'")
            if cached_result.get('results'):
                print(f"  Cached results: {len(cached_result['results'])}")
        else:
            print("No cached result found")
    except Exception as e:
        print(f"✗ Error: {e}")
    
    # Close connections
    database.close()
    print("\n✓ Done!")


if __name__ == "__main__":
    main()

