from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Literal
import sys
sys.path.append("..")  # 添加上级目录到模块搜索路径
from clients.generic_client import GenericClient

class GenericProcessor(ABC):
    model_name: str
    temperature: float
    max_tokens: int
    api_key: Optional[str]
    base_url: str
    prompts: Dict[str, str] = {
        "translate": "Translate the following text from {from_lang} to {to_lang}:\n\n",
        "translate-without-from": "Translate the following text to {to_lang}:\n\n",
        "translate-en-to-zh": "将以下英文文本翻译成中文：\n\n",
        "translate-to-zh": "将以下文本翻译成中文：\n\n",
    }
    @abstractmethod
    async def generate(self, prompt: str, input: str) -> str:
        pass
    # 下面这些方法可能与Client交互，以完成更复杂的任务；它们包括了具体实现。
    async def translate(self, from_lang: Optional[str], to_lang: str, text: str) -> str:
        if "translate" not in self.prompts:
            raise NotImplementedError("Translate prompt is not defined.")
        if from_lang and f"translate-{from_lang}-to-{to_lang}" in self.prompts:
            prompt = self.prompts.get(f"translate-{from_lang}-to-{to_lang}", "")
        elif f"translate-to-{to_lang}" in self.prompts:
            prompt = self.prompts.get(f"translate-to-{to_lang}", "")
        elif from_lang:
            prompt = self.prompts.get("translate", "").format(from_lang=from_lang, to_lang=to_lang)
        else:
            prompt = self.prompts.get("translate-without-from", "").format(to_lang=to_lang)
        return await self.generate(prompt, text)