import os
import logging
import sys
import json
import asyncio
from typing import Any, List, Dict
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import StreamingResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("product-server")

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# Server configuration
SERVER_HOST = os.getenv("PRODUCT_SERVER_HOST", "localhost")
SERVER_PORT = int(os.getenv("PRODUCT_SERVER_PORT", "5001"))
PRODUCTS_API_URL = os.getenv("PRODUCTS_API_URL", "http://localhost:5087/api/products")

# Create FastAPI app
app = FastAPI(title="Product Server")

async def products(url: str) -> dict[str, Any] | None:
    """Make a request to the API with proper error handling."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching products: {str(e)}")
            return None

@app.get("/tools")
async def get_tools() -> List[Dict[str, Any]]:
    """Return the list of available tools."""
    return [
        {
            "name": "get_products",
            "description": "Get the list of available products from the product API.",
            "parameters": {}
        }
    ]

async def sse_generator(tool_name: str, params: Dict[str, Any]):
    """Generate SSE events for tool execution."""
    if tool_name == "get_products":
        logger.info(f"Running get_products tool via SSE")
        # Call the products function to get real data
        result = await products(PRODUCTS_API_URL)
        if result is not None:
            logger.info(f"Returning real product data via SSE: {str(result)[:100]}...")
            yield f"data: {json.dumps({'result': result})}\n\n"
        else:
            logger.error("Failed to fetch products from API")
            yield f"data: {json.dumps({'error': 'Failed to fetch products from API'})}\n\n"
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

@app.get("/products")
async def get_products():
    """Get a list of products."""
    try:
        # Fetch products from the external API
        async with httpx.AsyncClient() as client:
            response = await client.get(PRODUCTS_API_URL)
            response.raise_for_status()
            data = response.json()
            
            # Handle both dictionary with "products" key and direct list of products
            if isinstance(data, dict) and "products" in data:
                products = data["products"]
            elif isinstance(data, list):
                products = data
            else:
                products = []
                logger.warning(f"Unexpected response format: {type(data)}")
            
            # Format the response in a standardized way
            formatted_content = "Here are some products you might be interested in:\n\n"
            for product in products[:5]:  # Limit to 5 products
                formatted_content += f"{product['product_name']}\t"
                formatted_content += f"${product['brand_name']}\n"
            
            return {
                "raw_data": products[:10],  # Limit to 10 products in raw data
                "formatted_content": formatted_content,
                "metadata": {
                    "count": len(products),
                    "type": "products",
                    "source": PRODUCTS_API_URL
                }
            }
    except Exception as e:
        logger.error(f"Error fetching products: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching products: {str(e)}")

if __name__ == "__main__":
    logger.info(f"Starting Product Server with SSE support on {SERVER_HOST}:{SERVER_PORT}")
    logger.info(f"Will fetch products from {PRODUCTS_API_URL}")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
