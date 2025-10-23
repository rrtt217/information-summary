from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
class GenericPushService(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    @abstractmethod
    async def push(self, content: str, title: str = "", url: Optional[str] = None) -> None:
        pass