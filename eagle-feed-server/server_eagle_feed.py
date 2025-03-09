#!/usr/bin/env python3
import os
import logging
import sys
import json
from typing import Any, List, Dict
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from dotenv import load_dotenv

# Create log directory if it doesn't exist
log_dir = os.path.join(os.path.dirname(__file__), "log")
os.makedirs(log_dir, exist_ok=True)

# Load environment variables from the local .env file
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("eagle-feed-server")

# Server Configuration
SERVER_HOST = os.getenv("EAGLE_FEED_SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("EAGLE_FEED_SERVER_PORT", "5003"))

# Create FastAPI app
app = FastAPI(title="Eagle Feed Server")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint that returns a welcome message."""
    return {"message": "Welcome to the Eagle Feed Server"}

@app.get("/eagle-feeds")
async def get_eagle_feeds():
    """Endpoint that returns a list of eagle feeds."""
    eagle_feeds = [
        {
            "location": "Big Bear Valley, California",
            "link": "https://www.friendsofbigbearvalley.org/eagle-cam/",
            "description": "This nest is home to the famous bald eagle pair Jackie and Shadow in Big Bear Valley, California. The Friends of Big Bear Valley maintain this popular live cam that has documented multiple nesting seasons. The nest is located in a Jeffrey Pine tree near Big Bear Lake in the San Bernardino Mountains."
        },
        {
            "location": "Channel Islands, California",
            "link": "https://www.youtube.com/watch?v=RRi7yvz0MUQ",
            "description": "This nest is located on Santa Cruz Island in Channel Islands National Park. The Institute for Wildlife Studies monitors this nest, which provides a unique view of bald eagles in their natural coastal habitat."
        }
    ]

    # Format the response in a standardized way
    formatted_content = "Here are some eagle live feeds you might be interested in:\n\n"
    for feed in eagle_feeds:
        formatted_content += f"{feed['location']}**\n"
        formatted_content += f"{feed['link']}\n"
        formatted_content += f"{feed['description']}\n\n"
    
    return {
        "raw_data": eagle_feeds,
        "formatted_content": formatted_content,
        "metadata": {
            "count": len(eagle_feeds),
            "type": "eagle_feeds"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

if __name__ == "__main__":
    logger.info(f"Starting Eagle Feed Server on {SERVER_HOST}:{SERVER_PORT}")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT) 
