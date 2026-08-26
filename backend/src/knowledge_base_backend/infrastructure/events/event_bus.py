import asyncio
from typing import Dict, Set, Any
import logging

logger = logging.getLogger(__name__)

class EventBus:
    """
    A simple in-memory event bus for broadcasting messages to SSE clients.
    Topic is usually the instrument_id to broadcast updates for a specific instrument.
    """
    def __init__(self):
        self._queues: Dict[str, Set[asyncio.Queue]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, topic: str) -> asyncio.Queue:
        """Subscribe to a topic. Returns a queue that will receive events."""
        queue = asyncio.Queue()
        async with self._lock:
            if topic not in self._queues:
                self._queues[topic] = set()
            self._queues[topic].add(queue)
            logger.info(f"New subscriber for topic: {topic}. Total: {len(self._queues[topic])}")
        return queue

    async def unsubscribe(self, topic: str, queue: asyncio.Queue) -> None:
        """Unsubscribe from a topic."""
        async with self._lock:
            if topic in self._queues and queue in self._queues[topic]:
                self._queues[topic].remove(queue)
                logger.info(f"Subscriber removed for topic: {topic}. Remaining: {len(self._queues[topic])}")
                if not self._queues[topic]:
                    del self._queues[topic]

    async def publish(self, topic: str, event: Any) -> None:
        """Publish an event to all subscribers of a topic."""
        async with self._lock:
            if topic not in self._queues:
                return
            
            # Put the event in all subscriber queues
            for queue in self._queues[topic]:
                try:
                    # Use put_nowait so one slow client doesn't block publishing
                    queue.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning(f"Queue full for topic {topic}, dropping event.")
