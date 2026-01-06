import asyncio
import websockets
import sys
from src.audio_recorder import AudioRecorder
from pynput import keyboard

# Global state
is_typing_enabled = False

def on_press(key):
    global is_typing_enabled
    try:
        # Toggle typing on F8
        if key == keyboard.Key.f8:
            is_typing_enabled = not is_typing_enabled
            status = "ENABLED" if is_typing_enabled else "DISABLED"
            print(f"\n[Keyboard Control] Typing is now {status}")
    except AttributeError:
        pass

async def send_audio_and_type_transcriptions(uri):
    global is_typing_enabled
    
    # Initialize keyboard controller
    kb_controller = keyboard.Controller( )
    
    # Start keyboard listener for the toggle key
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    print(f"Connecting to {uri}...")
    print("---------------------------------------------------------")
    print("Press F8 to TOGGLE typing (Default: DISABLED).")
    print("Focus the text field where you want the text to appear.")
    print("Press Ctrl+C in this terminal to exit.")
    print("---------------------------------------------------------")

    async with websockets.connect(uri) as websocket:
        print(f"Connected!")

        recorder = AudioRecorder(
            rate=16000,
            chunk_size=1024,
            channels=1
        )
        recorder.start_recording()

        try:
            # Task to send audio
            async def send_audio():
                while True:
                    for audio_chunk_int16 in recorder.get_audio_chunk():
                        await websocket.send(audio_chunk_int16.tobytes())
                        await asyncio.sleep(0.01)

            # Task to receive transcriptions and type them
            async def receive_and_type():
                while True:
                    transcription = await websocket.recv()
                    text = transcription.strip()
                    if text:
                        print(f"\n[Server]: {text}")
                        if is_typing_enabled:
                            print(f"[Typing]: {text}...")
                            # Type the text
                            kb_controller.type(text)
                            # Add a space after the sentence
                            kb_controller.type(" ")
                        else:
                            print("[Skipped]: Typing is disabled (Press F8 to enable)")

            # Run both tasks concurrently
            await asyncio.gather(send_audio(), receive_and_type())

        except websockets.exceptions.ConnectionClosedOK:
            print("\nWebSocket connection closed normally.")
        except asyncio.CancelledError:
            print("\nClient stopped.")
        except Exception as e:
            print(f"\nClient error: {e}")
        finally:
            recorder.stop_recording()
            listener.stop()

if __name__ == "__main__":
    websocket_uri = "ws://127.0.0.1:8000/ws/asr"
    try:
        asyncio.run(send_audio_and_type_transcriptions(websocket_uri))
    except KeyboardInterrupt:
        print("\nExiting keyboard client.")
