from concurrent.futures import Future
from threading import Thread

import logging
import asyncio

class ThreadLoop:
    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None

    def start_async(self):
        if self.loop: return
        self.loop = asyncio.new_event_loop()
        Thread(target=self.loop.run_forever, daemon=True).start()

    def submit_async(self, coro) -> Future | None:
        if self.loop:
            return asyncio.run_coroutine_threadsafe(coro, self.loop)
        return None

    def stop_async(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)

def setup_logging(
    *,
    handler: logging.Handler = logging.StreamHandler(),
    formatter: logging.Formatter = logging.Formatter(
            '[{asctime}] [{levelname:<8}] {name}: {message}',
            '%Y-%m-%d %H:%M:%S',
            style='{'
        ),
    level: int = logging.INFO,
    root: bool = False,
) -> None:
    if root:
        logger = logging.getLogger()
    else:
        library, _, _ = __name__.partition('.')
        logger = logging.getLogger(library)

    handler.setFormatter(formatter)
    logger.setLevel(level)
    logger.addHandler(handler)