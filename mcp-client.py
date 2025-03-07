#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import sys
import websockets
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("mcp-client")

# Configuration
MCP_HOST_URL = os.environ.get("MCP_HOST_URL", "ws://localhost:8765")

class MCPClient:
    def __init__(self, host_url: str):
        self.host_url = host_url
        self.websocket = None
        self.message_history: List[Dict[str, Any]] = []
        
    async def connect(self):
        """Connect to the MCP host."""
        try:
            self.websocket = await websockets.connect(self.host_url)
            logger.info(f"Connected to MCP host at {self.host_url}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP host: {str(e)}")
            return False
    
    async def receive_messages(self):
        """Listen for messages from the MCP host."""
        if not self.websocket:
            logger.error("Not connected to host")
            return
        
        try:
            async for message in self.websocket:
                try:
                    data = json.loads(message)
                    
                    if data["type"] == "llm_response":
                        logger.info(f"LLM Response for: '{data['user_message']}'")
                        print("\n----- LLM Response -----")
                        print(data["response"])
                        print("-----------------------\n")
                    
                    elif data["type"] == "history":
                        self.message_history = data["data"]
                        logger.info(f"Received message history ({len(self.message_history)} messages)")
                    
                    elif data["type"] == "history_cleared":
                        self.message_history = []
                        logger.info("Message history cleared")
                    
                except json.JSONDecodeError:
                    logger.error("Invalid JSON received from host")
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}")
        
        except websockets.exceptions.ConnectionClosed:
            logger.warning("Connection to MCP host closed")
        except Exception as e:
            logger.error(f"Error in receive_messages: {str(e)}")
    
    async def send_message(self, content: str):
        """Send a user message to the MCP host."""
        if not self.websocket:
            logger.error("Not connected to host")
            return False
        
        try:
            await self.websocket.send(json.dumps({
                "type": "user_message",
                "content": content
            }))
            return True
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            return False
    
    async def clear_history(self):
        """Clear the conversation history."""
        if not self.websocket:
            logger.error("Not connected to host")
            return False
        
        try:
            await self.websocket.send(json.dumps({
                "type": "clear_history"
            }))
            return True
        except Exception as e:
            logger.error(f"Failed to clear history: {str(e)}")
            return False
    
    async def close(self):
        """Close the connection to the MCP host."""
        if self.websocket:
            await self.websocket.close()
            logger.info("Connection to MCP host closed")

async def user_input_handler(client):
    """Handle user input from the console."""
    while True:
        try:
            print("\nEnter your message (type 'exit' to quit, 'clear' to clear history):")
            user_input = await asyncio.get_event_loop().run_in_executor(None, input)
            
            if user_input.lower() == 'exit':
                break
            elif user_input.lower() == 'clear':
                await client.clear_history()
            else:
                await client.send_message(user_input)
        
        except Exception as e:
            logger.error(f"Error handling user input: {str(e)}")
            break
    
    # Close the connection when done
    await client.close()

async def main():
    # Initialize and connect the client
    client = MCPClient(host_url=MCP_HOST_URL)
    
    if not await client.connect():
        logger.error("Failed to connect. Exiting.")
        return
    
    # Start tasks for receiving messages and handling user input
    receive_task = asyncio.create_task(client.receive_messages())
    input_task = asyncio.create_task(user_input_handler(client))
    
    # Wait for the input handler to complete (when user types 'exit')
    await input_task
    
    # Cancel the receive task
    receive_task.cancel()
    try:
        await receive_task
    except asyncio.CancelledError:
        pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Client stopped by user")
    except Exception as e:
        logger.error(f"Client error: {str(e)}")
