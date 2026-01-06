import unittest
from unittest.mock import AsyncMock, patch

from src.llm_service import LLMService


class TestLLMService(unittest.TestCase):
    def test_disabled_service(self):
        """If disabled, should return original text immediately."""
        service = LLMService(enabled=False)
        text = "Hello world"
        # Since it's async, we use asyncio.run or just check logic
        import asyncio

        result = asyncio.run(service.process_text(text))
        self.assertEqual(result, text)

    @patch("src.llm_service.AsyncOpenAI")
    def test_process_text_success(self, MockOpenAI):
        """Test successful LLM processing."""
        # Setup mock client and response
        mock_client = MockOpenAI.return_value
        mock_client.chat.completions.create = AsyncMock()

        mock_response = AsyncMock()
        mock_response.choices = [AsyncMock(message=AsyncMock(content="Corrected text"))]
        mock_client.chat.completions.create.return_value = mock_response

        service = LLMService(enabled=True)
        import asyncio

        result = asyncio.run(service.process_text("Original text"))

        self.assertEqual(result, "Corrected text")
        mock_client.chat.completions.create.assert_called_once()

    @patch("src.llm_service.AsyncOpenAI")
    def test_process_text_fallback_on_error(self, MockOpenAI):
        """Test that it returns original text if API fails."""
        mock_client = MockOpenAI.return_value
        mock_client.chat.completions.create = AsyncMock(
            side_effect=Exception("API Error")
        )

        service = LLMService(enabled=True)
        import asyncio

        original = "Original text"
        result = asyncio.run(service.process_text(original))

        # Should fallback to original text
        self.assertEqual(result, original)


if __name__ == "__main__":
    unittest.main()
