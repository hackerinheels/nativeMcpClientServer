import asyncio
import json
import logging
import os
import sys
import subprocess
import requests
import yaml
import websockets
from pathlib import Path
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv(".env.host")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mcp-host")

# Host Configuration from environment variables
USE_GEMINI = os.getenv("USE_GEMINI", "false").lower() == "true"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-pro")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:latest")
MCP_HOST_PORT = int(os.getenv("MCP_HOST_PORT", "8765"))
CLIENT_SCRIPT_PATH = os.getenv("CLIENT_SCRIPT_PATH", "./mcp-client.py")

# Load tool server configuration
config_path = Path(__file__).parent / "config.yaml"
try:
    with open(config_path) as f:
        config = yaml.safe_load(f)
    tool_servers = config["tool_servers"]
    logger.info(f"Discovered {len(tool_servers)} tool servers in config")
except Exception as e:
    logger.error(f"Failed to load tool servers from {config_path}: {str(e)}")
    sys.exit(1)

class MCPHost:
    def __init__(self, host_port: int, ollama_url: str, ollama_model: str):
        self.host_port = host_port
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.clients = set()
        self.messages_history: List[Dict[str, Any]] = []
        self.available_tools = self.discover_tools()
        
    def discover_tools(self) -> List[Dict[str, Any]]:
        """Discover available tools from registered tool servers."""
        tools = []
        for server in tool_servers:
            server_url = server["url"]
            try:
                response = requests.get(f"{server_url}/tools")
                if response.status_code == 200:
                    server_tools = response.json()
                    tools.extend(server_tools)
                    logger.info(f"Discovered {len(server_tools)} tools from {server_url}")
            except Exception as e:
                logger.error(f"Failed to discover tools from {server_url}: {str(e)}")
        return tools

    async def handle_client(self, websocket):
        """Handle a connected client."""
        self.clients.add(websocket)
        logger.info("Client connected")
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    logger.info(f"Received message from client: {data}")
                    
                    # Handle different message formats
                    if "type" in data and data["type"] == "user_message":
                        user_message = data["content"]
                    elif "message" in data:
                        user_message = data["message"]
                    else:
                        logger.error(f"Unknown message format: {data}")
                        await websocket.send(json.dumps({"error": "Unknown message format"}))
                        continue
                    
                    self.messages_history.append({"role": "user", "content": user_message})
                    
                    # Check if the message matches any available tools
                    tool_response = await self.check_and_use_tools(user_message)
                    if tool_response:
                        # Tool was used, send the response
                        self.messages_history.append({"role": "assistant", "content": tool_response})
                        await websocket.send(json.dumps({
                            "type": "llm_response",
                            "user_message": user_message,
                            "response": tool_response
                        }))
                        continue
                    
                    # No tool matched, use LLM
                    if USE_GEMINI and GEMINI_API_KEY:
                        # Use Gemini API
                        response_text = self.query_gemini(user_message)
                        self.messages_history.append({"role": "assistant", "content": response_text})
                        await websocket.send(json.dumps({
                            "type": "llm_response",
                            "user_message": user_message,
                            "response": response_text
                        }))
                    else:
                        # Use Ollama
                        # Prepare the Ollama request with tools
                        ollama_request = {
                            "model": self.ollama_model,
                            "messages": self.messages_history,
                            "tools": self.available_tools
                        }

                        # Make request to Ollama
                        response = requests.post(f"{self.ollama_url}/api/chat", json=ollama_request)
                        if response.status_code == 200:
                            assistant_message = response.json()["message"]
                            self.messages_history.append({"role": "assistant", "content": assistant_message["content"]})
                            await websocket.send(json.dumps({
                                "type": "llm_response",
                                "user_message": user_message,
                                "response": assistant_message["content"]
                            }))
                        else:
                            error_msg = f"Ollama request failed with status {response.status_code}"
                            logger.error(error_msg)
                            await websocket.send(json.dumps({"error": error_msg}))
                except Exception as e:
                    error_msg = f"Error processing message: {str(e)}"
                    logger.error(error_msg)
                    await websocket.send(json.dumps({"error": error_msg}))

        except websockets.exceptions.ConnectionClosed:
            logger.info("Client disconnected")
        finally:
            self.clients.remove(websocket)
    
    async def check_and_use_tools(self, message: str) -> Optional[str]:
        """Check if the message matches any available tools and use them if appropriate."""
        message_lower = message.lower().strip()
        
        # Check for get_products tool
        if "get products" in message_lower or "fetch products" in message_lower or "show products" in message_lower:
            logger.info("Using get_products tool")
            try:
                # Find the get_products tool
                get_products_tool = None
                for tool in self.available_tools:
                    if tool.get("name") == "get_products":
                        get_products_tool = tool
                        break
                
                if not get_products_tool:
                    logger.error("get_products tool not found")
                    return None
                
                # Make a request to the tool server
                server_url = tool_servers[0]["url"]  # Assuming the first server is the product server
                logger.info(f"Making SSE request to {server_url}/run")
                
                # Use httpx for SSE support
                async with httpx.AsyncClient() as client:
                    async with client.stream('POST', f"{server_url}/run", json={
                        "name": "get_products",
                        "parameters": {}
                    }, timeout=30.0) as response:
                        if response.status_code == 200:
                            logger.info("Receiving SSE stream...")
                            products_data = None
                            
                            # Process the SSE stream
                            async for line in response.aiter_lines():
                                if line.startswith("data: "):
                                    try:
                                        data = json.loads(line[6:])
                                        if "result" in data:
                                            products_data = data["result"]
                                            logger.info(f"Received products data via SSE: {str(products_data)[:100]}...")
                                        elif "error" in data:
                                            logger.error(f"Error from SSE stream: {data['error']}")
                                    except json.JSONDecodeError:
                                        logger.error(f"Failed to parse SSE data: {line}")
                                elif line.startswith("event: close"):
                                    logger.info("SSE stream closed by server")
                                    break
                            
                            if products_data:
                                # Format the products data into a nice response
                                response_text = "Here are the products I found:\n\n"
                                
                                if isinstance(products_data, list):
                                    # Handle list of products
                                    for i, product in enumerate(products_data[:10], 1):
                                        response_text += f"{i}. {product.get('product_name', 'Unknown')}"
                                        if 'brand_name' in product:
                                            response_text += f" by {product.get('brand_name', 'Unknown')}"
                                        response_text += "\n\n"
                                    
                                    if len(products_data) > 10:
                                        response_text += f"(Showing 10 of {len(products_data)} products)"
                                    elif len(products_data) == 0:
                                        response_text = "No products were found."
                                else:
                                    # Handle other formats
                                    response_text += f"Found product data: {json.dumps(products_data, indent=2)}"
                                    
                                logger.info(f"Returning response: {response_text[:100]}...")
                                return response_text
                            else:
                                logger.error("No product data received from SSE stream")
                        else:
                            logger.error(f"Tool execution failed with status {response.status_code}")
                            
            except Exception as e:
                logger.error(f"Error using get_products tool: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        return None

    def query_gemini(self, message: str) -> str:
        """Query the Gemini API with the given message."""
        try:
            logger.info(f"Querying Gemini API with message: {message[:50]}...")
            url = f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_MODEL}:generateContent"
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": GEMINI_API_KEY
            }
            
            # Prepare the request payload
            payload = {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": message}]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.7,
                    "topP": 0.8,
                    "topK": 40,
                    "maxOutputTokens": 2048
                }
            }
            
            # Add conversation history
            for msg in self.messages_history[:-1]:  # Exclude the current message
                role = "user" if msg["role"] == "user" else "model"
                payload["contents"].append({
                    "role": role,
                    "parts": [{"text": msg["content"]}]
                })
            
            logger.info(f"Sending request to Gemini API with {len(payload['contents'])} messages")
            
            # Make the API request
            response = requests.post(url, headers=headers, json=payload)
            
            logger.info(f"Received response from Gemini API with status code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                response_text = result["candidates"][0]["content"]["parts"][0]["text"]
                logger.info(f"Gemini response: {response_text[:50]}...")
                return response_text
            else:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return f"Error: Unable to get response from Gemini (Status {response.status_code})"
                
        except Exception as e:
            logger.error(f"Error querying Gemini: {str(e)}")
            return f"Error: {str(e)}"

    async def start(self):
        """Start the MCP host server."""
        logger.info(f"Starting MCP Host on port {self.host_port}")
        if USE_GEMINI:
            logger.info(f"Using Gemini API with model {GEMINI_MODEL}")
        else:
            logger.info(f"Using Ollama at {self.ollama_url} with model {self.ollama_model}")
        logger.info(f"Discovered {len(self.available_tools)} total tools")
        
        # Start the websocket server
        async with websockets.serve(self.handle_client, "localhost", self.host_port):
            # Keep running forever
            await asyncio.Future()

if __name__ == "__main__":
    host = MCPHost(MCP_HOST_PORT, OLLAMA_BASE_URL, OLLAMA_MODEL)
    
    # Start the client if path is specified
    if CLIENT_SCRIPT_PATH:
        try:
            import subprocess
            subprocess.Popen([sys.executable, CLIENT_SCRIPT_PATH])
            logger.info(f"Started client from {CLIENT_SCRIPT_PATH}")
        except Exception as e:
            logger.error(f"Failed to start client: {str(e)}")
    
    # Start the host server
    asyncio.run(host.start())