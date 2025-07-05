from concurrent.futures import Future
from threading import Thread

import logging
import asyncio

def start_async():
    loop = asyncio.get_event_loop()
    Thread(target=loop.run_forever).start()
    return loop

_loop = start_async()

def submit_async(coro) -> Future:
    return asyncio.run_coroutine_threadsafe(coro, _loop)

def stop_async():
    if _loop and _loop.is_running():
        _loop.call_soon_threadsafe(_loop.stop)

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