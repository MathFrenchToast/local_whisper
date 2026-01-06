import time

import numpy as np
import pyaudio


class AudioRecorder:
    def __init__(self, rate=16000, chunk_size=1024, format=pyaudio.paInt16, channels=1):
        """
        Initializes the audio recorder.

        Args:
            rate (int): Sample rate of the audio (Hz).
            chunk_size (int): Number of frames per buffer.
            format (int): Audio format (e.g., pyaudio.paInt16).
            channels (int): Number of audio channels.
        """
        self.rate = rate
        self.chunk_size = chunk_size
        self.format = format
        self.channels = channels
        self.p = pyaudio.PyAudio()
        self.stream = None
        self._running = False
        print(
            f"AudioRecorder initialized with rate={rate}, chunk_size={chunk_size}, channels={channels}"
        )

    def start_recording(self):
        """
        Starts the audio recording stream.
        """
        if self._running:
            print("Recording is already running.")
            return

        self.stream = self.p.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk_size,
        )
        self._running = True
        print("Recording started...")

    def stop_recording(self):
        """
        Stops the audio recording stream.
        """
        if not self._running:
            print("Recording is not running.")
            return

        self._running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        print("Recording stopped.")

    def get_audio_chunk(self):
        """
        Generator that yields audio chunks as NumPy arrays.
        """
        if not self._running:
            raise RuntimeError(
                "Recording is not started. Call start_recording() first."
            )

        while self._running:
            try:
                data = self.stream.read(self.chunk_size, exception_on_overflow=False)
                # Convert bytes to numpy array
                audio_array = np.frombuffer(data, dtype=np.int16)
                # Normalize to float32 for Whisper, if needed (Whisper expects float32 typically)
                # For now, return int16 and let ASRService handle conversion to float32
                yield audio_array
            except IOError as e:
                # Handle specific PyAudio errors, e.g., input overflow
                print(f"PyAudio error: {e}. Skipping chunk.")
                continue

    def __del__(self):
        """
        Clean up PyAudio resources when the object is deleted.
        """
        if self.p:
            self.p.terminate()


if __name__ == "__main__":
    # Example usage:
    recorder = AudioRecorder()
    recorder.start_recording()

    print("Listening for 5 seconds... Say something!")
    audio_chunks = []
    start_time = time.time()
    for i, chunk in enumerate(recorder.get_audio_chunk()):
        audio_chunks.append(chunk)
        if time.time() - start_time > 5:
            break
        # Optional: Print chunk info
        # print(f"Captured chunk {i+1}, size: {chunk.shape}, dtype: {chunk.dtype}")

    recorder.stop_recording()

    # You can now process the captured audio_chunks, e.g., save to a file or send to ASR
    print(f"\nCaptured {len(audio_chunks)} audio chunks.")
    if audio_chunks:
        # Concatenate all chunks into a single array
        full_audio = np.concatenate(audio_chunks)
        print(f"Total audio captured: {full_audio.shape} samples.")

        # Example: Save to a WAV file (requires soundfile)
        import soundfile as sf

        output_filename = "recorded_audio.wav"
        # Ensure it's float32 for soundfile if it was converted for ASR
        # For saving raw int16, specify dtype=np.int16 in sf.write
        sf.write(output_filename, full_audio, recorder.rate, subtype="PCM_16")
        print(f"Saved recorded audio to {output_filename}")

    print("Example finished.")
