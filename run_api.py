#!/usr/bin/env python3
"""
Run the News Aggregation & Search API server
"""

import uvicorn
from src.api.app import app

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True  # Enable auto-reload for development
    )

