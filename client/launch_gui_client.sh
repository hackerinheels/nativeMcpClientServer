#!/bin/bash

# Set the base directory to the client directory
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

# Check if Python virtual environment exists in the parent directory
if [ ! -d "../.venv" ]; then
    echo "Error: Virtual environment not found. Please create it first."
    exit 1
fi

# Activate the virtual environment
source ../.venv/bin/activate

# Check for required system dependencies
if [ "$(uname)" = "Darwin" ]; then  # macOS
    # Check for Homebrew
    if ! command -v brew &> /dev/null; then
        echo "Homebrew is not installed. It's recommended for installing dependencies on macOS."
        echo "Visit https://brew.sh to install Homebrew."
        read -p "Continue without Homebrew? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        # Check for portaudio
        if ! brew list portaudio &> /dev/null; then
            echo "Installing portaudio via Homebrew..."
            brew install portaudio
        else
            echo "portaudio is already installed via Homebrew."
        fi
    fi
fi

# Run the GUI client
echo "=== Starting GUI Client ==="
python mcp_gui_client.py

# Exit when the GUI client is closed
exit 0 