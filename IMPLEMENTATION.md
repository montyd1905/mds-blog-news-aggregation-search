# Implementation Summary

This document describes the implementation of the News Aggregation & Search system as specified in the README.

## System Architecture

The system is built with a modular architecture, with each component handling a specific responsibility:

```
┌─────────────┐
│   OCR       │ → Extract text from PDFs/images
└─────────────┘
      ↓
┌─────────────┐
│   NER       │ → Extract named entities (people, locations, dates, etc.)
└─────────────┘
      ↓
┌─────────────┐
│ TF-IDF      │ → Add relevance weights to entities
│ Rectifier   │
└─────────────┘
      ↓
┌─────────────┐
│  NoSQL DB   │ → Index rectified documents
└─────────────┘
      ↓
┌─────────────┐
│   Search    │ → Query with NER-based Boolean search
│   Engine    │
└─────────────┘
```

## Components

### 1. OCR Module (`src/ocr/`)

**Purpose**: Extract text from offline documents (PDFs, images)

**Key Features**:
- Supports PDF text extraction (direct and OCR fallback)
- Supports image OCR using Tesseract
- Batch processing for directories
- Automatic file type detection

**Files**:
- `extractor.py`: `OCRExtractor` class

### 2. NER Module (`src/ner/`)

**Purpose**: Extract named entities from text

**Entity Categories**:
- People (PERSON)
- Locations (LOC, GPE)
- Dates (DATE)
- Countries (GPE → countries)
- Places (FAC)
- Events (EVENT, pattern matching)

**Key Features**:
- Uses spaCy's `en_core_web_sm` model
- Entity type mapping and categorization
- Date normalization
- Event extraction via pattern matching
- Country vs. location distinction

**Files**:
- `extractor.py`: `NERExtractor` class

### 3. TF-IDF Rectifier (`src/rectifier/`)

**Purpose**: Add relevance weights to entities using TF-IDF scoring

**Key Features**:
- Calculates TF-IDF scores for each entity
- Normalizes scores to 0-1 range
- Filters low-relevance entities (configurable threshold)
- Sorts entities by relevance
- Batch processing support

**Files**:
- `tfidf_rectifier.py`: `TFIDFRectifier` class

### 4. Database Module (`src/database/`)

**Purpose**: Store and query indexed news articles

**Key Features**:
- MongoDB-based NoSQL storage
- Indexed entity fields for efficient search
- Boolean search with relevance thresholds
- Relevance score calculation
- Document CRUD operations

**Files**:
- `nosql_db.py`: `NoSQLDatabase` class

### 5. Search Engine (`src/search/`)

**Purpose**: Process search queries and return ranked results

**Key Features**:
- NER extraction from search queries
- Boolean search parameter building
- Relevance threshold application
- Result ranking by relevance score

**Files**:
- `engine.py`: `SearchEngine` class

### 6. Vector Database Cache (`src/vector_db/`)

**Purpose**: Cache search queries and results for performance

**Key Features**:
- Semantic similarity search using ChromaDB
- TTL-based cache expiration
- Query result caching
- Similar query detection

**Files**:
- `cache.py`: `VectorCache` class

### 7. LLM Query Improvement (`src/llm/`)

**Purpose**: Improve vague or low-quality search queries

**Key Features**:
- Uses OpenAI API for query improvement
- Extracts entities from improved queries
- Uses vector cache context for better improvements
- Confidence scoring

**Files**:
- `query_improver.py`: `LLMQueryImprover` class

### 8. Aggregation Pipeline (`src/pipeline/`)

**Purpose**: Orchestrate the complete aggregation workflow

**Key Features**:
- End-to-end pipeline: OCR → NER → Rectification → Indexing
- Single file processing
- Directory batch processing
- Pre-extracted text support

**Files**:
- `aggregator.py`: `NewsAggregator` class

### 9. API (`src/api/`)

**Purpose**: RESTful API for aggregation and search

**Endpoints**:
- `GET /` - API information
- `GET /health` - Health check
- `GET /stats` - Statistics
- `POST /aggregate` - Aggregate from file/directory
- `POST /aggregate/upload` - Upload and aggregate file
- `POST /search` - Search news articles
- `GET /document/{url}` - Get document by URL
- `DELETE /document/{url}` - Delete document

**Files**:
- `app.py`: FastAPI application

## Data Flow

### Aggregation Flow

1. **Input**: PDF/image file or directory
2. **OCR**: Extract text from document
3. **NER**: Extract named entities from text
4. **Rectification**: Calculate TF-IDF weights for entities
5. **Indexing**: Store rectified document in NoSQL database

### Search Flow

1. **Input**: Search query string
2. **Cache Check**: Check vector cache for similar queries
3. **LLM Improvement** (optional): Improve vague queries
4. **NER Extraction**: Extract entities from query
5. **Query Building**: Build Boolean search parameters
6. **Database Query**: Execute search with relevance thresholds
7. **Ranking**: Sort results by relevance score
8. **Caching**: Store query and results in vector cache
9. **Output**: Ranked list of matching documents

## Configuration

Configuration is done via environment variables (`.env` file):

- `MONGODB_URI`: MongoDB connection string
- `MONGODB_DB_NAME`: Database name
- `OPENAI_API_KEY`: OpenAI API key (for LLM features)
- `TESSERACT_CMD`: Tesseract executable path
- `CHROMA_DB_PATH`: Vector database storage path
- `MIN_ENTITY_RELEVANCE`: Minimum relevance threshold (default: 0.3)
- `VECTOR_CACHE_TTL`: Cache TTL in seconds (default: 3600)

## Production Considerations

As mentioned in the README, the implementation includes:

1. **Low-relevance filtering**: Entities below threshold are filtered during aggregation
2. **Vector database caching**: Query results are cached for similar queries
3. **LLM query improvement**: Vague queries are improved using OpenAI

## Dependencies

Key dependencies:
- `spacy`: NLP and NER
- `pytesseract`: OCR
- `pymongo`: MongoDB client
- `chromadb`: Vector database
- `openai`: LLM integration
- `fastapi`: API framework
- `scikit-learn`: TF-IDF calculation

See `requirements.txt` for complete list.

## Testing

Example scripts are provided in `examples/`:
- `aggregate_example.py`: Aggregation examples
- `search_example.py`: Search examples

## Future Enhancements

Potential improvements:
- Support for more file formats
- Custom NER models for domain-specific entities
- Advanced relevance scoring algorithms
- Multi-language support
- Real-time indexing
- Distributed search
- Analytics and reporting

