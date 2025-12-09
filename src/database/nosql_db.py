"""
NoSQL Database interface for storing and searching rectified news articles
"""

from typing import Dict, List, Optional, Any
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
import os
from datetime import datetime


class NoSQLDatabase:
    """
    MongoDB-based NoSQL database for storing and searching news articles.
    Stores rectified documents with weighted entities.
    """
    
    def __init__(self, 
                 mongodb_uri: Optional[str] = None,
                 db_name: Optional[str] = None,
                 collection_name: str = "news_articles"):
        """
        Initialize NoSQL database connection.
        
        Args:
            mongodb_uri: MongoDB connection URI (defaults to env var or localhost)
            db_name: Database name (defaults to env var or 'news_aggregation')
            collection_name: Collection name for news articles
        """
        self.mongodb_uri = mongodb_uri or os.getenv("MONGODB_URI", "mongodb://localhost:27017")
        self.db_name = db_name or os.getenv("MONGODB_DB_NAME", "news_aggregation")
        self.collection_name = collection_name
        
        # Connect to MongoDB
        self.client = MongoClient(self.mongodb_uri)
        self.db: Database = self.client[self.db_name]
        self.collection: Collection = self.db[self.collection_name]
        
        # Create indexes for efficient searching
        self._create_indexes()
    
    def _create_indexes(self):
        """Create database indexes for efficient querying."""
        # Index on URL for uniqueness
        self.collection.create_index("url", unique=True)
        
        # Index on entity keys for search
        self.collection.create_index("entities.people.key")
        self.collection.create_index("entities.locations.key")
        self.collection.create_index("entities.dates.key")
        self.collection.create_index("entities.countries.key")
        self.collection.create_index("entities.places.key")
        self.collection.create_index("entities.events.key")
        
        # Text index for full-text search
        self.collection.create_index([("url", "text")])
    
    def index_document(self, rectified_doc: Dict) -> str:
        """
        Index a rectified document.
        
        Args:
            rectified_doc: Rectified document with URL and weighted entities
            
        Returns:
            Document ID
        """
        # Add timestamp
        doc = {
            **rectified_doc,
            "indexed_at": datetime.utcnow()
        }
        
        # Upsert based on URL
        result = self.collection.update_one(
            {"url": rectified_doc["url"]},
            {"$set": doc},
            upsert=True
        )
        
        return str(result.upserted_id) if result.upserted_id else "updated"
    
    def index_documents(self, rectified_docs: List[Dict]) -> List[str]:
        """
        Index multiple rectified documents.
        
        Args:
            rectified_docs: List of rectified documents
            
        Returns:
            List of document IDs
        """
        ids = []
        for doc in rectified_docs:
            ids.append(self.index_document(doc))
        return ids
    
    def search(self, 
               query_params: Dict[str, List[str]],
               relevance_thresholds: Optional[Dict[str, float]] = None,
               limit: int = 10,
               sort_by_relevance: bool = True) -> List[Dict]:
        """
        Search for documents matching entity query parameters.
        
        Args:
            query_params: Dictionary mapping entity categories to lists of search terms
            relevance_thresholds: Optional dictionary mapping entity categories to minimum relevance scores
            limit: Maximum number of results to return
            sort_by_relevance: Whether to sort results by relevance score
            
        Returns:
            List of matching documents with relevance scores
        """
        if relevance_thresholds is None:
            relevance_thresholds = {}
        
        # Build MongoDB query
        query = self._build_query(query_params, relevance_thresholds)
        
        # Execute query
        cursor = self.collection.find(query)
        
        # Calculate relevance scores and sort
        results = []
        for doc in cursor:
            score = self._calculate_relevance_score(doc, query_params, relevance_thresholds)
            doc["_relevance_score"] = score
            results.append(doc)
        
        # Sort by relevance if requested
        if sort_by_relevance:
            results.sort(key=lambda x: x["_relevance_score"], reverse=True)
        
        # Limit results
        results = results[:limit]
        
        return results
    
    def _build_query(self, 
                    query_params: Dict[str, List[str]],
                    relevance_thresholds: Dict[str, float]) -> Dict:
        """
        Build MongoDB query from entity search parameters.
        
        Args:
            query_params: Entity search parameters
            relevance_thresholds: Relevance thresholds per category
            
        Returns:
            MongoDB query dictionary
        """
        query = {"$or": []}
        
        # For each entity category
        for category, search_terms in query_params.items():
            if not search_terms:
                continue
            
            category_path = f"entities.{category}"
            threshold = relevance_thresholds.get(category, 0.0)
            
            # Build query for this category
            category_query = {
                "$and": []
            }
            
            # Match any of the search terms
            term_conditions = []
            for term in search_terms:
                term_lower = term.lower()
                # Match entity key (case-insensitive)
                term_conditions.append({
                    f"{category_path}.key": {"$regex": term_lower, "$options": "i"}
                })
            
            if term_conditions:
                category_query["$and"].append({"$or": term_conditions})
            
            # Apply relevance threshold if specified
            if threshold > 0:
                category_query["$and"].append({
                    f"{category_path}.value": {"$gte": threshold}
                })
            
            if category_query["$and"]:
                query["$or"].append(category_query)
        
        # If no conditions, return empty query (no results)
        if not query["$or"]:
            return {}
        
        return query
    
    def _calculate_relevance_score(self,
                                   doc: Dict,
                                   query_params: Dict[str, List[str]],
                                   relevance_thresholds: Dict[str, float]) -> float:
        """
        Calculate relevance score for a document based on query parameters.
        
        Args:
            doc: Document from database
            query_params: Query parameters
            relevance_thresholds: Relevance thresholds
            
        Returns:
            Relevance score (0.0 to 1.0)
        """
        total_score = 0.0
        total_weight = 0.0
        
        entities = doc.get("entities", {})
        
        # Score each category
        for category, search_terms in query_params.items():
            if not search_terms:
                continue
            
            category_entities = entities.get(category, [])
            
            # Find matching entities and sum their scores
            category_score = 0.0
            matches = 0
            
            for term in search_terms:
                term_lower = term.lower()
                for entity in category_entities:
                    entity_key = entity.get("key", "").lower()
                    entity_value = entity.get("value", 0.0)
                    
                    if term_lower in entity_key or entity_key in term_lower:
                        category_score += entity_value
                        matches += 1
            
            # Average score for this category
            if matches > 0:
                avg_category_score = category_score / matches
            else:
                avg_category_score = 0.0
            
            # Weight by number of matches
            weight = len(search_terms)
            total_score += avg_category_score * weight
            total_weight += weight
        
        # Normalize to 0-1 range
        if total_weight > 0:
            final_score = total_score / total_weight
        else:
            final_score = 0.0
        
        return round(final_score, 3)
    
    def get_by_url(self, url: str) -> Optional[Dict]:
        """
        Retrieve a document by URL.
        
        Args:
            url: Document URL
            
        Returns:
            Document if found, None otherwise
        """
        return self.collection.find_one({"url": url})
    
    def delete_by_url(self, url: str) -> bool:
        """
        Delete a document by URL.
        
        Args:
            url: Document URL
            
        Returns:
            True if deleted, False if not found
        """
        result = self.collection.delete_one({"url": url})
        return result.deleted_count > 0
    
    def count_documents(self) -> int:
        """Get total number of indexed documents."""
        return self.collection.count_documents({})
    
    def close(self):
        """Close database connection."""
        self.client.close()

