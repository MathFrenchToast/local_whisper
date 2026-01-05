# Real-Time Local Speech-to-Text Server

This project provides a real-time, local speech-to-text (ASR) service using a client-server architecture. It captures audio from a microphone, streams it to a server, and returns transcriptions in near real-time.

## Architecture

The application is built on a client-server model, allowing for flexible integration with various types of clients in the future.

*   **Server (`src/main.py`):** A WebSocket server built with **FastAPI**. It accepts audio streams from clients, processes the audio, and sends back transcribed text.
*   **Client (`src/client.py`):** A command-line interface (CLI) client that captures audio from the microphone using **PyAudio** and streams it to the server over a WebSocket connection.
*   **ASR Service (`src/asr_service.py`):** A core service class that wraps the **`faster-whisper`** model. It is responsible for loading the transcription model and performing the actual speech-to-text conversion.
*   **Audio Recorder (`src/audio_recorder.py`):** A utility class that handles the details of capturing audio from the system's microphone in real-time.

The server continuously listens for audio chunks from the client. It accumulates a few seconds of audio before sending it to the ASR service for transcription. This segment-based approach provides a good balance between latency and transcription accuracy.

## Architecture Decision Record (ADR)

1.  **ASR Engine - `faster-whisper`**: We chose `faster-whisper` as the core ASR engine. It is an optimized implementation of OpenAI's Whisper model, offering significant speed improvements and reduced memory usage, which are critical for achieving real-time performance on local hardware.

2.  **Server Framework - `FastAPI`**: `FastAPI` was selected for the server implementation due to its high performance, asynchronous capabilities, and native support for WebSockets. This makes it an ideal choice for handling real-time, bidirectional communication with clients.

3.  **Server Configuration - Environment Variables**: The server's configuration (e.g., `MODEL_SIZE`, `LANGUAGE`) is managed through environment variables. This approach was chosen over command-line arguments because process managers like `uvicorn` do not pass unknown arguments to the application. Environment variables are a standard, robust, and container-friendly method for configuring applications.

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-directory>
    ```

2.  **Install System Dependencies:**
    This project requires `portaudio` for microphone access. On Debian-based systems (like Ubuntu), you can install it with:
    ```bash
    sudo apt-get update && sudo apt-get install -y portaudio19-dev
    ```

3.  **Create and Activate Virtual Environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

4.  **Install Python Packages:**
    ```bash
    pip install -r requirements.txt
    ```

## Docker

You can also run the server using Docker. This is useful for deployment or if you want to avoid installing system dependencies manually.

### 1. Build the Image
```bash
docker build -t tts-local-server .
```

### 2. Run the Container

**With GPU support (Recommended):**
You need the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed on your host.
```bash
docker run --gpus all -p 8000:8000 --env DEVICE=cuda tts-local-server
```

Note: Nvidia Container Toolkit is required: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
then enable gpu on docker:
```bash
sudo nvidia-ctk runtime configure --runtime=docker

```

**CPU Only:**
```bash
docker run -p 8000:8000 --env DEVICE=cpu tts-local-server
```

**Custom Configuration:**
You can pass any environment variable supported by the server:
```bash
docker run --gpus all -p 8000:8000 \
  -e DEVICE=cuda \
  -e MODEL_SIZE=medium \
  -e LANGUAGE=fr \
  tts-local-server
```

## Usage

You need to run the server first, and then run the client in a separate terminal.

### 1. Running the Server

The server can be configured via a `config.json` file and overridden by environment variables. It will auto-detect a CUDA-enabled GPU if `DEVICE` is set to `"auto"`.

**Recommended: Use the startup script**
This script automatically sets up the environment variables (fixing common library path issues with CUDA) and runs the server.
```bash
./start_server.sh
```

**To specify settings, use environment variables:**
You can pass environment variables to the script:

*   `DEVICE`: Set the device to run on (`auto`, `cuda`, `cpu`).
*   `MODEL_SIZE`: The Whisper model size (`tiny`, `base`, `small`, `medium`, `large-v3`).
*   `LANGUAGE`: The transcription language (`en`, `fr`, `es`, etc.).
*   `VAD_FILTER`: Enable/disable the internal VAD filter (`true` or `false`).
*   `COMPUTE_TYPE_GPU`: The compute type for GPU (`float16`, `int8_float16`).
*   `COMPUTE_TYPE_CPU`: The compute type for CPU (`int8`, `float32`).

**Example (running on CPU with the French `medium` model):**
```bash
DEVICE="cpu" MODEL_SIZE="medium" LANGUAGE="fr" ./start_server.sh
```

**Example (running on CUDA with `float16` precision):**
```bash
DEVICE="cuda" COMPUTE_TYPE_GPU="float16" ./start_server.sh
```

**Alternative: Running manually with `uvicorn`**
If you prefer to run `uvicorn` directly, ensure your `LD_LIBRARY_PATH` includes the NVIDIA libraries from your virtual environment:
```bash
export LD_LIBRARY_PATH=$(find venv/lib/python*/site-packages/nvidia -name lib -type d | paste -sd ":" -):$LD_LIBRARY_PATH
venv/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
```

The server will print the device it's using on startup and then wait for client connections.

### 2. Running the Client

So far two clients exist:
- python client
- html/js client as a firefox extension

avascript client

Open a **new terminal** in the same project directory.

**To start the client and stream your microphone input:**
```bash
#install the client requirements
venv/bin/pip install -r client_requirements.txt
#run the client 
venv/bin/python -m src.client
```

The client will connect to the server. Start speaking, and you will see the transcribed text appear in your terminal. Press `Ctrl+C` to stop the client.

### 3. Running the Web Test Page

A simple HTML test page is provided to verify the transcription and the browser extension in a controlled environment.

first, install locally the FF extension:
go to: [ff settings](about:debugging#/runtime/this-firefox)  
then add a unpacked extension by selecting the file: ./firefox_extension/manifest.json.

After this, you should be able to activate transcription on any form, e.g Gmail new email.

**To use the test page:**
1.  Open the file `test_page.html` in your browser (e.g., `firefox test_page.html`).
2.  Click inside the text area.
3.  Use the **Alt+Shift+W** shortcut (or the browser extension popup) to start dictating.

**Built-in Shortcuts for the Test Page:**
*   **Alt + C**: Copy the current content of the textarea to your clipboard.
*   **Alt + R** or **Alt + D**: Clear the entire textarea.
*   You can also click the interactive labels at the bottom of the page to perform these actions.
