import asyncio
import os
import platform
import queue
import signal
import subprocess
import sys
import threading
import time

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
AUTO_OFF_TIMEOUT = 60  # Seconds of silence before auto-disabling


class TrayClient:
    def __init__(self, websocket_uri):
        self.websocket_uri = websocket_uri
        self.stop_event = threading.Event()
        self.is_typing_enabled = False
        self.paste_mode = False  # False = Type mode, True = Paste (Clipboard) mode
        self.icon = None
        self.kb_controller = keyboard.Controller()
        self.currently_pressed = set()
        self.last_activity_time = time.time()

        # Queue for thread-safe communication
        self.status_queue = queue.Queue()

        # Pre-generate icons
        self.icons = {
            "active": self.create_image(COLOR_ACTIVE),
            "inactive": self.create_image(COLOR_INACTIVE),
            "error": self.create_image(COLOR_ERROR),
        }

        # Handle system shutdown signals (SIGTERM)
        try:
            signal.signal(signal.SIGTERM, lambda s, f: self.on_exit_click())
        except Exception:
            pass

    def sleep_watchdog(self):
        """Detect system suspension by monitoring time jumps + Auto-Stop."""
        last_time = time.time()
        while not self.stop_event.is_set():
            time.sleep(1)
            current_time = time.time()

            # 1. Detect Sleep (Time jump)
            if current_time - last_time > 10:
                print("\n[System] Sleep detected. Quitting proactively...")
                self.on_exit_click()
                time.sleep(0.5)
                os._exit(0)

            # 2. Handle Auto-Stop due to inactivity
            if self.is_typing_enabled:
                if current_time - self.last_activity_time > AUTO_OFF_TIMEOUT:
                    print(f"\n[Auto-Stop] Inactivity for {AUTO_OFF_TIMEOUT}s. Disabling.")
                    self.toggle_typing()

            last_time = current_time

    def create_image(self, color):
        """Generate a professional looking microphone icon with state color."""
        image = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        border_color = (0, 0, 0, 50)
        draw.ellipse(
            (2, 2, ICON_SIZE - 2, ICON_SIZE - 2), fill=color, outline=border_color, width=2
        )
        mic_color = (255, 255, 255, 230)
        draw.rounded_rectangle((24, 14, 40, 38), radius=8, fill=mic_color)
        draw.arc((18, 26, 46, 44), start=0, end=180, fill=mic_color, width=3)
        draw.line((32, 44, 32, 52), fill=mic_color, width=3)
        draw.line((24, 52, 40, 52), fill=mic_color, width=3)
        return image

    def update_icon_state(self, state):
        """Update the icon based on state."""
        if self.icon and state in self.icons:
            self.icon.icon = self.icons[state]
            if state == "active":
                self.icon.title = "Local Whisper: Listening"
            elif state == "inactive":
                self.icon.title = "Local Whisper: Paused (F8)"
            elif state == "error":
                self.icon.title = "Local Whisper: Error (Closing)"

    def toggle_typing(self):
        self.is_typing_enabled = not self.is_typing_enabled
        if self.is_typing_enabled:
            self.last_activity_time = time.time()  # Reset timer on activation
        new_state = "active" if self.is_typing_enabled else "inactive"
        self.update_icon_state(new_state)
        print(f"State toggled: {new_state}")

    def on_exit_click(self, icon=None, item=None):
        print("Exiting...")
        self.stop_event.set()
        if self.icon:
            self.icon.stop()

    def on_press(self, key):
        if key == keyboard.Key.f8:
            is_shift = any(
                k in self.currently_pressed
                for k in [keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r]
            )
            if is_shift:
                self.on_exit_click()
            else:
                self.toggle_typing()
        self.currently_pressed.add(key)

    def on_release(self, key):
        if key in self.currently_pressed:
            self.currently_pressed.remove(key)

    async def async_audio_loop(self):
        """Simple async loop. Quits on any major error."""
        print(f"Connecting to {self.websocket_uri}...")

        websocket = None
        # Initial connection attempts
        for attempt in range(1, 11):
            try:
                websocket = await websockets.connect(self.websocket_uri)
                print("Connected to server.")
                break
            except Exception as e:
                if attempt == 10:
                    print(f"Failed to connect after {attempt} attempts. Giving up.")
                    self.update_icon_state("error")
                    self.on_exit_click()
                    return
                print(f"Connection attempt {attempt}/10 failed ({e}). Retrying in 3s...")
                await asyncio.sleep(3)

        recorder = None
        try:
            async with websocket:
                recorder = AudioRecorder(rate=16000, chunk_size=1024, channels=1)

                async def send_audio():
                    """Starts/Stops the microphone hardware based on is_typing_enabled."""
                    while not self.stop_event.is_set():
                        if self.is_typing_enabled:
                            if not recorder._running:
                                recorder.start_recording()

                            try:
                                audio_iter = recorder.get_audio_chunk()
                                for chunk in audio_iter:
                                    if self.stop_event.is_set() or not self.is_typing_enabled:
                                        break
                                    await websocket.send(chunk.tobytes())
                                    await asyncio.sleep(0.001)
                            except Exception as e:
                                print(f"Recording Error: {e}")
                                break
                            finally:
                                if recorder._running:
                                    recorder.stop_recording()
                        await asyncio.sleep(0.1)

                async def receive_text():
                    while not self.stop_event.is_set():
                        try:
                            msg = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                            text = msg.strip()
                            if text and self.is_typing_enabled:
                                print(f"Server: {text}")
                                self.last_activity_time = time.time()
                                full_text = text + " "

                                if self.paste_mode:
                                    # --- Paste Mode (Clipboard Injection) ---
                                    try:
                                        pyperclip.copy(full_text)
                                        # Critical: Wait for clipboard to sync (required for Terminals)
                                        await asyncio.sleep(0.2)

                                        if platform.system() == "Linux":
                                            # Shift+Insert is more universal than Ctrl+V on Linux
                                            subprocess.run(
                                                [
                                                    "xdotool",
                                                    "key",
                                                    "--clearmodifiers",
                                                    "shift+Insert",
                                                ],
                                                check=False,
                                            )
                                        else:
                                            with self.kb_controller.pressed(keyboard.Key.ctrl):
                                                self.kb_controller.press("v")
                                                self.kb_controller.release("v")
                                    except Exception as e:
                                        print(f"Paste Error: {e}")
                                else:
                                    # --- Type Mode (Simulated Typing) ---
                                    if platform.system() == "Linux":
                                        try:
                                            # Delay 50ms is required for accents (dead keys) and Web Browsers
                                            subprocess.run(
                                                [
                                                    "xdotool",
                                                    "type",
                                                    "--clearmodifiers",
                                                    "--delay",
                                                    "50",
                                                    full_text,
                                                ],
                                                check=False,
                                            )
                                        except FileNotFoundError:
                                            for char in full_text:
                                                self.kb_controller.type(char)
                                                await asyncio.sleep(0.02)
                                    else:
                                        for char in full_text:
                                            self.kb_controller.type(char)
                                            await asyncio.sleep(0.02)
                        except asyncio.TimeoutError:
                            continue

                await asyncio.gather(send_audio(), receive_text())

        except Exception as e:
            print(f"Fatal error: {e}")
            self.update_icon_state("error")
            self.on_exit_click()
        finally:
            if recorder:
                try:
                    recorder.stop_recording()
                except Exception:
                    pass

    def run(self):
        kb_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        kb_listener.start()
        t_watchdog = threading.Thread(target=self.sleep_watchdog, daemon=True)
        t_watchdog.start()
        t_logic = threading.Thread(target=lambda: asyncio.run(self.async_audio_loop()), daemon=True)
        t_logic.start()

        def get_mode_text(item):
            return "Switch to Type Mode" if self.paste_mode else "Switch to Paste Mode"

        def on_mode_click(icon, item):
            self.paste_mode = not self.paste_mode

        self.icon = pystray.Icon(
            "Local Whisper",
            self.icons["inactive"],
            "Local Whisper: Paused",
            menu=pystray.Menu(
                pystray.MenuItem("Toggle (F8)", lambda i, item: self.toggle_typing()),
                pystray.MenuItem(get_mode_text, on_mode_click),
                pystray.MenuItem("Exit (Shift+F8)", self.on_exit_click),
            ),
        )
        self.icon.run()
        kb_listener.stop()


if __name__ == "__main__":
    uri = "ws://127.0.0.1:8000/ws/asr"
    TrayClient(uri).run()
