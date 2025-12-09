"""
Vector database cache for storing and retrieving similar search queries
"""

import os
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import json


class VectorCache:
    """
    Vector database cache for search queries and results.
    Enables semantic similarity search for query caching.
    """
    
    def __init__(self,
                 db_path: Optional[str] = None,
                 collection_name: str = "search_cache",
                 ttl_seconds: int = 3600):
        """
        Initialize vector cache.
        
        Args:
            db_path: Path to ChromaDB database (defaults to env var or ./chroma_db)
            collection_name: Name of the collection
            ttl_seconds: Time-to-live for cached entries in seconds
        """
        self.db_path = db_path or os.getenv("CHROMA_DB_PATH", "./chroma_db")
        self.collection_name = collection_name
        self.ttl_seconds = int(os.getenv("VECTOR_CACHE_TTL", str(ttl_seconds)))
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
    
    def store_query(self,
                   query: str,
                   results: List[Dict],
                   query_entities: Optional[Dict] = None) -> str:
        """
        Store a search query and its results in the cache.
        
        Args:
            query: Search query string
            results: Search results
            query_entities: Extracted entities from query
            
        Returns:
            Cache entry ID
        """
        # Create metadata
        metadata = {
            "query": query,
            "timestamp": datetime.utcnow().isoformat(),
            "result_count": len(results),
            "query_entities": json.dumps(query_entities) if query_entities else None
        }
        
        # Store results as JSON in metadata (for small results)
        # For large results, we might want to store separately
        if len(results) <= 10:  # Store small result sets in metadata
            metadata["results"] = json.dumps(results, default=str)
        
        # Add document to collection
        # Use query as both ID and document text for embedding
        doc_id = f"query_{datetime.utcnow().timestamp()}"
        
        self.collection.add(
            documents=[query],
            ids=[doc_id],
            metadatas=[metadata]
        )
        
        return doc_id
    
    def find_similar_query(self,
                          query: str,
                          similarity_threshold: float = 0.8,
                          max_results: int = 1) -> Optional[Dict]:
        """
        Find a similar cached query.
        
        Args:
            query: Search query string
            similarity_threshold: Minimum similarity score (0-1)
            max_results: Maximum number of similar queries to return
            
        Returns:
            Cached query metadata and results if found and not expired, None otherwise
        """
        # Query collection for similar documents
        results = self.collection.query(
            query_texts=[query],
            n_results=max_results
        )
        
        if not results["ids"] or len(results["ids"][0]) == 0:
            return None
        
        # Get the most similar result
        distances = results["distances"][0]
        metadatas = results["metadatas"][0]
        
        # Check similarity threshold (ChromaDB uses distance, lower is more similar)
        # Cosine distance: 0 = identical, 1 = opposite
        # Convert to similarity: similarity = 1 - distance
        if distances[0] > (1 - similarity_threshold):
            return None
        
        metadata = metadatas[0]
        
        # Check TTL
        timestamp_str = metadata.get("timestamp")
        if timestamp_str:
            timestamp = datetime.fromisoformat(timestamp_str)
            if datetime.utcnow() - timestamp > timedelta(seconds=self.ttl_seconds):
                return None  # Expired
        
        # Reconstruct cached entry
        cached_entry = {
            "query": metadata.get("query"),
            "timestamp": metadata.get("timestamp"),
            "similarity": 1 - distances[0],
            "query_entities": json.loads(metadata["query_entities"]) if metadata.get("query_entities") else None
        }
        
        # Try to get results from metadata
        if metadata.get("results"):
            try:
                cached_entry["results"] = json.loads(metadata["results"])
            except:
                cached_entry["results"] = None
        else:
            cached_entry["results"] = None
        
        return cached_entry
    
    def clear_expired(self):
        """Remove expired entries from cache."""
        # Get all entries
        all_results = self.collection.get()
        
        if not all_results["ids"]:
            return
        
        expired_ids = []
        now = datetime.utcnow()
        
        for i, metadata in enumerate(all_results["metadatas"]):
            timestamp_str = metadata.get("timestamp")
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str)
                if now - timestamp > timedelta(seconds=self.ttl_seconds):
                    expired_ids.append(all_results["ids"][i])
        
        # Delete expired entries
        if expired_ids:
            self.collection.delete(ids=expired_ids)
    
    def clear_all(self):
        """Clear all cached entries."""
        # Delete and recreate collection
        self.client.delete_collection(name=self.collection_name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

