"""
Search Engine for querying news articles using NER-based Boolean search
"""

from typing import Dict, List, Optional
from ..ner.extractor import NERExtractor
from ..database.nosql_db import NoSQLDatabase


class SearchEngine:
    """
    Search engine that processes queries through NER extraction
    and builds Boolean search parameters for NoSQL queries.
    """
    
    def __init__(self, 
                 database: NoSQLDatabase,
                 ner_extractor: Optional[NERExtractor] = None,
                 default_relevance_threshold: float = 0.4):
        """
        Initialize search engine.
        
        Args:
            database: NoSQL database instance
            ner_extractor: NER extractor instance (creates new if None)
            default_relevance_threshold: Default minimum relevance score
        """
        self.database = database
        self.ner_extractor = ner_extractor or NERExtractor()
        self.default_relevance_threshold = default_relevance_threshold
    
    def search(self, 
               query: str,
               relevance_thresholds: Optional[Dict[str, float]] = None,
               limit: int = 10) -> List[Dict]:
        """
        Search for news articles matching a query.
        
        Args:
            query: Search query string
            relevance_thresholds: Optional dictionary mapping entity categories to thresholds
            limit: Maximum number of results
            
        Returns:
            List of matching documents with relevance scores
        """
        # Extract entities from query
        entities = self.ner_extractor.extract_entities(query)
        
        # Build query parameters
        query_params = {}
        for category, entity_list in entities.items():
            if entity_list:
                query_params[category] = entity_list
        
        # If no entities extracted, return empty results
        if not query_params:
            return []
        
        # Use default thresholds if not provided
        if relevance_thresholds is None:
            relevance_thresholds = {
                category: self.default_relevance_threshold
                for category in query_params.keys()
            }
        
        # Execute search
        results = self.database.search(
            query_params=query_params,
            relevance_thresholds=relevance_thresholds,
            limit=limit,
            sort_by_relevance=True
        )
        
        return results
    
    def search_with_entities(self,
                            query_entities: Dict[str, List[str]],
                            relevance_thresholds: Optional[Dict[str, float]] = None,
                            limit: int = 10) -> List[Dict]:
        """
        Search using pre-extracted entities.
        
        Args:
            query_entities: Dictionary mapping entity categories to entity lists
            relevance_thresholds: Optional relevance thresholds
            limit: Maximum number of results
            
        Returns:
            List of matching documents
        """
        if relevance_thresholds is None:
            relevance_thresholds = {
                category: self.default_relevance_threshold
                for category in query_entities.keys()
            }
        
        return self.database.search(
            query_params=query_entities,
            relevance_thresholds=relevance_thresholds,
            limit=limit,
            sort_by_relevance=True
        )

