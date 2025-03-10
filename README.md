# Native MCP Client Server

A native implementation of the MCP (Machine Conversation Protocol) client-server architecture with HTTP Server-Sent Events (SSE) for real-time communication.

## Overview

This project implements a simple MCP host that can discover and use tools from multiple tool servers. It includes:

1. **MCP Host**: A WebSocket server that communicates with clients and tool servers
2. **Product Server**: A tool server that provides product information via SSE
3. **Analytics Server**: A tool server that provides analytics data via SSE
4. **MCP Client**: A simple client for interacting with the MCP host

## Architecture

```
┌─────────────┐      WebSocket      ┌──────────┐      HTTP/SSE      ┌────────────────┐
│  MCP Client │<─────────────────-->│ MCP Host │<─────────────────->│  Tool Servers  │
└─────────────┘                     └──────────┘                    └────────────────┘
                                         │
                                         │ HTTP
                                         ▼
                                   ┌──────────────┐
                                   │ Ollama/Gemini│
                                   └──────────────┘
```

## Multi-Server Architecture

The system supports multiple tool servers, each providing different functionality:

```
                                                    ┌─────────────────────┐
                                                 ┌─>│ Product Server     │
                                                 │  │ - get_products     │
                                                 │  └─────────────────────┘
┌─────────────┐      WebSocket      ┌──────────┐ │
│  MCP Client │<─────────────────-->│ MCP Host │─┤
└─────────────┘                     └──────────┘ │
                                                 │  ┌─────────────────────┐
                                                 └─>│ Analytics Server    │
                                                    │ - get_analytics     │
                                                    └─────────────────────┘
```

## Features

- Tool discovery via HTTP endpoints
- Real-time tool execution with SSE
- WebSocket-based client-host communication
- Support for both Ollama and Gemini LLM backends
- Environment-based configuration
- Multiple tool servers (Product and Analytics)
- Dynamic tool discovery from all configured servers

## Setup

1. Create a virtual environment:
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:
   ```
   uv pip install httpx fastapi uvicorn websockets python-dotenv requests PyYAML
   ```

3. Configure environment variables:
   - For the MCP Host:
     ```
     cp .env.example .env.host
     ```
     Edit `.env.host` and add your Gemini API key if you want to use Gemini
   
   - For the Product Server:
     ```
     cp product-server/.env.example product-server/.env
     ```
     Edit `product-server/.env` if you need to change the product API URL
     
   - For the Analytics Server:
     ```
     cp analytics-server/.env.example analytics-server/.env
     ```
     Edit `analytics-server/.env` if you need to change the analytics API URL

## Configuration

The system uses environment variables for configuration:

### MCP Host
- `MCP_HOST_PORT`: Port for the WebSocket server (default: 8765)
- `OLLAMA_BASE_URL`: URL for Ollama API (default: http://localhost:11434)
- `OLLAMA_MODEL`: Model to use with Ollama (default: llama2)
- `USE_GEMINI`: Whether to use Gemini API (default: false)
- `GEMINI_API_KEY`: API key for Gemini (required if USE_GEMINI=true)
- `GEMINI_MODEL`: Model to use with Gemini (default: gemini-1.5-flash)

### Product Server
- `PRODUCT_SERVER_HOST`: Host for the product server (default: localhost)
- `PRODUCT_SERVER_PORT`: Port for the product server (default: 5001)
- `PRODUCTS_API_URL`: URL for the products API (default: http://localhost:5087/api/products)

### Analytics Server
- `ANALYTICS_SERVER_HOST`: Host for the analytics server (default: localhost)
- `ANALYTICS_SERVER_PORT`: Port for the analytics server (default: 5002)
- `ANALYTICS_API_URL`: URL for the analytics API (default: http://localhost:5088/api/analytics)

## Tool Server Configuration

Tool servers are configured in the `config.yaml` file:

```yaml
tool_servers:
  - url: "http://localhost:5001"  # Product Server
    path: "product-server/server_product.py"
  - url: "http://localhost:5002"  # Analytics Server
    path: "analytics-server/server_analytics.py"
```

To add more tool servers, simply add new entries to this list.

## Running the System

1. Start the tool servers:
   ```
   # Start the product server
   python product-server/server_product.py
   
   # Start the analytics server (in a separate terminal)
   python analytics-server/server_analytics.py
   ```

2. Start the MCP host:
   ```
   python mcp-host.py
   ```

3. The MCP client will automatically start if `CLIENT_SCRIPT_PATH` is set.

4. Interact with the system by sending messages like:
   - "get products" to fetch product data
   - "show analytics" or "get analytics for last week" to fetch analytics data

## Available Tools

### Product Server Tools
- `get_products`: Fetches product information from the configured API

### Analytics Server Tools
- `get_analytics`: Fetches analytics data with optional period parameter (daily, weekly, monthly)

## Tool Servers

Tool servers must implement:

1. A `/tools` endpoint that returns a list of available tools
2. A `/run` endpoint that executes a tool and returns results via SSE

## Adding New Tool Servers

To add a new tool server:

1. Create a new directory for your server (e.g., `new-server/`)
2. Implement the server with `/tools` and `/run` endpoints
3. Add the server to `config.yaml`
4. Update the MCP host's `check_and_use_tools` method to handle the new tools

## License

MIT 