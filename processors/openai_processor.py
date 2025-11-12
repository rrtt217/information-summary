from openai import AsyncOpenAI
from .generic_processor import GenericProcessor
from typing import Optional
import logging

class OpenAIProcessor(GenericProcessor):
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 1024
    api_key: Optional[str] = None
    base_url: str = "https://api.openai.com/v1"
    languange: str = "zh"

    async def generate(self, prompt: str, input: str) -> str:
        client = AsyncOpenAI(api_key=self.api_key,base_url=self.base_url)
        full_prompt = f"{prompt}{input}"
        response = await client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=self.temperature,
                max_tokens=self.max_tokens
        )
        logging.debug(f"Response:{response.choices[0].message.content}")
        return str(response.choices[0].message.content)