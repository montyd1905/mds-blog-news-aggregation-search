"""
FastAPI application for news aggregation and search
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
import os
from dotenv import load_dotenv

from ..database.nosql_db import NoSQLDatabase
from ..pipeline.aggregator import NewsAggregator
from ..search.engine import SearchEngine
from ..vector_db.cache import VectorCache
from ..llm.query_improver import LLMQueryImprover

# Load environment variables
load_dotenv()

app = FastAPI(
    title="News Aggregation & Search API",
    description="API for aggregating and searching news from offline sources",
    version="1.0.0"
)

# Initialize components
database = NoSQLDatabase()
aggregator = NewsAggregator(database=database)
search_engine = SearchEngine(database=database)
vector_cache = VectorCache()
llm_improver = LLMQueryImprover(vector_cache=vector_cache)


# Request/Response models
class SearchRequest(BaseModel):
    query: str
    use_llm_improvement: bool = False
    relevance_threshold: Optional[float] = None
    limit: int = 10


class SearchResponse(BaseModel):
    query: str
    improved_query: Optional[str] = None
    results: List[Dict]
    result_count: int
    cached: bool = False


class AggregateRequest(BaseModel):
    file_path: Optional[str] = None
    directory_path: Optional[str] = None
    url: Optional[str] = None
    filter_low_relevance: bool = True


class AggregateResponse(BaseModel):
    message: str
    documents_indexed: int
    document_ids: List[str]


# API Endpoints
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "News Aggregation & Search API",
        "version": "1.0.0",
        "endpoints": {
            "aggregate": "/aggregate",
            "search": "/search",
            "health": "/health",
            "stats": "/stats"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    try:
        count = database.count_documents()
        return {
            "status": "healthy",
            "database": "connected",
            "indexed_documents": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")


@app.get("/stats")
async def stats():
    """Get statistics about indexed documents."""
    try:
        count = database.count_documents()
        return {
            "total_documents": count,
            "database": database.db_name,
            "collection": database.collection_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@app.post("/aggregate", response_model=AggregateResponse)
async def aggregate_news(request: AggregateRequest):
    """
    Aggregate news from files or directories.
    """
    try:
        if request.file_path:
            # Aggregate from single file
            rectified = aggregator.aggregate_from_file(
                file_path=request.file_path,
                url=request.url,
                filter_low_relevance=request.filter_low_relevance
            )
            doc_ids = [rectified.get("_id", "unknown")]
            return AggregateResponse(
                message="File aggregated successfully",
                documents_indexed=1,
                document_ids=doc_ids
            )
        
        elif request.directory_path:
            # Aggregate from directory
            results = aggregator.aggregate_from_directory(
                directory_path=request.directory_path,
                filter_low_relevance=request.filter_low_relevance
            )
            doc_ids = [doc.get("_id", "unknown") for doc in results]
            return AggregateResponse(
                message=f"Directory aggregated successfully",
                documents_indexed=len(results),
                document_ids=doc_ids
            )
        
        else:
            raise HTTPException(
                status_code=400,
                detail="Either file_path or directory_path must be provided"
            )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Aggregation failed: {str(e)}")


@app.post("/aggregate/upload")
async def aggregate_upload(file: UploadFile = File(...)):
    """
    Upload and aggregate a file.
    """
    try:
        # Save uploaded file temporarily
        temp_path = f"/tmp/{file.filename}"
        with open(temp_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Aggregate
        rectified = aggregator.aggregate_from_file(
            file_path=temp_path,
            url=file.filename,
            filter_low_relevance=True
        )
        
        # Clean up
        os.remove(temp_path)
        
        return {
            "message": "File uploaded and aggregated successfully",
            "document_id": rectified.get("_id"),
            "url": rectified.get("url")
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@app.post("/search", response_model=SearchResponse)
async def search_news(request: SearchRequest):
    """
    Search for news articles.
    """
    try:
        query = request.query
        improved_query = None
        cached = False
        
        # Check cache first
        cached_result = vector_cache.find_similar_query(query, similarity_threshold=0.8)
        if cached_result and cached_result.get("results"):
            cached = True
            return SearchResponse(
                query=query,
                improved_query=cached_result.get("query"),
                results=cached_result["results"],
                result_count=len(cached_result["results"]),
                cached=True
            )
        
        # Use LLM improvement if requested
        improvement = None
        query_entities = None
        
        if request.use_llm_improvement:
            improvement = llm_improver.improve_query(query)
            improved_query = improvement.get("improved_query")
            query_entities = improvement.get("entities", {})
            
            # If LLM extracted entities, use them
            if query_entities and improvement.get("confidence", 0) > 0.5:
                # Build relevance thresholds for each entity category
                relevance_thresholds = None
                if request.relevance_threshold:
                    relevance_thresholds = {
                        category: request.relevance_threshold
                        for category in query_entities.keys()
                    }
                
                results = search_engine.search_with_entities(
                    query_entities=query_entities,
                    relevance_thresholds=relevance_thresholds,
                    limit=request.limit
                )
            else:
                # Fall back to regular search
                results = search_engine.search(
                    query=improved_query or query,
                    relevance_thresholds=None,  # Use default thresholds
                    limit=request.limit
                )
        else:
            # Regular search - extract entities first to build proper thresholds
            entities = search_engine.ner_extractor.extract_entities(query)
            query_params = {k: v for k, v in entities.items() if v}
            
            # Build relevance thresholds if provided
            relevance_thresholds = None
            if request.relevance_threshold and query_params:
                relevance_thresholds = {
                    category: request.relevance_threshold
                    for category in query_params.keys()
                }
            
            if query_params:
                results = search_engine.search_with_entities(
                    query_entities=query_params,
                    relevance_thresholds=relevance_thresholds,
                    limit=request.limit
                )
            else:
                results = []
        
        vector_cache.store_query(query, results, query_entities)
        
        # Remove internal MongoDB fields for response
        clean_results = []
        for result in results:
            clean_result = {
                "url": result.get("url"),
                "entities": result.get("entities"),
                "relevance_score": result.get("_relevance_score", 0.0)
            }
            clean_results.append(clean_result)
        
        return SearchResponse(
            query=query,
            improved_query=improved_query,
            results=clean_results,
            result_count=len(clean_results),
            cached=False
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@app.get("/document/{url:path}")
async def get_document(url: str):
    """
    Get a document by URL.
    """
    try:
        doc = database.get_by_url(url)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Remove internal fields
        doc.pop("_id", None)
        return doc
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get document: {str(e)}")


@app.delete("/document/{url:path}")
async def delete_document(url: str):
    """
    Delete a document by URL.
    """
    try:
        deleted = database.delete_by_url(url)
        if not deleted:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {"message": "Document deleted successfully", "url": url}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

