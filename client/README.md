# MCP GUI Client

A graphical user interface client for the MCP (Model Context Protocol) system. This client provides a user-friendly way to interact with the MCP host, including text input and audio recording/transcription capabilities.

## Features

- Text input for sending messages to the MCP host
- Audio recording and transcription using Google's Speech Recognition API
- Real-time display of responses from the MCP host
- Ability to clear conversation history

## Requirements

- Python 3.7+
- Tkinter (included with Python)
- SpeechRecognition
- PyAudio
- Websockets
- Other dependencies listed in `requirements.txt`

## Installation

### macOS

1. Make sure you have Python 3.7 or higher installed
2. Install system dependencies:
   ```bash
   brew install portaudio
   ```
3. Install Python dependencies:
   ```bash
   # Activate your virtual environment if you have one
   source .venv/bin/activate
   
   # Install dependencies using uv (recommended) or pip
   uv pip install -r client/requirements.txt
   
   # Or using pip
   # pip install -r client/requirements.txt
   ```

### Linux (Ubuntu/Debian)

1. Make sure you have Python 3.7 or higher installed
2. Install system dependencies:
   ```bash
   sudo apt-get install python3-pyaudio
   ```
3. Install Python dependencies:
   ```bash
   # Activate your virtual environment if you have one
   source .venv/bin/activate
   
   # Install dependencies using uv (recommended)
   uv pip install -r requirements.txt
   
   # Or using pip
   # pip install -r requirements.txt
   ```

### Windows

1. Make sure you have Python 3.7 or higher installed
2. Install dependencies:
   ```bash
   # Activate your virtual environment if you have one
   .venv\Scripts\activate
   
   # Install dependencies using uv (recommended)
   uv pip install -r requirements.txt
   
   # Or using pip
   # pip install -r requirements.txt
   ```

## Usage

1. Make sure the MCP host is running
2. Run the GUI client:

```bash
python mcp_gui_client.py
```

3. The client will automatically attempt to connect to the MCP host
4. Once connected, you can:
   - Type messages in the input box and click "Send"
   - Click "Record Audio" to record and transcribe speech (10 seconds by default)
   - Click "Clear History" to clear the conversation history

## About Speech Recognition

This client uses Google's Speech Recognition API for transcribing audio. The API:
- Requires an internet connection
- Is free to use for limited usage
- Provides good accuracy for English and many other languages
- Does not require an API key for basic usage

## Quick Start with Launcher Script

For convenience, you can use the launcher script:

```bash
# Make the script executable (only needed once)
chmod +x launch_all.sh

# Run the launcher
./launch_all.sh
```

The launcher script will:
1. Check if Python is installed
2. Install required system dependencies (portaudio)
3. Create a virtual environment if it doesn't exist
4. Install dependencies (using uv if available)
5. Start all MCP components (product server, analytics server, MCP host)
6. Run the GUI client

## Environment Variables

- `MCP_HOST_URL`: WebSocket URL of the MCP host (default: `ws://localhost:8765`)

## Troubleshooting

- If you encounter connection issues, make sure the MCP host is running and accessible
- For audio recording issues, check your microphone settings and permissions
- If PyAudio installation fails, make sure you have the required system dependencies installed

## License

This project is part of the MCP system. 