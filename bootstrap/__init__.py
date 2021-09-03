import os
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

# The path to the JSON file containing the Redis data
REDIS_DATA_PATH: str = os.environ.get("REDIS_DATA_PATH") or os.path.join(
    os.path.dirname(__file__), "redis.data.json"
)
# The allowed users to process. None means all users are allowed
USER_WHITELIST: Optional[List[str]] = os.environ.get("USER_WHITELIST").split(
    ","
) if os.environ.get("USER_WHITELIST") else None
# The users not allowed to process. None means no users are disallowed
USER_BLACKLIST: List[str] = os.environ.get("USER_BLACKLIST").split(
    ","
) if os.environ.get("USER_BLACKLIST") else None
# Batch size
BATCH_SIZE: int = int(os.environ.get("BATCH_SIZE")) if os.environ.get(
    "BATCH_SIZE"
) else 20
