from abc import ABC, abstractmethod
from typing import Any, Dict

class ProcessingStep(ABC):
    """
    Interface for any step in the text processing pipeline.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of this step (e.g., 'translation', 'logger')."""
        pass

    @abstractmethod
    async def process(self, text: str, context: Dict[str, Any] = None) -> str:
        """
        Process the incoming text.
        
        Args:
            text: The text to process.
            context: A dictionary containing extra metadata (language, confidence, etc.).
                     Plugins can modify this context to pass data to subsequent steps.
        
        Returns:
            The modified (or original) text.
        """
        pass
