# helper script to start the server and the systray client

#!/bin/bash

CONTAINER_NAME="local-whisper-server"

# Check if container is already running
if [ "$(docker ps -q -f name=$CONTAINER_NAME -f status=running)" ]; then
    echo "Container '$CONTAINER_NAME' is already running"
else
    echo "Starting server as container..."
    
    # Remove existing container if it exists (stopped state)
    docker rm $CONTAINER_NAME 2>/dev/null
    
    docker run -d --gpus all -p 8000:8000 \
      -e DEVICE=cuda \
      -e MODEL_SIZE=medium \
      -e LANGUAGE=fr \
      --name $CONTAINER_NAME \
      local-whisper-server
    
    echo "Container started"
fi
  
echo "starting systray client"
# wait for server startup
sleep 10
chmod +x local_whisper-linux
./local_whisper-linux &
