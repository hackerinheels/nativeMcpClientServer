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

# Function to check if a process is running
is_running() {
    local port=$1
    nc -z localhost $port >/dev/null 2>&1
    return $?
}

# Function to start a component and wait for it to be ready
start_component() {
    local name=$1
    local command=$2
    local port=$3
    local timeout=$4
    local logfile="log/$name.log"
    
    echo "Starting $name..."
    $command > "$logfile" 2>&1 &
    local pid=$!
    echo "$name started with PID $pid"
    
    # Wait for the service to be available
    local count=0
    while ! is_running $port && [ $count -lt $timeout ]; do
        echo "Waiting for $name to be ready... ($count/$timeout)"
        sleep 1
        count=$((count + 1))
        
        # Check if process is still running
        if ! kill -0 $pid 2>/dev/null; then
            echo "Error: $name process died. Check $logfile for details."
            return 1
        fi
    done
    
    if [ $count -ge $timeout ]; then
        echo "Timeout waiting for $name to start. Check $logfile for details."
        return 1
    fi
    
    echo "$name is ready!"
    return 0
}

# Start the product server
echo "=== Starting Product Server ==="
start_component "product-server" "python product-server/server_product.py" 5001 30 || exit 1

# Start the analytics server
echo "=== Starting Analytics Server ==="
start_component "analytics-server" "python analytics-server/server_analytics.py" 5002 30 || exit 1

# Start the eagle feed server
echo "=== Starting Eagle Feed Server ==="
start_component "eagle-feed-server" "python eagle-feed-server/server_eagle_feed.py" 5003 30 || exit 1

# Start the MCP host
echo "=== Starting MCP Host ==="
start_component "mcp-host" "python host/mcp-host.py" 8765 30 || exit 1

# Cleanup function
cleanup() {
    echo "Shutting down all components..."
    pkill -f "python product-server/server_product.py"
    pkill -f "python analytics-server/server_analytics.py"
    pkill -f "python eagle-feed-server/server_eagle_feed.py"
    pkill -f "python host/mcp-host.py"
    exit 0
}

# Set up trap for cleanup on exit
trap cleanup EXIT

# Keep running until Ctrl+C
echo "All servers are running. Press Ctrl+C to stop."
while true; do
    sleep 1
done 