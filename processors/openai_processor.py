from openai import AsyncOpenAI
from processors.generic_processor import GenericProcessor
from typing import Optional

class OpenAIProcessor(GenericProcessor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def generate(self, prompt: str, input: str) -> str:
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        full_prompt = f"{prompt}{input}"
        response = await client.chat.completions.create(
            model=self.model_name,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        return str(response.choices[0].message.content)