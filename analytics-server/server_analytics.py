import os
import logging
import sys
import json
import asyncio
from typing import Any, List, Dict
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("analytics-server")

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Server configuration
SERVER_HOST = os.getenv("ANALYTICS_SERVER_HOST", "localhost")
SERVER_PORT = int(os.getenv("ANALYTICS_SERVER_PORT", "5002"))
ANALYTICS_API = os.getenv("ANALYTICS_API_URL", "http://localhost:5088/api/analytics")

# Create FastAPI app
app = FastAPI(title="Analytics Server")

async def analytics(url: str) -> dict[str, Any] | None:
    """Make a request to the API with proper error handling."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching analytics: {str(e)}")
            return None

@app.get("/tools")
async def get_tools() -> List[Dict[str, Any]]:
    """Return the list of available tools."""
    return [
        {
            "name": "get_analytics",
            "description": "Get analytics data from the analytics API.",
            "parameters": {
                "period": {
                    "type": "string",
                    "description": "Time period for analytics (daily, weekly, monthly)",
                    "default": "daily"
                }
            }
        }
    ]

async def sse_generator(tool_name: str, params: Dict[str, Any]):
    """Generate SSE events for tool execution."""
    if tool_name == "get_analytics":
        period = params.get("period", "daily")
        logger.info(f"Running get_analytics tool via SSE for period: {period}")
        
        # For testing, return structured test data
        if not ANALYTICS_API.startswith("http://localhost:5088"):
            # Call the analytics function to get real data
            result = await analytics(f"{ANALYTICS_API}?period={period}")
            if result:
                logger.info(f"Returning real analytics data via SSE: {str(result)[:100]}...")
                yield f"data: {json.dumps({'result': result})}\n\n"
            else:
                logger.error("Failed to fetch analytics from API")
                yield f"data: {json.dumps({'error': 'Failed to fetch analytics from API'})}\n\n"
        else:
            # Return test data for demonstration
            test_data = {
                "period": period,
                "metrics": {
                    "visitors": 1250,
                    "page_views": 3750,
                    "bounce_rate": 42.5,
                    "avg_session_duration": "2m 15s"
                },
                "top_pages": [
                    {"url": "/products", "views": 1200},
                    {"url": "/home", "views": 950},
                    {"url": "/about", "views": 450}
                ],
                "traffic_sources": {
                    "direct": 45,
                    "search": 30,
                    "social": 15,
                    "referral": 10
                }
            }
            logger.info(f"Returning test analytics data via SSE: {test_data}")
            yield f"data: {json.dumps({'result': test_data})}\n\n"
    else:
        logger.error(f"Unknown tool: {tool_name}")
        yield f"data: {json.dumps({'error': f'Unknown tool: {tool_name}'})}\n\n"
    
    # End the SSE stream
    yield "event: close\ndata: {}\n\n"

@app.post("/run")
async def run_tool(request: Request) -> StreamingResponse:
    """Run a tool based on the request and return results as SSE."""
    data = await request.json()
    tool_name = data.get("name")
    parameters = data.get("parameters", {})
    logger.info(f"Received tool request via SSE: {tool_name}")
    
    return StreamingResponse(
        sse_generator(tool_name, parameters),
        media_type="text/event-stream"
    )

if __name__ == "__main__":
    logger.info(f"Starting Analytics Server with SSE support on {SERVER_HOST}:{SERVER_PORT}")
    logger.info(f"Will fetch analytics from {ANALYTICS_API}")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT) 