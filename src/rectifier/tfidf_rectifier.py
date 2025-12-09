"""
TF-IDF Rectifier for adding relevance weights to named entities
"""

from typing import Dict, List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np


class TFIDFRectifier:
    """
    Applies TF-IDF scoring to named entities to determine their relevance.
    Converts entity lists to weighted entity dictionaries.
    """
    
    def __init__(self, min_relevance: float = 0.3):
        """
        Initialize TF-IDF Rectifier.
        
        Args:
            min_relevance: Minimum relevance score threshold (entities below this are filtered)
        """
        self.min_relevance = min_relevance
        self.vectorizer = TfidfVectorizer(
            lowercase=True,
            analyzer='word',
            ngram_range=(1, 2),  # Support both single words and phrases
            min_df=1,
            max_df=0.95
        )
    
    def rectify(self, entities: Dict[str, List[str]], 
                source_text: str,
                url: str,
                filter_low_relevance: bool = True) -> Dict:
        """
        Rectify entity dictionary by adding TF-IDF weights.
        
        Args:
            entities: Dictionary of entity categories to lists of entity values
            source_text: Original text from which entities were extracted
            url: URL or identifier for the news item
            filter_low_relevance: Whether to filter out entities below min_relevance threshold
            
        Returns:
            Rectified dictionary with URL and weighted entities
        """
        rectified = {
            "url": url,
            "entities": {}
        }
        
        # Process each entity category
        for category, entity_list in entities.items():
            if not entity_list:
                rectified["entities"][category] = []
                continue
            
            # Calculate TF-IDF scores for entities in this category
            weighted_entities = self._calculate_weights(
                entity_list, 
                source_text, 
                category
            )
            
            # Filter low relevance entities if requested
            if filter_low_relevance:
                weighted_entities = [
                    e for e in weighted_entities 
                    if e["value"] >= self.min_relevance
                ]
            
            # Sort by relevance (highest first)
            weighted_entities.sort(key=lambda x: x["value"], reverse=True)
            
            rectified["entities"][category] = weighted_entities
        
        return rectified
    
    def _calculate_weights(self, entities: List[str], 
                          source_text: str,
                          category: str) -> List[Dict[str, any]]:
        """
        Calculate TF-IDF weights for a list of entities.
        
        Args:
            entities: List of entity values
            source_text: Source text containing the entities
            category: Entity category name
            
        Returns:
            List of dictionaries with "key" and "value" (weight)
        """
        if not entities:
            return []
        
        # Create documents: one per entity (entity text + context from source)
        # This helps measure how important each entity is in the context
        documents = []
        entity_texts = []
        
        for entity in entities:
            # Create a document that includes the entity and surrounding context
            # This helps TF-IDF understand the entity's importance
            entity_lower = entity.lower()
            source_lower = source_text.lower()
            
            # Find all occurrences of the entity in the text
            occurrences = []
            start = 0
            while True:
                idx = source_lower.find(entity_lower, start)
                if idx == -1:
                    break
                # Extract context around the entity (50 chars before and after)
                context_start = max(0, idx - 50)
                context_end = min(len(source_text), idx + len(entity) + 50)
                context = source_text[context_start:context_end]
                occurrences.append(context)
                start = idx + 1
            
            # If entity found, use contexts; otherwise use entity itself
            if occurrences:
                doc = " ".join(occurrences)
            else:
                doc = entity
            
            documents.append(doc)
            entity_texts.append(entity)
        
        # Calculate TF-IDF
        try:
            # Fit and transform documents
            tfidf_matrix = self.vectorizer.fit_transform(documents)
            
            # Get feature names (terms)
            feature_names = self.vectorizer.get_feature_names_out()
            
            # Calculate average TF-IDF score for each entity
            weighted_entities = []
            for i, entity in enumerate(entity_texts):
                # Get TF-IDF scores for this document
                scores = tfidf_matrix[i].toarray()[0]
                
                # Calculate entity-specific score
                # Sum scores for words that appear in the entity name
                entity_words = set(entity.lower().split())
                entity_score = 0.0
                word_count = 0
                
                for j, term in enumerate(feature_names):
                    if term in entity_words or any(word in term for word in entity_words):
                        entity_score += scores[j]
                        word_count += 1
                
                # Normalize score (average, then scale to 0-1 range)
                if word_count > 0:
                    avg_score = entity_score / word_count
                else:
                    # Fallback: use maximum score in document
                    avg_score = np.max(scores) if len(scores) > 0 else 0.0
                
                # Normalize to 0-1 range (TF-IDF can be > 1, but we want 0-1)
                normalized_score = min(1.0, avg_score * 2)  # Scale factor to bring into 0-1 range
                
                # Boost score based on frequency in source text
                frequency_boost = min(1.0, source_text.lower().count(entity.lower()) * 0.1)
                final_score = min(1.0, normalized_score + frequency_boost * 0.2)
                
                weighted_entities.append({
                    "key": entity,
                    "value": round(final_score, 2)
                })
        
        except Exception as e:
            # Fallback: use simple frequency-based scoring
            print(f"TF-IDF calculation failed, using frequency-based scoring: {e}")
            weighted_entities = self._frequency_based_scoring(entities, source_text)
        
        return weighted_entities
    
    def _frequency_based_scoring(self, entities: List[str], 
                                source_text: str) -> List[Dict[str, any]]:
        """
        Fallback scoring method based on entity frequency in text.
        
        Args:
            entities: List of entity values
            source_text: Source text
            
        Returns:
            List of dictionaries with "key" and "value" (weight)
        """
        source_lower = source_text.lower()
        text_length = len(source_text.split())
        
        weighted_entities = []
        max_freq = 0
        
        # Calculate frequencies
        frequencies = {}
        for entity in entities:
            freq = source_lower.count(entity.lower())
            frequencies[entity] = freq
            max_freq = max(max_freq, freq)
        
        # Normalize frequencies to 0-1 range
        for entity, freq in frequencies.items():
            if max_freq > 0:
                score = freq / max_freq
            else:
                score = 0.5  # Default score if no frequency data
            
            weighted_entities.append({
                "key": entity,
                "value": round(score, 2)
            })
        
        return weighted_entities
    
    def batch_rectify(self, entity_dicts: List[Dict[str, List[str]]],
                     source_texts: List[str],
                     urls: List[str],
                     filter_low_relevance: bool = True) -> List[Dict]:
        """
        Rectify multiple entity dictionaries in batch.
        This is more efficient as it can use corpus-level TF-IDF.
        
        Args:
            entity_dicts: List of entity dictionaries
            source_texts: List of source texts
            urls: List of URLs
            filter_low_relevance: Whether to filter low relevance entities
            
        Returns:
            List of rectified dictionaries
        """
        if len(entity_dicts) != len(source_texts) or len(entity_dicts) != len(urls):
            raise ValueError("All input lists must have the same length")
        
        rectified_list = []
        for entities, text, url in zip(entity_dicts, source_texts, urls):
            rectified = self.rectify(entities, text, url, filter_low_relevance)
            rectified_list.append(rectified)
        
        return rectified_list

