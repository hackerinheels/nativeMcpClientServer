#!/bin/bash

# Set the base directory to the project root
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

# Check if Python virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Error: Virtual environment not found. Please create it first."
    exit 1
fi

# Activate the virtual environment
source .venv/bin/activate

# Run the command-line client
echo "=== Starting Command-Line Client ==="
python mcp-client.py

# Exit when the client is closed
exit 0 