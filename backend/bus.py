# bus.py
import asyncio
from typing import AsyncIterator, Any, Optional

class EventBus:
    """Simple in-process pub/sub bus using an asyncio.Queue."""

    def __init__(self, maxsize: int = 1000):
        self._q: asyncio.Queue[Any] = asyncio.Queue(maxsize=maxsize)

    async def publish(self, event: Any) -> None:
        """Put an event on the bus (awaits if queue is full)."""
        await self._q.put(event)

    async def subscribe(self) -> AsyncIterator[Any]:
        """Yield events forever (consumer loop)."""
        while True:
            evt = await self._q.get()
            yield evt
            self._q.task_done()
