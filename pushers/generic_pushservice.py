from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
class GenericPushService(ABC):
    config: Dict[str, Any]
    @abstractmethod
    async def push(self, content: str, title: str = "", url: Optional[str] = None) -> None:
        pass