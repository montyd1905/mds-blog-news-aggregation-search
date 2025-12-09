"""
LLM-based query improvement for vague or low-quality search queries
"""

import os
from typing import Optional, Dict, List
from openai import OpenAI
from ..vector_db.cache import VectorCache


class LLMQueryImprover:
    """
    Uses LLM to improve vague or low-quality search queries
    by extracting better search terms and entities.
    """
    
    def __init__(self,
                 api_key: Optional[str] = None,
                 model: str = "gpt-3.5-turbo",
                 vector_cache: Optional[VectorCache] = None):
        """
        Initialize LLM query improver.
        
        Args:
            api_key: OpenAI API key (defaults to env var)
            model: OpenAI model to use
            vector_cache: Vector cache for retrieving context from previous queries
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.vector_cache = vector_cache
    
    def improve_query(self,
                     query: str,
                     use_context: bool = True) -> Dict[str, any]:
        """
        Improve a search query using LLM.
        
        Args:
            query: Original search query
            use_context: Whether to use context from previous similar queries
            
        Returns:
            Dictionary with improved query and extracted entities
        """
        # Get context from similar queries if available
        context = None
        if use_context and self.vector_cache:
            similar_query = self.vector_cache.find_similar_query(query, similarity_threshold=0.7)
            if similar_query and similar_query.get("query_entities"):
                context = similar_query["query_entities"]
        
        # Build prompt
        prompt = self._build_prompt(query, context)
        
        # Call LLM
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            improved_text = response.choices[0].message.content.strip()
            
            # Parse response
            return self._parse_llm_response(improved_text, query)
        
        except Exception as e:
            print(f"LLM query improvement failed: {e}")
            # Return original query if LLM fails
            return {
                "original_query": query,
                "improved_query": query,
                "entities": {},
                "confidence": 0.0
            }
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM."""
        return """You are a search query improvement assistant for a news aggregation system.
Your task is to improve vague or unclear search queries by:
1. Extracting key entities (people, locations, dates, countries, places, events)
2. Clarifying ambiguous terms
3. Expanding abbreviations
4. Suggesting better search terms

Return your response in JSON format with:
- improved_query: A clearer version of the query
- entities: A dictionary with entity categories (people, locations, dates, countries, places, events) and their values
- confidence: A score from 0.0 to 1.0 indicating how confident you are in the improvement"""
    
    def _build_prompt(self, query: str, context: Optional[Dict] = None) -> str:
        """Build prompt for LLM."""
        prompt = f"""Improve the following search query for a news aggregation system:

Query: "{query}"

"""
        
        if context:
            prompt += f"""Context from similar previous queries:
{self._format_context(context)}

"""
        
        prompt += """Extract entities and improve the query. Return JSON format:
{
  "improved_query": "improved version",
  "entities": {
    "people": ["person1", "person2"],
    "locations": ["location1"],
    "dates": ["date1"],
    "countries": ["country1"],
    "places": ["place1"],
    "events": ["event1"]
  },
  "confidence": 0.85
}"""
        
        return prompt
    
    def _format_context(self, context: Dict) -> str:
        """Format context for prompt."""
        lines = []
        for category, values in context.items():
            if values:
                lines.append(f"{category}: {', '.join(values)}")
        return "\n".join(lines)
    
    def _parse_llm_response(self, response_text: str, original_query: str) -> Dict:
        """Parse LLM response."""
        import json
        import re
        
        # Try to extract JSON from response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                parsed = json.loads(json_match.group())
                return {
                    "original_query": original_query,
                    "improved_query": parsed.get("improved_query", original_query),
                    "entities": parsed.get("entities", {}),
                    "confidence": parsed.get("confidence", 0.5)
                }
            except json.JSONDecodeError:
                pass
        
        # Fallback: return original query
        return {
            "original_query": original_query,
            "improved_query": original_query,
            "entities": {},
            "confidence": 0.0
        }

