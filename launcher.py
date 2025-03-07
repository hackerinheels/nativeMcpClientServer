#!/usr/bin/env python3
import os
import sys
import time
import signal
import subprocess
import argparse
from pathlib import Path

# Get the actual directory where this script is located
script_dir = Path(__file__).parent.absolute()

# Default paths using hyphens instead of underscores
DEFAULT_HOST_PATH = "mcp-host.py"
DEFAULT_CLIENT_PATH = "mcp-client.py"
DEFAULT_SERVER_PATH = "product-server/server_product.py"

# Parse command line arguments
parser = argparse.ArgumentParser(description="Launch MCP system components")
parser.add_argument("--host", action="store_true", help="Launch the MCP host")
parser.add_argument("--client", action="store_true", help="Launch the MCP client")
parser.add_argument("--server", action="store_true", help="Launch the product server")
parser.add_argument("--all", action="store_true", help="Launch all components")
parser.add_argument("--host-path", default=DEFAULT_HOST_PATH, help=f"Path to host script (default: {DEFAULT_HOST_PATH})")
parser.add_argument("--client-path", default=DEFAULT_CLIENT_PATH, help=f"Path to client script (default: {DEFAULT_CLIENT_PATH})")
parser.add_argument("--server-path", default=DEFAULT_SERVER_PATH, help=f"Path to server script (default: {DEFAULT_SERVER_PATH})")
args = parser.parse_args()

# If no specific components are selected, show help
if not (args.host or args.client or args.server or args.all):
    parser.print_help()
    sys.exit(1)

# Convert paths to absolute paths
current_dir = Path.cwd()
host_path = current_dir / args.host_path
client_path = current_dir / args.client_path
server_path = current_dir / args.server_path

# Check if paths exist, and try alternative naming conventions if needed
if not host_path.exists():
    # Try alternate naming (underscore instead of hyphen)
    alt_host_path = current_dir / args.host_path.replace("-", "_")
    if alt_host_path.exists():
        print(f"Note: Using '{alt_host_path}' instead of '{host_path}'")
        host_path = alt_host_path
    else:
        print(f"Warning: Host script not found at {host_path}")
        print(f"         Also checked {alt_host_path}")

if not client_path.exists():
    # Try alternate naming (underscore instead of hyphen)
    alt_client_path = current_dir / args.client_path.replace("-", "_")
    if alt_client_path.exists():
        print(f"Note: Using '{alt_client_path}' instead of '{client_path}'")
        client_path = alt_client_path
    else:
        print(f"Warning: Client script not found at {client_path}")
        print(f"         Also checked {alt_client_path}")

if not server_path.exists():
    # Try alternate naming for server directory and file
    alt_server_path = current_dir / args.server_path.replace("-", "_")
    if alt_server_path.exists():
        print(f"Note: Using '{alt_server_path}' instead of '{server_path}'")
        server_path = alt_server_path
    else:
        # Try product_server directory
        alt_server_dir_path = current_dir / "product-server" / "server.py"
        if alt_server_dir_path.exists():
            print(f"Note: Using '{alt_server_dir_path}' instead of '{server_path}'")
            server_path = alt_server_dir_path
        else:
            print(f"Warning: Server script not found at {server_path}")
            print(f"         Also checked {alt_server_path} and {alt_server_dir_path}")

# Show the paths being used
print(f"\nUsing the following paths:")
print(f"Host:   {host_path}")
print(f"Client: {client_path}")
print(f"Server: {server_path}\n")

# Check if specified paths exist
for path, name, required in [
    (host_path, "Host", args.host or args.all),
    (client_path, "Client", args.client or args.all),
    (server_path, "Server", args.server or args.all)
]:
    if required and not path.exists():
        print(f"Error: {name} script not found at {path}")
        sys.exit(1)

# List to keep track of started processes
processes = []

def signal_handler(sig, frame):
    print("\nShutting down all processes...")
    for process in processes:
        if process.poll() is None:  # If process is still running
            process.terminate()
    print("Shutdown complete.")
    sys.exit(0)

# Register signal handler for graceful shutdown
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def start_process(script_path, process_name):
    """Start a Python script as a subprocess and return the process object."""
    if not script_path.exists():
        print(f"Warning: Skipping {process_name} - script not found at {script_path}")
        return None
        
    print(f"Starting {process_name}...")
    process = subprocess.Popen([sys.executable, str(script_path)], 
                               env=os.environ.copy())
    print(f"{process_name} started with PID {process.pid}")
    processes.append(process)
    return process

# Start components based on arguments
try:
    server_process = None
    host_process = None
    client_process = None
    
    # Determine which components to start
    start_server = args.server or args.all
    start_host = args.host or args.all
    start_client = args.client or args.all
    
    # Start in the correct order: server first, then host, then client
    if start_server:
        server_process = start_process(server_path, "Product Server")
        time.sleep(2)  # Give server time to start
    
    if start_host:
        host_process = start_process(host_path, "MCP Host")
        time.sleep(2)  # Give host time to start before client connects
    
    if start_client:
        client_process = start_process(client_path, "MCP Client")
    
    # Count how many processes were started
    started_count = sum(1 for p in [server_process, host_process, client_process] if p is not None)
    
    if started_count == 0:
        print("No components were started. Exiting.")
        sys.exit(1)
    
    print(f"\n{started_count} component(s) started. Press Ctrl+C to stop.\n")
    
    # Wait for processes to complete (they should run indefinitely)
    while True:
        # Check if any process has terminated unexpectedly
        for process, name in [(server_process, "Product Server"), 
                             (host_process, "MCP Host"), 
                             (client_process, "MCP Client")]:
            if process and process.poll() is not None:
                print(f"{name} has terminated with exit code {process.returncode}")
                # Optionally restart the process here
                
        time.sleep(1)
        
except KeyboardInterrupt:
    print("\nReceived keyboard interrupt. Shutting down...")
    
finally:
    # Clean up all processes
    for process in processes:
        if process and process.poll() is None:
            process.terminate()
    print("All processes terminated.")
