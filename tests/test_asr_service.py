import unittest
from unittest.mock import MagicMock, patch
import numpy as np
import sys
import os

# Ensure src can be imported
sys.path.append(os.getcwd())

from src.asr_service import ASRService

class TestASRService(unittest.TestCase):
    
    @patch('src.asr_service.WhisperModel')
    def test_initialization(self, MockWhisperModel):
        """Test that ASRService initializes the model with correct parameters."""
        service = ASRService(model_size="tiny", device="cpu", compute_type="int8")
        
        MockWhisperModel.assert_called_once_with(
            "tiny", 
            device="cpu", 
            compute_type="int8"
        )
        self.assertIsNotNone(service.model)

    @patch('src.asr_service.WhisperModel')
    def test_transcribe_audio(self, MockWhisperModel):
        """Test the transcription method."""
        # Setup mock
        mock_instance = MockWhisperModel.return_value
        
        # Mocking the return of transcribe method from faster-whisper
        # It returns (segments, info)
        Segment = MagicMock()
        Segment.text = " Hello world "
        mock_instance.transcribe.return_value = ([Segment], None)

        service = ASRService()
        
        # Create dummy audio data (float32)
        dummy_audio = np.zeros(16000, dtype=np.float32)
        
        # Call transcribe
        result = service.transcribe_audio(dummy_audio, language="en")
        
        # Verification
        mock_instance.transcribe.assert_called_once()
        # Verify args passed to transcribe
        args, kwargs = mock_instance.transcribe.call_args
        self.assertTrue(np.array_equal(args[0], dummy_audio))
        self.assertEqual(kwargs['language'], 'en')
        
        # Check result text (ASRService should strip whitespace)
        self.assertEqual(result, "Hello world")

    @patch('src.asr_service.WhisperModel')
    def test_transcribe_empty_result(self, MockWhisperModel):
        """Test when model returns no segments."""
        mock_instance = MockWhisperModel.return_value
        mock_instance.transcribe.return_value = ([], None)

        service = ASRService()
        dummy_audio = np.zeros(16000, dtype=np.float32)
        
        result = service.transcribe_audio(dummy_audio)
        self.assertEqual(result, "")

if __name__ == '__main__':
    unittest.main()
