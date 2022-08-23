import atexit
import logging
import os

import beeline


# todo: this is currently dead code.
def post_worker_init() -> None:
    """
    uWSGI post-forking hook, initializing new process.  # noqa: D403.

    In this case, we use it primarily for instrumentation and telemetry
    setup. Data will only get sent to honeycomb when we define the
    following environment variable: `HONEYCOMB_KEY`. If it is not
    defined, it will verbosely print to stderr what info it would have
    sent there. No valid API key would then be necessary.
    """
    logging.info(f"beeline initialization on process pid {os.getpid()}")

    honeycomb_key = os.getenv("HONEYCOMB_KEY", "")
    # if no api key, do not send data and instead print what would be sent to stderr
    # if we have a key, pass data to honeycomb.io
    args = {
        "writekey": honeycomb_key,
        "dataset": "blossom",
        "debug": True if len(honeycomb_key) == 0 else False,
        "sample_rate": 10,
    }
    beeline.init(**args)
    atexit.register(beeline.close)
