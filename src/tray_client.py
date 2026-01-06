import asyncio
import websockets
import sys
import threading
import queue
import time
from PIL import Image, ImageDraw
import pystray
from pynput import keyboard

# Ensure we can import our modules
import os
sys.path.append(os.getcwd())

from src.audio_recorder import AudioRecorder

# --- Configuration ---
ICON_SIZE = 64
COLOR_ACTIVE = (40, 167, 69, 255)   # Green
COLOR_INACTIVE = (220, 53, 69, 255) # Red
COLOR_ERROR = (255, 193, 7, 255)    # Orange/Yellow for errors

class TrayClient:
    def __init__(self, websocket_uri):
        self.websocket_uri = websocket_uri
        self.stop_event = threading.Event()
        self.is_typing_enabled = False
        self.icon = None
        self.kb_controller = keyboard.Controller()
        
        # Queue for thread-safe communication
        # We will use this to ask the main thread (Icon) to update its look
        self.status_queue = queue.Queue()

    def create_image(self, color):
        """Generate a simple circle icon with the given color."""
        image = Image.new('RGBA', (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        # Draw circle
        draw.ellipse((8, 8, ICON_SIZE-8, ICON_SIZE-8), fill=color)
        return image

    def update_icon_state(self, state):
        """Update the icon based on state ('active', 'inactive', 'error')."""
        if state == 'active':
            self.icon.icon = self.create_image(COLOR_ACTIVE)
            self.icon.title = "TTS Client: Listening"
        elif state == 'inactive':
            self.icon.icon = self.create_image(COLOR_INACTIVE)
            self.icon.title = "TTS Client: Paused (F8)"
        elif state == 'error':
            self.icon.icon = self.create_image(COLOR_ERROR)
            self.icon.title = "TTS Client: Connection Error"

    def on_toggle_click(self, icon, item):
        """Handler for the menu item click."""
        self.toggle_typing()

    def on_exit_click(self, icon, item):
        """Handler for exit."""
        self.stop_event.set()
        self.icon.stop()

    def toggle_typing(self):
        """Toggle the internal state and request icon update."""
        self.is_typing_enabled = not self.is_typing_enabled
        new_state = 'active' if self.is_typing_enabled else 'inactive'
        self.update_icon_state(new_state)
        print(f"State toggled: {new_state}")

    def on_key_press(self, key):
        """Global key listener handler."""
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
                    # If we reconnected, restore visual state
                    self.status_queue.put('active' if self.is_typing_enabled else 'inactive')

                    recorder = AudioRecorder(rate=16000, chunk_size=1024, channels=1)
                    recorder.start_recording()

                    try:
                        # Task: Send Audio
                        async def send_audio():
                            audio_iter = recorder.get_audio_chunk()
                            for chunk in audio_iter:
                                if self.stop_event.is_set():
                                    break
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
                                            self.kb_controller.type(text + " ")
                                except asyncio.TimeoutError:
                                    continue
                        
                        # Run tasks
                        task_send = asyncio.create_task(send_audio())
                        task_recv = asyncio.create_task(receive_text())

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
                    self.status_queue.put('error')
                    await asyncio.sleep(2)

    def run_async_thread(self):
        """Wrapper to run asyncio in a separate thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.async_audio_loop())
        loop.close()

    def run(self):
        """Entry point."""
        # 1. Start Keyboard Listener
        # We need a non-blocking listener
        kb_listener = keyboard.Listener(on_press=self.on_key_press)
        kb_listener.start()

        # 2. Start Asyncio Loop in a Thread
        t = threading.Thread(target=self.run_async_thread, daemon=True)
        t.start()

        # 3. Create and Run System Tray Icon (Main Thread)
        # This blocks until icon.stop() is called
        self.icon = pystray.Icon(
            "TTS Client",
            self.create_image(COLOR_INACTIVE),
            "TTS Client: Paused",
            menu=pystray.Menu(
                pystray.MenuItem("Toggle (F8)", self.on_toggle_click),
                pystray.MenuItem("Exit", self.on_exit_click)
            )
        )
        
        # We need a way to update the icon from the background thread/logic
        # Pystray doesn't have a native event loop integration for updates from threads
        # usually, but we can't easily 'push' updates to it while it runs its run() loop.
        # HOWEVER, pystray.Icon.run(setup) allows a setup function.
        # But we need to react to events.
        
        # Solution: We won't use icon.run() which blocks.
        # We will use the detached mode if backend supports it, or use a loop.
        # Linux (AppIndicator) usually requires the main thread.
        # Let's try to simple run() and use icon.update_menu / icon.icon = ... directly?
        # Pystray allows updating properties from other threads usually on many backends.
        # Let's try standard run().
        
        self.icon.run() 
        
        # Cleanup
        kb_listener.stop()
        print("Tray client exited.")

if __name__ == "__main__":
    uri = "ws://127.0.0.1:8000/ws/asr"
    client = TrayClient(uri)
    client.run()
