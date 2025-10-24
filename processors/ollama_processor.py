from ollama import AsyncClient
from processors.generic_processor import GenericProcessor
from typing import Optional

class OllamaProcessor(GenericProcessor):
    model_name: str = "llama2"
    temperature: float = 0.7
    max_tokens: int = 1024
    api_key: Optional[str] = None
    base_url: str = "http://localhost:11434"

    async def generate(self, prompt: str, input: str) -> str:
        client = AsyncClient(host=self.base_url)
        full_prompt = f"{prompt}{input}"
        response = await client.generate(
                model=self.model_name,
                prompt=full_prompt,
                options={
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens
                }
            )
        return response.response