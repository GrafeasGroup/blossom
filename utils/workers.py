# adapted from https://stackoverflow.com/a/6614844

import atexit
import queue
import threading
from typing import Any, Callable


def _worker() -> None:
    """Create worker for background tasks."""
    while True:
        func, args, kwargs = _queue.get()
        try:
            func(*args, **kwargs)
        except:  # noqa: E722
            import traceback

            # prevent circular dependency
            from api.views.slack_helpers import client

            details = traceback.format_exc()
            client.chat_postMessage(
                channel="botstuffs",
                text=f"Background worker exception: ```{details}```",
            )
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
        _queue.put((func, args, kwargs))

    return decorator


_queue = queue.Queue()
_thread = threading.Thread(target=_worker)
_thread.daemon = True
_thread.start()


def _cleanup() -> None:
    _queue.join()  # so we don't exit too soon


atexit.register(_cleanup)
