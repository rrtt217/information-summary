from ollama import AsyncClient
from processors.generic_processor import GenericProcessor
from typing import Optional

class OllamaProcessor(GenericProcessor):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)