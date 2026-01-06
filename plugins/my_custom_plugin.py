from src.interfaces import ProcessingStep
from typing import Dict, Any

class WordReplacerPlugin(ProcessingStep):
    """
    Example Plugin: Replaces specific words (e.g., swear words or specialized jargon).
    """
    @property
    def name(self) -> str:
        return "jargon_replacer"

    async def process(self, text: str, context: Dict[str, Any] = None) -> str:
        # Simple example dictionary
        replacements = {
            "gros mot": "****",
            "asap": "as soon as possible",
            "tba": "to be announced"
        }
        
        processed_text = text
        for old, new in replacements.items():
            # Case insensitive replace
            import re
            processed_text = re.sub(re.escape(old), new, processed_text, flags=re.IGNORECASE)
            
        if processed_text != text:
            print(f" [Plugin]: Replaced jargon in text.")
            
        return processed_text
