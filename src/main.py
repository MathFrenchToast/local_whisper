import os
import sys
import glob

def fix_library_paths():
    """
    Manually add the nvidia library paths to LD_LIBRARY_PATH so ctranslate2 can find them.
    This is necessary because pip-installed nvidia packages don't automatically update 
    the system linker path.
    """
    try:
        import nvidia.cublas.lib
        import nvidia.cudnn.lib
        
        libs_paths = [
            list(nvidia.cublas.lib.__path__)[0],
            list(nvidia.cudnn.lib.__path__)[0],
        ]
        
        current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        new_paths = [p for p in libs_paths if p not in current_ld_path]
        
        if new_paths:
            print(f"Adding NVIDIA library paths to LD_LIBRARY_PATH: {new_paths}")
            os.environ["LD_LIBRARY_PATH"] = f"{':'.join(new_paths)}:{current_ld_path}"
            
    except ImportError:
        print("NVIDIA libraries not found in python environment. proceeding without adding paths.")

fix_library_paths()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from src.asr_service import ASRService
from src.audio_processor import AudioProcessor
import json
import os
import torch

# --- Configuration Loading ---
def get_config():
    # 1. Load defaults from config file
    try:
        with open("config.json") as f:
            config_from_file = json.load(f)
    except FileNotFoundError:
        config_from_file = {}

    # 2. Get config from environment variables
    model_size_env = os.environ.get('MODEL_SIZE')
    language_env = os.environ.get('LANGUAGE')
    vad_filter_env = os.environ.get('VAD_FILTER', 'true')
    device_env = os.environ.get('DEVICE')
    compute_type_gpu_env = os.environ.get('COMPUTE_TYPE_GPU')
    compute_type_cpu_env = os.environ.get('COMPUTE_TYPE_CPU')

    # 3. Determine final config (Env > File > Hardcoded default)
    config = {
        "model_size": model_size_env or config_from_file.get("model_size", "small"),
        "language": language_env or config_from_file.get("language", "en"),
        "vad_filter": vad_filter_env.lower() == 'true',
        "device": device_env or config_from_file.get("device", "auto"),
        "compute_type_gpu": compute_type_gpu_env or config_from_file.get("compute_type_gpu", "float16"),
        "compute_type_cpu": compute_type_cpu_env or config_from_file.get("compute_type_cpu", "int8"),
    }

    # 4. Auto-detect device if set to "auto"
    if config["device"] == "auto":
        config["device"] = "cuda" if torch.cuda.is_available() else "cpu"
    
    # 5. Select compute type based on final device
    config["compute_type"] = config["compute_type_gpu"] if config["device"] == "cuda" else config["compute_type_cpu"]
    
    return config

config = get_config()

# --- FastAPI App ---
app = FastAPI()

# Initialize ASR Service with configured model size
print(f"Initializing ASR service with model: {config['model_size']}")
print(f"Using device: {config['device']} ({config['compute_type']})")
print(f"Internal VAD filter enabled: {config['vad_filter']}")
asr_service = ASRService(
    model_size=config['model_size'], 
    device=config['device'], 
    compute_type=config['compute_type']
)

@app.websocket("/ws/asr")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected.")

    # Initialize the Audio Stream Processor
    # This handles buffering, silence detection (VAD), and segmentation
    processor = AudioProcessor(
        sample_rate=16000,
        silence_threshold=200,
        silence_pause_duration=1.0,
        max_accumulate_duration=10
    )

    try:
        while True:
            # 1. Receive raw audio bytes
            data = await websocket.receive_bytes()
            
            # 2. Process audio chunk (VAD logic)
            # Returns a numpy float32 array if a segment is ready, else None
            audio_segment = processor.process(data)

            # 3. If we have a complete segment, run the pipeline
            if audio_segment is not None:
                # --- Pipeline Step A: ASR ---
                # Transcribe using the configured language
                # We disable internal VAD of Whisper because we handled it upstream
                transcription = asr_service.transcribe_audio(
                    audio_segment, 
                    language=config['language'],
                    vad_filter=False 
                )
                
                # --- Pipeline Step B: LLM / Post-processing (Future) ---
                # if config.use_llm:
                #     transcription = llm_service.process(transcription)

                if transcription:
                    print(f"Transcription ({config['language']}): {transcription}")
                    await websocket.send_text(transcription)
            
    except WebSocketDisconnect:
        print("WebSocket disconnected.")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        print("WebSocket connection closed.")