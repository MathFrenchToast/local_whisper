from openai import APIConnectionError, APITimeoutError, AsyncOpenAI

# Default system prompt if none is provided
DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant that corrects and formats speech-to-text transcriptions. 
Your task is to fix grammar, punctuation, and capitalization. 
Do not change the meaning. Do not add conversational filler. 
Return ONLY the corrected text."""


class LLMService:
    def __init__(
        self,
        base_url="http://localhost:11434/v1",
        api_key="ollama",
        model="llama3",
        system_prompt=None,
        enabled=False,
    ):
        self.enabled = enabled
        self.model = model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

        if self.enabled:
            print(f"Initializing LLM Service connected to: {base_url} (Model: {model})")
            self.client = AsyncOpenAI(base_url=base_url, api_key=api_key)
        else:
            self.client = None

    async def process_text(self, text: str) -> str:
        """
        Send text to LLM for post-processing.
        Returns the processed text, or the original text if LLM fails or is disabled.
        """
        if not self.enabled or not text or not text.strip():
            return text

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self.system_prompt
                        + "\n\nCRITICAL: Wrap your final answer in [[TEXT]] tags. Example: [[TEXT]]Your cleaned transcription here[[TEXT]]",
                    },
                    {"role": "user", "content": f"Input text to correct:\n{text}"},
                ],
                temperature=0.1,  # Minimal temperature
                max_tokens=1024,
            )

            raw_content = response.choices[0].message.content.strip()

            # --- Robust Extraction ---
            # Try to find content between [[TEXT]] tags or just [[ ]]
            import re

            # Match [[TEXT]]content[[TEXT]] OR [[content]]
            match = re.search(
                r"\[\[(?:TEXT)?\]\](.*?)\[\[(?:TEXT)?\]\]", raw_content, re.DOTALL
            )

            if match:
                cleaned_text = match.group(1).strip()
            else:
                # Fallback: Check if the whole string is wrapped in [[...]] without the TEXT label
                if raw_content.startswith("[[") and raw_content.endswith("]]"):
                    cleaned_text = raw_content[2:-2].strip()
                else:
                    cleaned_text = raw_content

            # --- Manual Cleanup of LLM Headers (Safety Net) ---
            lines = cleaned_text.split("\n")
            if len(lines) > 1 and lines[0].strip().endswith(":"):
                potential_header = lines[0].strip().lower()
                headers_keywords = [
                    "correct",
                    "output",
                    "transcription",
                    "résultat",
                    "texte",
                    "voici",
                ]
                if any(kw in potential_header for kw in headers_keywords):
                    cleaned_text = "\n".join(lines[1:]).strip()

            # Remove leading/trailing quotes often added by LLMs
            if cleaned_text.startswith('"') and cleaned_text.endswith('"'):
                cleaned_text = cleaned_text[1:-1].strip()

            # Final scrub of potential remaining brackets if the regex missed them
            if cleaned_text.startswith("[[") and cleaned_text.endswith("]]"):
                cleaned_text = cleaned_text[2:-2].strip()

            # Sanity check: if LLM returns empty string for non-empty input, fallback
            if not cleaned_text:
                return text

            return cleaned_text

        except (APIConnectionError, APITimeoutError) as e:
            print(f"[LLM Error] Connection failed: {e}")
            return text  # Fallback to original
        except Exception as e:
            print(f"[LLM Error] Unexpected error: {e}")
            return text  # Fallback to original
