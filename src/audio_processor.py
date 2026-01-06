import numpy as np
import collections
import time
from enum import Enum
from typing import Optional

class VadState(Enum):
    IDLE = 1
    SPEAKING = 2
    COOLDOWN = 3

class AudioProcessor:
    """
    Manages the audio stream buffering and Voice Activity Detection (VAD).
    It accumulates audio chunks and returns a complete segment when silence is detected
    or a max duration is reached.
    """
    def __init__(self, 
                 sample_rate=16000, 
                 silence_threshold=200, 
                 silence_pause_duration=1.0, 
                 max_accumulate_duration=10, 
                 history_buffer_chunks=8):
        
        self.sample_rate = sample_rate
        self.silence_threshold = silence_threshold
        self.silence_pause_duration = silence_pause_duration
        self.max_accumulate_duration = max_accumulate_duration
        
        # State
        self.state = VadState.IDLE
        self.silence_start_time = None
        
        # Buffers
        self.main_buffer = [] # Stores int16 chunks
        self.history_buffer = collections.deque(maxlen=history_buffer_chunks) # Stores int16 chunks (pre-roll)

    def is_silent(self, audio_chunk: np.ndarray) -> bool:
        """Check if an audio chunk is silent based on RMS energy."""
        rms = np.sqrt(np.mean(audio_chunk.astype(np.float32)**2))
        return rms < self.silence_threshold

    def _prepare_segment(self) -> np.ndarray:
        """Concatenates the main buffer and converts to float32 normalized audio."""
        if not self.main_buffer:
            return None
        
        full_audio_int16 = np.concatenate(self.main_buffer)
        # Clear buffer immediately after consuming
        self.main_buffer = [] 
        
        # Convert to float32 and normalize
        full_audio_float32 = full_audio_int16.astype(np.float32) / 32768.0
        return full_audio_float32

    def process(self, audio_bytes: bytes) -> Optional[np.ndarray]:
        """
        Process incoming raw audio bytes (int16).
        Returns a float32 numpy array if a speech segment is complete and ready for processing.
        Returns None if more audio is needed.
        """
        audio_chunk = np.frombuffer(audio_bytes, dtype=np.int16)
        
        # Update history buffer (always keep the last N chunks)
        self.history_buffer.append(audio_chunk)
        
        chunk_is_silent = self.is_silent(audio_chunk)
        current_time = time.time()
        
        result = None

        if self.state == VadState.IDLE:
            if not chunk_is_silent:
                # Speech detected!
                self.state = VadState.SPEAKING
                # Dump history (pre-roll) into main buffer to catch the start of the word
                self.main_buffer.extend(list(self.history_buffer))
                self.history_buffer.clear()
        
        elif self.state == VadState.SPEAKING:
            self.main_buffer.append(audio_chunk)
            
            if chunk_is_silent:
                # Speech paused, enter cooldown
                self.state = VadState.COOLDOWN
                self.silence_start_time = current_time
            else:
                # Check max duration
                # Assuming chunk size is somewhat constant or we can just sum lengths
                current_duration_samples = sum(len(c) for c in self.main_buffer)
                if current_duration_samples >= self.sample_rate * self.max_accumulate_duration:
                    # Force process
                    result = self._prepare_segment()
                    self.state = VadState.IDLE

        elif self.state == VadState.COOLDOWN:
            self.main_buffer.append(audio_chunk)
            
            if not chunk_is_silent:
                # Speech resumed
                self.state = VadState.SPEAKING
                self.silence_start_time = None
            elif (current_time - self.silence_start_time) > self.silence_pause_duration:
                # Silence has lasted long enough, segment is complete
                result = self._prepare_segment()
                self.state = VadState.IDLE
        
        return result
