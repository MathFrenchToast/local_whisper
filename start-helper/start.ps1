# helper script to start the server and the systray client

Write-Host "(re)starting server as container"
docker kill local-whisper-server 2>$null
docker rm local-whisper-server 2>$null

docker run -d --gpus all -p 8000:8000 `
  -e DEVICE=cuda `
  -e MODEL_SIZE=medium `
  -e LANGUAGE=fr `
  --name local-whisper-server `
  local-whisper-server

Write-Host "starting systray client"
# wait for server startup
Start-Sleep -Seconds 10
Start-Process -FilePath ".\local_whisper.exe"
