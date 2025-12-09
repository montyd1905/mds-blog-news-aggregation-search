# Setup Guide

This guide will help you set up and run the News Aggregation & Search system.

## Prerequisites

1. **Python 3.8+** - The system requires Python 3.8 or higher
2. **MongoDB** - Install and run MongoDB locally or use a cloud instance
3. **Tesseract OCR** - Required for OCR functionality
   - macOS: `brew install tesseract`
   - Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
   - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
4. **OpenAI API Key** (optional) - For LLM query improvement feature

## Installation Steps

### 1. Clone and Navigate to Project

```bash
cd mds-blog-news-aggregation-search
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install spaCy Language Model

```bash
python -m spacy download en_core_web_sm
```

### 5. Configure Environment Variables

Copy the example environment file and update it:

```bash
cp .env.example .env
```

Edit `.env` and set:
- `MONGODB_URI` - Your MongoDB connection string (default: `mongodb://localhost:27017`)
- `MONGODB_DB_NAME` - Database name (default: `news_aggregation`)
- `OPENAI_API_KEY` - Your OpenAI API key (optional, for LLM features)
- `TESSERACT_CMD` - Path to tesseract executable (if not in PATH)
- `CHROMA_DB_PATH` - Path for vector database storage
- `MIN_ENTITY_RELEVANCE` - Minimum relevance threshold (default: 0.3)
- `VECTOR_CACHE_TTL` - Cache TTL in seconds (default: 3600)

### 6. Start MongoDB

Make sure MongoDB is running:

```bash
# macOS (if installed via Homebrew)
brew services start mongodb-community

# Linux
sudo systemctl start mongod

# Or use Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

## Usage

### Running the API Server

```bash
python run_api.py
```

The API will be available at `http://localhost:8000`

API Documentation: `http://localhost:8000/docs`

### Running Example Scripts

#### Aggregate News from Files

```bash
python examples/aggregate_example.py
```

Update the file paths in the script to point to your PDF/image files.

#### Search News Articles

```bash
python examples/search_example.py
```

Make sure you have indexed some documents first using the aggregate example.

## API Endpoints

### Health Check
```
GET /health
```

### Get Statistics
```
GET /stats
```

### Aggregate News
```
POST /aggregate
Body: {
  "file_path": "/path/to/file.pdf",
  "url": "https://example.com/article",
  "filter_low_relevance": true
}
```

### Upload and Aggregate
```
POST /aggregate/upload
Form data: file (PDF or image)
```

### Search News
```
POST /search
Body: {
  "query": "John Matthews London",
  "use_llm_improvement": false,
  "relevance_threshold": 0.4,
  "limit": 10
}
```

### Get Document
```
GET /document/{url}
```

### Delete Document
```
DELETE /document/{url}
```

## Project Structure

```
mds-blog-news-aggregation-search/
├── src/
│   ├── ocr/              # OCR text extraction
│   ├── ner/              # Named Entity Recognition
│   ├── rectifier/        # TF-IDF rectification
│   ├── database/         # NoSQL database interface
│   ├── search/           # Search engine
│   ├── vector_db/        # Vector database cache
│   ├── llm/              # LLM query improvement
│   ├── pipeline/         # Main aggregation pipeline
│   └── api/              # FastAPI application
├── examples/             # Example scripts
├── requirements.txt      # Python dependencies
├── run_api.py           # API server runner
└── README.md            # Project documentation
```

## Troubleshooting

### Tesseract Not Found
- Make sure Tesseract is installed and in your PATH
- Or set `TESSERACT_CMD` in `.env` to the full path

### spaCy Model Not Found
```bash
python -m spacy download en_core_web_sm
```

### MongoDB Connection Error
- Verify MongoDB is running
- Check `MONGODB_URI` in `.env`
- Test connection: `mongosh mongodb://localhost:27017`

### OpenAI API Errors
- LLM features are optional
- Set `OPENAI_API_KEY` in `.env` to enable
- Or set `use_llm_improvement: false` in search requests

## Next Steps

1. Add your news documents (PDFs/images) to a directory
2. Run the aggregation pipeline to index them
3. Use the search API to query indexed articles
4. Explore the example scripts for more usage patterns

