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
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

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
CLIENT_SCRIPT_PATH = os.getenv("CLIENT_SCRIPT_PATH", "../mcp-client.py")

def load_tool_servers():
    """Load tool server configurations from YAML file."""
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('tool_servers', [])
    except Exception as e:
        logger.error(f"Failed to load tool servers from {config_path}: {str(e)}")
        return []

class MCPHost:
    """MCP Host that manages client connections and tool discovery."""
    def __init__(self, host_port: int, ollama_url: str, ollama_model: str):
        self.host_port = host_port
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.available_tools = []
        
        # Discover available tools
        self.available_tools = self.discover_tools()
        logger.info(f"Discovered {len(self.available_tools)} tools")
        
        # Log the available tools
        for tool in self.available_tools:
            logger.info(f"Tool: {tool['name']} - {tool['description']}")
        
        self.clients = set()
        self.messages_history: List[Dict[str, Any]] = []

    def discover_tools(self) -> List[Dict[str, Any]]:
        """Discover available tools from registered tool servers."""
        tools = []
        for server in load_tool_servers():
            server_url = server["url"]
            server_name = server.get("name", "unknown")
            server_path = server.get("path", "")
            server_description = server.get("description", "")
            
            try:
                # Add the eagle feed tool
                if "eagle" in server_name.lower():
                    tools.append({
                        "name": "get_eagle_feeds",
                        "description": "Get information about eagle live feeds and webcams",
                        "parameters": {},
                        "url": f"{server_url}{server_path}"
                    })
                    logger.info(f"Added eagle feed tool from {server_url}")
                
                # Add the product tool
                elif "product" in server_name.lower():
                    tools.append({
                        "name": "get_products",
                        "description": "Get information about available products",
                        "parameters": {},
                        "url": f"{server_url}{server_path}"
                    })
                    logger.info(f"Added product tool from {server_url}")
                
                # Add the analytics tool
                elif "analytics" in server_name.lower():
                    tools.append({
                        "name": "get_analytics",
                        "description": "Get analytics data and metrics",
                        "parameters": {},
                        "url": f"{server_url}{server_path}"
                    })
                    logger.info(f"Added analytics tool from {server_url}")
                
                # For other servers, try to discover tools dynamically
                else:
                    try:
                        response = requests.get(f"{server_url}/tools")
                        if response.status_code == 200:
                            server_tools = response.json()
                            tools.extend(server_tools)
                            logger.info(f"Discovered {len(server_tools)} tools from {server_url}")
                        else:
                            logger.warning(f"Failed to discover tools from {server_url}: {response.status_code}")
                    except Exception as e:
                        logger.error(f"Error discovering tools from {server_url}: {str(e)}")
            except Exception as e:
                logger.error(f"Error processing server {server_url}: {str(e)}")
        
        return tools

    async def handle_client(self, websocket):
        """Handle a client connection."""
        client_id = id(websocket)
        logger.info(f"New client connected: {client_id}")
        
        # Initialize client state
        message_history = []
        
        try:
            # Send welcome message
            await websocket.send(json.dumps({
                "type": "system_message",
                "content": "Connected to MCP Host. Type a message to begin."
            }))
            
            # Main message loop
            async for message in websocket:
                try:
                    data = json.loads(message)
                    message_type = data.get("type", "")
                    
                    if message_type == "user_message":
                        content = data.get("content", "").strip()
                        if not content:
                            continue
                        
                        logger.info(f"Received message from client {client_id}: {content[:50]}...")
                        
                        # Add to history
                        message_history.append({
                            "role": "user",
                            "content": content
                        })
                        
                        # Check if we should use a tool
                        tool_response = await self.check_and_use_tools(content)
                        
                        if tool_response:
                            # Tool was used, send the response
                            logger.info(f"Sending tool response to client {client_id}")
                            
                            # Add to history
                            message_history.append({
                                "role": "assistant",
                                "content": tool_response
                            })
                            
                            # Send response to client
                            await websocket.send(json.dumps({
                                "type": "llm_response",
                                "user_message": content,
                                "response": tool_response
                            }))
                        else:
                            # No tool was used, query LLM
                            logger.info(f"Querying LLM for client {client_id}")
                            
                            # Format the conversation history for the LLM
                            formatted_history = "\n".join([
                                f"{msg['role'].upper()}: {msg['content']}"
                                for msg in message_history[-5:]  # Use last 5 messages
                            ])
                            
                            # Query the LLM
                            llm_response = self.query_gemini(formatted_history)
                            
                            # Add to history
                            message_history.append({
                                "role": "assistant",
                                "content": llm_response
                            })
                            
                            # Send response to client
                            await websocket.send(json.dumps({
                                "type": "llm_response",
                                "user_message": content,
                                "response": llm_response
                            }))
                    
                    elif message_type == "clear_history":
                        logger.info(f"Clearing history for client {client_id}")
                        message_history = []
                        await websocket.send(json.dumps({
                            "type": "history_cleared"
                        }))
                    
                    else:
                        logger.warning(f"Unknown message type from client {client_id}: {message_type}")
                
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from client {client_id}")
                except Exception as e:
                    logger.error(f"Error handling message from client {client_id}: {str(e)}")
        
        except websockets.exceptions.ConnectionClosed as e:
            logger.info(f"Client {client_id} disconnected: {e.code} {e.reason}")
        except Exception as e:
            logger.error(f"Error handling client {client_id}: {str(e)}")
        finally:
            logger.info(f"Client {client_id} connection closed")
            # Perform any cleanup needed for this client

    async def check_and_use_tools(self, message: str) -> Optional[str]:
        """Check if the message requires using a tool and use it if needed."""
        try:
            # First, let's create a prompt for the LLM to decide which tool to use
            tool_descriptions = "\n".join([
                f"- {tool['name']}: {tool['description']}" 
                for tool in self.available_tools
            ])
            
            tool_selection_prompt = f"""
            Based on the user's message, determine if any of the following tools should be used:
            
            {tool_descriptions}
            
            User message: "{message}"
            
            If a tool should be used, respond with the tool name only. If no tool is appropriate, respond with "none".
            """
            
            # Print the tool selection prompt for debugging
            print("\n=== TOOL SELECTION PROMPT ===")
            print(tool_selection_prompt)
            print("=============================\n")
            
            # Use Gemini to decide which tool to use
            tool_decision = self.query_gemini(tool_selection_prompt).strip().lower()
            
            # Print the tool decision for debugging
            print(f"\n=== TOOL DECISION ===")
            print(f"Raw response: {tool_decision}")
            print(f"========================\n")
            
            logger.info(f"Tool decision: {tool_decision}")
            
            # If no tool is needed, return None
            if tool_decision == "none" or not tool_decision:
                print("No tool selected.")
                return None
            
            # Find the selected tool
            selected_tool = None
            for tool in self.available_tools:
                if tool["name"].lower() in tool_decision:
                    selected_tool = tool
                    print(f"Selected tool: {tool['name']}")
                    break
            
            if not selected_tool:
                logger.warning(f"Tool '{tool_decision}' not found in available tools")
                print(f"Tool '{tool_decision}' not found in available tools")
                return None
            
            # Use the selected tool
            tool_name = selected_tool["name"]
            tool_url = selected_tool["url"]
            
            logger.info(f"Using tool: {tool_name} from {tool_url}")
            print(f"\n=== EXECUTING TOOL ===")
            print(f"Tool: {tool_name}")
            print(f"URL: {tool_url}")
            print(f"========================\n")
            
            try:
                # Make a request to the tool server
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(tool_url)
                    print(f"Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        # Parse the response
                        response_data = response.json()
                        
                        # Check if the response is in the standardized format
                        if "formatted_content" in response_data:
                            # Use the pre-formatted content from the server
                            formatted_content = response_data["formatted_content"]
                            print(f"\n=== TOOL RESULT (Standardized) ===")
                            print(formatted_content[:200] + "..." if len(formatted_content) > 200 else formatted_content)
                            print("====================\n")
                            return formatted_content
                        else:
                            # Legacy format - just return the raw data as JSON
                            print(f"\n=== TOOL RESULT (Legacy) ===")
                            print(str(response_data)[:200] + "..." if len(str(response_data)) > 200 else str(response_data))
                            print("====================\n")
                            return f"Here's the information I found:\n\n```json\n{json.dumps(response_data, indent=2)}\n```"
                    else:
                        error_msg = f"I tried to use the {tool_name} tool, but encountered an error (HTTP {response.status_code}). Please try again later."
                        logger.error(f"Tool request failed: {response.status_code}")
                        print(f"Error: {error_msg}")
                        return error_msg
            
            except httpx.RequestError as e:
                logger.error(f"Request error using tool {tool_name}: {str(e)}")
                return f"I tried to use the {tool_name} tool, but encountered a connection error. Please check if the service is available and try again."
            
            except httpx.TimeoutException:
                logger.error(f"Timeout using tool {tool_name}")
                return f"The {tool_name} tool is taking too long to respond. Please try again later."
            
            except Exception as e:
                logger.error(f"Error using tool {tool_name}: {str(e)}")
                return f"I encountered an error while using the {tool_name} tool: {str(e)}. Please try again later."
        
        except Exception as e:
            logger.error(f"Error in check_and_use_tools: {str(e)}")
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
        
        try:
            async with websockets.serve(self.handle_client, "localhost", self.host_port):
                await asyncio.Future()  # Run forever
        except Exception as e:
            logger.error(f"Error starting MCP Host: {str(e)}")
            raise

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