# Quick Start Guide

Get up and running with the News Aggregation & Search system in minutes.

## Prerequisites Check

```bash
# Check Python version (need 3.8+)
python3 --version

# Check if MongoDB is installed
mongod --version

# Check if Tesseract is installed
tesseract --version
```

## Quick Setup (5 minutes)

### 1. Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate  # or: venv\Scripts\activate on Windows

# Install Python packages
pip install -r requirements.txt

# Install spaCy model
python -m spacy download en_core_web_sm
```

### 2. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env and set at minimum:
# MONGODB_URI=mongodb://localhost:27017
# MONGODB_DB_NAME=news_aggregation
```

### 3. Start MongoDB

```bash
# macOS
brew services start mongodb-community

# Linux
sudo systemctl start mongod

# Or Docker
docker run -d -p 27017:27017 --name mongodb mongo:latest
```

### 4. Test with Sample Text

Create a test script `test_quick.py`:

```python
from src.database.nosql_db import NoSQLDatabase
from src.pipeline.aggregator import NewsAggregator
from src.search.engine import SearchEngine

# Initialize
db = NoSQLDatabase()
agg = NewsAggregator(database=db)
search = SearchEngine(database=db)

# Sample news text
text = """
London, April 12, 2025 - John Matthews, CEO of TechCorp, announced today 
at the Economic Summit in Times Square that the company will expand operations 
to the United Kingdom. Elena Rodriguez, the company's CFO, was also present 
at the press conference.
"""

# Aggregate
doc = agg.aggregate_from_text(
    text=text,
    url="https://example.com/news1"
)
print(f"✓ Indexed: {doc['url']}")

# Search
results = search.search("John Matthews London", limit=5)
print(f"✓ Found {len(results)} results")
for r in results:
    print(f"  - {r['url']} (score: {r.get('_relevance_score', 0)})")

db.close()
```

Run it:
```bash
python test_quick.py
```

### 5. Start API Server

```bash
python run_api.py
```

Visit: http://localhost:8000/docs

## Next Steps

- Add your PDF/image files and aggregate them
- Try the search API with different queries
- Explore the example scripts in `examples/`
- Read the full [SETUP.md](SETUP.md) for detailed configuration

## Common Issues

**"Tesseract not found"**
- Install: `brew install tesseract` (macOS) or `sudo apt-get install tesseract-ocr` (Linux)
- Or set `TESSERACT_CMD` in `.env`

**"spaCy model not found"**
- Run: `python -m spacy download en_core_web_sm`

**"MongoDB connection failed"**
- Make sure MongoDB is running
- Check `MONGODB_URI` in `.env`

