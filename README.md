# Gap.com API Discovery Project

A tool for discovering and analyzing the APIs used by Gap.com's web application by examining browser network traffic.

## Overview

This project provides a GUI application that allows you to:

1. Browse Gap.com within an embedded web browser
2. Automatically capture and analyze API calls made by the website
3. Document the structure and patterns of these APIs
4. Record audio notes about your findings

## Features

- **Embedded Web Browser**: Navigate Gap.com directly within the application
- **API Call Interception**: Automatically captures API requests and responses
- **Request Analysis**: Filters and categorizes API calls
- **Audio Recording**: Record voice notes about your findings
- **Data Export**: Save captured API data for further analysis

## Project Structure

```
api-discovery/
├── data/               # Captured API data and recordings
├── docs/               # Documentation about discovered APIs
├── scripts/            # Python scripts
│   ├── api_analyzer.py        # API analysis utilities
│   ├── api_discovery_gui.py   # Main GUI application
│   └── request_logger.py      # Network request logging
└── venv/               # Python virtual environment
```

## Installation

1. Clone the repository
2. Create and activate a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install PyQt5 PyQtWebEngine pyaudio
   ```
   
   Note: For PyAudio, you may need to install portaudio first:
   - macOS: `brew install portaudio`
   - Ubuntu: `sudo apt-get install portaudio19-dev`
   - Windows: PyAudio wheel should work directly



## API Documentation

As you discover APIs, document them in the `docs/api_documentation.md` file with the following information:

- Base URL
- Authentication method
- Available endpoints
- Request parameters
- Response structure
- Rate limits (if any)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

# MCP - Model Context Protocol

## Launcher Scripts

The MCP system includes several launcher scripts to help you run the different components:

1. **`launch_all.sh`**: Starts all components (servers and GUI client)
   ```bash
   ./launch_all.sh
   ```

2. **`launch_servers.sh`**: Starts only the servers (without any client)
   ```bash
   ./launch_servers.sh
   ```

3. **`client/launch_gui_client.sh`**: Starts only the GUI client
   ```bash
   cd client
   ./launch_gui_client.sh
   ```

4. **`launch_cli_client.sh`**: Starts only the command-line client
   ```bash
   ./launch_cli_client.sh
   ```

## Components

The MCP system consists of the following components:

1. **Product Server**: Provides product information
2. **Analytics Server**: Provides analytics data
3. **Eagle Feed Server**: Provides information about eagle live feeds
4. **MCP Host**: Manages client connections and tool discovery
5. **GUI Client**: Graphical user interface for interacting with the MCP system
6. **Command-Line Client**: Command-line interface for interacting with the MCP system 