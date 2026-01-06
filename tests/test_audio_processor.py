import unittest

import numpy as np

from src.audio_processor import AudioProcessor, VadState


class TestAudioProcessor(unittest.TestCase):
    def setUp(self):
        # Configuration for fast testing
        self.sample_rate = 16000
        self.processor = AudioProcessor(
            sample_rate=self.sample_rate,
            silence_threshold=100,  # Low threshold for testing
            silence_pause_duration=0.1,  # Short pause for fast tests
            max_accumulate_duration=1.0,
            history_buffer_chunks=2,
        )

    def create_audio_chunk(self, amplitude, size=1024):
        """Helper to create a chunk of int16 audio with constant amplitude."""
        # amplitude should be int16
        return np.full(size, amplitude, dtype=np.int16).tobytes()

    def test_initial_state(self):
        self.assertEqual(self.processor.state, VadState.IDLE)
        self.assertEqual(len(self.processor.main_buffer), 0)

    def test_is_silent(self):
        # Create silent chunk (amplitude 0)
        silent_chunk = np.frombuffer(self.create_audio_chunk(0), dtype=np.int16)
        self.assertTrue(self.processor.is_silent(silent_chunk))

        # Create loud chunk (amplitude 1000 > threshold 100)
        loud_chunk = np.frombuffer(self.create_audio_chunk(1000), dtype=np.int16)
        self.assertFalse(self.processor.is_silent(loud_chunk))

    def test_workflow_speech_detection(self):
        """
        Simulate a sequence: Silence -> Speech -> Silence
        Verify that we get a segment at the end.
        """
        chunk_size = 1024

        # 1. Send Silence (Should remain IDLE)
        silent_bytes = self.create_audio_chunk(0, chunk_size)
        result = self.processor.process(silent_bytes)
        self.assertIsNone(result)
        self.assertEqual(self.processor.state, VadState.IDLE)

        # 2. Send Speech (Should switch to SPEAKING)
        loud_bytes = self.create_audio_chunk(5000, chunk_size)
        result = self.processor.process(loud_bytes)
        self.assertIsNone(result)  # Still buffering
        self.assertEqual(self.processor.state, VadState.SPEAKING)

        # 3. Send more Speech
        result = self.processor.process(loud_bytes)
        self.assertIsNone(result)
        self.assertEqual(self.processor.state, VadState.SPEAKING)

        # 4. Send Silence (Should switch to COOLDOWN)
        # Note: silence_pause_duration is 0.1s.
        # With 16k rate, 0.1s is 1600 samples.
        # chunk size 1024 is ~0.064s.
        # So we need ~2 chunks of silence to trigger the end.

        # First silent chunk -> Enter COOLDOWN
        result = self.processor.process(silent_bytes)
        self.assertIsNone(result)
        self.assertEqual(self.processor.state, VadState.COOLDOWN)

        # Second silent chunk -> Wait (time based)
        # We might need to sleep slightly to ensure time.time() difference is enough
        import time

        time.sleep(0.15)

        result = self.processor.process(silent_bytes)

        # Now it should be done
        self.assertIsNotNone(result)
        self.assertIsInstance(result, np.ndarray)
        self.assertEqual(result.dtype, np.float32)

        # State should be back to IDLE
        self.assertEqual(self.processor.state, VadState.IDLE)

    def test_max_duration_trigger(self):
        """Verify that max duration forces a cut even if speaking continues."""
        # Re-init with very short max duration
        self.processor = AudioProcessor(
            sample_rate=16000,
            silence_threshold=100,
            max_accumulate_duration=0.1,  # 0.1 second max
        )

        chunk_size = 1024  # ~0.064s
        loud_bytes = self.create_audio_chunk(5000, chunk_size)

        # 1. Start speaking
        self.processor.process(loud_bytes)  # 0.064s accumulated
        self.assertEqual(self.processor.state, VadState.SPEAKING)

        # 2. Continue speaking - this should cross 0.1s threshold (0.064 * 2 = 0.128s)
        result = self.processor.process(loud_bytes)

        # Should return a segment forced by max duration
        self.assertIsNotNone(result)
        self.assertEqual(self.processor.state, VadState.IDLE)


if __name__ == "__main__":
    unittest.main()
