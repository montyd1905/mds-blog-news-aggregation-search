"""
Named Entity Recognition (NER) Extractor
Extracts entities like people, locations, dates, countries, places, and events
"""

import spacy
from typing import Dict, List, Set
from datetime import datetime
import re


class NERExtractor:
    """
    Extracts named entities from text using spaCy NER model.
    Categorizes entities into: people, locations, dates, countries, places, events
    """
    
    # Entity type mappings from spaCy to our categories
    ENTITY_MAPPINGS = {
        'PERSON': 'people',
        'GPE': 'countries',  # Geopolitical entities (countries, cities, states)
        'LOC': 'locations',   # Non-GPE locations
        'FAC': 'places',      # Buildings, airports, highways, etc.
        'DATE': 'dates',
        'EVENT': 'events',
        'ORG': 'organizations',  # Organizations (can be used for events context)
    }
    
    def __init__(self, model_name: str = "en_core_web_sm"):
        """
        Initialize NER extractor with spaCy model.
        
        Args:
            model_name: Name of spaCy model to use
        """
        try:
            self.nlp = spacy.load(model_name)
        except OSError:
            raise ValueError(
                f"spaCy model '{model_name}' not found. "
                f"Install it with: python -m spacy download {model_name}"
            )
    
    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities from text and categorize them.
        
        Args:
            text: Input text to extract entities from
            
        Returns:
            Dictionary with entity categories as keys and lists of entities as values
        """
        doc = self.nlp(text)
        
        # Initialize result structure
        entities = {
            'people': [],
            'locations': [],
            'dates': [],
            'countries': [],
            'places': [],
            'events': []
        }
        
        # Extract and categorize entities
        seen_entities = {category: set() for category in entities.keys()}
        
        for ent in doc.ents:
            entity_text = ent.text.strip()
            entity_label = ent.label_
            
            # Map spaCy entity type to our category
            category = self.ENTITY_MAPPINGS.get(entity_label)
            
            if category:
                # Handle special cases
                if category == 'countries':
                    # GPE can be countries, cities, or states
                    # Try to identify if it's a country
                    if self._is_likely_country(entity_text):
                        if entity_text not in seen_entities['countries']:
                            entities['countries'].append(entity_text)
                            seen_entities['countries'].add(entity_text)
                    else:
                        # Treat as location
                        if entity_text not in seen_entities['locations']:
                            entities['locations'].append(entity_text)
                            seen_entities['locations'].add(entity_text)
                elif category == 'places':
                    if entity_text not in seen_entities['places']:
                        entities['places'].append(entity_text)
                        seen_entities['places'].add(entity_text)
                elif category == 'locations':
                    if entity_text not in seen_entities['locations']:
                        entities['locations'].append(entity_text)
                        seen_entities['locations'].add(entity_text)
                elif category == 'people':
                    if entity_text not in seen_entities['people']:
                        entities['people'].append(entity_text)
                        seen_entities['people'].add(entity_text)
                elif category == 'dates':
                    # Normalize date format
                    normalized_date = self._normalize_date(entity_text)
                    if normalized_date and normalized_date not in seen_entities['dates']:
                        entities['dates'].append(normalized_date)
                        seen_entities['dates'].add(normalized_date)
                elif category == 'organizations':
                    # Organizations might indicate events
                    # Check if it sounds like an event
                    if self._is_likely_event(entity_text):
                        if entity_text not in seen_entities['events']:
                            entities['events'].append(entity_text)
                            seen_entities['events'].add(entity_text)
        
        # Extract additional events using pattern matching
        events = self._extract_events(text)
        for event in events:
            if event not in seen_entities['events']:
                entities['events'].append(event)
                seen_entities['events'].add(event)
        
        return entities
    
    def _is_likely_country(self, text: str) -> bool:
        """
        Heuristic to determine if a GPE entity is likely a country.
        """
        # Common country indicators
        country_indicators = ['United States', 'United Kingdom', 'USA', 'UK', 
                            'America', 'Britain', 'France', 'Germany', 'China', 
                            'Japan', 'India', 'Russia', 'Canada', 'Australia']
        
        text_lower = text.lower()
        for indicator in country_indicators:
            if indicator.lower() in text_lower or text_lower in indicator.lower():
                return True
        
        # If it's a single word and capitalized, might be a country
        if len(text.split()) == 1 and text[0].isupper():
            return True
        
        return False
    
    def _is_likely_event(self, text: str) -> bool:
        """
        Heuristic to determine if an organization or text might be an event.
        """
        event_keywords = ['summit', 'conference', 'meeting', 'convention', 
                         'festival', 'ceremony', 'awards', 'championship',
                         'tournament', 'exhibition', 'forum', 'symposium']
        
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in event_keywords)
    
    def _extract_events(self, text: str) -> List[str]:
        """
        Extract event names using pattern matching.
        """
        events = []
        
        # Pattern for events: "Event Name" or Event Name followed by keywords
        event_patterns = [
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Summit|Conference|Meeting|Convention|Festival|Ceremony|Awards|Championship|Tournament|Exhibition|Forum|Symposium)',
            r'(?:the|The)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Summit|Conference|Meeting|Convention|Festival|Ceremony|Awards|Championship|Tournament|Exhibition|Forum|Symposium)',
        ]
        
        for pattern in event_patterns:
            matches = re.findall(pattern, text)
            events.extend(matches)
        
        return list(set(events))  # Remove duplicates
    
    def _normalize_date(self, date_text: str) -> str:
        """
        Normalize date strings to a standard format.
        """
        # Try to parse common date formats
        date_formats = [
            '%Y-%m-%d',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y',
            '%Y',
            '%B %Y',
            '%b %Y',
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_text, fmt)
                if '%Y' in fmt and len(fmt.replace('%Y', '').replace('%', '').replace(' ', '').replace(',', '').replace('-', '')) == 0:
                    return str(dt.year)
                elif '%Y' in fmt and '%d' not in fmt:
                    return dt.strftime('%B %Y')
                else:
                    return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # If parsing fails, return original (might be relative like "today", "yesterday")
        return date_text

