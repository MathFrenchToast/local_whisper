import argparse
import asyncio
import platform
import queue
import subprocess
import threading
import tkinter as tk

import websockets
from pynput import keyboard

from src.audio_recorder import AudioRecorder

# --- UI Abstraction ---


class BaseUI:
    """Base class for User Interface (CLI or GUI)."""

    def update_status(self, is_enabled: bool):
        raise NotImplementedError

    def update_text(self, text: str):
        raise NotImplementedError

    def log(self, message: str):
        print(message)


class TerminalUI(BaseUI):
    """Standard CLI output."""

    def update_status(self, is_enabled: bool):
        status = "ENABLED" if is_enabled else "DISABLED"
        print(f"\n[Keyboard Control] Typing is now {status}")

    def update_text(self, text: str):
        print(f"\n[Server]: {text}")


class GraphicalUI(BaseUI):
    """Tkinter-based Minimalist Floating Widget."""

    def __init__(self, root, stop_event):
        self.root = root
        self.stop_event = stop_event
        self.queue = queue.Queue()

        # Window setup - Frameless and Compact
        self.root.overrideredirect(True)  # Remove OS title bar
        self.root.attributes("-topmost", 1)  # Always on top
        self.root.geometry("250x35+100+100")  # Small size, default pos

        # Colors
        self.col_enabled = "#d4edda"  # Light Green
        self.col_disabled = "#f8d7da"  # Light Red
        self.col_text = "#155724"

        # Main Frame for background color
        self.frame = tk.Frame(root, bg=self.col_disabled, bd=1, relief="raised")
        self.frame.pack(fill="both", expand=True)

        # Content: Icon, Text, Close button
        self.lbl_icon = tk.Label(self.frame, text="🎙️", bg=self.col_disabled, font=("Arial", 12))
        self.lbl_icon.pack(side="left", padx=(8, 0))

        # Text Label
        self.lbl_text_var = tk.StringVar(value="[F8] to Start")
        self.lbl_text = tk.Label(
            self.frame,
            textvariable=self.lbl_text_var,
            bg=self.col_disabled,
            fg="#333",
            font=("Arial", 10),
        )
        self.lbl_text.pack(side="left", padx=5, fill="x", expand=True)

        # Close Button
        self.btn_close = tk.Label(
            self.frame,
            text="×",
            bg=self.col_disabled,
            fg="#555",
            font=("Arial", 12, "bold"),
            cursor="hand2",
        )
        self.btn_close.pack(side="right", padx=8)
        self.btn_close.bind("<Button-1>", lambda e: self.on_close())

        # Make draggable
        self.frame.bind("<Button-1>", self.start_move)
        self.frame.bind("<B1-Motion>", self.do_move)
        self.lbl_text.bind("<Button-1>", self.start_move)
        self.lbl_text.bind("<B1-Motion>", self.do_move)

        self.x = 0
        self.y = 0

        # Start checking queue
        self.root.after(100, self.process_queue)

    def start_move(self, event):
        self.x = event.x

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.root.winfo_x() + deltax
        y = self.root.winfo_y() + deltay
        self.root.geometry(f"+{x}+{y}")

    def update_visual_status(self, is_enabled):
        color = self.col_enabled if is_enabled else self.col_disabled
        status_text = "Listening..." if is_enabled else "Paused (F8)"

        self.frame.config(bg=color)
        self.lbl_icon.config(bg=color)
        self.lbl_text.config(bg=color)
        self.btn_close.config(bg=color)

        current_text = self.lbl_text_var.get()
        if "Paused" in current_text or "[F8]" in current_text or "Listening" in current_text:
            self.lbl_text_var.set(status_text)

    def update_status(self, is_enabled: bool):
        self.queue.put(("status", is_enabled))

    def update_text(self, text: str):
        display_text = (text[:25] + "..") if len(text) > 25 else text
        self.queue.put(("text", display_text))

    def process_queue(self):
        try:
            while True:
                msg_type, data = self.queue.get_nowait()
                if msg_type == "status":
                    self.update_visual_status(data)
                elif msg_type == "text":
                    self.lbl_text_var.set(data)
        except queue.Empty:
            pass
        finally:
            if not self.stop_event.is_set():
                self.root.after(100, self.process_queue)

    def on_close(self):
        self.stop_event.set()
        self.root.destroy()
        print("Window closed. Exiting...")


# --- Core Logic ---

is_typing_enabled = False


def on_press(key, ui_callback):
    global is_typing_enabled
    try:
        if key == keyboard.Key.f8:
            is_typing_enabled = not is_typing_enabled
            ui_callback(is_typing_enabled)
    except AttributeError:
        pass


async def async_main_loop(uri, ui: BaseUI, stop_event: threading.Event):
    global is_typing_enabled
    kb_controller = keyboard.Controller()
    listener = keyboard.Listener(on_press=lambda k: on_press(k, ui.update_status))
    listener.start()

    ui.log(f"Connecting to {uri}...")

    while not stop_event.is_set():
        try:
            async with websockets.connect(uri) as websocket:
                ui.log("Connected! Press F8 to toggle typing.")
                recorder = AudioRecorder(rate=16000, chunk_size=1024, channels=1)

                async def send_audio():
                    while not stop_event.is_set():
                        if is_typing_enabled:
                            if not recorder._running:
                                recorder.start_recording()
                            try:
                                audio_iter = recorder.get_audio_chunk()
                                for chunk in audio_iter:
                                    if stop_event.is_set() or not is_typing_enabled:
                                        break
                                    await websocket.send(chunk.tobytes())
                                    await asyncio.sleep(0.001)
                            except Exception:
                                break
                            finally:
                                if recorder._running:
                                    recorder.stop_recording()
                        await asyncio.sleep(0.1)

                async def receive_and_type():
                    while not stop_event.is_set():
                        try:
                            transcription = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                            text = transcription.strip()
                            if text:
                                ui.update_text(text)
                                if is_typing_enabled:
                                    full_text = text + " "
                                    if platform.system() == "Linux":
                                        try:
                                            # Use xdotool type with higher delay (50ms) for Web & Accents
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
                                            # Fallback to pynput with character delay
                                            for char in full_text:
                                                kb_controller.type(char)
                                                await asyncio.sleep(0.02)
                                    else:
                                        # Windows/Mac: standard pynput with character delay
                                        for char in full_text:
                                            kb_controller.type(char)
                                            await asyncio.sleep(0.02)
                        except asyncio.TimeoutError:
                            continue

                await asyncio.gather(send_audio(), receive_and_type())

        except Exception as e:
            if not stop_event.is_set():
                ui.log(f"Connection error: {e}. Retrying in 2s...")
                await asyncio.sleep(2)

    listener.stop()


def run_async_in_thread(uri, ui, stop_event):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(async_main_loop(uri, ui, stop_event))
    loop.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Local Whisper Keyboard Client")
    parser.add_argument("--gui", action="store_true", help="Launch with a status window")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", default="8000", help="Server port")
    args = parser.parse_args()

    websocket_uri = f"ws://{args.host}:{args.port}/ws/asr"
    stop_event = threading.Event()

    if args.gui:
        root = tk.Tk()
        ui = GraphicalUI(root, stop_event)
        t = threading.Thread(
            target=run_async_in_thread,
            args=(websocket_uri, ui, stop_event),
            daemon=True,
        )
        t.start()
        try:
            root.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            stop_event.set()
    else:
        ui = TerminalUI()
        try:
            asyncio.run(async_main_loop(websocket_uri, ui, stop_event))
        except KeyboardInterrupt:
            stop_event.set()
