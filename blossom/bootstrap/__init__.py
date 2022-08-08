import os
from datetime import datetime, timedelta
from typing import List, Optional

import dotenv
from blossom_wrapper import BlossomAPI
from praw import Reddit

dotenv.load_dotenv()

blossom: BlossomAPI = (
    BlossomAPI(
        email=os.environ.get("BLOSSOM_EMAIL"),
        password=os.environ.get("BLOSSOM_PASSWORD"),
        api_key=os.environ.get("BLOSSOM_API_KEY"),
        # Set this to https://grafeas.org/api/ if using in production
        api_base_url=os.environ.get("BLOSSOM_API_BASE_URL")
        or "http://localhost:8000/api/",
    )
    if os.environ.get("BLOSSOM_EMAIL")
    else None
)

REDDIT = (
    Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_SECRET"),
        password=os.getenv("REDDIT_PASSWORD"),
        username=os.getenv("REDDIT_USERNAME"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
    )
    if os.getenv("REDDIT_CLIENT_ID")
    else None
)

# The path to the log file
LOG_FILE_PATH: str = os.environ.get("LOG_FILE_PATH") or os.path.join(
    os.path.dirname(__file__), "bootstrap.log"
)

# The path to the JSON file containing the Redis data
REDIS_DATA_PATH: str = os.environ.get("REDIS_DATA_PATH") or os.path.join(
    os.path.dirname(__file__), "redis.data.json"
)

# The path to the JSON file caching processed data
CACHE_DATA_PATH: str = os.environ.get("CACHE_DATA_PATH") or os.path.join(
    os.path.dirname(__file__), "cache.data.json"
)

# The path to the JSON file caching incomplete data
INCOMPLETE_DATA_PATH: str = os.environ.get("INCOMPLETE_DATA_PATH") or os.path.join(
    os.path.dirname(__file__), "incomplete.data.json"
)

# The allowed users to process. None means all users are allowed
USER_WHITELIST: Optional[List[str]] = (
    os.environ.get("USER_WHITELIST").split(",")
    if os.environ.get("USER_WHITELIST")
    else None
)

# The users not allowed to process. None means no users are disallowed
USER_BLACKLIST: List[str] = (
    os.environ.get("USER_BLACKLIST").split(",")
    if os.environ.get("USER_BLACKLIST")
    else None
)

# The allowed IDs to process. None means all IDs are allowed
ID_WHITELIST: Optional[List[str]] = (
    os.environ.get("ID_WHITELIST").split(",")
    if os.environ.get("ID_WHITELIST")
    else None
)

# The IDs not allowed to process. None means no IDs are disallowed
ID_BLACKLIST: List[str] = (
    os.environ.get("ID_BLACKLIST").split(",")
    if os.environ.get("ID_BLACKLIST")
    else None
)

# Batch size
BATCH_SIZE: int = (
    int(os.environ.get("BATCH_SIZE")) if os.environ.get("BATCH_SIZE") else 20
)

# Start date of data processing
START_DATE: Optional[datetime] = (
    datetime.fromisoformat(os.getenv("START_DATE")) if os.getenv("START_DATE") else None
)

# End date of data processing
END_DATE: Optional[datetime] = (
    datetime.fromisoformat(os.getenv("END_DATE"))
    if os.getenv("END_DATE")
    else START_DATE + timedelta(hours=12)
    if START_DATE
    else None
)


def _is_env_true(var_name: str) -> bool:
    """Check if the env variable is set to true."""
    value = os.getenv(var_name)
    return value is not None and value.casefold() in [
        "true",
        "yes",
        "1",
    ]


REMOVE_ALL: bool = _is_env_true("REMOVE_ALL")
REPORT_NOT_REMOVED: bool = _is_env_true("REPORT_NOT_REMOVED")
