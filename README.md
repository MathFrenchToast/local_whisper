# Real-Time Local Speech-to-Text Server

This project provides a real-time, local speech-to-text (Local Whisper) service using a client-server architecture. It captures audio from a microphone, streams it to a server, and returns transcriptions in near real-time.
Many clients available, among them, one for keyboard emulation that work everywhere: Browser, terminal, applications.

## 🚀 Quick Start

Get up and running in minutes. You can either download pre-built binaries or run from source.

### 1. Start the Server (Docker)
This runs the heavy ASR engine in a container (CPU mode by default).
```bash
# Build the image
docker build -t local-whisper-server .

# Run container in background (Change 'cpu' to 'cuda' and add '--gpus all' for NVIDIA GPU)
docker run -d -p 8000:8000 --env DEVICE=cpu local-whisper-server
```

### 2. Start the Client
Choose the method that fits your needs:

#### A. Download Pre-built Binary (Recommended for Users)
Go to the **[GitHub Releases](https://github.com/your-username/your-repo/releases)** page and download the executable for your OS:
- **Windows**: `local_whisper.exe` (Standalone, no installation needed)
- **Linux**: `local_whisper-linux` (Standalone binary)

#### B. Run from Source (For Developers)
```bash
# Setup python environment
python3 -m venv venv
source venv/bin/activate

# Install client dependencies
pip install -r requirements-client.txt

# Launch the Tray App
python -m src.tray_client
```

### 3. How to Use
1.  **Focus** any text field where you want to type (Notepad, Browser, IDE).
2.  Press **F8** on your keyboard.
3.  The icon will turn **Green** 🟢. Start speaking.
4.  Your speech will be transcribed and typed automatically.
5.  Press **F8** again to stop (Icon turns **Red** 🔴).

---

## 🛠 CI/CD & Distribution

This project uses **GitHub Actions** to automatically build and package the client for multiple platforms. Whenever a new Release is created, the pipeline:
1.  Tests the code.
2.  Packages the Python client using **PyInstaller**.
3.  Uploads standalone executables to the Release page.

This ensures that users can enjoy the tool without having to install Python or manage virtual environments.

---

## Architecture

The application is built on a client-server model, allowing for flexible integration with various types of clients in the future.

*   **Server (`src/main.py`):** A WebSocket server built with **FastAPI**. It accepts audio streams from clients, processes the audio, and sends back transcribed text.
*   **Client (`src/client.py`):** A command-line interface (CLI) client that captures audio from the microphone using **PyAudio** and streams it to the server over a WebSocket connection.
*   **ASR Service (`src/asr_service.py`):** A core service class that wraps the **`faster-whisper`** model. It is responsible for loading the transcription model and performing the actual speech-to-text conversion.
*   **Audio Recorder (`src/audio_recorder.py`):** A utility class that handles the details of capturing audio from the system's microphone in real-time.

The server continuously listens for audio chunks from the client. It accumulates a few seconds of audio before sending it to the ASR service for transcription. This segment-based approach provides a good balance between latency and transcription accuracy.

## 🔌 Extensibility & Plugins

The server features a modular processing pipeline. You can easily extend it by adding custom Python scripts to the `plugins/` directory. This allows for features like:
- **Translation**: Translate transcriptions in real-time.
- **Custom Logging**: Save transcriptions to specific files or databases.
- **Jargon Replacement**: Automatically fix industry-specific terms.

For detailed instructions on how to create and install plugins, see [doc/plugins.md](doc/plugins.md).

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
    This project requires `portaudio` for microphone access, and `xclip`/`xdotool` for keyboard emulation on Linux. On Debian-based systems (like Ubuntu), you can install them with:
    ```bash
    sudo apt-get update && sudo apt-get install -y portaudio19-dev xclip xdotool
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
docker build -t local-whisper-server .
```

### 2. Run the Container

**With GPU support (Recommended):**
You need the [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html) installed on your host.
```bash
docker run --gpus all -p 8000:8000 --env DEVICE=cuda local-whisper-server
```

Note: Nvidia Container Toolkit is required: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
then enable gpu on docker:
```bash
sudo nvidia-ctk runtime configure --runtime=docker

```

**CPU Only:**
```bash
docker run -p 8000:8000 --env DEVICE=cpu local-whisper-server
```

**Custom Configuration:**
You can pass any environment variable supported by the server:
```bash
docker run --gpus all -p 8000:8000 \
  -e DEVICE=cuda \
  -e MODEL_SIZE=medium \
  -e LANGUAGE=fr \
  local-whisper-server
```

## Usage

You need to run the server first, and then run the client in a separate terminal.

### 1. Running the Server

use the startup script in a complete python env.
The server can be configured via a `config.json` file and overridden by environment variables. It will auto-detect a CUDA-enabled GPU if `DEVICE` is set to `"auto"`.

or use the server in docker (see above).

**Use the startup script**
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

### 2. Running the Python Client

Open a **new terminal** in the same project directory.

**To start the client and stream your microphone input:**
```bash
# Install the client requirements
venv/bin/pip install -r requirements-client.txt
# Run the client 
venv/bin/python -m src.client
```

The client will connect to the server. Start speaking, and you will see the transcribed text appear in your terminal. Press `Ctrl+C` to stop the client.

### 3. Running the Keyboard Client (Simulated Typing)

This client listens to your voice and directly types the transcription into whichever application is currently focused on your desktop (like a text editor, IDE, or chat window).

**To start the keyboard client:**
```bash
# Make sure you are in the virtual environment
source venv/bin/activate
# Run the keyboard client
python -m src.keyboard_client
```

**Usage Controls:**
*   **F8**: Toggle typing ON/OFF. The client starts in **DISABLED** mode by default to prevent accidental typing. Press F8 once you have focused the desired text field.
*   **Ctrl+C**: Stop the client (in the terminal).

### 4. Running the System Tray Client (Cross-Platform)

This is the most advanced client, designed to look and feel like a native application on Windows, macOS, and Linux. It minimizes to the system tray (notification area).

**Features:**
*   **System Tray Icon:** Shows status via color (🔴 Paused, 🟢 Active, 🟡 Error).
*   **Background Operation:** Runs silently in the background.
*   **Global Hotkey:** Press **F8** anywhere to toggle transcription.
*   **Two Insertion Modes:** (Toggle via right-click menu)
    *   **Type Mode (Default):** Simulates keyboard typing. Best for Terminals and general use.
    *   **Paste Mode:** Uses the clipboard to inject text instantly. Useful for specific GUI apps where typing is slow or blocked.
*   **Menu:** Right-click the icon to Exit, or change the insertion mode.
*   **Emergency Exit:** Press **Shift + F8** to quit the application instantly.

**To start the tray client:**
```bash
# Make sure you are in the virtual environment
source venv/bin/activate
# Run the tray client
python -m src.tray_client
```

*Note for Linux Users (Gnome/Wayland):* 
- If you don't see the icon, ensure you have the "AppIndicator and KStatusNotifierItem Support" extension installed.
- For keyboard emulation to work in native Wayland applications (like GNOME Text Editor), ensure you have installed `xclip` and `xdotool` (`sudo apt install xclip xdotool`). The client uses a clipboard-injection technique to bypass Wayland security restrictions.

### 5. Browser Extensions (Firefox & Chrome)

Browser extensions allow you to use the ASR server directly in any web form (Gmail, Google Docs, etc.).

#### Firefox Extension
1.  Open Firefox and go to `about:debugging#/runtime/this-firefox`.
2.  Click **"Load Temporary Add-on..."**.
3.  Select the `manifest.json` file inside the `firefox_extension/` directory.
4.  **Usage**: Press **Alt+Shift+W** on any page to start/stop transcription.

#### Chrome Extension
1.  Open Chrome and go to `chrome://extensions/`.
2.  Enable **"Developer mode"** (top right).
3.  Click **"Load unpacked"**.
4.  Select the `chrome_extension/` directory.
5.  **Usage**: Press **Alt+Shift+W** on any page to start/stop transcription.

### 4. Running the Web Test Page

A simple HTML test page is provided to verify the transcription in a controlled environment.

**To use the test page:**
1.  Open `test_page.html` in your browser.
2.  Click inside the text area.
3.  Use the **Alt+Shift+W** shortcut (after installing an extension) to start dictating.

**Built-in Shortcuts for the Test Page:**
*   **Alt + C**: Copy the current content of the textarea to your clipboard.
*   **Alt + R** or **Alt + D**: Clear the entire textarea.
*   You can also click the interactive labels at the bottom of the page to perform these actions.

## Testing

The project includes unit tests to ensure the reliability of the audio processing and ASR services.

**To run the tests:**
```bash
# Make sure your virtual environment is activated
source venv/bin/activate

# Run all tests
export PYTHONPATH=$PYTHONPATH:.
python3 -m unittest discover tests
```

This will run all tests located in the `tests/` directory, verifying the `AudioProcessor` logic and the `ASRService` wrapper.
