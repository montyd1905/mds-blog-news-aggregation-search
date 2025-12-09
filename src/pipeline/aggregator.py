"""
Main news aggregation pipeline
"""

from typing import List, Dict, Optional
from pathlib import Path
from ..ocr.extractor import OCRExtractor
from ..ner.extractor import NERExtractor
from ..rectifier.tfidf_rectifier import TFIDFRectifier
from ..database.nosql_db import NoSQLDatabase
from tqdm import tqdm


class NewsAggregator:
    """
    Main pipeline for aggregating news from offline sources.
    Orchestrates OCR, NER, TF-IDF rectification, and indexing.
    """
    
    def __init__(self,
                 database: NoSQLDatabase,
                 ocr_extractor: Optional[OCRExtractor] = None,
                 ner_extractor: Optional[NERExtractor] = None,
                 rectifier: Optional[TFIDFRectifier] = None,
                 min_relevance: float = 0.3):
        """
        Initialize news aggregator.
        
        Args:
            database: NoSQL database instance
            ocr_extractor: OCR extractor instance (creates new if None)
            ner_extractor: NER extractor instance (creates new if None)
            rectifier: TF-IDF rectifier instance (creates new if None)
            min_relevance: Minimum relevance threshold for entities
        """
        self.database = database
        self.ocr_extractor = ocr_extractor or OCRExtractor()
        self.ner_extractor = ner_extractor or NERExtractor()
        self.rectifier = rectifier or TFIDFRectifier(min_relevance=min_relevance)
        self.min_relevance = min_relevance
    
    def aggregate_from_file(self,
                            file_path: str,
                            url: Optional[str] = None,
                            filter_low_relevance: bool = True) -> Dict:
        """
        Aggregate news from a single file.
        
        Args:
            file_path: Path to file (PDF or image)
            url: URL or identifier for the news item (defaults to file path)
            filter_low_relevance: Whether to filter low-relevance entities
            
        Returns:
            Rectified document dictionary
        """
        if url is None:
            url = file_path
        
        # Step 1: Extract text using OCR
        print(f"Extracting text from {file_path}...")
        text = self.ocr_extractor.extract_from_file(file_path)
        
        if not text or len(text.strip()) < 50:
            raise ValueError(f"Insufficient text extracted from {file_path}")
        
        # Step 2: Extract entities using NER
        print(f"Extracting entities...")
        entities = self.ner_extractor.extract_entities(text)
        
        # Step 3: Rectify entities with TF-IDF weights
        print(f"Rectifying entities...")
        rectified = self.rectifier.rectify(
            entities=entities,
            source_text=text,
            url=url,
            filter_low_relevance=filter_low_relevance
        )
        
        # Step 4: Index in database
        print(f"Indexing document...")
        doc_id = self.database.index_document(rectified)
        rectified["_id"] = doc_id
        
        return rectified
    
    def aggregate_from_directory(self,
                                 directory_path: str,
                                 url_prefix: Optional[str] = None,
                                 filter_low_relevance: bool = True,
                                 extensions: Optional[List[str]] = None) -> List[Dict]:
        """
        Aggregate news from all supported files in a directory.
        
        Args:
            directory_path: Path to directory
            url_prefix: Prefix for URLs (defaults to directory path)
            filter_low_relevance: Whether to filter low-relevance entities
            extensions: File extensions to process (defaults to .pdf, .jpg, .png)
            
        Returns:
            List of rectified documents
        """
        if extensions is None:
            extensions = ['.pdf', '.jpg', '.jpeg', '.png']
        
        directory = Path(directory_path)
        if url_prefix is None:
            url_prefix = str(directory)
        
        # Find all files
        files = []
        for ext in extensions:
            files.extend(directory.rglob(f"*{ext}"))
        
        if not files:
            print(f"No files found in {directory_path}")
            return []
        
        print(f"Found {len(files)} files to process")
        
        # Process each file
        results = []
        for file_path in tqdm(files, desc="Processing files"):
            try:
                url = f"{url_prefix}/{file_path.relative_to(directory)}"
                rectified = self.aggregate_from_file(
                    str(file_path),
                    url=url,
                    filter_low_relevance=filter_low_relevance
                )
                results.append(rectified)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
        
        return results
    
    def aggregate_from_text(self,
                           text: str,
                           url: str,
                           filter_low_relevance: bool = True) -> Dict:
        """
        Aggregate news from pre-extracted text (skip OCR step).
        
        Args:
            text: Pre-extracted text
            url: URL or identifier for the news item
            filter_low_relevance: Whether to filter low-relevance entities
            
        Returns:
            Rectified document dictionary
        """
        # Step 1: Extract entities using NER
        entities = self.ner_extractor.extract_entities(text)
        
        # Step 2: Rectify entities with TF-IDF weights
        rectified = self.rectifier.rectify(
            entities=entities,
            source_text=text,
            url=url,
            filter_low_relevance=filter_low_relevance
        )
        
        # Step 3: Index in database
        doc_id = self.database.index_document(rectified)
        rectified["_id"] = doc_id
        
        return rectified

