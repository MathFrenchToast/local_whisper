#!/bin/bash

# start script for development

# Get the directory of the script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Activate virtual environment
source "$DIR/venv/bin/activate"

# Add Nvidia libraries from the venv to LD_LIBRARY_PATH
export LD_LIBRARY_PATH=$(find "$DIR/venv/lib" -name "nvidia" -type d -exec find {} -name "lib" -type d \; | paste -sd ":" -):$LD_LIBRARY_PATH

# Run the server
# You can pass environment variables to this script to override defaults
# e.g., DEVICE=cpu ./start_server.sh
exec uvicorn src.main:app --host 0.0.0.0 --port 8000
