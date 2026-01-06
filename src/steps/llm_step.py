from src.interfaces import ProcessingStep
from src.llm_service import LLMService
from typing import Dict, Any

class LLMCorrectionStep(ProcessingStep):
    """
    Wraps the LLMService into a pipeline step.
    """
    def __init__(self, config):
        self._llm_service = LLMService(
            base_url=config['llm_url'],
            api_key=config['llm_api_key'],
            model=config['llm_model'],
            system_prompt=None, # Will load default or from file internally if needed
            enabled=config['llm_enabled']
        )
        # Manually load system prompt file if needed since we are re-instantiating
        # In a real refactor, we would pass the existing instance.
        import os
        if os.path.exists("system_prompt.txt"):
            with open("system_prompt.txt", "r") as f:
                self._llm_service.system_prompt = f.read().strip()

    @property
    def name(self) -> str:
        return "llm_correction"

    async def process(self, text: str, context: Dict[str, Any] = None) -> str:
        if not self._llm_service.enabled:
            return text
        
        # We can also put the "Raw" text into context for other plugins
        if context is not None:
            context["raw_asr"] = text
            
        print(f" [Raw ASR]: {text}")
        result = await self._llm_service.process_text(text)
        print(f" [LLM Fix]: {result}")
        return result
