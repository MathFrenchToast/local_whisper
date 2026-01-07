# helper script to start the server and the systray client

$containerName = "local-whisper-server"

# Check if container is already running
$running = docker ps --filter "name=$containerName" --filter "status=running" -q

if ($running) {
    Write-Host "Container '$containerName' is already running"
} else {
    Write-Host "Starting server as container...(first start may be slow)"
    
    # Remove existing container if it exists (stopped state)
    docker rm $containerName 2>$null
    
    docker run -d --gpus all -p 8000:8000 `
      -e DEVICE=cuda `
      -e MODEL_SIZE=medium `
      -e LANGUAGE=fr `
      --name $containerName `
      local-whisper-server
    
    Write-Host "Container started"
}

Write-Host "starting systray client"
# wait for server startup
Start-Sleep -Seconds 10
.\local_whisper.exe
