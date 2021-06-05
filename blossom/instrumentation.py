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
    if len(honeycomb_key) == 0:
        # pass data to honeycomb.io if we have a key
        beeline.init(writekey=honeycomb_key, dataset="blossom", debug=False)
    else:
        # if no api key, do not send data and instead print what would be sent to stderr
        beeline.init(writekey="", dataset="blossom", debug=True)
    atexit.register(beeline.close)
