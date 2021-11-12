# noqa: F401,F403

import logging
import os

# Route us to the correct settings file based on environment variables. Allows
# us to add a stage environment really easily.

logger = logging.getLogger("blossom")
env = os.environ.get("ENVIRONMENT", None)

if env == "local":
    from blossom.settings.local import *
elif env == "testing":
    from blossom.settings.testing import *
elif os.path.exists("local_settings.py"):
    # Local override -- check for existence of local_settings.py and load it if possible
    logger.warning("Found local_settings.py -- loading and using!")
    from local_settings import *
else:
    from blossom.settings.prod import *
