import atexit
import logging
import os
from typing import Any

import beeline


def post_worker_init(*args: Any, **kwargs: Any) -> None:
    """
    Gunicorn post-forking hook, initializing new process.

    In this case, we use it primarily for instrumentation and telemetry
    setup. Data will only get sent to honeycomb when we define the
    following environment variable: `HONEYCOMB_KEY`. If it is not
    defined, it will verbosely print to stderr what info it would have
    sent there. No valid API key would then be necessary.
    """
    logging.info(f"beeline initialization on process pid {os.getpid()}")

    honeycomb_key = os.getenv("HONEYCOMB_KEY", "")
    beeline.init(
        writekey=honeycomb_key, dataset="blossom", debug=len(honeycomb_key) == 0
    )
    atexit.register(beeline.close)
