from serverchan_sdk import sc_send
from pushers.generic_pushservice import GenericPushService
from typing import Optional, Dict, Any

class ServerChanPushService(GenericPushService):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

    async def push(self, content: str, title: str = "", url: Optional[str] = None) -> None:
        sendkey = self.config.get("sendkey")
        if not sendkey:
            raise ValueError("ServerChan sendkey is not configured.")
        await sc_send(
            sendkey=sendkey,
            title=title,
            desp=content + (f"\n\n[更多详情]({url})" if url else "")
        )