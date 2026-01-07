# helper script to start the server and the systray client

#!/bin/bash

echo "(re)starting server as container"
docker kill local-whisper-server
docker rm  local-whisper-server

docker run -d --gpus all -p 8000:8000 \
  -e DEVICE=cuda \
  -e MODEL_SIZE=medium \
  -e LANGUAGE=fr \
  --name local-whisper-server \
  local-whisper-server
  
echo "starting systray client"
# wait for server startup
sleep 10
chmod +x local_whisper-linux
./local_whisper-linux &
