"""AXIOM Event Bus — lightweight pub/sub for inter-component communication."""

import asyncio
from typing import Callable, Any
from collections import defaultdict
from core.logger import get_logger

logger = get_logger(__name__)


class EventBus:
    """Simple async event bus for system-wide event propagation."""

    def __init__(self):
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable) -> None:
        self._handlers[event_type].append(handler)
        logger.debug(f"Subscribed to '{event_type}'", handler=handler.__name__)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        if handler in self._handlers[event_type]:
            self._handlers[event_type].remove(handler)

    async def emit(self, event_type: str, data: Any = None) -> None:
        handlers = self._handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Event handler error for '{event_type}': {e}")


# Singleton event bus
event_bus = EventBus()
