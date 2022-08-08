# adapted from https://stackoverflow.com/a/6614844

import atexit
import logging
import queue
import threading
from typing import Any, Callable

from django.conf import settings

log = logging.getLogger(__name__)


def _worker() -> None:
    """Create worker for background tasks."""
    while True:
        func, args, kwargs = _queue.get()
        try:
            func(*args, **kwargs)
        except:  # noqa: E722
            import traceback

            # prevent circular dependency
            from blossom.api.slack import client

            details = traceback.format_exc()
            message = f"Background worker exception: ```{details}```"
            if settings.ENABLE_SLACK:
                client.chat_postMessage(
                    channel=settings.SLACK_DEFAULT_CHANNEL,
                    text=message,
                )
            log.error(message)
        finally:
            _queue.task_done()  # so we can join at exit


def send_to_worker(func: Callable) -> Callable:
    """
    Pass decorated function to background thread.

    Note that any function passed to it should not expect to return any data.
    If communication is needed outside the function, then it should write to
    somewhere else that can be seen from a different thread.
    """

    def decorator(*args: Any, **kwargs: Any) -> None:
        # Detect the `worker_test_mode` arg here. If it's present, pop it out
        # and just return the function with all the other args instead of
        # routing it through the queue. This functionality should still be
        # tested separately.
        if "worker_test_mode" in kwargs:
            del kwargs["worker_test_mode"]
            return func(*args, **kwargs)

        _queue.put((func, args, kwargs))

    return decorator


_queue = queue.Queue()
_thread = threading.Thread(target=_worker)
_thread.daemon = True
_thread.start()


def _cleanup() -> None:
    _queue.join()  # so we don't exit too soon


atexit.register(_cleanup)
