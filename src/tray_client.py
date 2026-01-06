import asyncio
import os
import platform
import queue
import subprocess
import sys
import threading

import pyperclip
import pystray
import websockets
from PIL import Image, ImageDraw
from pynput import keyboard

sys.path.append(os.getcwd())

from src.audio_recorder import AudioRecorder

# --- Configuration ---
ICON_SIZE = 64
COLOR_ACTIVE = (40, 167, 69, 255)  # Green
COLOR_INACTIVE = (220, 53, 69, 255)  # Red
COLOR_ERROR = (255, 193, 7, 255)  # Orange/Yellow for errors


class TrayClient:
    def __init__(self, websocket_uri):
        self.websocket_uri = websocket_uri
        self.stop_event = threading.Event()
        self.is_typing_enabled = False
        self.icon = None
        self.kb_controller = keyboard.Controller()

        # Queue for thread-safe communication
        self.status_queue = queue.Queue()

    def create_image(self, color):
        """Generate a simple circle icon with the given color."""
        image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, ICON_SIZE - 8, ICON_SIZE - 8), fill=color)
        return image

    def update_icon_state(self, state):
        """Update the icon based on state ('active', 'inactive', 'error')."""
        if state == "active":
            self.icon.icon = self.create_image(COLOR_ACTIVE)
            self.icon.title = "TTS Client: Listening"
        elif state == "inactive":
            self.icon.icon = self.create_image(COLOR_INACTIVE)
            self.icon.title = "TTS Client: Paused (F8)"
        elif state == "error":
            self.icon.icon = self.create_image(COLOR_ERROR)
            self.icon.title = "TTS Client: Connection Error"

    def on_toggle_click(self, icon, item):
        self.toggle_typing()

    def on_exit_click(self, icon, item):
        self.stop_event.set()
        self.icon.stop()

    def toggle_typing(self):
        self.is_typing_enabled = not self.is_typing_enabled
        new_state = "active" if self.is_typing_enabled else "inactive"
        self.update_icon_state(new_state)
        print(f"State toggled: {new_state}")

    def on_key_press(self, key):
        try:
            if key == keyboard.Key.f8:
                self.toggle_typing()
        except AttributeError:
            pass

    async def async_audio_loop(self):
        """Main async loop for audio and websocket."""
        print(f"Connecting to {self.websocket_uri}...")

        while not self.stop_event.is_set():
            try:
                async with websockets.connect(self.websocket_uri) as websocket:
                    print("Connected to server.")
                    self.status_queue.put("active" if self.is_typing_enabled else "inactive")

                    recorder = AudioRecorder(rate=16000, chunk_size=1024, channels=1)
                    recorder.start_recording()

                    try:
                        # Task: Send Audio
                        async def send_audio():
                            audio_iter = recorder.get_audio_chunk()
                            for chunk in audio_iter:
                                if self.stop_event.is_set():
                                    break

                                # Privacy & Optimization: Only send audio if active
                                if self.is_typing_enabled:
                                    await websocket.send(chunk.tobytes())

                                await asyncio.sleep(0.001)

                        # Task: Receive Text
                        async def receive_text():
                            while not self.stop_event.is_set():
                                try:
                                    message = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                                    text = message.strip()
                                    if text:
                                        print(f"Server: {text}")
                                        if self.is_typing_enabled:
                                            # --- Wayland Bypass: Clipboard Injection ---
                                            try:
                                                pyperclip.copy(text + " ")
                                                await asyncio.sleep(0.05)  # Wait for clipboard

                                                # Linux Specific Hack: xdotool
                                                if platform.system() == "Linux":
                                                    try:
                                                        subprocess.run(
                                                            ["xdotool", "key", "ctrl+v"],
                                                            check=False,
                                                        )
                                                    except FileNotFoundError:
                                                        print(
                                                            "Error: 'xdotool' not found. Please install: sudo apt install xdotool"
                                                        )
                                                        # Fallback to pynput
                                                        with self.kb_controller.pressed(
                                                            keyboard.Key.ctrl
                                                        ):
                                                            self.kb_controller.press("v")
                                                            self.kb_controller.release("v")
                                                else:
                                                    # Windows/Mac standard pynput
                                                    with self.kb_controller.pressed(
                                                        keyboard.Key.ctrl
                                                    ):
                                                        self.kb_controller.press("v")
                                                        self.kb_controller.release("v")

                                                # Debounce
                                                await asyncio.sleep(0.1)
                                            except Exception as e:
                                                print(f"Clipboard Error: {e}")

                                except asyncio.TimeoutError:
                                    continue

                        # Create Tasks
                        task_send = asyncio.create_task(send_audio())
                        task_recv = asyncio.create_task(receive_text())

                        # Wait loop
                        while not self.stop_event.is_set():
                            if task_send.done() or task_recv.done():
                                break
                            await asyncio.sleep(0.1)

                        task_send.cancel()
                        task_recv.cancel()

                    except Exception as e:
                        print(f"Session error: {e}")
                    finally:
                        recorder.stop_recording()

            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"Connection failed: {e}. Retrying in 2s...")
                    self.status_queue.put("error")
                    await asyncio.sleep(2)

    def run_async_thread(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.async_audio_loop())
        loop.close()

    def run(self):
        kb_listener = keyboard.Listener(on_press=self.on_key_press)
        kb_listener.start()

        t = threading.Thread(target=self.run_async_thread, daemon=True)
        t.start()

        self.icon = pystray.Icon(
            "TTS Client",
            self.create_image(COLOR_INACTIVE),
            "TTS Client: Paused",
            menu=pystray.Menu(
                pystray.MenuItem("Toggle (F8)", self.on_toggle_click),
                pystray.MenuItem("Exit", self.on_exit_click),
            ),
        )

        self.icon.run()

        kb_listener.stop()
        print("Tray client exited.")


if __name__ == "__main__":
    uri = "ws://127.0.0.1:8000/ws/asr"
    client = TrayClient(uri)
    client.run()
