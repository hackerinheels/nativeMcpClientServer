#!/bin/bash

# Set the base directory to the project root
BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

# Start the servers in the background
echo "Starting all servers..."
./launch_servers.sh &
SERVER_PID=$!

# Wait for the servers to be ready
echo "Waiting for servers to be ready..."
sleep 5

# Start the GUI client
echo "Starting GUI client..."
cd client
./launch_gui_client.sh

# When the GUI client exits, kill the servers
echo "GUI client exited. Shutting down servers..."
kill $SERVER_PID

echo "All components have been shut down."
exit 0 