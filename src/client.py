import asyncio
import threading

import pyperclip
import websockets
from pynput import keyboard

from src.audio_recorder import AudioRecorder

# Shared state
transcription_history = []
sequence_start_index = 0
history_lock = threading.Lock()


def on_press(key):
    global sequence_start_index
    try:
        if hasattr(key, "char"):
            if key.char == "c":
                with history_lock:
                    current_sequence = transcription_history[sequence_start_index:]
                    text_to_copy = " ".join(current_sequence)
                if text_to_copy:
                    try:
                        pyperclip.copy(text_to_copy)
                        print(f"\n[Copied to clipboard]: {text_to_copy}")
                    except pyperclip.PyperclipException:
                        print(
                            "\n[Error] Clipboard copy failed. Please install 'xclip' or 'xsel' (sudo apt install xclip)."
                        )
                    except Exception as e:
                        print(f"\n[Error] Clipboard copy failed: {e}")
                else:
                    print("\n[Clipboard] Nothing to copy.")

            elif key.char == "r":
                with history_lock:
                    sequence_start_index = len(transcription_history)
                print("\n[Sequence Reset] Start index updated.")

    except AttributeError:
        pass


async def send_audio_and_receive_transcriptions(uri):
    # Start keyboard listener
    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    async with websockets.connect(uri) as websocket:
        print(f"Connected to WebSocket server at {uri}")
        print("Controls: 'c' to copy current sequence, 'r' to reset sequence start.")

        recorder = AudioRecorder(
            rate=16000,
            chunk_size=1024,  # Must match server's expected chunking if any, or be consistent.
            # For our current server, it accumulates based on seconds, not chunk_size.
            channels=1,
        )
        recorder.start_recording()

        try:
            # Task to send audio
            async def send_audio():
                print("Sending audio... (Press Ctrl+C to stop)")
                for audio_chunk_int16 in recorder.get_audio_chunk():
                    # Send raw bytes of the int16 numpy array
                    await websocket.send(audio_chunk_int16.tobytes())
                    await asyncio.sleep(
                        0.01
                    )  # Small delay to prevent overwhelming the network/CPU

            # Task to receive transcriptions
            async def receive_transcriptions():
                print("Transcription:")
                while True:
                    transcription = await websocket.recv()
                    text = transcription.strip()
                    if text:
                        with history_lock:
                            transcription_history.append(text)
                        print(f" {text}")  # \r to overwrite line

            # Run both tasks concurrently
            await asyncio.gather(send_audio(), receive_transcriptions())

        except websockets.exceptions.ConnectionClosedOK:
            print("\nWebSocket connection closed normally.")
        except asyncio.CancelledError:
            print("\nClient stopped.")
        except Exception as e:
            print(f"\nClient error: {e}")
        finally:
            recorder.stop_recording()
            listener.stop()
            print("Audio recording stopped.")


if __name__ == "__main__":
    websocket_uri = "ws://127.0.0.1:8000/ws/asr"  # Assuming server is running locally
    try:
        asyncio.run(send_audio_and_receive_transcriptions(websocket_uri))
    except KeyboardInterrupt:
        print("\nExiting client.")
