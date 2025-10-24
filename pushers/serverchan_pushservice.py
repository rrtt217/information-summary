from serverchan_sdk import sc_send
from pushers.generic_pushservice import GenericPushService
from typing import Optional, Dict, Any
import asyncio
import logging

logger = logging.getLogger(__name__)

class ServerChanPushService(GenericPushService):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)

    async def push(self, content: str, title: str = "", url: Optional[str] = None) -> None:
        logger.info(f"ServerChanPushService.push called with title: '{title}', content length: {len(content)}")
        sendkey = self.config.get("sendkey")
        if not sendkey:
            logger.error("ServerChan sendkey is not configured.")
            raise ValueError("ServerChan sendkey is not configured.")
        logger.info(f"ServerChan sendkey found: {sendkey[:8]}***")
        try:
            result = await asyncio.get_running_loop().run_in_executor(
                None,
                lambda: sc_send(
                    sendkey=sendkey,
                    title=title,
                    desp=content + (f"\n\n[更多详情]({url})" if url else "")
                )
            )
            logger.info(f"ServerChan push executed successfully, result: {result}")
        except Exception as e:
            logger.error(f"ServerChan push failed with error: {e}")
            raise e