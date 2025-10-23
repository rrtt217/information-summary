from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Literal
class GenericProcessor(ABC):
    model_name: str
    temperature: float
    max_tokens: int
    api_key: Optional[str]
    base_url: str
    @abstractmethod
    async def generate(self, prompt: str, input: str) -> str:
        pass