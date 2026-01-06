import numpy as np
from faster_whisper import WhisperModel


class ASRService:
    def __init__(self, model_size="small", device="cpu", compute_type="int8"):
        """
        Initializes the ASR service with a Faster Whisper model.

        Args:
            model_size (str): The size of the Whisper model to use (e.g., "tiny", "base", "small", "medium", "large-v2").
            device (str): The device to run the model on ("cuda" for GPU, "cpu" for CPU).
            compute_type (str): The compute type (e.g., "int8", "float16", "float32").
        """
        print(
            f"Loading Whisper model: {model_size} on {device} with {compute_type} compute type..."
        )
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print("Whisper model loaded.")

    def transcribe_audio(
        self, audio_segment: np.ndarray, language=None, vad_filter=False
    ) -> str:
        """
        Transcribes a segment of audio.

        Args:
            audio_segment (np.ndarray): A NumPy array containing the audio segment (float32, 16kHz).
            language (str, optional): The language of the audio. If None, it will be detected automatically.
            vad_filter (bool): Whether to use Voice Activity Detection to filter out silence.

        Returns:
            str: The transcribed text.
        """
        if audio_segment.dtype != np.float32:
            audio_segment = audio_segment.astype(np.float32)

        segments, info = self.model.transcribe(
            audio_segment, language=language, beam_size=5, vad_filter=vad_filter
        )

        transcribed_text = ""
        for segment in segments:
            transcribed_text += segment.text

        return transcribed_text.strip()


if __name__ == "__main__":
    # Example usage (for testing purposes, requires an audio file)
    import os

    import soundfile as sf

    # Create a dummy audio file for testing
    dummy_audio_path = "test_audio.wav"
    if not os.path.exists(dummy_audio_path):
        print("Creating a dummy audio file for testing...")
        # Generate 5 seconds of silent audio at 16kHz
        samplerate = 16000
        duration = 5  # seconds
        frequency = 440  # Hz
        t = np.linspace(0.0, duration, int(samplerate * duration), endpoint=False)
        data = 0.5 * np.sin(2 * np.pi * frequency * t)  # Simple sine wave
        sf.write(dummy_audio_path, data, samplerate)
        print(f"Dummy audio file created at {dummy_audio_path}")

    # Load the dummy audio file
    audio, samplerate = sf.read(dummy_audio_path)
    if samplerate != 16000:
        # Resample if not 16kHz (Whisper expects 16kHz)
        # For simplicity, this example assumes 16kHz or handles it manually.
        # In a real app, use a proper resampler like torchaudio.transforms.Resample
        print(
            f"Warning: Audio samplerate is {samplerate}Hz, Whisper expects 16kHz. Resampling would be needed."
        )
        # For this example, we'll just proceed, but be aware of this in a real scenario.

    # Initialize ASR service
    asr_service = ASRService(
        model_size="tiny", device="cpu", compute_type="int8"
    )  # Using tiny model for quick test

    # Transcribe the audio
    print(f"\nTranscribing '{dummy_audio_path}'...")
    transcription = asr_service.transcribe_audio(audio)
    print(f"Transcription: '{transcription}'")

    # Clean up dummy audio file
    # os.remove(dummy_audio_path)
    # print(f"Cleaned up {dummy_audio_path}")
